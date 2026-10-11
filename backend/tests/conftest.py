"""Test configuration: an isolated, freshly seeded SQLite database per test session.

Environment variables are set before any app module is imported so the app never touches the
developer's database, upload folder or LLM provider.
"""
import importlib.util
import os
import sys
import tempfile

_TMP = tempfile.mkdtemp(prefix="jasipa-tests-")
os.environ["DATABASE_URL"] = f"sqlite:///{_TMP}/test.db"
os.environ["UPLOAD_DIR"] = f"{_TMP}/uploads"
os.environ["LLM_PROVIDER"] = "mock"
os.environ["GEMINI_API_KEY"] = ""
os.environ["SECRET_KEY"] = "pytest-only-secret-key-not-for-production-use"
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest  # noqa: E402


@pytest.fixture(scope="session", autouse=True)
def seeded_database():
    path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts", "seed_data.py")
    spec = importlib.util.spec_from_file_location("seed_data", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.seed_database()
    yield


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


def _login(client, email, password):
    response = client.post("/api/auth/login", json={"email": email, "password": password})
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['access_token']}"}


@pytest.fixture(scope="session")
def hr_headers(client):
    return _login(client, "hr@jasipa.ai", "admin123")


@pytest.fixture(scope="session")
def reviewer_headers(client):
    return _login(client, "reviewer@jasipa.ai", "reviewer123")


@pytest.fixture
def register_candidate(client):
    """Creates a fresh candidate portal account and returns (headers, candidate_id)."""
    import uuid

    def make(name="Taylor Applicant"):
        email = f"applicant-{uuid.uuid4().hex[:12]}@example.org"
        response = client.post("/api/auth/register", json={"name": name, "email": email, "password": "s3cure-pass!"})
        assert response.status_code == 201, response.text
        body = response.json()
        return {"Authorization": f"Bearer {body['access_token']}"}, body["user"]["candidate_id"]
    return make
