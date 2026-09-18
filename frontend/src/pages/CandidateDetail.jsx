import React, { useState, useEffect } from "react";
import {
  FileText, CheckCircle2, AlertTriangle, ShieldCheck, Scale, ArrowLeft,
  Play, Bot, User, Award, ListChecks, HelpCircle, RefreshCw
} from "lucide-react";
import { getCandidate, getJob, runScreenResume, runPanelSynthesis, runFullGraph } from "../services/api";
import StageBadge from "../components/StageBadge";
import ScoreRadar from "../components/ScoreRadar";
import BiasAlertBanner from "../components/BiasAlertBanner";
import AuditTimeline from "../components/AuditTimeline";

export default function CandidateDetail({ candidateId, setActivePage, setSelectedCandidateId }) {
  const [candidate, setCandidate] = useState(null);
  const [targetJob, setTargetJob] = useState(null);
  const [activeTab, setActiveTab] = useState("overview");
  const [runningAction, setRunningAction] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (candidateId) {
      loadDetails();
    }
  }, [candidateId]);

  async function loadDetails() {
    try {
      const data = await getCandidate(candidateId);
      setCandidate(data);
      if (data.target_jd_id) {
        const j = await getJob(data.target_jd_id);
        setTargetJob(j);
      }
    } catch (err) {
      console.error("Error loading candidate:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleRunScreening() {
    setRunningAction(true);
    try {
      await runScreenResume(candidate.candidate_id, candidate.target_jd_id);
      await loadDetails();
      setActiveTab("screening");
    } catch (err) {
      alert("Screening run failed: " + err.message);
    } finally {
      setRunningAction(false);
    }
  }

  async function handleRunPanel() {
    setRunningAction(true);
    try {
      await runPanelSynthesis(candidate.candidate_id, candidate.target_jd_id);
      await loadDetails();
      setActiveTab("panel");
    } catch (err) {
      alert("Panel run failed: " + err.message);
    } finally {
      setRunningAction(false);
    }
  }

  async function handleRunFullGraph() {
    setRunningAction(true);
    try {
      await runFullGraph(candidate.candidate_id, candidate.target_jd_id);
      await loadDetails();
      setActiveTab("panel");
    } catch (err) {
      alert("LangGraph full pipeline run failed: " + err.message);
    } finally {
      setRunningAction(false);
    }
  }

  if (loading || !candidate) {
    return (
      <div style={{ padding: "40px", textAlign: "center", color: "#94a3b8" }}>
        Loading candidate dossier...
      </div>
    );
  }

  const latestScreening = candidate.screening_results?.[candidate.screening_results.length - 1];
  const techAssessment = candidate.assessments?.find(a => a.test_type === "TECHNICAL");
  const behAssessment = candidate.assessments?.find(a => a.test_type === "BEHAVIORAL");
  const latestPanel = candidate.panel_decisions?.[candidate.panel_decisions.length - 1];
  const latestBias = candidate.bias_checks?.[candidate.bias_checks.length - 1];
  const latestReview = candidate.human_reviews?.[candidate.human_reviews.length - 1];

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Back Button & Header */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px", marginBottom: "20px" }}>
        <button
          onClick={() => setActivePage("candidates")}
          className="btn btn-secondary"
          style={{ padding: "8px 12px" }}
        >
          <ArrowLeft size={16} />
          <span>Back to Candidates</span>
        </button>

        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
              {candidate.name}
            </h2>
            <StageBadge stage={candidate.current_stage} />
            <span style={{ fontSize: "0.75rem", color: "#94a3b8", background: "rgba(255, 255, 255, 0.05)", padding: "2px 8px", borderRadius: "6px" }}>
              {candidate.cohort_tag || "General Cohort"}
            </span>
          </div>
          <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
            {candidate.email} • Target: <span style={{ color: "#38bdf8", fontWeight: "600" }}>{targetJob?.title || candidate.target_jd_id || "Not assigned"}</span> • {candidate.experience_years} yrs exp
          </p>
        </div>
      </div>

      {/* Action Pipeline Control Bar */}
      <div
        className="glass-card"
        style={{
          padding: "14px 20px",
          marginBottom: "24px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <span style={{ fontSize: "0.8rem", color: "#94a3b8", fontWeight: "600" }}>Agent Actions:</span>
          
          <button
            onClick={handleRunScreening}
            disabled={runningAction}
            className="btn btn-secondary"
            style={{ fontSize: "0.78rem", padding: "6px 14px" }}
          >
            <Bot size={14} />
            <span>Screen Resume</span>
          </button>

          <button
            onClick={() => setActivePage("assessments")}
            className="btn btn-secondary"
            style={{ fontSize: "0.78rem", padding: "6px 14px" }}
          >
            <ListChecks size={14} />
            <span>Interactive Assessment Room</span>
          </button>

          <button
            onClick={handleRunPanel}
            disabled={runningAction}
            className="btn btn-secondary"
            style={{ fontSize: "0.78rem", padding: "6px 14px" }}
          >
            <Scale size={14} />
            <span>Run Panel Synthesis & Bias Check</span>
          </button>
        </div>

        <button
          onClick={handleRunFullGraph}
          disabled={runningAction}
          className="btn btn-primary"
          style={{ fontSize: "0.8rem", padding: "8px 16px" }}
        >
          <Play size={15} />
          <span>{runningAction ? "Executing LangGraph..." : "Run End-to-End Orchestrator"}</span>
        </button>
      </div>

      {/* Bias Alert Banner if exists */}
      <BiasAlertBanner biasCheck={latestBias} />

      {/* Tabs Bar */}
      <div
        style={{
          display: "flex",
          gap: "8px",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          marginBottom: "20px",
          paddingBottom: "8px",
          overflowX: "auto",
        }}
      >
        {[
          { id: "overview", label: "Executive Synthesis" },
          { id: "screening", label: "1. Resume Screener" },
          { id: "technical", label: "2. Skill Assessor" },
          { id: "behavioral", label: "3. Culture-Fit Agent" },
          { id: "panel", label: "4. Panel Coordinator & Bias" },
          { id: "review", label: "5. Human Review & Decision" },
          { id: "audit", label: "6. Candidate Memory & Audit" },
        ].map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "8px 16px",
              borderRadius: "8px",
              fontSize: "0.82rem",
              fontWeight: activeTab === tab.id ? "700" : "500",
              color: activeTab === tab.id ? "#fff" : "#94a3b8",
              background: activeTab === tab.id ? "rgba(99, 102, 241, 0.25)" : "transparent",
              border: activeTab === tab.id ? "1px solid rgba(99, 102, 241, 0.4)" : "1px solid transparent",
              cursor: "pointer",
              transition: "all 0.2s",
              whiteSpace: "nowrap",
            }}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content 1: Executive Overview */}
      {activeTab === "overview" && (
        <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            {/* Score Radar */}
            <ScoreRadar
              resumeScore={latestScreening?.score || 0}
              skillScore={techAssessment?.score || 0}
              cultureScore={behAssessment?.score || 0}
              mergedScore={latestPanel?.merged_score || 0}
            />

            {/* Panel Recommendation Highlights */}
            {latestPanel && (
              <div className="glass-card" style={{ padding: "20px" }}>
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "14px" }}>
                  <h3 style={{ fontSize: "1rem", fontWeight: "700", color: "#f8fafc" }}>
                    Panel Recommendation
                  </h3>
                  <span
                    style={{
                      padding: "4px 12px",
                      borderRadius: "9999px",
                      background: "rgba(99, 102, 241, 0.2)",
                      color: "#818cf8",
                      fontWeight: "700",
                      fontSize: "0.75rem",
                    }}
                  >
                    {latestPanel.recommendation}
                  </span>
                </div>

                <div style={{ marginBottom: "12px" }}>
                  <h4 style={{ fontSize: "0.8rem", color: "#34d399", fontWeight: "700", marginBottom: "4px" }}>
                    Key Strengths:
                  </h4>
                  <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                    {latestPanel.strengths?.map((s, idx) => (
                      <li key={idx}>{s}</li>
                    ))}
                  </ul>
                </div>

                {latestPanel.gaps?.length > 0 && (
                  <div style={{ marginBottom: "12px" }}>
                    <h4 style={{ fontSize: "0.8rem", color: "#fb7185", fontWeight: "700", marginBottom: "4px" }}>
                      Identified Gaps:
                    </h4>
                    <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                      {latestPanel.gaps?.map((g, idx) => (
                        <li key={idx}>{g}</li>
                      ))}
                    </ul>
                  </div>
                )}

                {latestPanel.disagreements?.length > 0 && (
                  <div>
                    <h4 style={{ fontSize: "0.8rem", color: "#fbbf24", fontWeight: "700", marginBottom: "4px" }}>
                      Agent Perspective Divergence:
                    </h4>
                    <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                      {latestPanel.disagreements?.map((d, idx) => (
                        <li key={idx}>{d}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right Column: Resume Preview & Quick Info */}
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="glass-card" style={{ padding: "20px" }}>
              <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "10px" }}>
                Resume Extracted Content
              </h3>
              <div
                style={{
                  background: "rgba(15, 23, 42, 0.8)",
                  padding: "14px",
                  borderRadius: "8px",
                  fontSize: "0.78rem",
                  color: "#cbd5e1",
                  maxHeight: "300px",
                  overflowY: "auto",
                  lineHeight: "1.6",
                  whiteSpace: "pre-wrap",
                }}
              >
                {candidate.resume_text || "No resume text extracted."}
              </div>
            </div>

            {latestReview && (
              <div
                className="glass-card"
                style={{
                  padding: "20px",
                  background: "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(15, 23, 42, 0.8) 100%)",
                  border: "1px solid rgba(16, 185, 129, 0.3)",
                }}
              >
                <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                  <h4 style={{ fontSize: "0.9rem", fontWeight: "700", color: "#34d399" }}>
                    Human Decision: {latestReview.decision}
                  </h4>
                  <span style={{ fontSize: "0.7rem", color: "#94a3b8" }}>
                    {new Date(latestReview.timestamp).toLocaleDateString()}
                  </span>
                </div>
                <p style={{ fontSize: "0.8rem", color: "#f8fafc", marginTop: "8px" }}>
                  "{latestReview.notes}"
                </p>
                <p style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "6px" }}>
                  Signed by: {latestReview.reviewer_name}
                </p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Tab 2: Resume Screening Agent Details */}
      {activeTab === "screening" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
            Resume-Screener Agent Evaluation
          </h3>

          {!latestScreening ? (
            <div style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
              Resume screening has not been executed yet. Click "Screen Resume" above.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ padding: "14px 20px", borderRadius: "10px", background: "rgba(6, 182, 212, 0.1)", border: "1px solid rgba(6, 182, 212, 0.3)" }}>
                  <div style={{ fontSize: "0.72rem", color: "#06b6d4", fontWeight: "600" }}>Resume Fit Score</div>
                  <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#f8fafc" }}>
                    {latestScreening.score}/100
                  </div>
                </div>

                <div style={{ flex: 1 }}>
                  <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Status: <span style={{ color: "#34d399", fontWeight: "600" }}>{latestScreening.status}</span> • Rubric v{latestScreening.rubric_version}
                  </div>
                  <div style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "4px" }}>
                    Experience Requirement Match: <span style={{ color: latestScreening.experience_match ? "#34d399" : "#fbbf24", fontWeight: "600" }}>{latestScreening.experience_match ? "Satisfied" : "Below Baseline"}</span>
                  </div>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#34d399", fontWeight: "700", marginBottom: "6px" }}>
                  Matched JD Requirements:
                </h4>
                <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                  {latestScreening.matched_requirements?.map((m) => (
                    <span key={m} style={{ background: "rgba(16, 185, 129, 0.15)", color: "#34d399", padding: "3px 10px", borderRadius: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                      ✓ {m}
                    </span>
                  ))}
                </div>
              </div>

              {latestScreening.missing_requirements?.length > 0 && (
                <div>
                  <h4 style={{ fontSize: "0.85rem", color: "#fb7185", fontWeight: "700", marginBottom: "6px" }}>
                    Missing JD Requirements:
                  </h4>
                  <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
                    {latestScreening.missing_requirements.map((m) => (
                      <span key={m} style={{ background: "rgba(244, 63, 94, 0.15)", color: "#fb7185", padding: "3px 10px", borderRadius: "6px", fontSize: "0.75rem", fontWeight: "600" }}>
                        ✗ {m}
                      </span>
                    ))}
                  </div>
                </div>
              )}

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#38bdf8", fontWeight: "700", marginBottom: "6px" }}>
                  Extracted Evidence Citations:
                </h4>
                <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1", display: "flex", flexDirection: "column", gap: "4px" }}>
                  {latestScreening.evidence?.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 3: Technical Skill Assessor Details */}
      {activeTab === "technical" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
            Skill-Assessor Agent (Demonstrated Technical Assessment)
          </h3>

          {!techAssessment ? (
            <div style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
              Technical assessment has not been completed. Go to "Assessment Room" to submit candidate answers.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ padding: "14px 20px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.1)", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
                  <div style={{ fontSize: "0.72rem", color: "#818cf8", fontWeight: "600" }}>Demonstrated Score</div>
                  <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#f8fafc" }}>
                    {techAssessment.score}/100
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Status: <span style={{ color: "#34d399", fontWeight: "600" }}>{techAssessment.status}</span> • Confidence: {(techAssessment.confidence * 100).toFixed(0)}%
                  </div>
                  <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>
                    Evaluated against actual MCQ choices, SQL syntax, and graph algorithm complexity.
                  </p>
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#818cf8", fontWeight: "700", marginBottom: "6px" }}>
                  Skill Breakdown Scores:
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "10px" }}>
                  {Object.entries(techAssessment.skill_breakdown || {}).map(([skill, val]) => (
                    <div key={skill} style={{ padding: "10px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                      <div style={{ fontSize: "0.75rem", color: "#cbd5e1" }}>{skill}</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: "700", color: val >= 80 ? "#10b981" : "#f59e0b" }}>
                        {val}/100
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#38bdf8", fontWeight: "700", marginBottom: "6px" }}>
                  Demonstrated Technical Evidence:
                </h4>
                <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                  {techAssessment.evidence?.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 4: Standardized Behavioral Assessment */}
      {activeTab === "behavioral" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
            Culture-Fit Agent (Standardized STAR Behavioral Assessment)
          </h3>

          {!behAssessment ? (
            <div style={{ textAlign: "center", padding: "30px", color: "#64748b" }}>
              Behavioral assessment not yet submitted.
            </div>
          ) : (
            <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "20px" }}>
                <div style={{ padding: "14px 20px", borderRadius: "10px", background: "rgba(168, 85, 247, 0.1)", border: "1px solid rgba(168, 85, 247, 0.3)" }}>
                  <div style={{ fontSize: "0.72rem", color: "#c084fc", fontWeight: "600" }}>Behavioral STAR Score</div>
                  <div style={{ fontSize: "1.8rem", fontWeight: "800", color: "#f8fafc" }}>
                    {behAssessment.score}/100
                  </div>
                </div>

                <div>
                  <div style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                    Status: <span style={{ color: behAssessment.status === "COMPLETED" ? "#34d399" : "#fb7185", fontWeight: "600" }}>{behAssessment.status}</span>
                  </div>
                  <p style={{ fontSize: "0.75rem", color: "#94a3b8", marginTop: "4px" }}>
                    Standardized questions only. Zero inference from demographic traits or resume fluff.
                  </p>
                </div>
              </div>

              {behAssessment.status === "INSUFFICIENT_EVIDENCE" && (
                <div style={{ padding: "12px 16px", borderRadius: "8px", background: "rgba(244, 63, 94, 0.15)", border: "1px solid rgba(244, 63, 94, 0.3)", color: "#fb7185", fontSize: "0.8rem" }}>
                  <strong>INSUFFICIENT_EVIDENCE Triggered:</strong> Candidate responses were too brief to evaluate competencies reliably. Requires human interviewer follow-up inquiry.
                </div>
              )}

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#c084fc", fontWeight: "700", marginBottom: "6px" }}>
                  Competency Breakdown:
                </h4>
                <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "10px" }}>
                  {Object.entries(behAssessment.skill_breakdown || {}).map(([comp, val]) => (
                    <div key={comp} style={{ padding: "10px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                      <div style={{ fontSize: "0.75rem", color: "#cbd5e1", textTransform: "capitalize" }}>{comp}</div>
                      <div style={{ fontSize: "1.1rem", fontWeight: "700", color: val >= 75 ? "#34d399" : "#fbbf24" }}>
                        {val}/100
                      </div>
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <h4 style={{ fontSize: "0.85rem", color: "#38bdf8", fontWeight: "700", marginBottom: "6px" }}>
                  Behavioral STAR Evidence:
                </h4>
                <ul style={{ paddingLeft: "18px", fontSize: "0.8rem", color: "#cbd5e1" }}>
                  {behAssessment.evidence?.map((ev, idx) => (
                    <li key={idx}>{ev}</li>
                  ))}
                </ul>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tab 5: Panel Coordinator & Bias Check */}
      {activeTab === "panel" && (
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {latestPanel && (
            <div className="glass-card" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
                Panel Coordinator Merged Synthesis
              </h3>
              
              <ScoreRadar
                resumeScore={latestPanel.resume_score}
                skillScore={latestPanel.skill_score}
                cultureScore={latestPanel.culture_score}
                mergedScore={latestPanel.merged_score}
              />

              <div style={{ marginTop: "16px", display: "flex", flexDirection: "column", gap: "10px" }}>
                <div style={{ padding: "12px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)" }}>
                  <div style={{ fontSize: "0.8rem", color: "#38bdf8", fontWeight: "700" }}>Recommendation:</div>
                  <div style={{ fontSize: "1rem", fontWeight: "800", color: "#f8fafc" }}>
                    {latestPanel.recommendation}
                  </div>
                </div>
              </div>
            </div>
          )}

          {latestBias && (
            <div className="glass-card" style={{ padding: "24px" }}>
              <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
                Bias Checker Audit Record
              </h3>
              <BiasAlertBanner biasCheck={latestBias} />
            </div>
          )}
        </div>
      )}

      {/* Tab 6: Human Review Decision */}
      {activeTab === "review" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "14px" }}>
            Authenticated Human Review Decision
          </h3>

          {latestReview ? (
            <div style={{ padding: "16px", borderRadius: "10px", background: "rgba(16, 185, 129, 0.1)", border: "1px solid rgba(16, 185, 129, 0.3)" }}>
              <h4 style={{ fontSize: "1rem", fontWeight: "800", color: "#34d399" }}>
                Decision: {latestReview.decision}
              </h4>
              <p style={{ fontSize: "0.85rem", color: "#f8fafc", marginTop: "6px" }}>
                "{latestReview.notes}"
              </p>
              <div style={{ fontSize: "0.72rem", color: "#94a3b8", marginTop: "10px" }}>
                Reviewer: {latestReview.reviewer_name} ({latestReview.reviewer_id}) • {new Date(latestReview.timestamp).toLocaleString()}
              </div>
            </div>
          ) : (
            <div style={{ textAlign: "center", padding: "30px" }}>
              <p style={{ color: "#fbbf24", fontSize: "0.9rem", fontWeight: "600", marginBottom: "14px" }}>
                This candidate is awaiting human review. Go to the Human Review Station to review complete evidence and submit the final decision.
              </p>
              <button
                onClick={() => setActivePage("reviews")}
                className="btn btn-primary"
                style={{ padding: "8px 18px" }}
              >
                Open Human Review Station
              </button>
            </div>
          )}
        </div>
      )}

      {/* Tab 7: Candidate Memory & Audit Log */}
      {activeTab === "audit" && (
        <div className="glass-card" style={{ padding: "24px" }}>
          <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "16px" }}>
            Candidate Immutable Audit Trail
          </h3>
          <AuditTimeline timeline={candidate.audit_logs} />
        </div>
      )}
    </div>
  );
}
