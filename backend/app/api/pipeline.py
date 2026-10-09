from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import Dict, Any, Optional
from pydantic import BaseModel
from app.database.session import get_db
from app.database.models import Candidate, JobDescription, Assessment, ScreeningResult
from app.services.rubric_service import get_or_create_rubric
from app.services.assessment_service import generate_technical_questions_for_jd, generate_behavioral_questions_for_jd
from app.agents.resume_screener import ResumeScreenerAgent
from app.agents.panel_coordinator import PanelCoordinatorAgent
from app.agents.bias_checker import BiasCheckerAgent
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.orchestration.workflow import create_candidate_workflow
from app.auth.security import require_hr

router = APIRouter(prefix="/pipeline", tags=["Agent Pipeline Orchestration"])

class PipelineRunRequest(BaseModel):
    candidate_id: str
    jd_id: Optional[str] = None

@router.post("/run-screen-resume")
def run_screen_resume(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = db.query(Candidate).filter(Candidate.candidate_id == req.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    jd_id = req.jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Target Job Description not specified or found")

    rubric = get_or_create_rubric(db, jd)
    screening_out = ResumeScreenerAgent.evaluate(
        candidate_id=cand.candidate_id,
        resume_text=cand.resume_text or "",
        jd_data=jd.__dict__,
        rubric_data=rubric.criteria
    )

    ATSTools.save_screening_result(
        db,
        candidate_id=cand.candidate_id,
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
        event="Resume Screening Evaluated",
        agent="ResumeScreenerAgent",
        candidate_id=cand.candidate_id,
        input_reference={"jd_id": jd.jd_id},
        output=screening_out.model_dump(),
        rubric_version=screening_out.rubric_version
    )

    return screening_out

@router.post("/run-panel")
def run_panel_synthesis(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """
    Executes multi-agent panel synthesis and bias verification via the unified LangGraph Swarm workflow.
    Guarantees single-source-of-truth orchestration without duplicate code paths or logic drift.
    """
    res = run_full_graph_orchestration(req, current_user, db)
    return {
        "panel_decision": res.get("panel_result"),
        "bias_check": res.get("bias_result")
    }

@router.post("/run-full-graph")
def run_full_graph_orchestration(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """
    Executes the entire LangGraph orchestration workflow end-to-end for a candidate.
    """
    cand = db.query(Candidate).filter(Candidate.candidate_id == req.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    jd_id = req.jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job Description not found")

    rubric = get_or_create_rubric(db, jd)
    tech_qs = generate_technical_questions_for_jd(jd)
    beh_qs = generate_behavioral_questions_for_jd(jd)

    # Retrieve latest submitted assessments from the database (empty list if not yet completed by candidate)
    tech_rec = db.query(Assessment).filter(
        Assessment.candidate_id == cand.candidate_id,
        Assessment.test_type == "TECHNICAL"
    ).order_by(Assessment.completed_date.desc(), Assessment.created_at.desc()).first()
    beh_rec = db.query(Assessment).filter(
        Assessment.candidate_id == cand.candidate_id,
        Assessment.test_type == "BEHAVIORAL"
    ).order_by(Assessment.completed_date.desc(), Assessment.created_at.desc()).first()

    tech_answers = tech_rec.answers if (tech_rec and tech_rec.answers) else []
    beh_answers = beh_rec.answers if (beh_rec and beh_rec.answers) else []

    initial_state = {
        "candidate_id": cand.candidate_id,
        "jd_id": jd.jd_id,
        "resume_text": cand.resume_text or "",
        "jd_data": {k: v for k, v in jd.__dict__.items() if not k.startswith('_')},
        "rubric_data": {k: v for k, v in rubric.__dict__.items() if not k.startswith('_')},
        "tech_questions": tech_qs,
        "tech_answers": tech_answers,
        "beh_questions": beh_qs,
        "beh_answers": beh_answers,
        "current_stage": "APPLIED"
    }

    graph = create_candidate_workflow(db)
    final_state = graph.invoke(initial_state)

    return {
        "candidate_id": cand.candidate_id,
        "current_stage": final_state.get("current_stage"),
        "screening_result": final_state.get("screening_result"),
        "skill_result": final_state.get("skill_result"),
        "behavioral_result": final_state.get("behavioral_result"),
        "panel_result": final_state.get("panel_result"),
        "bias_result": final_state.get("bias_result")
    }
