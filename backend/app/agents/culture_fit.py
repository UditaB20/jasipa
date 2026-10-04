from typing import Any, Dict, List
from app.agents.base_agent import LLMStrategy, STARFrameworkStrategy, HumanExpertStrategy, configured_chain
from app.schemas.assessment import CultureFitOutput


class CultureFitAgent:
    """Behavioral response assessor; evaluates evidence structure, never demographic or personality fit."""

    @staticmethod
    def evaluate(candidate_id: str, jd_data: Dict[str, Any], questions: List[Dict[str, Any]],
                 submitted_answers: List[Dict[str, str]]) -> CultureFitOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        answer_map = {a.get("question_id"): a.get("answer_text", "").strip() for a in submitted_answers}
        if not submitted_answers:
            return CultureFitOutput(candidate_id=candidate_id, jd_id=jd_id, score=0.0, breakdown={},
                evidence=["Candidate has not submitted behavioral responses. Assessment pending."],
                confidence=0.0, status="INSUFFICIENT_EVIDENCE")
        if sum(len(answer.split()) for answer in answer_map.values()) < 25:
            return CultureFitOutput(candidate_id=candidate_id, jd_id=jd_id, score=0.0,
                breakdown={"communication": 0.0, "teamwork": 0.0, "problem_solving": 0.0, "adaptability": 0.0},
                evidence=["Responses were too brief to evaluate consistently; request additional interview evidence."],
                confidence=0.30, status="INSUFFICIENT_EVIDENCE")
        system_prompt = (
            "Evaluate only the evidence in the submitted behavioral answers using the STAR framework. "
            "Do not infer demographic traits, personality, or similarity to a team. Do not make a hiring decision. "
            "Return JSON keys score (0-100), breakdown (competency scores 0-100), evidence (string list)."
        )
        details = "\n".join(f"{q.get('competency_or_skill')}: {q.get('prompt')}\nAnswer: "
                             f"{answer_map.get(q.get('question_id'), 'NOT ANSWERED')}" for q in questions)
        chain = configured_chain({"llm": LLMStrategy(), "star": STARFrameworkStrategy(),
                                  "human_expert": HumanExpertStrategy()},
                                 ("llm", "star", "human_expert"), "CultureFitAgent", candidate_id)
        result = chain.execute(candidate_id=candidate_id, agent_name="CultureFitAgent", jd_data=jd_data,
            questions=questions, answers=submitted_answers, system_prompt=system_prompt,
            user_prompt=f"Behavioral responses:\n{details}", required_keys=("score", "breakdown"),
            task_reason="Behavioral assessment strategies could not identify sufficient structured evidence.")
        data = result["data"]
        strategy = result["successful_strategy"] or "none"
        task_id = data.get("task_id")
        status = "EXPERT_REVIEW_PENDING" if task_id else data.get("status", "EVALUATION_FAILED")
        evidence = list(data.get("evidence") or [])
        if task_id:
            evidence.append(f"Evaluation task {task_id} is awaiting HR expert review; no score was produced.")
        elif strategy == "none":
            evidence.extend(f"{a['strategy_name']} failed ({a.get('error') or 'unknown error'})." for a in result["attempts"])
        return CultureFitOutput(candidate_id=candidate_id, jd_id=jd_id, score=float(data.get("score", 0)),
            breakdown={k: float(v) for k, v in (data.get("breakdown") or {}).items()}, evidence=evidence,
            confidence=0.86 if strategy == "star" else 0.88 if strategy == "llm" else 0.0,
            status=status, strategy_used=strategy, fallback_chain_depth=result["fallback_chain_depth"],
            fallback_latency_ms=result["total_latency_ms"], attempts_before_success=result["attempts_before_success"])
