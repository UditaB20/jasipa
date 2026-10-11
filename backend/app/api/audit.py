from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.auth.security import require_hr
from app.database.models import AuditLog
from app.database.session import get_db
from app.mcp.tools import ATSTools
from app.schemas.audit import AuditLogResponse
from app.services.audit_service import verify_chain

router = APIRouter(prefix="/audit", tags=["Auditability & Candidate Memory"])


@router.get("/candidate/{candidate_id}")
def get_candidate_audit_trail(candidate_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Chronological record of every agent output and human action for one candidate."""
    history = ATSTools.get_candidate_history(db, candidate_id)
    if "error" in history:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return history


@router.get("/logs", response_model=List[AuditLogResponse])
def get_audit_logs(limit: int = Query(100, ge=1, le=1000), candidate_id: Optional[str] = None,
                   current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    query = db.query(AuditLog)
    if candidate_id:
        query = query.filter(AuditLog.candidate_id == candidate_id)
    return query.order_by(AuditLog.seq.desc().nullslast(), AuditLog.timestamp.desc()).limit(limit).all()


@router.get("/verify")
def verify_audit_integrity(current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Recomputes every entry hash and checks the chain links; any edited or deleted entry is reported."""
    return verify_chain(db)
