from typing import Dict, Any, List
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
    - Deterministic Execution: Pure Python weighted merge algorithm with zero LLM dependency.
      Guarantees exact mathematical repeatability and full auditability without stochastic variance.
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
        behavioral: CultureFitOutput
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
            strengths.append(f"Demonstrated technical mastery ({s_score}/100) across practical assessment questions.")
        if c_score >= 80:
            strengths.append(f"High competency score ({c_score}/100) in structured STAR behavioral assessment.")

        # 2. Gaps synthesis
        if screening.missing_requirements:
            gaps.append(f"Missing JD requirements in resume: {', '.join(screening.missing_requirements)}.")
        if s_score < 70 and technical.status != "INSUFFICIENT_EVIDENCE":
            gaps.append(f"Technical assessment score ({s_score}/100) falls below recommended target threshold (70/100).")
        if c_score < 70 and behavioral.status != "INSUFFICIENT_EVIDENCE":
            gaps.append(f"Behavioral assessment score ({c_score}/100) indicates growth areas in communication/adaptability.")

        # 3. Agent perspective divergence / disagreements
        score_spread = max(r_score, s_score, c_score) - min(r_score, s_score, c_score)
        if (r_score - s_score) >= 25:
            disagreements.append(
                f"High Divergence: Resume score ({r_score}) significantly exceeds demonstrated technical test score ({s_score}). "
                "Suggests resume keyword inflation without hands-on depth."
            )
        elif (s_score - r_score) >= 25:
            disagreements.append(
                f"Hidden Gem Indicator: Technical test score ({s_score}) substantially outperforms resume score ({r_score}). "
                "Candidate has strong hands-on skills despite modest resume pedigree."
            )

        if has_insufficient_evidence:
            disagreements.append("Incomplete data: One or more stages returned insufficient or failed evaluation status.")

        # 4. Evidence aggregation
        evidence.extend(screening.evidence[:2])
        evidence.extend(technical.evidence[:2])
        evidence.extend(behavioral.evidence[:2])

        # 5. Deterministic routing: explanation generation cannot change this result.
        major_divergence = score_spread >= 30
        requires_four_eyes = major_divergence or (technical.confidence is not None and technical.confidence < 0.60)
        if requires_four_eyes:
            disagreements.append(
                f"Four-Eyes Governance Escalation: Inter-agent score divergence of {score_spread} points (>=30) detected. "
                "Dual independent human review sign-offs required prior to final disposition."
            )

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
        if panel_coordinator_config.use_llm_synthesis:
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
            synthesis_error=synthesis_error
        )
