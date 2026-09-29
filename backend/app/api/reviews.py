from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.models import Candidate, HumanReview, PanelDecision, BiasCheck
from app.schemas.review import HumanReviewCreate, HumanReviewResponse
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.auth.security import get_current_user, require_hr

router = APIRouter(prefix="/reviews", tags=["Human Review & Final Decisions"])

def model_to_dict(model_instance):
    if not model_instance:
        return None
    d = {}
    for column in model_instance.__table__.columns:
        val = getattr(model_instance, column.name)
        if hasattr(val, "isoformat"):
            val = val.isoformat()
        d[column.name] = val
    return d

@router.get("/pending", response_model=List[Dict[str, Any]])
def get_pending_human_reviews(
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    """
    Returns all candidates who have completed panel & bias checks and are awaiting final human decision.
    """
    candidates = db.query(Candidate).filter(
        Candidate.current_stage.in_(["HUMAN_REVIEW_PENDING", "PANEL_EVALUATED", "BIAS_CHECKED"])
    ).order_by(Candidate.created_at.desc()).all()

    results = []
    for c in candidates:
        latest_panel = db.query(PanelDecision).filter(PanelDecision.candidate_id == c.candidate_id).order_by(PanelDecision.created_at.desc()).first()
        latest_bias = db.query(BiasCheck).filter(BiasCheck.candidate_id == c.candidate_id).order_by(BiasCheck.created_at.desc()).first()
        
        results.append({
            "candidate_id": c.candidate_id,
            "name": c.name,
            "email": c.email,
            "cohort_tag": c.cohort_tag,
            "current_stage": c.current_stage,
            "target_jd_id": c.target_jd_id,
            "panel_decision": model_to_dict(latest_panel),
            "bias_check": model_to_dict(latest_bias),
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    return results

@router.post("/decide", response_model=HumanReviewResponse)
def submit_human_decision(
    payload: HumanReviewCreate, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    """
    Records an authenticated Human Reviewer's final hiring decision.
    Governance Rule: AI CAN NEVER INVOKE OR BYPASS THIS ENDPOINT.
    Allowed Decisions: APPROVE, REJECT, REQUEST_MORE_INFORMATION.
    """
    if payload.decision not in ["APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid decision. Must be APPROVE, REJECT, or REQUEST_MORE_INFORMATION."
        )

    cand = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    reviewer_id = current_user.get("user_id", payload.reviewer_id)
    reviewer_name = current_user.get("name", payload.reviewer_name)

    # Save through ATS Tool
    saved = ATSTools.save_human_review(
        db,
        candidate_id=cand.candidate_id,
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
        decision=payload.decision,
        notes=payload.notes
    )

    log_event(
        db,
        stage="DECIDED",
        event=f"Final Human Decision Recorded: {payload.decision} by {reviewer_name}",
        agent=f"HUMAN_REVIEWER ({reviewer_name})",
        candidate_id=cand.candidate_id,
        input_reference={"reviewer_id": reviewer_id, "notes": payload.notes},
        output={"decision": payload.decision, "final_status": cand.current_stage}
    )

    review_obj = db.query(HumanReview).filter(HumanReview.review_id == saved["review_id"]).first()
    return review_obj
