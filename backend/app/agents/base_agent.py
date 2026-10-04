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
            error = "LLM_TIMEOUT" if "timeout" in type(exc).__name__.lower() else "LLM_API_ERROR"
            return {"success": False, "data": {}, "error": error, "latency_ms": _elapsed_ms(started)}


class RegexStrategy(EvaluationStrategy):
    """Evidence-based resume skill and experience matcher."""
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
        matched = [skill for skill in required if re.search(r"\b" + re.escape(str(skill).lower()) + r"\b", lowered)]
        missing = [skill for skill in required if skill not in matched]
        matched_preferred = [skill for skill in preferred if re.search(r"\b" + re.escape(str(skill).lower()) + r"\b", lowered)]
        year_patterns = (
            r"(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)(?:\s+of)?\s+(?:relevant\s+)?experience",
            r"experience\s+(?:of\s+)?(\d+(?:\.\d+)?)\s*\+?\s*(?:years?|yrs?)",
        )
        years = [float(value) for pattern in year_patterns for value in re.findall(pattern, lowered)]
        experience = max(years, default=0.0)
        minimum = float(jd.get("min_experience") or 0)
        weights = rubric.get("criteria") or {}
        # Keep the transparent baseline; rubric weights can scale the two skill components.
        req_weight = float(weights.get("required_skill_weight", 50.0))
        preferred_weight = float(weights.get("preferred_skill_weight", 15.0))
        exp_points = 20.0 if experience >= minimum else (20.0 * experience / minimum if minimum else 20.0)
        req_ratio = len(matched) / len(required) if required else 1.0
        preferred_ratio = len(matched_preferred) / len(preferred) if preferred else 1.0
        education_points = 15.0 if re.search(r"\b(bachelor|master|b\.tech|computer science)\b", lowered) else 10.0
        score = round(max(0.0, min(100.0, req_ratio * req_weight + preferred_ratio * preferred_weight + exp_points + education_points)), 1)
        evidence = [f"Resume mentions required skill: {skill}." for skill in matched[:4]]
        evidence += [f"Resume declares {experience:g} years of experience." if experience else "Experience years were not explicitly found."]
        return {"success": True, "data": {"status": "COMPLETED", "score": score,
                "matched_skills": matched, "matched_requirements": matched, "missing_requirements": missing,
                "matched_preferred": matched_preferred, "experience_years": experience,
                "experience_match": experience >= minimum if minimum else True, "evidence": evidence}}


class HeuristicStrategy(EvaluationStrategy):
    """Deterministic question-type scoring for technical assessments."""
    def __init__(self):
        super().__init__("heuristic")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        questions = kwargs.get("questions") or []
        answers = {a.get("question_id"): str(a.get("answer_text", "")).strip() for a in kwargs.get("answers", [])}
        if not questions:
            return {"success": False, "data": {}, "error": "NO_QUESTIONS"}
        breakdown: Dict[str, float] = {}
        evidence: List[str] = []
        for question in questions:
            qid = question.get("question_id")
            skill = question.get("competency_or_skill", "General")
            answer = answers.get(qid, "")
            kind = str(question.get("type", "short_answer")).lower()
            if not answer:
                score = 0.0
                evidence.append(f"{skill}: Question {qid} was unanswered.")
            elif kind == "mcq":
                correct = str(question.get("correct_option", "")).strip().upper()
                score = 100.0 if correct and re.search(rf"(?<![A-Z0-9]){re.escape(correct)}(?![A-Z0-9])", answer.upper()) else 30.0
                evidence.append(f"{skill}: Multiple-choice answer scored {'correctly' if score == 100 else 'incorrectly'} by answer key.")
            elif kind == "coding":
                lowered = answer.lower()
                function = any(term in lowered for term in ("def ", "function ", "class ", "public ", "=>"))
                logic = any(term in lowered for term in ("if ", "for ", "while ", "return", "visited", "queue", "stack", "recursion"))
                complexity = any(term in lowered for term in ("o(v", "o(n", "o(e", "complexity", "o(log"))
                score = float((30 if function else 0) + (50 if logic else 0) + (20 if complexity else 0))
                evidence.append(f"{skill}: Coding rubric points (function 30, logic 50, complexity 20) = {score:.0f}/100.")
            else:
                lowered = answer.lower()
                guide = str(question.get("rubric_guideline") or "").lower()
                prompt = str(question.get("prompt") or "").lower()
                keywords = set(re.findall(r"[a-z][a-z0-9_+#.-]{2,}", guide + " " + prompt))
                keywords -= {"the", "and", "for", "from", "with", "that", "this", "which", "what", "write", "query", "answer", "expects"}
                hits = sum(1 for word in keywords if word in lowered)
                score = min(100.0, 25.0 + min(60.0, hits * 15.0) + (15.0 if len(answer.split()) >= 12 else 0.0))
                evidence.append(f"{skill}: Short-answer keyword rubric matched {hits} relevant terms.")
            breakdown[skill] = round(score, 1)
        overall = round(sum(breakdown.values()) / len(questions), 1)
        return {"success": True, "data": {"score": overall, "breakdown": breakdown, "evidence": evidence, "status": "COMPLETED"}}


class STARFrameworkStrategy(EvaluationStrategy):
    """Scores presence of STAR response structure, not personality or cultural similarity."""
    MARKERS = {
        "situation": ("situation", "when", "during", "in a project", "previous role", "at my previous"),
        "task": ("task", "responsible for", "needed to", "goal was", "required me to", "challenge was"),
        "action": ("i ", "we ", "implemented", "organized", "proposed", "analyzed", "communicated", "decided"),
        "result": ("result", "outcome", "improved", "reduced", "delivered", "resolved", "learned", "achieved"),
    }

    def __init__(self):
        super().__init__("star")

    def evaluate(self, **kwargs) -> Dict[str, Any]:
        questions = kwargs.get("questions") or []
        answers = {a.get("question_id"): str(a.get("answer_text", "")).strip() for a in kwargs.get("answers", [])}
        if not questions:
            return {"success": False, "data": {}, "error": "NO_QUESTIONS"}
        scores: Dict[str, List[float]] = {}
        evidence = []
        any_star = False
        for question in questions:
            competency = question.get("competency_or_skill", "behavioral")
            key = re.sub(r"[^a-z0-9]+", "_", competency.lower()).strip("_")[:64] or "behavioral"
            text = answers.get(question.get("question_id"), "").lower()
            components = {part: any(marker in text for marker in markers) for part, markers in self.MARKERS.items()}
            detected = sum(components.values())
            score = 40.0 if len(text.split()) < 10 else min(100.0, 40.0 + detected * 15.0)
            any_star = any_star or detected >= 3
            scores.setdefault(key, []).append(score)
            evidence.append(f"{competency}: {detected}/4 STAR components evident in response text.")
        breakdown = {key: round(sum(values) / len(values), 1) for key, values in scores.items()}
        return {"success": True, "data": {"breakdown": breakdown, "score": round(sum(breakdown.values()) / len(breakdown), 1),
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
        summary = f"Panel score: {score}/100. "
        summary += f"Strengths: {'; '.join(strengths) if strengths else 'No major strengths were established.'} "
        summary += f"Gaps: {'; '.join(gaps) if gaps else 'No major gaps were identified.'} "
        summary += f"Review notes: {'; '.join(disagreements) if disagreements else 'Agent scores were aligned.'} "
        summary += f"Routing: {recommendation}. A human reviewer makes the final decision."
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
