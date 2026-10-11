from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database.session import engine
from app.database.migrations import run_additive_migrations
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
from app.api.dashboard import router as dashboard_router

# Create tables and add any columns introduced since the database was first created.
run_additive_migrations(engine)

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="HR-side candidate screening, multi-agent panel synthesis, bias monitoring and human-reviewed decisions.",
    version="1.1.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE"],
    allow_headers=["Authorization", "Content-Type"],
)

for router in (auth_router, jobs_router, candidates_router, assessments_router, pipeline_router,
               reviews_router, bias_router, audit_router, mcp_router, candidate_router,
               learning_router, admin_router, dashboard_router):
    app.include_router(router, prefix=settings.API_V1_STR)


@app.get("/")
def root():
    return {
        "status": "online",
        "system": settings.PROJECT_NAME,
        "governance_rule": "AI MUST NEVER AUTONOMOUSLY REJECT OR HIRE A CANDIDATE",
        "version": "1.1.0",
        "docs_url": "/docs"
    }


@app.get("/health")
def health_check():
    return {"status": "healthy"}
