"""Authentication, data isolation, the end-to-end pipeline and the human-decision safeguards."""
import pytest

from app.auth.security import create_access_token
from app.database.models import Assessment, AuditLog, Candidate, HumanReview


def candidate_token(candidate_id):
    return {"Authorization": "Bearer " + create_access_token({"sub": "x@example.com", "role": "CANDIDATE", "candidate_id": candidate_id})}


# ---------- Authentication & authorisation ----------

@pytest.mark.parametrize("method,route", [
    ("GET", "/api/candidates/"), ("POST", "/api/candidates/"), ("GET", "/api/jobs/"), ("POST", "/api/jobs/"),
    ("GET", "/api/jobs/JD-SWE-101/rubric"), ("GET", "/api/assessments/questions/JD-SWE-101"),
    ("POST", "/api/pipeline/run-full-graph"), ("POST", "/api/reviews/decide"), ("GET", "/api/dashboard/summary"),
    ("POST", "/api/mcp/execute"), ("GET", "/api/audit/verify"),
])
def test_routes_require_authentication(client, method, route):
    response = client.request(method, route, json={})
    assert response.status_code == 401


def test_candidates_cannot_reach_hr_data(client):
    headers = candidate_token("CAND-001-ELENA")
    for method, route in [("GET", "/api/candidates/CAND-001-ELENA"), ("GET", "/api/assessments/candidate/CAND-001-ELENA"),
                          ("GET", "/api/audit/candidate/CAND-001-ELENA"), ("POST", "/api/reviews/decide"),
                          ("GET", "/api/assessments/questions/JD-SWE-101")]:
        assert client.request(method, route, json={}, headers=headers).status_code == 403, route


def test_imported_candidates_cannot_log_in_with_a_shared_default_password(client):
    response = client.post("/api/auth/login", json={"email": "marcus.vance@example.com", "password": "candidate123"})
    assert response.status_code == 401
    assert client.post("/api/auth/login", json={"email": "candidate@jasipa.ai", "password": "candidate123"}).status_code == 200


def test_registration_rejects_duplicates_and_weak_input(client):
    assert client.post("/api/auth/register", json={"name": "Elena", "email": "candidate@jasipa.ai", "password": "longenough1"}).status_code == 409
    assert client.post("/api/auth/register", json={"name": "A B", "email": "not-an-email", "password": "longenough1"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "A B", "email": "ok@example.com", "password": "short"}).status_code == 422


def test_removed_transparency_and_review_queue_endpoints_are_gone(client, hr_headers):
    headers = candidate_token("CAND-001-ELENA")
    assert client.get("/api/candidate/explanation", headers=headers).status_code == 404
    assert client.post("/api/candidate/request-re-review", headers=headers).status_code == 404
    assert client.get("/api/reviews/pending", headers=hr_headers).status_code in (404, 405)


# ---------- Candidate assessment flow ----------

def test_candidate_takes_assessments_with_objective_coding_scores(client, db):
    headers = {"Authorization": "Bearer " + client.post("/api/auth/login", json={"email": "student@jasipa.ai", "password": "student123"}).json()["access_token"]}
    portal = client.get("/api/candidate/assessments", headers=headers).json()
    technical = portal["technical"]["questions"]
    assert "correct_option" not in str(technical)
    mcq = next(q for q in technical if q["type"] == "mcq")
    assert len(mcq["options"]) == 4
    coding = next(q for q in technical if q["type"] == "coding")
    assert coding["coding"]["examples"]

    sample = client.post("/api/candidate/assessments/run-code", headers=headers,
                         json={"question_id": coding["question_id"], "code": "def merge_intervals(x):\n    return x"})
    assert sample.status_code == 200 and sample.json()["total"] == len(coding["coding"]["examples"])
    assert all(not t["hidden"] for t in sample.json()["tests"]), "practice runs never execute hidden tests"

    from app.database.models import QuestionSet
    full = db.query(QuestionSet).filter(QuestionSet.jd_id == "JD-SWE-101").first()
    reference = next(q for q in full.technical_questions if q["type"] == "coding")["coding"]["reference_solution"]
    answers = [{"question_id": q["question_id"], "answer_text": reference if q["type"] == "coding" else "B"} for q in technical]
    response = client.post("/api/candidate/submit-technical", json={"answers": answers}, headers=headers)
    assert response.status_code == 200, response.text
    assert client.post("/api/candidate/submit-technical", json={"answers": answers}, headers=headers).status_code == 409

    db.expire_all()
    stored = db.query(Assessment).filter(Assessment.candidate_id == "CAND-007-PRIYA", Assessment.test_type == "TECHNICAL").one()
    result = stored.execution_results[coding["question_id"]]
    assert result["status"] == "OK" and result["passed"] == result["total"]
    assert any(t["hidden"] for t in result["tests"])


