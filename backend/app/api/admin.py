from datetime import datetime, timedelta
from typing import Optional, Literal
from pydantic import BaseModel, Field
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.auth.security import require_hr
from app.config import settings, panel_coordinator_config
from app.database.models import StrategyMetric, HumanExpertTask, Candidate, HiringOutcome, BiasCheck
from app.database.session import get_db
from app.services.bias_service import calculate_cohort_analytics

router = APIRouter(prefix="/admin", tags=["HR Administration & Monitoring"])


class PanelCoordinatorConfigPatch(BaseModel):
    use_llm_synthesis: Optional[bool] = None
    llm_synthesis_model: Optional[str] = Field(None, min_length=1, max_length=120)
    synthesis_timeout_seconds: Optional[int] = Field(None, ge=1, le=60)
    explanation_detail_level: Optional[Literal["brief", "detailed", "comprehensive"]] = None


class ExpertTaskUpdate(BaseModel):
    status: Literal["PENDING", "IN_PROGRESS", "COMPLETED"]
    assigned_to: Optional[str] = Field(None, max_length=160)


@router.get("/strategy-effectiveness")
def strategy_effectiveness(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    rows = db.query(StrategyMetric).filter(StrategyMetric.timestamp >= since).all()
    by_strategy = {}
    invocations = {}
    for row in rows:
        metric = by_strategy.setdefault(row.strategy_name, {"attempts": 0, "failures": 0, "latency_ms": 0})
        metric["attempts"] += 1
        metric["failures"] += int(not row.success)
        metric["latency_ms"] += row.latency_ms
        invocations.setdefault(row.invocation_id, []).append(row)
    strategies = {name: {"attempts": m["attempts"], "failures": m["failures"],
                         "failure_rate": round(m["failures"] / m["attempts"], 3) if m["attempts"] else None,
                         "average_latency_ms": round(m["latency_ms"] / m["attempts"], 1) if m["attempts"] else None}
                  for name, m in by_strategy.items()}
    completed = [attempts for attempts in invocations.values() if any(row.success for row in attempts)]
    fallbacks = [attempts for attempts in completed if min(row.fallback_level for row in attempts if row.success) > 0]
    rate = len(fallbacks) / len(completed) if completed else None
    percent = rate * 100 if rate is not None else None
    return {"period_days": 30, "evaluation_invocations": len(completed), "fallback_invocations": len(fallbacks),
            "fallback_rate_percent": round(percent, 2) if percent is not None else None,
            "alert_threshold_percent": settings.FALLBACK_ALERT_THRESHOLD,
            "alert": percent is not None and percent > settings.FALLBACK_ALERT_THRESHOLD,
            "alert_message": (f"Fallback rate {percent:.1f}% exceeds {settings.FALLBACK_ALERT_THRESHOLD:.1f}% threshold."
                              if percent is not None and percent > settings.FALLBACK_ALERT_THRESHOLD else None),
            "by_strategy": strategies}


@router.get("/expert-tasks")
def list_expert_tasks(status: str = "PENDING", user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    query = db.query(HumanExpertTask)
    if status.upper() != "ALL":
        query = query.filter(HumanExpertTask.status == status.upper())
    return [{"task_id": task.task_id, "candidate_id": task.candidate_id,
             "candidate_name": candidate.name if (candidate := db.query(Candidate).filter_by(candidate_id=task.candidate_id).first()) else None,
             "agent_name": task.agent_name, "reason": task.reason, "status": task.status,
             "assigned_to": task.assigned_to, "created_at": task.created_at.isoformat() if task.created_at else None}
            for task in query.order_by(HumanExpertTask.created_at.desc()).all()]


@router.patch("/expert-tasks/{task_id}")
def update_expert_task(task_id: str, payload: ExpertTaskUpdate, user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    task = db.query(HumanExpertTask).filter_by(task_id=task_id).first()
    if not task:
        raise HTTPException(status_code=404, detail="Expert task not found")
    task.status = payload.status
    if payload.assigned_to:
        task.assigned_to = payload.assigned_to
    db.commit()
    return {"task_id": task.task_id, "status": task.status, "assigned_to": task.assigned_to}


@router.get("/panel-coordinator-config")
def get_panel_coordinator_config(user: dict = Depends(require_hr)):
    return panel_coordinator_config.model_dump()


@router.patch("/panel-coordinator-config")
def patch_panel_coordinator_config(payload: PanelCoordinatorConfigPatch, user: dict = Depends(require_hr)):
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(panel_coordinator_config, key, value)
    return panel_coordinator_config.model_dump()


@router.get("/metrics/panel-synthesis")
def panel_synthesis_metrics(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    since = datetime.utcnow() - timedelta(days=30)
    rows = db.query(StrategyMetric).filter(StrategyMetric.agent_name == "PanelCoordinatorAgent",
                                            StrategyMetric.timestamp >= since).all()
    groups = {}
    for row in rows:
        groups.setdefault(row.invocation_id, []).append(row)
    total = len(groups)
    llm_attempted = sum(any(row.strategy_name == "llm" for row in attempts) for attempts in groups.values())
    llm_succeeded = sum(any(row.strategy_name == "llm" and row.success for row in attempts) for attempts in groups.values())
    llm_failed = llm_attempted - llm_succeeded
    latencies = [sum(row.latency_ms for row in attempts) for attempts in groups.values()]
    fail_rate = llm_failed / llm_attempted if llm_attempted else None
    return {"period_days": 30, "synthesis_invocations": total, "llm_attempted": llm_attempted,
            "llm_succeeded": llm_succeeded, "llm_failure_rate": round(fail_rate, 3) if fail_rate is not None else None,
            "average_total_latency_ms": round(sum(latencies) / len(latencies), 1) if latencies else None,
            "alert_threshold_percent": 10,
            "alert": fail_rate is not None and fail_rate > 0.10}


@router.get("/bias-checks/summary")
def bias_check_summary(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    checks = db.query(BiasCheck).all()
    flagged = sum(check.flag_status == "FLAGGED" for check in checks)
    return {"checks_recorded": len(checks), "flagged_checks": flagged,
            "flag_rate_percent": round(flagged / len(checks) * 100, 1) if checks else None,
            "insufficient_data_checks": sum(any(item.get("flag_status") == "INSUFFICIENT_DATA"
                for item in (check.cohort_breakdown or {}).get("checks", [])) for check in checks),
            "notice": "Aggregate screening signals require HR review and are not findings about individual merit."}


@router.get("/bias-checks/by-cohort")
def bias_checks_by_cohort(user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    analytics = calculate_cohort_analytics(db)
    return {"total_evaluated": analytics["total_evaluated"],
            "cohorts": [{"cohort_name": row["cohort_name"], "sample_size": row["total_candidates"],
                         "proceed_rate": row["proceed_rate"] if row["total_candidates"] >= 10 else None,
                         "flagged_disparity": row["flagged_disparity"] if row["total_candidates"] >= 10 else None,
                         "confidence_level": "low" if row["total_candidates"] < 10 else "medium" if row["total_candidates"] < 30 else "high"}
                        for row in analytics["cohorts"]],
            "notice": "Rates and flags are suppressed below n=10; aggregate results are descriptive and may be confounded by role or process differences."}


@router.get("/outcomes")
def outcome_summary(cohort_tag: Optional[str] = None, user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    query = db.query(HiringOutcome, Candidate).join(Candidate)
    if cohort_tag:
        query = query.filter(Candidate.cohort_tag == cohort_tag)
    rows = query.all()
    sample = len(rows)
    if sample < 10:
        return {"sample_size": sample, "confidence_level": "low", "status": "INSUFFICIENT_DATA",
                "metrics": None, "notice": "Outcome statistics are suppressed below n=10."}
    rated = [outcome.performance_rating for outcome, _ in rows if outcome.performance_rating is not None]
    known = [outcome.still_employed for outcome, _ in rows if outcome.still_employed is not None]
    return {"sample_size": sample, "confidence_level": "medium" if sample < 30 else "high", "status": "AVAILABLE",
            "metrics": {"rated_count": len(rated), "average_performance": round(sum(rated) / len(rated), 2) if rated else None,
                        "retention_count": len(known), "retention_rate": round(sum(known) / len(known), 3) if known else None},
            "notice": "Outcome rates are descriptive and not adjusted for job, tenure, or other confounders."}
