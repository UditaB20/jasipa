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
    cand = db.query(Candidate).filter(Candidate.candidate_id == req.candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    
    jd_id = req.jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
    if not jd:
        raise HTTPException(status_code=404, detail="Job Description not found")

    rubric = get_or_create_rubric(db, jd)

    # 1. Screening Result
    screening_rec = db.query(ScreeningResult).filter(ScreeningResult.candidate_id == cand.candidate_id).first()
    if not screening_rec:
        screening_out = ResumeScreenerAgent.evaluate(cand.candidate_id, cand.resume_text or "", jd.__dict__, rubric.criteria)
    else:
        screening_out = ResumeScreeningOutput(
            candidate_id=cand.candidate_id,
            jd_id=jd.jd_id,
            score=screening_rec.score,
            matched_requirements=screening_rec.matched_requirements or [],
            missing_requirements=screening_rec.missing_requirements or [],
            experience_match=screening_rec.experience_match,
            evidence=screening_rec.evidence or [],
            rubric_version=screening_rec.rubric_version,
            status=screening_rec.status
        )

    # 2. Technical Assessment
    tech_rec = db.query(Assessment).filter(Assessment.candidate_id == cand.candidate_id, Assessment.test_type == "TECHNICAL").first()
    if not tech_rec:
        tech_out = SkillAssessorOutput(
            candidate_id=cand.candidate_id,
            jd_id=jd.jd_id,
            score=0.0,
            skill_breakdown={},
            evidence=["Technical assessment not yet submitted."],
            status="INSUFFICIENT_EVIDENCE"
        )
    else:
        tech_out = SkillAssessorOutput(
            candidate_id=cand.candidate_id,
            jd_id=jd.jd_id,
            score=tech_rec.score,
            skill_breakdown=tech_rec.skill_breakdown or {},
            evidence=tech_rec.evidence or [],
            confidence=tech_rec.confidence,
            status=tech_rec.status
        )

    # 3. Behavioral Assessment
    beh_rec = db.query(Assessment).filter(Assessment.candidate_id == cand.candidate_id, Assessment.test_type == "BEHAVIORAL").first()
    if not beh_rec:
        beh_out = CultureFitOutput(
            candidate_id=cand.candidate_id,
            jd_id=jd.jd_id,
            score=0.0,
            breakdown={},
            evidence=["Behavioral assessment not yet submitted."],
            status="INSUFFICIENT_EVIDENCE"
        )
    else:
        beh_out = CultureFitOutput(
            candidate_id=cand.candidate_id,
            jd_id=jd.jd_id,
            score=beh_rec.score,
            breakdown=beh_rec.skill_breakdown or {},
            evidence=beh_rec.evidence or [],
            confidence=beh_rec.confidence,
            status=beh_rec.status
        )

    # Panel Synthesis
    panel_out = PanelCoordinatorAgent.synthesize(
        candidate_id=cand.candidate_id,
        jd_data=jd.__dict__,
        rubric_data=rubric.__dict__,
        screening=screening_out,
        technical=tech_out,
        behavioral=beh_out
    )

    saved = ATSTools.save_panel_decision(
        db,
        candidate_id=cand.candidate_id,
        jd_id=jd.jd_id,
        resume_score=panel_out.resume_score,
        skill_score=panel_out.skill_score,
        culture_score=panel_out.culture_score,
        merged_score=panel_out.merged_score,
        recommendation=panel_out.recommendation,
        strengths=panel_out.strengths,
        gaps=panel_out.gaps,
        disagreements=panel_out.disagreements,
        evidence=panel_out.evidence,
        rubric_version=panel_out.rubric_version
    )

    log_event(
        db,
        stage="PANEL_EVALUATED",
        event="Panel Coordinator Synthesis Generated",
        agent="PanelCoordinatorAgent",
        candidate_id=cand.candidate_id,
        input_reference={"merged_score": panel_out.merged_score},
        output=panel_out.model_dump(),
        rubric_version=panel_out.rubric_version
    )

    # Automatically trigger Bias Check after Panel Coordinator
    bias_out = BiasCheckerAgent.check(db, cand.candidate_id, saved["decision_id"])
    ATSTools.save_bias_check(
        db,
        decision_id=saved["decision_id"],
        candidate_id=cand.candidate_id,
        flag_status=bias_out.flag_status,
        reason=bias_out.reason,
        cohort_breakdown=bias_out.cohort_breakdown,
        requires_human_review=bias_out.requires_human_review
    )

    log_event(
        db,
        stage="BIAS_CHECKED",
        event=f"Cohort Bias Check Completed ({bias_out.flag_status})",
        agent="BiasCheckerAgent",
        candidate_id=cand.candidate_id,
        input_reference={"decision_id": saved["decision_id"]},
        output=bias_out.model_dump(),
        rubric_version=panel_out.rubric_version
    )

    return {
        "panel_decision": panel_out,
        "bias_check": bias_out
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
    beh_qs = generate_behavioral_questions_for_jd()

    # If candidate doesn't have answers yet, prepare sample responses from profile
    tech_answers = [
        {"question_id": "TECH_Q1", "answer_text": "Option B: Asyncio uses an event loop on a single thread with cooperative multitasking."},
        {"question_id": "TECH_Q2", "answer_text": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;"},
        {"question_id": "TECH_Q3", "answer_text": "def has_cycle(graph):\n  visited = set()\n  rec_stack = set()\n  # DFS implementation with O(V+E) time complexity"}
    ]
    beh_answers = [
        {"question_id": "BEH_Q1", "answer_text": "In a previous project, we disagreed on database schema migration. I organized a data-driven benchmark test, presented results objectively, and we reached consensus on an indexed PostgreSQL design."},
        {"question_id": "BEH_Q2", "answer_text": "When building a real-time event pipeline with ambiguous latency SLAs, I broke the problem into measurable queuing and ingestion phases and delivered an iterative prototype."},
        {"question_id": "BEH_Q3", "answer_text": "I had 2 weeks to learn Kubernetes for a production deployment. I set up local Minikube clusters, wrote Helm charts, and successfully deployed on schedule."},
        {"question_id": "BEH_Q4", "answer_text": "I explained microservice decoupling tradeoffs to the product team using visual dependency charts and non-technical business impact scenarios."}
    ]

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
