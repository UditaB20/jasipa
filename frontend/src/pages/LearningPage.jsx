import { useState } from "react";
import { TrendingUp } from "lucide-react";
import { getEligibleOutcomes, getHiringLearningAnalytics, getHiringOutcomeHistory, recordHiringOutcome } from "../services/api";
import { Alert, Card, EmptyState, ErrorState, Field, PageHeader, PageLoading, Spinner, fmtDate, useAsync, useToast } from "../components/ui";

const today = new Date().toISOString().slice(0, 10);
const emptyForm = { candidate_id: "", hired_date: "", performance_rating: "", still_employed: "", months_employed: "", manager_name: "", promotion_date: "", attrition_reason: "", manager_feedback: "" };

function formFor(candidate) {
  const o = candidate?.outcome;
  if (!candidate) return emptyForm;
  return {
    ...emptyForm, candidate_id: candidate.candidate_id, hired_date: o?.hired_date || "",
    performance_rating: o?.performance_rating == null ? "" : String(o.performance_rating),
    still_employed: o?.still_employed == null ? "" : String(o.still_employed),
    months_employed: o?.months_employed == null ? "" : String(o.months_employed),
    manager_name: o?.manager_name || "", promotion_date: o?.promotion_date || "", attrition_reason: o?.attrition_reason || "", manager_feedback: o?.manager_feedback || "",
  };
}

