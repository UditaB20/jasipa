from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class PanelDecisionOutput(BaseModel):
    candidate_id: str
    jd_id: str
    resume_score: float
    skill_score: float
    culture_score: float
    merged_score: float
    recommendation: str # PROCEED_TO_HUMAN_REVIEW, HUMAN_REVIEW_REQUIRED, ADDITIONAL_INFORMATION_REQUIRED
    strengths: List[str]
    gaps: List[str]
    disagreements: List[str]
    evidence: List[str]
    rubric_version: str = "1.0"

class PanelDecisionResponse(PanelDecisionOutput):
    decision_id: str
    created_at: datetime

    class Config:
        from_attributes = True
