import React, { useState, useEffect } from "react";
import { Terminal, Play, CheckCircle2, Code2, Database, Copy } from "lucide-react";
import { getMcpTools, executeMcpTool } from "../services/api";

export default function McpToolsView() {
  const [tools, setTools] = useState([]);
  const [selectedTool, setSelectedTool] = useState(null);
  const [argumentsJson, setArgumentsJson] = useState("{\n  \"candidate_id\": \"CAND-001-ELENA\"\n}");
  const [executionResult, setExecutionResult] = useState(null);
  const [executing, setExecuting] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadTools();
  }, []);

  async function loadTools() {
    try {
      const res = await getMcpTools();
      setTools(res.tools || []);
      if (res.tools?.length > 0) {
        selectTool(res.tools[0]);
      }
    } catch (err) {
      console.error("Error loading MCP tools:", err);
    } finally {
      setLoading(false);
    }
  }

  function selectTool(tool) {
    setSelectedTool(tool);
    // Provide sample JSON arguments based on tool name
    if (tool.name === "get_candidate" || tool.name === "get_candidate_pipeline_status" || tool.name === "get_candidate_history") {
      setArgumentsJson(JSON.stringify({ candidate_id: "CAND-001-ELENA" }, null, 2));
    } else if (tool.name === "get_job_description") {
      setArgumentsJson(JSON.stringify({ jd_id: "JD-SWE-101" }, null, 2));
    } else if (tool.name === "save_screening_result") {
      setArgumentsJson(JSON.stringify({
        candidate_id: "CAND-001-ELENA",
        jd_id: "JD-SWE-101",
        score: 95.0,
        matched_requirements: ["Python", "React", "SQL"],
        missing_requirements: [],
        experience_match: true,
        evidence: ["5 years FastAPI experience"],
        rubric_version: "1.0"
      }, null, 2));
    } else if (tool.name === "save_human_review") {
      setArgumentsJson(JSON.stringify({
        candidate_id: "CAND-001-ELENA",
        reviewer_id: "USR_REV_01",
        reviewer_name: "Dr. Alex HumanReviewer",
        decision: "APPROVE",
        notes: "Excellent technical and behavioral assessment match."
      }, null, 2));
    } else {
      setArgumentsJson("{\n  \n}");
    }
    setExecutionResult(null);
  }

  async function handleExecuteTool(e) {
    e.preventDefault();
    setExecuting(true);
    try {
      const parsedArgs = JSON.parse(argumentsJson);
      const res = await executeMcpTool(selectedTool.name, parsedArgs);
      setExecutionResult(res);
    } catch (err) {
      setExecutionResult({ isError: true, error: err.message });
    } finally {
      setExecuting(false);
    }
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Model Context Protocol (MCP) ATS Tools
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Decoupled ATS Tool interface exposing standard JSON-RPC tools for candidate lookup, evaluation persistence, and pipeline history.
          </p>
        </div>
      </div>

      <div style={{ display: "grid", gridTemplateColumns: "340px 1fr", gap: "24px" }}>
        {/* Left: Tool List */}
        <div className="glass-card" style={{ padding: "18px" }}>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "12px" }}>
            Exposed ATS MCP Tools ({tools.length})
          </h3>

          <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
            {tools.map((t) => {
              const isSelected = selectedTool?.name === t.name;
              return (
                <div
                  key={t.name}
                  onClick={() => selectTool(t)}
                  style={{
                    padding: "10px 12px",
                    borderRadius: "8px",
                    background: isSelected ? "rgba(99, 102, 241, 0.2)" : "rgba(30, 41, 59, 0.4)",
                    border: isSelected ? "1px solid #6366f1" : "1px solid rgba(255, 255, 255, 0.05)",
                    cursor: "pointer",
                    transition: "all 0.2s",
                  }}
                >
                  <div style={{ fontSize: "0.82rem", fontWeight: "700", color: isSelected ? "#fff" : "#cbd5e1" }}>
                    {t.name}
                  </div>
                  <p style={{ fontSize: "0.7rem", color: "#94a3b8", marginTop: "2px", whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
                    {t.description}
                  </p>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right: Tool Execution Playground */}
        {selectedTool && (
          <div style={{ display: "flex", flexDirection: "column", gap: "20px" }}>
            <div className="glass-card" style={{ padding: "22px" }}>
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "8px" }}>
                <Terminal size={20} color="#818cf8" />
                <h3 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc" }}>
                  {selectedTool.name}
                </h3>
              </div>
              <p style={{ fontSize: "0.82rem", color: "#cbd5e1", marginBottom: "16px" }}>
                {selectedTool.description}
              </p>

              <form onSubmit={handleExecuteTool}>
                <div style={{ marginBottom: "14px" }}>
                  <label style={{ fontSize: "0.75rem", color: "#94a3b8", fontWeight: "600" }}>
                    Tool Arguments (JSON):
                  </label>
                  <textarea
                    className="form-textarea"
                    rows={6}
                    style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "#a5f3fc" }}
                    value={argumentsJson}
                    onChange={(e) => setArgumentsJson(e.target.value)}
                  />
                </div>

                <button type="submit" className="btn btn-primary" disabled={executing}>
                  <Play size={15} />
                  <span>{executing ? "Executing Tool..." : `Execute ${selectedTool.name}`}</span>
                </button>
              </form>
            </div>

            {/* Execution Result Box */}
            {executionResult && (
              <div className="glass-card" style={{ padding: "22px" }}>
                <h4 style={{ fontSize: "0.9rem", fontWeight: "700", color: executionResult.isError ? "#fb7185" : "#34d399", marginBottom: "10px" }}>
                  Execution Response:
                </h4>
                <pre
                  style={{
                    background: "rgba(15, 23, 42, 0.9)",
                    padding: "14px",
                    borderRadius: "8px",
                    fontSize: "0.78rem",
                    color: executionResult.isError ? "#fb7185" : "#86efac",
                    overflowX: "auto",
                    border: "1px solid rgba(255, 255, 255, 0.08)",
                  }}
                >
                  {JSON.stringify(executionResult, null, 2)}
                </pre>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}