export default function LearningPage({ user }) {
  const toast = useToast();
  const { data, loading, error, reload } = useAsync(() => Promise.all([getHiringLearningAnalytics(), getEligibleOutcomes(), getHiringOutcomeHistory()]), []);
  const [form, setForm] = useState(null);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [serverError, setServerError] = useState(null);

  if (loading && !data) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;
  const [analytics, eligible, history] = data;
  const current = form || formFor(eligible[0]);
  const update = (field, value) => { setForm({ ...current, [field]: value }); setErrors({ ...errors, [field]: null }); };

  const validate = () => {
    const next = {};
    if (!current.candidate_id) next.candidate_id = "Choose an approved candidate.";
    if (!current.hired_date) next.hired_date = "Hire date is required.";
    else if (current.hired_date >= today) next.hired_date = "Hire date must be before today.";
    const rating = Number(current.performance_rating);
    if (!current.performance_rating || rating < 1 || rating > 5) next.performance_rating = "Enter a rating from 1 to 5.";
    if (current.still_employed === "") next.still_employed = "Select an employment status.";
    const months = Number(current.months_employed);
    if (current.months_employed === "" || !Number.isInteger(months) || months < 0 || months > 120) next.months_employed = "Enter a whole number from 0 to 120.";
    setErrors(next);
    return !Object.keys(next).length;
  };

  const submit = async (e) => {
    e.preventDefault();
    setServerError(null);
    if (!validate()) return;
    setSaving(true);
    try {
      await recordHiringOutcome({
        ...current, manager_name: current.manager_name || null, manager_email: user.email,
        hired_date: new Date(`${current.hired_date}T12:00:00`).toISOString(),
        promotion_date: current.promotion_date ? new Date(`${current.promotion_date}T12:00:00`).toISOString() : null,
        performance_rating: Number(current.performance_rating), still_employed: current.still_employed === "true",
        months_employed: Number(current.months_employed), attrition_reason: current.still_employed === "false" ? current.attrition_reason || null : null,
      });
      toast("Hiring outcome saved.");
      setForm(null);
      await reload();
    } catch (err) {
      setServerError(err.message);
    } finally {
      setSaving(false);
    }
  };

  const retention = analytics.retention_rate == null ? "—" : `${Math.round(analytics.retention_rate * 100)}%`;
  const selected = eligible.find((c) => c.candidate_id === current.candidate_id);
  return (
    <div className="page">
      <PageHeader title="Hiring outcomes" subtitle="Manager-reported results for approved hires, shown next to their evaluation scores. Outcomes never change rubrics or decisions automatically." />
      <div className="grid grid-3 mb-24">
        <div className="card stat"><div className="stat-label">Outcomes recorded</div><div className="stat-value">{analytics.outcomes_recorded}</div><div className="stat-hint">{analytics.rated_outcomes} with a rating</div></div>
        <div className="card stat"><div className="stat-label">Average performance</div><div className="stat-value">{analytics.average_performance ?? "—"}<span className="small dim"> / 5</span></div><div className="stat-hint">Manager reported</div></div>
        <div className="card stat"><div className="stat-label">Still employed</div><div className="stat-value">{retention}</div><div className="stat-hint">{analytics.still_employed_count} of {analytics.retention_observations} with known status</div></div>
      </div>
      {analytics.small_sample && <div className="mb-16"><Alert tone="info">Fewer than {analytics.minimum_sample_for_trend} outcomes are recorded. Treat these figures as anecdotal, not as trends.</Alert></div>}

      <div className="split">
        <Card title="Recorded hires" pad={false}>
          {history.length === 0 ? <EmptyState icon={TrendingUp} title="No outcomes recorded">Record a check-in for an approved hire to start tracking.</EmptyState> : (
            <div className="table-wrap">
              <table className="table">
                <thead><tr><th>Hire</th><th className="right">Rating</th><th>Status</th><th className="right hide-sm">Panel score</th></tr></thead>
                <tbody>
                  {history.map((row) => (
                    <tr key={row.outcome_id}>
                      <td><div className="cell-title">{row.candidate_name}</div><div className="cell-sub">{row.role} · hired {fmtDate(row.hired_date)}</div></td>
                      <td className="right num">{row.performance_rating == null ? "—" : Number(row.performance_rating).toFixed(1)}</td>
                      <td className="muted">{row.still_employed == null ? "Unknown" : row.still_employed ? `Employed · ${row.months_employed} mo` : "Left"}</td>
                      <td className="right num hide-sm">{row.evaluation ? row.evaluation.merged_score : "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card title="Record a check-in" subtitle="For candidates with a human APPROVE decision.">
          {!eligible.length ? <p className="muted small">No approved candidates are waiting for an outcome.</p> : (
            <form onSubmit={submit} className="stack" noValidate>
              {serverError && <Alert tone="danger">{serverError}</Alert>}
              <Field label="Approved candidate" error={errors.candidate_id}>
                <select className="select" value={current.candidate_id} onChange={(e) => { setForm(formFor(eligible.find((c) => c.candidate_id === e.target.value))); setErrors({}); }}>
                  {eligible.map((c) => <option key={c.candidate_id} value={c.candidate_id}>{c.name}{c.role ? ` · ${c.role}` : ""}{c.has_outcome ? " (update)" : ""}</option>)}
                </select>
              </Field>
              <div className="form-grid">
                <Field label="Hire date" error={errors.hired_date}><input className="input" type="date" max={today} value={current.hired_date} onChange={(e) => update("hired_date", e.target.value)} /></Field>
                <Field label="Rating (1–5)" error={errors.performance_rating}><input className="input num" type="number" min="1" max="5" step="0.1" value={current.performance_rating} onChange={(e) => update("performance_rating", e.target.value)} /></Field>
                <Field label="Employment" error={errors.still_employed}>
                  <select className="select" value={current.still_employed} onChange={(e) => update("still_employed", e.target.value)}>
                    <option value="">Select</option><option value="true">Still employed</option><option value="false">Has left</option>
                  </select>
                </Field>
                <Field label="Months employed" error={errors.months_employed}><input className="input num" type="number" min="0" max="120" value={current.months_employed} onChange={(e) => update("months_employed", e.target.value)} /></Field>
                {current.still_employed === "false" && <Field className="span-2" label="Reason for leaving (optional)"><input className="input" value={current.attrition_reason} onChange={(e) => update("attrition_reason", e.target.value)} /></Field>}
                <Field label="Manager (optional)"><input className="input" value={current.manager_name} onChange={(e) => update("manager_name", e.target.value)} /></Field>
                <Field label="Promotion date (optional)"><input className="input" type="date" max={today} value={current.promotion_date} onChange={(e) => update("promotion_date", e.target.value)} /></Field>
                <Field className="span-2" label="Manager feedback (optional)"><textarea className="textarea" rows={3} maxLength={3000} value={current.manager_feedback} onChange={(e) => update("manager_feedback", e.target.value)} /></Field>
              </div>
              <div className="row" style={{ justifyContent: "flex-end" }}><button className="btn btn-primary" disabled={saving}>{saving && <Spinner />}{selected?.has_outcome ? "Update outcome" : "Save outcome"}</button></div>
            </form>
          )}
        </Card>
      </div>
    </div>
  );
}
