from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from datetime import datetime

class QuestionItem(BaseModel):
    question_id: str
    type: str # "mcq", "short_answer", "coding", "behavioral"
    competency_or_skill: str # e.g. "Python", "SQL", "Teamwork", "Communication"
    prompt: str
    options: Optional[List[str]] = None # for MCQ
    rubric_guideline: Optional[str] = None # what constitutes a strong answer

class AnswerItem(BaseModel):
    question_id: str = Field(min_length=1, max_length=40)
    answer_text: str = Field(default="", max_length=20000)

class SkillAssessorOutput(BaseModel):
    candidate_id: str
    jd_id: str
    test_id: Optional[str] = None
    score: float # 0 to 100
    skill_breakdown: Dict[str, float]
    evidence: List[str]
    confidence: float = 1.0
    status: str = "COMPLETED" # COMPLETED, INSUFFICIENT_EVIDENCE, EXPERT_REVIEW_PENDING, EVALUATION_FAILED
    strategy_used: str = "none"
    fallback_chain_depth: int = 0
    fallback_latency_ms: int = 0
    attempts_before_success: int = 0
    question_scores: Dict[str, float] = Field(default_factory=dict)
    execution_results: Dict[str, Any] = Field(default_factory=dict)

class CultureFitOutput(BaseModel):
    candidate_id: str
    jd_id: str
    test_id: Optional[str] = None
    score: float # 0 to 100 (or 0 if INSUFFICIENT_EVIDENCE)
    breakdown: Dict[str, float] # e.g. {"communication": 8.5, "teamwork": 9.0, "problem_solving": 8.0, "adaptability": 7.5}
    evidence: List[str]
    confidence: float = 1.0
    status: str = "COMPLETED" # COMPLETED or INSUFFICIENT_EVIDENCE
    strategy_used: str = "none"
    fallback_chain_depth: int = 0
    fallback_latency_ms: int = 0
    attempts_before_success: int = 0

class AssessmentResponse(BaseModel):
    assessment_id: str
    candidate_id: str
    jd_id: str
    test_type: str
    questions: List[Dict[str, Any]]
    answers: List[Dict[str, Any]]
    score: float
    skill_breakdown: Dict[str, Any]
    evidence: List[str]
    confidence: float
    status: str
    question_set_id: Optional[str] = None
    execution_results: Optional[Dict[str, Any]] = None
    strategy_used: Optional[str] = None
    completed_date: datetime

    class Config:
        from_attributes = True
