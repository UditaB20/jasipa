from typing import Dict, Any, List
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Candidate, PanelDecision, BiasCheck
from app.config import settings

def calculate_cohort_analytics(db: Session) -> Dict[str, Any]:
    """
    Computes statistical cohort distributions across all candidates who received panel evaluations.
    Applies statistical parity / the 4/5ths (80%) disparate impact standard.
    """
    # Join candidates with their latest panel decisions
    records = db.query(
        Candidate.cohort_tag,
        Candidate.candidate_id,
        PanelDecision.merged_score,
        PanelDecision.recommendation
    ).join(PanelDecision, Candidate.candidate_id == PanelDecision.candidate_id).all()

    if not records:
        return {
            "total_evaluated": 0,
            "cohorts": [],
            "overall_disparity_ratio": 1.0,
            "disparity_detected": False,
            "summary": "Insufficient cohort data for historical statistical parity assessment."
        }

    cohort_data = {}
    for tag, c_id, score, rec in records:
        cohort = tag or "General Cohort"
        if cohort not in cohort_data:
            cohort_data[cohort] = {
                "cohort_name": cohort,
                "scores": [],
                "proceed_count": 0,
                "total": 0
            }
        cohort_data[cohort]["scores"].append(score or 0.0)
        cohort_data[cohort]["total"] += 1
        if rec == "PROCEED_TO_HUMAN_REVIEW":
            cohort_data[cohort]["proceed_count"] += 1

    cohort_metrics = []
    max_proceed_rate = 0.0
    for cohort, data in cohort_data.items():
        total = data["total"]
        avg_score = round(sum(data["scores"]) / total, 1) if total > 0 else 0.0
        proceed_rate = round(data["proceed_count"] / total, 2) if total > 0 else 0.0
        if proceed_rate > max_proceed_rate:
            max_proceed_rate = proceed_rate

        cohort_metrics.append({
            "cohort_name": cohort,
            "total_candidates": total,
            "average_score": avg_score,
            "proceed_rate": proceed_rate,
            "flagged_disparity": False
        })

    # Apply 4/5ths rule (80% ratio of highest selection rate)
    disparity_detected = False
    min_ratio = 1.0
    for c in cohort_metrics:
        if max_proceed_rate > 0:
            ratio = c["proceed_rate"] / max_proceed_rate
            if ratio < settings.BIAS_DISPARITY_THRESHOLD and c["total_candidates"] >= 2:
                c["flagged_disparity"] = True
                disparity_detected = True
            min_ratio = min(min_ratio, ratio)

    summary = (
        "Potential disparity detected: One or more cohort recommendation rates fall below the 80% parity threshold. Human Reviewer flagged."
        if disparity_detected
        else "No significant disparity detected across evaluated cohorts. All selection rates comply with parity thresholds."
    )

    return {
        "total_evaluated": len(records),
        "cohorts": cohort_metrics,
        "overall_disparity_ratio": round(min_ratio, 2),
        "disparity_detected": disparity_detected,
        "summary": summary
    }

def evaluate_bias_for_candidate(
    db: Session, 
    candidate_id: str, 
    decision_id: str
) -> Dict[str, Any]:
    """
    Evaluates historical cohort statistics and tags the individual candidate evaluation with a bias audit record.
    """
    analytics = calculate_cohort_analytics(db)
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    cohort = candidate.cohort_tag if candidate else "General Cohort"

    # Find this candidate's cohort metric
    target_metric = next((c for c in analytics["cohorts"] if c["cohort_name"] == cohort), None)
    
    is_flagged = False
    reason = "All cohort recommendation ratios within normal statistical boundaries."
    
    if target_metric and target_metric["flagged_disparity"]:
        is_flagged = True
        reason = (
            f"Cohort '{cohort}' has an average recommendation rate of {int(target_metric['proceed_rate']*100)}%, "
            f"which is below the 80% parity threshold compared to the leading cohort. "
            f"Highlighted for Human Reviewer scrutiny."
        )
    elif analytics["disparity_detected"]:
        # Overall dataset has a disparity flag
        reason = f"Cohort disparity observed in broader talent pool (Ratio: {analytics['overall_disparity_ratio']}). Human review requested."

    status = "FLAGGED" if is_flagged else "NO_SIGNIFICANT_DISPARITY_DETECTED"

    return {
        "candidate_id": candidate_id,
        "decision_id": decision_id,
        "flag_status": status,
        "reason": reason,
        "cohort_breakdown": analytics,
        "requires_human_review": True
    }
