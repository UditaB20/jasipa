from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timezone
import re
from app.database.session import get_db
from app.database.models import Candidate, HiringOutcome, HumanReview, PanelDecision, JobDescription
from app.schemas.outcome import HiringOutcomeCreate, HiringOutcomeResponse
from app.auth.security import require_hr
from app.services.outcome_service import OutcomeRecordingService

router = APIRouter(prefix="/learning", tags=["Hiring Outcomes & Learning Analytics"])
TEST_MARKERS = ("test", "demo", "mock", "e2e")


def is_test_candidate(candidate: Candidate) -> bool:
    text = f"{candidate.name} {candidate.email} {candidate.cohort_tag or ''}".lower()
    return any(re.search(rf"(?:^|[\W_.-]){marker}(?:$|[\W_.-])", text) for marker in TEST_MARKERS)


@router.post("/outcomes", response_model=HiringOutcomeResponse)
@router.post("/outcomes/record", response_model=HiringOutcomeResponse, include_in_schema=False)
def record_hiring_outcome(payload: HiringOutcomeCreate, user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    candidate = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    if not candidate:
        raise HTTPException(status_code=404, detail="Candidate not found")
    if is_test_candidate(candidate):
        raise HTTPException(status_code=400, detail="Test/demo candidates are excluded from hiring outcome tracking")
    try:
        return OutcomeRecordingService(db).record_outcome(payload, user)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except PermissionError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@router.get("/outcomes", response_model=list[HiringOutcomeResponse])
def list_hiring_outcomes(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    return [outcome for outcome, candidate in db.query(HiringOutcome, Candidate).join(Candidate).order_by(HiringOutcome.updated_at.desc()).all() if not is_test_candidate(candidate)]


@router.get("/eligible")
def eligible_for_outcome(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    approved_ids = db.query(HumanReview.candidate_id).filter(HumanReview.decision == "APPROVE").distinct().all()
    ids = [row[0] for row in approved_ids]
    if not ids:
        return []
    outcomes = {row.candidate_id: row for row in db.query(HiringOutcome).filter(HiringOutcome.candidate_id.in_(ids)).all()}
    result = []
    for c in db.query(Candidate).filter(Candidate.candidate_id.in_(ids)).order_by(Candidate.name).all():
        if is_test_candidate(c):
            continue
        outcome = outcomes.get(c.candidate_id)
        result.append({"candidate_id": c.candidate_id, "name": c.name, "target_jd_id": c.target_jd_id,
             "role": c.job_description.title if c.job_description else None, "has_outcome": outcome is not None,
             "outcome": ({"hired_date": outcome.hired_date.date().isoformat(), "performance_rating": outcome.performance_rating,
                          "still_employed": outcome.still_employed, "months_employed": outcome.months_employed,
                          "manager_name": outcome.manager_name, "promotion_date": outcome.promotion_date.date().isoformat() if outcome.promotion_date else "",
                          "attrition_reason": outcome.attrition_reason, "manager_feedback": outcome.manager_feedback} if outcome else None)})
    return result


@router.get("/analytics")
def hiring_analytics(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    rows = [(outcome, candidate.target_jd_id) for outcome, candidate in db.query(HiringOutcome, Candidate).join(Candidate).all() if not is_test_candidate(candidate)]
    rated = [o for o, _ in rows if o.performance_rating is not None]
    known_retention = [o for o, _ in rows if o.still_employed is not None]
    roles = {}
    for outcome, jd_id in rows:
        key = jd_id or "UNASSIGNED"
        bucket = roles.setdefault(key, {"outcomes": 0, "rated": [], "retained": []})
        bucket["outcomes"] += 1
        if outcome.performance_rating is not None:
            bucket["rated"].append(outcome.performance_rating)
        if outcome.still_employed is not None:
            bucket["retained"].append(outcome.still_employed)
    role_summary = {
        key: {"outcomes": b["outcomes"], "average_performance": round(sum(b["rated"]) / len(b["rated"]), 2) if b["rated"] else None,
              "retention_rate": round(sum(b["retained"]) / len(b["retained"]), 3) if b["retained"] else None}
        for key, b in roles.items()
    }
    performance_bands = {
        "Excellent (4.5–5.0)": sum(1 for o in rated if o.performance_rating >= 4.5),
        "Good (3.5–4.4)": sum(1 for o in rated if 3.5 <= o.performance_rating < 4.5),
        "Developing (2.5–3.4)": sum(1 for o in rated if 2.5 <= o.performance_rating < 3.5),
        "Needs support (1.0–2.4)": sum(1 for o in rated if o.performance_rating < 2.5),
    }
    last_updated = max((o.updated_at for o, _ in rows if o.updated_at), default=None)
    return {
        "outcomes_recorded": len(rows),
        "rated_outcomes": len(rated),
        "average_performance": round(sum(o.performance_rating for o in rated) / len(rated), 2) if rated else None,
        "performance_scale": "1–5",
        "performance_bands": performance_bands,
        "retention_observations": len(known_retention),
        "still_employed_count": sum(1 for o in known_retention if o.still_employed),
        "retention_rate": round(sum(o.still_employed for o in known_retention) / len(known_retention), 3) if known_retention else None,
        "last_updated": last_updated.isoformat() if last_updated else None,
        "small_sample": len(known_retention) < 15 or len(rated) < 15,
        "minimum_sample_for_trend": 15,
        "by_role_id": role_summary,
        "learning_status": "DESCRIPTIVE_ONLY",
        "notice": "Early descriptive signals only. At least 15 records are recommended before interpreting trends; no model weights or thresholds are changed automatically."
    }


@router.get("/history")
def outcome_history(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    rows = db.query(HiringOutcome, Candidate, JobDescription).join(Candidate).outerjoin(
        JobDescription, Candidate.target_jd_id == JobDescription.jd_id
    ).order_by(HiringOutcome.updated_at.desc()).all()
    results = []
    for outcome, candidate, job in rows:
        if is_test_candidate(candidate):
            continue
        panel = db.query(PanelDecision).filter_by(candidate_id=candidate.candidate_id).order_by(PanelDecision.created_at.desc()).first()
        results.append({
            "outcome_id": outcome.outcome_id, "candidate_id": candidate.candidate_id,
            "candidate_name": candidate.name, "role": job.title if job else "Unassigned role",
            "hired_date": outcome.hired_date.isoformat(), "performance_rating": outcome.performance_rating,
            "still_employed": outcome.still_employed, "months_employed": outcome.months_employed,
            "manager_name": outcome.manager_name, "promotion_date": outcome.promotion_date.isoformat() if outcome.promotion_date else None,
            "manager_feedback": outcome.manager_feedback, "updated_at": outcome.updated_at.isoformat() if outcome.updated_at else None,
            "evaluation": ({"resume_score": panel.resume_score, "technical_score": panel.skill_score,
                            "behavioral_score": panel.culture_score, "merged_score": panel.merged_score,
                            "recommendation": panel.recommendation} if panel else None)
        })
    return results


def historical_context(db: Session, candidate: Candidate, panel: PanelDecision | None):
    """Return same-role, nearby-score evidence without presenting sparse data as a prediction."""
    if not panel:
        return {"similar_hires": 0, "confidence": None, "confidence_label": "UNAVAILABLE", "note": "Panel scores are not available."}
    # Match same job and each dimension within five points; never use cohort/demographic data.
    query = db.query(PanelDecision, HiringOutcome).join(
        HiringOutcome, HiringOutcome.candidate_id == PanelDecision.candidate_id
    ).join(Candidate, Candidate.candidate_id == PanelDecision.candidate_id).filter(
        Candidate.target_jd_id == candidate.target_jd_id,
        PanelDecision.candidate_id != candidate.candidate_id,
        func.abs(PanelDecision.resume_score - panel.resume_score) <= 5,
        func.abs(PanelDecision.skill_score - panel.skill_score) <= 5,
        func.abs(PanelDecision.culture_score - panel.culture_score) <= 5,
    ).all()
    latest = {}
    for prior_panel, outcome in query:
        prior_candidate = db.query(Candidate).filter_by(candidate_id=prior_panel.candidate_id).first()
        if not prior_candidate or is_test_candidate(prior_candidate):
            continue
        if prior_panel.candidate_id not in latest or prior_panel.created_at > latest[prior_panel.candidate_id][0].created_at:
            latest[prior_panel.candidate_id] = (prior_panel, outcome)
    known = [outcome for _, outcome in latest.values() if outcome.still_employed is not None or outcome.performance_rating is not None]
    successful = [o for o in known if o.still_employed is True and (o.performance_rating is None or o.performance_rating >= 3.5)]
    return {
        "similar_hires": len(known),
        "successful_outcomes": len(successful) if len(known) >= 5 else None,
        "success_rate": round(len(successful) / len(known), 3) if len(known) >= 5 else None,
        "confidence": round(len(successful) / len(known), 3) if len(known) >= 5 else None,
        "confidence_label": "HISTORICAL_SIGNAL" if len(known) >= 5 else "INSUFFICIENT_HISTORY",
        "note": "Historical context is descriptive and is not an automated hiring recommendation."
    }
