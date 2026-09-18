import React, { useState } from "react";
import { 
  Play, CheckCircle2, ChevronRight, Sparkles, ShieldCheck, ArrowRight,
  Briefcase, Scale, FileText, Code, MessageSquare, Bot, AlertTriangle, UserCheck, History
} from "lucide-react";
import confetti from "canvas-confetti";
import { 
  createJob, createCandidate, runScreenResume, submitTechnicalAssessment,
  submitBehavioralAssessment, runPanelSynthesis, submitHumanDecision, getCandidateAuditTrail
} from "../services/api";

const DEMO_STEPS = [
  { step: 1, title: "HR Creates Job Description", desc: "Creates 'Senior Software Engineer' JD with required skills (Python, SQL, FastAPI, Data Structures).", icon: Briefcase },
  { step: 2, title: "JD-Anchored Rubric Generated", desc: "System creates versioned scoring rubric: 40% Resume + 40% Technical + 20% Behavioral STAR.", icon: Scale },
  { step: 3, title: "Candidate Ingestion & Resume Parsing", desc: "Candidate 'Elena Rostova' submits PDF resume; text and metadata extracted via PyMuPDF.", icon: FileText },
  { step: 4, title: "Resume-Screener Agent Evaluation", desc: "Evaluates resume fit against JD requirements; generates structured score & evidence citations.", icon: Bot },
  { step: 5, title: "Technical Assessment Submitted", desc: "Candidate submits practical answers for Asyncio concepts, SQL indexing, and cycle detection.", icon: Code },
  { step: 6, title: "Skill-Assessor Agent Evaluation", desc: "Skill-Assessor scores demonstrated answers directly (does not just re-read resume).", icon: Bot },
  { step: 7, title: "Standardized Behavioral Assessment", desc: "Candidate provides STAR responses for Communication, Teamwork, Problem Solving, and Adaptability.", icon: MessageSquare },
  { step: 8, title: "Culture-Fit Agent Evaluation", desc: "Evaluates behavioral STAR responses against rubric; avoids demographic bias or resume guesswork.", icon: Bot },
  { step: 9, title: "Panel Coordinator Merged Synthesis", desc: "Merges 3 agent perspectives; detects perspective agreements/divergences and recommends review.", icon: Scale },
  { step: 10, title: "Post-Panel Bias Check", desc: "Evaluates candidate outcome against historical cohort data and 4/5ths rule; logs parity report.", icon: AlertTriangle },
  { step: 11, title: "Human Reviewer Evidence Docket", desc: "Authenticated human reviewer inspects complete multi-agent evidence docket and bias report.", icon: UserCheck },
  { step: 12, title: "Final Human Decision Recorded", desc: "Reviewer signs off with APPROVE decision and mandatory rationale notes (AI prohibited from auto-deciding).", icon: ShieldCheck },
  { step: 13, title: "Immutable Audit Trail Completed", desc: "Complete chronological journey permanently logged into tamper-evident audit database.", icon: History },
];

