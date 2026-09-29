import React, { useState, useEffect } from "react";
import { ShieldCheck, Database, Cpu, CheckCircle2, Server, Scale, User, Edit3, Save, X } from "lucide-react";
import { getMcpTools, updateHRProfile } from "../services/api";

export default function SettingsPage({ currentUser, onUserUpdate }) {
  const [mcpStatus, setMcpStatus] = useState("Checking...");
  const [toolsCount, setToolsCount] = useState(0);

  // HR Profile Edit state
  const [isEditingHR, setIsEditingHR] = useState(false);
  const [hrNameInput, setHrNameInput] = useState(currentUser?.name || "Sarah Connor");
  const [hrSaving, setHrSaving] = useState(false);
  const [hrSuccessMsg, setHrSuccessMsg] = useState(null);

  useEffect(() => {
    async function checkStatus() {
      try {
        const res = await getMcpTools();
        setMcpStatus("Connected");
        setToolsCount(res.tools?.length || 9);
      } catch (err) {
        setMcpStatus("Error");
      }
    }
    checkStatus();
  }, []);

  const handleSaveHRProfile = async (e) => {
    e.preventDefault();
    setHrSaving(true);
    setHrSuccessMsg(null);

    try {
      const res = await updateHRProfile({ name: hrNameInput });
      const updatedUser = {
        ...currentUser,
        name: res.user?.name || hrNameInput
      };
      localStorage.setItem("user", JSON.stringify(updatedUser));
      if (onUserUpdate) onUserUpdate(updatedUser);
      setHrSuccessMsg("HR Profile updated successfully!");
      setIsEditingHR(false);
    } catch (err) {
      alert("Failed to update HR profile: " + err.message);
    } finally {
      setHrSaving(false);
    }
  };

  return (
    <div className="page-container" style={{ maxWidth: "900px" }}>
      <div className="page-header">
        <div>
          <h2 className="page-title">Settings & Profile</h2>
          <p className="page-subtitle">Manage your HR profile, view system integrations, and governance parameters.</p>
        </div>
      </div>

      {/* HR Administrator Profile Card */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
            <div style={{
              width: "40px",
              height: "40px",
              borderRadius: "50%",
              background: "rgba(79, 70, 229, 0.15)",
              border: "1px solid rgba(79, 70, 229, 0.3)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              color: "#818cf8"
            }}>
              <User size={20} />
            </div>
            <div>
              <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc" }}>
                HR Administrator Profile
              </h3>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8" }}>
                Your current administrative session details and signing credentials.
              </p>
            </div>
          </div>

          {!isEditingHR && (
            <button
              onClick={() => {
                setHrNameInput(currentUser?.name || "Sarah Connor");
                setHrSuccessMsg(null);
                setIsEditingHR(true);
              }}
              className="btn btn-outline"
              style={{ gap: "6px" }}
            >
              <Edit3 size={15} />
              <span>Edit Profile</span>
            </button>
          )}
        </div>

        {hrSuccessMsg && (
          <div style={{
            background: "rgba(16, 185, 129, 0.1)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            color: "#34d399",
            padding: "10px 14px",
            borderRadius: "6px",
            marginBottom: "16px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <CheckCircle2 size={16} />
            <span>{hrSuccessMsg}</span>
          </div>
        )}

        {isEditingHR ? (
          <form onSubmit={handleSaveHRProfile} style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}>
            <div>
              <label className="form-label">Full Name</label>
              <input
                type="text"
                className="form-input"
                value={hrNameInput}
                onChange={(e) => setHrNameInput(e.target.value)}
                required
              />
            </div>

            <div>
              <label className="form-label">Email Address (Administrative Login)</label>
              <input
                type="email"
                className="form-input"
                value={currentUser?.email || "hr@jasipa.ai"}
                disabled
                style={{ opacity: 0.7, cursor: "not-allowed" }}
              />
              <span style={{ fontSize: "0.75rem", color: "#64748b", marginTop: "4px", display: "block" }}>
                Administrative email is tied to system RBAC policy.
              </span>
            </div>

            <div style={{ display: "flex", gap: "10px", marginTop: "6px" }}>
              <button type="submit" className="btn btn-primary" disabled={hrSaving}>
                <Save size={15} />
                <span>{hrSaving ? "Saving..." : "Save Profile"}</span>
              </button>
              <button
                type="button"
                onClick={() => setIsEditingHR(false)}
                className="btn btn-outline"
              >
                Cancel
              </button>
            </div>
          </form>
        ) : (
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr", gap: "16px", background: "#0f172a", padding: "16px", borderRadius: "8px", border: "1px solid #334155" }}>
            <div>
              <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Display Name</span>
              <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "4px" }}>
                {currentUser?.name || "Sarah Connor"}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Email Address</span>
              <div style={{ fontSize: "0.95rem", fontWeight: "600", color: "#f8fafc", marginTop: "4px" }}>
                {currentUser?.email || "hr@jasipa.ai"}
              </div>
            </div>

            <div>
              <span style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase" }}>Role</span>
              <div style={{ marginTop: "4px" }}>
                <span className="badge badge-primary">HR Admin</span>
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Part 12: System Integrations Status */}
      <div className="card" style={{ marginBottom: "24px" }}>
        <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc", marginBottom: "16px" }}>
          System & Service Integrations
        </h3>

        <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
          {/* ATS DB */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            background: "#0f172a",
            borderRadius: "8px",
            border: "1px solid #334155"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <Database size={20} color="#818cf8" />
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#f8fafc" }}>
                  ATS Database Connection
                </div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  SQLAlchemy 2.0 ORM (SQLite / PostgreSQL)
                </div>
              </div>
            </div>
            <span className="badge badge-success">Connected</span>
          </div>

          {/* MCP Service */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            background: "#0f172a",
            borderRadius: "8px",
            border: "1px solid #334155"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <Server size={20} color="#34d399" />
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#f8fafc" }}>
                  MCP Service (Model Context Protocol)
                </div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  {toolsCount} standard tool endpoints registered for agent automation
                </div>
              </div>
            </div>
            <span className="badge badge-success">{mcpStatus}</span>
          </div>

          {/* LLM Engine */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            background: "#0f172a",
            borderRadius: "8px",
            border: "1px solid #334155"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <Cpu size={20} color="#fbbf24" />
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#f8fafc" }}>
                  Evaluation LLM Engine
                </div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  Google Gemini (gemini-2.5-flash) with local deterministic fallback
                </div>
              </div>
            </div>
            <span className="badge badge-success">Active</span>
          </div>

          {/* Governance Rules */}
          <div style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            padding: "12px 16px",
            background: "#0f172a",
            borderRadius: "8px",
            border: "1px solid #334155"
          }}>
            <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
              <Scale size={20} color="#f472b6" />
              <div>
                <div style={{ fontSize: "0.875rem", fontWeight: "600", color: "#f8fafc" }}>
                  Bias Disparity Rule (EEOC 4/5ths Rule)
                </div>
                <div style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
                  Disparity threshold set to 80% (0.80) ratio
                </div>
              </div>
            </div>
            <span className="badge badge-primary">Enforced</span>
          </div>
        </div>
      </div>

      {/* Governance & Compliance Card */}
      <div className="card">
        <h3 style={{ fontSize: "1rem", fontWeight: "600", color: "#f8fafc", marginBottom: "12px" }}>
          Core Governance Principles
        </h3>
        <p style={{ fontSize: "0.85rem", color: "#cbd5e1", lineHeight: "1.6" }}>
          JASIPA enforces zero autonomous rejection. AI agents (Resume Screener, Skill Assessor, Culture-Fit, 
          Panel Coordinator, Bias Checker) generate evidence and structured recommendations, but all final hiring 
          and rejection decisions require an authenticated Human Reviewer sign-off.
        </p>
      </div>
    </div>
  );
}
