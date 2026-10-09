import React, { useState, useEffect } from "react";
import { 
  Briefcase, Plus, CheckCircle, Scale, Layers, ChevronRight,
  Edit3, Save, X, RotateCcw, AlertTriangle, Code, Sliders, Check, Sparkles, Trash2
} from "lucide-react";
import { getJobs, getJobRubric, createJob, updateJobRubric } from "../services/api";

export default function JobDescriptions() {
  const [jobs, setJobs] = useState([]);
  const [selectedJob, setSelectedJob] = useState(null);
  const [selectedRubric, setSelectedRubric] = useState(null);
  const [showModal, setShowModal] = useState(false);
  const [loading, setLoading] = useState(true);

  // Rubric Editing State
  const [isEditingRubric, setIsEditingRubric] = useState(false);
  const [rubricEditForm, setRubricEditForm] = useState(null);
  const [rubricEditMode, setRubricEditMode] = useState("guided"); // "guided" or "json"
  const [jsonError, setJsonError] = useState(null);
  const [savingRubric, setSavingRubric] = useState(false);
  const [rubricSuccessMsg, setRubricSuccessMsg] = useState(null);

  // New Job Form State
  const [formData, setFormData] = useState({
    title: "",
    department: "Engineering",
    description: "",
    required_skills: "Python, SQL, FastAPI, Data Structures",
    preferred_skills: "Docker, AWS, React",
    min_experience: 3,
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
    setIsEditingRubric(false);
    setRubricSuccessMsg(null);
    try {
      const rubric = await getJobRubric(job.jd_id);
      setSelectedRubric(rubric);
    } catch (err) {
      console.error("Error loading rubric:", err);
    }
  }

  function startEditingRubric() {
    if (!selectedRubric) return;
    const crit = selectedRubric.criteria || {};
    setRubricEditForm({
      resume_weight: Math.round((selectedRubric.resume_weight ?? 0.4) * 100),
      skill_weight: Math.round((selectedRubric.skill_weight ?? 0.4) * 100),
      culture_weight: Math.round((selectedRubric.culture_weight ?? 0.2) * 100),
      passing_threshold: crit.technical_scoring?.passing_threshold || 70,
      mcq_weight: crit.technical_scoring?.mcq_weight || 30,
      coding_weight: crit.technical_scoring?.coding_weight || 40,
      short_answer_weight: crit.technical_scoring?.short_answer_weight || 30,
      required_skills_weight: crit.resume_scoring?.required_skills_weight || 50,
      preferred_skills_weight: crit.resume_scoring?.preferred_skills_weight || 15,
      experience_weight: crit.resume_scoring?.experience_weight || 20,
      education_weight: crit.resume_scoring?.education_and_projects_weight || 15,
      competencies: JSON.parse(JSON.stringify(crit.behavioral_scoring?.competencies || [])),
      raw_json: JSON.stringify(crit, null, 2)
    });
    setJsonError(null);
    setRubricSuccessMsg(null);
    setIsEditingRubric(true);
  }

  function handleAddCompetency() {
    setRubricEditForm(prev => {
      const currentSum = prev.competencies.reduce((sum, c) => sum + (Number(c.max_points) || 0), 0);
      const remaining = Math.max(0, 100 - currentSum);
      return {
        ...prev,
        competencies: [
          ...prev.competencies,
          { 
            competency: "New Competency", 
            description: "Assessment criteria description", 
            max_points: remaining > 0 ? remaining : 10 
          }
        ]
      };
    });
  }

  function handleAutoBalanceCompetencies() {
    setRubricEditForm(prev => {
      const n = prev.competencies.length;
      if (n === 0) return prev;
      const basePoints = Math.floor(100 / n);
      const remainder = 100 - (basePoints * n);
      const updated = prev.competencies.map((c, i) => ({
        ...c,
        max_points: i < remainder ? basePoints + 1 : basePoints
      }));
      return { ...prev, competencies: updated };
    });
  }

  function handleRemoveCompetency(idx) {
    setRubricEditForm(prev => ({
      ...prev,
      competencies: prev.competencies.filter((_, i) => i !== idx)
    }));
  }

  function handleCompetencyChange(idx, field, value) {
    setRubricEditForm(prev => {
      const nextComp = [...prev.competencies];
      let formattedVal = value;
      if (field === "max_points") {
        formattedVal = value === "" ? "" : Math.max(1, Math.min(100, parseInt(value, 10) || 0));
      }
      nextComp[idx] = { ...nextComp[idx], [field]: formattedVal };
      return { ...prev, competencies: nextComp };
    });
  }

  async function handleSaveRubric() {
    if (!selectedJob || !selectedRubric || !rubricEditForm) return;
    setSavingRubric(true);
    setJsonError(null);

    try {
      let finalCriteria;
      let r_w = rubricEditForm.resume_weight / 100;
      let s_w = rubricEditForm.skill_weight / 100;
      let c_w = rubricEditForm.culture_weight / 100;

      if (rubricEditMode === "json") {
        try {
          finalCriteria = JSON.parse(rubricEditForm.raw_json);
        } catch (err) {
          setJsonError("Invalid JSON syntax: " + err.message);
          setSavingRubric(false);
          return;
        }
        if (finalCriteria.weights) {
          r_w = finalCriteria.weights.resume_fit ?? r_w;
          s_w = finalCriteria.weights.technical_skill ?? s_w;
          c_w = finalCriteria.weights.behavioral_fit ?? c_w;
        }
      } else {
        const domainTotal = Number(rubricEditForm.resume_weight) + Number(rubricEditForm.skill_weight) + Number(rubricEditForm.culture_weight);
        if (domainTotal !== 100) {
          alert(`Overall stage weights must sum to exactly 100%. Current sum: ${domainTotal}%`);
          setSavingRubric(false);
          return;
        }

        const threshold = Number(rubricEditForm.passing_threshold);
        if (isNaN(threshold) || threshold < 0 || threshold > 100) {
          alert(`Technical passing threshold must be between 0% and 100%. Current value: ${threshold}%`);
          setSavingRubric(false);
          return;
        }

        const techSubTotal = Number(rubricEditForm.mcq_weight) + Number(rubricEditForm.coding_weight) + Number(rubricEditForm.short_answer_weight);
        if (techSubTotal !== 100) {
          alert(`Technical task sub-weights (MCQ + Coding + Short Answer) must sum to exactly 100%. Current sum: ${techSubTotal}%`);
          setSavingRubric(false);
          return;
        }

        const compTotal = rubricEditForm.competencies.reduce((sum, c) => sum + (Number(c.max_points) || 0), 0);
        if (compTotal !== 100) {
          alert(`Behavioral competencies must sum to exactly 100 points. Current sum: ${compTotal} points across ${rubricEditForm.competencies.length} competencies. Adjust the points or click 'Auto-Balance Evenly'.`);
          setSavingRubric(false);
          return;
        }

        const baseCrit = JSON.parse(JSON.stringify(selectedRubric.criteria || {}));
        baseCrit.weights = {
          resume_fit: r_w,
          technical_skill: s_w,
          behavioral_fit: c_w
        };
        baseCrit.resume_scoring = {
          ...(baseCrit.resume_scoring || {}),
          required_skills_weight: Number(rubricEditForm.required_skills_weight),
          preferred_skills_weight: Number(rubricEditForm.preferred_skills_weight),
          experience_weight: Number(rubricEditForm.experience_weight),
          education_and_projects_weight: Number(rubricEditForm.education_weight)
        };
        baseCrit.technical_scoring = {
          ...(baseCrit.technical_scoring || {}),
          passing_threshold: Number(rubricEditForm.passing_threshold),
          mcq_weight: Number(rubricEditForm.mcq_weight),
          coding_weight: Number(rubricEditForm.coding_weight),
          short_answer_weight: Number(rubricEditForm.short_answer_weight)
        };
        baseCrit.behavioral_scoring = {
          ...(baseCrit.behavioral_scoring || {}),
          competencies: rubricEditForm.competencies,
          total_points: compTotal
        };
        finalCriteria = baseCrit;
      }


      const updated = await updateJobRubric(selectedJob.jd_id, {
        resume_weight: r_w,
        skill_weight: s_w,
        culture_weight: c_w,
        criteria: finalCriteria
      });

      setSelectedRubric(updated);
      setIsEditingRubric(false);
      setRubricSuccessMsg(`Scoring rubric updated successfully (Version ${updated.version})!`);
      setTimeout(() => setRubricSuccessMsg(null), 6000);
    } catch (err) {
      alert("Failed to save rubric: " + err.message);
    } finally {
      setSavingRubric(false);
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
        min_experience: Math.max(0, parseInt(formData.min_experience, 10) || 0),
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
                    {job.department} • Min {Math.max(0, Math.round(job.min_experience || 0))} yrs exp
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
                <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                  <span style={{ padding: "4px 10px", borderRadius: "9999px", background: "rgba(99, 102, 241, 0.15)", color: "#818cf8", fontSize: "0.75rem", fontWeight: "700", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
                    {Math.max(0, Math.round(selectedJob.min_experience || 0))} Yrs Exp Required
                  </span>
                  <span style={{ padding: "4px 10px", borderRadius: "9999px", background: "rgba(6, 182, 212, 0.15)", color: "#06b6d4", fontSize: "0.75rem", fontWeight: "700", border: "1px solid rgba(6, 182, 212, 0.3)" }}>
                    Rubric v{selectedJob.rubric_version}
                  </span>
                </div>
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

            {/* Rubric Success Banner */}
            {rubricSuccessMsg && (
              <div style={{ padding: "12px 18px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.2)", border: "1px solid #10b981", color: "#34d399", fontSize: "0.85rem", fontWeight: "600", display: "flex", alignItems: "center", gap: "8px" }}>
                <CheckCircle size={16} />
                <span>{rubricSuccessMsg}</span>
              </div>
            )}

            {/* Anchored Rubric Card */}
            {selectedRubric && (
              <div className="glass-card" style={{ padding: "24px" }}>
                {/* Header */}
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px", flexWrap: "wrap", gap: "10px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                    <Scale size={20} color="#06b6d4" />
                    <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc" }}>
                      Anchored Evaluation Rubric (Version {selectedRubric.version})
                    </h3>
                  </div>

                  {!isEditingRubric ? (
                    <button
                      onClick={startEditingRubric}
                      className="btn btn-primary"
                      style={{ padding: "7px 14px", fontSize: "0.78rem" }}
                    >
                      <Edit3 size={14} />
                      <span>Customize Rubric</span>
                    </button>
                  ) : (
                    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}>
                      <div style={{ display: "flex", background: "rgba(15, 23, 42, 0.7)", borderRadius: "6px", padding: "2px", border: "1px solid rgba(255, 255, 255, 0.1)" }}>
                        <button
                          type="button"
                          onClick={() => setRubricEditMode("guided")}
                          style={{
                            background: rubricEditMode === "guided" ? "#6366f1" : "transparent",
                            color: "#f8fafc",
                            border: "none",
                            borderRadius: "4px",
                            padding: "4px 10px",
                            fontSize: "0.72rem",
                            cursor: "pointer",
                            fontWeight: "600"
                          }}
                        >
                          Guided Form
                        </button>
                        <button
                          type="button"
                          onClick={() => setRubricEditMode("json")}
                          style={{
                            background: rubricEditMode === "json" ? "#6366f1" : "transparent",
                            color: "#f8fafc",
                            border: "none",
                            borderRadius: "4px",
                            padding: "4px 10px",
                            fontSize: "0.72rem",
                            cursor: "pointer",
                            fontWeight: "600"
                          }}
                        >
                          Raw JSON
                        </button>
                      </div>
                      <button
                        onClick={() => setIsEditingRubric(false)}
                        className="btn btn-secondary"
                        style={{ padding: "6px 10px", fontSize: "0.75rem" }}
                      >
                        <X size={14} />
                        <span>Cancel</span>
                      </button>
                    </div>
                  )}
                </div>

                {/* EDIT MODE */}
                {isEditingRubric && rubricEditForm ? (
                  <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
                    {/* Weight Sum Validation Alert */}
                    {(() => {
                      const total = (Number(rubricEditForm.resume_weight) || 0) + (Number(rubricEditForm.skill_weight) || 0) + (Number(rubricEditForm.culture_weight) || 0);
                      const isValid = total === 100;
                      return (
                        <div style={{
                          display: "flex",
                          justifyContent: "space-between",
                          alignItems: "center",
                          padding: "10px 14px",
                          borderRadius: "8px",
                          background: isValid ? "rgba(16, 185, 129, 0.12)" : "rgba(239, 68, 68, 0.12)",
                          border: isValid ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.4)",
                          fontSize: "0.8rem",
                          color: isValid ? "#34d399" : "#f87171"
                        }}>
                          <span>
                            {isValid 
                              ? "✓ Weights sum to 100% (Balanced distribution)." 
                              : `⚠ Total weight is ${total}%. Must equal exactly 100% to save.`}
                          </span>
                          <span style={{ fontWeight: "700" }}>Total: {total}%</span>
                        </div>
                      );
                    })()}

                    {rubricEditMode === "guided" ? (
                      (() => {
                        const domainTotal = (Number(rubricEditForm.resume_weight) || 0) + (Number(rubricEditForm.skill_weight) || 0) + (Number(rubricEditForm.culture_weight) || 0);
                        const techSubTotal = (Number(rubricEditForm.mcq_weight) || 0) + (Number(rubricEditForm.coding_weight) || 0) + (Number(rubricEditForm.short_answer_weight) || 0);
                        const compTotal = rubricEditForm.competencies.reduce((sum, c) => sum + (Number(c.max_points) || 0), 0);
                        const isDomainValid = domainTotal === 100;
                        const isThresholdValid = Number(rubricEditForm.passing_threshold) >= 0 && Number(rubricEditForm.passing_threshold) <= 100 && rubricEditForm.passing_threshold !== "";
                        const isTechSubValid = techSubTotal === 100;
                        const isCompValid = compTotal === 100;

                        return (
                          <>
                            {/* 1. Stage Weight Distribution */}
                            <div>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                                <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", margin: 0 }}>
                                  1. Overall Domain Weights
                                </h4>
                                <span style={{ fontSize: "0.75rem", fontWeight: "600", color: isDomainValid ? "#34d399" : "#f87171" }}>
                                  {isDomainValid ? "✓ Total: 100%" : `⚠ Total: ${domainTotal}% (Must = 100%)`}
                                </span>
                              </div>
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px" }}>
                                <div style={{ padding: "12px", borderRadius: "10px", background: "rgba(6, 182, 212, 0.08)", border: "1px solid rgba(6, 182, 212, 0.2)" }}>
                                  <label style={{ fontSize: "0.75rem", color: "#06b6d4", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                    Resume Fit Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.resume_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, resume_weight: val });
                                    }}
                                  />
                                </div>

                                <div style={{ padding: "12px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.08)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                                  <label style={{ fontSize: "0.75rem", color: "#818cf8", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                    Technical Test Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.skill_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, skill_weight: val });
                                    }}
                                  />
                                </div>

                                <div style={{ padding: "12px", borderRadius: "10px", background: "rgba(168, 85, 247, 0.08)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
                                  <label style={{ fontSize: "0.75rem", color: "#c084fc", fontWeight: "600", display: "block", marginBottom: "6px" }}>
                                    Behavioral STAR Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.culture_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, culture_weight: val });
                                    }}
                                  />
                                </div>
                              </div>
                            </div>

                            {/* 2. Technical Assessment Configuration */}
                            <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
                                <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", margin: 0 }}>
                                  2. Technical Assessment Criteria & Sub-Weights
                                </h4>
                                <div style={{ display: "flex", gap: "12px", alignItems: "center" }}>
                                  <span style={{ fontSize: "0.72rem", color: isThresholdValid ? "#34d399" : "#f87171", fontWeight: "600" }}>
                                    {isThresholdValid ? `✓ Passing: ${rubricEditForm.passing_threshold}%` : "⚠ Passing % must be 0-100"}
                                  </span>
                                  <span style={{ fontSize: "0.72rem", color: isTechSubValid ? "#34d399" : "#f87171", fontWeight: "600" }}>
                                    {isTechSubValid ? "✓ Sub-Weights Sum: 100%" : `⚠ Sub-Weights Sum: ${techSubTotal}% (Must = 100%)`}
                                  </span>
                                </div>
                              </div>
                              <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px" }}>
                                <div>
                                  <label style={{ fontSize: "0.72rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                    Passing Threshold (0–100%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.passing_threshold}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, passing_threshold: val });
                                    }}
                                  />
                                </div>
                                <div>
                                  <label style={{ fontSize: "0.72rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                    MCQ Tasks Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.mcq_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, mcq_weight: val });
                                    }}
                                  />
                                </div>
                                <div>
                                  <label style={{ fontSize: "0.72rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                    Coding Tasks Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.coding_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, coding_weight: val });
                                    }}
                                  />
                                </div>
                                <div>
                                  <label style={{ fontSize: "0.72rem", color: "#94a3b8", display: "block", marginBottom: "4px" }}>
                                    Short Answer Weight (%)
                                  </label>
                                  <input
                                    type="number"
                                    min="0"
                                    max="100"
                                    className="form-input"
                                    value={rubricEditForm.short_answer_weight}
                                    onChange={(e) => {
                                      const val = e.target.value === "" ? "" : Math.min(100, Math.max(0, parseInt(e.target.value, 10) || 0));
                                      setRubricEditForm({ ...rubricEditForm, short_answer_weight: val });
                                    }}
                                  />
                                </div>
                              </div>
                            </div>

                            {/* 3. Behavioral STAR Competencies Editor */}
                            <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px", flexWrap: "wrap", gap: "8px" }}>
                                <div>
                                  <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", margin: 0 }}>
                                    3. Behavioral Competencies & Scoring Anchors
                                  </h4>
                                  <span style={{ fontSize: "0.72rem", color: isCompValid ? "#34d399" : "#f87171", fontWeight: "600" }}>
                                    {isCompValid
                                      ? `✓ Total: 100 / 100 pts (${rubricEditForm.competencies.length} competencies balanced)`
                                      : `⚠ Total: ${compTotal} / 100 pts (${100 - compTotal > 0 ? `Needs +${100 - compTotal} pts` : `Over by ${compTotal - 100} pts`})`}
                                  </span>
                                </div>
                                <div style={{ display: "flex", gap: "8px" }}>
                                  <button
                                    type="button"
                                    onClick={handleAutoBalanceCompetencies}
                                    className="btn btn-secondary"
                                    style={{ padding: "4px 10px", fontSize: "0.72rem", borderColor: "rgba(99, 102, 241, 0.4)", color: "#a5b4fc" }}
                                    title="Evenly divides 100 points across all competencies"
                                  >
                                    ⚖ Auto-Balance Evenly
                                  </button>
                                  <button
                                    type="button"
                                    onClick={handleAddCompetency}
                                    className="btn btn-secondary"
                                    style={{ padding: "4px 10px", fontSize: "0.72rem" }}
                                  >
                                    <Plus size={12} />
                                    <span>Add Competency</span>
                                  </button>
                                </div>
                              </div>

                              <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
                                {rubricEditForm.competencies.map((c, idx) => (
                                  <div
                                    key={idx}
                                    style={{
                                      display: "grid",
                                      gridTemplateColumns: "180px 80px 1fr 32px",
                                      gap: "8px",
                                      alignItems: "center",
                                      background: "rgba(30, 41, 59, 0.4)",
                                      padding: "8px 10px",
                                      borderRadius: "6px"
                                    }}
                                  >
                                    <input
                                      type="text"
                                      className="form-input"
                                      placeholder="Competency name"
                                      value={c.competency}
                                      onChange={(e) => handleCompetencyChange(idx, "competency", e.target.value)}
                                      style={{ padding: "6px 8px", fontSize: "0.75rem" }}
                                    />
                                    <input
                                      type="number"
                                      min="1"
                                      max="100"
                                      className="form-input"
                                      placeholder="Pts"
                                      value={c.max_points}
                                      onChange={(e) => handleCompetencyChange(idx, "max_points", e.target.value)}
                                      style={{ padding: "6px 8px", fontSize: "0.75rem", fontWeight: "600", color: "#38bdf8" }}
                                    />
                                    <input
                                      type="text"
                                      className="form-input"
                                      placeholder="Scoring guideline description"
                                      value={c.description}
                                      onChange={(e) => handleCompetencyChange(idx, "description", e.target.value)}
                                      style={{ padding: "6px 8px", fontSize: "0.75rem" }}
                                    />
                                    <button
                                      type="button"
                                      onClick={() => handleRemoveCompetency(idx)}
                                      disabled={rubricEditForm.competencies.length <= 1}
                                      style={{
                                        background: "transparent",
                                        border: "none",
                                        color: rubricEditForm.competencies.length <= 1 ? "#64748b" : "#f87171",
                                        cursor: rubricEditForm.competencies.length <= 1 ? "not-allowed" : "pointer",
                                        display: "flex",
                                        alignItems: "center",
                                        justifyContent: "center"
                                      }}
                                    >
                                      <Trash2 size={14} />
                                    </button>
                                  </div>
                                ))}
                              </div>
                            </div>
                          </>
                        );
                      })()
                    ) : (
                      /* Raw JSON Mode */
                      <div>
                        <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", marginBottom: "8px" }}>
                          Raw Rubric Schema (JSON)
                        </h4>
                        <textarea
                          className="form-textarea"
                          rows={14}
                          value={rubricEditForm.raw_json}
                          onChange={(e) => setRubricEditForm({ ...rubricEditForm, raw_json: e.target.value })}
                          style={{ fontFamily: "monospace", fontSize: "0.75rem", width: "100%" }}
                        />
                        {jsonError && (
                          <div style={{ color: "#f87171", fontSize: "0.75rem", marginTop: "6px" }}>
                            {jsonError}
                          </div>
                        )}
                      </div>
                    )}

                    {/* Bottom Action Buttons */}
                    {(() => {
                      const domainTotal = (Number(rubricEditForm.resume_weight) || 0) + (Number(rubricEditForm.skill_weight) || 0) + (Number(rubricEditForm.culture_weight) || 0);
                      const techSubTotal = (Number(rubricEditForm.mcq_weight) || 0) + (Number(rubricEditForm.coding_weight) || 0) + (Number(rubricEditForm.short_answer_weight) || 0);
                      const compTotal = rubricEditForm.competencies?.reduce((sum, c) => sum + (Number(c.max_points) || 0), 0) || 0;
                      const isDomainValid = domainTotal === 100;
                      const isThresholdValid = Number(rubricEditForm.passing_threshold) >= 0 && Number(rubricEditForm.passing_threshold) <= 100 && rubricEditForm.passing_threshold !== "";
                      const isTechSubValid = techSubTotal === 100;
                      const isCompValid = compTotal === 100;
                      const isGuidedValid = isDomainValid && isThresholdValid && isTechSubValid && isCompValid;
                      const isSaveDisabled = savingRubric || (rubricEditMode === "guided" ? !isGuidedValid : false);

                      return (
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", paddingTop: "12px", borderTop: "1px solid rgba(255, 255, 255, 0.08)", flexWrap: "wrap", gap: "10px" }}>
                          <div>
                            <span style={{ fontSize: "0.75rem", color: "#94a3b8", display: "block" }}>
                              Saving increments rubric version and updates the immutable audit trail.
                            </span>
                            {rubricEditMode === "guided" && !isGuidedValid && (
                              <span style={{ fontSize: "0.72rem", color: "#f87171", fontWeight: "600" }}>
                                Cannot deploy until all items balance: 
                                {!isDomainValid && ` Domain (${domainTotal}/100%)`}
                                {!isThresholdValid && " Passing Threshold (0-100%)"}
                                {!isTechSubValid && ` Tech Sub-Weights (${techSubTotal}/100%)`}
                                {!isCompValid && ` Competencies (${compTotal}/100 pts)`}
                              </span>
                            )}
                          </div>

                          <div style={{ display: "flex", gap: "10px" }}>
                            <button
                              type="button"
                              onClick={() => setIsEditingRubric(false)}
                              className="btn btn-secondary"
                              style={{ padding: "8px 14px", fontSize: "0.8rem" }}
                            >
                              Cancel
                            </button>
                            <button
                              type="button"
                              disabled={isSaveDisabled}
                              onClick={handleSaveRubric}
                              className="btn btn-primary"
                              style={{ 
                                padding: "8px 18px", 
                                fontSize: "0.8rem",
                                opacity: isSaveDisabled ? 0.5 : 1,
                                cursor: isSaveDisabled ? "not-allowed" : "pointer"
                              }}
                            >
                              <Save size={14} />
                              <span>{savingRubric ? "Saving Rubric..." : "Save & Deploy Rubric"}</span>
                            </button>
                          </div>
                        </div>
                      );
                    })()}
                  </div>
                ) : (
                  /* VIEW MODE */
                  <div>
                    {/* Rubric Weights Overview */}
                    <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "14px", marginBottom: "20px" }}>
                      <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(6, 182, 212, 0.1)", border: "1px solid rgba(6, 182, 212, 0.2)" }}>
                        <div style={{ fontSize: "0.75rem", color: "#06b6d4", fontWeight: "600" }}>Resume Fit Weight</div>
                        <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                          {Math.round(selectedRubric.resume_weight * 100)}%
                        </div>
                        <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>
                          Skills, Exp & Pedigree
                        </div>
                      </div>

                      <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                        <div style={{ fontSize: "0.75rem", color: "#818cf8", fontWeight: "600" }}>Technical Test Weight</div>
                        <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                          {Math.round(selectedRubric.skill_weight * 100)}%
                        </div>
                        <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>
                          Pass: {selectedRubric.criteria?.technical_scoring?.passing_threshold || 70}%
                        </div>
                      </div>

                      <div style={{ padding: "14px", borderRadius: "10px", background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
                        <div style={{ fontSize: "0.75rem", color: "#c084fc", fontWeight: "600" }}>Behavioral STAR Weight</div>
                        <div style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc", marginTop: "4px" }}>
                          {Math.round(selectedRubric.culture_weight * 100)}%
                        </div>
                        <div style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px" }}>
                          {selectedRubric.criteria?.behavioral_scoring?.competencies?.length || 4} Competencies
                        </div>
                      </div>
                    </div>

                    {/* Behavioral Competencies Summary Cards */}
                    {selectedRubric.criteria?.behavioral_scoring?.competencies?.length > 0 && (
                      <div style={{ marginBottom: "20px" }}>
                        <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#c084fc", marginBottom: "10px" }}>
                          Behavioral Competency Anchors:
                        </h4>
                        <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: "10px" }}>
                          {selectedRubric.criteria.behavioral_scoring.competencies.map((c, i) => (
                            <div
                              key={i}
                              style={{
                                background: "rgba(15, 23, 42, 0.6)",
                                border: "1px solid rgba(255, 255, 255, 0.05)",
                                borderRadius: "8px",
                                padding: "10px 12px"
                              }}
                            >
                              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                                <span style={{ fontWeight: "700", color: "#f8fafc", fontSize: "0.8rem" }}>{c.competency}</span>
                                <span style={{ fontSize: "0.7rem", color: "#c084fc", background: "rgba(168, 85, 247, 0.15)", padding: "1px 6px", borderRadius: "4px" }}>
                                  {c.max_points} pts
                                </span>
                              </div>
                              <p style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "4px", lineHeight: "1.4" }}>
                                {c.description}
                              </p>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* Criteria Detail Breakdown */}
                    <div style={{ background: "rgba(15, 23, 42, 0.8)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "8px" }}>
                        <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#38bdf8", margin: 0 }}>
                          Full Rubric Criteria Schema (JSON):
                        </h4>
                        <button
                          type="button"
                          onClick={startEditingRubric}
                          className="btn btn-secondary"
                          style={{ padding: "3px 8px", fontSize: "0.7rem" }}
                        >
                          <Edit3 size={11} />
                          <span>Edit</span>
                        </button>
                      </div>
                      <pre style={{ fontSize: "0.75rem", color: "#cbd5e1", overflowX: "auto", maxHeight: "260px" }}>
                        {JSON.stringify(selectedRubric.criteria, null, 2)}
                      </pre>
                    </div>
                  </div>
                )}
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
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Min Experience (Years, whole numbers)</label>
                  <input
                    type="number"
                    min="0"
                    step="1"
                    className="form-input"
                    placeholder="e.g. 3"
                    value={formData.min_experience}
                    onChange={(e) => {
                      const val = e.target.value === "" ? "" : Math.max(0, parseInt(e.target.value, 10) || 0);
                      setFormData({ ...formData, min_experience: val });
                    }}
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
