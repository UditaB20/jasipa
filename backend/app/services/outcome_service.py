"""Business rules and persistence for authenticated, manager-attested hiring outcomes."""
from datetime import datetime, timezone
from typing import Any, Dict, List
from sqlalchemy.orm import Session
from app.database.models import Candidate, HiringOutcome, HumanReview
from app.schemas.outcome import HiringOutcomeCreate
from app.services.audit_service import log_event


class OutcomeRecordingService:
    def __init__(self, db: Session):
        self.db = db

    def validate_outcome_data(self, payload: HiringOutcomeCreate, actor: Dict[str, Any]) -> List[str]:
        errors = []
        manager_email = payload.manager_email.strip().lower()
        actor_email = str(actor.get("email", "")).strip().lower()
        if not actor_email or manager_email != actor_email:
            errors.append("Manager email must match the authenticated HR account submitting the outcome.")
        if "@" not in manager_email:
            errors.append("A valid manager email is required.")
        today = datetime.now(timezone.utc).date()
        if payload.hired_date.date() >= today:
            errors.append("Hire date must be before today.")
        if payload.promotion_date and payload.promotion_date.date() > today:
            errors.append("Promotion date cannot be in the future.")
        if payload.departure_date and payload.departure_date.date() > today:
            errors.append("Departure date cannot be in the future.")
        if payload.still_employed and payload.departure_date:
            errors.append("Departure date must be empty while the person is still employed.")
        if payload.still_employed and payload.attrition_reason:
            errors.append("Attrition reason applies only when the person is no longer employed.")
        return errors

    def check_outcome_completeness(self, payload: HiringOutcomeCreate) -> Dict[str, Any]:
        required = ("candidate_id", "hired_date", "performance_rating", "still_employed", "months_employed", "manager_email")
        missing = [field for field in required if getattr(payload, field, None) is None]
        return {"complete": not missing, "missing_fields": missing}

    def record_outcome(self, payload: HiringOutcomeCreate, actor: Dict[str, Any]) -> HiringOutcome:
        completeness = self.check_outcome_completeness(payload)
        errors = self.validate_outcome_data(payload, actor)
        if not completeness["complete"]:
            errors.extend(f"Required field missing: {field}." for field in completeness["missing_fields"])
        if errors:
            raise ValueError(" ".join(errors))
        candidate = self.db.query(Candidate).filter_by(candidate_id=payload.candidate_id).first()
        if not candidate:
            raise LookupError("Candidate not found")
        approved = self.db.query(HumanReview).filter_by(candidate_id=candidate.candidate_id, decision="APPROVE").first()
        if not approved:
            raise PermissionError("A human APPROVE decision is required before outcome recording.")
        data = payload.model_dump(exclude={"candidate_id"})
        data["manager_email"] = payload.manager_email.strip().lower()
        outcome = self.db.query(HiringOutcome).filter_by(candidate_id=candidate.candidate_id).first()
        if outcome is None:
            outcome = HiringOutcome(candidate_id=candidate.candidate_id,
                recorded_by=actor.get("email", "HR"), **data)
            self.db.add(outcome)
        else:
            for key, value in data.items():
                setattr(outcome, key, value)
            outcome.recorded_by = actor.get("email", "HR")
        self.db.commit()
        self.db.refresh(outcome)
        log_event(self.db, stage="HIRING_OUTCOME_RECORDED", event="Manager-attested hiring outcome created or updated",
                  agent="OutcomeRecordingService", candidate_id=candidate.candidate_id,
                  input_reference={"manager_email_verified_against_session": True},
                  output={"outcome_id": outcome.outcome_id, "hired_date": outcome.hired_date.isoformat(),
                          "performance_rating": outcome.performance_rating, "still_employed": outcome.still_employed})
        return outcome
