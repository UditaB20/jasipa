import hashlib
import json
import threading
from datetime import datetime
from typing import Optional, Dict, Any
from sqlalchemy import func
from sqlalchemy.orm import Session
from app.database.models import AuditLog

GENESIS_HASH = "0" * 64
HASH_VERSION = 2
_chain_lock = threading.Lock()


def _canonical(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), default=str)


def compute_entry_hash(entry: AuditLog) -> str:
    """Hash of the previous hash plus every recorded field, so edits to inputs/outputs are detectable."""
    body = {
        "seq": entry.seq, "candidate_id": entry.candidate_id, "stage": entry.stage, "event": entry.event,
        "agent": entry.agent, "input_reference": entry.input_reference or {}, "output": entry.output or {},
        "rubric_version": entry.rubric_version, "model_name": entry.model_name,
        "prompt_version": entry.prompt_version, "timestamp": entry.timestamp.isoformat() if entry.timestamp else None,
    }
    return hashlib.sha256(f"{entry.prev_hash}:{_canonical(body)}".encode("utf-8")).hexdigest()


def _legacy_entry_hash(entry: AuditLog) -> str:
    payload = (f"{entry.stage}|{entry.event}|{entry.agent}|{entry.candidate_id or 'NONE'}|{entry.rubric_version or 'NONE'}|"
               f"{entry.model_name}|{entry.prompt_version}|{entry.timestamp.isoformat()}")
    return hashlib.sha256(f"{entry.prev_hash}:{payload}".encode("utf-8")).hexdigest()


def log_event(
    db: Session,
    stage: str,
    event: str,
    agent: str,
    candidate_id: Optional[str] = None,
    input_reference: Optional[Dict[str, Any]] = None,
    output: Optional[Dict[str, Any]] = None,
    rubric_version: Optional[str] = None,
    model_name: Optional[str] = None,
    prompt_version: str = "v2.2"
) -> AuditLog:
    """Appends a tamper-evident entry to the audit ledger.

    model_name records what actually produced the output (an LLM model id, a deterministic strategy
    name, or "n/a" for human/system events) so the ledger does not imply an LLM ran when it did not.
    """
    with _chain_lock:
        last_log = db.query(AuditLog).filter(AuditLog.seq.isnot(None)).order_by(AuditLog.seq.desc()).first()
        if last_log is None:
            last_log = db.query(AuditLog).order_by(AuditLog.timestamp.desc(), AuditLog.log_id.desc()).first()
        prev_hash = last_log.entry_hash if (last_log and last_log.entry_hash) else GENESIS_HASH
        next_seq = (db.query(func.max(AuditLog.seq)).scalar() or 0) + 1

        entry = AuditLog(
            seq=next_seq,
            hash_version=HASH_VERSION,
            candidate_id=candidate_id,
            stage=stage,
            event=event,
            agent=agent,
            # Round-trip through JSON so the stored value hashes identically when read back.
            input_reference=json.loads(_canonical(input_reference or {})),
            output=json.loads(_canonical(output or {})),
            rubric_version=rubric_version,
            model_name=model_name or "n/a",
            prompt_version=prompt_version,
            prev_hash=prev_hash,
            timestamp=datetime.utcnow(),
        )
        entry.entry_hash = compute_entry_hash(entry)
        db.add(entry)
        db.commit()
        db.refresh(entry)
        return entry


def verify_chain(db: Session) -> Dict[str, Any]:
    """Recomputes every entry hash and checks each entry links to its predecessor."""
    logs = db.query(AuditLog).order_by(AuditLog.seq.is_(None).desc(), AuditLog.seq.asc(), AuditLog.timestamp.asc()).all()
    if not logs:
        return {"verified": True, "status": "EMPTY", "total_audited": 0, "chain_verified_count": 0, "issues": []}
    issues = []
    prev_hash = None
    for entry in logs:
        expected = compute_entry_hash(entry) if entry.hash_version == HASH_VERSION else _legacy_entry_hash(entry)
        if entry.entry_hash != expected:
            issues.append({"log_id": entry.log_id, "seq": entry.seq, "problem": "Entry content does not match its hash"})
        if prev_hash is not None and entry.prev_hash != prev_hash:
            issues.append({"log_id": entry.log_id, "seq": entry.seq, "problem": "Entry does not link to the previous entry"})
        prev_hash = entry.entry_hash
    return {
        "verified": not issues,
        "status": "VALID" if not issues else "TAMPERING_DETECTED",
        "total_audited": len(logs),
        "chain_verified_count": len(logs) - len({issue["log_id"] for issue in issues}),
        "issues": issues[:50],
    }
