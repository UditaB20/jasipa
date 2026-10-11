from sqlalchemy.orm import Session
from app.schemas.bias import BiasCheckOutput
from app.services.bias_service import comprehensive_bias_check


class BiasCheckerAgent:
    """Runs the bias checks against a merged panel decision.

    The result is stored with the panel decision and shown to the human reviewer. It never changes
    scores, routing or the candidate's stage, and is deterministic (no LLM).
    """

    @staticmethod
    def check(db: Session, candidate_id: str, decision_id: str) -> BiasCheckOutput:
        result = comprehensive_bias_check(db, candidate_id, decision_id)
        return BiasCheckOutput(
            candidate_id=candidate_id,
            decision_id=decision_id,
            flag_status=result["flag_status"],
            reason=result["reason"],
            cohort_breakdown={"checks": result["checks"], "sample_size": result["sample_size"],
                              "confidence_level": result["confidence_level"], "candidate_cohort": result["candidate_cohort"],
                              "recommendations": result["recommendations"], "pool": result["pool"],
                              "display_status": result["display_status"], "cohort_definition": result["cohort_definition"]},
            requires_human_review=True,
            checks=result["checks"],
            overall_flag=result["overall_flag"],
            recommendations=result["recommendations"],
            confidence_level=result["confidence_level"],
            sample_size=result["sample_size"],
            action_required=result["action_required"]
        )
