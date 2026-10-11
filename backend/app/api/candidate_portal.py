"""Candidate self-service portal. Every query is scoped to the authenticated candidate's own record."""
import threading
from collections import defaultdict
from typing import Dict, List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth.security import require_candidate
from app.config import settings
from app.database.models import Assessment, Candidate, JobDescription
from app.database.session import get_db
from app.schemas.assessment import AnswerItem
from app.services.assessment_service import find_question, question_set_for_candidate, sanitize_questions_for_candidate, submit_assessment
from app.services.audit_service import log_event
from app.services.code_sandbox import candidate_view, run_python_tests
from app.services.pipeline_service import screen_candidate
from app.services.resume_parser import ResumeFileError
from app.services.resume_service import ingest_resume, resume_file_path

router = APIRouter(prefix="/candidate", tags=["Candidate Portal"])

# Stages after which the evidence used for the panel must not change underneath it.
LOCKED_STAGES = {"PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING", "INFO_REQUESTED", "DECIDED"}
_sample_runs: Dict[str, int] = defaultdict(int)
_sample_lock = threading.Lock()


class CandidateApplyRequest(BaseModel):
    jd_id: str


class CandidateSubmitAssessment(BaseModel):
    answers: List[AnswerItem] = Field(max_length=30)


class RunCodeRequest(BaseModel):
    question_id: str
    code: str = Field(max_length=20000)


class CandidateProfileUpdateRequest(BaseModel):
    name: Optional[str] = Field(None, max_length=120)
    phone: Optional[str] = Field(None, max_length=40)


def _me(db: Session, auth_user: dict) -> Candidate:
    cand = db.query(Candidate).filter(Candidate.candidate_id == auth_user["candidate_id"]).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate profile not found")
    return cand


def _profile(cand: Candidate) -> dict:
    return {
        "candidate_id": cand.candidate_id, "name": cand.name, "email": cand.email, "phone": cand.phone,
        "education": cand.education, "experience_years": cand.experience_years,
        "skills_extracted": cand.skills_extracted or [], "resume_profile": cand.resume_profile or {},
        "resume_filename": cand.resume_original_filename, "has_resume": bool(cand.resume_text),
        "has_original_file": resume_file_path(cand) is not None,
        "resume_sections": cand.resume_sections, "resume_text": cand.resume_text,
        "target_jd_id": cand.target_jd_id, "current_stage": cand.current_stage,
        "created_at": cand.created_at.isoformat() if cand.created_at else None,
    }


def _target_jd(db: Session, cand: Candidate) -> JobDescription:
    jd = db.query(JobDescription).filter(JobDescription.jd_id == cand.target_jd_id).first() if cand.target_jd_id else None
    if not jd:
        raise HTTPException(status_code=400, detail="Apply to a job before taking assessments.")
    return jd


