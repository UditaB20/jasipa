import pytest
from app.agents.resume_screener import ResumeScreenerAgent
from app.agents.skill_assessor import SkillAssessorAgent
from app.agents.culture_fit import CultureFitAgent
from app.agents.panel_coordinator import PanelCoordinatorAgent
from app.schemas.screening import ResumeScreeningOutput
from app.schemas.assessment import SkillAssessorOutput, CultureFitOutput

def test_resume_screener_evaluation():
    jd_data = {
        "jd_id": "JD-SWE-101",
        "title": "Software Engineer",
        "required_skills": ["Python", "FastAPI", "SQL"],
        "preferred_skills": ["Docker"],
        "min_experience": 2.0
    }
    rubric_data = {"version": "1.0"}
    resume_text = "Experienced developer with 4 years of experience building Python and FastAPI applications with SQL databases and Docker containers."
    
    out = ResumeScreenerAgent.evaluate("C001", resume_text, jd_data, rubric_data)
    assert out.score >= 80.0
    assert "Python" in out.matched_requirements
    assert "FastAPI" in out.matched_requirements
    assert out.experience_match is True
    assert out.status == "COMPLETED"

def test_resume_screener_insufficient_evidence():
    jd_data = {"jd_id": "JD001", "required_skills": ["Python"], "preferred_skills": [], "min_experience": 1.0}
    out = ResumeScreenerAgent.evaluate("C002", "Too short", jd_data, {})
    assert out.status == "INSUFFICIENT_EVIDENCE"
    assert out.score == 0.0

def test_skill_assessor_evaluation():
    jd_data = {"jd_id": "JD001"}
    questions = [
        {"question_id": "Q1", "type": "mcq", "competency_or_skill": "Python", "correct_option": "B", "rubric_guideline": "Asyncio"},
        {"question_id": "Q2", "type": "short_answer", "competency_or_skill": "SQL", "rubric_guideline": "DENSE_RANK or limit offset"}
    ]
    answers = [
        {"question_id": "Q1", "answer_text": "B"},
        {"question_id": "Q2", "answer_text": "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;"}
    ]
    out = SkillAssessorAgent.evaluate("C001", jd_data, questions, answers)
    assert out.score >= 85.0
    assert "Python" in out.skill_breakdown
    assert out.status == "COMPLETED"

def test_culture_fit_evaluates_star_and_insufficient_evidence():
    jd_data = {"jd_id": "JD001"}
    questions = [{"question_id": "BEH_Q1", "prompt": "Conflict resolution", "competency_or_skill": "Teamwork"}]
    
    # 1. Test insufficient evidence
    empty_ans = [{"question_id": "BEH_Q1", "answer_text": "Yes."}]
    insufficient_out = CultureFitAgent.evaluate("C001", jd_data, questions, empty_ans)
    assert insufficient_out.status == "INSUFFICIENT_EVIDENCE"
    assert insufficient_out.score == 0.0

    # 2. Test valid STAR response
    star_ans = [{
        "question_id": "BEH_Q1", 
        "answer_text": "In a previous project situation, we had a technical disagreement on caching. I decided to benchmark Redis vs Memcached and presented data. As a result, the team unanimously agreed."
    }]
    valid_out = CultureFitAgent.evaluate("C001", jd_data, questions, star_ans)
    assert valid_out.status == "COMPLETED"
    assert valid_out.score >= 70.0
