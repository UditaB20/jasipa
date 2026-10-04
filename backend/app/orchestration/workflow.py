from typing import Dict, Any, TypedDict, Optional, List
from langgraph.graph import StateGraph, END
from sqlalchemy.orm import Session
from app.agents.resume_screener import ResumeScreenerAgent
from app.agents.skill_assessor import SkillAssessorAgent
from app.agents.culture_fit import CultureFitAgent
from app.agents.panel_coordinator import PanelCoordinatorAgent
from app.agents.bias_checker import BiasCheckerAgent
from app.mcp.tools import ATSTools
from app.services.audit_service import log_event
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput


class CandidateState(TypedDict, total=False):
    # Core identifiers (always present)
    candidate_id: str
    jd_id: str

    # Inputs passed in at start
    resume_text: str
    jd_data: Dict[str, Any]
    rubric_data: Dict[str, Any]
    tech_questions: List[Dict[str, Any]]
    tech_answers: List[Dict[str, str]]
    beh_questions: List[Dict[str, Any]]
    beh_answers: List[Dict[str, str]]

    # Stage outputs (set by each node)
    screening_result: Optional[Dict[str, Any]]
    skill_result: Optional[Dict[str, Any]]
    behavioral_result: Optional[Dict[str, Any]]
    panel_result: Optional[Dict[str, Any]]
    bias_result: Optional[Dict[str, Any]]

    # Progress tracking
    current_stage: str


