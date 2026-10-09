import os
import shutil
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Form
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database.session import get_db
from app.database.models import Candidate, JobDescription
from app.schemas.candidate import CandidateCreate, CandidateResponse, CandidateDetailResponse, CandidateUpdate
from app.services.resume_parser import extract_text_from_pdf, extract_preliminary_metadata
from app.services.audit_service import log_event
from app.config import settings
from app.auth.security import get_current_user, require_hr

router = APIRouter(prefix="/candidates", tags=["Candidates"])

@router.post("/", response_model=CandidateResponse)
def create_candidate(
    payload: CandidateCreate, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    # Extract preliminary skills if resume provided
    skills = payload.skills_extracted or []
    if payload.resume_text and not skills:
        meta = extract_preliminary_metadata(payload.resume_text)
        skills = meta["skills"]
        if not payload.experience_years:
            payload.experience_years = meta["experience_years"]
        if not payload.education:
            payload.education = meta["education"]

    candidate = Candidate(
        name=payload.name,
        email=payload.email,
        phone=payload.phone,
        cohort_tag=payload.cohort_tag or "General Cohort",
        resume_text=payload.resume_text,
        skills_extracted=skills,
        experience_years=payload.experience_years or 0.0,
        education=payload.education,
        target_jd_id=payload.target_jd_id,
        current_stage="APPLIED"
    )
    db.add(candidate)
    db.commit()
    db.refresh(candidate)

    log_event(
        db,
        stage="APPLIED",
        event=f"Candidate Application Created by HR: {candidate.name}",
        agent=f"HR_ADMIN ({current_user.get('name', 'Talent Team')})",
        candidate_id=candidate.candidate_id,
        input_reference={"email": candidate.email, "target_jd_id": candidate.target_jd_id},
        output={"current_stage": candidate.current_stage}
    )

    return candidate

@router.post("/upload-resume", response_model=CandidateResponse)
async def upload_candidate_resume(
    name: str = Form(...),
    email: str = Form(...),
    phone: Optional[str] = Form(None),
    cohort_tag: Optional[str] = Form("General Cohort"),
    target_jd_id: Optional[str] = Form(None),
    file: UploadFile = File(...),
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    # Validate PDF
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF resume files are supported.")
    
    file_bytes = await file.read()
    
    # Save file to disk
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    saved_path = os.path.join(settings.UPLOAD_DIR, f"{email}_{file.filename}")
    with open(saved_path, "wb") as f:
        f.write(file_bytes)

    # Extract text with PyMuPDF
    parsed = extract_text_from_pdf(file_bytes)
    resume_text = parsed["text"]
    meta = extract_preliminary_metadata(resume_text)

    # Check for existing candidate or create
    candidate = db.query(Candidate).filter(Candidate.email == email).first()
    if not candidate:
        candidate = Candidate(
            name=name,
            email=email,
            phone=phone,
            cohort_tag=cohort_tag or "General Cohort",
            resume_text=resume_text,
            resume_file_path=saved_path,
            skills_extracted=meta["skills"],
            experience_years=meta["experience_years"],
            education=meta["education"],
            target_jd_id=target_jd_id,
            current_stage="APPLIED" if parsed["status"] != "MANUAL_REVIEW_REQUIRED" else "MANUAL_REVIEW_REQUIRED"
        )
        db.add(candidate)
    else:
        candidate.name = name
        candidate.phone = phone or candidate.phone
        candidate.cohort_tag = cohort_tag or candidate.cohort_tag
        candidate.resume_text = resume_text
        candidate.resume_file_path = saved_path
        candidate.skills_extracted = meta["skills"]
        candidate.experience_years = meta["experience_years"]
        candidate.education = meta["education"]
        candidate.target_jd_id = target_jd_id or candidate.target_jd_id

    db.commit()
    db.refresh(candidate)

    log_event(
        db,
        stage="APPLIED",
        event=f"Resume Uploaded and Processed: {file.filename}",
        agent="ResumeParserService",
        candidate_id=candidate.candidate_id,
        input_reference={"filename": file.filename, "size_bytes": len(file_bytes)},
        output={"parsing_status": parsed["status"], "confidence": parsed["confidence"], "skills": meta["skills"]}
    )

    return candidate

@router.get("/", response_model=List[CandidateResponse])
def list_candidates(
    stage: Optional[str] = None,
    jd_id: Optional[str] = None,
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    query = db.query(Candidate)
    if stage:
        query = query.filter(Candidate.current_stage == stage)
    if jd_id:
        query = query.filter(Candidate.target_jd_id == jd_id)
    return query.order_by(Candidate.created_at.desc()).all()

@router.get("/{candidate_id}", response_model=CandidateDetailResponse)
def get_candidate_details(
    candidate_id: str,
    current_user: dict = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # Enforce strict candidate data isolation:
    # If the user is a Candidate, they can ONLY view their own candidate_id
    if current_user.get("role") != "HR" and current_user.get("candidate_id") != candidate_id:
        raise HTTPException(
            status_code=403, 
            detail="Access forbidden: You cannot view records belonging to another candidate."
        )

    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand

@router.patch("/{candidate_id}", response_model=CandidateResponse)
def update_candidate(
    candidate_id: str, 
    payload: CandidateUpdate, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    update_data = payload.model_dump(exclude_unset=True)

    if "current_stage" in update_data:
        target_stage = update_data["current_stage"]
        if target_stage == "DECIDED":
            raise HTTPException(
                status_code=400,
                detail="Direct stage update to 'DECIDED' is prohibited. Final hiring decisions must go through the Human Review governance process (/reviews/decide)."
            )
        allowed_stages = [
            "APPLIED", "RESUME_SCREENED", "TECHNICAL_ASSESSED", 
            "BEHAVIORAL_ASSESSED", "PANEL_EVALUATED", "HUMAN_REVIEW_PENDING", 
            "MANUAL_REVIEW_REQUIRED"
        ]
        if target_stage not in allowed_stages:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid stage '{target_stage}'. Must be one of: {', '.join(allowed_stages)}"
            )

    for key, value in update_data.items():
        setattr(cand, key, value)

    db.commit()
    db.refresh(cand)

    log_event(
        db,
        stage=cand.current_stage,
        event=f"Candidate Profile Updated by HR: {cand.name}",
        agent=f"HR_ADMIN ({current_user.get('name', 'Talent Team')})",
        candidate_id=cand.candidate_id,
        input_reference={"updated_fields": list(update_data.keys())},
        output={"current_stage": cand.current_stage}
    )

    return cand
