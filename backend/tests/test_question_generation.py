"""QuestionGenerationAgent: role-specific generation, validation, caching, regeneration and sanitisation."""
from unittest.mock import patch

from app.agents.question_generator import (
    QuestionGenerationAgent, _validate_llm_questions, build_template_questions, get_or_create_question_set,
    question_fingerprint, sanitize_questions_for_candidate,
)
from app.database.models import JobDescription, QuestionSet
from app.services.rubric_service import generate_rubric_for_jd, get_or_create_rubric

UNSEEN_ROLE = {
    "title": "Clinical Trial Data Coordinator", "department": "Life Sciences",
    "description": "Maintain trial databases in REDCap and resolve data queries with study sites.\n"
                   "Prepare enrolment reports for the sponsor using Excel.\n"
                   "Ensure GCP compliance in every data correction.",
    "required_skills": ["REDCap", "GCP Compliance", "Excel", "Data Analysis"], "preferred_skills": ["SQL"],
    "min_experience": 1,
}


def _criteria(spec):
    return generate_rubric_for_jd(JobDescription(**spec))


def test_unseen_role_gets_role_specific_questions_without_department_rules():
    """Feature: Question generation – unseen role (template fallback)
    Input: 'Clinical Trial Data Coordinator' JD with REDCap/GCP skills, no LLM
    Expected: scenario questions on the unbanked skills tied to JD duties, no coding question, 4 STAR questions"""
    out = build_template_questions(UNSEEN_ROLE, _criteria(UNSEEN_ROLE))
    technical = out["technical_questions"]
    skills = {q["competency_or_skill"] for q in technical}
    assert {"REDCap", "GCP Compliance"} & skills
    assert all(q["type"] != "coding" for q in technical)
    scenario = next(q for q in technical if q["competency_or_skill"] == "REDCap")
    assert "redcap" in scenario["prompt"].lower() and "trial databases" in scenario["prompt"].lower()
    assert len(out["behavioral_questions"]) == 4
    assert all(w in out["behavioral_questions"][0]["rubric_guideline"] for w in ("Situation", "Task", "Actions", "Result"))


def test_software_role_gets_verified_coding_challenge_and_mcqs():
    """Feature: Question generation – programming role
    Input: Backend Engineer JD (Python, SQL, Algorithms), 6 years minimum experience
    Expected: at least one MCQ, exactly one advanced coding challenge with hidden tests"""
    spec = {"title": "Backend Engineer", "description": "Build Python services and design SQL schemas for billing.",
            "required_skills": ["Python", "SQL", "Algorithms"], "preferred_skills": [], "min_experience": 6}
    technical = build_template_questions(spec, _criteria(spec))["technical_questions"]
    kinds = [q["type"] for q in technical]
    assert kinds.count("mcq") >= 1 and kinds.count("coding") == 1
    coding = next(q for q in technical if q["type"] == "coding")
    assert coding["proficiency"] == "advanced" and any(t.get("hidden") for t in coding["coding"]["tests"])


def test_llm_output_is_validated_and_bad_code_rejected():
    """Feature: Question generation – LLM output validation (negative)
    Input: LLM payload with a valid MCQ, a malformed MCQ, a coding item whose reference solution is wrong, a valid coding item, a scenario
    Expected: malformed MCQ and failing coding item dropped with notes; hidden tests enforced"""
    data = {"technical_questions": [
        {"type": "mcq", "competency_or_skill": "Excel", "prompt": "Q?", "options": ["a", "b", "c", "d"], "correct_option": "B"},
        {"type": "mcq", "competency_or_skill": "Excel", "prompt": "Bad", "options": ["a", "b"], "correct_option": "Z"},
        {"type": "coding", "competency_or_skill": "Python", "prompt": "Add", "coding": {
            "function_name": "add", "reference_solution": "def add(a, b):\n    return a - b",
            "tests": [{"args": [1, 2], "expected": 3}, {"args": [0, 0], "expected": 0}, {"args": [2, 2], "expected": 4}]}},
        {"type": "coding", "competency_or_skill": "Python", "prompt": "Add", "coding": {
            "function_name": "add", "reference_solution": "def add(a, b):\n    return a + b",
            "tests": [{"args": [1, 2], "expected": 3}, {"args": [0, 0], "expected": 0}, {"args": [2, 2], "expected": 4}]}},
        {"type": "scenario", "competency_or_skill": "Planning", "prompt": "Describe a plan."},
    ], "behavioral_questions": []}
    technical, _, notes = _validate_llm_questions(data)
    assert [q["type"] for q in technical] == ["mcq", "coding", "scenario"]
    assert technical[0]["options"][1].startswith("B)")
    assert any(t["hidden"] for t in technical[1]["coding"]["tests"])
    assert any("failed its own tests" in n for n in notes) and any("malformed MCQ" in n for n in notes)


