import React, { useState, useEffect } from "react";
import { Search, ArrowRight } from "lucide-react";
import { getCandidates, getJobs } from "../services/api";
import StageBadge from "../components/StageBadge";

// Resumes enter the system via the Candidate Portal (candidate applies) or scripts/import_dataset.py.
// HR intentionally has no upload path here.
export default function CandidatesList({ setActivePage, setSelectedCandidateId }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [jdFilter, setJdFilter] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadData();
  }, [stageFilter, jdFilter]);

  async function loadData() {
    try {
      const [cands, jbList] = await Promise.all([
        getCandidates(stageFilter, jdFilter),
        getJobs(),
      ]);
      setCandidates(cands);
      setJobs(jbList);
    } catch (err) {
      console.error("Error loading candidate list:", err);
    } finally {
      setLoading(false);
    }
  }

  const filteredCandidates = candidates.filter((c) => {
    const matchesSearch =
      c.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      c.email.toLowerCase().includes(searchQuery.toLowerCase()) ||
      (c.skills_extracted || []).some(s => s.toLowerCase().includes(searchQuery.toLowerCase()));
    return matchesSearch;
  });

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Candidate Pipeline & Dossiers
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Manage candidate profiles and view multi-agent evaluation statuses. Candidates apply via the Candidate Portal.
          </p>
        </div>
      </div>

      {/* Filter and Search Bar */}
      <div
        className="glass-card"
        style={{
          padding: "16px 20px",
          marginBottom: "20px",
          display: "flex",
          alignItems: "center",
          gap: "16px",
          flexWrap: "wrap",
        }}
      >
        <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
          <Search size={16} color="#94a3b8" style={{ position: "absolute", left: "12px", top: "12px" }} />
          <input
            className="form-input"
            style={{ paddingLeft: "36px" }}
            placeholder="Search by candidate name, email, or skill..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ width: "200px" }}>
          <select
            className="form-select"
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
          >
            <option value="">All Pipeline Stages</option>
            <option value="APPLIED">Applied</option>
            <option value="RESUME_SCREENED">Resume Screened</option>
            <option value="TECHNICAL_ASSESSED">Technical Assessed</option>
            <option value="BEHAVIORAL_ASSESSED">Behavioral Assessed</option>
            <option value="PANEL_EVALUATED">Panel Evaluated</option>
            <option value="HUMAN_REVIEW_PENDING">Human Review Pending</option>
            <option value="DECIDED">Decided</option>
          </select>
        </div>

        <div style={{ width: "220px" }}>
          <select
            className="form-select"
            value={jdFilter}
            onChange={(e) => setJdFilter(e.target.value)}
          >
            <option value="">All Job Descriptions</option>
            {jobs.map(j => (
              <option key={j.jd_id} value={j.jd_id}>{j.title}</option>
            ))}
          </select>
        </div>
      </div>

      {/* Candidates Table */}
      <div className="glass-card" style={{ overflow: "hidden" }}>
        <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.85rem" }}>
          <thead>
            <tr style={{ background: "rgba(15, 23, 42, 0.9)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", color: "#94a3b8" }}>
              <th style={{ padding: "14px 20px" }}>Candidate</th>
              <th style={{ padding: "14px 20px" }}>Cohort Tag</th>
              <th style={{ padding: "14px 20px" }}>Experience</th>
              <th style={{ padding: "14px 20px" }}>Target Role</th>
              <th style={{ padding: "14px 20px" }}>Pipeline Stage</th>
              <th style={{ padding: "14px 20px", textAlign: "right" }}>Action</th>
            </tr>
          </thead>
          <tbody>
            {filteredCandidates.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ padding: "30px", textAlign: "center", color: "#64748b" }}>
                  No candidates found matching the criteria.
                </td>
              </tr>
            ) : (
              filteredCandidates.map((c) => {
                const targetJob = jobs.find(j => j.jd_id === c.target_jd_id);
                return (
                  <tr
                    key={c.candidate_id}
                    style={{
                      borderBottom: "1px solid rgba(255, 255, 255, 0.04)",
                      transition: "background 0.2s",
                    }}
                    onMouseEnter={(e) => e.currentTarget.style.background = "rgba(30, 41, 59, 0.4)"}
                    onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                  >
                    <td style={{ padding: "14px 20px" }}>
                      <div style={{ fontWeight: "700", color: "#f8fafc" }}>{c.name}</div>
                      <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{c.email}</div>
                    </td>
                    <td style={{ padding: "14px 20px" }}>
                      <span style={{ fontSize: "0.75rem", padding: "2px 8px", borderRadius: "6px", background: "rgba(255, 255, 255, 0.05)", color: "#cbd5e1" }}>
                        {c.cohort_tag || "General Cohort"}
                      </span>
                    </td>
                    <td style={{ padding: "14px 20px", color: "#cbd5e1" }}>
                      {c.experience_years} yrs
                    </td>
                    <td style={{ padding: "14px 20px", color: "#38bdf8", fontWeight: "500" }}>
                      {targetJob?.title || c.target_jd_id || "Unassigned"}
                    </td>
                    <td style={{ padding: "14px 20px" }}>
                      <StageBadge stage={c.current_stage} />
                    </td>
                    <td style={{ padding: "14px 20px", textAlign: "right" }}>
                      <button
                        onClick={() => {
                          setSelectedCandidateId(c.candidate_id);
                          setActivePage("candidate-detail");
                        }}
                        className="btn btn-secondary"
                        style={{ padding: "6px 12px", fontSize: "0.75rem" }}
                      >
                        <span>View Dossier</span>
                        <ArrowRight size={13} />
                      </button>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