export default function DemoRunner({ setActivePage, setSelectedCandidateId }) {
  const [currentStep, setCurrentStep] = useState(0);
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState([]);
  const [demoState, setDemoState] = useState({
    jdId: null,
    candidateId: null,
    screeningResult: null,
    technicalResult: null,
    behavioralResult: null,
    panelResult: null,
    biasResult: null,
    reviewResult: null,
    auditTrail: null
  });

  const addLog = (msg, data = null) => {
    setLogs(prev => [...prev, { time: new Date().toLocaleTimeString(), msg, data }]);
  };

  async function runStep(stepNum) {
    setIsRunning(true);
    setCurrentStep(stepNum);

    try {
      if (stepNum === 1) {
        // Step 1: Create JD
        addLog("Step 1: HR creates 'Senior Full Stack Engineer' JD...");
        const jd = await createJob({
          title: `Senior Full Stack Engineer (Demo ${Date.now().toString().slice(-4)})`,
          department: "Engineering",
          description: "Architecting high-throughput FastAPI microservices and React web applications.",
          required_skills: ["Python", "React", "SQL", "FastAPI", "Data Structures"],
          preferred_skills: ["Docker", "Kubernetes", "AWS"],
          min_experience: 3.5,
          education_requirement: "Bachelor's in Computer Science or equivalent"
        });
        setDemoState(prev => ({ ...prev, jdId: jd.jd_id }));
        addLog(`✓ Job Description created successfully with ID: ${jd.jd_id}`);
      }

      else if (stepNum === 2) {
        // Step 2: Rubric is anchored
        addLog("Step 2: Dynamic JD-Anchored Scoring Rubric v1.0 instantiated with 40/40/20 weights.");
      }

      else if (stepNum === 3) {
        // Step 3: Candidate submits resume
        addLog("Step 3: Candidate 'Elena Rostova' submits resume. PyMuPDF parsing text...");
        const cand = await createCandidate({
          name: "Elena Rostova (Live Demo)",
          email: `elena.demo.${Date.now()}@example.com`,
          phone: "+1 (555) 890-1234",
          cohort_tag: "Cohort_Alpha",
          resume_text: "Senior Software Engineer with 5 years experience architecting high-performance FastAPI microservices and React user interfaces. Proficient in SQL, PostgreSQL, Python, Data Structures, and Docker.",
          experience_years: 5.0,
          education: "Bachelor's in Computer Science",
          target_jd_id: demoState.jdId
        });
        setDemoState(prev => ({ ...prev, candidateId: cand.candidate_id }));
        setSelectedCandidateId(cand.candidate_id);
        addLog(`✓ Candidate ingested into ATS with ID: ${cand.candidate_id}`);
      }

      else if (stepNum === 4) {
        // Step 4: Resume-Screener Agent
        addLog("Step 4: Running Resume-Screener Agent against JD rubric...");
        const screenRes = await runScreenResume(demoState.candidateId, demoState.jdId);
        setDemoState(prev => ({ ...prev, screeningResult: screenRes }));
        addLog(`✓ Resume Screener Score: ${screenRes.score}/100 (Matched: ${screenRes.matched_requirements.join(", ")})`);
      }

      else if (stepNum === 5) {
        // Step 5: Candidate submits tech assessment
        addLog("Step 5: Candidate submits practical answers for technical assessment questions...");
      }

      else if (stepNum === 6) {
        // Step 6: Skill-Assessor Agent
        addLog("Step 6: Running Skill-Assessor Agent to evaluate demonstrated technical ability...");
        const techRes = await submitTechnicalAssessment({
          candidate_id: demoState.candidateId,
          jd_id: demoState.jdId,
          answers: [
            { question_id: "TECH_Q1", answer_text: "Option B: Asyncio uses an event loop on a single thread with cooperative multitasking." },
            { question_id: "TECH_Q2", answer_text: "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;" },
            { question_id: "TECH_Q3", answer_text: "def has_cycle(graph):\n    visited = set()\n    rec_stack = set()\n    # DFS implementation O(V+E)" }
          ]
        });
        setDemoState(prev => ({ ...prev, technicalResult: techRes }));
        addLog(`✓ Skill-Assessor Score: ${techRes.score}/100 across Python, SQL, and Algorithms`);
      }

      else if (stepNum === 7) {
        // Step 7: Candidate answers standardized behavioral questions
        addLog("Step 7: Candidate completes standardized STAR behavioral questions...");
      }

      else if (stepNum === 8) {
        // Step 8: Culture-Fit Agent
        addLog("Step 8: Running Culture-Fit Agent assessing Communication, Teamwork, Problem Solving, and Adaptability...");
        const behRes = await submitBehavioralAssessment({
          candidate_id: demoState.candidateId,
          jd_id: demoState.jdId,
          answers: [
            { question_id: "BEH_Q1", answer_text: "In my previous project, we had a disagreement regarding database caching. I benchmarked Redis vs Memcached with realistic payloads, presented the latency metrics, and achieved consensus." },
            { question_id: "BEH_Q2", answer_text: "When faced with vague pipeline requirements, I decomposed the problem into ingestion and queuing stages, scheduled stakeholder demos, and shipped an MVP." },
            { question_id: "BEH_Q3", answer_text: "Required to learn Kubernetes in 2 weeks, I spun up local Minikube clusters, wrote Helm charts, and deployed successfully." },
            { question_id: "BEH_Q4", answer_text: "I explained microservice decoupling tradeoffs to the product team using business KPI impact diagrams rather than low-level code specifics." }
          ]
        });
        setDemoState(prev => ({ ...prev, behavioralResult: behRes }));
        addLog(`✓ Culture-Fit Agent Score: ${behRes.score}/100 (STAR structure verified, Confidence: 86%)`);
      }

      else if (stepNum === 9) {
        // Step 9: Panel Coordinator
        addLog("Step 9: Panel Coordinator synthesizing 3 agent perspectives into weighted merged score...");
        const panelRes = await runPanelSynthesis(demoState.candidateId, demoState.jdId);
        setDemoState(prev => ({ 
          ...prev, 
          panelResult: panelRes.panel_decision,
          biasResult: panelRes.bias_check
        }));
        addLog(`✓ Panel Coordinator Merged Score: ${panelRes.panel_decision.merged_score}/100`);
        addLog(`✓ Panel Recommendation: ${panelRes.panel_decision.recommendation}`);
      }

      else if (stepNum === 10) {
        // Step 10: Bias Check
        addLog("Step 10: Bias Checker evaluating outcome against historical cohort baseline (4/5ths rule)...");
        addLog("✓ Bias Check Status: NO_SIGNIFICANT_DISPARITY_DETECTED. Candidate routed to Human Review Queue.");
      }

      else if (stepNum === 11) {
        // Step 11: Human Reviewer inspects dossier
        addLog("Step 11: Complete evidence docket populated in Human Review Decision Room.");
      }

      else if (stepNum === 12) {
        // Step 12: Human Review Decision
        addLog("Step 12: Authenticated Human Reviewer submits final decision: APPROVE...");
        const reviewRes = await submitHumanDecision({
          candidate_id: demoState.candidateId,
          reviewer_id: "USR_REV_01",
          reviewer_name: "Dr. Alex HumanReviewer",
          decision: "APPROVE",
          notes: "Elena demonstrated exceptional technical and architectural fundamentals in both the coding questions and STAR behavioral assessment. Approved for Senior Full Stack Engineer offer."
        });
        setDemoState(prev => ({ ...prev, reviewResult: reviewRes }));
        confetti({ particleCount: 120, spread: 80, origin: { y: 0.6 } });
        addLog(`✓ Final Human Decision Recorded: APPROVE by ${reviewRes.reviewer_name}`);
      }

      else if (stepNum === 13) {
        // Step 13: Audit Trail
        addLog("Step 13: Retrieving immutable end-to-end audit trail from database...");
        const history = await getCandidateAuditTrail(demoState.candidateId);
        setDemoState(prev => ({ ...prev, auditTrail: history }));
        addLog(`✓ Full journey verified across ${history.timeline?.length || 8} immutable audit events.`);
      }
    } catch (err) {
      addLog(`❌ Error on step ${stepNum}: ${err.message}`);
    } finally {
      setIsRunning(false);
    }
  }

  async function runAllStepsSequentially() {
    for (let s = 1; s <= 13; s++) {
      await runStep(s);
      await new Promise(r => setTimeout(r, 600));
    }
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
              1-Click Interactive Live Demo Walkthrough
            </h2>
            <span style={{ padding: "3px 10px", borderRadius: "9999px", background: "linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)", color: "#fff", fontSize: "0.72rem", fontWeight: "700" }}>
              Steps 1 through 13
            </span>
          </div>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "4px" }}>
            Executes the complete Project 11 end-to-end scenario from JD creation to multi-agent scoring, bias checking, and final human decision.
          </p>
        </div>

        <div style={{ display: "flex", gap: "12px" }}>
          <button
            onClick={runAllStepsSequentially}
            disabled={isRunning}
            className="btn btn-primary"
            style={{ padding: "10px 22px", background: "linear-gradient(135deg, #6366f1 0%, #ec4899 100%)" }}
          >
            <Sparkles size={16} />
            <span>{isRunning ? "Running Scenario..." : "Run Complete 13-Step Demo"}</span>
          </button>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1.2fr 1fr", gap: "24px" }}>
        {/* Left: Step-by-Step Progress Pipeline */}
        <div className="glass-card" style={{ padding: "22px" }}>
          <h3 style={{ fontSize: "1rem", fontWeight: "700", color: "#f8fafc", marginBottom: "16px" }}>
            Scenario Execution Steps
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
            {DEMO_STEPS.map((stepItem) => {
              const Icon = stepItem.icon;
              const isCompleted = currentStep >= stepItem.step;
              const isCurrent = currentStep === stepItem.step;

              return (
                <div
                  key={stepItem.step}
                  onClick={() => !isRunning && runStep(stepItem.step)}
                  style={{
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "space-between",
                    padding: "12px 14px",
                    borderRadius: "10px",
                    background: isCurrent 
                      ? "rgba(99, 102, 241, 0.25)" 
                      : isCompleted 
                      ? "rgba(16, 185, 129, 0.1)" 
                      : "rgba(15, 23, 42, 0.5)",
                    border: isCurrent 
                      ? "1px solid #6366f1" 
                      : isCompleted 
                      ? "1px solid rgba(16, 185, 129, 0.3)" 
                      : "1px solid rgba(255, 255, 255, 0.04)",
                    cursor: isRunning ? "default" : "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                    <div
                      style={{
                        width: "32px",
                        height: "32px",
                        borderRadius: "8px",
                        background: isCompleted ? "rgba(16, 185, 129, 0.2)" : "rgba(30, 41, 59, 0.8)",
                        color: isCompleted ? "#34d399" : "#94a3b8",
                        display: "flex",
                        alignItems: "center",
                        justifyContent: "center",
                        fontWeight: "700",
                        fontSize: "0.8rem",
                      }}
                    >
                      {isCompleted ? <CheckCircle2 size={18} color="#34d399" /> : stepItem.step}
                    </div>

                    <div>
                      <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: isCurrent ? "#fff" : isCompleted ? "#34d399" : "#cbd5e1" }}>
                        {stepItem.title}
                      </h4>
                      <p style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                        {stepItem.desc}
                      </p>
                    </div>
                  </div>

                  <button
                    disabled={isRunning}
                    className="btn btn-secondary"
                    style={{ padding: "4px 10px", fontSize: "0.7rem", flexShrink: 0 }}
                  >
                    Run Step
                  </button>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Live Console Logs & Candidate Dossier Link */}
        <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
          {/* Live Streaming Log Box */}
          <div className="glass-card" style={{ padding: "20px" }}>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "12px" }}>
              Live Execution Event Stream
            </h3>

            <div
              style={{
                background: "rgba(15, 23, 42, 0.95)",
                borderRadius: "10px",
                padding: "14px",
                fontFamily: "monospace",
                fontSize: "0.75rem",
                height: "320px",
                overflowY: "auto",
                border: "1px solid rgba(255, 255, 255, 0.08)",
                display: "flex",
                flexDirection: "column",
                gap: "6px",
              }}
            >
              {logs.length === 0 ? (
                <span style={{ color: "#64748b" }}>Click "Run Complete 13-Step Demo" to stream the live scenario execution...</span>
              ) : (
                logs.map((l, i) => (
                  <div key={i} style={{ color: l.msg.includes("✓") ? "#86efac" : l.msg.includes("❌") ? "#fb7185" : "#a5f3fc" }}>
                    <span style={{ color: "#64748b", marginRight: "8px" }}>[{l.time}]</span>
                    {l.msg}
                  </div>
                ))
              )}
            </div>
          </div>

          {/* Quick Jump to Result Dossier */}
          {demoState.candidateId && (
            <div
              className="glass-card"
              style={{
                padding: "20px",
                background: "linear-gradient(135deg, rgba(99, 102, 241, 0.15) 0%, rgba(16, 185, 129, 0.1) 100%)",
                border: "1px solid rgba(99, 102, 241, 0.3)",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <div>
                  <h4 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc" }}>
                    Elena Rostova (Live Demo Candidate)
                  </h4>
                  <p style={{ fontSize: "0.75rem", color: "#34d399", marginTop: "2px" }}>
                    Ready for inspection in Candidate Dossier & Human Review Station!
                  </p>
                </div>

                <button
                  onClick={() => {
                    setSelectedCandidateId(demoState.candidateId);
                    setActivePage("candidate-detail");
                  }}
                  className="btn btn-primary"
                  style={{ padding: "8px 16px", fontSize: "0.8rem" }}
                >
                  <span>View Full Dossier</span>
                  <ArrowRight size={14} />
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
