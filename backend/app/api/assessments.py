from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.database.session import get_db
from app.database.models import Candidate, JobDescription, Assessment
from app.schemas.assessment import (
    TechnicalAssessmentSubmit, BehavioralAssessmentSubmit, 
    SkillAssessorOutput, CultureFitOutput, AssessmentResponse
)
from app.services.assessment_service import (
    generate_technical_questions_for_jd, 
    generate_behavioral_questions_for_jd,
    sanitize_questions_for_candidate
)
from app.agents.skill_assessor import SkillAssessorAgent
from app.agents.culture_fit import CultureFitAgent
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.auth.security import require_hr, get_current_user

router = APIRouter(prefix="/assessments", tags=["Assessments"])

@router.get("/questions/technical/{jd_id}")
def get_technical_questions(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    questions = generate_technical_questions_for_jd(jd)
    return {"jd_id": jd_id, "test_type": "TECHNICAL", "questions": sanitize_questions_for_candidate(questions)}

@router.get("/questions/behavioral/{jd_id}")
def get_behavioral_questions(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    questions = generate_behavioral_questions_for_jd(jd)
    return {"jd_id": jd_id, "test_type": "BEHAVIORAL", "questions": sanitize_questions_for_candidate(questions)}

@router.post("/submit/technical", response_model=SkillAssessorOutput)
def submit_technical_assessment(
    payload: TechnicalAssessmentSubmit, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    cand = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    jd = db.query(JobDescription).filter(JobDescription.jd_id == payload.jd_id).first()
    if not cand or not jd:
        raise HTTPException(status_code=404, detail="Candidate or JD not found")

    questions = generate_technical_questions_for_jd(jd)
    answers_dict = [{"question_id": a.question_id, "answer_text": a.answer_text} for a in payload.answers]

    # Evaluate with SkillAssessorAgent
    skill_out = SkillAssessorAgent.evaluate(cand.candidate_id, jd.__dict__, questions, answers_dict)

    # Save through ATS Tool
    ATSTools.save_assessment_result(
        db,
        candidate_id=cand.candidate_id,
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
        event="Candidate Submitted Technical Assessment",
        agent="SkillAssessorAgent",
        candidate_id=cand.candidate_id,
        input_reference={"jd_id": jd.jd_id, "answer_count": len(payload.answers)},
        output=skill_out.model_dump(),
        rubric_version=jd.rubric_version
    )

    return skill_out

@router.post("/submit/behavioral", response_model=CultureFitOutput)
def submit_behavioral_assessment(
    payload: BehavioralAssessmentSubmit, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    cand = db.query(Candidate).filter(Candidate.candidate_id == payload.candidate_id).first()
    jd = db.query(JobDescription).filter(JobDescription.jd_id == payload.jd_id).first()
    if not cand or not jd:
        raise HTTPException(status_code=404, detail="Candidate or JD not found")

    questions = generate_behavioral_questions_for_jd(jd)
    answers_dict = [{"question_id": a.question_id, "answer_text": a.answer_text} for a in payload.answers]

    # Evaluate with CultureFitAgent
    culture_out = CultureFitAgent.evaluate(cand.candidate_id, jd.__dict__, questions, answers_dict)

    # Save through ATS Tool
    ATSTools.save_assessment_result(
        db,
        candidate_id=cand.candidate_id,
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
        event="Candidate Submitted Behavioral Assessment",
        agent="CultureFitAgent",
        candidate_id=cand.candidate_id,
        input_reference={"jd_id": jd.jd_id, "answer_count": len(payload.answers)},
        output=culture_out.model_dump(),
        rubric_version=jd.rubric_version
    )

    return culture_out

@router.get("/candidate/{candidate_id}", response_model=List[AssessmentResponse])
def get_candidate_assessments(
    candidate_id: str, 
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Strict candidate data isolation: candidate can only view their own assessments
    if current_user.get("role") != "HR" and current_user.get("candidate_id") != candidate_id:
        raise HTTPException(
            status_code=403, 
            detail="Access forbidden: You cannot view assessments belonging to another candidate."
        )
    return db.query(Assessment).filter(Assessment.candidate_id == candidate_id).all()
