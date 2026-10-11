"""Test configuration: an isolated database seeded from the Kaggle Resume Dataset.

Environment variables are set before any app module is imported so the app never touches the
developer's database, upload folder or LLM provider. Candidates that need assessments and decisions
are created through the real API (portal registration, resume upload, application, submissions,
pipeline), because the dataset itself contains no assessment data.

Every test carries a docstring with "Feature:", "Input:" and "Expected:" lines; scripts/test_report.py
turns those plus the executed results into the test-case table.
"""
import importlib.util
import os
import sys
import tempfile
import uuid

_TMP = tempfile.mkdtemp(prefix="jasipa-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["SECRET_KEY"] = "pytest-only-secret-key-not-for-production-use"
BACKEND = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, BACKEND)
CSV_PATH = os.path.join(BACKEND, "..", "Resume.csv")

import pytest  # noqa: E402

from helpers import STRONG_RESUME, WEAK_RESUME, answers_for, make_docx, make_pdf  # noqa: E402,F401


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    spec = importlib.util.spec_from_file_location("seed_data", os.path.join(BACKEND, "scripts", "seed_data.py"))
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    stats = module.seed_database(CSV_PATH, per_category=4, demo_accounts=True)
    yield stats


@pytest.fixture
def db():
    from app.database.session import SessionLocal
    session = SessionLocal()
    yield session
    session.close()


@pytest.fixture(scope="session")
def client(seeded_database):
    from fastapi.testclient import TestClient
    from app.main import app
    return TestClient(app)


def login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def hr_headers(client):
    return login(client, "hr@jasipa.ai", "admin123")


@pytest.fixture(scope="session")
def reviewer_headers(client):
    return login(client, "reviewer@jasipa.ai", "reviewer123")


@pytest.fixture(scope="session")
def software_job(client, hr_headers):
    """A programming role created through the HR API, so assessments include a sandboxed coding challenge."""
    response = client.post("/api/jobs/", headers=hr_headers, json={
        "title": "Backend Engineer", "department": "Engineering",
        "description": "Build Python services for billing.\nDesign SQL schemas for reporting.\nImplement algorithms for reconciliation.",
        "required_skills": ["Python", "SQL", "Algorithms"], "preferred_skills": ["Docker"], "min_experience": 3})
    assert response.status_code == 200, response.text
    return response.json()


def register_candidate(client, name="Taylor Applicant"):
    email = f"applicant-{uuid.uuid4().hex[:12]}@example.org"
    response = client.post("/api/auth/register", json={"name": name, "email": email, "password": "s3cure-pass!"})
    assert response.status_code == 201, response.text
    body = response.json()
    return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["candidate_id"]


@pytest.fixture
def new_candidate(client):
    return lambda name="Taylor Applicant": register_candidate(client, name)


@pytest.fixture
def evaluated_candidate(client, hr_headers, software_job, db):
    """Portal candidate → resume upload → apply → both assessments → full pipeline. Returns the candidate id.

    quality: "strong" (good resume and answers), "weak", or "mixed" (strong resume, failing technical,
    good behavioral — produces a large score divergence that requires two reviewers).
    """
    def make(quality="strong", name="Pipeline Candidate"):
        headers, candidate_id = register_candidate(client, name)
        resume = WEAK_RESUME if quality == "weak" else STRONG_RESUME
        assert client.post("/api/candidate/upload-resume", headers=headers,
                           files={"file": ("cv.pdf", make_pdf(resume), "application/pdf")}).status_code == 200
        assert client.post("/api/candidate/apply", headers=headers, json={"jd_id": software_job["jd_id"]}).status_code == 200
        portal = client.get("/api/candidate/assessments", headers=headers).json()
        tech_quality = "weak" if quality in ("weak", "mixed") else "strong"
        db.expire_all()
        for kind, part, q in (("technical", "technical", tech_quality), ("behavioral", "behavioral", quality)):
            answers = answers_for(portal[part]["questions"], q, db, software_job["jd_id"], kind)
            assert client.post(f"/api/candidate/submit-{kind}", headers=headers, json={"answers": answers}).status_code == 200
        run = client.post("/api/pipeline/run-full-graph", headers=hr_headers, json={"candidate_id": candidate_id})
        assert run.status_code == 200, run.text
        return candidate_id
    return make
