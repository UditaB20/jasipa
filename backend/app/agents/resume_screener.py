from typing import Any, Dict
from app.agents.base_agent import LLMStrategy, RegexStrategy, HeuristicStrategy, StrategyChain, configured_chain
from app.schemas.screening import ResumeScreeningOutput


class ResumeScreenerAgent:
    """Evidence-based resume screening with a configurable, auditable strategy chain."""

    @staticmethod
    def evaluate(candidate_id: str, resume_text: str, jd_data: Dict[str, Any], rubric_data: Dict[str, Any]) -> ResumeScreeningOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        rubric_version = rubric_data.get("version", "1.0")
        required = jd_data.get("required_skills", []) or []
        if not resume_text or len(resume_text.strip()) < 30:
            return ResumeScreeningOutput(candidate_id=candidate_id, jd_id=jd_id, score=0.0,
                matched_requirements=[], missing_requirements=required, experience_match=False,
                evidence=["Insufficient resume text provided for evaluation."], rubric_version=rubric_version,
                status="INSUFFICIENT_EVIDENCE")

        system_prompt = (
            "Evaluate the resume against the supplied job requirements using only explicit evidence. "
            "Do not make a hiring decision. Return JSON keys: score (0-100), matched_requirements, "
            "missing_requirements, experience_match (boolean), evidence (string list)."
        )
        user_prompt = (f"Job: {jd_data.get('title', '')}\nRequired skills: {required}\n"
                       f"Preferred skills: {jd_data.get('preferred_skills', [])}\n"
                       f"Minimum experience: {jd_data.get('min_experience', 0)} years\nResume:\n{resume_text[:3000]}")
        chain = configured_chain({"llm": LLMStrategy(), "regex": RegexStrategy(), "heuristic": HeuristicStrategy()},
                                 ("llm", "regex", "heuristic"), "ResumeScreenerAgent", candidate_id)
        result = chain.execute(candidate_id=candidate_id, resume_text=resume_text, jd_data=jd_data,
                               rubric_data=rubric_data, system_prompt=system_prompt, user_prompt=user_prompt,
                               required_keys=("score", "matched_requirements"))
        data = result["data"]
        strategy = result["successful_strategy"] or "none"
        if not result["successful_strategy"]:
            status = "EVALUATION_FAILED"
        else:
            status = data.get("status", "COMPLETED")
        evidence = list(data.get("evidence") or [])
        if not result["successful_strategy"]:
            evidence.extend(f"{attempt['strategy_name']} failed ({attempt.get('error') or 'unknown error'})." for attempt in result["attempts"])
        return ResumeScreeningOutput(
            candidate_id=candidate_id, jd_id=data.get("jd_id", jd_id), score=float(data.get("score", 0)),
            matched_requirements=list(data.get("matched_requirements", data.get("matched_skills", []))),
            missing_requirements=list(data.get("missing_requirements", [])),
            experience_match=bool(data.get("experience_match", False)), evidence=evidence[:8],
            rubric_version=rubric_version, status=status, strategy_used=strategy,
            fallback_chain_depth=result["fallback_chain_depth"], fallback_latency_ms=result["total_latency_ms"],
            attempts_before_success=result["attempts_before_success"])
