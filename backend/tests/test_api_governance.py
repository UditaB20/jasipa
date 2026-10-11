"""Authentication, data isolation, pipeline orchestration, human decisions, MCP and the audit ledger."""
import pytest

from app.auth.security import create_access_token
from app.database.models import Assessment, AuditLog, Candidate
from helpers import STRONG_RESUME, answers_for, make_pdf


def candidate_token(candidate_id):
    return {"Authorization": "Bearer " + create_access_token({"sub": "x@example.com", "role": "CANDIDATE", "candidate_id": candidate_id})}


@pytest.mark.parametrize("method,route", [
    ("GET", "/api/candidates/"), ("POST", "/api/candidates/"), ("GET", "/api/jobs/"), ("POST", "/api/jobs/"),
    ("GET", "/api/jobs/JD-KAG-HR/rubric"), ("GET", "/api/assessments/questions/JD-KAG-HR"),
    ("POST", "/api/assessments/questions/JD-KAG-HR/regenerate"), ("POST", "/api/pipeline/run-full-graph"),
    ("POST", "/api/reviews/decide"), ("GET", "/api/dashboard/summary"), ("POST", "/api/mcp/execute"), ("GET", "/api/audit/verify"),
])
def test_routes_require_authentication(client, method, route):
    """Feature: API security – authentication
    Input: request without a bearer token
    Expected: 401"""
    assert client.request(method, route, json={}).status_code == 401


def test_candidates_cannot_reach_hr_data(client, db):
    """Feature: API security – role isolation (negative)
    Input: candidate token calling HR dossier, assessments, audit, decision and question-preview endpoints
    Expected: 403 for each"""
    cid = db.query(Candidate).filter(Candidate.source == "dataset_import").first().candidate_id
    headers = candidate_token(cid)
    for method, route in [("GET", f"/api/candidates/{cid}"), ("GET", f"/api/assessments/candidate/{cid}"),
                          ("GET", f"/api/audit/candidate/{cid}"), ("POST", "/api/reviews/decide"),
                          ("GET", "/api/assessments/questions/JD-KAG-HR")]:
        assert client.request(method, route, json={}, headers=headers).status_code == 403, route


def test_login_and_registration_validation(client):
    """Feature: Authentication forms – validation (negative, boundary)
    Input: dataset record email with any password; wrong HR password; duplicate/invalid/short registrations
    Expected: 401 for logins; 409 duplicate; 422 invalid email and short password"""
    assert client.post("/api/auth/login", json={"email": "kaggle-16852973@dataset.invalid", "password": "candidate123"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "hr@jasipa.ai", "password": "wrong"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "student@jasipa.ai", "password": "student123"}).status_code == 200
    assert client.post("/api/auth/register", json={"name": "Dup", "email": "student@jasipa.ai", "password": "longenough1"}).status_code == 409
    assert client.post("/api/auth/register", json={"name": "A B", "email": "not-an-email", "password": "longenough1"}).status_code == 422
    assert client.post("/api/auth/register", json={"name": "A B", "email": "ok@example.com", "password": "short"}).status_code == 422


def test_job_creation_validation_and_rubric_versioning(client, hr_headers):
    """Feature: Jobs and rubrics – validation and versioning
    Input: job with no required skills; valid job; rubric edit with weights not summing to 1; valid rubric edit
    Expected: 422; job with rubric v1.0; 400; new version 1.1 while v1.0 stays in history"""
    assert client.post("/api/jobs/", headers=hr_headers, json={"title": "Bad", "department": "X", "description": "short",
                                                               "required_skills": []}).status_code == 422
    job = client.post("/api/jobs/", headers=hr_headers, json={"title": "Payroll Officer", "department": "Finance",
        "description": "Run monthly payroll for 400 staff and reconcile deductions.", "required_skills": ["Payroll", "Excel"]}).json()
    assert job["rubric_version"] == "1.0"
    assert client.put(f"/api/jobs/{job['jd_id']}/rubric", headers=hr_headers, json={"resume_weight": 0.5, "skill_weight": 0.5,
                                                                                    "culture_weight": 0.5}).status_code == 400
    saved = client.put(f"/api/jobs/{job['jd_id']}/rubric", headers=hr_headers, json={"resume_weight": 0.5, "skill_weight": 0.3, "culture_weight": 0.2})
    assert saved.status_code == 200 and saved.json()["version"] == "1.1"
    versions = [r["version"] for r in client.get(f"/api/jobs/{job['jd_id']}/rubrics", headers=hr_headers).json()]
    assert versions == ["1.0", "1.1"]


