import React, { useState, useEffect } from "react";
import { Code, MessageSquare, Clock, CheckCircle2, AlertTriangle, ArrowRight } from "lucide-react";
import { getCandidates, getCandidate, getJobs } from "../services/api";

/**
 * Assessment Submissions (HR, read-only).
 *
 * Purpose: let HR audit exactly what a candidate submitted in the Candidate Portal and how the
 * Skill-Assessor / Culture-Fit agents scored it. HR can NOT enter or edit answers here — doing so
 * would inject non-candidate evidence into the panel decision. Data comes from the Assessment table.
 */
export default function AssessmentRoom({ selectedCandidateId, setSelectedCandidateId, setActivePage }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [candidate, setCandidate] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("submitted"); // submitted | all

  useEffect(() => {
    (async () => {
      try {
        const [cList, jList] = await Promise.all([getCandidates(), getJobs()]);
        setCandidates(cList || []);
        setJobs(jList || []);
        const initial = (cList || []).find(c => c.candidate_id === selectedCandidateId) || (cList || [])[0];
        if (initial) await loadCandidate(initial.candidate_id);
      } catch (err) {
        console.error("Error loading assessment submissions:", err);
      } finally {
        setLoading(false);
      }
    })();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function loadCandidate(id) {
    try {
      const detail = await getCandidate(id);
      setCandidate(detail);
      setSelectedCandidateId(id);
    } catch (err) {
      console.error("Error loading candidate:", err);
    }
  }

  // Backend orders assessments oldest -> newest; keep the latest attempt per test type.
  const latestOf = (type) => (candidate?.assessments || []).filter(a => a.test_type === type).at(-1);
  const tech = latestOf("TECHNICAL");
  const beh = latestOf("BEHAVIORAL");
  const jobTitle = jobs.find(j => j.jd_id === candidate?.target_jd_id)?.title || candidate?.target_jd_id || "Unassigned";

  const SUBMITTED_STAGES = ["TECHNICAL_ASSESSED", "BEHAVIORAL_ASSESSED", "PANEL_EVALUATED", "BIAS_CHECKED", "HUMAN_REVIEW_PENDING", "DECIDED"];
  const visibleCandidates = filter === "all" ? candidates : candidates.filter(c => SUBMITTED_STAGES.includes(c.current_stage));

  if (loading) {
    return <div className="page-container" style={{ textAlign: "center", padding: "80px 0", color: "#94a3b8" }}>Loading assessment submissions...</div>;
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ marginBottom: "20px" }}>
        <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>Assessment Submissions</h2>
        <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
          Read-only record of answers candidates submitted in the Candidate Portal and how each agent scored them.
          HR cannot enter or modify answers.
        </p>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "300px 1fr", gap: "24px" }}>
        {/* Candidate list */}
        <div className="glass-card" style={{ padding: "16px", alignSelf: "start" }}>
          <div style={{ display: "flex", gap: "6px", marginBottom: "12px" }}>
            {[["submitted", "With submissions"], ["all", "All candidates"]].map(([key, label]) => (
              <button key={key} id={`assessment-filter-${key}`} onClick={() => setFilter(key)}
                className={filter === key ? "btn btn-primary" : "btn btn-secondary"}
                style={{ padding: "4px 10px", fontSize: "0.72rem", flex: 1 }}>{label}</button>
            ))}
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: "6px", maxHeight: "65vh", overflowY: "auto" }}>
            {visibleCandidates.length === 0 && (
              <p style={{ fontSize: "0.8rem", color: "#64748b", padding: "12px" }}>No candidates have submitted assessments yet.</p>
            )}
            {visibleCandidates.map(c => {
              const active = candidate?.candidate_id === c.candidate_id;
              return (
                <div key={c.candidate_id} onClick={() => loadCandidate(c.candidate_id)}
                  style={{ padding: "10px 12px", borderRadius: "8px", cursor: "pointer",
                    background: active ? "rgba(99,102,241,0.18)" : "rgba(30,41,59,0.4)",
                    border: active ? "1px solid #6366f1" : "1px solid rgba(255,255,255,0.05)" }}>
                  <div style={{ fontSize: "0.82rem", fontWeight: 700, color: "#f8fafc" }}>{c.name}</div>
                  <div style={{ fontSize: "0.7rem", color: "#94a3b8" }}>{c.current_stage.replaceAll("_", " ")}</div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Submissions */}
        {candidate ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="glass-card" style={{ padding: "18px 20px", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h3 style={{ fontSize: "1.1rem", fontWeight: 800, color: "#f8fafc" }}>{candidate.name}</h3>
                <p style={{ fontSize: "0.78rem", color: "#94a3b8" }}>{candidate.email} · Role: {jobTitle}</p>
              </div>
              <button id="assessment-open-dossier" className="btn btn-secondary" style={{ padding: "6px 12px", fontSize: "0.75rem" }}
                onClick={() => setActivePage("candidate-detail")}>
                <span>Open Dossier</span><ArrowRight size={13} />
              </button>
            </div>

            <SubmissionCard title="Technical Assessment" agent="Skill-Assessor Agent" icon={Code} color="#818cf8" assessment={tech} />
            <SubmissionCard title="Behavioral (STAR) Assessment" agent="Culture-Fit Agent" icon={MessageSquare} color="#c084fc" assessment={beh} />
          </div>
        ) : (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>Select a candidate.</div>
        )}
      </div>
    </div>
  );
}

function SubmissionCard({ title, agent, icon: Icon, color, assessment }) {
  if (!assessment) {
    return (
      <div className="glass-card" style={{ padding: "20px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
          <Icon size={18} color={color} />
          <h4 style={{ fontSize: "1rem", fontWeight: 700, color: "#f8fafc" }}>{title}</h4>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", color: "#fbbf24", fontSize: "0.82rem" }}>
          <Clock size={15} /> Not submitted by the candidate yet. The panel will treat this stage as INSUFFICIENT_EVIDENCE.
        </div>
      </div>
    );
  }

  const answers = Object.fromEntries((assessment.answers || []).map(a => [a.question_id, a.answer_text]));
  const completed = assessment.status === "COMPLETED";

  return (
    <div className="glass-card" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <Icon size={18} color={color} />
          <div>
            <h4 style={{ fontSize: "1rem", fontWeight: 700, color: "#f8fafc" }}>{title}</h4>
            <p style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
              Scored by {agent} · submitted {new Date(assessment.completed_date).toLocaleString()}
            </p>
          </div>
        </div>
        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: "1.1rem", fontWeight: 800, color }}>{assessment.score}/100</div>
          <span style={{ fontSize: "0.7rem", fontWeight: 600, color: completed ? "#34d399" : "#fb7185", display: "inline-flex", alignItems: "center", gap: 4 }}>
            {completed ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}{assessment.status}
          </span>
        </div>
      </div>

      {assessment.skill_breakdown && Object.keys(assessment.skill_breakdown).length > 0 && (
        <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginBottom: "14px" }}>
          {Object.entries(assessment.skill_breakdown).map(([k, v]) => (
            <span key={k} style={{ fontSize: "0.7rem", padding: "2px 8px", borderRadius: 6, background: "rgba(255,255,255,0.05)", color: "#cbd5e1" }}>
              {k}: {typeof v === "number" ? v : JSON.stringify(v)}
            </span>
          ))}
        </div>
      )}

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {(assessment.questions || []).map((q, idx) => {
          const ans = answers[q.question_id];
          return (
            <div key={q.question_id || idx} style={{ background: "rgba(15,23,42,0.7)", padding: "12px 14px", borderRadius: 8, border: "1px solid rgba(255,255,255,0.05)" }}>
              <div style={{ fontSize: "0.72rem", fontWeight: 700, color }}>
                Q{idx + 1}: {q.competency_or_skill}{q.type ? ` (${String(q.type).toUpperCase()})` : ""}
              </div>
              <p style={{ fontSize: "0.8rem", color: "#f8fafc", margin: "4px 0 8px" }}>{q.prompt}</p>
              <pre style={{ whiteSpace: "pre-wrap", fontFamily: q.type === "coding" ? "monospace" : "inherit", fontSize: "0.76rem",
                color: ans ? "#cbd5e1" : "#64748b", background: "rgba(0,0,0,0.25)", padding: "8px 10px", borderRadius: 6, margin: 0 }}>
                {ans || "(no answer submitted)"}
              </pre>
            </div>
          );
        })}
      </div>

      {!!assessment.evidence?.length && (
        <div style={{ marginTop: "14px" }}>
          <div style={{ fontSize: "0.75rem", fontWeight: 700, color: "#94a3b8", marginBottom: 4 }}>Agent evidence</div>
          <ul style={{ paddingLeft: 18, fontSize: "0.75rem", color: "#cbd5e1", margin: 0 }}>
            {assessment.evidence.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}
