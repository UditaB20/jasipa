import React, { useState, useEffect } from "react";
import { Briefcase, Plus, CheckCircle, Scale, Layers, ChevronRight } from "lucide-react";
import { getJobs, getJobRubric, createJob } from "../services/api";

export default function JobDescriptions() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedRubric, setSelectedRubric] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // New Job Form State
  const [formData, setFormData] = useState({
    title: "",
    department: "Engineering",
    description: "",
    required_skills: "Python, SQL, FastAPI, Data Structures",
    preferred_skills: "Docker, AWS, React",
    min_experience: 3.0,
    education_requirement: "Bachelor's in Computer Science or related field"
  });

  useEffect(() => {
    loadJobs();
  }, []);

  async function loadJobs() {
    try {
      const list = await getJobs();
      setJobs(list);
      if (list.length > 0) {
        selectJob(list[0]);
      }
    } catch (err) {
      console.error("Error loading jobs:", err);
    } finally {
      setLoading(false);
    }
  }

  async function selectJob(job) {
    setSelectedJob(job);
    try {
      const rubric = await getJobRubric(job.jd_id);
      setSelectedRubric(rubric);
    } catch (err) {
      console.error("Error loading rubric:", err);
    }
  }

  async function handleCreateJob(e) {
    e.preventDefault();
    try {
      const payload = {
        title: formData.title,
        department: formData.department,
        description: formData.description,
        required_skills: formData.required_skills.split(",").map(s => s.trim()).filter(Boolean),
        preferred_skills: formData.preferred_skills.split(",").map(s => s.trim()).filter(Boolean),
        min_experience: parseFloat(formData.min_experience),
        education_requirement: formData.education_requirement
      };
      const created = await createJob(payload);
      setShowModal(false);
      setJobs([created, ...jobs]);
      selectJob(created);
    } catch (err) {
      alert("Failed to create job: " + err.message);
    }
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Job Descriptions & Anchored Scoring Rubrics
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Every Job Description dynamically anchors a versioned rubric mapping required skills, weights, and competencies.
          </p>
        </div>

        <button
          onClick={() => setShowModal(true)}
          className="btn btn-primary"
          style={{ padding: "10px 18px" }}
        >
          <Plus size={16} />
          <span>Create New Job Description</span>
        </button>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "24px" }}>
        {/* Left: JDs List */}
        <div className="glass-card" style={{ padding: "18px" }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "12px" }}>
            Active Job Requisitions ({jobs.length})
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "8px" }}>
            {jobs.map((job) => {
              const isSelected = selectedJob?.jd_id === job.jd_id;
              return (
                <div
                  key={job.jd_id}
                  onClick={() => selectJob(job)}
                  style={{
                    padding: "12px 14px",
                    borderRadius: "10px",
                    background: isSelected ? "rgba(99, 102, 241, 0.2)" : "rgba(30, 41, 59, 0.4)",
                    border: isSelected ? "1px solid #6366f1" : "1px solid rgba(255, 255, 255, 0.05)",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                    <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
                      {job.title}
                    </h4>
                    <span style={{ fontSize: "0.7rem", color: "#06b6d4", fontWeight: "600" }}>
                      v{job.rubric_version}
                    </span>
                  </div>
                  <p style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "4px" }}>
                    {job.department} • Min {job.min_experience} yrs exp
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Selected JD & Anchored Rubric Inspector */}
        {selectedJob && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* JD Details Card */}
            <div className="glass-card" style={{ padding: "24px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#818cf8", fontWeight: "600", textTransform: "uppercase" }}>
                    {selectedJob.department} Requisition
                  </span>
                  <h3 style={{ fontSize: "1.3rem", fontWeight: "800", color: "#f8fafc", marginTop: "2px" }}>
                    {selectedJob.title}
                  </h3>
                </div>
                <span style={{ padding: "4px 10px", borderRadius: "9999px", background: "rgba(6, 182, 212, 0.15)", color: "#06b6d4", fontSize: "0.75rem", fontWeight: "700", border: "1px solid rgba(6, 182, 212, 0.3)" }}>
                  Rubric v{selectedJob.rubric_version}
                </span>
              </div>

              <p style={{ fontSize: "0.85rem", color: "#cbd5e1", marginTop: "12px", lineHeight: "1.6" }}>
                {selectedJob.description}
              </p>

              {/* Skills Tags */}
              <div style={{ marginTop: "18px", display: "flex", flexDirection: "column", gap: "10px" }}>
                <div>
                  <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Required Core Skills:</span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                    {selectedJob.required_skills?.map((s) => (
                      <span
                        key={s}
                        style={{
                          background: "rgba(99, 102, 241, 0.15)",
                          color: "#818cf8",
                          border: "1px solid rgba(99, 102, 241, 0.3)",
                          padding: "3px 10px",
                          borderRadius: "6px",
                          fontSize: "0.75rem",
                          fontWeight: "600",
                        }}
                      >
                        {s}
                      </span>
                    ))}
                  </div>
                </div>

                {selectedJob.preferred_skills?.length > 0 && (
                  <div>
                    <span style={{ fontSize: "0.75rem", color: "#64748b", fontWeight: "600" }}>Preferred Skills:</span>
                    <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                      {selectedJob.preferred_skills.map((s) => (
                        <span
                          key={s}
                          style={{
                            background: "rgba(255, 255, 255, 0.05)",
                            color: "#94a3b8",
                            border: "1px solid rgba(255, 255, 255, 0.1)",
                            padding: "3px 10px",
                            borderRadius: "6px",
                            fontSize: "0.75rem",
                          }}
                        >
                          {s}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Anchored Rubric Card */}
            {selectedRubric && (
              <div className="glass-card" style={{ padding: "24px" }}>
                <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "16px" }}>
                  <Scale size={20} color="#06b6d4" />
                  <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc" }}>
                    Anchored Evaluation Rubric (Version {selectedRubric.version})
                  </h3>
                </div>

                {/* Rubric Weights Overview */}
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px", marginBottom: "20px" }}>
                  <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(6, 182, 212, 0.1)", border: "1px solid rgba(6, 182, 212, 0.2)" }}>
                    <div style={{ fontSize: "0.75rem", color: "#06b6d4", fontWeight: "600" }}>Resume Fit Weight</div>
                    <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                      {Math.round(selectedRubric.resume_weight * 100)}%
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>Skills, Exp & Pedigree</div>
                  </div>

                  <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                    <div style={{ fontSize: "0.75rem", color: "#818cf8", fontWeight: "600" }}>Technical Test Weight</div>
                    <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                      {Math.round(selectedRubric.skill_weight * 100)}%
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>MCQ, SQL, Coding Tasks</div>
                  </div>

                  <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
                    <div style={{ fontSize: "0.75rem", color: "#c084fc", fontWeight: "600" }}>Behavioral STAR Weight</div>
                    <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                      {Math.round(selectedRubric.culture_weight * 100)}%
                    </div>
                    <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>Standardized Competencies</div>
                  </div>
                </div>

                {/* Criteria Detail Breakdown */}
                <div style={{ background: "rgba(15, 23, 42, 0.8)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                  <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", marginBottom: "8px" }}>
                    Rubric Criteria Breakdown:
                  </h4>
                  <pre style={{ fontSize: "0.75rem", color: "#cbd5e1", overflowX: "auto" }}>
                    {JSON.stringify(selectedRubric.criteria, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        )}
      </div>

      {/* Modal for Creating New Job Description */}
      {showModal && (
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
          <div className="glass-card" style={{ width: "600px", padding: "28px", maxHeight: "90vh", overflowY: "auto" }}>
            <h3 style={{ fontSize: "1.2rem", fontWeight: "800", color: "#f8fafc", marginBottom: "16px" }}>
              Create Job Description & Auto-Generate Rubric
            </h3>

            <form onSubmit={handleCreateJob} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Job Title</label>
                <input
                  className="form-input"
                  required
                  placeholder="e.g. Senior Backend Engineer"
                  value={formData.title}
                  onChange={(e) => setFormData({ ...formData, title: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Department</label>
                <input
                  className="form-input"
                  value={formData.department}
                  onChange={(e) => setFormData({ ...formData, department: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Description</label>
                <textarea
                  className="form-textarea"
                  rows={3}
                  required
                  placeholder="Describe core duties and expectations..."
                  value={formData.description}
                  onChange={(e) => setFormData({ ...formData, description: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Required Skills (comma separated)</label>
                <input
                  className="form-input"
                  required
                  value={formData.required_skills}
                  onChange={(e) => setFormData({ ...formData, required_skills: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Preferred Skills (comma separated)</label>
                <input
                  className="form-input"
                  value={formData.preferred_skills}
                  onChange={(e) => setFormData({ ...formData, preferred_skills: e.target.value })}
                />
              </div>

              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Min Experience (Years)</label>
                  <input
                    type="number"
                    step="0.5"
                    className="form-input"
                    value={formData.min_experience}
                    onChange={(e) => setFormData({ ...formData, min_experience: e.target.value })}
                  />
                </div>
                <div>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Education Requirement</label>
                  <input
                    className="form-input"
                    value={formData.education_requirement}
                    onChange={(e) => setFormData({ ...formData, education_requirement: e.target.value })}
                  />
                </div>
              </div>

              <div style={{ display: "flex", justifyContent: "flex-end", gap: "10px", marginTop: "10px" }}>
                <button
                  type="button"
                  onClick={() => setShowModal(false)}
                  className="btn btn-secondary"
                >
                  Cancel
                </button>
                <button type="submit" className="btn btn-primary">
                  Save & Generate Anchored Rubric
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
}