def test_removed_rights_and_review_queue_endpoints_stay_removed(client, hr_headers, db):
    """Feature: Removed features – transparency page and review queue
    Input: old /candidate/explanation, /candidate/request-re-review and /reviews/pending routes
    Expected: 404/405"""
    headers = candidate_token(db.query(Candidate).first().candidate_id)
    assert client.get("/api/candidate/explanation", headers=headers).status_code == 404
    assert client.post("/api/candidate/request-re-review", headers=headers).status_code == 404
    assert client.get("/api/reviews/pending", headers=hr_headers).status_code in (404, 405)


def test_candidate_assessment_flow_scores_code_objectively(client, new_candidate, software_job, db):
    """Feature: Assessments – candidate flow with sandboxed coding
    Input: portal candidate applies to the software job, runs examples, submits correct answers, then submits again
    Expected: MCQ options shown without keys; practice run uses only visible tests; stored result passes all hidden tests; resubmission 409"""
    headers, candidate_id = new_candidate("Coding Candidate")
    client.post("/api/candidate/upload-resume", headers=headers, files={"file": ("cv.pdf", make_pdf(STRONG_RESUME), "application/pdf")})
    client.post("/api/candidate/apply", headers=headers, json={"jd_id": software_job["jd_id"]})
    technical = client.get("/api/candidate/assessments", headers=headers).json()["technical"]["questions"]
    assert "correct_option" not in str(technical)
    assert len(next(q for q in technical if q["type"] == "mcq")["options"]) == 4
    coding = next(q for q in technical if q["type"] == "coding")
    sample = client.post("/api/candidate/assessments/run-code", headers=headers,
                         json={"question_id": coding["question_id"], "code": f"def {coding['coding']['function_name']}(*a):\n    return None"})
    assert sample.status_code == 200 and all(not t["hidden"] for t in sample.json()["tests"])
    db.expire_all()
    answers = answers_for(technical, "strong", db, software_job["jd_id"], "technical")
    assert client.post("/api/candidate/submit-technical", json={"answers": answers}, headers=headers).status_code == 200
    assert client.post("/api/candidate/submit-technical", json={"answers": answers}, headers=headers).status_code == 409
    db.expire_all()
    stored = db.query(Assessment).filter(Assessment.candidate_id == candidate_id, Assessment.test_type == "TECHNICAL").one()
    result = stored.execution_results[coding["question_id"]]
    assert result["status"] == "OK" and result["passed"] == result["total"] and any(t["hidden"] for t in result["tests"])


def test_empty_submission_is_rejected(client, new_candidate, software_job):
    """Feature: Assessments – form validation (negative)
    Input: technical submission with only blank answers
    Expected: 422 'Answer at least one question'"""
    headers, _ = new_candidate()
    client.post("/api/candidate/upload-resume", headers=headers, files={"file": ("cv.pdf", make_pdf(STRONG_RESUME), "application/pdf")})
    client.post("/api/candidate/apply", headers=headers, json={"jd_id": software_job["jd_id"]})
    questions = client.get("/api/candidate/assessments", headers=headers).json()["technical"]["questions"]
    response = client.post("/api/candidate/submit-technical", headers=headers,
                           json={"answers": [{"question_id": q["question_id"], "answer_text": " "} for q in questions]})
    assert response.status_code == 422 and "at least one" in response.json()["detail"]


def test_full_pipeline_runs_and_reuses_stored_assessments(client, hr_headers, evaluated_candidate, db):
    """Feature: Agent orchestration – LangGraph pipeline
    Input: evaluated candidate; pipeline re-run
    Expected: HUMAN_REVIEW_PENDING; bias check bound to the panel decision; round number increments; no duplicate assessment rows"""
    candidate_id = evaluated_candidate("strong", "Orchestration Candidate")
    before = db.query(Assessment).filter(Assessment.candidate_id == candidate_id).count()
    body = client.post("/api/pipeline/run-full-graph", json={"candidate_id": candidate_id}, headers=hr_headers).json()
    assert body["current_stage"] == "HUMAN_REVIEW_PENDING" and body["round_number"] == 2
    assert body["panel_result"]["recommendation"] in ("PROCEED_TO_HUMAN_REVIEW", "HUMAN_REVIEW_REQUIRED", "ADDITIONAL_INFORMATION_REQUIRED")
    assert body["bias_result"]["decision_id"] == body["panel_result"]["decision_id"]
    db.expire_all()
    assert db.query(Assessment).filter(Assessment.candidate_id == candidate_id).count() == before


def test_dataset_candidate_pipeline_reports_incomplete_evidence(client, hr_headers, db):
    """Feature: Agent orchestration – dataset record without assessments
    Input: run the pipeline for an imported Kaggle resume
    Expected: ADDITIONAL_INFORMATION_REQUIRED, technical and behavioral marked insufficient (no invented scores)"""
    cand = db.query(Candidate).filter(Candidate.source == "dataset_import", Candidate.current_stage == "RESUME_SCREENED").first()
    body = client.post("/api/pipeline/run-full-graph", json={"candidate_id": cand.candidate_id}, headers=hr_headers).json()
    assert body["panel_result"]["recommendation"] == "ADDITIONAL_INFORMATION_REQUIRED"
    assert body["skill_result"]["status"] == "INSUFFICIENT_EVIDENCE" and body["behavioral_result"]["status"] == "INSUFFICIENT_EVIDENCE"


