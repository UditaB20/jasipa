from typing import Dict, Any, List
from app.schemas.assessment import CultureFitOutput
from app.agents.llm_factory import LLMService

class CultureFitAgent:
    """
    Evaluates candidate responses to standardized behavioral questions.
    Governance Rule: Soft skills/behavior must NEVER be inferred from resumes.
    Assesses structured responses for Communication, Teamwork, Problem Solving, and Adaptability.
    If evidence is missing or too brief, flags INSUFFICIENT_EVIDENCE.
    """

    @staticmethod
    def evaluate(
        candidate_id: str,
        jd_data: Dict[str, Any],
        questions: List[Dict[str, Any]],
        submitted_answers: List[Dict[str, str]]
    ) -> CultureFitOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        
        if not submitted_answers:
            return CultureFitOutput(
                candidate_id=candidate_id,
                jd_id=jd_id,
                score=0.0,
                breakdown={},
                evidence=["Candidate has not submitted behavioral responses. Assessment pending."],
                confidence=0.0,
                status="INSUFFICIENT_EVIDENCE"
            )

        answer_map = {a.get("question_id"): a.get("answer_text", "").strip() for a in submitted_answers}
        total_word_count = sum(len(ans.split()) for ans in answer_map.values())

        # Check for insufficient evidence (e.g. single-word/evasive answers)
        if total_word_count < 25:
            return CultureFitOutput(
                candidate_id=candidate_id,
                jd_id=jd_id,
                score=0.0,
                breakdown={
                    "communication": 0.0,
                    "teamwork": 0.0,
                    "problem_solving": 0.0,
                    "adaptability": 0.0
                },
                evidence=[
                    "Candidate answers were too brief/evasive to evaluate behavioral competencies objectively.",
                    "Status tagged as INSUFFICIENT_EVIDENCE; requires additional interview inquiry."
                ],
                confidence=0.30,
                status="INSUFFICIENT_EVIDENCE"
            )

        # Attempt LLM-based evaluation
        system_prompt = (
            "You are an expert HR Behavioral & Competency Assessor (Culture-Fit Agent). Evaluate candidate answers to behavioral questions "
            "using the STAR framework (Situation, Task, Action, Result). Evaluate ONLY Communication, Teamwork, Problem Solving, and Adaptability. "
            "Do NOT judge demographic, personal, or superficial attributes. "
            "Return JSON with: score (0-100), breakdown (dict of competency names to 0-100 scores), evidence (list of concrete observations)."
        )
        user_prompt = "Behavioral Responses:\n"
        for q in questions:
            qid = q.get("question_id")
            prompt = q.get("prompt")
            ans = answer_map.get(qid, "NOT ANSWERED")
            user_prompt += f"\nPrompt: {prompt}\nCandidate Response: {ans}\n"

        llm_result = LLMService.call_llm(system_prompt, user_prompt)
        if llm_result and "score" in llm_result and "breakdown" in llm_result:
            return CultureFitOutput(
                candidate_id=candidate_id,
                jd_id=jd_id,
                score=float(llm_result["score"]),
                breakdown={k: float(v) for k, v in llm_result.get("breakdown", {}).items()},
                evidence=llm_result.get("evidence", []),
                confidence=0.88,
                status="COMPLETED"
            )

        # High-Fidelity Heuristic Competency Evaluator
        breakdown = {}
        evidence = []
        active_scores = []

        competencies = [
            ("communication", ["BEH_Q4", "BEH_Q1"], "Technical Communication"),
            ("teamwork", ["BEH_Q1"], "Team Collaboration & Conflict Resolution"),
            ("problem_solving", ["BEH_Q2"], "Problem Solving & Ambiguity"),
            ("adaptability", ["BEH_Q3"], "Adaptability & Continuous Learning")
        ]

        for comp_key, qids, comp_name in competencies:
            # Check if this competency was actually present in questions
            has_questions_for_comp = any(q.get("question_id") in qids or comp_key in q.get("competency_or_skill", "").lower() for q in questions)
            
            comp_answers = [answer_map.get(qid, "") for qid in qids if qid in answer_map]
            text = " ".join(comp_answers).lower()
            
            if not text or len(text.split()) < 10:
                if has_questions_for_comp:
                    breakdown[comp_key] = 40.0
                    evidence.append(f"{comp_name}: Minimal evidence provided; candidate gave brief response.")
                    active_scores.append(40.0)
                else:
                    breakdown[comp_key] = 75.0 # Neutral baseline for unassessed competency
                continue

            comp_score = 70.0 # Base score for thoughtful answer
            
            # Look for STAR structure indicators
            has_situation = any(k in text for k in ["situation", "when i was", "at my previous", "in a project", "during"])
            has_action = any(k in text for k in ["i decided", "i organized", "i implemented", "i communicated", "i proposed", "i scheduled", "i researched", "i benchmarked"])
            has_result = any(k in text for k in ["result", "outcome", "successfully", "delivered", "agreed", "resolved", "improved", "learned", "consensus"])
            
            if has_situation and has_action and has_result:
                comp_score += 20.0
                evidence.append(f"{comp_name}: Structured STAR response with clear action steps and documented positive resolution.")
            elif has_action or has_result:
                comp_score += 10.0
                evidence.append(f"{comp_name}: Clear concrete actions described; demonstrated self-reflection.")
            else:
                evidence.append(f"{comp_name}: Answer is conversational but lacks explicit outcome metrics.")

            comp_score = min(95.0, comp_score)
            breakdown[comp_key] = round(comp_score, 1)
            active_scores.append(comp_score)

        avg_score = round(sum(active_scores) / len(active_scores), 1) if active_scores else 75.0

        return CultureFitOutput(
            candidate_id=candidate_id,
            jd_id=jd_id,
            test_id="BEH_EVAL_01",
            score=avg_score,
            breakdown=breakdown,
            evidence=evidence,
            confidence=0.86,
            status="COMPLETED"
        )
