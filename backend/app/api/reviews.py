from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from app.database.session import get_db
from app.database.models import Candidate, HumanReview, PanelDecision, BiasCheck, AuditLog
from app.schemas.review import HumanReviewCreate, HumanReviewResponse
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.auth.security import get_current_user, require_hr
from app.api.learning import historical_context

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
    Candidates with active, unresolved rights appeals are prioritized at the top.
    """
    candidates = db.query(Candidate).filter(
        Candidate.current_stage.in_(["HUMAN_REVIEW_PENDING", "PANEL_EVALUATED", "BIAS_CHECKED"])
    ).order_by(Candidate.created_at.desc()).all()

    results = []
    for c in candidates:
        latest_panel = db.query(PanelDecision).filter(PanelDecision.candidate_id == c.candidate_id).order_by(PanelDecision.created_at.desc()).first()
        latest_bias = db.query(BiasCheck).filter(BiasCheck.candidate_id == c.candidate_id).order_by(BiasCheck.created_at.desc()).first()
        
        # Check if candidate has requested an expedited human appeal / re-review
        latest_appeal = db.query(AuditLog).filter(
            AuditLog.candidate_id == c.candidate_id,
            AuditLog.agent == "HUMAN_CANDIDATE_APPEAL"
        ).order_by(AuditLog.timestamp.desc()).first()

        latest_review = db.query(HumanReview).filter(
            HumanReview.candidate_id == c.candidate_id
        ).order_by(HumanReview.timestamp.desc()).first()

        is_appeal = bool(latest_appeal and (not latest_review or latest_appeal.timestamp > latest_review.timestamp))

        incomplete = bool(latest_panel and latest_panel.recommendation == "ADDITIONAL_INFORMATION_REQUIRED")
        score_spread = (max(latest_panel.resume_score, latest_panel.skill_score, latest_panel.culture_score) - min(latest_panel.resume_score, latest_panel.skill_score, latest_panel.culture_score)) if latest_panel and not incomplete else None
        # Agreement is a transparent heuristic, not a calibrated probability of job success.
        # It is withheld when a stage is missing, because a 0 placeholder is not a real disagreement.
        agreement = round(max(0, 1 - score_spread / 50), 2) if score_spread is not None else None
        if incomplete:
            agreement_label = "INCOMPLETE_EVIDENCE"
        elif agreement is None:
            agreement_label = "UNAVAILABLE"
        else:
            agreement_label = "HIGH_AGREEMENT" if agreement >= 0.8 else "MIXED" if agreement >= 0.5 else "LOW_AGREEMENT"
        
        results.append({
            "candidate_id": c.candidate_id,
            "name": c.name,
            "email": c.email,
            "cohort_tag": c.cohort_tag,
            "current_stage": c.current_stage,
            "target_jd_id": c.target_jd_id,
            "is_appeal": is_appeal,
            "appeal_timestamp": latest_appeal.timestamp.isoformat() if latest_appeal else None,
            "panel_decision": model_to_dict(latest_panel),
            "confidence": {"agreement_score": agreement, "label": agreement_label, "calibrated": False, "score_spread": score_spread},
            "historical_context": historical_context(db, c, latest_panel),
            "bias_check": model_to_dict(latest_bias),
            "created_at": c.created_at.isoformat() if c.created_at else None
        })
    # Prioritize active appeals first, then newest
    results.sort(key=lambda x: (not x.get("is_appeal", False), x.get("created_at") or ""), reverse=False)
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
    Strictly verifies that Panel Evaluation and Bias Check are completed before sign-off.
    """
    if payload.decision not in ["APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"]:
        raise HTTPException(
            status_code=400, 
            detail="Invalid decision. Must be APPROVE, REJECT, or REQUEST_MORE_INFORMATION."
        )

    cand = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    # Verify candidate is in a valid stage for final human review
    allowed_stages = ["HUMAN_REVIEW_PENDING", "PANEL_EVALUATED", "BIAS_CHECKED", "DECIDED"]
    if cand.current_stage not in allowed_stages:
        raise HTTPException(
            status_code=400,
            detail=f"Candidate current stage is '{cand.current_stage}'. Final decision requires completion of panel evaluation and bias check."
        )

    # Verify and bind Panel Decision
    if payload.decision_id:
        panel_decision = db.query(PanelDecision).filter(
            PanelDecision.decision_id == payload.decision_id,
            PanelDecision.candidate_id == cand.candidate_id
        ).first()
    else:
        panel_decision = db.query(PanelDecision).filter(
            PanelDecision.candidate_id == cand.candidate_id
        ).order_by(PanelDecision.created_at.desc()).first()

    if not panel_decision:
        raise HTTPException(
            status_code=400,
            detail="Governance violation: Cannot finalize hiring decision without a completed Panel Coordinator evaluation."
        )

    # Verify and bind Bias Check
    if payload.bias_check_id:
        bias_check = db.query(BiasCheck).filter(
            BiasCheck.check_id == payload.bias_check_id,
            BiasCheck.candidate_id == cand.candidate_id
        ).first()
    else:
        bias_check = db.query(BiasCheck).filter(
            BiasCheck.candidate_id == cand.candidate_id
        ).order_by(BiasCheck.created_at.desc()).first()

    if not bias_check:
        raise HTTPException(
            status_code=400,
            detail="Governance violation: Cannot finalize hiring decision without an explicit Bias Check audit logged alongside the decision."
        )

    reviewer_id = current_user.get("user_id", payload.reviewer_id)
    reviewer_name = current_user.get("name", payload.reviewer_name)

    # Save through ATS Tool with immutable audit links
    saved = ATSTools.save_human_review(
        db,
        candidate_id=cand.candidate_id,
        reviewer_id=reviewer_id,
        reviewer_name=reviewer_name,
        decision=payload.decision,
        notes=payload.notes,
        decision_id=panel_decision.decision_id,
        bias_check_id=bias_check.check_id
    )

    log_event(
        db,
        stage="DECIDED",
        event=f"Final Human Decision Recorded: {payload.decision} by {reviewer_name}",
        agent=f"HUMAN_REVIEWER ({reviewer_name})",
        candidate_id=cand.candidate_id,
        input_reference={
            "reviewer_id": reviewer_id, 
            "notes": payload.notes,
            "decision_id": panel_decision.decision_id,
            "bias_check_id": bias_check.check_id
        },
        output={"decision": payload.decision, "final_status": cand.current_stage}
    )

    review_obj = db.query(HumanReview).filter(HumanReview.review_id == saved["review_id"]).first()
    return review_obj
