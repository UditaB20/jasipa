from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.schemas.screening import ScreeningResultResponse
from app.schemas.assessment import AssessmentResponse
from app.schemas.panel import PanelDecisionResponse
from app.schemas.bias import BiasCheckResponse
from app.schemas.review import HumanReviewResponse
from app.schemas.audit import AuditLogResponse

class CandidateBase(BaseModel):
    name: str = Field(min_length=2, max_length=120)
    email: str = Field(max_length=254)
    phone: Optional[str] = Field(None, max_length=40)
    cohort_tag: Optional[str] = Field(None, max_length=80)
    experience_years: Optional[float] = Field(0.0, ge=0, le=60)
    education: Optional[str] = Field(None, max_length=200)
    target_jd_id: Optional[str] = None

class CandidateCreate(CandidateBase):
    resume_text: Optional[str] = Field(None, max_length=60000)

class CandidateUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=120)
    email: Optional[str] = Field(None, max_length=254)
    phone: Optional[str] = Field(None, max_length=40)
    cohort_tag: Optional[str] = Field(None, max_length=80)
    current_stage: Optional[str] = None
    target_jd_id: Optional[str] = None
    experience_years: Optional[float] = Field(None, ge=0, le=60)
    education: Optional[str] = Field(None, max_length=200)
    resume_text: Optional[str] = Field(None, max_length=60000)

class CandidateResponse(CandidateBase):
    name: str
    email: str
    candidate_id: str
    current_stage: str
    skills_extracted: List[str] = []
    resume_original_filename: Optional[str] = None
    source: Optional[str] = None
    external_id: Optional[str] = None
    dataset_category: Optional[str] = None
    resume_profile: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CandidateDetailResponse(CandidateResponse):
    resume_text: Optional[str] = None
    resume_sections: List[Dict[str, Any]] = []
    has_original_file: bool = False
    screening_results: List[ScreeningResultResponse] = []
    assessments: List[AssessmentResponse] = []
    panel_decisions: List[PanelDecisionResponse] = []
    bias_checks: List[BiasCheckResponse] = []
    human_reviews: List[HumanReviewResponse] = []
    audit_logs: List[AuditLogResponse] = []

    class Config:
        from_attributes = True
