import os
from pydantic_settings import BaseSettings
from typing import Optional, List, Literal

class Settings(BaseSettings):
    PROJECT_NAME: str = "JASIPA - Job Applicant Screening & Interview Panel Agent"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "jasipa-super-secret-jwt-key-2026")
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 # 24 hours
    
    # Database: Supports SQLite (default for quick zero-setup local dev/test) & PostgreSQL
    DATABASE_URL: str = os.getenv(
        "DATABASE_URL", 
        "sqlite:///./jasipa.db"
    )
    
    # LLM Configuration (Google Gemini)
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "gemini") # "gemini" or "mock"
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    
    # File storage
    UPLOAD_DIR: str = os.getenv("UPLOAD_DIR", "./uploads")
    
    # Bias detection thresholds
    BIAS_DISPARITY_THRESHOLD: float = 0.80 # 4/5ths rule (80% rule)

    FALLBACK_STRATEGY_CHAIN: List[str] = ["llm", "regex", "heuristic", "star", "human_expert"]
    FALLBACK_TIMEOUT_SECONDS: float = 30.0
    FALLBACK_ALERT_THRESHOLD: float = 20.0
    ENABLE_HUMAN_EXPERT_FALLBACK: bool = True
    
    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore"

settings = Settings()


class PanelCoordinatorConfig(BaseSettings):
    use_llm_synthesis: bool = True
    llm_synthesis_model: str = "gemini-1.5-flash"
    synthesis_timeout_seconds: int = 10
    explanation_detail_level: Literal["brief", "detailed", "comprehensive"] = "detailed"

    class Config:
        env_prefix = "PANEL_"
        extra = "ignore"


panel_coordinator_config = PanelCoordinatorConfig()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
