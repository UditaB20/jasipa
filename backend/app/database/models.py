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
    # Self-reported/HR-recorded cohort used only for aggregate bias monitoring; None means not recorded.
    cohort_tag = Column(String, nullable=True, default=None)
    password_hash = Column(String, nullable=True)  # Only set for candidates with a portal account
    # Where the record came from: dataset_import (Kaggle Resume Dataset), candidate_portal, hr_upload, hr_entry.
    source = Column(String, nullable=True, default="hr_entry", index=True)
    external_id = Column(String, nullable=True, index=True)  # Kaggle row ID for dataset imports
    dataset_category = Column(String, nullable=True)  # Kaggle "Category" label (job category, not a demographic cohort)
    resume_text = Column(Text, nullable=True)
    resume_file_path = Column(String, nullable=True)  # Server-side storage key; never exposed to clients
    resume_original_filename = Column(String, nullable=True)
    resume_hash = Column(String, nullable=True)  # SHA-256 of resume_text; lets screening reuse cached results
    resume_profile = Column(JSON, default=dict)  # Structured extraction: skills, education, experience, projects
    # The question set this applicant was shown; kept even if the rubric (and its questions) change later.
    assigned_question_set_id = Column(String, nullable=True)
    skills_extracted = Column(JSON, default=list) # List of extracted skills
    experience_years = Column(Float, default=0.0)
    education = Column(String, nullable=True)
    target_jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=True)
    current_stage = Column(
        String, 
        default="APPLIED", 
        index=True
    ) # APPLIED, RESUME_SCREENED, TECHNICAL_ASSESSED, BEHAVIORAL_ASSESSED, PANEL_EVALUATED, HUMAN_REVIEW_PENDING, INFO_REQUESTED, DECIDED
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    @property
    def resume_sections(self):
        """Resume text split at recognised headings, in document order (for display)."""
        from app.services.resume_parser import ordered_sections
        return ordered_sections(self.resume_text or "")

    @property
    def has_original_file(self) -> bool:
        from app.services.resume_service import resume_file_path
        return resume_file_path(self) is not None

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
    question_sets = relationship("QuestionSet", back_populates="job_description", cascade="all, delete-orphan")


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
    strategy_used = Column(String, nullable=True)
    resume_hash = Column(String, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    candidate = relationship("Candidate", back_populates="screening_results")


class QuestionSet(Base):
    """Generated assessment for one JD + rubric version, shared by every applicant to that role.

    Persisting the set is both the cache (no repeated LLM calls) and a fairness control: every
    candidate for the same rubric version answers the same questions.
    """
    __tablename__ = "question_sets"

    question_set_id = Column(String, primary_key=True, default=generate_uuid, index=True)
    jd_id = Column(String, ForeignKey("job_descriptions.jd_id"), nullable=False, index=True)
    rubric_version = Column(String, nullable=False)
    content_hash = Column(String, nullable=False, index=True)
    generator = Column(String, nullable=False, default="template")  # llm | template
    technical_questions = Column(JSON, default=list)
    behavioral_questions = Column(JSON, default=list)
    generation_notes = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)

    job_description = relationship("JobDescription", back_populates="question_sets")


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
    status = Column(String, default="COMPLETED") # COMPLETED, INSUFFICIENT_EVIDENCE, EXPERT_REVIEW_PENDING
    question_set_id = Column(String, nullable=True)
    execution_results = Column(JSON, default=dict)  # Sandboxed test-case results per coding question
    strategy_used = Column(String, nullable=True)
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
    round_number = Column(Integer, nullable=True)  # Assessment round this panel run belongs to (candidate memory)
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
        default="NO_INDICATOR_DETECTED"
    ) # STATISTICALLY_SUPPORTED_DISPARITY, POTENTIAL_DISPARITY_INDICATOR, INSUFFICIENT_DATA, NO_INDICATOR_DETECTED
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
    # Four-eyes: a final APPROVE/REJECT on an escalated decision needs two distinct reviewers who agree.
    is_final = Column(Boolean, default=True)
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
    seq = Column(Integer, nullable=True, index=True)  # Monotonic chain position (timestamps can tie)
    hash_version = Column(Integer, nullable=True)  # 2 = hash covers the full canonical entry
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
