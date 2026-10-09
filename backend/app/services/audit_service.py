import hashlib
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from app.database.models import AuditLog

GENESIS_HASH = "0000000000000000000000000000000000000000000000000000000000000000"

def log_event(
    db: Session,
    stage: str,
    event: str,
    agent: str,
    candidate_id: Optional[str] = None,
    input_reference: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    rubric_version: Optional[str] = None,
    model_name: str = "gemini-2.5-flash",
    prompt_version: str = "v2.1"
) -> AuditLog:
    """
    Persistently logs every workflow action, agent invocation, and human decision.
    Calculates a cryptographic SHA-256 hash chain with the previous entry to ensure
    mathematical, tamper-evident auditability, binding model name and prompt version.
    """
    last_log = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.log_id.desc()).first()
    prev_hash = last_log.entry_hash if (last_log and last_log.entry_hash) else GENESIS_HASH

    now = datetime.utcnow()
    payload_str = f"{stage}|{event}|{agent}|{candidate_id or 'NONE'}|{rubric_version or 'NONE'}|{model_name}|{prompt_version}|{now.isoformat()}"
    entry_hash = hashlib.sha256(f"{prev_hash}:{payload_str}".encode("utf-8")).hexdigest()

    audit_entry = AuditLog(
        candidate_id=candidate_id,
        stage=stage,
        event=event,
        agent=agent,
        input_reference=input_reference or {},
        output=output or {},
        rubric_version=rubric_version,
        model_name=model_name,
        prompt_version=prompt_version,
        prev_hash=prev_hash,
        entry_hash=entry_hash,
        timestamp=now
    )
    db.add(audit_entry)
    db.commit()
    db.refresh(audit_entry)
    return audit_entry
