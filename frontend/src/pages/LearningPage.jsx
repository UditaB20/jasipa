import React, { useEffect, useMemo, useState } from "react";
import { getHiringLearningAnalytics, getEligibleOutcomes, getHiringOutcomeHistory, recordHiringOutcome } from "../services/api";

const today = new Date().toISOString().slice(0, 10);
const emptyForm = { candidate_id: "", hired_date: "", performance_rating: "", still_employed: "", months_employed: "", manager_name: "", promotion_date: "", attrition_reason: "", manager_feedback: "" };

export default function LearningPage({ currentUser }) {
  const [analytics, setAnalytics] = useState(null);
  const [eligible, setEligible] = useState([]);
  const [history, setHistory] = useState([]);
  const [message, setMessage] = useState("");
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [form, setForm] = useState(emptyForm);
  const [errors, setErrors] = useState({});
  const [feedbackTouched, setFeedbackTouched] = useState(false);

  async function refresh() {
    setLoading(true);
    try {
      const [stats, candidates, records] = await Promise.all([getHiringLearningAnalytics(), getEligibleOutcomes(), getHiringOutcomeHistory()]);
      setAnalytics(stats); setEligible(candidates); setHistory(records);
      setForm(f => {
        const selected = candidates.find(c => c.candidate_id === f.candidate_id) || candidates[0];
        if (!selected) return { ...f, candidate_id: "" };
        const o = selected.outcome;
        return { ...f, candidate_id: selected.candidate_id, hired_date: o?.hired_date || "", performance_rating: o?.performance_rating == null ? "" : String(o.performance_rating), still_employed: o?.still_employed == null ? "" : String(o.still_employed), months_employed: o?.months_employed == null ? "" : String(o.months_employed), manager_name: o?.manager_name || "", promotion_date: o?.promotion_date || "", attrition_reason: o?.attrition_reason || "", manager_feedback: o?.manager_feedback || "" };
      });
    } catch (err) { setMessage(err.message); }
    finally { setLoading(false); }
  }
  useEffect(() => { refresh(); }, []);

  const evaluated = useMemo(() => history.filter(row => row.evaluation), [history]);
  const avgPerformance = analytics?.average_performance;
  const active = analytics?.still_employed_count ?? 0;
  const knownStatus = analytics?.retention_observations ?? 0;
  const retentionPct = analytics?.retention_rate == null ? null : Math.round(analytics.retention_rate * 100);

  function update(field, value) { setForm(current => ({ ...current, [field]: value })); setErrors(current => ({ ...current, [field]: "" })); }
  function selectCandidate(candidateId) {
    const selected = eligible.find(c => c.candidate_id === candidateId);
    const o = selected?.outcome;
    setForm({ ...emptyForm, candidate_id: candidateId, hired_date: o?.hired_date || "", performance_rating: o?.performance_rating == null ? "" : String(o.performance_rating), still_employed: o?.still_employed == null ? "" : String(o.still_employed), months_employed: o?.months_employed == null ? "" : String(o.months_employed), manager_name: o?.manager_name || "", promotion_date: o?.promotion_date || "", attrition_reason: o?.attrition_reason || "", manager_feedback: o?.manager_feedback || "" });
    setErrors({}); setFeedbackTouched(false);
  }
  function validate() {
    const next = {};
    if (!form.candidate_id) next.candidate_id = "Choose an approved candidate.";
    if (!form.hired_date) next.hired_date = "Hire date is required.";
    else if (form.hired_date >= today) next.hired_date = "Hire date must be before today.";
    if (!form.performance_rating || Number(form.performance_rating) < 1 || Number(form.performance_rating) > 5) next.performance_rating = "Enter a rating from 1 to 5.";
    if (form.still_employed === "") next.still_employed = "Select Yes or No.";
    if (form.months_employed === "" || !Number.isInteger(Number(form.months_employed)) || Number(form.months_employed) < 0 || Number(form.months_employed) > 120) next.months_employed = "Enter a whole number from 0 to 120.";
    setErrors(next); return Object.keys(next).length === 0;
  }
  async function submit(e) {
    e.preventDefault(); setMessage("");
    if (!validate()) return;
    setSaving(true);
    try {
      await recordHiringOutcome({ ...form, manager_name: form.manager_name || currentUser?.name || null, manager_email: currentUser?.email || "", hired_date: new Date(`${form.hired_date}T12:00:00`).toISOString(), promotion_date: form.promotion_date ? new Date(`${form.promotion_date}T12:00:00`).toISOString() : null, performance_rating: Number(form.performance_rating), still_employed: form.still_employed === "true", months_employed: Number(form.months_employed), attrition_reason: form.still_employed === "false" ? (form.attrition_reason || null) : null });
      setMessage("Hiring outcome saved."); setForm(emptyForm); setFeedbackTouched(false); setErrors({}); await refresh();
    } catch (err) { setMessage(err.message); }
    finally { setSaving(false); }
  }

  const panel = { background: "rgba(30,41,59,.55)", border: "1px solid #334155", borderRadius: 12, padding: 20 };
  const labelStyle = { display: "block", color: "#cbd5e1", fontSize: 13, fontWeight: 600, marginBottom: 5 };
  const inputStyle = { width: "100%", padding: "10px 12px", borderRadius: 7, border: "1px solid #475569", background: "#0f172a", color: "#f8fafc", font: "inherit" };
  const errorStyle = { color: "#fda4af", fontSize: 12, marginTop: 3 };
  const cardStyle = { ...panel, minHeight: 112 };
  return <div className="page-container" style={{ maxWidth: 1250 }}>
    <div className="page-header"><div><h2 className="page-title">Hiring Outcomes &amp; Learning</h2><p className="page-subtitle">Track reported outcomes and compare them with the evaluation record.</p></div><button className="btn btn-secondary" onClick={refresh} disabled={loading}>{loading ? "Refreshing…" : "Refresh data"}</button></div>
    {message && <div role="status" style={{ ...panel, padding: "10px 14px", marginBottom: 14, color: message.includes("saved") ? "#6ee7b7" : "#fbbf24" }}>{message}</div>}

    <section aria-label="Outcome overview" style={{ marginBottom: 20 }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(210px,1fr))", gap: 12 }}>
        <div style={cardStyle}><div style={{ color: "#94a3b8", fontSize: 12 }}>Hires with recorded outcomes</div><strong style={{ display: "block", color: "#f8fafc", fontSize: 28 }}>{analytics?.outcomes_recorded ?? "—"}</strong><div style={{ color: "#94a3b8", fontSize: 12 }}>{eligible.filter(c => !c.has_outcome).length} approved candidate{eligible.filter(c => !c.has_outcome).length === 1 ? "" : "s"} awaiting outcome entry</div></div>
        <div style={cardStyle}><div style={{ color: "#94a3b8", fontSize: 12 }}>Average performance rating</div><strong style={{ display: "block", color: "#f8fafc", fontSize: 28 }}>{avgPerformance == null ? "—" : `${avgPerformance.toFixed(1)} / 5`}</strong><div style={{ color: "#94a3b8", fontSize: 12 }}>{analytics?.rated_outcomes ?? 0} manager rating{analytics?.rated_outcomes === 1 ? "" : "s"} recorded</div></div>
        <div style={cardStyle}><div style={{ color: "#94a3b8", fontSize: 12 }}>Still employed</div><strong style={{ display: "block", color: "#f8fafc", fontSize: 28 }}>{retentionPct == null ? "—" : `${retentionPct}%`}</strong><div style={{ color: "#94a3b8", fontSize: 12 }}>{active} of {knownStatus} known employment statuses</div></div>
        <div style={cardStyle}><div style={{ color: "#94a3b8", fontSize: 12 }}>Last outcome update</div><strong style={{ display: "block", color: "#f8fafc", fontSize: 17, marginTop: 7 }}>{analytics?.last_updated ? new Date(analytics.last_updated).toLocaleString() : "No records yet"}</strong></div>
      </div>
      {analytics?.small_sample && <div style={{ marginTop: 12, padding: "12px 16px", borderRadius: 9, background: "rgba(245,158,11,.1)", border: "1px solid rgba(245,158,11,.35)", color: "#fcd34d", fontSize: 13 }}>Small sample: {analytics?.outcomes_recorded ?? 0} outcome records ({analytics?.rated_outcomes ?? 0} rated; {analytics?.retention_observations ?? 0} with known employment status). Treat rates and patterns as early descriptions; at least {analytics?.minimum_sample_for_trend ?? 15} records are recommended before interpreting trends.</div>}
      {analytics?.rated_outcomes > 0 && <div style={{ ...panel, display: "flex", flexWrap: "wrap", gap: "8px 20px", marginTop: 12, padding: "12px 16px" }}><strong style={{ color: "#cbd5e1", fontSize: 12, width: "100%" }}>Performance distribution</strong>{Object.entries(analytics.performance_bands || {}).map(([label,count]) => <span key={label} style={{ color: "#94a3b8", fontSize: 12 }}>{label}: <strong style={{ color: "#f8fafc" }}>{count}</strong></span>)}</div>}
    </section>

    <section style={{ ...panel, marginBottom: 20 }}>
      <h3 style={{ color: "#f8fafc", fontSize: 16, marginBottom: 4 }}>Recorded hires and evaluation context</h3>
      <p style={{ color: "#94a3b8", fontSize: 12, marginBottom: 14 }}>Outcome data is manager reported. Scores are shown for context and are not labeled as correct or incorrect predictions.</p>
      {history.length === 0 ? <p style={{ color: "#94a3b8", fontSize: 13 }}>No outcomes recorded yet.</p> : <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Candidate / role</th><th>Hire date</th><th>Performance</th><th>Employment</th><th>Tenure</th><th>Manager</th><th>Evaluation scores (resume / technical / behavioral / panel)</th></tr></thead><tbody>{history.map(row => <tr key={row.outcome_id}><td>{row.candidate_name}<div style={{ color: "#94a3b8", fontSize: 12 }}>{row.role}</div></td><td>{new Date(row.hired_date).toLocaleDateString()}</td><td>{row.performance_rating == null ? "Not rated" : `${Number(row.performance_rating).toFixed(1)} / 5`}</td><td>{row.still_employed == null ? "Not recorded" : row.still_employed ? "Active" : "Left"}</td><td>{row.months_employed == null ? "—" : `${row.months_employed} mo`}</td><td>{row.manager_name || "—"}{row.promotion_date && <div style={{ color: "#94a3b8", fontSize: 11 }}>Promoted {new Date(row.promotion_date).toLocaleDateString()}</div>}</td><td>{row.evaluation ? `${row.evaluation.resume_score} / ${row.evaluation.technical_score} / ${row.evaluation.behavioral_score} / ${row.evaluation.merged_score}` : "No panel scores"}<div style={{ color: "#94a3b8", fontSize: 11 }}>{row.evaluation?.recommendation || ""}</div></td></tr>)}</tbody></table></div>}
    </section>

    <section style={{ ...panel, marginBottom: 20 }}>
      <h3 style={{ color: "#f8fafc", fontSize: 16, marginBottom: 4 }}>Early score/outcome view</h3>
      <p style={{ color: "#94a3b8", fontSize: 12, marginBottom: 14 }}>These are grouped averages, not validated predictor tests. They are hidden as a comparison until at least five rated hires are available.</p>
      {analytics?.rated_outcomes >= (analytics?.minimum_sample_for_trend ?? 15) && <div style={{ overflowX: "auto" }}><table className="data-table"><thead><tr><th>Evaluation dimension</th><th>Average score</th><th>Average reported performance</th><th>Rated hires</th></tr></thead><tbody>{[ ["Resume", "resume_score"], ["Technical", "technical_score"], ["Behavioral", "culture_score"], ["Panel", "merged_score"] ].map(([name,key]) => { const rows = evaluated.filter(row => row.performance_rating != null); const meanScore = rows.filter(row => row.evaluation?.[key] != null); return <tr key={key}><td>{name}</td><td>{meanScore.length ? (meanScore.reduce((sum,row)=>sum+row.evaluation[key],0)/meanScore.length).toFixed(1) : "—"}</td><td>{meanScore.length ? (meanScore.reduce((sum,row)=>sum+Number(row.performance_rating),0)/meanScore.length).toFixed(1) : "—"} / 5</td><td>{meanScore.length}</td></tr>; })}</tbody></table></div>}
      {analytics?.rated_outcomes < (analytics?.minimum_sample_for_trend ?? 15) && <p style={{ color: "#cbd5e1", fontSize: 13 }}>There are {analytics?.rated_outcomes ?? 0} rated outcomes. Exploratory score/outcome summaries will appear after at least {analytics?.minimum_sample_for_trend ?? 15} rated hires.</p>}
      <p style={{ color: "#94a3b8", fontSize: 12, marginTop: 12 }}>No benchmarks or weight recommendations are shown because JASIPA has no validated baseline for this organization. Outcomes do not automatically modify rubrics or hiring decisions.</p>
    </section>

    <section style={{ ...panel, maxWidth: 900 }}>
      <h3 style={{ color: "#f8fafc", fontSize: 16 }}>Record or update a post-hire outcome</h3><p style={{ color: "#94a3b8", fontSize: 12, margin: "4px 0 18px" }}>Select an approved candidate with an actual hire date. Approved candidates awaiting outcome entry are not confirmed hires. Records marked as test, demo, mock, or E2E are excluded from tracking. Performance ratings and employment status are required for this check-in.</p>
      {!eligible.length ? <p style={{ color: "#94a3b8", fontSize: 13 }}>No approved non-test candidates are awaiting outcome entry.</p> : <form onSubmit={submit} noValidate>
        <fieldset style={{ border: 0, padding: 0, margin: 0 }}><legend style={{ color: "#a5b4fc", fontWeight: 700, fontSize: 13, marginBottom: 10 }}>HIRE DETAILS</legend><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 14, marginBottom: 20 }}>
          <div><label style={labelStyle} htmlFor="outcome-candidate">Approved candidate</label><select id="outcome-candidate" style={inputStyle} value={form.candidate_id} onChange={e=>selectCandidate(e.target.value)}><option value="">Select candidate</option>{eligible.map(c=><option key={c.candidate_id} value={c.candidate_id}>{c.name}{c.role ? ` · ${c.role}` : ""}{c.has_outcome ? " · update outcome" : ""}</option>)}</select>{errors.candidate_id && <div style={errorStyle}>{errors.candidate_id}</div>}</div>
          <div><label style={labelStyle} htmlFor="hire-date">Hire date</label><input id="hire-date" style={inputStyle} type="date" max={today} value={form.hired_date} onChange={e=>update("hired_date",e.target.value)}/>{errors.hired_date && <div style={errorStyle}>{errors.hired_date}</div>}</div>
        </div></fieldset>
        <fieldset style={{ border: 0, borderTop: "1px solid #334155", padding: "16px 0 0", margin: 0 }}><legend style={{ color: "#a5b4fc", fontWeight: 700, fontSize: 13, paddingRight: 8 }}>EMPLOYMENT STATUS</legend><div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 14, marginBottom: 20 }}>
          <div><label style={labelStyle} htmlFor="still-employed">Still employed?</label><select id="still-employed" style={inputStyle} value={form.still_employed} onChange={e=>update("still_employed",e.target.value)}><option value="">Select status</option><option value="true">Yes, still employed</option><option value="false">No, left the company</option></select>{errors.still_employed && <div style={errorStyle}>{errors.still_employed}</div>}</div>
          <div><label style={labelStyle} htmlFor="tenure-months">Months employed (0–120)</label><input id="tenure-months" style={inputStyle} type="number" min="0" max="120" step="1" value={form.months_employed} onChange={e=>update("months_employed",e.target.value)} placeholder="e.g. 3"/>{errors.months_employed && <div style={errorStyle}>{errors.months_employed}</div>}</div>
          {form.still_employed === "false" && <div style={{ gridColumn: "1 / -1" }}><label style={labelStyle} htmlFor="attrition-reason">Reason for leaving (optional)</label><textarea id="attrition-reason" style={inputStyle} rows={2} maxLength={1000} value={form.attrition_reason} onChange={e=>update("attrition_reason",e.target.value)} /></div>}
        </div></fieldset>
        <fieldset style={{ border: 0, borderTop: "1px solid #334155", padding: "16px 0 0", margin: 0 }}><legend style={{ color: "#a5b4fc", fontWeight: 700, fontSize: 13, paddingRight: 8 }}>PERFORMANCE CHECK-IN</legend>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(230px,1fr))", gap: 14, marginBottom: 14 }}><div><label style={labelStyle} htmlFor="rating">Manager-reported rating (1–5)</label><div style={{ display: "flex", gap: 12, alignItems: "center" }}><input id="rating" type="range" min="1" max="5" step="0.1" value={form.performance_rating || "3"} onChange={e=>update("performance_rating",e.target.value)} style={{ flex: 1 }}/><strong style={{ color: form.performance_rating ? "#f8fafc" : "#fbbf24", minWidth: 78 }}>{form.performance_rating ? `${Number(form.performance_rating).toFixed(1)} / 5` : "Select rating"}</strong></div>{errors.performance_rating && <div style={errorStyle}>{errors.performance_rating}</div>}</div>
            <div><label style={labelStyle} htmlFor="manager-name">Manager name <span style={{ color: "#94a3b8", fontWeight: 400 }}>(optional)</span></label><input id="manager-name" style={inputStyle} maxLength={160} value={form.manager_name} onChange={e=>update("manager_name",e.target.value)} placeholder="Name of the manager providing this check-in"/></div>
            <div><label style={labelStyle} htmlFor="manager-feedback">Manager feedback <span style={{ color: "#94a3b8", fontWeight: 400 }}>(recommended)</span></label><textarea id="manager-feedback" style={inputStyle} rows={3} maxLength={3000} value={form.manager_feedback} onBlur={()=>setFeedbackTouched(true)} onChange={e=>update("manager_feedback",e.target.value)} placeholder="A short note helps interpret this rating."/></div>
            <div><label style={labelStyle} htmlFor="promotion-date">Promotion date <span style={{ color: "#94a3b8", fontWeight: 400 }}>(optional)</span></label><input id="promotion-date" style={inputStyle} type="date" max={today} value={form.promotion_date} onChange={e=>update("promotion_date",e.target.value)}/></div>
          </div>
          {feedbackTouched && !form.manager_feedback.trim() && <p style={{ color: "#fbbf24", fontSize: 12, marginBottom: 10 }}>Manager feedback is optional, but adding context improves later review.</p>}
        </fieldset>
        <div style={{ display: "flex", justifyContent: "flex-end", paddingTop: 12 }}><button className="btn btn-success" type="submit" disabled={saving}>{saving ? "Saving…" : eligible.find(c => c.candidate_id === form.candidate_id)?.has_outcome ? "Update outcome" : "Save outcome"}</button></div>
      </form>}
    </section>
    <p style={{ color: "#94a3b8", fontSize: 12, marginTop: 14 }}>{analytics?.notice || "Outcomes are manager reported. Insights remain exploratory and never change hiring decisions automatically."}</p>
  </div>;
}
