from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database.session import get_db
from app.services.bias_service import calculate_cohort_analytics
from app.auth.security import require_hr

router = APIRouter(prefix="/bias", tags=["Bias & Cohort Analytics"])


@router.get("/analytics")
def get_cohort_analytics(current_user: dict = Depends(require_hr), db: Session = Depends(get_db)):
    """Cohort selection-rate comparison at the AI recommendation and final human decision stages."""
    return calculate_cohort_analytics(db)
