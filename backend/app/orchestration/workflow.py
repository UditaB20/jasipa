"""LangGraph swarm workflow: three independent evaluators fan in to the Panel Coordinator, then the bias check.

    swarm_dispatch ─┬─> screen_resume  ─┐
                    ├─> assess_skills  ─┼─> panel_coordinate ─> check_bias ─> END
                    └─> assess_culture ─┘

Design rules
* Evaluator nodes are pure: they read only the graph state and never touch the database, because
  LangGraph runs parallel branches on worker threads and a SQLAlchemy session is not thread-safe.
  The API layer preloads stored evidence (latest screening, submitted assessments, prior rounds).
* Stored assessment evaluations are reused rather than re-scored, so re-running the panel does not
  create duplicate assessment rows or repeat LLM calls. A stored evaluation that previously failed is
  re-scored on the same stored questions and answers.
* Persistence happens sequentially in panel_coordinate / check_bias through the ATS (MCP) tools.
* The bias result never changes scores or routing. The graph always ends at HUMAN_REVIEW_PENDING.
"""
from typing import Any, Dict, List, Optional, TypedDict

from langgraph.graph import END, StateGraph
from sqlalchemy.orm import Session

from app.agents.bias_checker import BiasCheckerAgent
from app.agents.culture_fit import CultureFitAgent
from app.agents.llm_factory import llm_available
from app.agents.panel_coordinator import PanelCoordinatorAgent
from app.agents.resume_screener import ResumeScreenerAgent
from app.agents.skill_assessor import SkillAssessorAgent
from app.config import settings
from app.database.models import Assessment
from app.mcp.tools import ATSTools
from app.schemas.assessment import CultureFitOutput, SkillAssessorOutput
from app.schemas.screening import ResumeScreeningOutput
from app.services.audit_service import log_event

RESCORE_STATUSES = {"EVALUATION_FAILED"}


class CandidateState(TypedDict, total=False):
    candidate_id: str
    jd_id: str
    round_number: int
    interview_history: List[Dict[str, Any]]

    resume_text: str
    resume_hash: Optional[str]
    jd_data: Dict[str, Any]
    rubric_data: Dict[str, Any]
    cached_screening: Optional[Dict[str, Any]]
    tech_assessment: Optional[Dict[str, Any]]
    beh_assessment: Optional[Dict[str, Any]]

    screening_result: Dict[str, Any]
    screening_reused: bool
    skill_result: Dict[str, Any]
    skill_rescored: bool
    behavioral_result: Dict[str, Any]
    behavioral_rescored: bool
    panel_result: Dict[str, Any]
    bias_result: Dict[str, Any]
    current_stage: str


def strategy_label(strategy: Optional[str]) -> str:
    """What actually produced an output, for the audit ledger."""
    if strategy and "llm" in strategy and llm_available():
        return settings.LLM_MODEL
    return f"deterministic:{strategy or 'none'}"


def _skill_from_record(record: Dict[str, Any], candidate_id: str, jd_id: str) -> Dict[str, Any]:
    return SkillAssessorOutput(candidate_id=candidate_id, jd_id=jd_id, score=record.get("score") or 0.0,
                               skill_breakdown=record.get("skill_breakdown") or {}, evidence=record.get("evidence") or [],
                               confidence=record.get("confidence") or 0.0, status=record.get("status") or "COMPLETED",
                               strategy_used=record.get("strategy_used") or "stored",
                               execution_results=record.get("execution_results") or {}).model_dump()


def _culture_from_record(record: Dict[str, Any], candidate_id: str, jd_id: str) -> Dict[str, Any]:
    return CultureFitOutput(candidate_id=candidate_id, jd_id=jd_id, score=record.get("score") or 0.0,
                            breakdown=record.get("skill_breakdown") or {}, evidence=record.get("evidence") or [],
                            confidence=record.get("confidence") or 0.0, status=record.get("status") or "COMPLETED",
                            strategy_used=record.get("strategy_used") or "stored").model_dump()


