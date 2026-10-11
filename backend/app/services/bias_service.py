"""Bias checks attached to every panel decision.

Pool-level checks compare selection rates across cohorts at two points: the AI panel's routing
recommendation and the final human decision. Each uses the small-sample-aware comparison in
fairness_stats. A per-decision check looks for demographic language in the panel rationale.
No check alters scores, routing or decisions; every result is shown to the human reviewer and
stored with the panel decision in the audit log.
"""
import re
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple

from sqlalchemy.orm import Session

from app.database.models import BiasCheck, Candidate, HiringOutcome, HumanReview, PanelDecision
from app.services.fairness_stats import (
    SEVERITY, STATUS_INDICATOR, STATUS_INSUFFICIENT, STATUS_NONE, STATUS_SUPPORTED, compare_groups, is_missing_cohort,
)


def _is_test_record(name: str, email: str, cohort: Optional[str]) -> bool:
    value = f"{name} {email} {cohort or ''}".lower()
    return any(re.search(rf"(?:^|[\W_.-]){marker}(?:$|[\W_.-])", value) for marker in ("test", "demo", "mock", "e2e"))


def _latest_panel_records(db: Session) -> Dict[str, Tuple[Optional[str], PanelDecision]]:
    rows = db.query(Candidate, PanelDecision).join(PanelDecision, PanelDecision.candidate_id == Candidate.candidate_id).all()
    latest: Dict[str, Tuple[Optional[str], PanelDecision]] = {}
    for candidate, decision in rows:
        if _is_test_record(candidate.name or "", candidate.email or "", candidate.cohort_tag):
            continue
        current = latest.get(candidate.candidate_id)
        if current is None or (decision.created_at or datetime.min) > (current[1].created_at or datetime.min):
            latest[candidate.candidate_id] = (candidate.cohort_tag, decision)
    return latest


def ai_recommendation_analysis(db: Session) -> Dict[str, Any]:
    records = [(cohort, decision.recommendation == "PROCEED_TO_HUMAN_REVIEW") for cohort, decision in _latest_panel_records(db).values()]
    return {"stage": "ai_recommendation",
            **compare_groups(records, "the panel recommended Proceed (latest panel run per candidate)")}


def human_decision_analysis(db: Session) -> Dict[str, Any]:
    rows = db.query(Candidate, HumanReview).join(HumanReview, HumanReview.candidate_id == Candidate.candidate_id).filter(
        HumanReview.decision.in_(["APPROVE", "REJECT"])).all()
    latest: Dict[str, Tuple[Optional[str], HumanReview]] = {}
    for candidate, review in rows:
        if review.is_final is False or _is_test_record(candidate.name or "", candidate.email or "", candidate.cohort_tag):
            continue
        current = latest.get(candidate.candidate_id)
        if current is None or (review.timestamp or datetime.min) > (current[1].timestamp or datetime.min):
            latest[candidate.candidate_id] = (candidate.cohort_tag, review)
    records = [(cohort, review.decision == "APPROVE") for cohort, review in latest.values()]
    return {"stage": "human_decision", **compare_groups(records, "the final human decision was Approve (latest final decision per candidate)")}


def calculate_cohort_analytics(db: Session) -> Dict[str, Any]:
    """Pool-level view for the bias monitor page."""
    ai = ai_recommendation_analysis(db)
    human = human_decision_analysis(db)
    checks = db.query(BiasCheck.flag_status).all()
    by_status: Dict[str, int] = {}
    for (status,) in checks:
        by_status[status] = by_status.get(status, 0) + 1
    return {
        "ai_recommendation": ai,
        "human_decision": human,
        "overall_status": max((ai["overall_status"], human["overall_status"]), key=lambda s: SEVERITY[s]),
        "bias_checks_recorded": len(checks),
        "bias_checks_by_status": by_status,
        "method": {
            "impact_ratio": "Cohort selection rate divided by the highest rate among cohorts with enough candidates (four-fifths screen).",
            "significance": "Two-sided Fisher's exact test of each cohort against all other candidates with a recorded cohort.",
            "interval": "Wilson 95% interval for each selection rate.",
            "interpretation": "A potential disparity indicator is a screening signal. Only a ratio below the screen with a significant test "
                              "is reported as statistically supported. A non-significant result does not show that bias is absent.",
        },
    }


