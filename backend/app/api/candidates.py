from typing import List, Optional

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.auth import normalize_email
from app.auth.security import require_hr
from app.config import settings
from app.database.models import Candidate, JobDescription
from app.database.session import get_db
from app.schemas.candidate import CandidateCreate, CandidateDetailResponse, CandidateResponse, CandidateUpdate
from app.services.audit_service import log_event
from app.services.pipeline_service import screen_candidate
from app.services.resume_parser import ResumeFileError, extract_preliminary_metadata, text_hash
from app.services.resume_service import ingest_resume, resume_file_path

router = APIRouter(prefix="/candidates", tags=["Candidates"])

LOCKED_STAGES = {"PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING", "INFO_REQUESTED", "DECIDED"}


def _actor(user: dict) -> str:
    return f"HR ({user.get('name') or user.get('email')})"


def _valid_jd(db: Session, jd_id: Optional[str]) -> Optional[str]:
    if not jd_id:
        return None
    if not db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first():
        raise HTTPException(status_code=422, detail="Selected job does not exist.")
    return jd_id


def _clean_cohort(value: Optional[str]) -> Optional[str]:
    value = (value or "").strip()
    return value[:80] or None


@router.post("/", response_model=CandidateResponse, status_code=201)
def create_candidate(payload: CandidateCreate, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    try:
        email = normalize_email(payload.email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    if db.query(Candidate).filter(Candidate.email == email).first():
        raise HTTPException(status_code=409, detail="A candidate with this email already exists.")
    meta = extract_preliminary_metadata(payload.resume_text or "") if payload.resume_text else None
    candidate = Candidate(
        name=" ".join(payload.name.split()), email=email, phone=payload.phone, cohort_tag=_clean_cohort(payload.cohort_tag),
        resume_text=payload.resume_text, resume_hash=text_hash(payload.resume_text),
        skills_extracted=(meta["skills"] if meta else []), resume_profile=(meta["profile"] if meta else {}),
        experience_years=payload.experience_years or (meta["experience_years"] if meta else 0.0),
        education=payload.education or (meta["education"] if meta else None),
        target_jd_id=_valid_jd(db, payload.target_jd_id), current_stage="APPLIED")
    db.add(candidate)
    db.commit()
    db.refresh(candidate)
    log_event(db, stage="APPLIED", event="Candidate record created by HR", agent=_actor(current_user),
              candidate_id=candidate.candidate_id, input_reference={"target_jd_id": candidate.target_jd_id})
    return candidate


@router.post("/upload-resume", response_model=CandidateResponse)
async def upload_candidate_resume(
    name: str = Form(..., min_length=2, max_length=120),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    cohort_tag: Optional[str] = Form(None),
    target_jd_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    """Creates a candidate from a PDF/DOCX resume, or replaces the resume of an existing candidate with this email."""
    try:
        email = normalize_email(email)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc))
    target_jd_id = _valid_jd(db, target_jd_id)
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    created = candidate is None
    if candidate and candidate.current_stage in LOCKED_STAGES:
        raise HTTPException(status_code=409, detail="This candidate is already under panel review; their resume can no longer be replaced.")
    if created:
        candidate = Candidate(name=" ".join(name.split()), email=email, phone=phone, cohort_tag=_clean_cohort(cohort_tag),
                              target_jd_id=target_jd_id, current_stage="APPLIED", skills_extracted=[], resume_profile={})
        db.add(candidate)
    else:
        candidate.name = " ".join(name.split())
        candidate.phone = phone or candidate.phone
        candidate.cohort_tag = _clean_cohort(cohort_tag) or candidate.cohort_tag
        candidate.target_jd_id = target_jd_id or candidate.target_jd_id

    data = await file.read(settings.MAX_RESUME_BYTES + 1)
    try:
        parsed = ingest_resume(db, candidate, file.filename or "", data)
    except ResumeFileError as exc:
        db.rollback()
        raise HTTPException(status_code=422, detail=str(exc))
    db.commit()
    db.refresh(candidate)
    log_event(db, stage=candidate.current_stage, event="Resume uploaded by HR" + (" (new candidate)" if created else ""),
              agent=_actor(current_user), candidate_id=candidate.candidate_id,
              input_reference={"format": parsed["format"], "size_bytes": len(data)},
              output={"parse_status": parsed["status"], "confidence": parsed["confidence"],
                      "skills": parsed["profile"].get("skills", [])})
    if candidate.target_jd_id and candidate.current_stage != "MANUAL_REVIEW_REQUIRED":
        screen_candidate(db, candidate, actor=current_user["email"])
        db.refresh(candidate)
    return candidate


@router.get("/{candidate_id}/resume")
def download_resume(candidate_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    path = resume_file_path(cand) if cand else None
    if not path:
        raise HTTPException(status_code=404, detail="No resume file is stored for this candidate.")
    media = "application/pdf" if path.endswith(".pdf") else "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    log_event(db, stage=cand.current_stage, event="Resume file accessed", agent=_actor(current_user), candidate_id=cand.candidate_id)
    return FileResponse(path, media_type=media, filename=cand.resume_original_filename or f"resume.{path.rsplit('.', 1)[-1]}")


@router.get("/", response_model=List[CandidateResponse])
def list_candidates(stage: Optional[str] = None, jd_id: Optional[str] = None,
                    current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    query = db.query(Candidate)
    if stage:
        query = query.filter(Candidate.current_stage.in_(stage.split(",")))
    if jd_id:
        query = query.filter(Candidate.target_jd_id == jd_id)
    return query.order_by(Candidate.created_at.desc()).all()


@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_details(candidate_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Full evaluation dossier. HR only: it contains answer keys, scores and bias analysis."""
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand


@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(candidate_id: str, payload: CandidateUpdate, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    update_data = payload.model_dump(exclude_unset=True)

    if "current_stage" in update_data:
        # Stages are driven by the pipeline. HR may only release a resume that needed manual review.
        if not (cand.current_stage == "MANUAL_REVIEW_REQUIRED" and update_data["current_stage"] == "APPLIED"):
            raise HTTPException(status_code=400, detail="Pipeline stages cannot be edited directly. Final decisions are recorded through the decision workflow.")
    if "email" in update_data:
        try:
            update_data["email"] = normalize_email(update_data["email"])
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc))
        if db.query(Candidate).filter(Candidate.email == update_data["email"], Candidate.candidate_id != cand.candidate_id).first():
            raise HTTPException(status_code=409, detail="Another candidate already uses this email.")
    if "resume_text" in update_data and cand.current_stage in LOCKED_STAGES:
        raise HTTPException(status_code=409, detail="Resume text cannot change while the candidate is under panel review.")
    if "target_jd_id" in update_data:
        if cand.current_stage in LOCKED_STAGES:
            raise HTTPException(status_code=409, detail="The target job cannot change while the candidate is under panel review.")
        update_data["target_jd_id"] = _valid_jd(db, update_data["target_jd_id"])
    if "cohort_tag" in update_data:
        update_data["cohort_tag"] = _clean_cohort(update_data["cohort_tag"])

    for key, value in update_data.items():
        setattr(cand, key, value)
    if "resume_text" in update_data:
        cand.resume_hash = text_hash(cand.resume_text)
    db.commit()
    db.refresh(cand)
    log_event(db, stage=cand.current_stage, event="Candidate record updated by HR", agent=_actor(current_user),
              candidate_id=cand.candidate_id, input_reference={"updated_fields": sorted(update_data.keys())})
    return cand
