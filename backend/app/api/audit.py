from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.database.models import AuditLog, Candidate
from app.schemas.audit import AuditLogResponse
from app.mcp.tools import ATSTools
from app.auth.security import require_hr, get_current_user

router = APIRouter(prefix="/audit", tags=["Auditability & Candidate Memory"])

@router.get("/candidate/{candidate_id}")
def get_candidate_audit_trail(
    candidate_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Returns full chronological audit timeline answering:
    'Why did this candidate receive this recommendation?'
    Only HR or the candidate themselves can query their audit trail.
    """
    if current_user.get("role") != "HR" and current_user.get("candidate_id") != candidate_id:
        raise HTTPException(status_code=403, detail="Forbidden: You cannot access audit logs of other candidates.")

    history = ATSTools.get_candidate_history(db, candidate_id)
    if "error" in history:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return history

@router.get("/logs", response_model=List[AuditLogResponse])
def get_recent_audit_logs(
    limit: int = 50,
    candidate_id: Optional[str] = None,
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    """
    Returns system-wide immutable event logs.
    Restricted strictly to HR users.
    """
    query = db.query(AuditLog)
    if candidate_id:
        query = query.filter(AuditLog.candidate_id == candidate_id)
    return query.order_by(AuditLog.timestamp.desc()).limit(limit).all()
