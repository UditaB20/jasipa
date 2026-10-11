from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.auth.security import require_hr
from app.database.models import BiasCheck, Candidate, JobDescription, PanelDecision
from app.database.session import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])

PIPELINE_GROUPS = [
    ("Applied", ("REGISTERED", "APPLIED", "MANUAL_REVIEW_REQUIRED")),
    ("Screened", ("RESUME_SCREENED",)),
    ("Assessed", ("TECHNICAL_ASSESSED", "BEHAVIORAL_ASSESSED")),
    ("Awaiting decision", ("PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING")),
    ("More info requested", ("INFO_REQUESTED",)),
    ("Decided", ("DECIDED",)),
]
AWAITING = ("PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING")
ATTENTION = ("STATISTICALLY_SUPPORTED_DISPARITY", "POTENTIAL_DISPARITY_INDICATOR")


@router.get("/summary")
def dashboard_summary(current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    candidates = db.query(Candidate).all()
    jobs = {j.jd_id: j.title for j in db.query(JobDescription).all()}
    counts = {label: sum(1 for c in candidates if c.current_stage in stages) for label, stages in PIPELINE_GROUPS}

    awaiting = []
    for cand in sorted((c for c in candidates if c.current_stage in AWAITING), key=lambda c: c.updated_at or c.created_at):
        panel = (db.query(PanelDecision).filter(PanelDecision.candidate_id == cand.candidate_id)
                 .order_by(PanelDecision.created_at.desc()).first())
        bias = (db.query(BiasCheck).filter(BiasCheck.decision_id == panel.decision_id)
                .order_by(BiasCheck.created_at.desc()).first()) if panel else None
        awaiting.append({"candidate_id": cand.candidate_id, "name": cand.name, "job_title": jobs.get(cand.target_jd_id),
                         "merged_score": panel.merged_score if panel else None,
                         "recommendation": panel.recommendation if panel else None,
                         "requires_two_reviewers": bool(panel and panel.requires_four_eyes_review),
                         "bias_flag_status": bias.flag_status if bias else None,
                         "waiting_since": (panel.created_at if panel else cand.updated_at).isoformat() if (panel or cand.updated_at) else None})

    latest_bias = {}
    for check in db.query(BiasCheck).order_by(BiasCheck.created_at.asc()).all():
        latest_bias[check.candidate_id] = check.flag_status
    return {
        "total_candidates": len(candidates),
        "open_jobs": len(jobs),
        "awaiting_decision": len(awaiting),
        "bias_attention": sum(1 for status in latest_bias.values() if status in ATTENTION),
        "pipeline": [{"label": label, "count": counts[label]} for label, _ in PIPELINE_GROUPS],
        "awaiting_list": awaiting[:10],
    }
