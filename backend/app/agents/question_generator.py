"""QuestionGenerationAgent: builds a role-specific assessment from a job description and its anchored rubric.

Generation order (StrategyChain):
1. ``llm``: the configured LLM drafts MCQs, coding challenges, scenario questions and STAR behavioral
   questions from the JD responsibilities, required skills, proficiency level and rubric competencies.
   Every item is schema-validated; coding challenges are kept only if their reference solution passes
   all of their own test cases in the sandbox.
2. ``template``: a deterministic generator driven by the JD's skills, responsibilities and rubric
   (not by department name), so previously unseen roles still receive relevant questions.

Gaps left by the LLM (for example a rejected coding challenge) are filled from the template output.
Results are persisted per JD + rubric version (QuestionSet), which is both the cache and the guarantee
that all applicants to the same rubric version receive identical questions.
"""
import copy
import hashlib
import json
import re
import threading
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.agents.base_agent import EvaluationStrategy, LLMStrategy, StrategyChain
from app.agents.question_banks import CODING_BANK, CODING_SKILLS, MCQ_BANK, SKILL_ALIASES, SOFTWARE_SKILLS
from app.config import settings
from app.database.models import JobDescription, QuestionSet, Rubric
from app.services.code_sandbox import run_python_tests

GENERATOR_VERSION = "qgen-2"
OPEN_ENDED_TYPES = {"short_answer", "scenario", "case_analysis"}
_generation_lock = threading.Lock()


def proficiency_for(min_experience: Optional[float]) -> str:
    years = float(min_experience or 0)
    if years < 2:
        return "foundational"
    if years <= 5:
        return "intermediate"
    return "advanced"


def responsibilities_from(description: str) -> List[str]:
    """Sentences or bullet lines from the JD that describe work to be done."""
    parts = re.split(r"(?:\n+|[•;]|(?<=[.!?])\s+)", description or "")
    cleaned = []
    for part in parts:
        text = part.strip(" -*\t.")
        if len(text) < 25:
            continue
        text = re.sub(r"^(we are (seeking|looking for)|looking for|you will|responsible for|the role)\s+", "", text, flags=re.I)
        cleaned.append(text[0].lower() + text[1:] if text else text)
    return cleaned[:6] or ["deliver the core responsibilities described in the job description"]


def _bank_key(skill: str) -> Optional[str]:
    key = skill.lower().strip()
    key = SKILL_ALIASES.get(key, key)
    return key if key in MCQ_BANK else None


def _level_rank(level: str) -> int:
    return {"foundational": 0, "intermediate": 1, "advanced": 2}.get(level, 1)


def _role_domain(skills: List[str]) -> str:
    lowered = {s.lower() for s in skills}
    if lowered & {"machine learning", "pytorch", "tensorflow", "deep learning", "scikit-learn"}:
        return "ml"
    if lowered & SOFTWARE_SKILLS:
        return "software"
    if lowered & {"sql", "pandas", "data analysis", "postgresql", "excel", "power bi", "tableau", "spark"}:
        return "data"
    return "general"


def _duty_for(skill: str, duties: List[str], fallback_index: int) -> str:
    """The JD responsibility that mentions the skill, else the one sharing the most words with it."""
    key = skill.lower()
    mentioning = [d for d in duties if key in d.lower()]
    if mentioning:
        return mentioning[0]
    words = set(re.findall(r"[a-z]{4,}", key))
    scored = sorted(duties, key=lambda d: -len(words & set(re.findall(r"[a-z]{4,}", d.lower()))))
    if words and scored and words & set(re.findall(r"[a-z]{4,}", scored[0].lower())):
        return scored[0]
    return duties[fallback_index % len(duties)]


def _rubric_competencies(criteria: Dict[str, Any]) -> List[Dict[str, Any]]:
    competencies = ((criteria or {}).get("behavioral_scoring") or {}).get("competencies") or []
    return [c for c in competencies if c.get("competency")] or [
        {"competency": "Communication", "description": "Explains ideas clearly to different audiences.", "max_points": 25},
        {"competency": "Team Collaboration", "description": "Works constructively with others and resolves disagreement.", "max_points": 25},
        {"competency": "Problem Solving", "description": "Breaks down ambiguous problems and validates solutions.", "max_points": 25},
        {"competency": "Adaptability", "description": "Learns quickly and responds well to change and feedback.", "max_points": 25},
    ]