# ---------- Pipeline orchestration ----------

def test_full_pipeline_runs_and_does_not_duplicate_assessments(client, hr_headers, db):
    before = db.query(Assessment).filter(Assessment.candidate_id == "CAND-006-SAMUEL").count()
    response = client.post("/api/pipeline/run-full-graph", json={"candidate_id": "CAND-006-SAMUEL"}, headers=hr_headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["current_stage"] == "HUMAN_REVIEW_PENDING"
    assert body["panel_result"]["recommendation"] in ("PROCEED_TO_HUMAN_REVIEW", "HUMAN_REVIEW_REQUIRED", "ADDITIONAL_INFORMATION_REQUIRED")
    assert body["bias_result"]["decision_id"] == body["panel_result"]["decision_id"]
    second = client.post("/api/pipeline/run-full-graph", json={"candidate_id": "CAND-006-SAMUEL"}, headers=hr_headers).json()
    assert second["round_number"] == body["round_number"] + 1
    db.expire_all()
    assert db.query(Assessment).filter(Assessment.candidate_id == "CAND-006-SAMUEL").count() == before


def test_pipeline_refuses_decided_candidates(client, hr_headers):
    response = client.post("/api/pipeline/run-full-graph", json={"candidate_id": "CAND-001-ELENA"}, headers=hr_headers)
    assert response.status_code == 409


# ---------- Human decisions ----------

def test_ai_cannot_write_a_rejection_through_mcp(client, hr_headers):
    response = client.post("/api/mcp/execute", headers=hr_headers, json={"name": "save_panel_decision", "arguments": {
        "candidate_id": "CAND-002-MARCUS", "jd_id": "JD-SWE-101", "merged_score": 10, "recommendation": "AUTO_REJECT"}}).json()
    assert response["isError"] and "not allowed" in response["error"]
    tools = [t["name"] for t in client.get("/api/mcp/tools", headers=hr_headers).json()["tools"]]
    assert "save_human_review" not in tools


def test_decision_requires_panel_and_bias_check(client, hr_headers):
    response = client.post("/api/reviews/decide", headers=hr_headers,
                           json={"candidate_id": "CAND-012-SOFIA", "decision": "APPROVE", "notes": "Looks good to me overall."})
    assert response.status_code == 409 and "panel" in response.json()["detail"].lower()


def test_decision_records_bias_check_and_closes_application(client, hr_headers, db):
    status = client.get("/api/reviews/candidate/CAND-002-MARCUS", headers=hr_headers).json()
    assert status["can_decide"] and status["bias_check_id"]
    response = client.post("/api/reviews/decide", headers=hr_headers, json={
        "candidate_id": "CAND-002-MARCUS", "decision": "REJECT", "decision_id": status["decision_id"],
        "notes": "Technical depth below the bar for a senior role."})
    assert response.status_code == 200, response.text
    assert response.json()["outcome"] == "FINAL" and response.json()["status"]["current_stage"] == "DECIDED"
    db.expire_all()
    log = db.query(AuditLog).filter(AuditLog.candidate_id == "CAND-002-MARCUS", AuditLog.event.like("Human decision recorded%")).one()
    assert log.input_reference["bias_check_id"] == status["bias_check_id"] and log.input_reference["bias_flag_status"]
    again = client.post("/api/reviews/decide", headers=hr_headers, json={
        "candidate_id": "CAND-002-MARCUS", "decision": "APPROVE", "notes": "Changing my mind after all."})
    assert again.status_code == 409


def test_escalated_decision_needs_two_agreeing_reviewers(client, hr_headers, reviewer_headers):
    status = client.get("/api/reviews/candidate/CAND-005-ROHAN", headers=hr_headers).json()
    assert status["requires_two_reviewers"]
    payload = {"candidate_id": "CAND-005-ROHAN", "decision": "APPROVE", "notes": "Strong resume; technical gap acceptable."}
    first = client.post("/api/reviews/decide", headers=hr_headers, json=payload).json()
    assert first["outcome"] == "AWAITING_SECOND_REVIEWER" and first["status"]["current_stage"] == "HUMAN_REVIEW_PENDING"
    assert client.post("/api/reviews/decide", headers=hr_headers, json=payload).status_code == 409, "same reviewer cannot sign twice"
    second = client.post("/api/reviews/decide", headers=reviewer_headers, json=payload).json()
    assert second["outcome"] == "FINAL" and second["status"]["current_stage"] == "DECIDED"


def test_stale_panel_decision_is_rejected_and_info_request_keeps_application_open(client, hr_headers):
    payload = {"candidate_id": "CAND-014-AISHA", "decision": "REQUEST_MORE_INFORMATION",
               "notes": "Please complete a follow-up technical interview.", "decision_id": "not-the-latest"}
    assert client.post("/api/reviews/decide", headers=hr_headers, json=payload).status_code == 409
    payload.pop("decision_id")
    response = client.post("/api/reviews/decide", headers=hr_headers, json=payload).json()
    assert response["status"]["current_stage"] == "INFO_REQUESTED"
    rerun = client.post("/api/pipeline/run-full-graph", json={"candidate_id": "CAND-014-AISHA"}, headers=hr_headers)
    assert rerun.status_code == 200 and rerun.json()["current_stage"] == "HUMAN_REVIEW_PENDING"


def test_stage_cannot_be_forced_through_patch(client, hr_headers):
    response = client.patch("/api/candidates/CAND-003-TARIQ", json={"current_stage": "DECIDED"}, headers=hr_headers)
    assert response.status_code == 400


# ---------- Audit ledger ----------

def test_audit_chain_verifies_and_detects_tampering(client, hr_headers, db):
    assert client.get("/api/audit/verify", headers=hr_headers).json()["verified"] is True
    entry = db.query(AuditLog).filter(AuditLog.stage == "BIAS_CHECKED").first()
    original = dict(entry.output)
    entry.output = {**original, "flag_status": "NO_INDICATOR_DETECTED"}
    db.commit()
    report = client.get("/api/audit/verify", headers=hr_headers).json()
    assert report["verified"] is False and any(i["log_id"] == entry.log_id for i in report["issues"])
    entry.output = original
    db.commit()
    assert client.get("/api/audit/verify", headers=hr_headers).json()["verified"] is True


def test_dashboard_summary_lists_candidates_awaiting_decision(client, hr_headers):
    summary = client.get("/api/dashboard/summary", headers=hr_headers).json()
    assert summary["awaiting_decision"] == len([c for c in summary["awaiting_list"]]) or summary["awaiting_decision"] > 10
    assert all(item["bias_flag_status"] for item in summary["awaiting_list"] if item["merged_score"] is not None)


def test_mcp_stdio_server_speaks_json_rpc():
    from app.mcp.stdio_server import handle
    init = handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})
    assert init["result"]["capabilities"]["tools"] is not None
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
    assert "get_candidate" in names and "save_human_review" not in names
    call = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": "get_candidate_pipeline_status", "arguments": {"candidate_id": "CAND-001-ELENA"}}})
    assert call["result"]["isError"] is False and "DECIDED" in call["result"]["content"][0]["text"]
    refused = handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "save_human_review", "arguments": {}}})
    assert refused["result"]["isError"] is True
    assert handle({"jsonrpc": "2.0", "id": 5, "method": "bogus"})["error"]["code"] == -32601
