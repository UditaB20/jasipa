from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.bias_service import calculate_cohort_analytics
from app.schemas.bias import CohortAnalyticsResponse

router = APIRouter(prefix="/bias", tags=["Bias & Cohort Analytics"])

@router.get("/analytics", response_model=CohortAnalyticsResponse)
def get_cohort_analytics(db: Session = Depends(get_db)):
    """
    Returns aggregated statistical parity & cohort disparity analysis across candidate pool.
    """
    return calculate_cohort_analytics(db)
