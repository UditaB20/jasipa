from pydantic import BaseModel, Field, field_validator
from typing import List, Optional
from datetime import datetime

class JobDescriptionBase(BaseModel):
    title: str = Field(min_length=3, max_length=150)
    department: str = Field("Engineering", min_length=2, max_length=100)
    description: str = Field(min_length=30, max_length=10000)
    required_skills: List[str] = Field(min_length=1, max_length=25)
    preferred_skills: Optional[List[str]] = Field(default_factory=list, max_length=25)

    @field_validator("title", "department", "description")
    @classmethod
    def strip_text(cls, v):
        return v.strip() if isinstance(v, str) else v

    @field_validator("required_skills", "preferred_skills")
    @classmethod
    def clean_skills(cls, v):
        seen, cleaned = set(), []
        for skill in v or []:
            skill = " ".join(str(skill).split())[:60]
            if skill and skill.lower() not in seen:
                seen.add(skill.lower())
                cleaned.append(skill)
        return cleaned
    min_experience: Optional[int] = Field(default=2, ge=0, le=40, description="Minimum years of experience required (whole numbers >= 0)")
    education_requirement: Optional[str] = "Bachelor's in Computer Science or related field"

    @field_validator("min_experience", mode="before")
    @classmethod
    def coerce_min_experience(cls, v):
        if v is None:
            return 0
        try:
            return max(0, min(40, int(round(float(v)))))
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
