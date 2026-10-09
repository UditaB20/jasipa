from typing import Dict, Any
from sqlalchemy.orm import Session
from app.schemas.bias import BiasCheckOutput
from app.services.bias_service import comprehensive_bias_check

class BiasCheckerAgent:
    """
    Evaluates historical cohort statistics and candidate outcomes against the 4/5ths (80%) disparate impact standard.
    
    ARCHITECTURE:
    - Bias Flag Impact: A bias flag is recorded for transparency and auditing, but NEVER modifies
      the candidate recommendation, scores, or decisions. All candidates route to human review.
    - Tool Use: This agent does NOT call MCP tools directly. It returns BiasCheckOutput.
      The LangGraph bias_node calls ATSTools.save_bias_check() after evaluation completes.
    - Deterministic Evaluation: Runs statistical 4/5ths cohort ratio calculations without LLM dependency.
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
