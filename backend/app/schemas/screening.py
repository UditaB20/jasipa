from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class ResumeScreeningOutput(BaseModel):
    candidate_id: str
    jd_id: str
    score: float # 0 to 100
    matched_requirements: List[str]
    missing_requirements: List[str]
    experience_match: bool
    evidence: List[str]
    rubric_version: str = "1.0"
    status: str = "COMPLETED" # COMPLETED or INSUFFICIENT_EVIDENCE
    strategy_used: str = "none"
    fallback_chain_depth: int = 0
    fallback_latency_ms: int = 0
    attempts_before_success: int = 0

class ScreeningResultResponse(ResumeScreeningOutput):
    screening_id: str
    created_at: datetime

    class Config:
        from_attributes = True
