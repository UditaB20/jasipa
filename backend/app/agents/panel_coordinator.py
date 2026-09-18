from typing import Dict, Any, List
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput
from app.schemas.panel import PanelDecisionOutput

class PanelCoordinatorAgent:
    """
    Synthesizes independent evaluations from Resume Screener, Skill Assessor, and Culture-Fit agents.
    Calculates rubric-weighted merged score and identifies strengths, gaps, and perspective divergences.
    
    Governance Rule:
    The AI must NEVER autonomously reject or hire. Recommendations route to human review.
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
            screening.status == "INSUFFICIENT_EVIDENCE" or
            technical.status == "INSUFFICIENT_EVIDENCE" or
            behavioral.status == "INSUFFICIENT_EVIDENCE"
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
            disagreements.append("Incomplete data: One or more stages returned INSUFFICIENT_EVIDENCE.")

        # 4. Evidence aggregation
        evidence.extend(screening.evidence[:2])
        evidence.extend(technical.evidence[:2])
        evidence.extend(behavioral.evidence[:2])

        # 5. Recommendation Formulation (Strictly Human Review-Anchored)
        if has_insufficient_evidence:
            recommendation = "ADDITIONAL_INFORMATION_REQUIRED"
        elif merged_score >= 75 and not disagreements:
            recommendation = "PROCEED_TO_HUMAN_REVIEW"
        else:
            recommendation = "HUMAN_REVIEW_REQUIRED"

        return PanelDecisionOutput(
            candidate_id=candidate_id,
            jd_id=jd_id,
            resume_score=r_score,
            skill_score=s_score,
            culture_score=c_score,
            merged_score=merged_score,
            recommendation=recommendation,
            strengths=strengths if strengths else ["Candidate meets baseline prerequisites for review."],
            gaps=gaps if gaps else ["No major qualification deficits identified."],
            disagreements=disagreements if disagreements else ["Agent perspectives are aligned across all evaluation dimensions."],
            evidence=evidence,
            rubric_version=rubric_version
        )