def test_llm_path_used_when_available_and_falls_back_on_failure():
    """Feature: Question generation – LLM integration and fallback
    Input: (a) mocked LLM returning valid questions; (b) LLM raising TimeoutError
    Expected: (a) generator 'llm' with sequential IDs; (b) generator 'template' with questions"""
    llm_payload = {"technical_questions": [{"type": "scenario", "competency_or_skill": "REDCap", "prompt": "How would you clean REDCap exports?"}],
                   "behavioral_questions": [{"competency_or_skill": "Communication", "prompt": "Tell me about..."},
                                            {"competency_or_skill": "Teamwork", "prompt": "Describe..."}]}
    with patch("app.agents.question_generator.settings") as fake, \
         patch("app.agents.llm_factory.LLMService.call_llm", return_value=llm_payload), \
         patch("app.agents.base_agent.StrategyChain._record_attempt"):
        fake.LLM_PROVIDER, fake.GEMINI_API_KEY = "gemini", "key"
        out = QuestionGenerationAgent.generate(UNSEEN_ROLE, _criteria(UNSEEN_ROLE))
    assert out["generator"] == "llm" and out["technical_questions"][0]["question_id"] == "TECH_Q1"
    with patch("app.agents.question_generator.settings") as fake, \
         patch("app.agents.llm_factory.LLMService.call_llm", side_effect=TimeoutError()), \
         patch("app.agents.base_agent.StrategyChain._record_attempt"):
        fake.LLM_PROVIDER, fake.GEMINI_API_KEY = "gemini", "key"
        out = QuestionGenerationAgent.generate(UNSEEN_ROLE, _criteria(UNSEEN_ROLE))
    assert out["generator"] == "template" and out["technical_questions"]


def test_question_set_is_cached_per_jd_and_rubric_version(db):
    """Feature: Question generation – caching
    Input: request the HR category job's question set twice
    Expected: second call returns the same set without invoking the generator"""
    jd = db.query(JobDescription).filter(JobDescription.jd_id == "JD-KAG-HR").one()
    rubric = get_or_create_rubric(db, jd)
    first = get_or_create_question_set(db, jd, rubric)
    with patch("app.agents.question_generator.QuestionGenerationAgent.generate") as generate:
        again = get_or_create_question_set(db, jd, rubric)
        generate.assert_not_called()
    assert again.question_set_id == first.question_set_id


def test_regenerate_endpoint_returns_and_persists_a_different_set(client, hr_headers, db):
    """Feature: Assessment regeneration – end to end (regression for the 'Regenerate does nothing' bug)
    Input: POST /assessments/questions/JD-KAG-FINANCE/regenerate twice, without an LLM
    Expected: 200 each time; new question_set_id; changed_questions > 0; GET returns the new set; audit entry logged"""
    before = client.get("/api/assessments/questions/JD-KAG-FINANCE", headers=hr_headers).json()
    for _ in range(2):
        response = client.post("/api/assessments/questions/JD-KAG-FINANCE/regenerate", headers=hr_headers)
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["question_set_id"] != before["question_set_id"] and body["changed_questions"] > 0
        assert question_fingerprint(body["technical_questions"], body["behavioral_questions"]) != \
            question_fingerprint(before["technical_questions"], before["behavioral_questions"])
        current = client.get("/api/assessments/questions/JD-KAG-FINANCE", headers=hr_headers).json()
        assert current["question_set_id"] == body["question_set_id"]
        before = body
    from app.database.models import AuditLog
    assert db.query(AuditLog).filter(AuditLog.stage == "QUESTIONS_GENERATED").count() >= 2


