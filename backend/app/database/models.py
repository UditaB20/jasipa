import uuid
from datetime import datetime
from sqlalchemy import (
    Column, String, Integer, Float, Boolean, Text, DateTime, ForeignKey, JSON
)
from sqlalchemy.orm import relationship
from app.database.session import Base

def generate_uuid():
    return str(uuid.uuid4())

class Candidate(Base):
    __tablename__ = "candidates"

    candidate_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    name = Column(String, nullable=False, index=True)
    email = Column(String, nullable=False, unique=True, index=True)
    phone = Column(String, nullable=True)
    cohort_tag = Column(String, nullable=True, default="General Cohort")
    resume_text = Column(Text, nullable=True)
    resume_file_path = Column(String, nullable=True)
    skills_extracted = Column(JSON, default=list) # List of extracted skills
    experience_years = Column(Float, default=0.0)
    education = Column(String, nullable=True)
    target_jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=True)
    current_stage = Column(
        String, 
        default="APPLIED", 
        index=True
    ) # APPLIED, RESUME_SCREENED, TECHNICAL_ASSESSED, BEHAVIORAL_ASSESSED, PANEL_EVALUATED, BIAS_CHECKED, HUMAN_REVIEW_PENDING, DECIDED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships (ordered oldest -> newest; PKs are UUIDs so insertion order is NOT implied)
    job_description = relationship("JobDescription", back_populates="candidates")
    screening_results = relationship("ScreeningResult", back_populates="candidate", cascade="all, delete-orphan", order_by="ScreeningResult.created_at")
    assessments = relationship("Assessment", back_populates="candidate", cascade="all, delete-orphan", order_by="Assessment.completed_date")
    panel_decisions = relationship("PanelDecision", back_populates="candidate", cascade="all, delete-orphan", order_by="PanelDecision.created_at")
    bias_checks = relationship("BiasCheck", back_populates="candidate", cascade="all, delete-orphan", order_by="BiasCheck.created_at")
    human_reviews = relationship("HumanReview", back_populates="candidate", cascade="all, delete-orphan", order_by="HumanReview.timestamp")
    hiring_outcomes = relationship("HiringOutcome", back_populates="candidate", cascade="all, delete-orphan")
    audit_logs = relationship("AuditLog", back_populates="candidate", cascade="all, delete-orphan")


class JobDescription(Base):
    __tablename__ = "job_descriptions"

    jd_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    title = Column(String, nullable=False, index=True)
    department = Column(String, nullable=False, default="Engineering")
    description = Column(Text, nullable=False)
    required_skills = Column(JSON, default=list) # e.g. ["Python", "SQL", "FastAPI"]
    preferred_skills = Column(JSON, default=list) # e.g. ["Docker", "Kubernetes"]
    min_experience = Column(Float, default=2.0)
    education_requirement = Column(String, default="Bachelor's in Computer Science or related field")
    rubric_version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidates = relationship("Candidate", back_populates="job_description")
    rubrics = relationship("Rubric", back_populates="job_description", cascade="all, delete-orphan")


class Rubric(Base):
    __tablename__ = "rubrics"

    rubric_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=False, index=True)
    version = Column(String, default="1.0", nullable=False)
    resume_weight = Column(Float, default=0.40) # 40%
    skill_weight = Column(Float, default=0.40)  # 40%
    culture_weight = Column(Float, default=0.20) # 20%
    criteria = Column(JSON, default=dict) # Detailed breakdown of skill points and behavioral competencies
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    job_description = relationship("JobDescription", back_populates="rubrics")


class ScreeningResult(Base):
    __tablename__ = "screening_results"

    screening_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=False, index=True)
    score = Column(Float, nullable=False) # 0 to 100
    matched_requirements = Column(JSON, default=list)
    missing_requirements = Column(JSON, default=list)
    experience_match = Column(Boolean, default=True)
    evidence = Column(JSON, default=list) # Observed facts extracted from resume
    rubric_version = Column(String, default="1.0")
    status = Column(String, default="COMPLETED") # COMPLETED, INSUFFICIENT_EVIDENCE
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="screening_results")


class Assessment(Base):
    __tablename__ = "assessments"

    assessment_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=False, index=True)
    test_type = Column(String, nullable=False) # "TECHNICAL" or "BEHAVIORAL"
    questions = Column(JSON, default=list) # List of generated question dicts
    answers = Column(JSON, default=list) # Candidate submitted answers
    score = Column(Float, default=0.0) # 0 to 100
    skill_breakdown = Column(JSON, default=dict) # e.g. {"Python": 90, "SQL": 80} or {"communication": 8, "teamwork": 9}
    evidence = Column(JSON, default=list) # Specific citations from candidate answers
    confidence = Column(Float, default=1.0)
    status = Column(String, default="COMPLETED") # COMPLETED, INSUFFICIENT_EVIDENCE, PENDING
    completed_date = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="assessments")


