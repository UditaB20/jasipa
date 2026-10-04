from unittest.mock import patch

from app.agents.base_agent import (
    EvaluationStrategy,
    HeuristicStrategy,
    LLMStrategy,
    RegexStrategy,
    STARFrameworkStrategy,
    StrategyChain,
)


class StubStrategy(EvaluationStrategy):
    def __init__(self, name, result):
        super().__init__(name)
        self.result = result

    def evaluate(self, **kwargs):
        return self.result


def run_without_metrics(chain, **kwargs):
    with patch.object(chain, "_record_attempt"):
        return chain.execute(**kwargs)


def test_regex_resume_strategy_extracts_skills_experience_and_score():
    result = RegexStrategy().evaluate(
        resume_text="Python developer with 5 years of experience. Built APIs with FastAPI.",
        jd_data={"required_skills": ["Python", "FastAPI"], "min_experience": 3},
    )
    assert result["success"]
    assert result["data"]["matched_skills"] == ["Python", "FastAPI"]
    assert result["data"]["experience_years"] == 5
    assert 0 <= result["data"]["score"] <= 100


def test_heuristic_mcq_binary_scoring_and_star_detection():
    mcq = HeuristicStrategy().evaluate(
        questions=[{"question_id": "q1", "type": "mcq", "correct_option": "B"}],
        answers=[{"question_id": "q1", "answer_text": "B"}],
    )
    assert mcq["data"]["score"] == 100
    star = STARFrameworkStrategy().evaluate(
        questions=[{"question_id": "q1", "competency_or_skill": "Ownership"}],
        answers=[{"question_id": "q1", "answer_text": "Situation: During a project my task was to improve delivery. I implemented a fix. Result: we improved speed."}],
    )
    assert star["success"] and star["data"]["star_detected"]


def test_llm_api_failure_returns_failure_result():
    with patch("app.agents.llm_factory.LLMService.call_llm", side_effect=TimeoutError()):
        result = LLMStrategy().evaluate(system_prompt="", user_prompt="")
    assert result["success"] is False
    assert result["error"] == "LLM_TIMEOUT"


def test_strategy_chain_uses_first_success_and_records_order():
    first = StubStrategy("first", {"success": False, "error": "unavailable"})
    second = StubStrategy("second", {"success": True, "data": {"score": 77}})
    third = StubStrategy("third", {"success": True, "data": {"score": 99}})
    chain = StrategyChain([("first", first), ("second", second), ("third", third)])
    result = run_without_metrics(chain)
    assert result["successful_strategy"] == "second"
    assert result["data"]["score"] == 77
    assert [attempt["strategy_name"] for attempt in result["attempts"]] == ["first", "second"]
    assert result["fallback_chain_depth"] == result["attempts_before_success"] == 1


def test_strategy_chain_returns_failure_after_all_strategies_fail():
    chain = StrategyChain([("a", StubStrategy("a", {"success": False, "error": "a"})),
                           ("b", StubStrategy("b", {"success": False, "error": "b"}))])
    result = run_without_metrics(chain)
    assert result["successful_strategy"] is None
    assert len(result["attempts"]) == 2
