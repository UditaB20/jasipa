# Bias checks and hiring outcomes

Every panel run ends with a bias check that is stored with that panel decision (`bias_checks.decision_id`), written to the audit log, and shown to the reviewer next to the decision form. A human decision is refused unless the latest panel decision has its bias check, and the decision's audit entry repeats the bias status and reason. Bias checks never change scores, routing or a candidate's stage.

## What is checked

| Check | Question | Data |
| --- | --- | --- |
| `decision_rationale_language` | Does the panel's rationale contain demographic or proxy language? | This panel decision |
| `selection_rate_ai_recommendation` | Do cohorts reach "Proceed" at different rates? | Latest panel decision per candidate |
| `selection_rate_human_decision` | Do cohorts get approved at different rates? | Latest final human decision per candidate |
| `outcome_based_fairness` | Do approved hires from different cohorts receive different performance ratings? | Recorded hiring outcomes |
| `threshold_consistency` | Do the lowest "Proceed" scores differ across cohorts? | Latest panel decision per candidate |

## Small cohorts

The original implementation applied the four-fifths rule to cohorts with as few as two candidates, so a single outcome could flip the result. Selection-rate comparisons (`app/services/fairness_stats.py`) now report, for every cohort:

* selection rate with a Wilson 95% interval;
* impact ratio against the highest-rate cohort that has at least `BIAS_MIN_GROUP_SIZE` (default 5) candidates;
* a two-sided Fisher's exact test of the cohort against all other candidates with a recorded cohort (exact for small counts; verified against SciPy reference values in the tests);
* a fragility flag when changing one candidate's outcome would flip the four-fifths result.

Each comparison is classified as:

| Status | Meaning |
| --- | --- |
| `STATISTICALLY_SUPPORTED_DISPARITY` | Impact ratio below 0.80 **and** Fisher p < 0.05. Escalate. It still does not establish cause or intent. |
| `POTENTIAL_DISPARITY_INDICATOR` | Ratio below 0.80 without significance, or a significant shortfall within the 0.80 screen. A prompt to look closer, not a finding. |
| `INSUFFICIENT_DATA` | Fewer than the minimum candidates, fewer than two comparable cohorts, or no selections in the reference cohort. Explicitly *not* evidence of fairness. |
| `NO_INDICATOR_DETECTED` | Nothing flagged. For cohorts under 30 the result notes that a real disparity could go undetected. |

Missing data: candidates without a recorded cohort (including the legacy default "General Cohort") are excluded from comparisons and counted; the summary warns when more than 20% are missing. Cohort tags are never passed to the evaluation agents.

## Hiring outcomes

Outcomes can be recorded only for candidates with a final human APPROVE decision, by an authenticated HR user whose email is recorded as the manager email. Analytics are descriptive, flag samples under 15, exclude records marked test/demo/mock/e2e, and never change rubrics, weights or decisions automatically.
