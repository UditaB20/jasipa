"""Composable evaluation strategies and auditable fallback-chain execution."""
from abc import ABC, abstractmethod
from datetime import datetime
import re
import time
import uuid
from typing import Any, Dict, List, Optional, Sequence, Tuple

from app.config import settings


class EvaluationStrategy(ABC):
    def __init__(self, strategy_name: str, fallback_level: int = 0):
        self.strategy_name = strategy_name
        self.fallback_level = fallback_level
        self.execution_time = 0

    @abstractmethod
    def evaluate(self, **kwargs) -> Dict[str, Any]:
        """Return a dictionary with at least a success boolean."""
        raise NotImplementedError


class LLMStrategy(EvaluationStrategy):
    def __init__(self):
        super().__init__("llm")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        from app.agents.llm_factory import LLMService
        started = time.perf_counter()
        try:
            data = LLMService.call_llm(
                kwargs["system_prompt"], kwargs["user_prompt"],
                response_schema=kwargs.get("response_schema"),
                timeout_seconds=kwargs.get("timeout_seconds", settings.FALLBACK_TIMEOUT_SECONDS),
                model_name=kwargs.get("model_name"), raise_errors=True
            )
            missing = [key for key in kwargs.get("required_keys", []) if key not in data]
            if not data or missing:
                return {"success": False, "data": {}, "error": "LLM_INVALID_RESPONSE", "latency_ms": _elapsed_ms(started)}
            return {"success": True, "data": data, "error": None, "latency_ms": _elapsed_ms(started)}
        except Exception as exc:
            if str(exc) == "LLM_DISABLED":
                error = "LLM_DISABLED"
            else:
                error = "LLM_TIMEOUT" if "timeout" in type(exc).__name__.lower() else "LLM_API_ERROR"
            return {"success": False, "data": {}, "error": error, "latency_ms": _elapsed_ms(started)}


def mentions(text: str, term: str) -> bool:
    """Word-bounded, case-insensitive match that also works for terms like C++, C# and Node.js."""
    term = str(term or "").lower().strip()
    return bool(term) and re.search(r"(?<![a-z0-9])" + re.escape(term) + r"(?![a-z0-9])", text) is not None


class RegexStrategy(EvaluationStrategy):
    """Evidence-based resume matcher scored with the rubric's anchored resume weights."""
    def __init__(self):
        super().__init__("regex")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        resume = (kwargs.get("resume_text") or "").strip()
        jd = kwargs.get("jd_data") or {}
        rubric = kwargs.get("rubric_data") or {}
        required = jd.get("required_skills") or []
        preferred = jd.get("preferred_skills") or []
        if len(resume) < 30:
            return {"success": True, "data": {"status": "INSUFFICIENT_EVIDENCE", "score": 0.0,
                    "matched_skills": [], "matched_requirements": [], "missing_requirements": required,
                    "experience_years": 0.0, "experience_match": False,
                    "evidence": ["Insufficient resume text for deterministic screening."]}}

        lowered = resume.lower()
        matched = [skill for skill in required if mentions(lowered, skill)]
        missing = [skill for skill in required if skill not in matched]
        matched_preferred = [skill for skill in preferred if mentions(lowered, skill)]
        year_patterns = (
            r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:\w+\s+){0,3}?experience",
            r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        )
        years = [float(value) for pattern in year_patterns for value in re.findall(pattern, lowered) if 0 < float(value) <= 50]
        experience = max(years, default=float(kwargs.get("profile_experience_years") or 0.0))
        minimum = float(jd.get("min_experience") or 0)

        anchors = (rubric.get("criteria") or {}).get("resume_scoring") or {}
        req_weight = float(anchors.get("required_skills_weight", 50))
        pref_weight = float(anchors.get("preferred_skills_weight", 15))
        exp_weight = float(anchors.get("experience_weight", 20))
        edu_weight = float(anchors.get("education_and_projects_weight", 15))
        total_weight = (req_weight + pref_weight + exp_weight + edu_weight) or 100.0

        req_ratio = len(matched) / len(required) if required else 1.0
        pref_ratio = len(matched_preferred) / len(preferred) if preferred else 1.0
        exp_ratio = 1.0 if not minimum or experience >= minimum else experience / minimum
        has_degree = re.search(r"\b(bachelor|master|ph\.?d|b\.?\s?tech|m\.?\s?tech|b\.?\s?sc|m\.?\s?sc|degree|diploma)\b", lowered)
        has_projects = re.search(r"\b(project|built|developed|designed|led|implemented|launched|delivered)\b", lowered)
        edu_ratio = (0.6 if has_degree else 0.0) + (0.4 if has_projects else 0.0)
        points = req_ratio * req_weight + pref_ratio * pref_weight + exp_ratio * exp_weight + edu_ratio * edu_weight
        score = round(max(0.0, min(100.0, 100.0 * points / total_weight)), 1)

        evidence = [f"Resume mentions required skill: {skill}." for skill in matched[:5]]
        if missing:
            evidence.append(f"No resume evidence for required skill(s): {', '.join(missing[:5])}.")
        evidence.append(f"Resume states {experience:g} years of experience (minimum {minimum:g})." if experience
                        else "Years of experience were not stated in the resume.")
        evidence.append(f"Rubric points: required {req_ratio * req_weight:.1f}/{req_weight:g}, preferred {pref_ratio * pref_weight:.1f}/{pref_weight:g}, "
                        f"experience {exp_ratio * exp_weight:.1f}/{exp_weight:g}, education & projects {edu_ratio * edu_weight:.1f}/{edu_weight:g}.")
        return {"success": True, "data": {"status": "COMPLETED", "score": score,
                "matched_skills": matched, "matched_requirements": matched, "missing_requirements": missing,
                "matched_preferred": matched_preferred, "experience_years": experience,
                "experience_match": experience >= minimum if minimum else True, "evidence": evidence}}


