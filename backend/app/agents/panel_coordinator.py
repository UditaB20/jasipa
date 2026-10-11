from typing import Dict, Any, List, Optional
from app.agents.base_agent import LLMStrategy, StrategyChain, TemplateSynthesisStrategy
from app.config import panel_coordinator_config
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput
from app.schemas.panel import PanelDecisionOutput

class PanelCoordinatorAgent:
    """
    Synthesizes independent evaluations from Resume Screener, Skill Assessor, and Culture-Fit agents.
    Calculates rubric-weighted merged score and identifies strengths, gaps, and perspective divergences.
    
    ARCHITECTURE:
    - Deterministic routing: scores are merged with the rubric weights in plain Python. An optional LLM
      may only rephrase the already-computed facts into a summary; it cannot change scores or routing.
    - Tool Use: This agent does NOT call MCP tools directly. It returns PanelDecisionOutput.
      The LangGraph panel_node calls ATSTools.save_panel_decision() after synthesis completes.
    - Governance Rule:
      The AI must NEVER autonomously reject or hire. All recommendations route to human review.
    """

    @staticmethod
    def synthesize(
        candidate_id: str,
        jd_data: Dict[str, Any],
        rubric_data: Dict[str, Any],
        screening: ResumeScreeningOutput,
        technical: SkillAssessorOutput,
        behavioral: CultureFitOutput,
        history: Optional[List[Dict[str, Any]]] = None
    ) -> PanelDecisionOutput:
        jd_id = jd_data.get("jd_id", "JD001")
        rubric_version = rubric_data.get("version", "1.0")
        
        resume_wt = rubric_data.get("resume_weight", 0.40)
        skill_wt = rubric_data.get("skill_weight", 0.40)
        culture_wt = rubric_data.get("culture_weight", 0.20)

        r_score = screening.score
        s_score = technical.score
        c_score = behavioral.score

        # Check for insufficient evidence states
        has_insufficient_evidence = (
            screening.status != "COMPLETED" or
            technical.status != "COMPLETED" or
            behavioral.status != "COMPLETED"
        )

        merged_score = round((r_score * resume_wt) + (s_score * skill_wt) + (c_score * culture_wt), 1)

        strengths = []
        gaps = []
        disagreements = []
        evidence = []

        # 1. Strengths synthesis
        if r_score >= 80:
            strengths.append(f"Strong resume alignment ({r_score}/100) matching core JD requirements: {', '.join(screening.matched_requirements[:3])}.")
        if s_score >= 80:
            strengths.append(f"Strong demonstrated technical performance ({s_score}/100) on the practical assessment.")
        if c_score >= 80:
            strengths.append(f"Strong structured (STAR) behavioral evidence ({c_score}/100).")

        # 2. Gaps synthesis
        if screening.missing_requirements:
            gaps.append(f"Missing JD requirements in resume: {', '.join(screening.missing_requirements)}.")
        if s_score < 70 and technical.status == "COMPLETED":
            gaps.append(f"Technical assessment score ({s_score}/100) falls below recommended target threshold (70/100).")
        if c_score < 70 and behavioral.status == "COMPLETED":
            gaps.append(f"Behavioral assessment score ({c_score}/100) is below the 70/100 target; see competency evidence.")

        # 3. Agent perspective divergence / disagreements
        score_spread = max(r_score, s_score, c_score) - min(r_score, s_score, c_score)
        if technical.status == "COMPLETED" and screening.status == "COMPLETED":
            if (r_score - s_score) >= 25:
                disagreements.append(f"Resume score ({r_score}) exceeds the demonstrated technical score ({s_score}) by "
                                     f"{r_score - s_score:.0f} points; verify hands-on depth in interview.")
            elif (s_score - r_score) >= 25:
                disagreements.append(f"Technical score ({s_score}) exceeds the resume score ({r_score}) by "
                                     f"{s_score - r_score:.0f} points; the resume may understate the candidate's skills.")

        if has_insufficient_evidence:
            incomplete = [name for name, status in (("resume screening", screening.status), ("technical assessment", technical.status),
                                                    ("behavioral assessment", behavioral.status)) if status != "COMPLETED"]
            disagreements.append(f"Incomplete evidence: {', '.join(incomplete)} not completed; those stages count as 0 in the merged score.")

        # Candidate memory: compare with the previous assessment round, if any.
        if history:
            previous = history[-1]
            disagreements.append(
                f"Previous round {previous.get('round_number', len(history))}: merged score {previous.get('merged_score')} "
                f"({previous.get('recommendation')}); human outcome: {previous.get('human_decision') or 'none recorded'}.")

        # 4. Evidence aggregation
        evidence.extend(screening.evidence[:2])
        evidence.extend(technical.evidence[:2])
        evidence.extend(behavioral.evidence[:2])

        # 5. Deterministic routing: explanation generation cannot change this result.
        # Divergence is only meaningful when every stage produced a real score.
        major_divergence = score_spread >= 30 and not has_insufficient_evidence
        low_confidence = technical.status == "COMPLETED" and technical.confidence is not None and technical.confidence < 0.60
        requires_four_eyes = major_divergence or low_confidence
        if requires_four_eyes:
            cause = (f"agent scores diverge by {score_spread:.0f} points (threshold 30)" if major_divergence
                     else f"technical evaluation confidence is low ({technical.confidence:.2f})")
            disagreements.append(f"Two-reviewer sign-off required: {cause}. A final decision needs two different HR reviewers who agree.")

        if has_insufficient_evidence:
            recommendation = "ADDITIONAL_INFORMATION_REQUIRED"
        elif merged_score < 50:
            recommendation = "HUMAN_REVIEW_REQUIRED"
        elif major_divergence:
            recommendation = "HUMAN_REVIEW_REQUIRED"
        elif merged_score >= 75:
            recommendation = "PROCEED_TO_HUMAN_REVIEW"
        else:
            recommendation = "HUMAN_REVIEW_REQUIRED"

        final_strengths = strengths if strengths else ["No score dimension reached the strength threshold."]
        final_gaps = gaps if gaps else ["No score dimension fell below the gap threshold."]
        final_disagreements = disagreements if disagreements else ["Agent scores were aligned across evaluation dimensions."]

        # Optional LLM prose is restricted to the structured facts above; only deterministic code routes.
        strategy_map = {"template": TemplateSynthesisStrategy()}
        from app.agents.llm_factory import llm_available
        if panel_coordinator_config.use_llm_synthesis and llm_available():
            strategy_map["llm"] = LLMStrategy()
            order = ("llm", "template")
        else:
            order = ("template",)
        chain = StrategyChain([(name, strategy_map[name]) for name in order],
            timeout_seconds=panel_coordinator_config.synthesis_timeout_seconds, agent_name="PanelCoordinatorAgent",
            candidate_id=candidate_id)
        prompt = (f"Scores resume={r_score}/100, technical={s_score}/100, behavioral={c_score}/100, merged={merged_score}/100. "
                  f"Strengths={final_strengths}. Gaps={final_gaps}. Divergences={final_disagreements}. "
                  f"Routing label={recommendation}. Detail level={panel_coordinator_config.explanation_detail_level}. "
                  "Write a concise factual summary for an HR reviewer based only on these supplied facts. "
                  "Do not infer personal traits, add unsupported claims, or alter the routing label.")
        synthesis = chain.execute(
            candidate_id=candidate_id,
            system_prompt=("You write evidence-grounded evaluation summaries for human review. Never hire or reject candidates. "
                           "Return JSON with summary (string), decision_factors (string list), highlighted_concerns (string list), "
                           "and highlighted_strengths (string list)."),
            user_prompt=prompt, required_keys=("summary",), model_name=panel_coordinator_config.llm_synthesis_model,
            # Structured facts consumed by TemplateSynthesisStrategy (previously omitted -> summaries showed 0/100).
            merged_score=merged_score, resume_score=r_score, skill_score=s_score, culture_score=c_score,
            strengths=strengths, gaps=gaps, disagreements=disagreements, recommendation=recommendation)
        synthesis_data = synthesis["data"]
        synthesis_error = next((a["error"] for a in synthesis["attempts"] if not a["success"]), None)

        return PanelDecisionOutput(
            candidate_id=candidate_id,
            jd_id=jd_id,
            resume_score=r_score,
            skill_score=s_score,
            culture_score=c_score,
            merged_score=merged_score,
            recommendation=recommendation,
            strengths=final_strengths,
            gaps=final_gaps,
            disagreements=final_disagreements,
            evidence=evidence,
            rubric_version=rubric_version,
            natural_language_summary=synthesis_data.get("summary"),
            decision_factors=synthesis_data.get("decision_factors", []),
            highlighted_concerns=synthesis_data.get("highlighted_concerns", final_gaps),
            highlighted_strengths=synthesis_data.get("highlighted_strengths", final_strengths),
            requires_four_eyes_review=requires_four_eyes,
            used_llm_synthesis=synthesis["successful_strategy"] == "llm",
            synthesis_latency_ms=synthesis["total_latency_ms"],
            synthesis_strategy=synthesis["successful_strategy"] or "none",
            synthesis_error=synthesis_error,
            round_number=len(history or []) + 1
        )
