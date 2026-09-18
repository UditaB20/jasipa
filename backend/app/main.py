from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
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

# Create all database tables
Base.metadata.create_all(bind=engine)

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
