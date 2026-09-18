from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.database.models import JobDescription, Rubric
from app.schemas.job import JobDescriptionCreate, JobDescriptionResponse, JobDescriptionUpdate
from app.schemas.rubric import RubricResponse
from app.services.rubric_service import get_or_create_rubric, generate_rubric_for_jd
from app.services.audit_service import log_event

router = APIRouter(prefix="/jobs", tags=["Job Descriptions"])

@router.post("/", response_model=JobDescriptionResponse)
def create_job_description(payload: JobDescriptionCreate, db: Session = Depends(get_db)):
    jd = JobDescription(
        title=payload.title,
        department=payload.department,
        description=payload.description,
        required_skills=payload.required_skills,
        preferred_skills=payload.preferred_skills,
        min_experience=payload.min_experience,
        education_requirement=payload.education_requirement,
        rubric_version="1.0"
    )
    db.add(jd)
    db.commit()
    db.refresh(jd)

    # Automatically generate anchored rubric
    rubric = get_or_create_rubric(db, jd)

    log_event(
        db,
        stage="JD_CREATED",
        event=f"Job Description Created: {jd.title}",
        agent="HR_ADMIN",
        input_reference={"jd_id": jd.jd_id, "title": jd.title},
        output={"rubric_version": rubric.version, "criteria": rubric.criteria},
        rubric_version=rubric.version
    )

    return jd

@router.get("/", response_model=List[JobDescriptionResponse])
def list_job_descriptions(db: Session = Depends(get_db)):
    return db.query(JobDescription).order_by(JobDescription.created_at.desc()).all()

@router.get("/{jd_id}", response_model=JobDescriptionResponse)
def get_job_description(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd

@router.get("/{jd_id}/rubric", response_model=RubricResponse)
def get_job_rubric(jd_id: str, db: Session = Depends(get_db)):
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    rubric = get_or_create_rubric(db, jd)
    return rubric
