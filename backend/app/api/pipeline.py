from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.auth.security import require_hr
from app.database.models import Candidate
from app.database.session import get_db
from app.services.pipeline_service import PipelineError, run_candidate_pipeline, screen_candidate

router = APIRouter(prefix="/pipeline", tags=["Agent Pipeline Orchestration"])


class PipelineRunRequest(BaseModel):
    candidate_id: str
    jd_id: Optional[str] = None


def _candidate(db: Session, candidate_id: str) -> Candidate:
    cand = db.query(Candidate).filter(Candidate.candidate_id == candidate_id).first()
    if not cand:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return cand


@router.post("/run-screen-resume")
def run_screen_resume(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    cand = _candidate(db, req.candidate_id)
    if cand.current_stage == "DECIDED":
        raise HTTPException(status_code=409, detail="A final decision has already been recorded for this candidate.")
    try:
        return screen_candidate(db, cand, actor=current_user["email"])
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/run-full-graph")
def run_full_graph_orchestration(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Runs the full swarm (screening, skill, behavioral → panel → bias check) and leaves the candidate awaiting a human decision."""
    cand = _candidate(db, req.candidate_id)
    try:
        return run_candidate_pipeline(db, cand, actor=current_user["email"], jd_id=req.jd_id)
    except PipelineError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.detail)


@router.post("/run-panel")
def run_panel_synthesis(req: PipelineRunRequest, current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Backwards-compatible alias returning only the panel decision and its bias check."""
    result = run_full_graph_orchestration(req, current_user, db)
    return {"panel_decision": result.get("panel_result"), "bias_check": result.get("bias_result")}
