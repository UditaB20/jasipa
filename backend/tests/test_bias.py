"""Bias detection: Fisher's exact test, screening criteria, sample-size limits, cohort handling and auditing."""
import pytest

from app.services.fairness_stats import (
    STATUS_INDICATOR, STATUS_INSUFFICIENT, STATUS_NONE, STATUS_SUPPORTED, compare_groups,
    fisher_exact_two_sided, wilson_interval,
)


def records(spec):
    return [(cohort, i < selected) for cohort, n, selected in spec for i in range(n)]


def group(result, name):
    return next(g for g in result["groups"] if g["cohort_name"] == name)


@pytest.mark.parametrize("table,expected", [((1, 9, 11, 3), 0.0028), ((8, 2, 1, 5), 0.0350), ((3, 1, 1, 3), 0.4857), ((0, 0, 1, 1), 1.0)])
def test_fisher_matches_reference_values(table, expected):
    """Feature: Bias statistics – Fisher's exact test
    Input: 2x2 contingency tables with published/SciPy p-values
    Expected: two-sided p-value matches the reference to 4 decimals"""
    assert fisher_exact_two_sided(*table) == pytest.approx(expected, abs=1e-4)


def test_wilson_interval_bounds():
    """Feature: Bias statistics – Wilson interval (boundary)
    Input: 0 selected of 5; 0 of 0
    Expected: interval [0, ~0.43]; undefined (None, None) for n=0"""
    low, high = wilson_interval(0, 5)
    assert low == 0.0 and 0.4 < high < 0.5
    assert wilson_interval(0, 0) == (None, None)


def test_two_candidate_cohort_is_not_compared():
    """Feature: Bias – sample-size limit (boundary)
    Input: cohort A 6/10 selected, cohort B 0/2 selected
    Expected: B reported as insufficient data, not as a disparity; overall insufficient"""
    result = compare_groups(records([("A", 10, 6), ("B", 2, 0)]), "selected")
    assert group(result, "B")["status"] == STATUS_INSUFFICIENT
    assert result["overall_status"] == STATUS_INSUFFICIENT and result["display_status"] == "INSUFFICIENT_DATA"
    assert "not evidence that the process is fair" in result["summary"]


def test_screen_triggered_without_significance_is_detected_but_qualified():
    """Feature: Bias – screening criterion without statistical support
    Input: A 4/6, B 2/6 (impact ratio 0.50, Fisher p ≈ 0.57)
    Expected: 'Disparity detected', qualified as not statistically significant; note says it is not evidence of no disparity"""
    result = compare_groups(records([("A", 6, 4), ("B", 6, 2)]), "selected")
    b = group(result, "B")
    assert b["impact_ratio"] == pytest.approx(0.5)
    assert b["status"] == STATUS_INDICATOR and b["display_status"] == "DISPARITY_DETECTED"
    assert b["significance"] == "not statistically significant"
    assert "not evidence that no disparity exists" in " ".join(b["notes"])


def test_screen_triggered_with_significance_is_supported():
    """Feature: Bias – statistically supported disparity
    Input: A 30/40, B 8/40
    Expected: 'Disparity detected', statistically significant"""
    result = compare_groups(records([("A", 40, 30), ("B", 40, 8)]), "selected")
    assert group(result, "B")["status"] == STATUS_SUPPORTED and result["significance"] == "statistically significant"


def test_rate_difference_alone_is_not_flagged():
    """Feature: Bias – a selection-rate difference alone is not a disparity
    Input: A 180/200 vs B 150/200 (ratio 0.83, Fisher p < 0.05)
    Expected: no disparity warning (screen not triggered); significance mentioned only as a note"""
    result = compare_groups(records([("A", 200, 180), ("B", 200, 150)]), "selected")
    b = group(result, "B")
    assert b["fisher_p_value"] < 0.05 and b["impact_ratio"] > 0.8
    assert b["status"] == STATUS_NONE and b["display_status"] == "NO_INDICATOR_DETECTED"
    assert "rate difference alone is not treated as disparity" in " ".join(b["notes"])


def test_no_indicator_still_warns_about_power_for_small_groups():
    """Feature: Bias – statistical uncertainty
    Input: A 4/8, B 4/8
    Expected: no indicator, with the note that a real disparity could go undetected"""
    result = compare_groups(records([("A", 8, 4), ("B", 8, 4)]), "selected")
    assert group(result, "B")["status"] == STATUS_NONE and "could still go undetected" in " ".join(group(result, "B")["notes"])


