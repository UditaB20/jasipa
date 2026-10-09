from pydantic import BaseModel
from typing import Optional
from datetime import datetime

class HumanReviewCreate(BaseModel):
    candidate_id: str
    reviewer_id: str = "HR_REVIEWER_01"
    reviewer_name: str = "Lead Talent Reviewer"
    decision: str # "APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"
    notes: str
    decision_id: Optional[str] = None
    bias_check_id: Optional[str] = None

class HumanReviewResponse(HumanReviewCreate):
    review_id: str
    timestamp: datetime
    decision_id: Optional[str] = None
    bias_check_id: Optional[str] = None

    class Config:
        from_attributes = True

