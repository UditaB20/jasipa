import React, { useState, useEffect } from "react";
import { 
  FileText, Upload, Code, MessageSquare, CheckCircle2, Clock, 
  Sparkles, Briefcase, ArrowRight, User, AlertCircle
} from "lucide-react";
import { 
  getJobs, uploadResume, createCandidate, getTechnicalQuestions, 
  getBehavioralQuestions, submitTechnicalAssessment, submitBehavioralAssessment,
  getCandidate
} from "../services/api";
import StageBadge from "../components/StageBadge";

export default function StudentPortal({ selectedCandidateId, setSelectedCandidateId }) {
  const [jobs, setJobs] = useState([]);
  const [selectedJdId, setSelectedJdId] = useState("");
  const [candidateProfile, setCandidateProfile] = useState(null);
  const [activeStep, setActiveStep] = useState("resume"); // "resume", "technical", "behavioral", "status"

  // Application Form State
  const [formData, setFormData] = useState({
    name: "Elena Rostova",
    email: "elena.student@example.com",
    phone: "+1 (555) 432-1098",
    cohort_tag: "Cohort_Alpha",
    resume_text: "Senior Software Engineer with 5 years experience architecting high-performance FastAPI microservices and React web applications. Proficient in SQL, PostgreSQL, Python, Data Structures, and Docker.",
    file: null
  });
  const [uploading, setUploading] = useState(false);

  // Assessment Questions & Answers
  const [techQuestions, setTechQuestions] = useState([]);
  const [behQuestions, setBehQuestions] = useState([]);
  const [techAnswers, setTechAnswers] = useState({});
  const [behAnswers, setBehAnswers] = useState({});
  const [submittingTech, setSubmittingTech] = useState(false);
  const [submittingBeh, setSubmittingBeh] = useState(false);
  const [techSubmitted, setTechSubmitted] = useState(false);
  const [behSubmitted, setBehSubmitted] = useState(false);

  useEffect(() => {
    loadPortalData();
  }, []);

  async function loadPortalData() {
    try {
      const jList = await getJobs();
      setJobs(jList);
      if (jList.length > 0) {
        setSelectedJdId(jList[0].jd_id);
        loadQuestions(jList[0].jd_id);
      }

      if (selectedCandidateId) {
        const cand = await getCandidate(selectedCandidateId);
        setCandidateProfile(cand);
        if (cand.assessments?.some(a => a.test_type === "TECHNICAL")) setTechSubmitted(true);
        if (cand.assessments?.some(a => a.test_type === "BEHAVIORAL")) setBehSubmitted(true);
      }
    } catch (err) {
      console.error("Error loading student portal data:", err);
    }
  }

  async function loadQuestions(jdId) {
    try {
      const [tq, bq] = await Promise.all([
        getTechnicalQuestions(jdId),
        getBehavioralQuestions(jdId)
      ]);
      setTechQuestions(tq.questions || []);
      setBehQuestions(bq.questions || []);

      const tAns = {};
      (tq.questions || []).forEach(q => {
        if (q.type === "mcq") tAns[q.question_id] = "B";
        else if (q.type === "short_answer") tAns[q.question_id] = "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;";
        else if (q.type === "coding") tAns[q.question_id] = "def has_cycle(graph):\n    visited = set()\n    rec_stack = set()\n    # Recursive DFS cycle check with O(V+E) time complexity";
      });
      setTechAnswers(tAns);

      const bAns = {
        "BEH_Q1": "In my previous project, we had a technical disagreement on database caching. I benchmarked Redis vs Memcached with realistic payloads, presented the latency metrics, and achieved team consensus.",
        "BEH_Q2": "When faced with vague pipeline requirements, I decomposed the problem into measurable ingestion and queuing stages, scheduled stakeholder demos, and delivered an MVP.",
        "BEH_Q3": "Required to learn Kubernetes in 2 weeks for release, I spun up local Minikube clusters, wrote Helm charts, and deployed successfully.",
        "BEH_Q4": "I communicated API decoupling to non-technical stakeholders using business KPI impact diagrams rather than low-level code specifics."
      };
      setBehAnswers(bAns);
    } catch (err) {
      console.error("Error loading assessment questions:", err);
    }
  }

  async function handleApplyAndUpload(e) {
    e.preventDefault();
    setUploading(true);
    try {
      let cand;
      if (formData.file) {
        const uploadForm = new FormData();
        uploadForm.append("name", formData.name);
        uploadForm.append("email", formData.email);
        uploadForm.append("phone", formData.phone || "");
        uploadForm.append("cohort_tag", formData.cohort_tag);
        uploadForm.append("target_jd_id", selectedJdId);
        uploadForm.append("file", formData.file);
        cand = await uploadResume(uploadForm);
      } else {
        cand = await createCandidate({
          name: formData.name,
          email: formData.email,
          phone: formData.phone,
          cohort_tag: formData.cohort_tag,
          resume_text: formData.resume_text,
          target_jd_id: selectedJdId
        });
      }

      setCandidateProfile(cand);
      setSelectedCandidateId(cand.candidate_id);
      setActiveStep("technical");
    } catch (err) {
      alert("Application submission failed: " + err.message);
    } finally {
      setUploading(false);
    }
  }

  async function handleSubmitTechnical(e) {
    e.preventDefault();
    if (!candidateProfile) return;
    setSubmittingTech(true);
    try {
      const answersList = Object.entries(techAnswers).map(([qid, text]) => ({
        question_id: qid,
        answer_text: text
      }));
      await submitTechnicalAssessment({
        candidate_id: candidateProfile.candidate_id,
        jd_id: selectedJdId,
        answers: answersList
      });
      setTechSubmitted(true);
      setActiveStep("behavioral");
    } catch (err) {
      alert("Technical submission failed: " + err.message);
    } finally {
      setSubmittingTech(false);
    }
  }

  async function handleSubmitBehavioral(e) {
    e.preventDefault();
    if (!candidateProfile) return;
    setSubmittingBeh(true);
    try {
      const answersList = Object.entries(behAnswers).map(([qid, text]) => ({
        question_id: qid,
        answer_text: text
      }));
      await submitBehavioralAssessment({
        candidate_id: candidateProfile.candidate_id,
        jd_id: selectedJdId,
        answers: answersList
      });
      setBehSubmitted(true);
      setActiveStep("status");
      // Refresh profile
      const updated = await getCandidate(candidateProfile.candidate_id);
      setCandidateProfile(updated);
    } catch (err) {
      alert("Behavioral submission failed: " + err.message);
    } finally {
      setSubmittingBeh(false);
    }
  }

  const selectedJobObj = jobs.find(j => j.jd_id === selectedJdId);

  return (
    <div style={{ padding: "28px", maxWidth: "1200px", margin: "0 auto" }}>
      {/* Student Portal Header */}
      <div
        style={{
          background: "linear-gradient(135deg, rgba(6, 182, 212, 0.15) 0%, rgba(99, 102, 241, 0.1) 100%)",
          border: "1px solid rgba(6, 182, 212, 0.3)",
          borderRadius: "16px",
          padding: "24px 28px",
          marginBottom: "24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
        }}
      >
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <span style={{ padding: "4px 10px", borderRadius: "9999px", background: "rgba(6, 182, 212, 0.2)", color: "#22d3ee", fontSize: "0.72rem", fontWeight: "700" }}>
              Student & Candidate Portal
            </span>
          </div>
          <h2 style={{ fontSize: "1.5rem", fontWeight: "800", color: "#f8fafc", marginTop: "6px" }}>
            Welcome to the JASIPA Candidate Portal
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#cbd5e1", marginTop: "4px" }}>
            Apply for open job requisitions, upload your resume for automated parsing, and complete your technical & behavioral assessments.
          </p>
        </div>

        {candidateProfile && (
          <div style={{ textAlign: "right", background: "rgba(15, 23, 42, 0.8)", padding: "12px 18px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.08)" }}>
            <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>Logged in as:</div>
            <div style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc" }}>{candidateProfile.name}</div>
            <div style={{ marginTop: "4px" }}><StageBadge stage={candidateProfile.current_stage} /></div>
          </div>
        )}
      </div>

      {/* 4 Step Navigation Tracker */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "12px", marginBottom: "28px" }}>
        {[
          { id: "resume", step: "Step 1", title: "Job Selection & Resume", done: !!candidateProfile },
          { id: "technical", step: "Step 2", title: "Technical Assessment", done: techSubmitted },
          { id: "behavioral", step: "Step 3", title: "Behavioral STAR Test", done: behSubmitted },
          { id: "status", step: "Step 4", title: "Application Status", done: candidateProfile?.current_stage === "DECIDED" },
        ].map((item) => {
          const isActive = activeStep === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setActiveStep(item.id)}
              style={{
                padding: "14px 16px",
                borderRadius: "10px",
                background: isActive 
                  ? "rgba(99, 102, 241, 0.25)" 
                  : item.done 
                  ? "rgba(16, 185, 129, 0.1)" 
                  : "rgba(15, 23, 42, 0.6)",
                border: isActive 
                  ? "1px solid #6366f1" 
                  : item.done 
                  ? "1px solid rgba(16, 185, 129, 0.3)" 
                  : "1px solid rgba(255, 255, 255, 0.05)",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.2s",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.7rem", color: isActive ? "#818cf8" : item.done ? "#34d399" : "#94a3b8", fontWeight: "700" }}>
                  {item.step}
                </span>
                {item.done && <CheckCircle2 size={15} color="#34d399" />}
              </div>
              <div style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc", marginTop: "4px" }}>
                {item.title}
              </div>
            </button>
          );
        })}
      </div>

      {/* STEP 1: Job Selection & Resume Upload */}
      {activeStep === "resume" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
          <div className="glass-card" style={{ padding: "24px" }}>
            <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
              1. Choose Requisition & Submit Resume
            </h3>

            <form onSubmit={handleApplyAndUpload} style={{ display: "flex", flexDirection: "column", gap: "14px" }}>
              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Select Job Requisition</label>
                <select
                  className="form-select"
                  value={selectedJdId}
                  onChange={(e) => {
                    setSelectedJdId(e.target.value);
                    loadQuestions(e.target.value);
                  }}
                >
                  {jobs.map(j => (
                    <option key={j.jd_id} value={j.jd_id}>
                      {j.title} ({j.department})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Full Name</label>
                <input
                  className="form-input"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Email Address</label>
                <input
                  type="email"
                  className="form-input"
                  required
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Upload PDF Resume (PyMuPDF Parser)</label>
                <input
                  type="file"
                  accept=".pdf"
                  className="form-input"
                  style={{ padding: "8px" }}
                  onChange={(e) => setFormData({ ...formData, file: e.target.files[0] })}
                />
              </div>

              <div>
                <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Or Paste Plaintext Resume</label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  value={formData.resume_text}
                  onChange={(e) => setFormData({ ...formData, resume_text: e.target.value })}
                />
              </div>

              <button type="submit" className="btn btn-primary" disabled={uploading} style={{ marginTop: "8px" }}>
                <Upload size={15} />
                <span>{uploading ? "Ingesting Resume..." : "Submit Application & Proceed to Assessments"}</span>
              </button>
            </form>
          </div>

          {/* Job Overview Card */}
          {selectedJobObj && (
            <div className="glass-card" style={{ padding: "24px" }}>
              <span style={{ fontSize: "0.72rem", color: "#818cf8", fontWeight: "600", textTransform: "uppercase" }}>
                Job Overview
              </span>
              <h3 style={{ fontSize: "1.2rem", fontWeight: "800", color: "#f8fafc", marginTop: "2px" }}>
                {selectedJobObj.title}
              </h3>
              <p style={{ fontSize: "0.82rem", color: "#cbd5e1", marginTop: "10px", lineHeight: "1.5" }}>
                {selectedJobObj.description}
              </p>

              <div style={{ marginTop: "16px" }}>
                <span style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>Required Core Skills:</span>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px", marginTop: "6px" }}>
                  {selectedJobObj.required_skills?.map(s => (
                    <span key={s} style={{ background: "rgba(99, 102, 241, 0.15)", color: "#818cf8", padding: "3px 8px", borderRadius: "6px", fontSize: "0.75rem" }}>
                      {s}
                    </span>
                  ))}
                </div>
              </div>
            </div>
          )}
        </div>
      )}

      {/* STEP 2: Technical Assessment */}
      {activeStep === "technical" && (
        <div className="glass-card" style={{ padding: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
            <Code size={22} color="#6366f1" />
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#f8fafc" }}>
              2. Technical Skill Assessment
            </h3>
          </div>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: "20px" }}>
            Answer the following practical technical questions tailored to the required job skills. The Skill-Assessor Agent evaluates your submitted answers.
          </p>

          <form onSubmit={handleSubmitTechnical} style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {techQuestions.map((q, idx) => (
              <div key={q.question_id} style={{ background: "rgba(15, 23, 42, 0.7)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#818cf8", marginBottom: "6px" }}>
                  Question {idx + 1}: {q.competency_or_skill} ({q.type.toUpperCase()})
                </div>
                <p style={{ fontSize: "0.85rem", color: "#f8fafc", marginBottom: "10px" }}>{q.prompt}</p>

                {q.options && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "6px", marginBottom: "10px" }}>
                    {q.options.map(opt => (
                      <div key={opt} style={{ fontSize: "0.78rem", color: "#cbd5e1" }}>{opt}</div>
                    ))}
                  </div>
                )}

                <textarea
                  className="form-textarea"
                  rows={q.type === "coding" ? 5 : 2}
                  style={{ fontFamily: q.type === "coding" ? "monospace" : "inherit" }}
                  value={techAnswers[q.question_id] || ""}
                  onChange={(e) => setTechAnswers({ ...techAnswers, [q.question_id]: e.target.value })}
                />
              </div>
            ))}

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" className="btn btn-primary" disabled={submittingTech}>
                <span>{submittingTech ? "Submitting..." : "Submit Technical Assessment & Continue"}</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </div>
      )}

      {/* STEP 3: Behavioral STAR Test */}
      {activeStep === "behavioral" && (
        <div className="glass-card" style={{ padding: "28px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "10px" }}>
            <MessageSquare size={22} color="#a855f7" />
            <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#f8fafc" }}>
              3. Standardized Behavioral Assessment (STAR Method)
            </h3>
          </div>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: "20px" }}>
            Describe real past workplace experiences using the STAR method (Situation, Task, Action, Result) across Communication, Teamwork, Problem Solving, and Adaptability.
          </p>

          <form onSubmit={handleSubmitBehavioral} style={{ display: "flex", flexDirection: "column", gap: "18px" }}>
            {behQuestions.map((q, idx) => (
              <div key={q.question_id} style={{ background: "rgba(15, 23, 42, 0.7)", padding: "16px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#c084fc", marginBottom: "6px" }}>
                  Competency {idx + 1}: {q.competency_or_skill}
                </div>
                <p style={{ fontSize: "0.85rem", color: "#f8fafc", marginBottom: "10px" }}>{q.prompt}</p>

                <textarea
                  className="form-textarea"
                  rows={3}
                  value={behAnswers[q.question_id] || ""}
                  onChange={(e) => setBehAnswers({ ...behAnswers, [q.question_id]: e.target.value })}
                />
              </div>
            ))}

            <div style={{ display: "flex", justifyContent: "flex-end" }}>
              <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)" }} disabled={submittingBeh}>
                <span>{submittingBeh ? "Evaluating..." : "Submit Behavioral Assessment & View Status"}</span>
                <ArrowRight size={15} />
              </button>
            </div>
          </form>
        </div>
      )}

      {/* STEP 4: Application Status Tracker */}
      {activeStep === "status" && (
        <div className="glass-card" style={{ padding: "28px" }}>
          <h3 style={{ fontSize: "1.2rem", fontWeight: "700", color: "#f8fafc", marginBottom: "8px" }}>
            4. Application Status & Next Steps
          </h3>
          <p style={{ fontSize: "0.82rem", color: "#94a3b8", marginBottom: "20px" }}>
            Your application and assessments have been received by the JASIPA Multi-Agent System.
          </p>

          <div style={{ padding: "20px", borderRadius: "12px", background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(255, 255, 255, 0.08)", marginBottom: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <div>
                <h4 style={{ fontSize: "1rem", fontWeight: "700", color: "#f8fafc" }}>
                  {candidateProfile?.name || formData.name}
                </h4>
                <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                  Target Requisition: {selectedJobObj?.title || "Software Engineer"}
                </p>
              </div>
              <StageBadge stage={candidateProfile?.current_stage || "HUMAN_REVIEW_PENDING"} />
            </div>

            <div style={{ marginTop: "18px", display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "12px" }}>
              <div style={{ padding: "12px", borderRadius: "8px", background: "rgba(6, 182, 212, 0.1)", border: "1px solid rgba(6, 182, 212, 0.2)" }}>
                <div style={{ fontSize: "0.72rem", color: "#06b6d4" }}>Resume Ingestion</div>
                <div style={{ fontSize: "0.9rem", fontWeight: "700", color: "#34d399", marginTop: "2px" }}>✓ Processed</div>
              </div>

              <div style={{ padding: "12px", borderRadius: "8px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.2)" }}>
                <div style={{ fontSize: "0.72rem", color: "#818cf8" }}>Technical Assessment</div>
                <div style={{ fontSize: "0.9rem", fontWeight: "700", color: "#34d399", marginTop: "2px" }}>✓ Submitted</div>
              </div>

              <div style={{ padding: "12px", borderRadius: "8px", background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.2)" }}>
                <div style={{ fontSize: "0.72rem", color: "#c084fc" }}>Behavioral STAR Test</div>
                <div style={{ fontSize: "0.9rem", fontWeight: "700", color: "#34d399", marginTop: "2px" }}>✓ Submitted</div>
              </div>
            </div>
          </div>

          <div style={{ padding: "16px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.12)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
            <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#34d399" }}>
              Next Step: Human Reviewer Evaluation
            </h4>
            <p style={{ fontSize: "0.78rem", color: "#cbd5e1", marginTop: "4px" }}>
              Your assessment dossier has entered the Human Review Queue. The hiring team will review all evidence and contact you with next steps.
            </p>
          </div>
        </div>
      )}
    </div>
  );
}
