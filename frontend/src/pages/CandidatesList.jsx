import React, { useState, useEffect } from "react";
import { Users, Upload, Search, Filter, Play, ArrowRight, FileText, CheckCircle2 } from "lucide-react";
import { getCandidates, getJobs, uploadResume, createCandidate } from "../services/api";
import StageBadge from "../components/StageBadge";

export default function CandidatesList({ setActivePage, setSelectedCandidateId }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [searchQuery, setSearchQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("");
  const [jdFilter, setJdFilter] = useState("");
  const [showUploadModal, setShowUploadModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // Resume Upload Form State
  const [uploadData, setUploadData] = useState({
    name: "",
    email: "",
    phone: "",
    cohort_tag: "Cohort_Alpha",
    target_jd_id: "",
    file: null,
  });
  const [uploading, setUploading] = useState(false);

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
      if (jbList.length > 0 && !uploadData.target_jd_id) {
        setUploadData(prev => ({ ...prev, target_jd_id: jbList[0].jd_id }));
      }
    } catch (err) {
      console.error("Error loading candidate list:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleUploadResume(e) {
    e.preventDefault();
    if (!uploadData.file) {
      alert("Please select a PDF resume file.");
      return;
    }
    setUploading(true);
    try {
      const formData = new FormData();
      formData.append("name", uploadData.name);
      formData.append("email", uploadData.email);
      formData.append("phone", uploadData.phone || "");
      formData.append("cohort_tag", uploadData.cohort_tag || "General Cohort");
      formData.append("target_jd_id", uploadData.target_jd_id);
      formData.append("file", uploadData.file);

      const res = await uploadResume(formData);
      setShowUploadModal(false);
      await loadData();
      setSelectedCandidateId(res.candidate_id);
      setActivePage("candidate-detail");
    } catch (err) {
      alert("Upload error: " + err.message);
    } finally {
      setUploading(false);
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
            Manage candidate profiles, view multi-agent evaluation statuses, and upload PDF resumes for automated parsing.
          </p>
        </div>

        <button
          onClick={() => setShowUploadModal(true)}
          className="btn btn-primary"
          style={{ padding: "10px 18px" }}
        >
          <Upload size={16} />
          <span>Upload PDF Resume</span>
        </button>
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

      {/* PDF Resume Upload Modal */}
      {showUploadModal && (
        <div
          style={{
            position: "fixed",
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(6px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 100,
          }}
        >
          <div className="glass-card" style={{ width: "560px", padding: "28px" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "800", color: "#f8fafc", marginBottom: "14px" }}>
              Upload Candidate Resume (PyMuPDF Parser)
            </h3>
            <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: "18px" }}>
              The backend will extract plain text, calculate extraction confidence, and extract preliminary metadata.
            </p>

            <form onSubmit={handleUploadResume} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Candidate Name</label>
                <input
                  className="form-input"
                  required
                  placeholder="e.g. Maya Lin"
                  value={uploadData.name}
                  onChange={(e) => setUploadData({ ...uploadData, name: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  required
                  placeholder="maya.lin@example.com"
                  value={uploadData.email}
                  onChange={(e) => setUploadData({ ...uploadData, email: e.target.value })}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Cohort Tag</label>
                  <select
                    className="form-select"
                    value={uploadData.cohort_tag}
                    onChange={(e) => setUploadData({ ...uploadData, cohort_tag: e.target.value })}
                  >
                    <option value="Cohort_Alpha">Cohort_Alpha</option>
                    <option value="Cohort_Beta">Cohort_Beta</option>
                    <option value="Cohort_Gamma">Cohort_Gamma</option>
                    <option value="General Cohort">General Cohort</option>
                  </select>
                </div>

                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Target Job Description</label>
                  <select
                    className="form-select"
                    value={uploadData.target_jd_id}
                    onChange={(e) => setUploadData({ ...uploadData, target_jd_id: e.target.value })}
                  >
                    {jobs.map(j => (
                      <option key={j.jd_id} value={j.jd_id}>{j.title}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Select PDF Resume File</label>
                <input
                  type="file"
                  accept=".pdf"
                  required
                  className="form-input"
                  style={{ padding: "8px" }}
                  onChange={(e) => setUploadData({ ...uploadData, file: e.target.files[0] })}
                />
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowUploadModal(false)}
                  className="btn btn-secondary"
                  disabled={uploading}
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary" disabled={uploading}>
                  {uploading ? "Extracting & Ingesting..." : "Parse & Ingest Resume"}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