def test_fragile_ratio_is_flagged():
    """Feature: Bias – unstable ratios
    Input: A 5/10, B 4/10
    Expected: B flagged as fragile because one outcome would flip the four-fifths result"""
    assert group(compare_groups(records([("A", 10, 5), ("B", 10, 4)]), "selected"), "B")["unstable_ratio"] is True


def test_missing_cohort_data_is_excluded_and_reported():
    """Feature: Bias – cohort assignment and missing data
    Input: 12 labelled candidates, 5 unlabelled, 3 with legacy 'General Cohort'
    Expected: 8 counted as missing and excluded; summary warns about missing data"""
    result = compare_groups(records([("A", 6, 3), ("B", 6, 3), (None, 5, 0), ("General Cohort", 3, 0)]), "selected")
    assert result["missing_cohort"] == 8 and result["with_cohort"] == 12 and "missing" in result["summary"]


def test_zero_reference_selections_is_insufficient():
    """Feature: Bias – undefined impact ratio (boundary)
    Input: nobody selected in either cohort
    Expected: insufficient data"""
    assert compare_groups(records([("A", 6, 0), ("B", 6, 0)]), "selected")["overall_status"] == STATUS_INSUFFICIENT


def test_dataset_imports_have_no_cohort_and_analysis_says_so(client, hr_headers, db):
    """Feature: Bias – cohort definition with the Kaggle dataset
    Input: database seeded only from the Kaggle Resume Dataset
    Expected: imported records have no cohort; analytics documents the cohort definition and does not report fairness"""
    from app.database.models import Candidate
    assert all(c.cohort_tag is None for c in db.query(Candidate).filter(Candidate.source == "dataset_import"))
    analytics = client.get("/api/bias/analytics", headers=hr_headers).json()
    assert "never inferred from resume content" in analytics["cohort_definition"]
    assert analytics["ai_recommendation"]["display_status"] in ("INSUFFICIENT_DATA", "DISPARITY_DETECTED", "NO_INDICATOR_DETECTED")


def test_bias_check_is_bound_to_panel_decision_and_audited(evaluated_candidate, db):
    """Feature: Bias – association with panel decisions and audit log
    Input: candidate evaluated end to end through the pipeline
    Expected: bias check references the panel decision; checks include both selection stages and rationale language; audit entry has the decision_id"""
    from app.database.models import AuditLog, BiasCheck, PanelDecision
    candidate_id = evaluated_candidate("strong", "Bias Audit Candidate")
    db.expire_all()
    check = db.query(BiasCheck).filter(BiasCheck.candidate_id == candidate_id).one()
    assert db.query(PanelDecision).filter(PanelDecision.decision_id == check.decision_id).one()
    assert {c["check_type"] for c in check.cohort_breakdown["checks"]} >= {
        "selection_rate_ai_recommendation", "selection_rate_human_decision", "decision_rationale_language"}
    assert check.cohort_breakdown["display_status"] in ("INSUFFICIENT_DATA", "DISPARITY_DETECTED", "NO_INDICATOR_DETECTED")
    logged = db.query(AuditLog).filter(AuditLog.stage == "BIAS_CHECKED", AuditLog.candidate_id == candidate_id).all()
    assert any(log.input_reference.get("decision_id") == check.decision_id for log in logged)


def test_bias_check_never_changes_scores_or_routing(evaluated_candidate, db):
    """Feature: Bias – human oversight preserved
    Input: evaluated candidate
    Expected: candidate ends in HUMAN_REVIEW_PENDING; bias result requires human review; no human review was created automatically"""
    from app.database.models import BiasCheck, Candidate, HumanReview
    candidate_id = evaluated_candidate("strong", "Oversight Candidate")
    db.expire_all()
    assert db.query(Candidate).filter(Candidate.candidate_id == candidate_id).one().current_stage == "HUMAN_REVIEW_PENDING"
    assert db.query(BiasCheck).filter(BiasCheck.candidate_id == candidate_id).one().requires_human_review is True
    assert db.query(HumanReview).filter(HumanReview.candidate_id == candidate_id).count() == 0
