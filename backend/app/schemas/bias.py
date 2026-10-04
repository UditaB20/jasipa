from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime

class BiasCheckOutput(BaseModel):
    candidate_id: str
    decision_id: str
    flag_status: str # "FLAGGED" or "NO_SIGNIFICANT_DISPARITY_DETECTED"
    reason: str
    cohort_breakdown: Dict[str, Any]
    requires_human_review: bool = True # Always True per project governance
    checks: List[Dict[str, Any]] = []
    overall_flag: bool = False
    recommendations: List[str] = []
    confidence_level: str = "low"
    sample_size: int = 0
    action_required: bool = True

class BiasCheckResponse(BiasCheckOutput):
    check_id: str
    reviewer_notes: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True

class CohortMetric(BaseModel):
    cohort_name: str
    total_candidates: int
    average_score: float
    proceed_rate: float
    flagged_disparity: bool

class CohortAnalyticsResponse(BaseModel):
    total_evaluated: int
    cohorts: List[CohortMetric]
    overall_disparity_ratio: float
    disparity_detected: bool
    summary: str
