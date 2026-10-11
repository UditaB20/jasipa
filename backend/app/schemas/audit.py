from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class AuditLogCreate(BaseModel):
    candidate_id: Optional[str] = None
    stage: str
    event: str
    agent: str
    input_reference: Optional[Dict[str, Any]] = {}
    output: Optional[Dict[str, Any]] = {}
    rubric_version: Optional[str] = None
    model_name: Optional[str] = None
    prompt_version: Optional[str] = None
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None

class AuditLogResponse(AuditLogCreate):
    log_id: str
    seq: Optional[int] = None
    timestamp: datetime
    prev_hash: Optional[str] = None
    entry_hash: Optional[str] = None

    class Config:
        from_attributes = True
