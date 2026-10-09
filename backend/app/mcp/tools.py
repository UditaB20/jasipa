from typing import Dict, Any, List, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from app.database.models import (
    Candidate, JobDescription, ScreeningResult, Assessment, 
    PanelDecision, BiasCheck, HumanReview, AuditLog
)

STAGE_RANKS = {
    "APPLIED": 1,
    "MANUAL_REVIEW_REQUIRED": 1,
    "RESUME_SCREENED": 2,
    "TECHNICAL_ASSESSED": 3,
    "BEHAVIORAL_ASSESSED": 4,
    "PANEL_EVALUATED": 5,
    "BIAS_CHECKED": 6,
    "HUMAN_REVIEW_PENDING": 6,
    "DECIDED": 7
}

def advance_stage_if_higher(candidate: Candidate, target_stage: str):
    """
    Finite-State Machine guard: Ensures the pipeline can only advance forward.
    Prevents re-evaluations from overwriting higher or terminal (DECIDED) stages.
    """
    if not candidate or candidate.current_stage == "DECIDED":
        return
    current_rank = STAGE_RANKS.get(candidate.current_stage, 0)
    target_rank = STAGE_RANKS.get(target_stage, 0)
    if target_rank > current_rank:
        candidate.current_stage = target_stage

class ATSTools:
    """
    Standard Model Context Protocol (MCP) ATS Tool layer.
    Allows agent nodes to interact with ATS data store through decoupled standard tools.
    """

    @staticmethod
    def get_candidate(db: Session, candidate_id: str) -> Optional[Dict[str, Any]]:
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not cand:
            return None
        return {
            "candidate_id": cand.candidate_id,
            "name": cand.name,
            "email": cand.email,
            "cohort_tag": cand.cohort_tag,
            "resume_text": cand.resume_text,
            "skills_extracted": cand.skills_extracted or [],
            "experience_years": cand.experience_years,
            "education": cand.education,
            "current_stage": cand.current_stage,
            "target_jd_id": cand.target_jd_id,
            "created_at": cand.created_at.isoformat() if cand.created_at else None
        }

    @staticmethod
    def get_job_description(db: Session, jd_id: str) -> Optional[Dict[str, Any]]:
        jd = db.query(JobDescription).filter(JobDescription.jd_id == jd_id).first()
        if not jd:
            return None
        return {
            "jd_id": jd.jd_id,
            "title": jd.title,
            "department": jd.department,
            "description": jd.description,
            "required_skills": jd.required_skills or [],
            "preferred_skills": jd.preferred_skills or [],
            "min_experience": jd.min_experience,
            "rubric_version": jd.rubric_version
        }

    @staticmethod
    def get_candidate_pipeline_status(db: Session, candidate_id: str) -> Dict[str, Any]:
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not cand:
            return {"candidate_id": candidate_id, "error": "Candidate not found"}
        return {
            "candidate_id": cand.candidate_id,
            "name": cand.name,
            "current_stage": cand.current_stage,
            "updated_at": cand.updated_at.isoformat() if cand.updated_at else None
        }

    @staticmethod
    def save_screening_result(
        db: Session,
        candidate_id: str,
        jd_id: str,
        score: float,
        matched_requirements: List[str],
        missing_requirements: List[str],
        experience_match: bool,
        evidence: List[str],
        rubric_version: str = "1.0",
        status: str = "COMPLETED"
    ) -> Dict[str, Any]:
        result = ScreeningResult(
            candidate_id=candidate_id,
            jd_id=jd_id,
            score=score,
            matched_requirements=matched_requirements,
            missing_requirements=missing_requirements,
            experience_match=experience_match,
            evidence=evidence,
            rubric_version=rubric_version,
            status=status
        )
        db.add(result)
        
        # Advance pipeline stage safely via FSM
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if cand:
            advance_stage_if_higher(cand, "RESUME_SCREENED")
            
        db.commit()
        db.refresh(result)
        return {
            "screening_id": result.screening_id,
            "candidate_id": candidate_id,
            "score": score,
            "status": status
        }

    @staticmethod
    def save_assessment_result(
        db: Session,
        candidate_id: str,
        jd_id: str,
        test_type: str,
        questions: List[Dict[str, Any]],
        answers: List[Dict[str, Any]],
        score: float,
        skill_breakdown: Dict[str, Any],
        evidence: List[str],
        confidence: float = 1.0,
        status: str = "COMPLETED"
    ) -> Dict[str, Any]:
        assessment = Assessment(
            candidate_id=candidate_id,
            jd_id=jd_id,
            test_type=test_type,
            questions=questions,
            answers=answers,
            score=score,
            skill_breakdown=skill_breakdown,
            evidence=evidence,
            confidence=confidence,
            status=status,
            completed_date=datetime.utcnow()
        )
        db.add(assessment)
        
        # Update stage safely via FSM
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if cand:
            if test_type == "TECHNICAL":
                advance_stage_if_higher(cand, "TECHNICAL_ASSESSED")
            elif test_type == "BEHAVIORAL":
                advance_stage_if_higher(cand, "BEHAVIORAL_ASSESSED")
                
        db.commit()
        db.refresh(assessment)
        return {
            "assessment_id": assessment.assessment_id,
            "test_type": test_type,
            "score": score,
            "status": status
        }

    @staticmethod
    def save_panel_decision(
        db: Session,
        candidate_id: str,
        jd_id: str,
        resume_score: float,
        skill_score: float,
        culture_score: float,
        merged_score: float,
        recommendation: str,
        strengths: List[str],
        gaps: List[str],
        disagreements: List[str],
        evidence: List[str],
        rubric_version: str = "1.0",
        natural_language_summary: Optional[str] = None,
        decision_factors: Optional[List[str]] = None,
        highlighted_concerns: Optional[List[str]] = None,
        highlighted_strengths: Optional[List[str]] = None,
        requires_four_eyes_review: bool = False,
        used_llm_synthesis: bool = False,
        synthesis_latency_ms: int = 0,
        synthesis_strategy: str = "template",
        synthesis_error: Optional[str] = None
    ) -> Dict[str, Any]:
        decision = PanelDecision(
            candidate_id=candidate_id,
            jd_id=jd_id,
            resume_score=resume_score,
            skill_score=skill_score,
            culture_score=culture_score,
            merged_score=merged_score,
            recommendation=recommendation,
            strengths=strengths,
            gaps=gaps,
            disagreements=disagreements,
            evidence=evidence,
            rubric_version=rubric_version,
            natural_language_summary=natural_language_summary,
            decision_factors=decision_factors or [],
            highlighted_concerns=highlighted_concerns or [],
            highlighted_strengths=highlighted_strengths or [],
            requires_four_eyes_review=requires_four_eyes_review,
            used_llm_synthesis=used_llm_synthesis,
            synthesis_latency_ms=synthesis_latency_ms,
            synthesis_strategy=synthesis_strategy,
            synthesis_error=synthesis_error
        )
        db.add(decision)
        
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if cand:
            advance_stage_if_higher(cand, "PANEL_EVALUATED")
            
        db.commit()
        db.refresh(decision)
        return {
            "decision_id": decision.decision_id,
            "merged_score": merged_score,
            "recommendation": recommendation
        }

    @staticmethod
    def save_bias_check(
        db: Session,
        decision_id: str,
        candidate_id: str,
        flag_status: str,
        reason: str,
        cohort_breakdown: Dict[str, Any],
        requires_human_review: bool = True
    ) -> Dict[str, Any]:
        bias = BiasCheck(
            decision_id=decision_id,
            candidate_id=candidate_id,
            flag_status=flag_status,
            reason=reason,
            cohort_breakdown=cohort_breakdown,
            requires_human_review=requires_human_review
        )
        db.add(bias)
        
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if cand:
            advance_stage_if_higher(cand, "HUMAN_REVIEW_PENDING")
            
        db.commit()
        db.refresh(bias)
        return {
            "check_id": bias.check_id,
            "flag_status": flag_status,
            "requires_human_review": requires_human_review
        }

    @staticmethod
    def save_human_review(
        db: Session,
        candidate_id: str,
        reviewer_id: str,
        reviewer_name: str,
        decision: str,
        notes: str,
        decision_id: Optional[str] = None,
        bias_check_id: Optional[str] = None
    ) -> Dict[str, Any]:
        review = HumanReview(
            candidate_id=candidate_id,
            decision_id=decision_id,
            bias_check_id=bias_check_id,
            reviewer_id=reviewer_id,
            reviewer_name=reviewer_name,
            decision=decision,
            notes=notes,
            timestamp=datetime.utcnow()
        )
        db.add(review)
        
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if cand:
            cand.current_stage = "DECIDED"
            
        db.commit()
        db.refresh(review)
        return {
            "review_id": review.review_id,
            "candidate_id": candidate_id,
            "decision_id": decision_id,
            "bias_check_id": bias_check_id,
            "decision": decision,
            "reviewer": reviewer_name
        }

    @staticmethod
    def get_candidate_history(db: Session, candidate_id: str) -> Dict[str, Any]:
        cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
        if not cand:
            return {"error": "Candidate not found"}
            
        logs = db.query(AuditLog).filter(AuditLog.candidate_id == candidate_id).order_by(AuditLog.timestamp.asc()).all()
        return {
            "candidate_id": candidate_id,
            "name": cand.name,
            "current_stage": cand.current_stage,
            "timeline": [
                {
                    "log_id": l.log_id,
                    "stage": l.stage,
                    "event": l.event,
                    "agent": l.agent,
                    "input_reference": l.input_reference,
                    "output": l.output,
                    "rubric_version": l.rubric_version,
                    "timestamp": l.timestamp.isoformat()
                }
                for l in logs
            ]
        }
