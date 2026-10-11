from pydantic import BaseModel, Field
from typing import Literal, Optional
from datetime import datetime


class HumanReviewCreate(BaseModel):
    candidate_id: str
    decision: Literal["APPROVE", "REJECT", "REQUEST_MORE_INFORMATION"]
    notes: str = Field(min_length=10, max_length=4000)
    # The decision is bound to a specific panel decision and its bias check; defaults to the latest.
    decision_id: Optional[str] = None


class HumanReviewResponse(BaseModel):
    review_id: str
    candidate_id: str
    reviewer_id: str
    reviewer_name: str
    decision: str
    notes: str
    decision_id: Optional[str] = None
    bias_check_id: Optional[str] = None
    is_final: Optional[bool] = True
    timestamp: datetime

    class Config:
        from_attributes = True