def test_ai_cannot_write_a_rejection_through_mcp(client, hr_headers):
    """Feature: Governance – no autonomous rejection via tools (negative)
    Input: MCP save_panel_decision with recommendation AUTO_REJECT; tool listing
    Expected: tool error 'not allowed'; save_human_review not exposed"""
    response = client.post("/api/mcp/execute", headers=hr_headers, json={"name": "save_panel_decision", "arguments": {
        "candidate_id": "x", "jd_id": "JD-KAG-HR", "merged_score": 10, "recommendation": "AUTO_REJECT"}}).json()
    assert response["isError"] and "not allowed" in response["error"]
    assert "save_human_review" not in [t["name"] for t in client.get("/api/mcp/tools", headers=hr_headers).json()["tools"]]


def test_decision_requires_panel_and_bias_check(client, hr_headers, db):
    """Feature: Human decision – preconditions (negative)
    Input: APPROVE for a screened dataset candidate that has no panel evaluation
    Expected: 409 explaining a panel recommendation is required"""
    cand = db.query(Candidate).filter(Candidate.source == "dataset_import", Candidate.current_stage == "RESUME_SCREENED").first()
    response = client.post("/api/reviews/decide", headers=hr_headers,
                           json={"candidate_id": cand.candidate_id, "decision": "APPROVE", "notes": "Looks good to me overall."})
    assert response.status_code == 409 and "panel" in response.json()["detail"].lower()


def test_decision_validation(client, hr_headers, evaluated_candidate):
    """Feature: Human decision – form validation (negative, boundary)
    Input: notes shorter than 10 characters; unknown decision value
    Expected: 422 for both"""
    candidate_id = evaluated_candidate("strong", "Validation Candidate")
    assert client.post("/api/reviews/decide", headers=hr_headers, json={"candidate_id": candidate_id, "decision": "APPROVE", "notes": "ok"}).status_code == 422
    assert client.post("/api/reviews/decide", headers=hr_headers, json={"candidate_id": candidate_id, "decision": "HIRE", "notes": "long enough notes"}).status_code == 422


def test_decision_records_bias_check_and_closes_application(client, hr_headers, evaluated_candidate, db):
    """Feature: Human decision – recording and audit
    Input: REJECT with notes bound to the latest panel decision; then a second decision
    Expected: FINAL outcome, stage DECIDED, audit entry carries bias check id and status; second decision 409"""
    candidate_id = evaluated_candidate("weak", "Decision Candidate")
    status = client.get(f"/api/reviews/candidate/{candidate_id}", headers=hr_headers).json()
    assert status["can_decide"] and status["bias_check_id"]
    response = client.post("/api/reviews/decide", headers=hr_headers, json={
        "candidate_id": candidate_id, "decision": "REJECT", "decision_id": status["decision_id"],
        "notes": "Technical depth below the bar for this role."})
    assert response.status_code == 200 and response.json()["outcome"] in ("FINAL", "AWAITING_SECOND_REVIEWER")
    if response.json()["outcome"] == "FINAL":
        assert response.json()["status"]["current_stage"] == "DECIDED"
        db.expire_all()
        log = db.query(AuditLog).filter(AuditLog.candidate_id == candidate_id, AuditLog.event.like("Human decision recorded%")).one()
        assert log.input_reference["bias_check_id"] == status["bias_check_id"] and log.input_reference["bias_flag_status"]
        assert client.post("/api/reviews/decide", headers=hr_headers, json={"candidate_id": candidate_id, "decision": "APPROVE",
                                                                           "notes": "Changing my mind after all."}).status_code == 409


def test_escalated_decision_needs_two_agreeing_reviewers(client, hr_headers, reviewer_headers, evaluated_candidate):
    """Feature: Human decision – two-reviewer rule
    Input: candidate with strong resume but failing technical answers (large score divergence); two sign-offs
    Expected: two reviewers required; first sign-off keeps HUMAN_REVIEW_PENDING; same reviewer cannot sign twice; second agreeing reviewer closes it"""
    candidate_id = evaluated_candidate("mixed", "Divergent Candidate")
    status = client.get(f"/api/reviews/candidate/{candidate_id}", headers=hr_headers).json()
    assert status["requires_two_reviewers"]
    payload = {"candidate_id": candidate_id, "decision": "REJECT", "notes": "Technical assessment does not support the resume."}
    first = client.post("/api/reviews/decide", headers=hr_headers, json=payload).json()
    assert first["outcome"] == "AWAITING_SECOND_REVIEWER" and first["status"]["current_stage"] == "HUMAN_REVIEW_PENDING"
    assert client.post("/api/reviews/decide", headers=hr_headers, json=payload).status_code == 409
    second = client.post("/api/reviews/decide", headers=reviewer_headers, json=payload).json()
    assert second["outcome"] == "FINAL" and second["status"]["current_stage"] == "DECIDED"


