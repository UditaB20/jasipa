from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List
from app.database.session import get_db
from app.database.models import JobDescription, Rubric
from app.schemas.job import JobDescriptionCreate, JobDescriptionResponse, JobDescriptionUpdate
from app.schemas.rubric import RubricResponse, RubricUpdate
from app.services.rubric_service import get_or_create_rubric, generate_rubric_for_jd
from app.services.audit_service import log_event
from app.auth.security import require_hr, get_current_user

router = APIRouter(prefix="/jobs", tags=["Job Descriptions"])

@router.post("/", response_model=JobDescriptionResponse)
def create_job_description(
    payload: JobDescriptionCreate, 
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
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

@router.put("/{jd_id}/rubric", response_model=RubricResponse)
def update_job_rubric(
    jd_id: str,
    payload: RubricUpdate,
    current_user: dict = Depends(require_hr),
    db: Session = Depends(get_db)
):
    """
    Allows authorized HR to customize the AI-generated scoring rubric, weights,
    and competency criteria for a specific job description.
    """
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")

    rubric = get_or_create_rubric(db, jd)

    # Validate weights if provided
    r_w = payload.resume_weight if payload.resume_weight is not None else rubric.resume_weight
    s_w = payload.skill_weight if payload.skill_weight is not None else rubric.skill_weight
    c_w = payload.culture_weight if payload.culture_weight is not None else rubric.culture_weight

    total_weight = round(r_w + s_w + c_w, 2)
    if not (0.98 <= total_weight <= 1.02):
        raise HTTPException(
            status_code=400, 
            detail=f"Total weights must sum to 1.0 (100%). Current sum: {total_weight}"
        )

    rubric.resume_weight = r_w
    rubric.skill_weight = s_w
    rubric.culture_weight = c_w

    if payload.criteria is not None:
        updated_criteria = dict(payload.criteria)

        # 1. Validate Technical Scoring criteria
        tech_crit = updated_criteria.get("technical_scoring")
        if tech_crit and isinstance(tech_crit, dict):
            threshold = tech_crit.get("passing_threshold")
            if threshold is not None:
                if not (0 <= float(threshold) <= 100):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Technical passing threshold must be between 0 and 100%. Current value: {threshold}%"
                    )
            
            mcq = tech_crit.get("mcq_weight")
            coding = tech_crit.get("coding_weight")
            sa = tech_crit.get("short_answer_weight")
            if mcq is not None and coding is not None and sa is not None:
                sub_sum = round(float(mcq) + float(coding) + float(sa), 2)
                if not (99 <= sub_sum <= 101):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Technical task sub-weights (MCQ {mcq}% + Coding {coding}% + Short Answer {sa}%) must sum to 100%. Current sum: {sub_sum}%"
                    )

        # 2. Validate Behavioral Competencies
        beh_crit = updated_criteria.get("behavioral_scoring")
        if beh_crit and isinstance(beh_crit, dict):
            competencies = beh_crit.get("competencies", [])
            if competencies:
                for c in competencies:
                    pts = float(c.get("max_points") or 0)
                    if pts <= 0:
                        raise HTTPException(
                            status_code=400,
                            detail=f"Each competency must have max_points > 0. Found '{c.get('competency')}' with {pts} pts."
                        )
                pts_sum = round(sum(float(c.get("max_points") or 0) for c in competencies), 2)
                if not (99 <= pts_sum <= 101):
                    raise HTTPException(
                        status_code=400,
                        detail=f"Behavioral competencies must sum to 100 points. Current sum: {pts_sum} pts across {len(competencies)} competencies."
                    )
                beh_crit["total_points"] = int(round(pts_sum))

        # Ensure top-level weights inside criteria match the model weights
        updated_criteria["weights"] = {
            "resume_fit": r_w,
            "technical_skill": s_w,
            "behavioral_fit": c_w
        }
        rubric.criteria = updated_criteria

    else:
        current_crit = dict(rubric.criteria or {})
        current_crit["weights"] = {
            "resume_fit": r_w,
            "technical_skill": s_w,
            "behavioral_fit": c_w
        }
        rubric.criteria = current_crit

    # Increment or set version
    if payload.version:
        rubric.version = payload.version
    else:
        try:
            cur_v = float(rubric.version)
            rubric.version = f"{cur_v + 0.1:.1f}"
        except Exception:
            rubric.version = f"{rubric.version}.1"

    jd.rubric_version = rubric.version

    db.commit()
    db.refresh(rubric)

    log_event(
        db,
        stage="JD_RUBRIC_UPDATED",
        event=f"Job Rubric Customized by HR: {jd.title} (v{rubric.version})",
        agent=f"HR_ADMIN ({current_user.get('name', 'Talent Team')})",
        candidate_id=None,
        input_reference={"jd_id": jd.jd_id, "version": rubric.version},
        output={
            "resume_weight": rubric.resume_weight,
            "skill_weight": rubric.skill_weight,
            "culture_weight": rubric.culture_weight,
            "criteria": rubric.criteria
        },
        rubric_version=rubric.version
    )

    return rubric