def _candidate_group(analysis: Dict[str, Any], cohort: Optional[str]) -> Optional[Dict[str, Any]]:
    if is_missing_cohort(cohort):
        return None
    return next((group for group in analysis["groups"] if group["cohort_name"] == str(cohort).strip()), None)


def check_selection_rate(analysis: Dict[str, Any], cohort: Optional[str], check_type: str, label: str) -> Dict[str, Any]:
    group = _candidate_group(analysis, cohort)
    if group is None:
        status = STATUS_INSUFFICIENT
        reason = (f"{label}: the candidate has no recorded cohort, so their group cannot be compared."
                  if is_missing_cohort(cohort) else f"{label}: no comparable records for cohort {cohort}.")
    else:
        status = group["status"] if group["status"] in SEVERITY and group["status"] != "REFERENCE_GROUP" else STATUS_NONE
        reason = f"{label} — cohort {group['cohort_name']} (n={group['n']}): " + " ".join(group["notes"])
    # The pool-wide status matters too: other cohorts may be disadvantaged even if this candidate's is not.
    if SEVERITY[analysis["overall_status"]] > SEVERITY[status] and analysis["overall_status"] in (STATUS_SUPPORTED, STATUS_INDICATOR):
        reason += f" Pool-wide: {analysis['summary']}"
        status = analysis["overall_status"]
    return {"check_type": check_type, "flag_status": status, "reason": reason, "cohort": cohort,
            "group": group, "pool_status": analysis["overall_status"], "sample_size": group["n"] if group else 0}


def check_outcome_based_fairness(db: Session, candidate: Optional[Candidate]) -> Dict[str, Any]:
    rows = db.query(Candidate, HiringOutcome).join(HiringOutcome, HiringOutcome.candidate_id == Candidate.candidate_id).filter(
        HiringOutcome.performance_rating.isnot(None)).all()
    records = [(c.cohort_tag, float(o.performance_rating) >= 3.5) for c, o in rows
               if not _is_test_record(c.name or "", c.email or "", c.cohort_tag)]
    analysis = compare_groups(records, "manager-reported performance rating of at least 3.5/5")
    result = check_selection_rate(analysis, candidate.cohort_tag if candidate else None, "outcome_based_fairness", "Post-hire outcomes")
    result["success_definition"] = "performance_rating >= 3.5/5"
    return result


def check_threshold_bias(db: Session) -> Dict[str, Any]:
    proceed_scores: Dict[str, List[float]] = {}
    totals: Dict[str, int] = {}
    for cohort, decision in _latest_panel_records(db).values():
        if is_missing_cohort(cohort):
            continue
        totals[cohort] = totals.get(cohort, 0) + 1
        if decision.recommendation == "PROCEED_TO_HUMAN_REVIEW":
            proceed_scores.setdefault(cohort, []).append(float(decision.merged_score))
    floors = {name: {"observed_minimum_proceed_score": round(min(scores), 1), "proceed_count": len(scores),
                     "evaluated_count": totals.get(name, 0)} for name, scores in proceed_scores.items()}
    comparable = [row["observed_minimum_proceed_score"] for row in floors.values() if row["evaluated_count"] >= 10]
    variance = round(max(comparable) - min(comparable), 1) if len(comparable) >= 2 else None
    if variance is None:
        status, reason = STATUS_INSUFFICIENT, "Score floors need at least 10 evaluated candidates in two cohorts to compare."
    elif variance > 10:
        status, reason = STATUS_INDICATOR, ("Observed minimum proceed scores differ by more than 10 points between cohorts. "
                                            "This is a screening signal, not proof that different thresholds were applied.")
    else:
        status, reason = STATUS_NONE, "Observed minimum proceed scores are within 10 points across adequately sized cohorts."
    return {"check_type": "threshold_consistency", "flag_status": status, "reason": reason,
            "thresholds_by_cohort": floors, "variance": variance, "sample_size": sum(totals.values())}


