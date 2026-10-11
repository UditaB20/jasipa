"""Small-sample-aware selection-rate comparison used by the bias checker.

For each cohort we report the selection rate with a Wilson 95% interval, the four-fifths impact ratio
against the highest-rate adequately sized cohort, and a two-sided Fisher's exact test of the cohort
against everyone else. Results are classified so that a ratio screen alone is never presented as a
statistically supported finding, and a non-significant test is never presented as proof of fairness.
"""
from math import comb, sqrt
from typing import Any, Dict, Iterable, List, Optional, Tuple

from app.config import settings

STATUS_SUPPORTED = "STATISTICALLY_SUPPORTED_DISPARITY"
STATUS_INDICATOR = "POTENTIAL_DISPARITY_INDICATOR"
STATUS_INSUFFICIENT = "INSUFFICIENT_DATA"
STATUS_NONE = "NO_INDICATOR_DETECTED"
STATUS_REFERENCE = "REFERENCE_GROUP"
SEVERITY = {STATUS_SUPPORTED: 3, STATUS_INDICATOR: 2, STATUS_INSUFFICIENT: 1, STATUS_NONE: 0, STATUS_REFERENCE: 0}

MISSING_COHORT_VALUES = {"", "general cohort", "unspecified", "unknown", "not recorded", "n/a", "none"}


def is_missing_cohort(value: Optional[str]) -> bool:
    return value is None or str(value).strip().lower() in MISSING_COHORT_VALUES


def fisher_exact_two_sided(a: int, b: int, c: int, d: int) -> float:
    """Two-sided Fisher's exact p-value for the 2x2 table [[a, b], [c, d]] (rows: group, cols: selected/not)."""
    row1, row2, col1 = a + b, c + d, a + c
    n = row1 + row2
    if n == 0 or row1 == 0 or row2 == 0 or col1 == 0 or col1 == n:
        return 1.0
    denominator = comb(n, col1)

    def probability(x: int) -> float:
        return comb(row1, x) * comb(row2, col1 - x) / denominator

    observed = probability(a)
    low, high = max(0, col1 - row2), min(row1, col1)
    total = sum(p for p in (probability(x) for x in range(low, high + 1)) if p <= observed * (1 + 1e-7))
    return min(1.0, total)


def wilson_interval(selected: int, n: int, z: float = 1.959964) -> Tuple[Optional[float], Optional[float]]:
    if n == 0:
        return None, None
    p = selected / n
    denom = 1 + z * z / n
    centre = (p + z * z / (2 * n)) / denom
    margin = z * sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return round(max(0.0, centre - margin), 3), round(min(1.0, centre + margin), 3)


