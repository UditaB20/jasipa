import React, { useState, useEffect } from "react";
import { UserCheck, ShieldAlert, CheckCircle, XCircle, HelpCircle, FileText, ArrowRight, Award } from "lucide-react";
import confetti from "canvas-confetti";
import { getPendingReviews, getCandidate, submitHumanDecision } from "../services/api";
import ScoreRadar from "../components/ScoreRadar";
import BiasAlertBanner from "../components/BiasAlertBanner";
import AuditTimeline from "../components/AuditTimeline";

export default function HumanReviewPage({ currentRole, selectedCandidateId, setSelectedCandidateId }) {
  const [pendingReviews, setPendingReviews] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [decisionNotes, setDecisionNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [successMessage, setSuccessMessage] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadPending();
  }, []);

  async function loadPending() {
    try {
      const list = await getPendingReviews();
      setPendingReviews(list);
      if (list.length > 0) {
        const targetId = selectedCandidateId || list[0].candidate_id;
        loadCandidateDetails(targetId);
      }
    } catch (err) {
      console.error("Error loading pending reviews:", err);
    } finally {
      setLoading(false);
    }
  }

  async function loadCandidateDetails(id) {
    try {
      const cand = await getCandidate(id);
      setSelectedCandidate(cand);
      setSelectedCandidateId(cand.candidate_id);
    } catch (err) {
      console.error("Error loading candidate:", err);
    }
  }

  async function handleDecision(decisionType) {
    if (!decisionNotes.trim()) {
      alert("Please provide reviewer notes explaining your rationale for this decision.");
      return;
    }

    setSubmitting(true);
    try {
      const res = await submitHumanDecision({
        candidate_id: selectedCandidate.candidate_id,
        reviewer_id: currentRole === "REVIEWER" ? "USR_REV_01" : "USR_REC_01",
        reviewer_name: currentRole === "REVIEWER" ? "Dr. Alex HumanReviewer" : "Sarah Recruiter",
        decision: decisionType,
        notes: decisionNotes
      });

      if (decisionType === "APPROVE") {
        confetti({ particleCount: 100, spread: 70, origin: { y: 0.6 } });
      }

      setSuccessMessage(`Decision "${decisionType}" recorded successfully by ${res.reviewer_name}!`);
      setDecisionNotes("");
      await loadPending();
    } catch (err) {
      alert("Decision submission failed: " + err.message);
    } finally {
      setSubmitting(false);
    }
  }

  const latestPanel = selectedCandidate?.panel_decisions?.[selectedCandidate.panel_decisions.length - 1];
  const latestBias = selectedCandidate?.bias_checks?.[selectedCandidate.bias_checks.length - 1];
  const latestScreening = selectedCandidate?.screening_results?.[selectedCandidate.screening_results.length - 1];
  const techAssessment = selectedCandidate?.assessments?.find(a => a.test_type === "TECHNICAL");
  const behAssessment = selectedCandidate?.assessments?.find(a => a.test_type === "BEHAVIORAL");

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Human Review Decision Room
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#fbbf24" }}>
            Mandatory Human-in-the-Loop Governance: The AI system NEVER makes final hiring decisions autonomously.
          </p>
        </div>

        <div style={{ padding: "6px 14px", borderRadius: "8px", background: "rgba(245, 158, 11, 0.15)", border: "1px solid rgba(245, 158, 11, 0.4)", color: "#fbbf24", fontSize: "0.78rem", fontWeight: "700" }}>
          Active Human Reviewer: {currentRole === "REVIEWER" ? "Dr. Alex (Reviewer)" : "Sarah (HR Admin)"}
        </div>
      </div>

      {successMessage && (
        <div style={{ padding: "14px 18px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.2)", border: "1px solid #10b981", color: "#34d399", marginBottom: "20px", fontSize: "0.85rem", fontWeight: "600" }}>
          ✓ {successMessage}
        </div>
      )}

      <div style={{ display: "grid", gridTemplateColumns: "320px 1fr", gap: "24px" }}>
        {/* Left: Pending Review Queue */}
        <div className="glass-card" style={{ padding: "18px" }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "12px" }}>
            Pending Review Queue ({pendingReviews.length})
          </h3>

          {pendingReviews.length === 0 ? (
            <div style={{ padding: "20px", textAlign: "center", color: "#64748b", fontSize: "0.82rem" }}>
              Queue is clear! All candidates have received human decisions.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
              {pendingReviews.map((p) => {
                const isSelected = selectedCandidate?.candidate_id === p.candidate_id;
                return (
                  <div
                    key={p.candidate_id}
                    onClick={() => loadCandidateDetails(p.candidate_id)}
                    style={{
                      padding: "12px 14px",
                      borderRadius: "10px",
                      background: isSelected ? "rgba(245, 158, 11, 0.2)" : "rgba(30, 41, 59, 0.4)",
                      border: isSelected ? "1px solid #f59e0b" : "1px solid rgba(255, 255, 255, 0.05)",
                      cursor: "pointer",
                      transition: "all 0.2s",
                    }}
                  >
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                      <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
                        {p.name}
                      </h4>
                      <span style={{ fontSize: "0.7rem", color: "#fbbf24", fontWeight: "700" }}>
                        {p.panel_decision?.merged_score || "N/A"}/100
                      </span>
                    </div>
                    <p style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "2px" }}>
                      Cohort: {p.cohort_tag || "General"}
                    </p>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {/* Right: Comprehensive Evidence Dossier & Sign-Off Station */}
        {selectedCandidate ? (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Candidate Header */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h3 style={{ fontSize: "1.2rem", fontWeight: "800", color: "#f8fafc" }}>
                    {selectedCandidate.name}
                  </h3>
                  <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    {selectedCandidate.email} • {selectedCandidate.experience_years} yrs experience • Cohort: {selectedCandidate.cohort_tag}
                  </p>
                </div>
                <div style={{ textAlign: "right" }}>
                  <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Panel Recommendation:</div>
                  <span style={{ fontSize: "0.85rem", fontWeight: "800", color: "#38bdf8" }}>
                    {latestPanel?.recommendation || "PENDING"}
                  </span>
                </div>
              </div>
            </div>

            {/* Bias Alert Banner */}
            <BiasAlertBanner biasCheck={latestBias} />

            <div className="glass-card" style={{ padding: "16px 20px" }}>
              <h4 style={{ color: "#f8fafc", marginBottom: "8px" }}>Decision context</h4>
              <p style={{ color: "#cbd5e1", fontSize: "0.82rem", margin: "4px 0" }}>
                Agent score agreement: <strong>{pendingReviews.find(p => p.candidate_id === selectedCandidate.candidate_id)?.confidence?.label || "UNAVAILABLE"}</strong>
                {pendingReviews.find(p => p.candidate_id === selectedCandidate.candidate_id)?.confidence?.agreement_score != null && ` (${Math.round(pendingReviews.find(p => p.candidate_id === selectedCandidate.candidate_id).confidence.agreement_score * 100)}%)`}
                <span style={{ color: "#94a3b8" }}> · agreement heuristic, not a probability of job success</span>
              </p>
              {(() => {
                const history = pendingReviews.find(p => p.candidate_id === selectedCandidate.candidate_id)?.historical_context;
                return <p style={{ color: "#cbd5e1", fontSize: "0.82rem", margin: "4px 0" }}>
                  Similar prior hires: <strong>{history?.similar_hires ?? 0}</strong>
                  {history?.success_rate != null ? ` · ${Math.round(history.success_rate * 100)}% recorded successful outcomes` : " · insufficient outcome history for a rate"}
                  <span style={{ color: "#94a3b8" }}> · same role and scores within 5 points</span>
                </p>;
              })()}
            </div>

            {latestPanel?.natural_language_summary && <div className="glass-card" style={{ padding: "16px 20px" }}>
              <h4 style={{ color: "#f8fafc", marginBottom: 8 }}>Panel summary</h4>
              <p style={{ color: "#cbd5e1", fontSize: "0.85rem", lineHeight: 1.6 }}>{latestPanel.natural_language_summary}</p>
              <p style={{ color: "#94a3b8", fontSize: "0.72rem", marginTop: 8 }}>Explanation: {latestPanel.synthesis_strategy || "template"}{latestPanel.synthesis_latency_ms != null ? ` · ${latestPanel.synthesis_latency_ms} ms` : ""}. Recommendation routing is determined by the scored evidence; a human makes the final decision.</p>
              {!!latestPanel.decision_factors?.length && <ul style={{ color: "#cbd5e1", fontSize: "0.78rem", paddingLeft: 18, marginBottom: 0 }}>{latestPanel.decision_factors.map((factor, i) => <li key={i}>{factor}</li>)}</ul>}
            </div>}

            {/* Multi-Agent Score Synthesis */}
            <ScoreRadar
              resumeScore={latestScreening?.score || 0}
              skillScore={techAssessment?.score || 0}
              cultureScore={behAssessment?.score || 0}
              mergedScore={latestPanel?.merged_score || 0}
            />

            {/* Complete Evidence Docket */}
            <div className="glass-card" style={{ padding: "20px" }}>
              <h4 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "12px" }}>
                Complete Multi-Agent Evidence Docket
              </h4>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
                <div style={{ background: "rgba(15, 23, 42, 0.7)", padding: "14px", borderRadius: "10px" }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: "700", color: "#34d399", marginBottom: "6px" }}>
                    Demonstrated Strengths:
                  </div>
                  <ul style={{ paddingLeft: "16px", fontSize: "0.75rem", color: "#cbd5e1" }}>
                    {latestPanel?.strengths?.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>

                <div style={{ background: "rgba(15, 23, 42, 0.7)", padding: "14px", borderRadius: "10px" }}>
                  <div style={{ fontSize: "0.78rem", fontWeight: "700", color: "#fb7185", marginBottom: "6px" }}>
                    Identified Gaps:
                  </div>
                  <ul style={{ paddingLeft: "16px", fontSize: "0.75rem", color: "#cbd5e1" }}>
                    {latestPanel?.gaps?.map((g, idx) => (
                      <li key={idx}>{g}</li>
                    ))}
                  </ul>
                </div>
              </div>
            </div>

            {/* Human Decision Sign-Off Card */}
            <div
              className="glass-card"
              style={{
                padding: "24px",
                background: "linear-gradient(135deg, rgba(30, 41, 59, 0.9) 0%, rgba(15, 23, 42, 0.95) 100%)",
                border: "1px solid rgba(245, 158, 11, 0.4)",
              }}
            >
              <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: "#fbbf24", marginBottom: "10px" }}>
                Human Reviewer Decision & Signature
              </h3>
              <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: "14px" }}>
                Provide detailed notes explaining the hiring decision. This decision is permanently logged into the immutable audit record.
              </p>

              <div style={{ marginBottom: "16px" }}>
                <label style={{ fontSize: "0.75rem", color: "#cbd5e1", fontWeight: "600" }}>
                  Reviewer Notes & Decision Rationale:
                </label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  required
                  placeholder="e.g. Candidate demonstrated strong problem solving fundamentals and passed technical benchmark. Approved for engineering offer."
                  value={decisionNotes}
                  onChange={(e) => setDecisionNotes(e.target.value)}
                />
              </div>

              {/* 3 Decision Buttons */}
              <div style={{ display: "flex", gap: "12px", justifyContent: "flex-end" }}>
                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision("REQUEST_MORE_INFORMATION")}
                  className="btn btn-warning"
                  style={{ padding: "10px 18px" }}
                >
                  <HelpCircle size={16} />
                  <span>Request More Information</span>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision("REJECT")}
                  className="btn btn-danger"
                  style={{ padding: "10px 18px" }}
                >
                  <XCircle size={16} />
                  <span>Reject Candidate</span>
                </button>

                <button
                  type="button"
                  disabled={submitting}
                  onClick={() => handleDecision("APPROVE")}
                  className="btn btn-success"
                  style={{ padding: "10px 22px" }}
                >
                  <CheckCircle size={16} />
                  <span>Approve Candidate for Hire</span>
                </button>
              </div>
            </div>
          </div>
        ) : (
          <div style={{ padding: "40px", textAlign: "center", color: "#64748b" }}>
            Select a candidate from the queue to review evidence.
          </div>
        )}
      </div>
    </div>
  );
}
