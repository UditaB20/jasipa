from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import inspect, text
from app.config import settings
from app.database.session import engine, Base
from app.api.auth import router as auth_router
from app.api.jobs import router as jobs_router
from app.api.candidates import router as candidates_router
from app.api.assessments import router as assessments_router
from app.api.pipeline import router as pipeline_router
from app.api.reviews import router as reviews_router
from app.api.bias import router as bias_router
from app.api.audit import router as audit_router
from app.api.mcp_api import router as mcp_router
from app.api.candidate_portal import router as candidate_router
from app.api.learning import router as learning_router
from app.api.admin import router as admin_router

# Create all database tables
Base.metadata.create_all(bind=engine)
# Lightweight additive migration for installations created before outcome manager fields.
if "manager_name" not in {column["name"] for column in inspect(engine).get_columns("hiring_outcomes")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE hiring_outcomes ADD COLUMN manager_name VARCHAR"))
if "promotion_date" not in {column["name"] for column in inspect(engine).get_columns("hiring_outcomes")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE hiring_outcomes ADD COLUMN promotion_date TIMESTAMP"))
if "manager_email" not in {column["name"] for column in inspect(engine).get_columns("hiring_outcomes")}:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE hiring_outcomes ADD COLUMN manager_email VARCHAR(254)"))
outcome_columns = {column["name"] for column in inspect(engine).get_columns("hiring_outcomes")}
for column_name, sql_type in (("role", "VARCHAR(200)"), ("manager_id", "VARCHAR(160)"), ("department", "VARCHAR(160)"),
                              ("departure_date", "TIMESTAMP"), ("tenure_days", "INTEGER"),
                              ("promotion_role", "VARCHAR(200)"), ("performance_comments", "TEXT"),
                              ("technical_skills_rating", "FLOAT"), ("communication_rating", "FLOAT"),
                              ("leadership_rating", "FLOAT"), ("rehire_eligible", "BOOLEAN"),
                              ("recorded_date", "TIMESTAMP"), ("last_updated", "TIMESTAMP")):
    if column_name not in outcome_columns:
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE hiring_outcomes ADD COLUMN {column_name} {sql_type}"))
panel_columns = {column["name"] for column in inspect(engine).get_columns("panel_decisions")}
for column_name, sql_type in (("natural_language_summary", "TEXT"), ("decision_factors", "JSON"),
                              ("highlighted_strengths", "JSON"), ("highlighted_concerns", "JSON"),
                              ("used_llm_synthesis", "BOOLEAN"), ("synthesis_latency_ms", "INTEGER"),
                              ("synthesis_strategy", "VARCHAR(80)"), ("synthesis_error", "TEXT")):
    if column_name not in panel_columns:
        with engine.begin() as connection:
            connection.execute(text(f"ALTER TABLE panel_decisions ADD COLUMN {column_name} {sql_type}"))
metric_columns = {column["name"] for column in inspect(engine).get_columns("strategy_metrics")}
if "fallback_level" not in metric_columns:
    with engine.begin() as connection:
        connection.execute(text("ALTER TABLE strategy_metrics ADD COLUMN fallback_level INTEGER NOT NULL DEFAULT 0"))

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="HR-side Agentic AI Candidate Screening, Multi-Agent Panel, and Bias Governance System",
    version="1.0.0"
)

# CORS middleware for React Vite Frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API Routers
app.include_router(auth_router, prefix=settings.API_V1_STR)
app.include_router(jobs_router, prefix=settings.API_V1_STR)
app.include_router(candidates_router, prefix=settings.API_V1_STR)
app.include_router(assessments_router, prefix=settings.API_V1_STR)
app.include_router(pipeline_router, prefix=settings.API_V1_STR)
app.include_router(reviews_router, prefix=settings.API_V1_STR)
app.include_router(bias_router, prefix=settings.API_V1_STR)
app.include_router(audit_router, prefix=settings.API_V1_STR)
app.include_router(mcp_router, prefix=settings.API_V1_STR)
app.include_router(candidate_router, prefix=settings.API_V1_STR)
app.include_router(learning_router, prefix=settings.API_V1_STR)
app.include_router(admin_router, prefix=settings.API_V1_STR)

@app.get("/")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "governance_rule": "AI MUST NEVER AUTONOMOUSLY REJECT OR HIRE A CANDIDATE",
        "version": "1.0.0",
        "docs_url": "/docs"
    }

@app.get("/health")
def health_check():
    return {"status": "healthy"}