def test_stale_decision_rejected_and_info_request_keeps_application_open(client, hr_headers, evaluated_candidate):
    """Feature: Human decision – stale evaluation and REQUEST_MORE_INFORMATION
    Input: decision citing an old panel id; then REQUEST_MORE_INFORMATION; then pipeline re-run
    Expected: 409; stage INFO_REQUESTED; re-run returns to HUMAN_REVIEW_PENDING"""
    candidate_id = evaluated_candidate("strong", "Info Candidate")
    payload = {"candidate_id": candidate_id, "decision": "REQUEST_MORE_INFORMATION",
               "notes": "Please complete a follow-up technical interview.", "decision_id": "not-the-latest"}
    assert client.post("/api/reviews/decide", headers=hr_headers, json=payload).status_code == 409
    payload.pop("decision_id")
    assert client.post("/api/reviews/decide", headers=hr_headers, json=payload).json()["status"]["current_stage"] == "INFO_REQUESTED"
    rerun = client.post("/api/pipeline/run-full-graph", json={"candidate_id": candidate_id}, headers=hr_headers)
    assert rerun.status_code == 200 and rerun.json()["current_stage"] == "HUMAN_REVIEW_PENDING"


def test_stage_cannot_be_forced_through_patch(client, hr_headers, db):
    """Feature: Governance – stage machine (negative)
    Input: PATCH current_stage=DECIDED
    Expected: 400"""
    cid = db.query(Candidate).filter(Candidate.source == "dataset_import").first().candidate_id
    assert client.patch(f"/api/candidates/{cid}", json={"current_stage": "DECIDED"}, headers=hr_headers).status_code == 400


def test_audit_chain_verifies_and_detects_tampering(client, hr_headers, db):
    """Feature: Audit log – tamper evidence
    Input: verify; edit one stored entry's output; verify; restore
    Expected: verified, then TAMPERING_DETECTED naming the entry, then verified again"""
    assert client.get("/api/audit/verify", headers=hr_headers).json()["verified"] is True
    entry = db.query(AuditLog).filter(AuditLog.stage == "RESUME_SCREENED").first()
    original = dict(entry.output)
    entry.output = {**original, "score": 100}
    db.commit()
    report = client.get("/api/audit/verify", headers=hr_headers).json()
    assert report["verified"] is False and any(i["log_id"] == entry.log_id for i in report["issues"])
    entry.output = original
    db.commit()
    assert client.get("/api/audit/verify", headers=hr_headers).json()["verified"] is True


def test_dashboard_summary_counts_are_consistent(client, hr_headers, db):
    """Feature: Dashboard – database consistency
    Input: GET /dashboard/summary
    Expected: total equals candidate rows; pipeline counts sum to the total; awaiting list items have bias statuses"""
    summary = client.get("/api/dashboard/summary", headers=hr_headers).json()
    assert summary["total_candidates"] == db.query(Candidate).count()
    assert sum(step["count"] for step in summary["pipeline"]) == summary["total_candidates"]
    assert all(item["bias_flag_status"] for item in summary["awaiting_list"] if item["merged_score"] is not None)


def test_mcp_stdio_server_speaks_json_rpc():
    """Feature: MCP connector – stdio JSON-RPC
    Input: initialize, notification, tools/list, tools/call (valid and disallowed), unknown method
    Expected: capabilities returned; no reply to notification; tool result; isError for save_human_review; -32601"""
    from app.mcp.stdio_server import handle
    assert handle({"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {}})["result"]["capabilities"]["tools"] is not None
    assert handle({"jsonrpc": "2.0", "method": "notifications/initialized"}) is None
    names = [t["name"] for t in handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})["result"]["tools"]]
    assert "get_candidate" in names and "save_human_review" not in names
    call = handle({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
                   "params": {"name": "get_job_description", "arguments": {"jd_id": "JD-KAG-HR"}}})
    assert call["result"]["isError"] is False and "Human Resources Specialist" in call["result"]["content"][0]["text"]
    assert handle({"jsonrpc": "2.0", "id": 4, "method": "tools/call", "params": {"name": "save_human_review", "arguments": {}}})["result"]["isError"]
    assert handle({"jsonrpc": "2.0", "id": 5, "method": "bogus"})["error"]["code"] == -32601
