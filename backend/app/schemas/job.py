from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class JobDescriptionBase(BaseModel):
    title: str
    department: str = "Engineering"
    description: str
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    min_experience: Optional[int] = Field(default=2, ge=0, description="Minimum years of experience required (whole numbers >= 0)")
    education_requirement: Optional[str] = "Bachelor's in Computer Science or related field"

    @field_validator("min_experience", mode="before")
    @classmethod
    def coerce_min_experience(cls, v):
        if v is None:
            return 0
        try:
            return max(0, int(round(float(v))))
        except Exception:
            return 0

class JobDescriptionCreate(JobDescriptionBase):
    pass

class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience: Optional[int] = Field(None, ge=0)
    education_requirement: Optional[str] = None

    @field_validator("min_experience", mode="before")
    @classmethod
    def coerce_min_experience_update(cls, v):
        if v is None:
            return None
        try:
            return max(0, int(round(float(v))))
        except Exception:
            return None



class JobDescriptionResponse(JobDescriptionBase):
    jd_id: str
    rubric_version: str
    created_at: datetime

    class Config:
        from_attributes = True
