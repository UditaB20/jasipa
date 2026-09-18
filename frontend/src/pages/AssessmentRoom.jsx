import React, { useState, useEffect } from "react";
import { ListChecks, Code, MessageSquare, CheckCircle, ArrowRight, Play, Sparkles } from "lucide-react";
import { 
  getCandidates, getJobs, getTechnicalQuestions, getBehavioralQuestions,
  submitTechnicalAssessment, submitBehavioralAssessment
} from "../services/api";

export default function AssessmentRoom({ selectedCandidateId, setSelectedCandidateId, setActivePage }) {
  const [candidates, setCandidates] = useState([]);
  const [jobs, setJobs] = useState([]);
  const [selectedCandidate, setSelectedCandidate] = useState(null);
  const [techQuestions, setTechQuestions] = useState([]);
  const [behQuestions, setBehQuestions] = useState([]);
  
  // Answers state
  const [techAnswers, setTechAnswers] = useState({});
  const [behAnswers, setBehAnswers] = useState({});

  // Submitting / Result state
  const [submittingTech, setSubmittingTech] = useState(false);
  const [submittingBeh, setSubmittingBeh] = useState(false);
  const [techResult, setTechResult] = useState(null);
  const [behResult, setBehResult] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    try {
      const [cList, jList] = await Promise.all([getCandidates(), getJobs()]);
      setCandidates(cList);
      setJobs(jList);

      const cand = cList.find(c => c.candidate_id === selectedCandidateId) || cList[0];
      if (cand) {
        selectCandidate(cand, jList);
      }
    } catch (err) {
      console.error("Error loading assessment room:", err);
    }
  }

  async function selectCandidate(cand, jList = jobs) {
    setSelectedCandidate(cand);
    setSelectedCandidateId(cand.candidate_id);
    const jdId = cand.target_jd_id || (jList.length > 0 ? jList[0].jd_id : "JD-SWE-101");

    try {
      const [tq, bq] = await Promise.all([
        getTechnicalQuestions(jdId),
        getBehavioralQuestions(jdId)
      ]);
      setTechQuestions(tq.questions || []);
      setBehQuestions(bq.questions || []);

      // Autofill starter answers for easy testing
      const tAns = {};
      (tq.questions || []).forEach(q => {
        if (q.type === "mcq") tAns[q.question_id] = "B";
        else if (q.type === "short_answer") tAns[q.question_id] = "SELECT DISTINCT salary FROM employees ORDER BY salary DESC LIMIT 1 OFFSET 1;";
        else if (q.type === "coding") tAns[q.question_id] = "def has_cycle(graph):\n    visited = set()\n    rec_stack = set()\n    def dfs(node):\n        visited.add(node)\n        rec_stack.add(node)\n        for neighbor in graph.get(node, []):\n            if neighbor not in visited and dfs(neighbor): return True\n            elif neighbor in rec_stack: return True\n        rec_stack.remove(node)\n        return False\n    for node in graph:\n        if node not in visited and dfs(node): return True\n    return False\n# Time Complexity: O(V + E)";
      });
      setTechAnswers(tAns);

      const bAns = {
        "BEH_Q1": "In my previous role, a teammate and I disagreed on caching. I benchmarked Redis vs Memcached on latency, presented the data calmly, and the team adopted our hybrid Redis strategy.",
        "BEH_Q2": "Given vague latency requirements on a pipeline, I broke the challenge into ingestion and queuing stages, scheduled stakeholder demos, and delivered an MVP.",
        "BEH_Q3": "When required to learn Kubernetes within 2 weeks for release, I spun up local Minikube clusters, wrote Helm charts, and deployed successfully.",
        "BEH_Q4": "I communicated API decoupling to non-technical leaders by using business process flow diagrams rather than raw code syntax."
      };
      setBehAnswers(bAns);
    } catch (err) {
      console.error("Error loading questions:", err);
    }
  }

  async function handleSubmitTechnical(e) {
    e.preventDefault();
    setSubmittingTech(true);
    try {
      const answersList = Object.entries(techAnswers).map(([qid, text]) => ({
        question_id: qid,
        answer_text: text
      }));
      const res = await submitTechnicalAssessment({
        candidate_id: selectedCandidate.candidate_id,
        jd_id: selectedCandidate.target_jd_id || "JD-SWE-101",
        answers: answersList
      });
      setTechResult(res);
    } catch (err) {
      alert("Technical submission failed: " + err.message);
    } finally {
      setSubmittingTech(false);
    }
  }

  async function handleSubmitBehavioral(e) {
    e.preventDefault();
    setSubmittingBeh(true);
    try {
      const answersList = Object.entries(behAnswers).map(([qid, text]) => ({
        question_id: qid,
        answer_text: text
      }));
      const res = await submitBehavioralAssessment({
        candidate_id: selectedCandidate.candidate_id,
        jd_id: selectedCandidate.target_jd_id || "JD-SWE-101",
        answers: answersList
      });
      setBehResult(res);
    } catch (err) {
      alert("Behavioral submission failed: " + err.message);
    } finally {
      setSubmittingBeh(false);
    }
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Candidate Assessment Room
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Separate technical ability evaluation from resume screening. Administer standardized technical and STAR behavioral assessments.
          </p>
        </div>

        {/* Candidate Selector */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <label style={{ fontSize: "0.78rem", color: "#94a3b8", fontWeight: "600" }}>Active Candidate:</label>
          <select
            className="form-select"
            style={{ width: "240px" }}
            value={selectedCandidate?.candidate_id || ""}
            onChange={(e) => {
              const cand = candidates.find(c => c.candidate_id === e.target.value);
              if (cand) selectCandidate(cand);
            }}
          >
            {candidates.map(c => (
              <option key={c.candidate_id} value={c.candidate_id}>
                {c.name} ({c.cohort_tag || "General"})
              </option>
            ))}
          </select>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "24px" }}>
        {/* Left: Technical Skill Assessment */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <Code size={20} color="#6366f1" />
            <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc" }}>
              Technical Assessment (Skill-Assessor Agent)
            </h3>
          </div>
          <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: "18px" }}>
            Assesses candidate's demonstrated knowledge in Python, SQL queries, and algorithmic complexity.
          </p>

          <form onSubmit={handleSubmitTechnical} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {techQuestions.map((q, idx) => (
              <div key={q.question_id} style={{ background: "rgba(15, 23, 42, 0.7)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#818cf8" }}>
                    Q{idx + 1}: {q.competency_or_skill} ({q.type.toUpperCase()})
                  </span>
                </div>
                <p style={{ fontSize: "0.82rem", color: "#f8fafc", marginBottom: "8px" }}>{q.prompt}</p>

                {q.options && (
                  <div style={{ display: "flex", flexDirection: "column", gap: "4px", marginBottom: "8px" }}>
                    {q.options.map(opt => (
                      <div key={opt} style={{ fontSize: "0.75rem", color: "#94a3b8" }}>{opt}</div>
                    ))}
                  </div>
                )}

                <textarea
                  className="form-textarea"
                  rows={q.type === "coding" ? 5 : 2}
                  style={{ fontFamily: q.type === "coding" ? "monospace" : "inherit", fontSize: "0.78rem" }}
                  value={techAnswers[q.question_id] || ""}
                  onChange={(e) => setTechAnswers({ ...techAnswers, [q.question_id]: e.target.value })}
                  placeholder="Enter answer..."
                />
              </div>
            ))}

            <button type="submit" className="btn btn-primary" disabled={submittingTech}>
              <Play size={15} />
              <span>{submittingTech ? "Skill-Assessor Evaluating..." : "Submit to Skill-Assessor Agent"}</span>
            </button>
          </form>

          {/* Technical Result Display */}
          {techResult && (
            <div style={{ marginTop: "18px", padding: "16px", borderRadius: "10px", background: "rgba(99, 102, 241, 0.15)", border: "1px solid rgba(99, 102, 241, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.9rem", fontWeight: "700", color: "#818cf8" }}>Technical Score: {techResult.score}/100</span>
                <span style={{ fontSize: "0.72rem", color: "#34d399", fontWeight: "600" }}>{techResult.status}</span>
              </div>
              <ul style={{ paddingLeft: "18px", fontSize: "0.75rem", color: "#cbd5e1", marginTop: "8px" }}>
                {techResult.evidence?.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>

        {/* Right: Standardized Behavioral STAR Assessment */}
        <div className="glass-card" style={{ padding: "24px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "14px" }}>
            <MessageSquare size={20} color="#a855f7" />
            <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc" }}>
              Standardized Behavioral Assessment (Culture-Fit Agent)
            </h3>
          </div>
          <p style={{ fontSize: "0.78rem", color: "#94a3b8", marginBottom: "18px" }}>
            Evaluates Communication, Teamwork, Problem Solving, and Adaptability using the STAR method.
          </p>

          <form onSubmit={handleSubmitBehavioral} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            {behQuestions.map((q, idx) => (
              <div key={q.question_id} style={{ background: "rgba(15, 23, 42, 0.7)", padding: "14px", borderRadius: "10px", border: "1px solid rgba(255, 255, 255, 0.05)" }}>
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
                  <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#c084fc" }}>
                    Q{idx + 1}: {q.competency_or_skill}
                  </span>
                </div>
                <p style={{ fontSize: "0.82rem", color: "#f8fafc", marginBottom: "8px" }}>{q.prompt}</p>

                <textarea
                  className="form-textarea"
                  rows={3}
                  style={{ fontSize: "0.78rem" }}
                  value={behAnswers[q.question_id] || ""}
                  onChange={(e) => setBehAnswers({ ...behAnswers, [q.question_id]: e.target.value })}
                  placeholder="Candidate STAR response..."
                />
              </div>
            ))}

            <button type="submit" className="btn btn-primary" style={{ background: "linear-gradient(135deg, #a855f7 0%, #7e22ce 100%)" }} disabled={submittingBeh}>
              <Sparkles size={15} />
              <span>{submittingBeh ? "Culture-Fit Agent Evaluating..." : "Submit to Culture-Fit Agent"}</span>
            </button>
          </form>

          {/* Behavioral Result Display */}
          {behResult && (
            <div style={{ marginTop: "18px", padding: "16px", borderRadius: "10px", background: "rgba(168, 85, 247, 0.15)", border: "1px solid rgba(168, 85, 247, 0.3)" }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                <span style={{ fontSize: "0.9rem", fontWeight: "700", color: "#c084fc" }}>Behavioral STAR Score: {behResult.score}/100</span>
                <span style={{ fontSize: "0.72rem", color: behResult.status === "COMPLETED" ? "#34d399" : "#fb7185", fontWeight: "600" }}>{behResult.status}</span>
              </div>
              <ul style={{ paddingLeft: "18px", fontSize: "0.75rem", color: "#cbd5e1", marginTop: "8px" }}>
                {behResult.evidence?.map((e, idx) => (
                  <li key={idx}>{e}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
