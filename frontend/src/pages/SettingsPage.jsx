import { useState } from "react";
import { getExpertTasks, getMcpTools, getPanelConfig, getStrategyEffectiveness, updateExpertTask, updatePanelConfig } from "../services/api";
import { Alert, Badge, Card, ErrorState, Field, PageHeader, PageLoading, fmtDateTime, useAsync, useToast } from "../components/ui";

const STRATEGY_LABELS = { llm: "LLM", regex: "Resume rules", heuristic: "Answer rubric", star: "STAR rubric", template: "Template", human_expert: "Expert queue" };

export default function SettingsPage({ user }) {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => Promise.all([getPanelConfig(), getStrategyEffectiveness(), getExpertTasks("ALL"), getMcpTools()]), []);
  const [saving, setSaving] = useState(false);
  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [config, effectiveness, tasks, mcp] = data;

  const saveConfig = async (patch) => {
    setSaving(true);
    try { await updatePanelConfig(patch); toast("Setting saved and recorded in the audit log."); await reload(); }
    catch (err) { toast(err.message, "error"); } finally { setSaving(false); }
  };
  const setTask = async (task, status) => {
    try { await updateExpertTask(task.task_id, { status, assigned_to: user.email }); await reload(); }
    catch (err) { toast(err.message, "error"); }
  };
  const open = tasks.filter((t) => t.status !== "COMPLETED");

  return (
    <div className="page page-narrow">
      <PageHeader title="Settings" subtitle="Evaluation configuration and the health of the automated scoring." />
      <div className="stack">
        <Card title="Account">
          <dl className="kv"><dt>Name</dt><dd>{user.name}</dd><dt>Email</dt><dd>{user.email}</dd><dt>Role</dt><dd>HR reviewer: can record decisions and edit rubrics</dd></dl>
        </Card>

        <Card title="Panel summary" subtitle="An optional LLM can rephrase the panel's computed facts into a summary. It never changes scores or routing.">
          <div className="form-grid">
            <Field label="Summary writer">
              <select className="select" value={config.use_llm_synthesis ? "llm" : "template"} disabled={saving} onChange={(e) => saveConfig({ use_llm_synthesis: e.target.value === "llm" })}>
                <option value="llm">LLM when available, template otherwise</option><option value="template">Template only</option>
              </select>
            </Field>
            <Field label="Detail level">
              <select className="select" value={config.explanation_detail_level} disabled={saving} onChange={(e) => saveConfig({ explanation_detail_level: e.target.value })}>
                <option value="brief">Brief</option><option value="detailed">Detailed</option><option value="comprehensive">Comprehensive</option>
              </select>
            </Field>
          </div>
        </Card>

        <Card title="Automated scoring health" subtitle={`Last ${effectiveness.period_days} days`}>
          {effectiveness.alert && <div className="mb-16"><Alert tone="warning">{effectiveness.alert_message}</Alert></div>}
          {!effectiveness.evaluation_invocations ? <p className="muted small">No evaluations in this period.</p> : (
            <>
              <p className="small mb-16">{effectiveness.evaluation_invocations} evaluations; {effectiveness.fallback_invocations} used a fallback strategy ({effectiveness.fallback_rate_percent}%).</p>
              <div className="table-wrap"><table className="table">
                <thead><tr><th>Strategy</th><th className="right">Attempts</th><th className="right">Failure rate</th><th className="right">Avg latency</th></tr></thead>
                <tbody>{Object.entries(effectiveness.by_strategy).map(([name, m]) => (
                  <tr key={name}><td>{STRATEGY_LABELS[name] || name}</td><td className="right num">{m.attempts}</td><td className="right num">{Math.round(m.failure_rate * 100)}%</td><td className="right num">{m.average_latency_ms} ms</td></tr>
                ))}</tbody>
              </table></div>
            </>
          )}
        </Card>

        <Card title="Expert review queue" subtitle="Answers that no automated strategy could score are sent here for a person to score." pad={!open.length}>
          {!open.length ? <p className="muted small">Nothing waiting.</p> : open.map((t) => (
            <div key={t.task_id} className="list-item">
              <div><div className="cell-title">{t.candidate_name || t.candidate_id}</div><div className="cell-sub">{t.reason} · {fmtDateTime(t.created_at)}</div></div>
              <div className="row"><Badge tone={t.status === "PENDING" ? "warning" : "accent"}>{t.status.replace("_", " ").toLowerCase()}</Badge>
                {t.status === "PENDING" ? <button className="btn btn-secondary btn-sm" onClick={() => setTask(t, "IN_PROGRESS")}>Take</button>
                  : <button className="btn btn-secondary btn-sm" onClick={() => setTask(t, "COMPLETED")}>Mark done</button>}</div>
            </div>
          ))}
        </Card>

        <Card title="ATS connector (MCP)" subtitle={`${mcp.tools.length} tools exposed to agents · protocol ${mcp.protocolVersion}. Recording a human decision is deliberately not exposed.`}>
          <div className="chips">{mcp.tools.map((t) => <span key={t.name} className="chip mono" title={t.description}>{t.name}</span>)}</div>
        </Card>
      </div>
    </div>
  );
}
