from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class HiringOutcomeCreate(BaseModel):
    candidate_id: str
    hired_date: datetime
    role: Optional[str] = Field(None, max_length=200)
    performance_rating: float = Field(ge=1, le=5)
    still_employed: bool
    months_employed: int = Field(ge=0, le=120)
    manager_name: Optional[str] = Field(None, max_length=160)
    manager_email: str = Field(min_length=5, max_length=254)
    manager_id: Optional[str] = Field(None, max_length=160)
    department: Optional[str] = Field(None, max_length=160)
    departure_date: Optional[datetime] = None
    tenure_days: Optional[int] = Field(None, ge=0)
    promotion_date: Optional[datetime] = None
    promotion_role: Optional[str] = Field(None, max_length=200)
    performance_comments: Optional[str] = Field(None, max_length=3000)
    technical_skills_rating: Optional[float] = Field(None, ge=1, le=5)
    communication_rating: Optional[float] = Field(None, ge=1, le=5)
    leadership_rating: Optional[float] = Field(None, ge=1, le=5)
    rehire_eligible: Optional[bool] = None
    attrition_reason: Optional[str] = Field(None, max_length=1000)
    manager_feedback: Optional[str] = Field(None, max_length=3000)


class HiringOutcomeResponse(HiringOutcomeCreate):
    performance_rating: Optional[float] = None
    still_employed: Optional[bool] = None
    months_employed: Optional[int] = None
    manager_email: Optional[str] = None
    outcome_id: str
    recorded_by: str
    updated_at: datetime
    recorded_date: Optional[datetime] = None
    last_updated: Optional[datetime] = None

    class Config:
        from_attributes = True
