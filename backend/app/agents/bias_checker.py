from typing import Dict, Any
from sqlalchemy.orm import Session
from app.schemas.bias import BiasCheckOutput
from app.services.bias_service import evaluate_bias_for_candidate

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
        result = evaluate_bias_for_candidate(db, candidate_id, decision_id)
        
        return BiasCheckOutput(
            candidate_id=candidate_id,
            decision_id=decision_id,
            flag_status=result["flag_status"],
            reason=result["reason"],
            cohort_breakdown=result["cohort_breakdown"],
            requires_human_review=True
        )
