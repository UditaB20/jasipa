from pydantic import BaseModel
from typing import Dict, Any, Optional
from datetime import datetime

class RubricBase(BaseModel):
    jd_id: str
    version: str = "1.0"
    resume_weight: float = 0.40
    skill_weight: float = 0.40
    culture_weight: float = 0.20
    criteria: Dict[str, Any]

class RubricCreate(RubricBase):
    pass

class RubricResponse(RubricBase):
    rubric_id: str
    created_at: datetime

    class Config:
        from_attributes = True
