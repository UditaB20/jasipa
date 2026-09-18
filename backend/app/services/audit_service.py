from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import AuditLog

def log_event(
    db: Session,
    stage: str,
    event: str,
    agent: str,
    candidate_id: Optional[str] = None,
    input_reference: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    rubric_version: Optional[str] = None
) -> AuditLog:
    """
    Persistently logs every workflow action, agent invocation, and human decision.
    Ensures complete, tamper-evident auditability.
    """
    audit_entry = AuditLog(
        candidate_id=candidate_id,
        stage=stage,
        event=event,
        agent=agent,
        input_reference=input_reference or {},
        output=output or {},
        rubric_version=rubric_version,
        timestamp=datetime.utcnow()
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