def create_candidate_workflow(db: Session):
    """
    Builds the LangGraph stateful candidate screening and interview panel workflow.

    ARCHITECTURE (Key Design Decisions):
    ─────────────────────────────────────
    1. LangGraph:     Explicit StateGraph(CandidateState) with 5 sequential nodes.
    2. MCP Usage:     MCP/ATS tools are called BY nodes AFTER agents complete evaluation.
                      Agents NEVER call tools directly — they only produce structured output.
    3. LLM Strategy:  LLM (Gemini) generates JSON responses; agents parse them.
                      Every agent has a deterministic regex/heuristic FALLBACK if LLM fails.
    4. Panel Coord:   Pure Python weighted merge — no LLM call. Deterministic synthesis.
    5. Bias Impact:   Bias flags are logged but NEVER affect recommendation scores.
                      All candidates always route to HUMAN_REVIEW_PENDING.
    6. Invocation:    /pipeline/run-full-graph endpoint calls graph.invoke(initial_state).

    Graph Edges: screen_resume → assess_skills → assess_culture → panel_coordinate → check_bias → END
    """

    # 1. Node: Screen Resume
    def node_screen_resume(state: CandidateState) -> CandidateState:
        cid = state["candidate_id"]
        jd_id = state["jd_id"]
        resume_text = state.get("resume_text", "")
        jd_data = state.get("jd_data", {})
        rubric_data = state.get("rubric_data", {})

        screening_out = ResumeScreenerAgent.evaluate(cid, resume_text, jd_data, rubric_data)

        # Save via ATS Tool
        ATSTools.save_screening_result(
            db,
            candidate_id=cid,
            jd_id=jd_id,
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
            event="Resume Screening Completed",
            agent="ResumeScreenerAgent",
            candidate_id=cid,
            input_reference={"jd_id": jd_id, "resume_length": len(resume_text)},
            output=screening_out.model_dump(),
            rubric_version=screening_out.rubric_version
        )

        return {
            **state,
            "screening_result": screening_out.model_dump(),
            "current_stage": "RESUME_SCREENED"
        }

    # 2. Node: Assess Technical Skills
    def node_assess_skills(state: CandidateState) -> CandidateState:
        cid = state["candidate_id"]
        jd_id = state["jd_id"]
        jd_data = state.get("jd_data", {})
        questions = state.get("tech_questions", [])
        answers = state.get("tech_answers", [])

        skill_out = SkillAssessorAgent.evaluate(cid, jd_data, questions, answers)

        ATSTools.save_assessment_result(
            db,
            candidate_id=cid,
            jd_id=jd_id,
            test_type="TECHNICAL",
            questions=questions,
            answers=answers,
            score=skill_out.score,
            skill_breakdown=skill_out.skill_breakdown,
            evidence=skill_out.evidence,
            confidence=skill_out.confidence,
            status=skill_out.status
        )

        log_event(
            db,
            stage="TECHNICAL_ASSESSED",
            event="Technical Skill Assessment Completed",
            agent="SkillAssessorAgent",
            candidate_id=cid,
            input_reference={"question_count": len(questions), "answer_count": len(answers)},
            output=skill_out.model_dump(),
            rubric_version=state.get("rubric_data", {}).get("version", "1.0")
        )

        return {
            **state,
            "skill_result": skill_out.model_dump(),
            "current_stage": "TECHNICAL_ASSESSED"
        }

    # 3. Node: Assess Behavioral Culture-Fit
    def node_assess_culture(state: CandidateState) -> CandidateState:
        cid = state["candidate_id"]
        jd_id = state["jd_id"]
        jd_data = state.get("jd_data", {})
        questions = state.get("beh_questions", [])
        answers = state.get("beh_answers", [])

        culture_out = CultureFitAgent.evaluate(cid, jd_data, questions, answers)

        ATSTools.save_assessment_result(
            db,
            candidate_id=cid,
            jd_id=jd_id,
            test_type="BEHAVIORAL",
            questions=questions,
            answers=answers,
            score=culture_out.score,
            skill_breakdown=culture_out.breakdown,
            evidence=culture_out.evidence,
            confidence=culture_out.confidence,
            status=culture_out.status
        )

        log_event(
            db,
            stage="BEHAVIORAL_ASSESSED",
            event="Behavioral Assessment Completed",
            agent="CultureFitAgent",
            candidate_id=cid,
            input_reference={"question_count": len(questions), "answer_count": len(answers)},
            output=culture_out.model_dump(),
            rubric_version=state.get("rubric_data", {}).get("version", "1.0")
        )

        return {
            **state,
            "behavioral_result": culture_out.model_dump(),
            "current_stage": "BEHAVIORAL_ASSESSED"
        }

    # 4. Node: Panel Coordinator Synthesis
    def node_panel_coordinate(state: CandidateState) -> CandidateState:
        cid = state["candidate_id"]
        jd_id = state["jd_id"]
        jd_data = state.get("jd_data", {})
        rubric_data = state.get("rubric_data", {})

        screening = ResumeScreeningOutput(**state["screening_result"])
        technical = SkillAssessorOutput(**state["skill_result"])
        behavioral = CultureFitOutput(**state["behavioral_result"])

        panel_out = PanelCoordinatorAgent.synthesize(
            candidate_id=cid,
            jd_data=jd_data,
            rubric_data=rubric_data,
            screening=screening,
            technical=technical,
            behavioral=behavioral
        )

        saved = ATSTools.save_panel_decision(
            db,
            candidate_id=cid,
            jd_id=jd_id,
            resume_score=panel_out.resume_score,
            skill_score=panel_out.skill_score,
            culture_score=panel_out.culture_score,
            merged_score=panel_out.merged_score,
            recommendation=panel_out.recommendation,
            strengths=panel_out.strengths,
            gaps=panel_out.gaps,
            disagreements=panel_out.disagreements,
            evidence=panel_out.evidence,
            rubric_version=panel_out.rubric_version,
            natural_language_summary=panel_out.natural_language_summary,
            decision_factors=panel_out.decision_factors,
            highlighted_concerns=panel_out.highlighted_concerns,
            highlighted_strengths=panel_out.highlighted_strengths,
            used_llm_synthesis=panel_out.used_llm_synthesis,
            synthesis_latency_ms=panel_out.synthesis_latency_ms,
            synthesis_strategy=panel_out.synthesis_strategy,
            synthesis_error=panel_out.synthesis_error
        )

        log_event(
            db,
            stage="PANEL_EVALUATED",
            event="Multi-Agent Panel Synthesis Completed",
            agent="PanelCoordinatorAgent",
            candidate_id=cid,
            input_reference={
                "resume_score": panel_out.resume_score,
                "skill_score": panel_out.skill_score,
                "culture_score": panel_out.culture_score
            },
            output=panel_out.model_dump(),
            rubric_version=panel_out.rubric_version
        )

        out_dict = panel_out.model_dump()
        out_dict["decision_id"] = saved["decision_id"]

        return {
            **state,
            "panel_result": out_dict,
            "current_stage": "PANEL_EVALUATED"
        }

    # 5. Node: Bias Checker
    def node_check_bias(state: CandidateState) -> CandidateState:
        cid = state["candidate_id"]
        decision_id = state["panel_result"]["decision_id"]

        bias_out = BiasCheckerAgent.check(db, cid, decision_id)

        ATSTools.save_bias_check(
            db,
            decision_id=decision_id,
            candidate_id=cid,
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
            candidate_id=cid,
            input_reference={"decision_id": decision_id},
            output=bias_out.model_dump(),
            rubric_version=state.get("rubric_data", {}).get("version", "1.0")
        )

        return {
            **state,
            "bias_result": bias_out.model_dump(),
            "current_stage": "HUMAN_REVIEW_PENDING"
        }

    # Construct the graph with TypedDict state
    workflow = StateGraph(CandidateState)

    workflow.add_node("screen_resume", node_screen_resume)
    workflow.add_node("assess_skills", node_assess_skills)
    workflow.add_node("assess_culture", node_assess_culture)
    workflow.add_node("panel_coordinate", node_panel_coordinate)
    workflow.add_node("check_bias", node_check_bias)

    # Define edges: Resume -> Skills -> Culture -> Panel -> Bias -> End (ready for human review)
    workflow.set_entry_point("screen_resume")
    workflow.add_edge("screen_resume", "assess_skills")
    workflow.add_edge("assess_skills", "assess_culture")
    workflow.add_edge("assess_culture", "panel_coordinate")
    workflow.add_edge("panel_coordinate", "check_bias")
    workflow.add_edge("check_bias", END)

    return workflow.compile()