def compare_groups(records: Iterable[Tuple[Optional[str], bool]], selection_label: str) -> Dict[str, Any]:
    """records: (cohort, selected) per candidate. Returns per-cohort statistics and an overall classification."""
    threshold = settings.BIAS_DISPARITY_THRESHOLD
    alpha = settings.BIAS_SIGNIFICANCE_LEVEL
    minimum = settings.BIAS_MIN_GROUP_SIZE

    counts: Dict[str, List[int]] = {}
    missing = 0
    total = 0
    for cohort, selected in records:
        total += 1
        if is_missing_cohort(cohort):
            missing += 1
            continue
        bucket = counts.setdefault(str(cohort).strip(), [0, 0])
        bucket[0] += 1
        bucket[1] += int(bool(selected))

    known_n = sum(n for n, _ in counts.values())
    known_selected = sum(s for _, s in counts.values())
    eligible = {name: (n, s) for name, (n, s) in counts.items() if n >= minimum}
    reference = max(eligible, key=lambda name: (eligible[name][1] / eligible[name][0], eligible[name][0]), default=None)
    reference_rate = (eligible[reference][1] / eligible[reference][0]) if reference else None

    groups = []
    for name, (n, selected) in sorted(counts.items()):
        rate = selected / n if n else 0.0
        low, high = wilson_interval(selected, n)
        rest_n, rest_selected = known_n - n, known_selected - selected
        p_value = fisher_exact_two_sided(selected, n - selected, rest_selected, rest_n - rest_selected) if rest_n else None
        ratio = (rate / reference_rate) if reference_rate else None
        notes: List[str] = []
        unstable = False

        if n < minimum:
            status = STATUS_INSUFFICIENT
            notes.append(f"Only {n} candidate(s); at least {minimum} are needed before this cohort is compared.")
        elif reference is None or len(eligible) < 2:
            status = STATUS_INSUFFICIENT
            notes.append("Fewer than two cohorts have enough candidates to compare.")
        elif not reference_rate:
            status = STATUS_INSUFFICIENT
            notes.append("No candidate in the reference cohort was selected, so the impact ratio is undefined.")
        elif name == reference:
            status = STATUS_REFERENCE
            notes.append("Highest selection rate among adequately sized cohorts; used as the four-fifths reference.")
        else:
            below_screen = ratio < threshold
            significant = p_value is not None and p_value < alpha
            if below_screen and significant:
                status = STATUS_SUPPORTED
                notes.append(f"Impact ratio {ratio:.2f} is below {threshold:.2f} and the difference is statistically significant "
                             f"(Fisher p={p_value:.3f}). Investigate the process; this does not establish intent or cause.")
            elif below_screen:
                status = STATUS_INDICATOR
                notes.append(f"Impact ratio {ratio:.2f} is below the {threshold:.2f} screen, but the difference is not statistically "
                             f"significant at this sample size (Fisher p={p_value:.3f}). This is not evidence that no disparity exists.")
            elif significant and rate < (rest_selected / rest_n if rest_n else rate):
                status = STATUS_INDICATOR
                notes.append(f"Selection rate is significantly lower than other cohorts (Fisher p={p_value:.3f}) "
                             f"although the impact ratio {ratio:.2f} passes the four-fifths screen.")
            else:
                status = STATUS_NONE
                notes.append("No disparity indicator observed.")
                if n < 30:
                    notes.append("With fewer than 30 candidates a real disparity could still go undetected.")
            # Fragility: would one candidate's outcome flip the four-fifths result?
            for delta in (-1, 1):
                alt = selected + delta
                if 0 <= alt <= n:
                    alt_ratio = (alt / n) / reference_rate
                    if (alt_ratio < threshold) != below_screen:
                        unstable = True
            if unstable:
                notes.append("Unstable ratio: changing a single candidate's outcome would change the four-fifths result.")
            if reference_rate < 0.2 or selected < 5:
                notes.append("Few selections in the comparison; the ratio can swing widely.")

        groups.append({"cohort_name": name, "n": n, "selected": selected, "selection_rate": round(rate, 3),
                       "ci_low": low, "ci_high": high, "impact_ratio": round(ratio, 3) if ratio is not None else None,
                       "fisher_p_value": round(p_value, 4) if p_value is not None else None,
                       "status": status, "unstable_ratio": unstable, "notes": notes})

    compared = [g for g in groups if g["status"] in (STATUS_SUPPORTED, STATUS_INDICATOR, STATUS_NONE)]
    worst = max((g["status"] for g in groups), key=lambda s: SEVERITY[s], default=STATUS_INSUFFICIENT)
    if not compared and worst in (STATUS_NONE, STATUS_REFERENCE):
        worst = STATUS_INSUFFICIENT
    overall = worst if worst != STATUS_REFERENCE else STATUS_NONE
    if not compared and overall == STATUS_NONE:
        overall = STATUS_INSUFFICIENT

    missing_share = missing / total if total else 0.0
    summary = {
        STATUS_SUPPORTED: "At least one cohort shows a statistically supported disparity in selection rates.",
        STATUS_INDICATOR: "At least one cohort shows a potential disparity indicator that is not statistically supported at the current sample size.",
        STATUS_INSUFFICIENT: "There is not enough cohort data for a reliable comparison. This is not evidence that the process is fair.",
        STATUS_NONE: "No disparity indicators were observed among the compared cohorts. Small samples limit how much this rules out.",
    }[overall]
    if missing_share > 0.2:
        summary += f" Cohort data is missing for {missing_share:.0%} of candidates, so results may not represent the full pool."
    return {"selection_definition": selection_label, "total_evaluated": total, "with_cohort": known_n,
            "missing_cohort": missing, "reference_cohort": reference, "threshold": threshold, "alpha": alpha,
            "min_group_size": minimum, "groups": groups, "overall_status": overall, "summary": summary}