class TemplateQuestionStrategy(EvaluationStrategy):
    """Deterministic, skill- and rubric-driven question generation."""

    def __init__(self):
        super().__init__("template")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        jd = kwargs["jd_data"]
        criteria = kwargs.get("rubric_criteria") or {}
        return {"success": True, "data": build_template_questions(jd, criteria)}


SCENARIO_TEMPLATES = [
    "As {title}, you will {duty}. Describe how you would apply {skill} to this work: the approach you would take, "
    "the main trade-offs or risks, and how you would check that the result is correct.",
    "You join as {title} and are asked to {duty}. Walk through how you would use {skill}: your first steps, the decisions "
    "you would need to make, what could go wrong, and how you would know the work is done well.",
    "A stakeholder asks you, as {title}, to {duty} on a tight deadline. Explain how {skill} shapes your plan, which "
    "corners you would refuse to cut and why, and how you would verify the outcome.",
]
BEHAVIORAL_TEMPLATES = [
    "Tell us about a specific time you demonstrated {competency} in work similar to {title}. "
    "Describe the situation, your task, the actions you personally took, and the result.",
    "Describe a recent situation where {competency} made the difference to an outcome. What was at stake, what did you "
    "personally do, and what happened as a result?",
    "Think of a time when your {competency} was tested under pressure. Explain the context, your responsibility, the steps "
    "you took, and the measurable result.",
]


def _rotate(items: List[Any], offset: int) -> List[Any]:
    if not items:
        return items
    offset %= len(items)
    return items[offset:] + items[:offset]


