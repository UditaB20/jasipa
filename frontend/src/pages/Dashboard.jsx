import { CheckCircle2, ArrowRight, Users } from "lucide-react";
import { getDashboard } from "../services/api";
import { BiasBadge, Card, EmptyState, ErrorState, PageHeader, PageLoading, RecommendationBadge, fmtDate, fmtScore, useAsync } from "../components/ui";

export default function Dashboard() {
  const { data, loading, error, reload } = useAsync(getDashboard, []);
  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  const maxStage = Math.max(1, ...data.pipeline.map((s) => s.count));
  return (
    <div className="page">
      <PageHeader title="Dashboard" subtitle="Where candidates are in the pipeline and which decisions are waiting on you." />

      <div className="grid grid-4 mb-24">
        <Stat label="Candidates" value={data.total_candidates} hint="Across all open jobs" />
        <Stat label="Awaiting your decision" value={data.awaiting_decision} hint="Panel and bias check complete" attention={data.awaiting_decision > 0} />
        <Stat label="Open jobs" value={data.open_jobs} hint="With active rubrics" />
        <Stat label="Bias checks needing attention" value={data.bias_attention} hint="Indicator or supported disparity" attention={data.bias_attention > 0} />
      </div>

      <Card title="Pipeline" pad={false} className="mb-24">
        <div className="funnel">
          {data.pipeline.map((stage) => (
            <div key={stage.label} className="funnel-step">
              <div className="funnel-count">{stage.count}</div>
              <div className="funnel-label">{stage.label}</div>
              <div className="funnel-bar"><span style={{ width: `${(stage.count / maxStage) * 100}%` }} /></div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Decisions needed" subtitle="Oldest first. Every application is closed by a person, never by the system."
        actions={<a className="btn btn-ghost btn-sm" href="#/candidates?stage=awaiting">View all <ArrowRight size={13} /></a>} pad={false}>
        {data.awaiting_list.length === 0 ? (
          <EmptyState icon={CheckCircle2} title="No decisions waiting">
            Candidates appear here once their panel evaluation and bias check are complete.
          </EmptyState>
        ) : (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr><th>Candidate</th><th className="hide-sm">Job</th><th className="right">Panel score</th><th>Recommendation</th><th className="hide-sm">Bias check</th><th className="hide-sm">Waiting since</th></tr>
              </thead>
              <tbody>
                {data.awaiting_list.map((row) => (
                  <tr key={row.candidate_id} className="clickable" onClick={() => { window.location.hash = `/candidates/${row.candidate_id}`; }}>
                    <td>
                      <div className="cell-title">{row.name}</div>
                      {row.requires_two_reviewers && <div className="cell-sub">Needs two reviewers</div>}
                    </td>
                    <td className="hide-sm muted">{row.job_title || "—"}</td>
                    <td className="right num">{fmtScore(row.merged_score)}</td>
                    <td><RecommendationBadge value={row.recommendation} /></td>
                    <td className="hide-sm"><BiasBadge value={row.bias_flag_status} /></td>
                    <td className="hide-sm muted">{fmtDate(row.waiting_since)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      {data.total_candidates === 0 && (
        <div className="mt-24"><EmptyState icon={Users} title="No candidates yet" action={<a className="btn btn-primary" href="#/candidates">Add a candidate</a>}>
          Upload a resume or share the candidate portal so applicants can apply.
        </EmptyState></div>
      )}
    </div>
  );
}

function Stat({ label, value, hint, attention }) {
  return (
    <div className={`card stat ${attention ? "attention" : ""}`}>
      <div className="stat-label">{label}</div>
      <div className="stat-value">{value}</div>
      <div className="stat-hint">{hint}</div>
    </div>
  );
}
