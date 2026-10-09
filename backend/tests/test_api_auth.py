import pytest
from fastapi.testclient import TestClient
from app.main import app
from app.auth.security import create_access_token

client = TestClient(app)

def test_unauthenticated_requests_blocked():
    """All sensitive HR and pipeline endpoints must reject unauthenticated requests with 401."""
    routes_to_test = [
        ("GET", "/api/candidates"),
        ("POST", "/api/candidates"),
        ("POST", "/api/mcp/execute"),
        ("GET", "/api/mcp/tools"),
        ("POST", "/api/pipeline/run-full-graph"),
        ("POST", "/api/pipeline/run-panel"),
        ("POST", "/api/reviews/decide"),
        ("POST", "/api/jobs")
    ]
    for method, route in routes_to_test:
        if method == "GET":
            response = client.get(route)
        else:
            response = client.post(route, json={})
        assert response.status_code == 401, f"Expected 401 for {method} {route}, got {response.status_code}"

def test_candidate_forbidden_from_hr_routes():
    """Candidates authenticated via JWT must receive 403 Forbidden when accessing HR routes."""
    candidate_token = create_access_token({"sub": "test@candidate.com", "role": "candidate", "candidate_id": "CAND-001-ELENA"})
    headers = {"Authorization": f"Bearer {candidate_token}"}

    hr_routes = [
        client.get("/api/candidates", headers=headers),
        client.post("/api/mcp/execute", json={"name": "get_candidate_profile", "arguments": {"candidate_id": "CAND-001-ELENA"}}, headers=headers),
        client.post("/api/pipeline/run-full-graph", json={"candidate_id": "CAND-001-ELENA"}, headers=headers),
        client.post("/api/reviews/decide", json={"candidate_id": "CAND-001-ELENA", "decision": "APPROVE"}, headers=headers)
    ]
    for resp in hr_routes:
        assert resp.status_code == 403, f"Expected 403 for candidate accessing HR route, got {resp.status_code}"

def test_applicant_isolation_enforced():
    """Candidate A cannot inspect Candidate B's assessments (enforces 403 Forbidden)."""
    token_cand_a = create_access_token({"sub": "elena@tech.io", "role": "candidate", "candidate_id": "CAND-001-ELENA"})
    headers = {"Authorization": f"Bearer {token_cand_a}"}

    # Attempting to query Candidate B's assessments
    resp = client.get("/api/assessments/candidate/CAND-002-MARCUS", headers=headers)
    assert resp.status_code == 403, f"Expected 403 when querying another candidate's assessment, got {resp.status_code}"

    # Querying own assessments succeeds
    resp_own = client.get("/api/assessments/candidate/CAND-001-ELENA", headers=headers)
    assert resp_own.status_code == 200

def test_candidate_explanation_and_rights():
    """Candidate can access plain-language AI governance disclosures and invoke re-review appeal."""
    token = create_access_token({"sub": "elena@tech.io", "role": "candidate", "candidate_id": "CAND-001-ELENA"})
    headers = {"Authorization": f"Bearer {token}"}

    # 1. Get transparent explanation
    resp = client.get("/api/candidate/explanation", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["governance_guarantee"]["autonomous_decisions_prohibited"] is True
    assert data["governance_guarantee"]["human_in_the_loop_mandatory"] is True
    assert data["candidate_rights"]["right_to_human_re_review"] is True

    # 2. Invoke human re-review request
    resp_appeal = client.post("/api/candidate/request-re-review", headers=headers)
    assert resp_appeal.status_code == 200
    appeal_data = resp_appeal.json()
    assert appeal_data["status"] == "SUCCESS"
    assert "tamper-evident audit ledger" in appeal_data["message"]
