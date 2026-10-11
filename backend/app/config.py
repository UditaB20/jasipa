import os
import secrets
import warnings
from pydantic_settings import BaseSettings
from typing import Optional, List, Literal

_INSECURE_DEFAULT_KEYS = {"", "jasipa-super-secret-jwt-key-2026", "change-me"}


class Settings(BaseSettings):
    PROJECT_NAME: str = "JASIPA - Job Applicant Screening & Interview Panel Agent"
    API_V1_STR: str = "/api"
    SECRET_KEY: str = ""
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 8

    # Browser origins allowed to call the API (comma-separated in the environment).
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://127.0.0.1:5173"]

    # Database: SQLite for zero-setup local runs, PostgreSQL in docker-compose.
    DATABASE_URL: str = "sqlite:///./jasipa.db"

    # LLM configuration (Google Gemini). "mock" disables network calls and uses deterministic strategies.
    GEMINI_API_KEY: Optional[str] = None
    LLM_PROVIDER: str = "gemini"
    LLM_MODEL: str = "gemini-2.5-flash"

    # Resume storage. Files are stored under random names and never served statically.
    UPLOAD_DIR: str = "./uploads"
    MAX_RESUME_BYTES: int = 5 * 1024 * 1024

    # Sandboxed code execution: "subprocess" (rlimits + audit hook) or "docker" (no network, read-only FS).
    SANDBOX_BACKEND: Literal["subprocess", "docker"] = "subprocess"
    SANDBOX_DOCKER_IMAGE: str = "python:3.12-alpine"
    SANDBOX_TIMEOUT_SECONDS: float = 4.0
    SANDBOX_MEMORY_MB: int = 256
    SANDBOX_MAX_CODE_CHARS: int = 20000
    SANDBOX_SAMPLE_RUNS_PER_QUESTION: int = 15

    # Bias detection
    BIAS_DISPARITY_THRESHOLD: float = 0.80  # 4/5ths screen
    BIAS_SIGNIFICANCE_LEVEL: float = 0.05   # two-sided Fisher's exact test
    BIAS_MIN_GROUP_SIZE: int = 5            # below this a group comparison is reported as insufficient data

    FALLBACK_STRATEGY_CHAIN: List[str] = ["llm", "regex", "heuristic", "star", "human_expert"]
    FALLBACK_TIMEOUT_SECONDS: float = 30.0
    FALLBACK_ALERT_THRESHOLD: float = 20.0
    ENABLE_HUMAN_EXPERT_FALLBACK: bool = True

    class Config:
        env_file = [".env", "../.env"]
        extra = "ignore"


settings = Settings()

if settings.SECRET_KEY in _INSECURE_DEFAULT_KEYS:
    # A published default key would let anyone mint HR tokens. Use a per-process random key instead;
    # sessions then reset on restart, which is acceptable for local development.
    warnings.warn("SECRET_KEY is not configured; using a random per-process key. Set SECRET_KEY in .env.")
    settings.SECRET_KEY = secrets.token_urlsafe(48)


class PanelCoordinatorConfig(BaseSettings):
    use_llm_synthesis: bool = True
    llm_synthesis_model: str = "gemini-2.5-flash"
    synthesis_timeout_seconds: int = 10
    explanation_detail_level: Literal["brief", "detailed", "comprehensive"] = "detailed"

    class Config:
        env_prefix = "PANEL_"
        extra = "ignore"


panel_coordinator_config = PanelCoordinatorConfig()

os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
