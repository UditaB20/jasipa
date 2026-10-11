"""QuestionGenerationAgent: role-specific generation, validation, caching and sanitisation."""
from unittest.mock import patch

from app.agents.question_generator import (
    QuestionGenerationAgent, _validate_llm_questions, build_template_questions, get_or_create_question_set,
    sanitize_questions_for_candidate,
)
from app.database.models import JobDescription
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
    jd = JobDescription(**{k: v for k, v in spec.items()})
    return generate_rubric_for_jd(jd)


def test_unseen_role_gets_role_specific_questions_without_department_rules():
    out = build_template_questions(UNSEEN_ROLE, _criteria(UNSEEN_ROLE))
    technical = out["technical_questions"]
    skills = {q["competency_or_skill"] for q in technical}
    assert {"REDCap", "GCP Compliance"} & skills, "unbanked required skills still receive scenario questions"
    assert all(q["type"] != "coding" for q in technical), "non-programming roles do not get coding challenges"
    scenario = next(q for q in technical if q["competency_or_skill"] == "REDCap")
    assert "redcap" in scenario["prompt"].lower() and "trial databases" in scenario["prompt"].lower()
    assert len(out["behavioral_questions"]) == 4
    assert all(word in out["behavioral_questions"][0]["rubric_guideline"] for word in ("Situation", "Task", "Actions", "Result"))


def test_software_role_gets_verified_coding_challenge_and_mcqs():
    spec = {"title": "Backend Engineer", "description": "Build Python services and design SQL schemas for billing.",
            "required_skills": ["Python", "SQL", "Algorithms"], "preferred_skills": [], "min_experience": 6}
    technical = build_template_questions(spec, _criteria(spec))["technical_questions"]
    kinds = [q["type"] for q in technical]
    assert kinds.count("mcq") >= 1 and kinds.count("coding") == 1
    coding = next(q for q in technical if q["type"] == "coding")
    assert coding["proficiency"] == "advanced"
    assert any(t.get("hidden") for t in coding["coding"]["tests"])


def test_llm_output_is_validated_and_bad_code_rejected():
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
    assert any(t["hidden"] for t in technical[1]["coding"]["tests"]), "a hidden split is enforced"
    assert any("failed its own tests" in n for n in notes) and any("malformed MCQ" in n for n in notes)


def test_llm_path_used_when_available_and_falls_back_on_failure():
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
    jd = db.query(JobDescription).filter(JobDescription.jd_id == "JD-SCA-303").first()
    rubric = get_or_create_rubric(db, jd)
    first = get_or_create_question_set(db, jd, rubric)
    with patch("app.agents.question_generator.QuestionGenerationAgent.generate") as generate:
        again = get_or_create_question_set(db, jd, rubric)
        generate.assert_not_called()
    assert again.question_set_id == first.question_set_id


def test_candidate_copy_hides_answer_keys_solutions_and_hidden_tests(db):
    jd = db.query(JobDescription).filter(JobDescription.jd_id == "JD-SWE-101").first()
    question_set = get_or_create_question_set(db, jd, get_or_create_rubric(db, jd))
    sanitized = sanitize_questions_for_candidate(question_set.technical_questions)
    text = str(sanitized)
    assert "correct_option" not in text and "rubric_guideline" not in text and "reference_solution" not in text
    coding = next(q for q in sanitized if q["type"] == "coding")["coding"]
    assert coding["hidden_test_count"] >= 1 and "tests" not in coding
    assert all("args" in example for example in coding["examples"])
