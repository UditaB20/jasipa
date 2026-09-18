from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

class CandidateGraphState(BaseModel):
    candidate_id: str
    jd_id: str
    
    # Raw inputs
    resume_text: Optional[str] = None
    jd_data: Dict[str, Any] = Field(default_factory=dict)
    rubric_data: Dict[str, Any] = Field(default_factory=dict)
    
    # Technical assessment inputs & outputs
    tech_questions: List[Dict[str, Any]] = Field(default_factory=list)
    tech_answers: List[Dict[str, str]] = Field(default_factory=list)
    skill_result: Optional[Dict[str, Any]] = None
    
    # Behavioral assessment inputs & outputs
    beh_questions: List[Dict[str, Any]] = Field(default_factory=list)
    beh_answers: List[Dict[str, str]] = Field(default_factory=list)
    behavioral_result: Optional[Dict[str, Any]] = None
    
    # Resume screening output
    screening_result: Optional[Dict[str, Any]] = None
    
    # Panel synthesis
    panel_result: Optional[Dict[str, Any]] = None
    
    # Bias check
    bias_result: Optional[Dict[str, Any]] = None
    
    # Pipeline stage & Human review
    current_stage: str = "APPLIED"
    human_review_result: Optional[Dict[str, Any]] = None
    errors: List[str] = Field(default_factory=list)
