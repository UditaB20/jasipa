import React, { useState, useEffect } from "react";
import { 
  Users, Briefcase, UserCheck, AlertTriangle, Play, Upload, ArrowRight,
  TrendingUp, Shield, Activity, Sparkles
} from "lucide-react";
import { getCandidates, getJobs, getPendingReviews, getCohortAnalytics, getRecentAuditLogs } from "../services/api";
import StageBadge from "../components/StageBadge";

export default function Dashboard({ setActivePage, setSelectedCandidateId }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [pendingReviews, setPendingReviews] = useState([]);
  const [biasAnalytics, setBiasAnalytics] = useState(null);
  const [auditLogs, setAuditLogs] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    async function loadData() {
      try {
        const [cands, jbList, reviews, bias, logs] = await Promise.all([
          getCandidates(),
          getJobs(),
          getPendingReviews(),
          getCohortAnalytics(),
          getRecentAuditLogs(10)
        ]);
        setCandidates(cands);
        setJobs(jbList);
        setPendingReviews(reviews);
        setBiasAnalytics(bias);
        setAuditLogs(logs);
      } catch (err) {
        console.error("Error loading dashboard data:", err);
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  const totalCandidates = candidates.length;
  const pendingCount = pendingReviews.length;
  const biasFlaggedCount = candidates.filter(c => c.cohort_tag === "Cohort_Beta" || c.current_stage === "BIAS_CHECKED").length;

  const stageCounts = candidates.reduce((acc, c) => {
    acc[c.current_stage] = (acc[c.current_stage] || 0) + 1;
    return acc;
  }, {});

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Top Banner / Welcome */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          marginBottom: "28px",
          background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(6, 182, 212, 0.08) 100%)",
          padding: "24px 28px",
          borderRadius: "16px",
          border: "1px solid rgba(99, 102, 241, 0.25)",
        }}
      >
        <div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "800", color: "#f8fafc", letterSpacing: "-0.02em" }}>
            Candidate Screening & Interview Panel Agent Hub
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "4px" }}>
            Multi-Agent JD-Anchored Evaluation • PyMuPDF Parsing • STAR Behavioral Scoring • Disparate Impact Governance
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <button
            onClick={() => setActivePage("demo-runner")}
            className="btn btn-primary"
            style={{ padding: "10px 18px", fontSize: "0.85rem" }}
          >
            <Play size={16} />
            <span>Launch Live Demo Walkthrough</span>
          </button>
        </div>
      </div>

      {/* 4 Metric Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "20px", marginBottom: "28px" }}>
        <div className="glass-card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: "600" }}>Total Candidates</span>
            <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(99, 102, 241, 0.15)", color: "#818cf8" }}>
              <Users size={20} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#f8fafc", marginTop: "8px" }}>
            {totalCandidates}
          </div>
          <div style={{ fontSize: "0.72rem", color: "#38bdf8", marginTop: "4px" }}>
            Across {jobs.length} active Job Descriptions
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: "600" }}>Pending Human Reviews</span>
            <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(245, 158, 11, 0.15)", color: "#fbbf24" }}>
              <UserCheck size={20} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#fbbf24", marginTop: "8px" }}>
            {pendingCount}
          </div>
          <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "4px" }}>
            AI prohibited from auto-rejecting
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: "600" }}>Disparity Ratio (4/5ths Rule)</span>
            <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(244, 63, 94, 0.15)", color: "#fb7185" }}>
              <AlertTriangle size={20} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "800", color: biasAnalytics?.disparity_detected ? "#fb7185" : "#34d399", marginTop: "8px" }}>
            {biasAnalytics ? `${Math.round(biasAnalytics.overall_disparity_ratio * 100)}%` : "100%"}
          </div>
          <div style={{ fontSize: "0.72rem", color: biasAnalytics?.disparity_detected ? "#fbbf24" : "#10b981", marginTop: "4px" }}>
            {biasAnalytics?.disparity_detected ? "Cohort Disparity Flagged" : "Within Parity Limits"}
          </div>
        </div>

        <div className="glass-card" style={{ padding: "20px" }}>
          <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between" }}>
            <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: "600" }}>Active Job Rubrics</span>
            <div style={{ padding: "8px", borderRadius: "8px", background: "rgba(6, 182, 212, 0.15)", color: "#22d3ee" }}>
              <Briefcase size={20} />
            </div>
          </div>
          <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#f8fafc", marginTop: "8px" }}>
            {jobs.length}
          </div>
          <div style={{ fontSize: "0.72rem", color: "#22d3ee", marginTop: "4px" }}>
            JD-Anchored Scoring v1.0
          </div>
        </div>
      </div>

      {/* Middle Grid: Pipeline Funnel + Pending Reviews */}
      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px", marginBottom: "28px" }}>
        {/* Candidates List with Stage Breakdown */}
        <div className="glass-card" style={{ padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: "700", color: "#f8fafc" }}>
                Active Candidate Pipeline
              </h3>
              <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                Multi-agent evaluation progress across all stages
              </p>
            </div>
            <button
              onClick={() => setActivePage("candidates")}
              className="btn btn-secondary"
              style={{ padding: "6px 12px", fontSize: "0.75rem" }}
            >
              <span>View All</span>
              <ArrowRight size={14} />
            </button>
          </div>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {candidates.slice(0, 5).map((cand) => (
              <div
                key={cand.candidate_id}
                onClick={() => {
                  setSelectedCandidateId(cand.candidate_id);
                  setActivePage("candidate-detail");
                }}
                style={{
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "space-between",
                  padding: "12px 14px",
                  borderRadius: "10px",
                  background: "rgba(30, 41, 59, 0.5)",
                  border: "1px solid rgba(255, 255, 255, 0.05)",
                  cursor: "pointer",
                  transition: "all 0.2s",
                }}
              >
                <div>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
                      {cand.name}
                    </span>
                    <span style={{ fontSize: "0.7rem", color: "#64748b" }}>
                      ({cand.cohort_tag || "General"})
                    </span>
                  </div>
                  <p style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                    {cand.email} • {cand.experience_years} yrs exp
                  </p>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                  <StageBadge stage={cand.current_stage} />
                  <ArrowRight size={14} color="#64748b" />
                </div>
              </div>
            ))}
          </div>
        </div>

        {/* Pending Human Reviews Queue */}
        <div className="glass-card" style={{ padding: "22px" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <div>
              <h3 style={{ fontSize: "1.05rem", fontWeight: "700", color: "#f8fafc" }}>
                Human Review Queue
              </h3>
              <p style={{ fontSize: "0.75rem", color: "#fbbf24" }}>
                Decision station awaiting authenticated human sign-off
              </p>
            </div>
            <button
              onClick={() => setActivePage("reviews")}
              className="btn btn-primary"
              style={{ padding: "6px 12px", fontSize: "0.75rem", background: "#f59e0b", color: "#000" }}
            >
              <span>Decision Room</span>
              <ArrowRight size={14} />
            </button>
          </div>

          {pendingReviews.length === 0 ? (
            <div style={{ textAlign: "center", padding: "30px", color: "#64748b", fontSize: "0.85rem" }}>
              No candidates currently waiting for human review.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
              {pendingReviews.slice(0, 4).map((p) => (
                <div
                  key={p.candidate_id}
                  onClick={() => {
                    setSelectedCandidateId(p.candidate_id);
                    setActivePage("reviews");
                  }}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "10px",
                    background: "rgba(245, 158, 11, 0.08)",
                    border: "1px solid rgba(245, 158, 11, 0.25)",
                    cursor: "pointer",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
                      {p.name}
                    </span>
                    <span
                      style={{
                        fontSize: "0.72rem",
                        fontWeight: "700",
                        padding: "2px 8px",
                        borderRadius: "9999px",
                        background: "rgba(245, 158, 11, 0.2)",
                        color: "#fbbf24",
                      }}
                    >
                      Score: {p.panel_decision?.merged_score || "N/A"}/100
                    </span>
                  </div>

                  <p style={{ fontSize: "0.72rem", color: "#cbd5e1", marginTop: "4px" }}>
                    Recommendation: <span style={{ color: "#38bdf8", fontWeight: "600" }}>{p.panel_decision?.recommendation || "HUMAN_REVIEW_REQUIRED"}</span>
                  </p>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Bottom Stream: Recent Audit Activity Logs */}
      <div className="glass-card" style={{ padding: "22px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
          <div>
            <h3 style={{ fontSize: "1.05rem", fontWeight: "700", color: "#f8fafc" }}>
              System-Wide Audit Event Stream
            </h3>
            <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
              Immutable real-time audit log of agent invocations, rubric evaluations, and human decisions
            </p>
          </div>
          <button
            onClick={() => setActivePage("audit")}
            className="btn btn-secondary"
            style={{ padding: "6px 12px", fontSize: "0.75rem" }}
          >
            <span>Complete Audit Trail</span>
            <ArrowRight size={14} />
          </button>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
          {auditLogs.slice(0, 5).map((log) => (
            <div
              key={log.log_id}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 14px",
                background: "rgba(15, 23, 42, 0.6)",
                borderRadius: "8px",
                border: "1px solid rgba(255, 255, 255, 0.04)",
                fontSize: "0.78rem",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <span
                  style={{
                    padding: "2px 8px",
                    borderRadius: "6px",
                    background: log.agent.includes("HUMAN") ? "rgba(16, 185, 129, 0.2)" : "rgba(99, 102, 241, 0.2)",
                    color: log.agent.includes("HUMAN") ? "#34d399" : "#818cf8",
                    fontWeight: "600",
                    fontSize: "0.7rem",
                  }}
                >
                  {log.agent}
                </span>
                <span style={{ color: "#f8fafc", fontWeight: "500" }}>{log.event}</span>
              </div>
              <span style={{ color: "#64748b", fontSize: "0.7rem" }}>
                {new Date(log.timestamp).toLocaleTimeString()}
              </span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
