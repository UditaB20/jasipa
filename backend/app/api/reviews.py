"""Human decisions: the only way a candidate's application can be approved or rejected.

Rules enforced here (no AI component can call this endpoint or the underlying tool):
* A decision requires the candidate's latest panel decision and the bias check recorded for that decision.
* The bias-check result is written to the audit log together with the decision.
* When the panel escalated (score divergence or low confidence), APPROVE/REJECT needs two different
  HR reviewers who agree. The first sign-off is recorded but does not close the application.
* REQUEST_MORE_INFORMATION keeps the application open; HR re-runs the evaluation once new evidence arrives.
"""
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.auth.security import require_hr
from app.database.models import BiasCheck, Candidate, HumanReview, PanelDecision
from app.database.session import get_db
from app.mcp.tools import ATSTools
from app.schemas.review import HumanReviewCreate
from app.services.audit_service import log_event

router = APIRouter(prefix="/reviews", tags=["Human Decisions"])

DECIDABLE_STAGES = {"HUMAN_REVIEW_PENDING", "PANEL_EVALUATED", "BIAS_CHECKED"}


def _latest_panel(db: Session, candidate_id: str) -> Optional[PanelDecision]:
    return db.query(PanelDecision).filter(PanelDecision.candidate_id == candidate_id).order_by(PanelDecision.created_at.desc()).first()


def _bias_for(db: Session, decision_id: str) -> Optional[BiasCheck]:
    return db.query(BiasCheck).filter(BiasCheck.decision_id == decision_id).order_by(BiasCheck.created_at.desc()).first()


def decision_status(db: Session, cand: Candidate) -> Dict[str, Any]:
    panel = _latest_panel(db, cand.candidate_id)
    bias = _bias_for(db, panel.decision_id) if panel else None
    signoffs = []
    if panel:
        signoffs = [{"review_id": r.review_id, "reviewer_id": r.reviewer_id, "reviewer_name": r.reviewer_name,
                     "decision": r.decision, "notes": r.notes, "is_final": r.is_final is not False,
                     "timestamp": r.timestamp.isoformat() if r.timestamp else None}
                    for r in db.query(HumanReview).filter(HumanReview.decision_id == panel.decision_id).order_by(HumanReview.timestamp.asc()).all()]
    blocking = None
    if cand.current_stage == "DECIDED":
        blocking = "A final decision has been recorded."
    elif cand.current_stage == "INFO_REQUESTED":
        blocking = "More information was requested. Re-run the evaluation when the new evidence is available."
    elif not panel:
        blocking = "Run the evaluation pipeline first: a decision needs a panel recommendation."
    elif not bias:
        blocking = "The panel decision has no bias check recorded. Re-run the evaluation pipeline."
    elif cand.current_stage not in DECIDABLE_STAGES:
        blocking = "The candidate is not awaiting a decision."
    return {"candidate_id": cand.candidate_id, "current_stage": cand.current_stage,
            "decision_id": panel.decision_id if panel else None, "bias_check_id": bias.check_id if bias else None,
            "bias_flag_status": bias.flag_status if bias else None,
            "requires_two_reviewers": bool(panel and panel.requires_four_eyes_review),
            "signoffs": signoffs, "can_decide": blocking is None, "blocking_reason": blocking}


@router.get("/candidate/{candidate_id}")
def get_decision_status(candidate_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return decision_status(db, cand)


@router.post("/decide")
def submit_human_decision(payload: HumanReviewCreate, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    status = decision_status(db, cand)
    if not status["can_decide"]:
        raise HTTPException(status_code=409, detail=status["blocking_reason"])
    if payload.decision_id and payload.decision_id != status["decision_id"]:
        raise HTTPException(status_code=409, detail="A newer panel evaluation exists. Review the latest evaluation before deciding.")

    panel = db.query(PanelDecision).filter(PanelDecision.decision_id == status["decision_id"]).first()
    bias = db.query(BiasCheck).filter(BiasCheck.check_id == status["bias_check_id"]).first()
    reviewer_id, reviewer_name = current_user["user_id"], current_user.get("name") or current_user["email"]
    notes = payload.notes.strip()

    is_final, outcome = True, "FINAL"
    if status["requires_two_reviewers"] and payload.decision in ("APPROVE", "REJECT"):
        prior = [s for s in status["signoffs"] if not s["is_final"] and s["decision"] in ("APPROVE", "REJECT")]
        if any(s["reviewer_id"] == reviewer_id for s in prior):
            raise HTTPException(status_code=409, detail="You have already signed off. A different HR reviewer must give the second sign-off.")
        agreeing = [s for s in prior if s["decision"] == payload.decision]
        if not agreeing:
            is_final = False
            outcome = "AWAITING_SECOND_REVIEWER" if not prior else "REVIEWERS_DISAGREE"

    saved = ATSTools.save_human_review(db, candidate_id=cand.candidate_id, reviewer_id=reviewer_id, reviewer_name=reviewer_name,
                                       decision=payload.decision, notes=notes, decision_id=panel.decision_id,
                                       bias_check_id=bias.check_id, is_final=is_final)
    event = {"FINAL": f"Human decision recorded: {payload.decision}",
             "AWAITING_SECOND_REVIEWER": f"First reviewer sign-off: {payload.decision} (second reviewer required)",
             "REVIEWERS_DISAGREE": f"Reviewer sign-off: {payload.decision} (disagrees with the first reviewer; another reviewer must agree)"}[outcome]
    log_event(db, stage=cand.current_stage, event=event, agent=f"HUMAN_REVIEWER ({reviewer_name})", candidate_id=cand.candidate_id,
              input_reference={"reviewer_id": reviewer_id, "decision_id": panel.decision_id, "panel_recommendation": panel.recommendation,
                               "merged_score": panel.merged_score, "bias_check_id": bias.check_id,
                               "bias_flag_status": bias.flag_status, "bias_reason": bias.reason, "notes": notes},
              output={"decision": payload.decision, "is_final": is_final, "outcome": outcome, "stage": cand.current_stage},
              rubric_version=panel.rubric_version, model_name="n/a")
    return {"review": saved, "outcome": outcome, "status": decision_status(db, cand)}