@router.get("/me")
def get_my_profile(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    return _profile(_me(db, auth_user))


@router.put("/profile")
def update_my_profile(payload: CandidateProfileUpdateRequest, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """Contact details only. Skills, education and experience come from the uploaded resume so they match the evidence screened."""
    cand = _me(db, auth_user)
    if payload.name is not None:
        name = " ".join(payload.name.split())
        if len(name) < 2:
            raise HTTPException(status_code=422, detail="Name must have at least 2 characters.")
        cand.name = name
    if payload.phone is not None:
        cand.phone = payload.phone.strip() or None
    db.commit()
    return _profile(cand)


@router.post("/upload-resume")
async def upload_my_resume(file: UploadFile = File(...), auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _me(db, auth_user)
    if cand.current_stage in LOCKED_STAGES:
        raise HTTPException(status_code=409, detail="Your application is already under panel review, so your resume can no longer be changed. Contact the recruiter if something is wrong.")
    data = await file.read(settings.MAX_RESUME_BYTES + 1)
    try:
        parsed = ingest_resume(db, cand, file.filename or "", data)
    except ResumeFileError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    log_event(db, stage=cand.current_stage, event="Candidate uploaded a resume", agent="ResumeParserService",
              candidate_id=cand.candidate_id, input_reference={"format": parsed["format"], "size_bytes": len(data)},
              output={"parse_status": parsed["status"], "confidence": parsed["confidence"],
                      "skills_found": len(parsed["profile"].get("skills", []))})
    # An active application is re-screened so the panel always sees the current resume.
    if cand.target_jd_id and cand.current_stage in ("APPLIED", "RESUME_SCREENED", "TECHNICAL_ASSESSED", "BEHAVIORAL_ASSESSED"):
        screen_candidate(db, cand, actor="candidate")
    return {"profile": _profile(cand), "parse_status": parsed["status"]}


@router.get("/resume")
def download_my_resume(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """The original file the candidate uploaded, exactly as received."""
    cand = _me(db, auth_user)
    path = resume_file_path(cand)
    if not path:
        raise HTTPException(status_code=404, detail="No uploaded resume file is stored for your profile.")
    media = "application/pdf" if path.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    return FileResponse(path, media_type=media, filename=cand.resume_original_filename or f"resume.{path.rsplit('.', 1)[-1]}")


@router.get("/applications")
def get_my_applications(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _me(db, auth_user)
    if not cand.target_jd_id:
        return []
    jd = db.query(JobDescription).filter(JobDescription.jd_id == cand.target_jd_id).first()
    return [{"candidate_id": cand.candidate_id, "jd_id": cand.target_jd_id, "job_title": jd.title if jd else "Unknown role",
             "department": jd.department if jd else None, "current_stage": cand.current_stage,
             "applied_date": cand.created_at.isoformat() if cand.created_at else None}]


@router.get("/jobs")
def get_open_jobs(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    jobs = db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()
    return [{"jd_id": j.jd_id, "title": j.title, "department": j.department, "description": j.description,
             "required_skills": j.required_skills or [], "preferred_skills": j.preferred_skills or [],
             "min_experience": j.min_experience, "education_requirement": j.education_requirement} for j in jobs]


@router.post("/apply")
def apply_to_job(payload: CandidateApplyRequest, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _me(db, auth_user)
    jd = db.query(JobDescription).filter(JobDescription.jd_id == payload.jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job not found")
    if cand.target_jd_id and cand.current_stage not in ("REGISTERED", "APPLIED", "MANUAL_REVIEW_REQUIRED"):
        raise HTTPException(status_code=409, detail="You already have an application in progress. Contact the recruiter to change roles.")
    if not cand.resume_text or len(cand.resume_text.strip()) < 50:
        raise HTTPException(status_code=422, detail="Upload your resume (PDF or DOCX) before applying.")

    cand.target_jd_id = jd.jd_id
    if cand.current_stage in (None, "REGISTERED", "MANUAL_REVIEW_REQUIRED"):
        cand.current_stage = "APPLIED"
    db.commit()
    log_event(db, stage="APPLIED", event=f"Candidate applied for {jd.title}", agent="CandidatePortal",
              candidate_id=cand.candidate_id, input_reference={"jd_id": jd.jd_id})
    screen_candidate(db, cand, jd, actor="candidate")
    # Generate (or load) the role's question set now and pin it to this applicant.
    cand.assigned_question_set_id = None
    question_set_for_candidate(db, cand, jd)
    return {"status": "success", "message": f"Application submitted for {jd.title}.", "current_stage": cand.current_stage}


@router.get("/assessments")
def get_my_assessments(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _me(db, auth_user)
    if not cand.target_jd_id:
        return {"candidate_id": cand.candidate_id, "jd_id": None, "job_title": None, "available": False,
                "technical": {"completed": False, "questions": []}, "behavioral": {"completed": False, "questions": []}}
    jd = _target_jd(db, cand)
    question_set = question_set_for_candidate(db, cand, jd)

    def completed(test_type: str) -> bool:
        return db.query(Assessment).filter(Assessment.candidate_id == cand.candidate_id, Assessment.jd_id == jd.jd_id,
                                           Assessment.test_type == test_type).first() is not None

    return {
        "candidate_id": cand.candidate_id, "jd_id": jd.jd_id, "job_title": jd.title, "available": True,
        "technical": {"completed": completed("TECHNICAL"), "questions": sanitize_questions_for_candidate(question_set.technical_questions)},
        "behavioral": {"completed": completed("BEHAVIORAL"), "questions": sanitize_questions_for_candidate(question_set.behavioral_questions)},
    }


@router.post("/assessments/run-code")
def run_sample_tests(payload: RunCodeRequest, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    """Runs the candidate's draft against the visible example tests only. Not scored or stored."""
    cand = _me(db, auth_user)
    jd = _target_jd(db, cand)
    question = find_question(question_set_for_candidate(db, cand, jd).technical_questions, payload.question_id)
    if not question or question.get("type") != "coding":
        raise HTTPException(status_code=404, detail="Coding question not found")
    key = f"{cand.candidate_id}:{payload.question_id}"
    with _sample_lock:
        if _sample_runs[key] >= settings.SANDBOX_SAMPLE_RUNS_PER_QUESTION:
            raise HTTPException(status_code=429, detail="You have reached the limit of practice runs for this question.")
        _sample_runs[key] += 1
        remaining = settings.SANDBOX_SAMPLE_RUNS_PER_QUESTION - _sample_runs[key]
    visible = [t for t in question["coding"].get("tests", []) if not t.get("hidden")]
    result = run_python_tests(payload.code, question["coding"]["function_name"], visible)
    return {**candidate_view(result, visible), "runs_remaining": remaining}


def _submit(test_type: str, payload: CandidateSubmitAssessment, auth_user: dict, db: Session):
    cand = _me(db, auth_user)
    jd = _target_jd(db, cand)
    exists = db.query(Assessment).filter(Assessment.candidate_id == cand.candidate_id, Assessment.jd_id == jd.jd_id,
                                         Assessment.test_type == test_type).first()
    if exists:
        raise HTTPException(status_code=409, detail=f"Your {test_type.lower()} assessment has already been submitted.")
    try:
        submit_assessment(db, cand, jd, test_type, [a.model_dump() for a in payload.answers])
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    return {"status": "RECEIVED", "message": f"Your {test_type.lower()} assessment was submitted."}


@router.post("/submit-technical")
def submit_my_technical_assessment(payload: CandidateSubmitAssessment, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    return _submit("TECHNICAL", payload, auth_user, db)


@router.post("/submit-behavioral")
def submit_my_behavioral_assessment(payload: CandidateSubmitAssessment, auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    return _submit("BEHAVIORAL", payload, auth_user, db)


TIMELINE = [
    ("APPLIED", "Application submitted"),
    ("RESUME_SCREENED", "Resume reviewed"),
    ("TECHNICAL_ASSESSED", "Technical assessment"),
    ("BEHAVIORAL_ASSESSED", "Behavioral assessment"),
    ("HUMAN_REVIEW_PENDING", "Hiring team review"),
    ("DECIDED", "Decision"),
]
STAGE_TO_STEP = {"REGISTERED": -1, "APPLIED": 0, "MANUAL_REVIEW_REQUIRED": 0, "RESUME_SCREENED": 1, "TECHNICAL_ASSESSED": 2,
                 "BEHAVIORAL_ASSESSED": 3, "PANEL_EVALUATED": 4, "BIAS_CHECKED": 4, "HUMAN_REVIEW_PENDING": 4,
                 "INFO_REQUESTED": 4, "DECIDED": 5}


@router.get("/timeline")
def get_my_timeline(auth_user: dict = Depends(require_candidate), db: Session = Depends(get_db)):
    cand = _me(db, auth_user)
    current = STAGE_TO_STEP.get(cand.current_stage, 0)
    items = [{"stage": stage, "label": label,
              "status": "COMPLETED" if i < current or (i == current and stage == "DECIDED") else "CURRENT" if i == current else "UPCOMING"}
             for i, (stage, label) in enumerate(TIMELINE)]
    return {"candidate_id": cand.candidate_id, "current_stage": cand.current_stage, "timeline": items,
            "info_requested": cand.current_stage == "INFO_REQUESTED"}
