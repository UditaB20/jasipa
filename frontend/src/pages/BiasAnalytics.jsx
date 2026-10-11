import { useState } from "react";
import { AlertTriangle, Scale } from "lucide-react";
import { getCohortAnalytics } from "../services/api";
import { Alert, BiasBadge, BIAS, Card, EmptyState, ErrorState, PageHeader, PageLoading, Tabs, useAsync } from "../components/ui";
import { BIAS_DISPLAY, fmtP, fmtPct as pct, fmtRatio } from "../lib/format";

export default function BiasAnalytics() {
  const { data, loading, error, reload } = useAsync(getCohortAnalytics, []);
  const [stage, setStage] = useState("ai_recommendation");
  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const analysis = data[stage];
  const overallTone = { STATISTICALLY_SUPPORTED_DISPARITY: "danger", POTENTIAL_DISPARITY_INDICATOR: "warning", INSUFFICIENT_DATA: "info", NO_INDICATOR_DETECTED: "success" }[analysis.overall_status];
  const overallLabel = BIAS_DISPLAY[analysis.display_status]?.label || BIAS[analysis.overall_status]?.label;

  return (
    <div className="page">
      <PageHeader title="Bias monitor" subtitle="Selection rates by monitoring cohort, at the AI recommendation stage and in final human decisions. Results inform reviewers; they never change scores or decisions." />

      <Tabs active={stage} onChange={setStage} tabs={[
        { id: "ai_recommendation", label: "AI panel recommendations", badge: BIAS[data.ai_recommendation.overall_status]?.label, badgeTone: BIAS[data.ai_recommendation.overall_status]?.tone },
        { id: "human_decision", label: "Final human decisions", badge: BIAS[data.human_decision.overall_status]?.label, badgeTone: BIAS[data.human_decision.overall_status]?.tone },
      ]} />

      <div className="mb-16"><Alert tone={overallTone} title={`${overallLabel}${analysis.significance ? ` · ${analysis.significance}` : ""}`}>{analysis.summary}</Alert></div>

      <div className="grid grid-4 mb-16">
        <div className="card stat"><div className="stat-label">Candidates compared</div><div className="stat-value">{analysis.with_cohort}</div><div className="stat-hint">of {analysis.total_evaluated} evaluated</div></div>
        <div className={`card stat ${analysis.missing_cohort ? "attention" : ""}`}><div className="stat-label">Cohort not recorded</div><div className="stat-value">{analysis.missing_cohort}</div><div className="stat-hint">Excluded from comparisons</div></div>
        <div className="card stat"><div className="stat-label">Reference cohort</div><div className="stat-value" style={{ fontSize: 18, marginTop: 12 }}>{analysis.reference_cohort || "None"}</div><div className="stat-hint">Highest rate with n ≥ {analysis.min_group_size}</div></div>
        <div className="card stat"><div className="stat-label">Screens</div><div className="stat-value" style={{ fontSize: 18, marginTop: 12 }}>ratio {analysis.threshold} · p {analysis.alpha}</div><div className="stat-hint">Four-fifths and Fisher's exact test</div></div>
      </div>

      <Card title="Cohort comparison" subtitle={`Selected = ${analysis.selection_definition}`} pad={false}>
        {analysis.groups.length === 0 ? <EmptyState icon={Scale} title="No cohort data yet">Rates appear once candidates with a recorded cohort reach this stage.</EmptyState> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th>Cohort</th><th className="right">n</th><th className="right">Selected</th><th className="right">Rate (95% interval)</th><th className="right">Impact ratio</th><th className="right">Fisher p</th><th>Result</th></tr></thead>
              <tbody>
                {analysis.groups.map((g) => (
                  <tr key={g.cohort_name}>
                    <td className="cell-title">{g.cohort_name}</td>
                    <td className="right num">{g.n}</td>
                    <td className="right num">{g.selected}</td>
                    <td className="right num">{pct(g.selection_rate)} <span className="dim xs">({pct(g.ci_low)}–{pct(g.ci_high)})</span></td>
                    <td className="right num">{fmtRatio(g.impact_ratio)}</td>
                    <td className="right num">{fmtP(g.fisher_p_value)}</td>
                    <td>
                      <div className="row wrap"><BiasBadge value={g.status} showQualifier />{g.unstable_ratio && <span className="badge badge-warning" title="One candidate's outcome would change the four-fifths result"><AlertTriangle size={11} />Fragile</span>}</div>
                      <div className="xs dim mt-4" style={{ maxWidth: 420 }}>{g.notes[0]}</div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>

      <div className="grid grid-2 mt-16">
        <Card title="How cohorts are defined">
          <p className="small muted">{data.cohort_definition}</p>
        </Card>
        <Card title="Method">
          <dl className="kv">
            <dt>Screening criterion</dt><dd className="small">Impact ratio below {analysis.threshold} with at least {analysis.min_group_size} candidates per cohort. Only this triggers "Disparity detected".</dd>
            <dt>Significance</dt><dd className="small">{data.method.significance} Shown as a qualifier, never as proof either way.</dd>
            <dt>Interval</dt><dd className="small">{data.method.interval}</dd>
            <dt>Per-decision checks</dt><dd className="small">{data.bias_checks_recorded} recorded with panel decisions</dd>
          </dl>
        </Card>
      </div>
    </div>
  );
}
