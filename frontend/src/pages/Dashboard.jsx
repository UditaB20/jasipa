import React, { useState, useEffect } from "react";
import { Users, Briefcase, UserCheck, AlertTriangle, ArrowRight, CheckCircle2 } from "lucide-react";
import { getCandidates, getJobs, getPendingReviews, getCohortAnalytics, getRecentAuditLogs } from "../services/api";

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
          getCandidates().catch(() => []),
          getJobs().catch(() => []),
          getPendingReviews().catch(() => []),
          getCohortAnalytics().catch(() => null),
          getRecentAuditLogs(6).catch(() => [])
        ]);

        setCandidates(cands || []);
        setJobs(jbList || []);
        setPendingReviews(reviews || []);
        setBiasAnalytics(bias);
        setAuditLogs(logs || []);
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
  const activeJobsCount = jobs.length;
  // Only real bias-checker output counts; no heuristic fallback.
  const biasFlagsCount = biasAnalytics?.flagged_candidates_count ?? 0;

  // Pipeline stage grouping
  const stageCounts = {
    applied: candidates.filter(c => c.current_stage === "APPLIED").length,
    screening: candidates.filter(c => c.current_stage === "RESUME_SCREENED").length,
    assessment: candidates.filter(c => ["TECHNICAL_ASSESSED", "BEHAVIORAL_ASSESSED"].includes(c.current_stage)).length,
    panel: candidates.filter(c => c.current_stage === "PANEL_EVALUATED").length,
    humanReview: candidates.filter(c => ["HUMAN_REVIEW_PENDING", "BIAS_CHECKED"].includes(c.current_stage)).length,
    completed: candidates.filter(c => c.current_stage === "DECIDED").length,
  };

  const handleReviewCandidate = (candidateId) => {
    if (setSelectedCandidateId) setSelectedCandidateId(candidateId);
    if (setActivePage) setActivePage("reviews");
  };

  if (loading) {
    return (
      <div className="page-container" style={{ textAlign: "center", padding: "80px 0" }}>
        <p style={{ color: "#94a3b8" }}>Loading recruitment dashboard...</p>
      </div>
    );
  }

  return (
    <div className="page-container">
      {/* Page Header */}
      <div className="page-header">
        <div>
          <h2 className="page-title">Recruitment Dashboard</h2>
          <p className="page-subtitle">Overview of candidates, review queues, and hiring progress</p>
        </div>
      </div>

      {/* Part 4: Top 4 Summary Cards */}
      <div style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))",
        gap: "16px",
        marginBottom: "32px"
      }}>
        {/* Card 1: Total Candidates */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.8125rem", color: "#94a3b8", fontWeight: "500" }}>Total Candidates</span>
            <Users size={18} color="#818cf8" />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "#f8fafc" }}>{totalCandidates}</div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>Active applicant pool</div>
        </div>

        {/* Card 2: Pending Human Reviews */}
        <div className="card" style={{ borderColor: pendingCount > 0 ? "rgba(245, 158, 11, 0.4)" : "#334155" }}>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.8125rem", color: "#94a3b8", fontWeight: "500" }}>Pending Reviews</span>
            <UserCheck size={18} color="#fbbf24" />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: "700", color: pendingCount > 0 ? "#fbbf24" : "#f8fafc" }}>
            {pendingCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>Awaiting HR sign-off</div>
        </div>

        {/* Card 3: Active Jobs */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.8125rem", color: "#94a3b8", fontWeight: "500" }}>Active Jobs</span>
            <Briefcase size={18} color="#34d399" />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: "700", color: "#f8fafc" }}>{activeJobsCount}</div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>Open requisitions</div>
        </div>

        {/* Card 4: Bias Flags */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "8px" }}>
            <span style={{ fontSize: "0.8125rem", color: "#94a3b8", fontWeight: "500" }}>Bias Flags</span>
            <AlertTriangle size={18} color="#f87171" />
          </div>
          <div style={{ fontSize: "1.75rem", fontWeight: "700", color: biasFlagsCount > 0 ? "#f87171" : "#f8fafc" }}>
            {biasFlagsCount}
          </div>
          <div style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px" }}>Disparity alerts logged</div>
        </div>
      </div>

      {/* Part 5A: Candidate Pipeline */}
      <div className="card" style={{ marginBottom: "32px" }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginBottom: "16px" }}>
          Candidate Pipeline
        </h3>
        <div style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(140px, 1fr))",
          gap: "12px",
          alignItems: "center"
        }}>
          {[
            { label: "Applied", count: stageCounts.applied },
            { label: "Resume Screening", count: stageCounts.screening },
            { label: "Assessment", count: stageCounts.assessment },
            { label: "Panel", count: stageCounts.panel },
            { label: "Human Review", count: stageCounts.humanReview },
            { label: "Completed", count: stageCounts.completed },
          ].map((stage, idx, arr) => (
            <div
              key={stage.label}
              style={{
                background: "#0f172a",
                border: "1px solid #334155",
                borderRadius: "8px",
                padding: "12px 14px",
                textAlign: "center",
              }}
            >
              <div style={{ fontSize: "1.25rem", fontWeight: "700", color: "#f8fafc" }}>{stage.count}</div>
              <div style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "2px" }}>{stage.label}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Part 5B & 5C: Human Review Queue & Recent Activity */}
      <div style={{ display: "grid", gridTemplateColumns: "2fr 1fr", gap: "24px" }}>
        {/* Section B: Human Review Queue */}
        <div className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc" }}>
              Human Review Queue
            </h3>
            {pendingCount > 0 && (
              <span className="badge badge-warning">{pendingCount} Waiting</span>
            )}
          </div>

          {pendingReviews.length === 0 ? (
            <div style={{ textAlign: "center", padding: "32px 0", color: "#64748b" }}>
              <CheckCircle2 size={32} color="#10b981" style={{ margin: "0 auto 8px" }} />
              <p style={{ fontSize: "0.875rem" }}>All candidate reviews are up to date.</p>
            </div>
          ) : (
            <div className="table-container">
              <table className="data-table">
                <thead>
                  <tr>
                    <th>Candidate</th>
                    <th>Target Job</th>
                    <th>Score</th>
                    <th>Status</th>
                    <th style={{ textAlign: "right" }}>Action</th>
                  </tr>
                </thead>
                <tbody>
                  {pendingReviews.slice(0, 5).map((rev) => {
                    const score = rev.panel_decision?.merged_score;
                    const jobTitle = jobs.find(j => j.jd_id === rev.target_jd_id)?.title || rev.target_jd_id || "Unassigned";
                    return (
                      <tr key={rev.candidate_id}>
                        <td style={{ fontWeight: "600" }}>{rev.name}</td>
                        <td style={{ color: "#94a3b8" }}>{jobTitle}</td>
                        <td>
                          {score != null ? (
                            <span style={{ fontWeight: "600", color: score >= 80 ? "#34d399" : "#fbbf24" }}>
                              {score.toFixed(1)}
                            </span>
                          ) : (
                            <span style={{ color: "#64748b" }}>—</span>
                          )}
                        </td>
                        <td>
                          <span className="badge badge-warning">Review Pending</span>
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            onClick={() => handleReviewCandidate(rev.candidate_id)}
                            className="btn btn-primary"
                            style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                          >
                            <span>Review</span>
                            <ArrowRight size={12} />
                          </button>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </div>

        {/* Section C: Recent Activity */}
        <div className="card">
          <h3 style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginBottom: "16px" }}>
            Recent Activity
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
            {auditLogs.length === 0 ? (
              <p style={{ color: "#64748b", fontSize: "0.85rem" }}>No recent events logged.</p>
            ) : (
              auditLogs.map((log) => {
                const dateStr = log.timestamp ? new Date(log.timestamp).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : "Just now";
                return (
                  <div
                    key={log.log_id}
                    style={{
                      borderLeft: "2px solid #4f46e5",
                      paddingLeft: "10px",
                      fontSize: "0.8125rem",
                    }}
                  >
                    <div style={{ color: "#f8fafc", fontWeight: "500" }}>{log.event}</div>
                    <div style={{ display: "flex", justifyContent: "space-between", color: "#64748b", fontSize: "0.75rem", marginTop: "2px" }}>
                      <span>{log.agent}</span>
                      <span>{dateStr}</span>
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
