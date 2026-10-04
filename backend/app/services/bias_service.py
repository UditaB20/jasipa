from typing import Dict, Any, List
from datetime import datetime
import re
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.database.models import Candidate, PanelDecision, BiasCheck, HiringOutcome
from app.config import settings

def _is_test_record(name: str, email: str, cohort: str | None) -> bool:
    value = f"{name} {email} {cohort or ''}".lower()
    return any(re.search(rf"(?:^|[\W_.-]){marker}(?:$|[\W_.-])", value)
               for marker in ("test", "demo", "mock", "e2e"))

def calculate_cohort_analytics(db: Session) -> Dict[str, Any]:
    """
    Computes statistical cohort distributions across all candidates who received panel evaluations.
    Applies statistical parity / the 4/5ths (80%) disparate impact standard.
    """
    # Join candidates with their latest panel decisions
    raw_records = db.query(
        Candidate.cohort_tag,
        Candidate.candidate_id,
        Candidate.name,
        Candidate.email,
        PanelDecision.merged_score,
        PanelDecision.recommendation,
        PanelDecision.created_at
    ).join(PanelDecision, Candidate.candidate_id == PanelDecision.candidate_id).all()
    # Compare one current evaluation per candidate so repeated workflow runs do not
    # overweight candidates with more panel records.
    latest = {}
    for tag, candidate_id, name, email, score, recommendation, created_at in raw_records:
        if _is_test_record(name or "", email or "", tag):
            continue
        if candidate_id not in latest or (created_at or datetime.min) > (latest[candidate_id][6] or datetime.min):
            latest[candidate_id] = (tag, candidate_id, name, email, score, recommendation, created_at)
    records = [(row[0], row[1], row[4], row[5]) for row in latest.values()]

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
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    result = comprehensive_bias_check(db, candidate_id, decision_id)
    # Keep the legacy contract for callers while storing the complete audit in the breakdown.
    result["cohort_breakdown"] = {**result, "statistical_analytics": calculate_cohort_analytics(db),
                                  "candidate_cohort": candidate.cohort_tag if candidate else "General Cohort"}
    return result


def _confidence(sample_size: int) -> str:
    if sample_size < 10:
        return "low"
    if sample_size < 30:
        return "medium"
    return "high"


def check_statistical_disparate_impact(db: Session, candidate_id: str, decision_id: str) -> Dict[str, Any]:
    analytics = calculate_cohort_analytics(db)
    candidate = db.query(Candidate).filter_by(candidate_id=candidate_id).first()
    cohort_name = (candidate.cohort_tag if candidate else None) or "General Cohort"
    metric = next((row for row in analytics["cohorts"] if row["cohort_name"] == cohort_name), None)
    reference = max(analytics["cohorts"], key=lambda row: row["proceed_rate"], default=None)
    z_score = None
    impact_ratio = 1.0
    if metric and reference and metric["total_candidates"] and reference["total_candidates"]:
        impact_ratio = metric["proceed_rate"] / reference["proceed_rate"] if reference["proceed_rate"] else (1.0 if metric["proceed_rate"] == 0 else None)
        n1, n2 = metric["total_candidates"], reference["total_candidates"]
        p1, p2 = metric["proceed_rate"], reference["proceed_rate"]
        pooled = (p1 * n1 + p2 * n2) / (n1 + n2)
        se = (pooled * (1 - pooled) * (1 / n1 + 1 / n2)) ** 0.5
        z_score = round((p1 - p2) / se, 3) if se else (0.0 if p1 == p2 else None)
    flagged = bool(metric and metric["flagged_disparity"])
    sample = metric["total_candidates"] if metric else 0
    if sample < 10:
        status = "INSUFFICIENT_DATA"
        reason = f"Only {sample} evaluated records are available for cohort {cohort_name}; comparison is low confidence."
    else:
        status = "WARNING" if flagged else "CLEARED"
        reason = (f"Observed recommendation-rate ratio is {impact_ratio:.2f}, below the configured 4/5ths screen." if flagged and impact_ratio is not None
                  else "No disparate-impact ratio below the configured 4/5ths screen was observed." if not flagged
                  else "Reference selection rate is zero; an impact ratio cannot be computed.")
    return {"check_type": "statistical_disparate_impact", "flag_status": status, "reason": reason,
            "z_score": z_score, "impact_ratio": impact_ratio, "sample_size": sample,
            "cohort_breakdown": analytics}