def score_open_answer(question: Dict[str, Any], answer: str) -> Tuple[float, str]:
    """Keyword-rubric score for a short-answer or scenario response (deterministic fallback)."""
    lowered = answer.lower()
    guide = str(question.get("rubric_guideline") or "").lower()
    prompt = str(question.get("prompt") or "").lower()
    stop = {"the", "and", "for", "from", "with", "that", "this", "which", "what", "write", "query", "answer", "expects",
            "strong", "answers", "expected", "elements", "least", "one", "would", "how", "your", "you", "will", "describe",
            "role", "work", "main", "depth", "named", "take", "check", "result", "approach", "apply", "into", "such"}
    keywords = {w.strip(".,:;()") for w in re.findall(r"[a-z][a-z0-9_+#.-]{2,}", guide + " " + prompt)} - stop
    hits = sorted(word for word in keywords if word and mentions(lowered, word))
    words = len(answer.split())
    structure = 15.0 if words >= 40 else 8.0 if words >= 15 else 0.0
    coverage = min(60.0, 60.0 * len(hits) / max(6, len(keywords) // 3)) if keywords else 30.0
    score = round(min(100.0, (20.0 if words >= 5 else 0.0) + coverage + structure), 1)
    return score, f"keyword rubric matched {len(hits)} relevant term(s), {words} words"


class HeuristicStrategy(EvaluationStrategy):
    """Deterministic scoring of open-ended technical answers (MCQ and coding are scored objectively elsewhere)."""
    def __init__(self):
        super().__init__("heuristic")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        questions = kwargs.get("questions") or []
        answers = {a.get("question_id"): str(a.get("answer_text", "")).strip() for a in kwargs.get("answers", [])}
        if not questions:
            return {"success": False, "data": {}, "error": "NO_QUESTIONS"}
        question_scores: Dict[str, float] = {}
        evidence: List[str] = []
        for question in questions:
            qid = question.get("question_id")
            skill = question.get("competency_or_skill", "General")
            answer = answers.get(qid, "")
            if not answer:
                question_scores[qid] = 0.0
                evidence.append(f"{skill}: question {qid} was unanswered.")
                continue
            score, detail = score_open_answer(question, answer)
            question_scores[qid] = score
            evidence.append(f"{skill}: {detail} ({score:.0f}/100).")
        overall = round(sum(question_scores.values()) / len(question_scores), 1)
        return {"success": True, "data": {"score": overall, "question_scores": question_scores,
                                          "evidence": evidence, "status": "COMPLETED"}}


class STARFrameworkStrategy(EvaluationStrategy):
    """Scores presence of STAR response structure, not personality or cultural similarity."""
    MARKERS = {
        "situation": ("situation", "when i", "during", "in a project", "previous role", "at my previous", "while working", "last year", "once"),
        "task": ("task", "responsible for", "needed to", "goal was", "required me to", "challenge was", "my role", "asked to", "had to"),
        "action": ("i implemented", "i organized", "i proposed", "i analyzed", "i communicated", "i decided", "i built", "i led",
                   "i created", "i set up", "i scheduled", "i worked", "i wrote", "i reached out", "i introduced", "i designed", "we agreed"),
        "result": ("result", "outcome", "improved", "reduced", "delivered", "resolved", "learned", "achieved", "increased", "saved", "%"),
    }

    def __init__(self):
        super().__init__("star")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        questions = kwargs.get("questions") or []
        answers = {a.get("question_id"): str(a.get("answer_text", "")).strip() for a in kwargs.get("answers", [])}
        weights = kwargs.get("competency_weights") or {}
        if not questions:
            return {"success": False, "data": {}, "error": "NO_QUESTIONS"}
        scores: Dict[str, List[float]] = {}
        names: Dict[str, str] = {}
        evidence = []
        any_star = False
        for question in questions:
            competency = question.get("competency_or_skill", "behavioral")
            key = re.sub(r"[^a-z0-9]+", "_", competency.lower()).strip("_")[:64] or "behavioral"
            names[key] = competency
            text = answers.get(question.get("question_id"), "").lower()
            components = {part: any(marker in text for marker in markers) for part, markers in self.MARKERS.items()}
            detected = sum(components.values())
            words = len(text.split())
            if words == 0:
                score = 0.0
            elif words < 10:
                score = 20.0
            else:
                score = min(100.0, 30.0 + detected * 15.0 + (10.0 if words >= 60 else 0.0))
            any_star = any_star or detected >= 3
            scores.setdefault(key, []).append(score)
            missing = [part.title() for part, present in components.items() if not present]
            evidence.append(f"{competency}: {detected}/4 STAR components evident"
                            + (f" (missing: {', '.join(missing)})." if missing else "."))
        breakdown = {key: round(sum(values) / len(values), 1) for key, values in scores.items()}
        total_weight = sum(float(weights.get(names[key], 1.0) or 1.0) for key in breakdown)
        overall = sum(breakdown[key] * float(weights.get(names[key], 1.0) or 1.0) for key in breakdown) / (total_weight or 1)
        return {"success": True, "data": {"breakdown": breakdown, "score": round(overall, 1),
                "star_detected": any_star, "evidence": evidence, "status": "COMPLETED"}}


class TemplateSynthesisStrategy(EvaluationStrategy):
    """Grounded prose template over already-computed, deterministic panel facts."""
    def __init__(self):
        super().__init__("template")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        strengths = kwargs.get("strengths", [])
        gaps = kwargs.get("gaps", [])
        disagreements = kwargs.get("disagreements", [])
        score = kwargs.get("merged_score", 0)
        recommendation = kwargs.get("recommendation", "HUMAN_REVIEW_REQUIRED")
        routing = {"PROCEED_TO_HUMAN_REVIEW": "proceed to reviewer decision",
                   "HUMAN_REVIEW_REQUIRED": "needs careful review",
                   "ADDITIONAL_INFORMATION_REQUIRED": "incomplete evidence"}.get(recommendation, recommendation)

        def join(items: List[str], empty: str) -> str:
            return "; ".join(item.rstrip(". ") for item in items) + "." if items else empty

        summary = (f"Panel score {score}/100 ({routing}). Strengths: {join(strengths, 'none above the strength threshold.')} "
                   f"Gaps: {join(gaps, 'none below the gap threshold.')} "
                   f"Notes: {join(disagreements, 'agent scores were consistent.')} A human reviewer makes the final decision.")
        factors = [f"Resume {kwargs.get('resume_score', 0)}/100",
                   f"Technical {kwargs.get('skill_score', 0)}/100",
                   f"Behavioral {kwargs.get('culture_score', 0)}/100"]
        return {"success": True, "data": {"summary": summary, "decision_factors": factors,
                "highlighted_concerns": gaps, "highlighted_strengths": strengths}, "error": None}


class HumanExpertStrategy(EvaluationStrategy):
    """Persist a task for HR follow-up; never makes or implies a hiring decision."""
    def __init__(self):
        super().__init__("human_expert")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        try:
            from app.database.models import HumanExpertTask
            from app.database.session import SessionLocal
            with SessionLocal() as db:
                task = HumanExpertTask(candidate_id=kwargs.get("candidate_id"),
                    agent_name=kwargs.get("agent_name", "EvaluationAgent"),
                    reason=kwargs.get("task_reason", "Automated evaluation strategies could not produce a result."),
                    status="PENDING", assigned_to="HR_EXPERT")
                db.add(task)
                db.commit()
                db.refresh(task)
                return {"success": True, "data": {"task_id": task.task_id, "status": "pending"}, "error": None}
        except Exception as exc:
            return {"success": False, "data": {}, "error": f"HUMAN_TASK_CREATE_FAILED:{type(exc).__name__}"}


class StrategyChain:
    def __init__(self, strategies: Sequence[Tuple[str, EvaluationStrategy]], timeout_seconds: Optional[float] = None,
                 agent_name: str = "EvaluationAgent", candidate_id: Optional[str] = None):
        self.strategies = list(strategies)
        self.timeout_seconds = float(timeout_seconds or settings.FALLBACK_TIMEOUT_SECONDS)
        self.agent_name = agent_name
        self.candidate_id = candidate_id

    def execute(self, **kwargs) -> Dict[str, Any]:
        attempts = []
        invocation_id = str(uuid.uuid4())
        total_start = time.perf_counter()
        for depth, (name, strategy) in enumerate(self.strategies):
            strategy.strategy_name = name
            strategy.fallback_level = depth
            started = time.perf_counter()
            try:
                result = strategy.evaluate(timeout_seconds=self.timeout_seconds, **kwargs)
                elapsed = int(result.get("latency_ms", _elapsed_ms(started)))
                success = bool(result.get("success"))
                error = result.get("error")
                data = result.get("data") or {}
            except Exception as exc:
                elapsed = _elapsed_ms(started)
                success = False
                error = f"STRATEGY_ERROR:{type(exc).__name__}"
                data = {}
            strategy.execution_time = elapsed
            attempt = {"strategy_name": name, "success": success, "error": error, "latency_ms": elapsed}
            attempts.append(attempt)
            self._record_attempt(invocation_id, depth, name, success, error, elapsed, kwargs.get("candidate_id") or self.candidate_id)
            if success:
                return {"successful_strategy": name, "data": data, "attempts": attempts, "invocation_id": invocation_id,
                        "total_latency_ms": _elapsed_ms(total_start), "fallback_chain_depth": depth,
                        "attempts_before_success": depth}
        return {"successful_strategy": None, "data": {}, "attempts": attempts, "invocation_id": invocation_id,
                "total_latency_ms": _elapsed_ms(total_start), "fallback_chain_depth": max(0, len(attempts) - 1),
                "attempts_before_success": len(attempts)}

    def _record_attempt(self, invocation_id: str, depth: int, name: str, success: bool, error: Optional[str], latency_ms: int, candidate_id: Optional[str]):
        try:
            from app.database.models import StrategyMetric
            from app.database.session import SessionLocal
            with SessionLocal() as db:
                db.add(StrategyMetric(invocation_id=invocation_id, fallback_level=depth, candidate_id=candidate_id, agent_name=self.agent_name,
                    strategy_name=name, success=success, error_code=(error or "")[:120], latency_ms=latency_ms,
                    timestamp=datetime.utcnow()))
                db.commit()
        except Exception:
            # Evaluation remains usable even if optional monitoring storage is unavailable.
            pass


def configured_chain(strategy_map: Dict[str, EvaluationStrategy], default_order: Sequence[str],
                     agent_name: str, candidate_id: Optional[str] = None) -> StrategyChain:
    from app.agents.llm_factory import llm_available
    if not llm_available():
        # No provider configured: skip the LLM rather than recording a guaranteed failure on every call.
        strategy_map = {name: strategy for name, strategy in strategy_map.items() if name != "llm"}
        default_order = [name for name in default_order if name != "llm"]
    configured = settings.FALLBACK_STRATEGY_CHAIN
    order = [name for name in configured if name in strategy_map]
    if not settings.ENABLE_HUMAN_EXPERT_FALLBACK:
        order = [name for name in order if name != "human_expert"]
    # Preserve required, agent-compatible fallbacks if the environment list names other agents' strategies.
    order += [name for name in default_order if name in strategy_map and name not in order]
    if not settings.ENABLE_HUMAN_EXPERT_FALLBACK:
        order = [name for name in order if name != "human_expert"]
    if not order:
        order = list(default_order)
    return StrategyChain([(name, strategy_map[name]) for name in order], settings.FALLBACK_TIMEOUT_SECONDS,
                         agent_name=agent_name, candidate_id=candidate_id)


def _elapsed_ms(started: float) -> int:
    return max(0, int((time.perf_counter() - started) * 1000))
