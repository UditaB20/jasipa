from typing import Dict, Any
from sqlalchemy.orm import Session
from app.schemas.bias import BiasCheckOutput
from app.services.bias_service import comprehensive_bias_check

class BiasCheckerAgent:
    """
    Evaluates historical cohort statistics and candidate outcomes against the 4/5ths (80%) disparate impact standard.
    
    Governance Rule:
    A bias flag NEVER automatically rejects or modifies candidate data. It generates an audit warning
    and explanation for the Human Reviewer.
    """

    @staticmethod
    def check(
        db: Session,
        candidate_id: str,
        decision_id: str
    ) -> BiasCheckOutput:
        result = comprehensive_bias_check(db, candidate_id, decision_id)
        
        return BiasCheckOutput(
            candidate_id=candidate_id,
            decision_id=decision_id,
            flag_status=result["flag_status"],
            reason=result["reason"],
            cohort_breakdown={"checks": result["checks"], "sample_size": result["sample_size"],
                              "confidence_level": result["confidence_level"]},
            requires_human_review=True,
            checks=result["checks"],
            overall_flag=result["overall_flag"],
            recommendations=result["recommendations"],
            confidence_level=result["confidence_level"],
            sample_size=result["sample_size"],
            action_required=result["action_required"]
        )