GENDER_CUES = ["she", "he", "her", "his", "him", "hers", "mrs", "mr", "ms", "female", "male", "woman", "man", "girl", "boy"]
OTHER_CUES = ["recent graduate", "overqualified", "too senior", "too old", "too young", "mature", "young", "pregnan",
              "maternity", "religio", "nationality", "native speaker", "accent", "married", "children", "disabilit"]


def check_decision_language(db: Session, decision: Optional[PanelDecision]) -> Dict[str, Any]:
    """Looks for demographic or proxy language in the panel's rationale for this specific decision."""
    if not decision:
        return {"check_type": "decision_rationale_language", "flag_status": STATUS_INSUFFICIENT,
                "reason": "Panel decision record not found.", "sample_size": 0}
    text = " ".join((decision.evidence or []) + (decision.strengths or []) + (decision.gaps or [])
                    + (decision.disagreements or []) + [decision.natural_language_summary or ""]).lower()
    found = [w for w in GENDER_CUES if re.search(rf"\b{w}\b", text)] + [w for w in OTHER_CUES if w in text]
    if found:
        return {"check_type": "decision_rationale_language", "flag_status": STATUS_INDICATOR,
                "reason": f"Panel rationale contains demographic or proxy language: {', '.join(sorted(set(found)))}. "
                          "The reviewer should confirm the recommendation rests on job-related evidence only.",
                "detected_terms": sorted(set(found)), "sample_size": 1}
    return {"check_type": "decision_rationale_language", "flag_status": STATUS_NONE,
            "reason": "No demographic or proxy language was found in the panel rationale.", "detected_terms": [], "sample_size": 1}


def comprehensive_bias_check(db: Session, candidate_id: str, decision_id: str) -> Dict[str, Any]:
    candidate = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    decision = db.query(PanelDecision).filter(PanelDecision.decision_id == decision_id).first()
    cohort = candidate.cohort_tag if candidate else None
    ai = ai_recommendation_analysis(db)
    human = human_decision_analysis(db)
    checks = [
        check_decision_language(db, decision),
        check_selection_rate(ai, cohort, "selection_rate_ai_recommendation", "AI panel recommendations"),
        check_selection_rate(human, cohort, "selection_rate_human_decision", "Final human decisions"),
        check_outcome_based_fairness(db, candidate),
        check_threshold_bias(db),
    ]
    overall = max((c["flag_status"] for c in checks), key=lambda s: SEVERITY.get(s, 0))
    supported = [c for c in checks if c["flag_status"] == STATUS_SUPPORTED]
    indicators = [c for c in checks if c["flag_status"] == STATUS_INDICATOR]
    insufficient = [c for c in checks if c["flag_status"] == STATUS_INSUFFICIENT]
    if supported:
        reason = " ".join(c["reason"] for c in supported)
    elif indicators:
        reason = " ".join(c["reason"] for c in indicators)
    elif insufficient:
        reason = (f"{len(insufficient)} of {len(checks)} checks lack enough data for a reliable comparison; "
                  "this is not evidence that the process is fair. Remaining checks found no indicators.")
    else:
        reason = "No disparity indicators were found. Small samples limit how much this rules out."

    recommendations = []
    if supported:
        recommendations.append("Escalate to HR leadership: review the affected stage, criteria and data quality before further decisions.")
    if indicators:
        recommendations.append("Review the indicator with the evidence before deciding; confirm the decision rests on job-related evidence.")
    if insufficient:
        recommendations.append("Record cohort data consistently and keep monitoring as more decisions accumulate.")
    if not recommendations:
        recommendations.append("Continue routine monitoring; no automated action is taken from these checks.")

    sample = max((c.get("sample_size") or 0 for c in checks), default=0)
    confidence = "low" if sample < 10 else "medium" if sample < 30 else "high"
    return {"candidate_id": candidate_id, "decision_id": decision_id, "flag_status": overall, "reason": reason,
            "checks": checks, "overall_flag": overall in (STATUS_SUPPORTED, STATUS_INDICATOR),
            "recommendations": recommendations, "confidence_level": confidence, "sample_size": sample,
            "action_required": overall != STATUS_NONE, "requires_human_review": True,
            "candidate_cohort": cohort, "pool": {"ai_recommendation": ai, "human_decision": human}}