def build_template_questions(jd: Dict[str, Any], criteria: Dict[str, Any], variant: int = 0) -> Dict[str, Any]:
    """Deterministic for a given variant; regeneration asks for the next variant to obtain different questions."""
    required = [s for s in (jd.get("required_skills") or []) if s]
    preferred = [s for s in (jd.get("preferred_skills") or []) if s]
    evaluated = ((criteria or {}).get("technical_scoring") or {}).get("skills_evaluated") or required
    level = proficiency_for(jd.get("min_experience"))
    duties = responsibilities_from(jd.get("description", ""))
    title = jd.get("title") or "this role"
    technical: List[Dict[str, Any]] = []

    # 1. MCQs for skills with curated items at or below the role's proficiency level.
    used_keys = set()
    bank_skills = [s for s in list(evaluated) + preferred if _bank_key(s)]
    for skill in _rotate(bank_skills, variant):
        key = _bank_key(skill)
        if key in used_keys:
            continue
        items = sorted(MCQ_BANK[key], key=lambda item: abs(_level_rank(item["level"]) - _level_rank(level)))
        item = items[(variant // max(1, len(bank_skills))) % len(items)]
        used_keys.add(key)
        technical.append({"type": "mcq", "competency_or_skill": skill, "proficiency": item["level"],
                          "prompt": item["prompt"], "options": item["options"],
                          "correct_option": item["correct_option"], "rubric_guideline": item["rubric_guideline"]})
        if len([q for q in technical if q["type"] == "mcq"]) >= 2:
            break

    # 2. Coding challenge when the role's skills involve writing code.
    if {s.lower() for s in required} & CODING_SKILLS:
        domain = _role_domain(required + preferred)
        candidates = [c for c in CODING_BANK if domain in c["domains"]] or [c for c in CODING_BANK if "general" in c["domains"]]
        ranked = sorted(candidates, key=lambda c: (abs(_level_rank(c["level"]) - _level_rank(level)), c["key"]))
        challenge = ranked[variant % len(ranked)]
        technical.append(_coding_question(challenge))

    # 3. Scenario questions for required skills not otherwise assessed, anchored to JD responsibilities.
    covered = {q["competency_or_skill"].lower() for q in technical}
    open_skills = [s for s in evaluated if s.lower() not in covered] or required[:1] or ["the core skills of the role"]
    template = SCENARIO_TEMPLATES[variant % len(SCENARIO_TEMPLATES)]
    for index, skill in enumerate(_rotate(open_skills, variant)[:2]):
        duty = _duty_for(skill, duties, index + variant)
        technical.append({
            "type": "scenario", "competency_or_skill": skill, "proficiency": level,
            "prompt": template.format(title=title, duty=duty, skill=skill),
            "rubric_guideline": (f"Strong answers apply {skill} concretely to: {duty}. Expected elements: a stepwise approach, "
                                 f"named tools or techniques for {skill}, at least one trade-off or risk, and a validation or quality check. "
                                 f"Depth expected: {level}."),
        })

    behavioral = []
    for competency in _rubric_competencies(criteria)[:4]:
        name = competency["competency"]
        description = competency.get("description") or ""
        behavioral.append({
            "type": "behavioral", "competency_or_skill": name, "proficiency": level,
            "prompt": BEHAVIORAL_TEMPLATES[variant % len(BEHAVIORAL_TEMPLATES)].format(competency=name.lower(), title=title),
            "rubric_guideline": (f"STAR anchors for {name}: {description} Score the specificity of the Situation and Task, "
                                 "the candidate's own Actions, and a concrete, preferably measurable Result."),
            "max_points": competency.get("max_points"),
        })
    return {"technical_questions": technical, "behavioral_questions": behavioral}


def _coding_question(challenge: Dict[str, Any]) -> Dict[str, Any]:
    return {"type": "coding", "competency_or_skill": challenge["skill"], "proficiency": challenge["level"],
            "title": challenge["title"], "prompt": challenge["prompt"], "rubric_guideline": challenge["rubric_guideline"],
            "coding": {"language": "python", "function_name": challenge["function_name"],
                       "starter_code": challenge["starter_code"], "tests": copy.deepcopy(challenge["tests"]),
                       "reference_solution": challenge["reference_solution"]}}


def _validate_llm_questions(data: Dict[str, Any], verify_code: bool = True) -> Tuple[List[Dict], List[Dict], List[str]]:
    """Keeps only well-formed items; coding items must pass their own tests with the reference solution."""
    notes: List[str] = []
    technical: List[Dict[str, Any]] = []
    for raw in (data.get("technical_questions") or [])[:8]:
        if not isinstance(raw, dict):
            continue
        kind = str(raw.get("type", "")).lower()
        prompt = str(raw.get("prompt") or "").strip()
        skill = str(raw.get("competency_or_skill") or raw.get("skill") or "").strip()[:80]
        if not prompt or not skill or len(prompt) > 1500:
            continue
        base = {"type": kind, "competency_or_skill": skill, "proficiency": str(raw.get("proficiency") or "intermediate"),
                "prompt": prompt, "rubric_guideline": str(raw.get("rubric_guideline") or "")[:800]}
        if kind == "mcq":
            options = [str(o)[:300] for o in (raw.get("options") or [])]
            answer = str(raw.get("correct_option") or "").strip().upper()[:1]
            if len(options) != 4 or answer not in "ABCD" or not answer:
                notes.append(f"Dropped malformed MCQ for {skill}.")
                continue
            options = [o if re.match(r"^[A-D]\)", o) else f"{'ABCD'[i]}) {o}" for i, o in enumerate(options)]
            technical.append({**base, "options": options, "correct_option": answer})
        elif kind == "coding":
            coding = raw.get("coding") or {}
            fn = str(coding.get("function_name") or "")
            tests = coding.get("tests") or []
            solution = str(coding.get("reference_solution") or "")
            if not re.match(r"^[a-z_][a-z0-9_]*$", fn) or len(tests) < 3 or not solution:
                notes.append(f"Dropped coding challenge for {skill}: incomplete specification.")
                continue
            tests = [{"args": t.get("args", []), "expected": t.get("expected"), "hidden": bool(t.get("hidden"))}
                     for t in tests[:12] if isinstance(t, dict) and isinstance(t.get("args", []), list)]
            if not any(t["hidden"] for t in tests):
                for t in tests[len(tests) // 2:]:
                    t["hidden"] = True
            if verify_code:
                check = run_python_tests(solution, fn, tests)
                if check["status"] != "OK" or check["passed"] != check["total"]:
                    notes.append(f"Dropped coding challenge for {skill}: reference solution failed its own tests.")
                    continue
            technical.append({**base, "title": str(raw.get("title") or "Coding challenge")[:80],
                              "coding": {"language": "python", "function_name": fn, "tests": tests,
                                         "starter_code": str(coding.get("starter_code") or f"def {fn}():\n    pass\n")[:2000],
                                         "reference_solution": solution}})
        elif kind in OPEN_ENDED_TYPES:
            technical.append({**base, "type": "scenario" if kind == "case_analysis" else kind})
    behavioral = []
    for raw in (data.get("behavioral_questions") or [])[:5]:
        if isinstance(raw, dict) and raw.get("prompt") and raw.get("competency_or_skill"):
            behavioral.append({"type": "behavioral", "competency_or_skill": str(raw["competency_or_skill"])[:80],
                               "prompt": str(raw["prompt"])[:1500], "rubric_guideline": str(raw.get("rubric_guideline") or "")[:800]})
    return technical, behavioral, notes


class QuestionGenerationAgent:
    """Generates and caches the standard assessment for a JD + rubric version."""

    SYSTEM_PROMPT = (
        "You design fair, job-related hiring assessments. Use only the job description and rubric supplied. "
        "Never ask about age, gender, ethnicity, religion, disability, family status, nationality or other protected characteristics. "
        "Return JSON with keys technical_questions and behavioral_questions.\n"
        "technical_questions: 4-6 items. Each item has type (mcq|coding|scenario|short_answer), competency_or_skill (a JD skill), "
        "proficiency (foundational|intermediate|advanced), prompt, rubric_guideline (what a strong answer contains). "
        "mcq items add options (exactly 4 strings prefixed 'A) '..'D) ') and correct_option (A-D). "
        "Include exactly one coding item only if the role writes code; it adds coding: {function_name, starter_code, "
        "reference_solution (Python 3, standard library only), tests: [{args: [...], expected: ..., hidden: bool}] with 5-8 JSON-serialisable tests, at least 2 hidden}. "
        "Include at least one scenario item grounded in a stated responsibility.\n"
        "behavioral_questions: one STAR question per rubric competency, each with competency_or_skill, prompt and rubric_guideline."
    )

    @staticmethod
    def generate(jd_data: Dict[str, Any], rubric_criteria: Dict[str, Any], candidate_id: Optional[str] = None,
                 use_llm: bool = True, variant: int = 0, avoid_prompts: Optional[List[str]] = None) -> Dict[str, Any]:
        template = build_template_questions(jd_data, rubric_criteria, variant)
        notes: List[str] = []
        generator = "template"
        technical, behavioral = template["technical_questions"], template["behavioral_questions"]

        llm_enabled = use_llm and settings.LLM_PROVIDER in ("gemini", "default") and bool(settings.GEMINI_API_KEY)
        if llm_enabled:
            competencies = [c["competency"] for c in _rubric_competencies(rubric_criteria)]
            user_prompt = json.dumps({
                "title": jd_data.get("title"), "department": jd_data.get("department"),
                "description": (jd_data.get("description") or "")[:3000],
                "required_skills": jd_data.get("required_skills") or [], "preferred_skills": jd_data.get("preferred_skills") or [],
                "proficiency_level": proficiency_for(jd_data.get("min_experience")),
                "rubric_technical_skills": ((rubric_criteria or {}).get("technical_scoring") or {}).get("skills_evaluated"),
                "rubric_behavioral_competencies": competencies,
                "do_not_repeat_these_questions": (avoid_prompts or [])[:12],
            })
            chain = StrategyChain([("llm", LLMStrategy()), ("template", TemplateQuestionStrategy())],
                                  agent_name="QuestionGenerationAgent", candidate_id=candidate_id)
            result = chain.execute(system_prompt=QuestionGenerationAgent.SYSTEM_PROMPT, user_prompt=user_prompt,
                                   required_keys=("technical_questions",), jd_data=jd_data, rubric_criteria=rubric_criteria)
            if result["successful_strategy"] == "llm":
                llm_technical, llm_behavioral, notes = _validate_llm_questions(result["data"])
                if llm_technical:
                    generator = "llm"
                    technical = llm_technical
                    template_coding = [q for q in template["technical_questions"] if q["type"] == "coding"]
                    if template_coding and not any(q["type"] == "coding" for q in technical):
                        technical.append(template_coding[0])
                        generator = "llm+template"
                        notes.append("Coding challenge supplied by the verified template bank.")
                if len(llm_behavioral) >= 2:
                    behavioral = llm_behavioral
            else:
                notes.append("LLM generation unavailable; deterministic template used.")

        for index, question in enumerate(technical, start=1):
            question["question_id"] = f"TECH_Q{index}"
        for index, question in enumerate(behavioral, start=1):
            question["question_id"] = f"BEH_Q{index}"
        return {"technical_questions": technical, "behavioral_questions": behavioral, "generator": generator, "notes": notes}


def _content_hash(jd: JobDescription, rubric: Rubric) -> str:
    material = {"v": GENERATOR_VERSION, "title": jd.title, "description": jd.description,
                "required": jd.required_skills or [], "preferred": jd.preferred_skills or [],
                "min_experience": jd.min_experience, "criteria": rubric.criteria or {}}
    return hashlib.sha256(json.dumps(material, sort_keys=True, default=str).encode()).hexdigest()


class QuestionRegenerationError(RuntimeError):
    """Raised when regeneration cannot produce a question set that differs from the current one."""


def question_fingerprint(technical: List[Dict[str, Any]], behavioral: List[Dict[str, Any]]) -> str:
    material = [(q.get("type"), q.get("competency_or_skill"), q.get("prompt")) for q in list(technical) + list(behavioral)]
    return hashlib.sha256(json.dumps(material, sort_keys=True).encode()).hexdigest()


def get_or_create_question_set(db: Session, jd: JobDescription, rubric: Rubric, force_new: bool = False) -> QuestionSet:
    """Returns the cached question set for this JD + rubric version, generating it once if needed.

    With force_new (regeneration) a new set is generated with the next template variant and, when an LLM is
    configured, an instruction not to repeat the current questions. The new set is only saved if it differs
    from the current one; otherwise QuestionRegenerationError is raised so callers never report a false success.
    """
    digest = _content_hash(jd, rubric)
    with _generation_lock:
        existing = (db.query(QuestionSet)
                    .filter(QuestionSet.jd_id == jd.jd_id, QuestionSet.rubric_version == rubric.version,
                            QuestionSet.content_hash == digest)
                    .order_by(QuestionSet.created_at.desc()).first())
        if existing and not force_new:
            return existing
        jd_data = {"jd_id": jd.jd_id, "title": jd.title, "department": jd.department, "description": jd.description,
                   "required_skills": jd.required_skills or [], "preferred_skills": jd.preferred_skills or [],
                   "min_experience": jd.min_experience}
        previous_fp = question_fingerprint(existing.technical_questions or [], existing.behavioral_questions or []) if existing else None
        avoid = [q.get("prompt", "") for q in (existing.technical_questions or [])] if existing else []
        start_variant = db.query(QuestionSet).filter(QuestionSet.jd_id == jd.jd_id,
                                                    QuestionSet.rubric_version == rubric.version).count()
        generated = None
        for variant in range(start_variant, start_variant + 6):
            candidate = QuestionGenerationAgent.generate(jd_data, rubric.criteria or {}, variant=variant, avoid_prompts=avoid)
            if question_fingerprint(candidate["technical_questions"], candidate["behavioral_questions"]) != previous_fp:
                generated = candidate
                break
        if generated is None:
            raise QuestionRegenerationError("No different questions could be generated for this job's current skills and rubric.")
        question_set = QuestionSet(jd_id=jd.jd_id, rubric_version=rubric.version, content_hash=digest,
                                   generator=generated["generator"], technical_questions=generated["technical_questions"],
                                   behavioral_questions=generated["behavioral_questions"], generation_notes=generated["notes"])
        db.add(question_set)
        db.commit()
        db.refresh(question_set)
        return question_set


def sanitize_questions_for_candidate(questions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Removes answer keys, scoring guidance, reference solutions and hidden tests before delivery."""
    sanitized = []
    for question in questions or []:
        item = {k: v for k, v in question.items() if k not in ("correct_option", "rubric_guideline", "max_points")}
        if "coding" in question:
            coding = question["coding"]
            item["coding"] = {"language": coding.get("language", "python"), "function_name": coding.get("function_name"),
                              "starter_code": coding.get("starter_code", ""),
                              "examples": [{"args": t.get("args"), "expected": t.get("expected")}
                                           for t in coding.get("tests", []) if not t.get("hidden")],
                              "hidden_test_count": sum(1 for t in coding.get("tests", []) if t.get("hidden"))}
        sanitized.append(item)
    return sanitized
