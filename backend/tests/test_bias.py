"""Small-cohort bias statistics: Fisher's exact test, classification and data-quality handling."""
import pytest

from app.services.fairness_stats import (
    STATUS_INDICATOR, STATUS_INSUFFICIENT, STATUS_NONE, STATUS_SUPPORTED, compare_groups,
    fisher_exact_two_sided, wilson_interval,
)


@pytest.mark.parametrize("table,expected", [((1, 9, 11, 3), 0.0028), ((8, 2, 1, 5), 0.0350), ((3, 1, 1, 3), 0.4857), ((0, 0, 1, 1), 1.0)])
def test_fisher_matches_reference_values(table, expected):
    assert fisher_exact_two_sided(*table) == pytest.approx(expected, abs=1e-4)


def test_wilson_interval_bounds():
    low, high = wilson_interval(0, 5)
    assert low == 0.0 and 0.4 < high < 0.5
    assert wilson_interval(0, 0) == (None, None)


def records(spec):
    return [(cohort, i < selected) for cohort, n, selected in spec for i in range(n)]


def group(result, name):
    return next(g for g in result["groups"] if g["cohort_name"] == name)


def test_two_candidate_cohort_is_not_compared():
    result = compare_groups(records([("A", 10, 6), ("B", 2, 0)]), "selected")
    assert group(result, "B")["status"] == STATUS_INSUFFICIENT
    assert result["overall_status"] == STATUS_INSUFFICIENT


def test_low_ratio_without_significance_is_only_an_indicator():
    result = compare_groups(records([("A", 6, 4), ("B", 6, 2)]), "selected")
    b = group(result, "B")
    assert b["impact_ratio"] == pytest.approx(0.5)
    assert b["status"] == STATUS_INDICATOR
    assert "not evidence that no disparity exists" in " ".join(b["notes"])


def test_low_ratio_with_significance_is_supported():
    result = compare_groups(records([("A", 40, 30), ("B", 40, 8)]), "selected")
    assert group(result, "B")["status"] == STATUS_SUPPORTED
    assert result["overall_status"] == STATUS_SUPPORTED


def test_no_indicator_still_warns_about_power_for_small_groups():
    result = compare_groups(records([("A", 8, 4), ("B", 8, 4)]), "selected")
    notes = " ".join(group(result, "B")["notes"])
    assert group(result, "B")["status"] == STATUS_NONE and "could still go undetected" in notes


def test_fragile_ratio_is_flagged():
    result = compare_groups(records([("A", 10, 5), ("B", 10, 4)]), "selected")
    assert group(result, "B")["unstable_ratio"] is True


def test_missing_cohort_data_is_excluded_and_reported():
    result = compare_groups(records([("A", 6, 3), ("B", 6, 3), (None, 5, 0), ("General Cohort", 3, 0)]), "selected")
    assert result["missing_cohort"] == 8 and result["with_cohort"] == 12
    assert "missing" in result["summary"]


def test_zero_reference_selections_is_insufficient():
    result = compare_groups(records([("A", 6, 0), ("B", 6, 0)]), "selected")
    assert result["overall_status"] == STATUS_INSUFFICIENT


def test_bias_check_is_bound_to_panel_decision_and_audited(db):
    from app.database.models import AuditLog, BiasCheck, PanelDecision
    check = db.query(BiasCheck).first()
    assert db.query(PanelDecision).filter(PanelDecision.decision_id == check.decision_id).first() is not None
    assert {c["check_type"] for c in check.cohort_breakdown["checks"]} >= {
        "selection_rate_ai_recommendation", "selection_rate_human_decision", "decision_rationale_language"}
    logged = db.query(AuditLog).filter(AuditLog.stage == "BIAS_CHECKED", AuditLog.candidate_id == check.candidate_id).all()
    assert any(log.input_reference.get("decision_id") == check.decision_id for log in logged)
