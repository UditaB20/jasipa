import os
from pydantic_settings import BaseSettings
from typing import Optional

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
    
    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore"

settings = Settings()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