def check_outcome_based_fairness(db: Session, candidate_id: str) -> Dict[str, Any]:
    candidate = db.query(Candidate).filter_by(candidate_id=candidate_id).first()
    target = (candidate.cohort_tag if candidate else None) or "General Cohort"
    records = db.query(Candidate.cohort_tag, Candidate.name, Candidate.email,
                       HiringOutcome.performance_rating).join(
        HiringOutcome, HiringOutcome.candidate_id == Candidate.candidate_id
    ).filter(HiringOutcome.performance_rating.isnot(None)).all()
    groups: Dict[str, List[float]] = {}
    for cohort, name, email, rating in records:
        if _is_test_record(name or "", email or "", cohort):
            continue
        name = cohort or "General Cohort"
        groups.setdefault(name, []).append(float(rating))
    reference_name = max(groups, key=lambda name: len(groups[name]), default=None)
    cohort_ratings = groups.get(target, [])
    reference_ratings = groups.get(reference_name, []) if reference_name else []
    cohort_success = sum(rating >= 3.5 for rating in cohort_ratings) / len(cohort_ratings) if cohort_ratings else None
    reference_success = sum(rating >= 3.5 for rating in reference_ratings) / len(reference_ratings) if reference_ratings else None
    impact = cohort_success / reference_success if cohort_success is not None and reference_success not in (None, 0) else None
    sample = len(cohort_ratings)
    if sample < 10 or len(reference_ratings) < 10 or reference_success in (None, 0):
        status = "INSUFFICIENT_DATA"
        reason = f"Outcome comparison needs at least 10 rated hires in both cohorts; target n={sample}, reference n={len(reference_ratings)}."
    elif impact is not None and impact < settings.BIAS_DISPARITY_THRESHOLD:
        status = "WARNING"
        reason = f"Recorded success rate for cohort {target} is {impact:.0%} of reference cohort {reference_name}, below the 4/5ths screen."
    else:
        status = "CLEARED"
        reason = f"Recorded outcome success rate is not below the 4/5ths screen relative to {reference_name}."
    return {"check_type": "outcome_based_fairness", "flag_status": status, "reason": reason,
            "impact_ratio": round(impact, 3) if impact is not None else None,
            "cohort_success": round(cohort_success, 3) if cohort_success is not None else None,
            "ref_success": round(reference_success, 3) if reference_success is not None else None,
            "cohort": target, "reference_cohort": reference_name, "sample_size": sample,
            "reference_sample_size": len(reference_ratings), "success_definition": "performance_rating >= 3.5/5"}


def check_threshold_bias(db: Session) -> Dict[str, Any]:
    records = db.query(Candidate.cohort_tag, Candidate.candidate_id, Candidate.name, Candidate.email,
                       PanelDecision.merged_score, PanelDecision.recommendation, PanelDecision.created_at).join(
        PanelDecision, PanelDecision.candidate_id == Candidate.candidate_id
    ).all()
    latest = {}
    for row in records:
        cohort, candidate_id, name, email, score, recommendation, created_at = row
        if _is_test_record(name or "", email or "", cohort):
            continue
        if candidate_id not in latest or (created_at or datetime.min) > (latest[candidate_id][6] or datetime.min):
            latest[candidate_id] = row
    total_by_cohort: Dict[str, int] = {}
    proceed_scores: Dict[str, List[float]] = {}
    for cohort, _, _, _, score, recommendation, _ in latest.values():
        name = cohort or "General Cohort"
        total_by_cohort[name] = total_by_cohort.get(name, 0) + 1
        if recommendation == "PROCEED_TO_HUMAN_REVIEW":
            proceed_scores.setdefault(name, []).append(float(score))
    thresholds = {name: {"observed_minimum_proceed_score": round(min(scores), 1),
                         "proceed_count": len(scores), "evaluated_count": total_by_cohort.get(name, 0)}
                  for name, scores in proceed_scores.items() if scores}
    comparable = [row["observed_minimum_proceed_score"] for row in thresholds.values() if row["evaluated_count"] >= 10]
    variance = round(max(comparable) - min(comparable), 1) if len(comparable) >= 2 else None
    if len(comparable) < 2:
        status = "INSUFFICIENT_DATA"
        reason = "Need at least 10 evaluated candidates in two cohorts with proceed recommendations to compare observed score floors."
    elif variance is not None and variance > 10:
        status = "WARNING"
        reason = "Observed minimum proceed scores differ by more than 10 points; this is a screening signal, not proof of different thresholds."
    else:
        status = "CLEARED"
        reason = "Observed minimum proceed scores are within 10 points across adequately sized cohorts."
    return {"check_type": "threshold_bias", "flag_status": status, "reason": reason,
            "thresholds_by_cohort": thresholds, "variance": variance,
            "sample_size": sum(total_by_cohort.values())}


def comprehensive_bias_check(db: Session, candidate_id: str, decision_id: str) -> Dict[str, Any]:
    checks = [check_statistical_disparate_impact(db, candidate_id, decision_id),
              check_outcome_based_fairness(db, candidate_id), check_threshold_bias(db)]
    overall_flag = any(check["flag_status"] == "WARNING" for check in checks)
    incomplete = any(check["flag_status"] == "INSUFFICIENT_DATA" for check in checks)
    sample_size = max((check["sample_size"] for check in checks), default=0)
    confidence = "low" if incomplete else _confidence(sample_size)
    recommendations = []
    if overall_flag:
        recommendations.append("Review the flagged cohort comparison with HR and validate data quality before changing evaluation criteria.")
    if incomplete:
        recommendations.append("Collect more comparable outcomes and evaluation records; insufficient data is not evidence of fairness.")
    if not recommendations:
        recommendations.append("Continue monitoring cohort-level outcomes; no automated hiring action is taken from these checks.")
    flags = [check for check in checks if check["flag_status"] == "WARNING"]
    reason = "; ".join(check["reason"] for check in flags) if flags else (
        "One or more comparisons have insufficient data." if incomplete else "No disparity threshold was crossed in the available aggregate comparisons.")
    legacy_status = "FLAGGED" if overall_flag else "NO_SIGNIFICANT_DISPARITY_DETECTED"
    return {"candidate_id": candidate_id, "decision_id": decision_id, "flag_status": legacy_status,
            "reason": reason, "checks": checks, "overall_flag": overall_flag,
            "recommendations": recommendations, "confidence_level": confidence,
            "sample_size": sample_size, "action_required": overall_flag or incomplete,
            "requires_human_review": True}