def create_candidate_workflow(db: Session):

    def node_swarm_dispatch(state: CandidateState) -> Dict[str, Any]:
        return {"round_number": state.get("round_number", 1), "interview_history": list(state.get("interview_history", []))}

    def node_screen_resume(state: CandidateState) -> Dict[str, Any]:
        cached = state.get("cached_screening")
        if cached:
            return {"screening_result": cached, "screening_reused": True}
        out = ResumeScreenerAgent.evaluate(state["candidate_id"], state.get("resume_text", ""),
                                           state.get("jd_data", {}), state.get("rubric_data", {}))
        return {"screening_result": out.model_dump(), "screening_reused": False}

    def node_assess_skills(state: CandidateState) -> Dict[str, Any]:
        cid, jd_id = state["candidate_id"], state["jd_id"]
        record = state.get("tech_assessment")
        if not record:
            out = SkillAssessorAgent.evaluate(cid, state.get("jd_data", {}), [], [])
            return {"skill_result": out.model_dump(), "skill_rescored": False}
        if record.get("status") in RESCORE_STATUSES:
            out = SkillAssessorAgent.evaluate(cid, state.get("jd_data", {}), record.get("questions") or [],
                                              record.get("answers") or [],
                                              (state.get("rubric_data", {}).get("criteria") or {}).get("technical_scoring"))
            return {"skill_result": out.model_dump(), "skill_rescored": True}
        return {"skill_result": _skill_from_record(record, cid, jd_id), "skill_rescored": False}

    def node_assess_culture(state: CandidateState) -> Dict[str, Any]:
        cid, jd_id = state["candidate_id"], state["jd_id"]
        record = state.get("beh_assessment")
        if not record:
            out = CultureFitAgent.evaluate(cid, state.get("jd_data", {}), [], [])
            return {"behavioral_result": out.model_dump(), "behavioral_rescored": False}
        if record.get("status") in RESCORE_STATUSES:
            out = CultureFitAgent.evaluate(cid, state.get("jd_data", {}), record.get("questions") or [],
                                           record.get("answers") or [],
                                           (state.get("rubric_data", {}).get("criteria") or {}).get("behavioral_scoring"))
            return {"behavioral_result": out.model_dump(), "behavioral_rescored": True}
        return {"behavioral_result": _culture_from_record(record, cid, jd_id), "behavioral_rescored": False}

    def node_panel_coordinate(state: CandidateState) -> Dict[str, Any]:
        cid, jd_id = state["candidate_id"], state["jd_id"]
        rubric_data = state.get("rubric_data", {})
        rubric_version = rubric_data.get("version", "1.0")
        screening_dict = state["screening_result"]
        skill_dict = state["skill_result"]
        behavioral_dict = state["behavioral_result"]

        if not state.get("screening_reused"):
            saved = ATSTools.save_screening_result(
                db, candidate_id=cid, jd_id=jd_id, score=screening_dict["score"],
                matched_requirements=screening_dict.get("matched_requirements", []),
                missing_requirements=screening_dict.get("missing_requirements", []),
                experience_match=screening_dict.get("experience_match", False),
                evidence=screening_dict.get("evidence", []), rubric_version=rubric_version,
                status=screening_dict.get("status", "COMPLETED"))
            from app.database.models import ScreeningResult
            row = db.query(ScreeningResult).filter(ScreeningResult.screening_id == saved["screening_id"]).first()
            if row:
                row.resume_hash = state.get("resume_hash")
                row.strategy_used = screening_dict.get("strategy_used")
                db.commit()
            log_event(db, stage="RESUME_SCREENED", event="Resume screening completed", agent="ResumeScreenerAgent",
                      candidate_id=cid, input_reference={"jd_id": jd_id, "rubric_version": rubric_version},
                      output=screening_dict, rubric_version=rubric_version,
                      model_name=strategy_label(screening_dict.get("strategy_used")))

        for key, record_key, rescored_key, test_type in (("skill_result", "tech_assessment", "skill_rescored", "TECHNICAL"),
                                                         ("behavioral_result", "beh_assessment", "behavioral_rescored", "BEHAVIORAL")):
            if state.get(rescored_key) and state.get(record_key):
                result = state[key]
                row = db.query(Assessment).filter(Assessment.assessment_id == state[record_key]["assessment_id"]).first()
                if row:
                    row.score = result["score"]
                    row.skill_breakdown = result.get("skill_breakdown") or result.get("breakdown") or {}
                    row.evidence = result.get("evidence", [])
                    row.confidence = result.get("confidence", 0.0)
                    row.status = result.get("status", "COMPLETED")
                    row.strategy_used = result.get("strategy_used")
                    if test_type == "TECHNICAL":
                        row.execution_results = result.get("execution_results") or {}
                    db.commit()
                    log_event(db, stage=f"{test_type}_ASSESSED", event=f"{test_type.title()} assessment re-scored after a failed evaluation",
                              agent="SkillAssessorAgent" if test_type == "TECHNICAL" else "CultureFitAgent", candidate_id=cid,
                              input_reference={"assessment_id": row.assessment_id}, output=result, rubric_version=rubric_version,
                              model_name=strategy_label(result.get("strategy_used")))

        panel_out = PanelCoordinatorAgent.synthesize(
            candidate_id=cid, jd_data=state.get("jd_data", {}), rubric_data=rubric_data,
            screening=ResumeScreeningOutput(**screening_dict), technical=SkillAssessorOutput(**skill_dict),
            behavioral=CultureFitOutput(**behavioral_dict), history=state.get("interview_history", []))
        panel_out.round_number = state.get("round_number", 1)

        saved = ATSTools.save_panel_decision(db, candidate_id=cid, jd_id=jd_id, **{
            k: v for k, v in panel_out.model_dump().items() if k not in ("candidate_id", "jd_id")})
        log_event(db, stage="PANEL_EVALUATED", event=f"Panel synthesis completed (round {panel_out.round_number})",
                  agent="PanelCoordinatorAgent", candidate_id=cid,
                  input_reference={"resume_score": panel_out.resume_score, "skill_score": panel_out.skill_score,
                                   "culture_score": panel_out.culture_score, "round_number": panel_out.round_number,
                                   "prior_rounds": len(state.get("interview_history", []))},
                  output={**panel_out.model_dump(), "decision_id": saved["decision_id"]}, rubric_version=panel_out.rubric_version,
                  model_name=settings.LLM_MODEL if panel_out.used_llm_synthesis else "deterministic:weighted-merge")
        return {"panel_result": {**panel_out.model_dump(), "decision_id": saved["decision_id"]}, "current_stage": "PANEL_EVALUATED"}

    def node_check_bias(state: CandidateState) -> Dict[str, Any]:
        cid = state["candidate_id"]
        decision_id = state["panel_result"]["decision_id"]
        bias_out = BiasCheckerAgent.check(db, cid, decision_id)
        saved = ATSTools.save_bias_check(db, decision_id=decision_id, candidate_id=cid, flag_status=bias_out.flag_status,
                                         reason=bias_out.reason, cohort_breakdown=bias_out.cohort_breakdown,
                                         requires_human_review=True)
        log_event(db, stage="BIAS_CHECKED", event=f"Bias check recorded for panel decision ({bias_out.flag_status})",
                  agent="BiasCheckerAgent", candidate_id=cid,
                  input_reference={"decision_id": decision_id, "check_id": saved["check_id"]},
                  output={"flag_status": bias_out.flag_status, "reason": bias_out.reason, "checks": bias_out.checks,
                          "recommendations": bias_out.recommendations, "confidence_level": bias_out.confidence_level},
                  rubric_version=state.get("rubric_data", {}).get("version", "1.0"), model_name="deterministic:fairness-stats")
        return {"bias_result": {**bias_out.model_dump(), "check_id": saved["check_id"]}, "current_stage": "HUMAN_REVIEW_PENDING"}

    workflow = StateGraph(CandidateState)
    workflow.add_node("swarm_dispatch", node_swarm_dispatch)
    workflow.add_node("screen_resume", node_screen_resume)
    workflow.add_node("assess_skills", node_assess_skills)
    workflow.add_node("assess_culture", node_assess_culture)
    workflow.add_node("panel_coordinate", node_panel_coordinate)
    workflow.add_node("check_bias", node_check_bias)
    workflow.set_entry_point("swarm_dispatch")
    for evaluator in ("screen_resume", "assess_skills", "assess_culture"):
        workflow.add_edge("swarm_dispatch", evaluator)
    workflow.add_edge(["screen_resume", "assess_skills", "assess_culture"], "panel_coordinate")
    workflow.add_edge("panel_coordinate", "check_bias")
    workflow.add_edge("check_bias", END)
    return workflow.compile()
