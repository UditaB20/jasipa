from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.agents.question_generator import QuestionRegenerationError, get_or_create_question_set
from app.auth.security import require_hr
from app.database.models import Assessment, JobDescription
from app.database.session import get_db
from app.schemas.assessment import AssessmentResponse
from app.services.audit_service import log_event
from app.services.rubric_service import get_or_create_rubric

router = APIRouter(prefix="/assessments", tags=["Assessments"])


def _question_set_payload(question_set, rubric) -> dict:
    return {"question_set_id": question_set.question_set_id, "jd_id": question_set.jd_id,
            "rubric_version": question_set.rubric_version, "generator": question_set.generator,
            "generation_notes": question_set.generation_notes or [],
            "created_at": question_set.created_at.isoformat() if question_set.created_at else None,
            "technical_questions": question_set.technical_questions or [],
            "behavioral_questions": question_set.behavioral_questions or [],
            "technical_weights": (rubric.criteria or {}).get("technical_scoring", {})}


def _jd(db: Session, jd_id: str) -> JobDescription:
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job description not found")
    return jd


@router.get("/questions/{jd_id}")
def get_question_set(jd_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """HR preview of the generated assessment, including answer keys and hidden tests."""
    jd = _jd(db, jd_id)
    rubric = get_or_create_rubric(db, jd)
    return _question_set_payload(get_or_create_question_set(db, jd, rubric), rubric)


@router.post("/questions/{jd_id}/regenerate")
def regenerate_question_set(jd_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Generates a fresh set for future applicants. Submitted assessments keep the questions they were given."""
    jd = _jd(db, jd_id)
    rubric = get_or_create_rubric(db, jd)
    previous = get_or_create_question_set(db, jd, rubric)
    try:
        question_set = get_or_create_question_set(db, jd, rubric, force_new=True)
    except QuestionRegenerationError as exc:
        raise HTTPException(status_code=409, detail=str(exc))
    except Exception as exc:  # LLM/network/validation failures must surface instead of looking like success
        raise HTTPException(status_code=502, detail=f"Assessment generation failed: {type(exc).__name__}. The current assessment was kept.")
    old_prompts = {q.get("prompt") for q in (previous.technical_questions or []) + (previous.behavioral_questions or [])}
    new_questions = (question_set.technical_questions or []) + (question_set.behavioral_questions or [])
    changed = sum(1 for q in new_questions if q.get("prompt") not in old_prompts)
    log_event(db, stage="QUESTIONS_GENERATED", event=f"Assessment regenerated for {jd.title}", agent="QuestionGenerationAgent",
              input_reference={"jd_id": jd.jd_id, "rubric_version": rubric.version, "requested_by": current_user["email"]},
              output={"question_set_id": question_set.question_set_id, "previous_question_set_id": previous.question_set_id,
                      "changed_questions": changed, "generator": question_set.generator,
                      "technical": len(question_set.technical_questions or []), "behavioral": len(question_set.behavioral_questions or [])},
              rubric_version=rubric.version, model_name=question_set.generator)
    return {**_question_set_payload(question_set, rubric), "previous_question_set_id": previous.question_set_id,
            "changed_questions": changed, "total_questions": len(new_questions)}


@router.get("/candidate/{candidate_id}", response_model=List[AssessmentResponse])
def get_candidate_assessments(candidate_id: str, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Submitted answers with scores and execution results. HR only: the records contain answer keys."""
    return (db.query(Assessment).filter(Assessment.candidate_id == candidate_id)
            .order_by(Assessment.completed_date.asc()).all())
