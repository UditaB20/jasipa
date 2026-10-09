from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from datetime import datetime
from typing import List, Dict, Any, Optional
from pydantic import BaseModel
from app.database.session import get_db
from app.database.models import Candidate, JobDescription, Assessment, ScreeningResult
from app.auth.security import require_candidate
from app.services.assessment_service import (
    generate_technical_questions_for_jd, 
    generate_behavioral_questions_for_jd,
    sanitize_questions_for_candidate
)
from app.agents.skill_assessor import SkillAssessorAgent
from app.agents.culture_fit import CultureFitAgent
from app.agents.resume_screener import ResumeScreenerAgent
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.api.pipeline import get_or_create_rubric

router = APIRouter(prefix="/candidate", tags=["Candidate Portal"])

class CandidateApplyRequest(BaseModel):
    jd_id: str
    resume_text: Optional[str] = None

class AnswerItem(BaseModel):
    question_id: str
    answer_text: str

class CandidateSubmitAssessment(BaseModel):
    jd_id: Optional[str] = None
    answers: List[AnswerItem]

@router.get("/me")
def get_my_profile(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Returns the authenticated candidate's own profile.
    Strictly isolated: queries ONLY by auth_user['candidate_id'].
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    return {
        "candidate_id": cand.candidate_id,
        "name": cand.name,
        "email": cand.email,
        "phone": cand.phone,
        "education": cand.education,
        "experience_years": cand.experience_years,
        "skills_extracted": cand.skills_extracted or [],
        "target_jd_id": cand.target_jd_id,
        "current_stage": cand.current_stage,
        "created_at": cand.created_at.isoformat() if cand.created_at else None
    }

class CandidateProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    phone: Optional[str] = None
    education: Optional[str] = None
    experience_years: Optional[float] = None
    skills_extracted: Optional[List[str]] = None

@router.put("/profile")
def update_my_profile(payload: CandidateProfileUpdateRequest, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Updates the authenticated candidate's profile information.
    Strictly isolated: only modifies the authenticated candidate's record.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    if payload.name is not None and payload.name.strip():
        cand.name = payload.name.strip()
    if payload.phone is not None:
        cand.phone = payload.phone.strip()
    if payload.education is not None:
        cand.education = payload.education.strip()
    if payload.experience_years is not None:
        cand.experience_years = float(payload.experience_years)
    if payload.skills_extracted is not None:
        cand.skills_extracted = payload.skills_extracted

    db.commit()
    db.refresh(cand)

    return {
        "candidate_id": cand.candidate_id,
        "name": cand.name,
        "email": cand.email,
        "phone": cand.phone,
        "education": cand.education,
        "experience_years": cand.experience_years,
        "skills_extracted": cand.skills_extracted or [],
        "target_jd_id": cand.target_jd_id,
        "current_stage": cand.current_stage,
        "created_at": cand.created_at.isoformat() if cand.created_at else None
    }

@router.get("/applications")
def get_my_applications(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Returns the authenticated candidate's application history and status.
    Strictly isolated: never exposes applications belonging to other candidates.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        return []

    jd = None
    if cand.target_jd_id:
        jd = db.query(JobDescription).filter(JobDescription.jd_id == cand.target_jd_id).first()

    return [{
        "candidate_id": cand.candidate_id,
        "jd_id": cand.target_jd_id,
        "job_title": jd.title if jd else "General Application",
        "department": jd.department if jd else "Engineering",
        "current_stage": cand.current_stage,
        "applied_date": cand.created_at.isoformat() if cand.created_at else None
    }]

@router.get("/jobs")
def get_open_jobs(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Returns available job openings for the candidate to browse and apply.
    """
    jobs = db.query(JobDescription).all()
    return [{
        "jd_id": j.jd_id,
        "title": j.title,
        "department": j.department,
        "description": j.description,
        "required_skills": j.required_skills or [],
        "preferred_skills": j.preferred_skills or [],
        "min_experience": j.min_experience,
        "education_requirement": j.education_requirement
    } for j in jobs]

@router.post("/apply")
def apply_to_job(payload: CandidateApplyRequest, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Applies for a job requisition. Enforces that the application is tied strictly
    to the authenticated candidate's ID.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")

    jd = db.query(JobDescription).filter(JobDescription.jd_id == payload.jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    cand.target_jd_id = jd.jd_id
    if payload.resume_text:
        cand.resume_text = payload.resume_text
    
    cand.current_stage = "RESUME_SCREENED"
    db.commit()

    # Trigger Resume Screener Agent for this candidate
    rubric = get_or_create_rubric(db, jd)
    screening_out = ResumeScreenerAgent.evaluate(
        cid, 
        cand.resume_text or "", 
        {k: v for k, v in jd.__dict__.items() if not k.startswith('_')}, 
        rubric.criteria
    )

    ATSTools.save_screening_result(
        db,
        candidate_id=cid,
        jd_id=jd.jd_id,
        score=screening_out.score,
        matched_requirements=screening_out.matched_requirements,
        missing_requirements=screening_out.missing_requirements,
        experience_match=screening_out.experience_match,
        evidence=screening_out.evidence,
        rubric_version=screening_out.rubric_version,
        status=screening_out.status
    )

    log_event(
        db,
        stage="RESUME_SCREENED",
        event=f"Candidate applied and resume screened for {jd.title}",
        agent="ResumeScreenerAgent",
        candidate_id=cid,
        input_reference={"jd_id": jd.jd_id},
        output=screening_out.model_dump(),
        rubric_version=screening_out.rubric_version
    )

    return {
        "status": "success",
        "message": f"Successfully applied to {jd.title}",
        "current_stage": cand.current_stage
    }

@router.get("/assessments")
def get_my_assessments(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Returns questions for the job assigned to this candidate.
    Only allows access to questions relevant to the authenticated candidate.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    jd = db.query(JobDescription).filter(JobDescription.jd_id == cand.target_jd_id).first()
    if not jd:
        # Fallback to first available JD if not explicitly set
        jd = db.query(JobDescription).first()

    tech_questions = generate_technical_questions_for_jd(jd) if jd else []
    beh_questions = generate_behavioral_questions_for_jd()

    # Check already completed assessments for this candidate
    completed_tech = db.query(Assessment).filter(
        Assessment.candidate_id == cid,
        Assessment.test_type == "TECHNICAL"
    ).first()
    completed_beh = db.query(Assessment).filter(
        Assessment.candidate_id == cid,
        Assessment.test_type == "BEHAVIORAL"
    ).first()

    return {
        "candidate_id": cid,
        "jd_id": jd.jd_id if jd else None,
        "job_title": jd.title if jd else "Technical Assessment",
        "technical": {
            "completed": completed_tech is not None,
            "questions": sanitize_questions_for_candidate(tech_questions)
        },
        "behavioral": {
            "completed": completed_beh is not None,
            "questions": sanitize_questions_for_candidate(beh_questions)
        }
    }

@router.post("/submit-technical")
def submit_my_technical_assessment(payload: CandidateSubmitAssessment, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Submits technical answers. Strictly binds the candidate_id to auth_user.
    Prevents repeated retakes/score grinding once submitted.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    existing_tech = db.query(Assessment).filter(
        Assessment.candidate_id == cid,
        Assessment.test_type == "TECHNICAL"
    ).first()
    if existing_tech:
        raise HTTPException(
            status_code=400,
            detail="Technical assessment has already been submitted and finalized for this application."
        )

    jd_id = payload.jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        jd = db.query(JobDescription).first()

    questions = generate_technical_questions_for_jd(jd)
    answers_dict = [{"question_id": a.question_id, "answer_text": a.answer_text} for a in payload.answers]

    # Evaluate with SkillAssessorAgent
    skill_out = SkillAssessorAgent.evaluate(cid, jd.__dict__, questions, answers_dict)

    ATSTools.save_assessment_result(
        db,
        candidate_id=cid,
        jd_id=jd.jd_id,
        test_type="TECHNICAL",
        questions=questions,
        answers=answers_dict,
        score=skill_out.score,
        skill_breakdown=skill_out.skill_breakdown,
        evidence=skill_out.evidence,
        confidence=skill_out.confidence,
        status=skill_out.status
    )

    log_event(
        db,
        stage="TECHNICAL_ASSESSED",
        event="Candidate Completed Technical Assessment via Portal",
        agent="SkillAssessorAgent",
        candidate_id=cid,
        input_reference={"jd_id": jd.jd_id, "answer_count": len(answers_dict)},
        output=skill_out.model_dump(),
        rubric_version="1.0"
    )

    return {
        "status": "COMPLETED",
        "message": "Technical assessment submitted and received successfully."
    }

@router.post("/submit-behavioral")
def submit_my_behavioral_assessment(payload: CandidateSubmitAssessment, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Submits behavioral answers. Strictly binds the candidate_id to auth_user.
    Prevents repeated retakes/score grinding once submitted.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    existing_beh = db.query(Assessment).filter(
        Assessment.candidate_id == cid,
        Assessment.test_type == "BEHAVIORAL"
    ).first()
    if existing_beh:
        raise HTTPException(
            status_code=400,
            detail="Behavioral assessment has already been submitted and finalized for this application."
        )

    jd_id = payload.jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        jd = db.query(JobDescription).first()

    questions = generate_behavioral_questions_for_jd(jd)
    answers_dict = [{"question_id": a.question_id, "answer_text": a.answer_text} for a in payload.answers]

    # Evaluate with CultureFitAgent
    culture_out = CultureFitAgent.evaluate(cid, jd.__dict__, questions, answers_dict)

    ATSTools.save_assessment_result(
        db,
        candidate_id=cid,
        jd_id=jd.jd_id,
        test_type="BEHAVIORAL",
        questions=questions,
        answers=answers_dict,
        score=culture_out.score,
        skill_breakdown=culture_out.breakdown,
        evidence=culture_out.evidence,
        confidence=culture_out.confidence,
        status=culture_out.status
    )

    log_event(
        db,
        stage="BEHAVIORAL_ASSESSED",
        event="Candidate Completed Behavioral Assessment via Portal",
        agent="CultureFitAgent",
        candidate_id=cid,
        input_reference={"jd_id": jd.jd_id, "answer_count": len(answers_dict)},
        output=culture_out.model_dump(),
        rubric_version="1.0"
    )

    return {
        "status": "COMPLETED",
        "message": "Behavioral assessment submitted and received successfully."
    }

@router.get("/timeline")
def get_my_timeline(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Returns candidate application timeline strictly for the authenticated candidate.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    stages_order = [
        {"id": "APPLIED", "label": "Application Submitted", "desc": "Profile and initial information ingested."},
        {"id": "RESUME_SCREENED", "label": "Resume Screening", "desc": "Qualifications evaluated against job requirements."},
        {"id": "TECHNICAL_ASSESSED", "label": "Technical Assessment", "desc": "Practical skills and problem-solving evaluated."},
        {"id": "BEHAVIORAL_ASSESSED", "label": "Behavioral Assessment", "desc": "STAR competency and culture alignment evaluated."},
        {"id": "PANEL_EVALUATED", "label": "Panel Review", "desc": "Multi-agent committee synthesized scores and evidence."},
        {"id": "HUMAN_REVIEW_PENDING", "label": "Human Review", "desc": "Final review dossier inspected by Talent Team."},
        {"id": "DECIDED", "label": "Decision Finalized", "desc": "Hiring decision signed off by Human Reviewer."}
    ]

    current_idx = 0
    stage_keys = [s["id"] for s in stages_order]
    if cand.current_stage in stage_keys:
        current_idx = stage_keys.index(cand.current_stage)

    timeline_items = []
    for i, s in enumerate(stages_order):
        if i < current_idx:
            status = "COMPLETED"
        elif i == current_idx:
            status = "CURRENT"
        else:
            status = "UPCOMING"
        timeline_items.append({
            "stage": s["id"],
            "label": s["label"],
            "description": s["desc"],
            "status": status
        })

    return {
        "candidate_id": cid,
        "current_stage": cand.current_stage,
        "timeline": timeline_items
    }

@router.get("/explanation")
def get_candidate_transparency_explanation(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Candidate Rights & Transparency Disclosure (NYC Local Law 144 & EU AI Act Art. 14):
    Provides a clear, plain-language explanation of how automated screening assists human evaluators,
    the rubric dimensions assessed, blind screening protections, and the right to request human re-review.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    jd = db.query(JobDescription).filter(JobDescription.jd_id == cand.target_jd_id).first() if cand.target_jd_id else None

    return {
        "candidate_id": cid,
        "applicant_name": cand.name,
        "target_role": jd.title if jd else "Applied Role",
        "current_stage": cand.current_stage,
        "governance_guarantee": {
            "autonomous_decisions_prohibited": True,
            "human_in_the_loop_mandatory": True,
            "summary": "JASIPA operates under strict AI governance: AI models evaluate qualifications against job rubrics, but AI is STRICTLY PROHIBITED from autonomously rejecting or hiring you. Every hiring outcome is finalized by human HR talent leads."
        },
        "evaluation_methodology": {
            "blind_screening_mode": "Active (emails, phone numbers, and portfolio links are redacted prior to AI evaluation to prevent demographic bias)",
            "rubric_anchoring": "Scores are calculated strictly against transparent, documented job requirements, not subjective impressions.",
            "components": [
                {"name": "Resume Experience Match", "weight": "40%", "description": "Verification of required skills and years of relevant experience."},
                {"name": "Technical Assessment", "weight": "40%", "description": "Practical problem-solving, algorithms, and domain knowledge."},
                {"name": "Behavioral Competency", "weight": "20%", "description": "STAR-method structured interview evaluating teamwork and communication."}
            ]
        },
        "candidate_rights": {
            "right_to_explanation": True,
            "right_to_human_re_review": True,
            "appeal_process": "You may request an expedited independent human re-review at any time using the re-review action."
        }
    }

@router.post("/request-re-review")
def request_human_re_review(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """
    Invokes candidate right to appeal / request human re-review under NYC LL 144 / EU AI Act.
    Logs an immutable audit event and transitions candidate current_stage to HUMAN_REVIEW_PENDING for immediate HR inspection.
    """
    cid = auth_user["candidate_id"]
    cand = db.query(Candidate).filter(Candidate.candidate_id == cid).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")

    cand.current_stage = "HUMAN_REVIEW_PENDING"
    db.commit()

    log_event(
        db,
        stage="HUMAN_REVIEW_PENDING",
        event="Candidate Formally Requested Human Re-Review (NYC LL 144 / EU AI Act Appeal)",
        agent="HUMAN_CANDIDATE_APPEAL",
        candidate_id=cid,
        input_reference={"request_type": "EXPEDITED_HUMAN_RE_REVIEW"},
        output={"status": "APPEAL_LOGGED", "appeal_timestamp": datetime.utcnow().isoformat()}
    )

    return {
        "status": "SUCCESS",
        "message": "Your request for human re-review has been formally recorded and logged to the tamper-evident audit ledger. Your application has been placed in the Human Review Docket for expedited inspection.",
        "candidate_id": cid
    }
