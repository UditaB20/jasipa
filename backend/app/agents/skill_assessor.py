from typing import Any, Dict, List
from app.agents.base_agent import LLMStrategy, HeuristicStrategy, HumanExpertStrategy, configured_chain
from app.schemas.assessment import SkillAssessorOutput


class SkillAssessorAgent:
    """Technical assessment agent; deterministic assessment is the configured fallback."""

    @staticmethod
    def evaluate(candidate_id: str, jd_data: Dict[str, Any], questions: List[Dict[str, Any]],
                 submitted_answers: List[Dict[str, str]]) -> SkillAssessorOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        if not submitted_answers:
            return SkillAssessorOutput(candidate_id=candidate_id, jd_id=jd_id, score=0.0,
                skill_breakdown={}, evidence=["No answers submitted for the technical assessment."],
                confidence=0.0, status="INSUFFICIENT_EVIDENCE")
        system_prompt = (
            "Score each technical answer only against its question and rubric. Do not infer ability from a resume. "
            "Return JSON keys score (0-100), skill_breakdown (scores 0-100), evidence (string list)."
        )
        answer_map = {a.get("question_id"): a.get("answer_text", "") for a in submitted_answers}
        details = "\n".join(f"{q.get('question_id')} [{q.get('type')}] {q.get('competency_or_skill')}: "
                             f"{q.get('prompt')}\nRubric: {q.get('rubric_guideline')}\nAnswer: {answer_map.get(q.get('question_id'), 'NO ANSWER')}"
                             for q in questions)
        chain = configured_chain({"llm": LLMStrategy(), "heuristic": HeuristicStrategy(),
                                  "human_expert": HumanExpertStrategy()},
                                 ("llm", "heuristic", "human_expert"), "SkillAssessorAgent", candidate_id)
        result = chain.execute(candidate_id=candidate_id, agent_name="SkillAssessorAgent", jd_data=jd_data,
            questions=questions, answers=submitted_answers, system_prompt=system_prompt,
            user_prompt=f"Technical questions and submitted answers:\n{details}",
            required_keys=("score", "skill_breakdown"), task_reason="Technical assessment strategies were unable to score the submitted responses.")
        data = result["data"]
        strategy = result["successful_strategy"] or "none"
        task_id = data.get("task_id")
        status = "EXPERT_REVIEW_PENDING" if task_id else data.get("status", "EVALUATION_FAILED")
        evidence = list(data.get("evidence") or [])
        if task_id:
            evidence.append(f"Evaluation task {task_id} is awaiting HR expert review; no score was produced.")
        elif strategy == "none":
            evidence.extend(f"{a['strategy_name']} failed ({a.get('error') or 'unknown error'})." for a in result["attempts"])
        return SkillAssessorOutput(candidate_id=candidate_id, jd_id=jd_id, score=float(data.get("score", 0)),
            skill_breakdown={k: float(v) for k, v in (data.get("breakdown") or data.get("skill_breakdown") or {}).items()},
            evidence=evidence, confidence=0.90 if strategy == "heuristic" else 0.95 if strategy == "llm" else 0.0,
            status=status, strategy_used=strategy, fallback_chain_depth=result["fallback_chain_depth"],
            fallback_latency_ms=result["total_latency_ms"], attempts_before_success=result["attempts_before_success"])
