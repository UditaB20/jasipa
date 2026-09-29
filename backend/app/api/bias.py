from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.bias_service import calculate_cohort_analytics
from app.schemas.bias import CohortAnalyticsResponse
from app.auth.security import require_hr

router = APIRouter(prefix="/bias", tags=["Bias & Cohort Analytics"])

@router.get("/analytics", response_model=CohortAnalyticsResponse)
def get_cohort_analytics(current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """
    Returns aggregated statistical parity & cohort disparity analysis across candidate pool.
    Restricted to HR personnel.
    """
    return calculate_cohort_analytics(db)
