"""Entry points that run agents for a candidate and persist results through the ATS tools."""
from typing import Any, Dict, Optional

from sqlalchemy.orm import Session

from app.agents.resume_screener import ResumeScreenerAgent
from app.database.models import Assessment, Candidate, HumanReview, JobDescription, PanelDecision, ScreeningResult
from app.mcp.tools import ATSTools
from app.orchestration.workflow import create_candidate_workflow, strategy_label
from app.services.audit_service import log_event
from app.services.resume_parser import text_hash
from app.services.rubric_service import get_or_create_rubric, jd_to_dict, rubric_to_dict


class PipelineError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


def _target_jd(db: Session, cand: Candidate, jd_id: Optional[str] = None) -> JobDescription:
    jd_id = jd_id or cand.target_jd_id
    jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first() if jd_id else None
    if not jd:
        raise PipelineError(400, "The candidate has not applied to a job yet.")
    return jd


def _ensure_resume_hash(db: Session, cand: Candidate) -> Optional[str]:
    if cand.resume_text and not cand.resume_hash:
        cand.resume_hash = text_hash(cand.resume_text)
        db.commit()
    return cand.resume_hash


def screen_candidate(db: Session, cand: Candidate, jd: Optional[JobDescription] = None, actor: str = "system") -> Dict[str, Any]:
    """Runs the Resume-Screener for the candidate's target job and stores the result."""
    jd = jd or _target_jd(db, cand)
    rubric = get_or_create_rubric(db, jd)
    rubric_data = rubric_to_dict(rubric)
    out = ResumeScreenerAgent.evaluate(cand.candidate_id, cand.resume_text or "", jd_to_dict(jd), rubric_data)
    saved = ATSTools.save_screening_result(
        db, candidate_id=cand.candidate_id, jd_id=jd.jd_id, score=out.score,
        matched_requirements=out.matched_requirements, missing_requirements=out.missing_requirements,
        experience_match=out.experience_match, evidence=out.evidence, rubric_version=rubric.version, status=out.status)
    row = db.query(ScreeningResult).filter(ScreeningResult.screening_id == saved["screening_id"]).first()
    row.resume_hash = _ensure_resume_hash(db, cand)
    row.strategy_used = out.strategy_used
    db.commit()
    log_event(db, stage="RESUME_SCREENED", event=f"Resume screened for {jd.title}", agent="ResumeScreenerAgent",
              candidate_id=cand.candidate_id, input_reference={"jd_id": jd.jd_id, "requested_by": actor},
              output=out.model_dump(), rubric_version=rubric.version, model_name=strategy_label(out.strategy_used))
    return out.model_dump()


def _assessment_dict(record: Optional[Assessment]) -> Optional[Dict[str, Any]]:
    if not record:
        return None
    return {"assessment_id": record.assessment_id, "questions": record.questions or [], "answers": record.answers or [],
            "score": record.score, "skill_breakdown": record.skill_breakdown or {}, "evidence": record.evidence or [],
            "confidence": record.confidence, "status": record.status, "strategy_used": record.strategy_used,
            "execution_results": record.execution_results or {}}


def run_candidate_pipeline(db: Session, cand: Candidate, actor: str, jd_id: Optional[str] = None) -> Dict[str, Any]:
    if cand.current_stage == "DECIDED":
        raise PipelineError(409, "A final decision has already been recorded for this candidate.")
    jd = _target_jd(db, cand, jd_id)
    rubric = get_or_create_rubric(db, jd)
    resume_hash = _ensure_resume_hash(db, cand)

    cached = None
    if resume_hash:
        latest = (db.query(ScreeningResult)
                  .filter(ScreeningResult.candidate_id == cand.candidate_id, ScreeningResult.jd_id == jd.jd_id,
                          ScreeningResult.rubric_version == rubric.version, ScreeningResult.resume_hash == resume_hash)
                  .order_by(ScreeningResult.created_at.desc()).first())
        if latest:
            cached = {"candidate_id": cand.candidate_id, "jd_id": jd.jd_id, "score": latest.score,
                      "matched_requirements": latest.matched_requirements or [], "missing_requirements": latest.missing_requirements or [],
                      "experience_match": bool(latest.experience_match), "evidence": latest.evidence or [],
                      "rubric_version": latest.rubric_version, "status": latest.status, "strategy_used": latest.strategy_used or "stored"}

    def latest_assessment(test_type: str) -> Optional[Assessment]:
        return (db.query(Assessment)
                .filter(Assessment.candidate_id == cand.candidate_id, Assessment.jd_id == jd.jd_id, Assessment.test_type == test_type)
                .order_by(Assessment.completed_date.desc()).first())

    history = []
    for decision in (db.query(PanelDecision).filter(PanelDecision.candidate_id == cand.candidate_id, PanelDecision.jd_id == jd.jd_id)
                     .order_by(PanelDecision.created_at.asc()).all()):
        review = (db.query(HumanReview).filter(HumanReview.decision_id == decision.decision_id)
                  .order_by(HumanReview.timestamp.desc()).first())
        history.append({"round_number": decision.round_number or len(history) + 1, "merged_score": decision.merged_score,
                        "recommendation": decision.recommendation, "human_decision": review.decision if review else None,
                        "created_at": decision.created_at.isoformat() if decision.created_at else None})

    state = {
        "candidate_id": cand.candidate_id, "jd_id": jd.jd_id, "round_number": len(history) + 1, "interview_history": history,
        "resume_text": cand.resume_text or "", "resume_hash": resume_hash, "jd_data": jd_to_dict(jd),
        "rubric_data": rubric_to_dict(rubric), "cached_screening": cached,
        "tech_assessment": _assessment_dict(latest_assessment("TECHNICAL")),
        "beh_assessment": _assessment_dict(latest_assessment("BEHAVIORAL")),
        "current_stage": cand.current_stage,
    }
    final_state = create_candidate_workflow(db).invoke(state)
    log_event(db, stage="PIPELINE_RUN", event=f"Evaluation pipeline run (round {state['round_number']})", agent="Orchestrator",
              candidate_id=cand.candidate_id, input_reference={"requested_by": actor, "jd_id": jd.jd_id,
                                                               "screening_reused": bool(cached)},
              output={"decision_id": final_state["panel_result"]["decision_id"], "bias_check_id": final_state["bias_result"]["check_id"]},
              rubric_version=rubric.version, model_name="n/a")
    return {
        "candidate_id": cand.candidate_id,
        "current_stage": final_state.get("current_stage"),
        "round_number": state["round_number"],
        "screening_result": final_state.get("screening_result"),
        "skill_result": final_state.get("skill_result"),
        "behavioral_result": final_state.get("behavioral_result"),
        "panel_result": final_state.get("panel_result"),
        "bias_result": final_state.get("bias_result"),
    }