def test_regenerate_reports_failure_instead_of_false_success(client, hr_headers, db):
    """Feature: Assessment regeneration – failure handling (negative)
    Input: generator that can only reproduce the current questions; generator that raises an exception
    Expected: 409 with explanation and 502 respectively; the stored set is unchanged"""
    current = client.get("/api/assessments/questions/JD-KAG-ACCOUNTANT", headers=hr_headers).json()
    same = {"technical_questions": current["technical_questions"], "behavioral_questions": current["behavioral_questions"],
            "generator": "template", "notes": []}
    with patch("app.agents.question_generator.QuestionGenerationAgent.generate", return_value=same):
        response = client.post("/api/assessments/questions/JD-KAG-ACCOUNTANT/regenerate", headers=hr_headers)
    assert response.status_code == 409 and "No different questions" in response.json()["detail"]
    with patch("app.agents.question_generator.QuestionGenerationAgent.generate", side_effect=RuntimeError("provider down")):
        response = client.post("/api/assessments/questions/JD-KAG-ACCOUNTANT/regenerate", headers=hr_headers)
    assert response.status_code == 502 and "kept" in response.json()["detail"]
    after = client.get("/api/assessments/questions/JD-KAG-ACCOUNTANT", headers=hr_headers).json()
    assert after["question_set_id"] == current["question_set_id"]


def test_applicants_keep_their_pinned_questions_after_regeneration(client, hr_headers, new_candidate, software_job):
    """Feature: Assessment regeneration – applicants mid-assessment
    Input: candidate applies and loads questions; HR regenerates the job's assessment
    Expected: candidate still receives the same question set they were first shown"""
    from helpers import STRONG_RESUME, make_pdf
    headers, _ = new_candidate()
    client.post("/api/candidate/upload-resume", headers=headers, files={"file": ("cv.pdf", make_pdf(STRONG_RESUME), "application/pdf")})
    assert client.post("/api/candidate/apply", headers=headers, json={"jd_id": software_job["jd_id"]}).status_code == 200
    shown = client.get("/api/candidate/assessments", headers=headers).json()["technical"]["questions"]
    assert client.post(f"/api/assessments/questions/{software_job['jd_id']}/regenerate", headers=hr_headers).status_code == 200
    again = client.get("/api/candidate/assessments", headers=headers).json()["technical"]["questions"]
    assert [q["prompt"] for q in again] == [q["prompt"] for q in shown]


def test_candidate_copy_hides_answer_keys_solutions_and_hidden_tests(db, software_job):
    """Feature: Question delivery – sanitisation (security)
    Input: the software job's full question set passed through sanitize_questions_for_candidate
    Expected: no answer keys, scoring guides, reference solutions or hidden test data; examples only"""
    jd = db.query(JobDescription).filter(JobDescription.jd_id == software_job["jd_id"]).one()
    question_set = get_or_create_question_set(db, jd, get_or_create_rubric(db, jd))
    sanitized = sanitize_questions_for_candidate(question_set.technical_questions)
    text = str(sanitized)
    assert "correct_option" not in text and "rubric_guideline" not in text and "reference_solution" not in text
    coding = next(q for q in sanitized if q["type"] == "coding")["coding"]
    assert coding["hidden_test_count"] >= 1 and "tests" not in coding


def test_dataset_jobs_have_cached_question_sets(db):
    """Feature: Question generation – dataset category jobs
    Input: database seeded from the Kaggle dataset
    Expected: every category job has a stored question set with technical and STAR questions"""
    for jd in db.query(JobDescription).filter(JobDescription.jd_id.like("JD-KAG-%")).all():
        qs = db.query(QuestionSet).filter(QuestionSet.jd_id == jd.jd_id).first()
        assert qs and qs.technical_questions and len(qs.behavioral_questions) == 4
