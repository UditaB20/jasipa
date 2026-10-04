import React, { useState, useEffect, useRef } from "react";
import { 
  Briefcase, 
  CheckCircle2, 
  Clock, 
  FileText, 
  Send, 
  User, 
  Code, 
  MessageSquare, 
  AlertCircle, 
  CheckCircle,
  ChevronRight,
  LayoutDashboard,
  Edit3,
  Save,
  X,
  Upload,
  FileUp
} from "lucide-react";
import { 
  getCandidateProfile, 
  getCandidateApplications, 
  getCandidateJobs, 
  applyCandidateJob, 
  getCandidateAssessments, 
  submitCandidateTechnical, 
  submitCandidateBehavioral, 
  getCandidateTimeline,
  updateCandidateProfile,
  uploadCandidateResume
} from "../services/api";

export default function CandidatePortal({ currentUser, onLogout }) {
  const [activeTab, setActiveTab] = useState("dashboard"); // dashboard, jobs, applications, assessments, profile
  const [profile, setProfile] = useState(null);
  const [applications, setApplications] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [timeline, setTimeline] = useState([]);
  const [assessmentsData, setAssessmentsData] = useState(null);
  const [loading, setLoading] = useState(true);

  // Apply form state
  const [selectedJobToApply, setSelectedJobToApply] = useState(null);
  const [resumeTextInput, setResumeTextInput] = useState("");
  const [applyLoading, setApplyLoading] = useState(false);
  const [applySuccessMsg, setApplySuccessMsg] = useState(null);

  // Technical Assessment answers state
  const [techAnswers, setTechAnswers] = useState({});
  const [techSubmitting, setTechSubmitting] = useState(false);
  const [techDoneMsg, setTechDoneMsg] = useState(null);

  // Behavioral Assessment answers state
  const [behAnswers, setBehAnswers] = useState({});
  const [behSubmitting, setBehSubmitting] = useState(false);
  const [behDoneMsg, setBehDoneMsg] = useState(null);

  // Edit Profile state
  const [isEditingProfile, setIsEditingProfile] = useState(false);
  const [editFormData, setEditFormData] = useState({
    name: "",
    phone: "",
    education: "",
    experience_years: 0,
    skills_text: ""
  });
  const [saveProfileLoading, setSaveProfileLoading] = useState(false);
  const [profileSuccessMsg, setProfileSuccessMsg] = useState(null);

  // Resume upload state
  const [resumeUploading, setResumeUploading] = useState(false);
  const [resumeUploadMsg, setResumeUploadMsg] = useState(null);
  const resumeFileRef = useRef(null);


  const startEditProfile = () => {
    setEditFormData({
      name: profile?.name || "",
      phone: profile?.phone || "",
      education: profile?.education || "",
      experience_years: profile?.experience_years || 0,
      skills_text: (profile?.skills_extracted || []).join(", ")
    });
    setProfileSuccessMsg(null);
    setIsEditingProfile(true);
  };

  const handleSaveProfile = async (e) => {
    e.preventDefault();
    setSaveProfileLoading(true);
    setProfileSuccessMsg(null);
    try {
      const skillsArray = editFormData.skills_text
        .split(",")
        .map(s => s.trim())
        .filter(Boolean);

      const res = await updateCandidateProfile({
        name: editFormData.name,
        phone: editFormData.phone,
        education: editFormData.education,
        experience_years: parseFloat(editFormData.experience_years) || 0,
        skills_extracted: skillsArray
      });

      setProfile(res);
      setProfileSuccessMsg("Your candidate profile was updated successfully!");
      setIsEditingProfile(false);
      loadCandidateData();
    } catch (err) {
      alert("Failed to update profile: " + err.message);
    } finally {
      setSaveProfileLoading(false);
    }
  };

  const handleResumeUpload = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!file.name.toLowerCase().endsWith(".pdf")) {
      setResumeUploadMsg({ type: "error", text: "Only PDF files are accepted." });
      return;
    }
    setResumeUploading(true);
    setResumeUploadMsg(null);
    try {
      const result = await uploadCandidateResume(file);
      setResumeUploadMsg({
        type: "success",
        text: `Resume uploaded! Found ${result.skills_extracted?.length || 0} skills — profile updated automatically.`
      });
      loadCandidateData();
    } catch (err) {
      setResumeUploadMsg({ type: "error", text: "Upload failed: " + err.message });
    } finally {
      setResumeUploading(false);
      if (resumeFileRef.current) resumeFileRef.current.value = "";
    }
  };

  useEffect(() => {

    loadCandidateData();
  }, []);

  async function loadCandidateData() {
    setLoading(true);
    try {
      const [prof, apps, jbs, tline, assess] = await Promise.all([
        getCandidateProfile().catch(() => null),
        getCandidateApplications().catch(() => []),
        getCandidateJobs().catch(() => []),
        getCandidateTimeline().catch(() => ({ timeline: [] })),
        getCandidateAssessments().catch(() => null)
      ]);

      setProfile(prof);
      setApplications(apps || []);
      setJobs(jbs || []);
      setTimeline(tline?.timeline || []);
      setAssessmentsData(assess);
    } catch (err) {
      console.error("Error loading candidate portal data:", err);
    } finally {
      setLoading(false);
    }
  }

  const handleApply = async (e) => {
    e.preventDefault();
    if (!selectedJobToApply) return;
    setApplyLoading(true);
    setApplySuccessMsg(null);

    try {
      await applyCandidateJob({
        jd_id: selectedJobToApply.jd_id,
        resume_text: resumeTextInput || "Candidate submitted resume via portal."
      });
      setApplySuccessMsg(`Application submitted successfully for ${selectedJobToApply.title}!`);
      setSelectedJobToApply(null);
      setResumeTextInput("");
      loadCandidateData();
    } catch (err) {
      alert("Failed to submit application: " + err.message);
    } finally {
      setApplyLoading(false);
    }
  };

  const handleSubmitTechnical = async (e) => {
    e.preventDefault();
    setTechSubmitting(true);
    try {
      const answersList = Object.entries(techAnswers).map(([qid, ans]) => ({
        question_id: qid,
        answer_text: ans
      }));
      const res = await submitCandidateTechnical({ answers: answersList });
      setTechDoneMsg(`Technical assessment submitted! Score: ${res.score}/100`);
      loadCandidateData();
    } catch (err) {
      alert("Failed to submit technical answers: " + err.message);
    } finally {
      setTechSubmitting(false);
    }
  };

  const handleSubmitBehavioral = async (e) => {
    e.preventDefault();
    setBehSubmitting(true);
    try {
      const answersList = Object.entries(behAnswers).map(([qid, ans]) => ({
        question_id: qid,
        answer_text: ans
      }));
      const res = await submitCandidateBehavioral({ answers: answersList });
      setBehDoneMsg(`Behavioral assessment submitted! Score: ${res.score}/100`);
      loadCandidateData();
    } catch (err) {
      alert("Failed to submit behavioral answers: " + err.message);
    } finally {
      setBehSubmitting(false);
    }
  };

  if (loading) {
    return (
      <div style={{ padding: "60px 20px", textAlign: "center", color: "#94a3b8" }}>
        Loading your candidate career portal...
      </div>
    );
  }

  const candidateName = profile?.name || currentUser?.name || "Candidate";

  return (
    <div style={{ display: "flex", minHeight: "calc(100vh - 57px)" }}>
      {/* Candidate Left Navigation */}
      <aside style={{
        width: "220px",
        background: "#0f172a",
        borderRight: "1px solid #334155",
        padding: "16px 12px",
        flexShrink: 0
      }}>
        <div style={{ padding: "8px 12px 6px", fontSize: "0.75rem", fontWeight: "600", color: "#64748b", textTransform: "uppercase" }}>
          My Career
        </div>
        <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          {[
            { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
            { id: "jobs", label: "Browse Jobs", icon: Briefcase },
            { id: "applications", label: "My Applications", icon: Clock },
            { id: "assessments", label: "Assessments", icon: Code },
            { id: "profile", label: "My Profile", icon: User },
          ].map((tab) => {
            const Icon = tab.icon;
            const isActive = activeTab === tab.id;
            return (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  padding: "9px 12px",
                  borderRadius: "6px",
                  border: "none",
                  background: isActive ? "#1e293b" : "transparent",
                  color: isActive ? "#ffffff" : "#94a3b8",
                  fontWeight: isActive ? "600" : "500",
                  fontSize: "0.875rem",
                  cursor: "pointer",
                  textAlign: "left",
                }}
              >
                <Icon size={16} color={isActive ? "#34d399" : "#64748b"} />
                <span>{tab.label}</span>
              </button>
            );
          })}
        </nav>
      </aside>

      {/* Main Content Area */}
      <main style={{ flex: 1, padding: "28px 36px", overflowY: "auto", maxWidth: "1200px" }}>
        
        {/* TAB 1: DASHBOARD */}
        {activeTab === "dashboard" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <h2 className="page-title">Welcome, {candidateName}</h2>
              <p className="page-subtitle">Track your application status, complete assessments, and explore open roles.</p>
            </div>

            {applySuccessMsg && (
              <div style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#34d399",
                padding: "12px 16px",
                borderRadius: "8px",
                marginBottom: "20px",
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}>
                <CheckCircle2 size={18} />
                <span>{applySuccessMsg}</span>
              </div>
            )}

            {/* My Applications Card */}
            <div className="card" style={{ marginBottom: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc" }}>My Applications</h3>
                <button onClick={() => setActiveTab("jobs")} className="btn btn-outline" style={{ fontSize: "0.8rem", padding: "4px 10px" }}>
                  View All Jobs
                </button>
              </div>

              {applications.length === 0 ? (
                <div style={{ textAlign: "center", padding: "24px 0", color: "#64748b" }}>
                  <p>You have not applied to any roles yet.</p>
                  <button onClick={() => setActiveTab("jobs")} className="btn btn-primary" style={{ marginTop: "12px" }}>
                    Explore Available Positions
                  </button>
                </div>
              ) : (
                <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                  {applications.map((app, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: "#0f172a",
                        border: "1px solid #334155",
                        borderRadius: "8px",
                        padding: "14px 18px",
                        display: "flex",
                        justifyContent: "space-between",
                        alignItems: "center"
                      }}
                    >
                      <div>
                        <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc" }}>
                          {app.job_title}
                        </div>
                        <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "2px" }}>
                          Department: {app.department}
                        </div>
                      </div>

                      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                        <span className="badge badge-primary">
                          Stage: {app.current_stage?.replace(/_/g, " ")}
                        </span>
                        <button
                          onClick={() => setActiveTab("assessments")}
                          className="btn btn-outline"
                          style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                        >
                          Go to Assessment
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>

            {/* Application Journey Timeline */}
            <div className="card">
              <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc", marginBottom: "16px" }}>
                Application Journey Timeline
              </h3>

              <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
                {timeline.map((step, index) => {
                  const isCompleted = step.status === "COMPLETED";
                  const isCurrent = step.status === "CURRENT";

                  return (
                    <div
                      key={step.stage}
                      style={{
                        display: "flex",
                        alignItems: "flex-start",
                        gap: "14px",
                        padding: "10px 14px",
                        borderRadius: "8px",
                        background: isCurrent ? "rgba(79, 70, 229, 0.08)" : "transparent",
                        border: isCurrent ? "1px solid rgba(79, 70, 229, 0.3)" : "1px solid transparent"
                      }}
                    >
                      <div style={{ marginTop: "2px" }}>
                        {isCompleted ? (
                          <CheckCircle2 size={18} color="#10b981" />
                        ) : isCurrent ? (
                          <div style={{ width: "18px", height: "18px", borderRadius: "50%", background: "#4f46e5", display: "flex", alignItems: "center", justifyContent: "center", color: "#fff", fontSize: "10px", fontWeight: "700" }}>
                            {index + 1}
                          </div>
                        ) : (
                          <div style={{ width: "18px", height: "18px", borderRadius: "50%", border: "2px solid #475569" }} />
                        )}
                      </div>

                      <div style={{ flex: 1 }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                          <span style={{ fontSize: "0.875rem", fontWeight: isCurrent ? "700" : "500", color: isCurrent ? "#f8fafc" : isCompleted ? "#cbd5e1" : "#64748b" }}>
                            {step.label}
                          </span>
                          {isCurrent && <span className="badge badge-primary">Current Stage</span>}
                          {isCompleted && <span className="badge badge-success">Completed</span>}
                        </div>
                        <p style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "2px" }}>
                          {step.description}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: BROWSE JOBS */}
        {activeTab === "jobs" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <h2 className="page-title">Available Positions</h2>
              <p className="page-subtitle">Explore open job requisitions and submit your application.</p>
            </div>

            {selectedJobToApply && (
              <div className="card" style={{ marginBottom: "28px", borderColor: "#4f46e5" }}>
                <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc", marginBottom: "8px" }}>
                  Apply for: {selectedJobToApply.title}
                </h3>
                <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginBottom: "16px" }}>
                  Please paste or summarize your resume highlights and qualifications below:
                </p>

                <form onSubmit={handleApply}>
                  <div style={{ marginBottom: "16px" }}>
                    <label className="form-label">Resume / Profile Highlights</label>
                    <textarea
                      rows={5}
                      className="form-textarea"
                      placeholder="e.g. Senior Software Engineer with 4 years in Python, FastAPI, React, SQL..."
                      value={resumeTextInput}
                      onChange={(e) => setResumeTextInput(e.target.value)}
                      required
                    />
                  </div>

                  <div style={{ display: "flex", gap: "10px" }}>
                    <button type="submit" className="btn btn-primary" disabled={applyLoading}>
                      <Send size={15} />
                      <span>{applyLoading ? "Submitting Application..." : "Submit Application"}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setSelectedJobToApply(null)}
                      className="btn btn-outline"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            )}

            <div style={{ display: "grid", gridTemplateColumns: "1fr", gap: "16px" }}>
              {jobs.map((job) => (
                <div key={job.jd_id} className="card">
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "10px" }}>
                    <div>
                      <h3 style={{ fontSize: "1.1rem", fontWeight: "600", color: "#f8fafc" }}>{job.title}</h3>
                      <div style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "2px" }}>
                        {job.department} • Minimum {job.min_experience} Years Experience
                      </div>
                    </div>

                    <button
                      onClick={() => {
                        setSelectedJobToApply(job);
                        window.scrollTo({ top: 0, behavior: "smooth" });
                      }}
                      className="btn btn-primary"
                      style={{ padding: "6px 14px" }}
                    >
                      <span>Apply Now</span>
                      <ChevronRight size={14} />
                    </button>
                  </div>

                  <p style={{ fontSize: "0.875rem", color: "#cbd5e1", margin: "12px 0", lineHeight: "1.5" }}>
                    {job.description}
                  </p>

                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "12px" }}>
                    {job.required_skills?.map((skill) => (
                      <span key={skill} className="badge badge-neutral">
                        {skill}
                      </span>
                    ))}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* TAB 3: MY APPLICATIONS */}
        {activeTab === "applications" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <h2 className="page-title">My Applications</h2>
              <p className="page-subtitle">Review the status and milestones of your active job submissions.</p>
            </div>

            {applications.length === 0 ? (
              <div className="card" style={{ textAlign: "center", padding: "40px" }}>
                <p style={{ color: "#94a3b8" }}>No active applications found.</p>
                <button onClick={() => setActiveTab("jobs")} className="btn btn-primary" style={{ marginTop: "12px" }}>
                  Apply for a Job
                </button>
              </div>
            ) : (
              <div className="table-container">
                <table className="data-table">
                  <thead>
                    <tr>
                      <th>Position</th>
                      <th>Department</th>
                      <th>Current Stage</th>
                      <th>Applied Date</th>
                      <th style={{ textAlign: "right" }}>Action</th>
                    </tr>
                  </thead>
                  <tbody>
                    {applications.map((app, i) => (
                      <tr key={i}>
                        <td style={{ fontWeight: "600" }}>{app.job_title}</td>
                        <td style={{ color: "#94a3b8" }}>{app.department}</td>
                        <td>
                          <span className="badge badge-primary">
                            {app.current_stage?.replace(/_/g, " ")}
                          </span>
                        </td>
                        <td style={{ color: "#94a3b8", fontSize: "0.8rem" }}>
                          {app.applied_date ? new Date(app.applied_date).toLocaleDateString() : "Active"}
                        </td>
                        <td style={{ textAlign: "right" }}>
                          <button
                            onClick={() => setActiveTab("assessments")}
                            className="btn btn-outline"
                            style={{ padding: "4px 10px", fontSize: "0.75rem" }}
                          >
                            Assessments
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
        )}

        {/* TAB 4: ASSESSMENTS */}
        {activeTab === "assessments" && (
          <div>
            <div style={{ marginBottom: "24px" }}>
              <h2 className="page-title">Skill & Behavioral Assessments</h2>
              <p className="page-subtitle">Demonstrate your technical competencies and structured STAR experiences.</p>
            </div>

            {techDoneMsg && (
              <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px" }}>
                {techDoneMsg}
              </div>
            )}

            {behDoneMsg && (
              <div style={{ background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)", color: "#34d399", padding: "10px 14px", borderRadius: "6px", marginBottom: "16px" }}>
                {behDoneMsg}
              </div>
            )}

            {/* Technical Assessment Section */}
            <div className="card" style={{ marginBottom: "28px" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc" }}>
                    Part 1: Technical Assessment
                  </h3>
                  <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Standardized practical questions evaluated by the Skill-Assessor.
                  </p>
                </div>
                {assessmentsData?.technical?.completed ? (
                  <span className="badge badge-success">
                    Completed (Score: {assessmentsData.technical.score}/100)
                  </span>
                ) : (
                  <span className="badge badge-warning">Pending Submission</span>
                )}
              </div>

              {!assessmentsData?.technical?.completed ? (
                <form onSubmit={handleSubmitTechnical}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "16px" }}>
                    {(assessmentsData?.technical?.questions || []).map((q, idx) => (
                      <div key={q.question_id} style={{ background: "#0f172a", padding: "14px", borderRadius: "8px", border: "1px solid #334155" }}>
                        <div style={{ fontWeight: "600", color: "#f8fafc", fontSize: "0.875rem", marginBottom: "6px" }}>
                          Q{idx + 1}: {q.prompt}
                        </div>
                        <textarea
                          rows={3}
                          className="form-textarea"
                          placeholder="Write your answer or code snippet..."
                          value={techAnswers[q.question_id] || ""}
                          onChange={(e) => setTechAnswers({ ...techAnswers, [q.question_id]: e.target.value })}
                          required
                        />
                      </div>
                    ))}
                  </div>

                  <button type="submit" className="btn btn-primary" disabled={techSubmitting}>
                    {techSubmitting ? "Evaluating with Skill-Assessor..." : "Submit Technical Assessment"}
                  </button>
                </form>
              ) : (
                <p style={{ color: "#64748b", fontSize: "0.85rem" }}>
                  Your technical assessment responses have been scored and logged in the panel dossier.
                </p>
              )}
            </div>

            {/* Behavioral STAR Assessment Section */}
            <div className="card">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
                <div>
                  <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc" }}>
                    Part 2: Behavioral Assessment (STAR Method)
                  </h3>
                  <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Evaluated by the Culture-Fit Agent for Communication, Teamwork, Problem-Solving, and Adaptability.
                  </p>
                </div>
                {assessmentsData?.behavioral?.completed ? (
                  <span className="badge badge-success">
                    Completed (Score: {assessmentsData.behavioral.score}/100)
                  </span>
                ) : (
                  <span className="badge badge-warning">Pending Submission</span>
                )}
              </div>

              {!assessmentsData?.behavioral?.completed ? (
                <form onSubmit={handleSubmitBehavioral}>
                  <div style={{ display: "flex", flexDirection: "column", gap: "16px", marginBottom: "16px" }}>
                    {(assessmentsData?.behavioral?.questions || []).map((q, idx) => (
                      <div key={q.question_id} style={{ background: "#0f172a", padding: "14px", borderRadius: "8px", border: "1px solid #334155" }}>
                        <div style={{ fontWeight: "600", color: "#f8fafc", fontSize: "0.875rem", marginBottom: "6px" }}>
                          Q{idx + 1}: {q.prompt}
                        </div>
                        <textarea
                          rows={4}
                          className="form-textarea"
                          placeholder="Describe the Situation, Task, Action you took, and Result achieved (STAR)..."
                          value={behAnswers[q.question_id] || ""}
                          onChange={(e) => setBehAnswers({ ...behAnswers, [q.question_id]: e.target.value })}
                          required
                        />
                      </div>
                    ))}
                  </div>

                  <button type="submit" className="btn btn-primary" disabled={behSubmitting}>
                    {behSubmitting ? "Evaluating with Culture-Fit Agent..." : "Submit Behavioral Assessment"}
                  </button>
                </form>
              ) : (
                <p style={{ color: "#64748b", fontSize: "0.85rem" }}>
                  Your behavioral answers have been evaluated and recorded.
                </p>
              )}
            </div>
          </div>
        )}

        {/* TAB 5: PROFILE */}
        {activeTab === "profile" && (
          <div>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "24px" }}>
              <div>
                <h2 className="page-title">Candidate Profile</h2>
                <p className="page-subtitle">Your personal account details and stored application credentials.</p>
              </div>

              {!isEditingProfile && (
                <button
                  onClick={startEditProfile}
                  className="btn btn-outline"
                  style={{ gap: "6px" }}
                >
                  <Edit3 size={15} />
                  <span>Edit Profile</span>
                </button>
              )}
            </div>

            {profileSuccessMsg && (
              <div style={{
                background: "rgba(16, 185, 129, 0.1)",
                border: "1px solid rgba(16, 185, 129, 0.3)",
                color: "#34d399",
                padding: "12px 16px",
                borderRadius: "8px",
                marginBottom: "20px",
                display: "flex",
                alignItems: "center",
                gap: "10px"
              }}>
                <CheckCircle2 size={18} />
                <span>{profileSuccessMsg}</span>
              </div>
            )}

            {isEditingProfile ? (
              <div className="card" style={{ maxWidth: "650px", borderColor: "#4f46e5" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "18px" }}>
                  <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc" }}>
                    Edit Personal & Professional Details
                  </h3>
                  <button
                    type="button"
                    onClick={() => setIsEditingProfile(false)}
                    style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
                  >
                    <X size={18} />
                  </button>
                </div>

                <form onSubmit={handleSaveProfile} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
                  <div>
                    <label className="form-label">Full Name</label>
                    <input
                      type="text"
                      className="form-input"
                      value={editFormData.name}
                      onChange={(e) => setEditFormData({ ...editFormData, name: e.target.value })}
                      required
                    />
                  </div>

                  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "14px" }}>
                    <div>
                      <label className="form-label">Phone Number</label>
                      <input
                        type="text"
                        className="form-input"
                        placeholder="+1 (555) 000-0000"
                        value={editFormData.phone}
                        onChange={(e) => setEditFormData({ ...editFormData, phone: e.target.value })}
                      />
                    </div>

                    <div>
                      <label className="form-label">Years of Experience</label>
                      <input
                        type="number"
                        step="0.5"
                        min="0"
                        className="form-input"
                        value={editFormData.experience_years}
                        onChange={(e) => setEditFormData({ ...editFormData, experience_years: e.target.value })}
                      />
                    </div>
                  </div>

                  <div>
                    <label className="form-label">Highest Education</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Master's in Computer Science"
                      value={editFormData.education}
                      onChange={(e) => setEditFormData({ ...editFormData, education: e.target.value })}
                    />
                  </div>

                  <div>
                    <label className="form-label">Skills (comma-separated)</label>
                    <input
                      type="text"
                      className="form-input"
                      placeholder="e.g. Python, SQL, React, FastAPI, Docker"
                      value={editFormData.skills_text}
                      onChange={(e) => setEditFormData({ ...editFormData, skills_text: e.target.value })}
                    />
                    <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px", display: "block" }}>
                      Separate skills with commas (e.g. Python, SQL, Docker)
                    </span>
                  </div>

                  <div style={{ display: "flex", gap: "10px", marginTop: "8px" }}>
                    <button type="submit" className="btn btn-primary" disabled={saveProfileLoading}>
                      <Save size={15} />
                      <span>{saveProfileLoading ? "Saving Changes..." : "Save Profile"}</span>
                    </button>
                    <button
                      type="button"
                      onClick={() => setIsEditingProfile(false)}
                      className="btn btn-outline"
                    >
                      Cancel
                    </button>
                  </div>
                </form>
              </div>
            ) : (
              <div className="card" style={{ maxWidth: "600px" }}>
                <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginBottom: "16px" }}>
                  <div>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Full Name</span>
                    <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "2px" }}>
                      {profile?.name || candidateName}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Email Address</span>
                    <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "2px" }}>
                      {profile?.email || currentUser?.email}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Phone</span>
                    <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "2px" }}>
                      {profile?.phone || "Not provided"}
                    </div>
                  </div>

                  <div>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Years of Experience</span>
                    <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "2px" }}>
                      {profile?.experience_years ? `${profile.experience_years} Years` : "0 Years"}
                    </div>
                  </div>

                  <div style={{ gridColumn: "span 2" }}>
                    <span style={{ fontSize: "0.8rem", color: "#64748b" }}>Education</span>
                    <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "2px" }}>
                      {profile?.education || "Bachelor's Degree"}
                    </div>
                  </div>
                </div>

                <div style={{ marginTop: "16px", paddingTop: "16px", borderTop: "1px solid #334155" }}>
                  <span style={{ fontSize: "0.8rem", color: "#64748b", display: "block", marginBottom: "8px" }}>
                    Extracted Skills & Competencies
                  </span>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {(profile?.skills_extracted || ["Python", "FastAPI", "SQL", "React", "Data Structures"]).map((s) => (
                      <span key={s} className="badge badge-neutral">{s}</span>
                    ))}
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

      </main>
    </div>
  );
}
