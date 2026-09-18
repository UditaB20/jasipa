from pydantic import BaseModel
from typing import List, Optional, Any, Dict
from datetime import datetime
from app.schemas.screening import ScreeningResultResponse
from app.schemas.assessment import AssessmentResponse
from app.schemas.panel import PanelDecisionResponse
from app.schemas.bias import BiasCheckResponse
from app.schemas.review import HumanReviewResponse
from app.schemas.audit import AuditLogResponse

class CandidateBase(BaseModel):
    name: str
    email: str
    phone: Optional[str] = None
    cohort_tag: Optional[str] = "General Cohort"
    experience_years: Optional[float] = 0.0
    education: Optional[str] = None
    target_jd_id: Optional[str] = None

class CandidateCreate(CandidateBase):
    resume_text: Optional[str] = None
    skills_extracted: Optional[List[str]] = []

class CandidateUpdate(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    cohort_tag: Optional[str] = None
    current_stage: Optional[str] = None
    target_jd_id: Optional[str] = None
    experience_years: Optional[float] = None
    education: Optional[str] = None
    resume_text: Optional[str] = None

class CandidateResponse(CandidateBase):
    candidate_id: str
    current_stage: str
    skills_extracted: List[str] = []
    resume_file_path: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

class CandidateDetailResponse(CandidateResponse):
    screening_results: List[ScreeningResultResponse] = []
    assessments: List[AssessmentResponse] = []
    panel_decisions: List[PanelDecisionResponse] = []
    bias_checks: List[BiasCheckResponse] = []
    human_reviews: List[HumanReviewResponse] = []
    audit_logs: List[AuditLogResponse] = []

    class Config:
        from_attributes = True
