"""Assessment question delivery.

Questions come from QuestionGenerationAgent and are cached per JD + rubric version, so the
candidate portal, scoring and the panel pipeline all use the exact same question set.
"""
from typing import Any, Dict, List, Tuple

from sqlalchemy.orm import Session

from app.agents.question_generator import get_or_create_question_set, sanitize_questions_for_candidate
from app.database.models import JobDescription, QuestionSet
from app.services.rubric_service import get_or_create_rubric

__all__ = ["get_question_set_for_jd", "find_question", "sanitize_questions_for_candidate"]


def get_question_set_for_jd(db: Session, jd: JobDescription) -> QuestionSet:
    rubric = get_or_create_rubric(db, jd)
    return get_or_create_question_set(db, jd, rubric)


def question_set_for_candidate(db: Session, candidate, jd: JobDescription) -> QuestionSet:
    """The set pinned to this applicant, assigning the current one on first use."""
    if candidate.assigned_question_set_id:
        pinned = db.query(QuestionSet).filter(QuestionSet.question_set_id == candidate.assigned_question_set_id,
                                              QuestionSet.jd_id == jd.jd_id).first()
        if pinned:
            return pinned
    question_set = get_question_set_for_jd(db, jd)
    candidate.assigned_question_set_id = question_set.question_set_id
    db.commit()
    return question_set


def find_question(questions: List[Dict[str, Any]], question_id: str) -> Dict[str, Any] | None:
    return next((q for q in questions or [] if q.get("question_id") == question_id), None)


def split_by_type(question_set: QuestionSet) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    return list(question_set.technical_questions or []), list(question_set.behavioral_questions or [])


def submit_assessment(db: Session, candidate, jd: JobDescription, test_type: str, answers: List[Dict[str, str]]) -> Dict[str, Any]:
    """Scores a candidate's submission against the cached question set and stores it once."""
    from app.agents.culture_fit import CultureFitAgent
    from app.agents.skill_assessor import SkillAssessorAgent
    from app.mcp.tools import ATSTools
    from app.database.models import Assessment
    from app.orchestration.workflow import strategy_label
    from app.services.audit_service import log_event

    rubric = get_or_create_rubric(db, jd)
    question_set = question_set_for_candidate(db, candidate, jd)
    questions = list(question_set.technical_questions if test_type == "TECHNICAL" else question_set.behavioral_questions)
    known_ids = {q["question_id"] for q in questions}
    cleaned = [{"question_id": a["question_id"], "answer_text": (a.get("answer_text") or "")[:20000]}
               for a in answers if a.get("question_id") in known_ids]
    if not any(a["answer_text"].strip() for a in cleaned):
        raise ValueError("Answer at least one question before submitting.")

    criteria = rubric.criteria or {}
    jd_data = {"jd_id": jd.jd_id, "title": jd.title}
    if test_type == "TECHNICAL":
        out = SkillAssessorAgent.evaluate(candidate.candidate_id, jd_data, questions, cleaned, criteria.get("technical_scoring"))
        breakdown, agent = out.skill_breakdown, "SkillAssessorAgent"
    else:
        out = CultureFitAgent.evaluate(candidate.candidate_id, jd_data, questions, cleaned, criteria.get("behavioral_scoring"))
        breakdown, agent = out.breakdown, "CultureFitAgent"

    saved = ATSTools.save_assessment_result(
        db, candidate_id=candidate.candidate_id, jd_id=jd.jd_id, test_type=test_type, questions=questions, answers=cleaned,
        score=out.score, skill_breakdown=breakdown, evidence=out.evidence, confidence=out.confidence, status=out.status)
    record = db.query(Assessment).filter(Assessment.assessment_id == saved["assessment_id"]).first()
    record.question_set_id = question_set.question_set_id
    record.strategy_used = out.strategy_used
    if test_type == "TECHNICAL":
        record.execution_results = out.execution_results
    db.commit()
    log_event(db, stage=f"{test_type}_ASSESSED", event=f"Candidate submitted {test_type.lower()} assessment", agent=agent,
              candidate_id=candidate.candidate_id,
              input_reference={"jd_id": jd.jd_id, "question_set_id": question_set.question_set_id,
                               "answered": sum(1 for a in cleaned if a["answer_text"].strip()), "questions": len(questions)},
              output=out.model_dump(), rubric_version=rubric.version, model_name=strategy_label(out.strategy_used))
    return {"assessment_id": record.assessment_id, "status": out.status}