class PanelDecision(Base):
    __tablename__ = "panel_decisions"

    decision_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=False, index=True)
    resume_score = Column(Float, nullable=False)
    skill_score = Column(Float, nullable=False)
    culture_score = Column(Float, nullable=False)
    merged_score = Column(Float, nullable=False)
    recommendation = Column(
        String, 
        nullable=False
    ) # PROCEED_TO_HUMAN_REVIEW, HUMAN_REVIEW_REQUIRED, ADDITIONAL_INFORMATION_REQUIRED
    strengths = Column(JSON, default=list)
    gaps = Column(JSON, default=list)
    disagreements = Column(JSON, default=list)
    evidence = Column(JSON, default=list)
    natural_language_summary = Column(Text, nullable=True)
    decision_factors = Column(JSON, default=list)
    highlighted_concerns = Column(JSON, default=list)
    highlighted_strengths = Column(JSON, default=list)
    requires_four_eyes_review = Column(Boolean, default=False)
    used_llm_synthesis = Column(Boolean, default=False)
    synthesis_latency_ms = Column(Integer, default=0)
    synthesis_strategy = Column(String, default="template")
    synthesis_error = Column(String, nullable=True)
    rubric_version = Column(String, default="1.0")
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="panel_decisions")
    bias_checks = relationship("BiasCheck", back_populates="panel_decision", cascade="all, delete-orphan")


class BiasCheck(Base):
    __tablename__ = "bias_checks"

    check_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    decision_id = Column(String, ForeignKey("panel_decisions.decision_id"), nullable=False, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    flag_status = Column(
        String, 
        nullable=False, 
        default="NO_SIGNIFICANT_DISPARITY_DETECTED"
    ) # FLAGGED, NO_SIGNIFICANT_DISPARITY_DETECTED
    reason = Column(String, nullable=True)
    cohort_breakdown = Column(JSON, default=dict) # Comparative statistics across cohorts
    requires_human_review = Column(Boolean, default=True) # Always True per governance rule
    reviewer_notes = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="bias_checks")
    panel_decision = relationship("PanelDecision", back_populates="bias_checks")


class HumanReview(Base):
    __tablename__ = "human_reviews"

    review_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, index=True)
    decision_id = Column(String, ForeignKey("panel_decisions.decision_id"), nullable=True, index=True)
    bias_check_id = Column(String, ForeignKey("bias_checks.check_id"), nullable=True, index=True)
    reviewer_id = Column(String, nullable=False, default="HR_REVIEWER_01")
    reviewer_name = Column(String, nullable=False, default="Lead Talent Partner")
    decision = Column(
        String, 
        nullable=False
    ) # APPROVE, REJECT, REQUEST_MORE_INFORMATION
    notes = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="human_reviews")
    panel_decision = relationship("PanelDecision")
    bias_check = relationship("BiasCheck")


class HiringOutcome(Base):
    """Post-hire outcomes entered by HR; kept separate from candidate evaluation."""
    __tablename__ = "hiring_outcomes"

    outcome_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=False, unique=True, index=True)
    hired_date = Column(DateTime, nullable=False)
    role = Column(String, nullable=True)
    performance_rating = Column(Float, nullable=True)  # 1–5, manager-reported
    still_employed = Column(Boolean, nullable=True)
    months_employed = Column(Integer, nullable=True)
    manager_name = Column(String, nullable=True)
    manager_email = Column(String, nullable=True)
    manager_id = Column(String, nullable=True)
    department = Column(String, nullable=True)
    departure_date = Column(DateTime, nullable=True)
    tenure_days = Column(Integer, nullable=True)
    promotion_date = Column(DateTime, nullable=True)
    promotion_role = Column(String, nullable=True)
    performance_comments = Column(Text, nullable=True)
    technical_skills_rating = Column(Float, nullable=True)
    communication_rating = Column(Float, nullable=True)
    leadership_rating = Column(Float, nullable=True)
    rehire_eligible = Column(Boolean, nullable=True)
    attrition_reason = Column(Text, nullable=True)
    manager_feedback = Column(Text, nullable=True)
    recorded_by = Column(String, nullable=False)
    recorded_date = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    last_updated = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    candidate = relationship("Candidate", back_populates="hiring_outcomes")


class StrategyMetric(Base):
    __tablename__ = "strategy_metrics"

    metric_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    invocation_id = Column(String, nullable=False, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=True, index=True)
    agent_name = Column(String, nullable=False, index=True)
    strategy_name = Column(String, nullable=False, index=True)
    fallback_level = Column(Integer, nullable=False, default=0)
    success = Column(Boolean, nullable=False)
    error_code = Column(String, nullable=True)
    latency_ms = Column(Integer, nullable=False, default=0)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)


class HumanExpertTask(Base):
    __tablename__ = "human_expert_tasks"

    task_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=True, index=True)
    agent_name = Column(String, nullable=False)
    reason = Column(Text, nullable=False)
    status = Column(String, nullable=False, default="PENDING", index=True)
    assigned_to = Column(String, nullable=False, default="HR_EXPERT")
    created_at = Column(DateTime, default=datetime.utcnow, index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    log_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    candidate_id = Column(String, ForeignKey("candidates.candidate_id"), nullable=True, index=True)
    stage = Column(String, nullable=False)
    event = Column(String, nullable=False)
    agent = Column(String, nullable=False)
    input_reference = Column(JSON, default=dict)
    output = Column(JSON, default=dict)
    rubric_version = Column(String, nullable=True)
    model_name = Column(String, default="gemini-2.5-flash")
    prompt_version = Column(String, default="v2.1")
    prev_hash = Column(String, nullable=True)
    entry_hash = Column(String, nullable=True)
    timestamp = Column(DateTime, default=datetime.utcnow, index=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="audit_logs")
