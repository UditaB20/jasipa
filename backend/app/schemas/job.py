from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime

class JobDescriptionBase(BaseModel):
    title: str
    department: str = "Engineering"
    description: str
    required_skills: List[str]
    preferred_skills: Optional[List[str]] = []
    min_experience: Optional[float] = 2.0
    education_requirement: Optional[str] = "Bachelor's in Computer Science or related field"

class JobDescriptionCreate(JobDescriptionBase):
    pass

class JobDescriptionUpdate(BaseModel):
    title: Optional[str] = None
    department: Optional[str] = None
    description: Optional[str] = None
    required_skills: Optional[List[str]] = None
    preferred_skills: Optional[List[str]] = None
    min_experience: Optional[float] = None
    education_requirement: Optional[str] = None

class JobDescriptionResponse(JobDescriptionBase):
    jd_id: str
    rubric_version: str
    created_at: datetime

    class Config:
        from_attributes = True
