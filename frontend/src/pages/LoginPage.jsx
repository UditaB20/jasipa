import React, { useState } from "react";
import { login } from "../services/api";
import { Briefcase, UserCheck, Shield, AlertCircle, ArrowRight } from "lucide-react";

export default function LoginPage({ onLoginSuccess }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleSubmit = async (e) => {
    if (e) e.preventDefault();
    setError(null);
    setLoading(true);

    try {
      const res = await login(email, password);
      localStorage.setItem("token", res.access_token);
      localStorage.setItem("user", JSON.stringify(res.user));
      if (onLoginSuccess) {
        onLoginSuccess(res.user);
      }
    } catch (err) {
      setError(err.message || "Invalid credentials. Please try again.");
    } finally {
      setLoading(false);
    }
  };

  const handleQuickFill = (demoEmail, demoPassword) => {
    setEmail(demoEmail);
    setPassword(demoPassword);
    setError(null);
  };

  return (
    <div style={{
      minHeight: "100vh",
      display: "flex",
      alignItems: "center",
      justifyContent: "center",
      background: "#0b1120",
      padding: "24px"
    }}>
      <div style={{
        width: "100%",
        maxWidth: "420px",
        background: "#1e293b",
        border: "1px solid #334155",
        borderRadius: "12px",
        padding: "36px 32px",
        boxShadow: "0 20px 25px -5px rgba(0, 0, 0, 0.4)"
      }}>
        {/* Logo and Header */}
        <div style={{ textAlign: "center", marginBottom: "28px" }}>
          <div style={{
            width: "48px",
            height: "48px",
            background: "#4f46e5",
            borderRadius: "10px",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            marginBottom: "12px"
          }}>
            <Shield size={26} color="#ffffff" />
          </div>
          <h1 style={{ fontSize: "1.5rem", fontWeight: "700", color: "#f8fafc", letterSpacing: "-0.02em" }}>
            JASIPA
          </h1>
          <p style={{ fontSize: "0.875rem", color: "#94a3b8", marginTop: "4px" }}>
            Recruitment & Interview Panel System
          </p>
        </div>

        {/* Error Alert */}
        {error && (
          <div style={{
            background: "rgba(239, 68, 68, 0.1)",
            border: "1px solid rgba(239, 68, 68, 0.3)",
            color: "#f87171",
            padding: "10px 14px",
            borderRadius: "6px",
            fontSize: "0.85rem",
            marginBottom: "20px",
            display: "flex",
            alignItems: "center",
            gap: "8px"
          }}>
            <AlertCircle size={16} />
            <span>{error}</span>
          </div>
        )}

        {/* Login Form */}
        <form onSubmit={handleSubmit}>
          <div style={{ marginBottom: "16px" }}>
            <label className="form-label">Email Address</label>
            <input
              type="email"
              className="form-input"
              placeholder="e.g. hr@jasipa.ai or candidate@jasipa.ai"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
            />
          </div>

          <div style={{ marginBottom: "24px" }}>
            <label className="form-label">Password</label>
            <input
              type="password"
              className="form-input"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />
          </div>

          <button
            type="submit"
            className="btn btn-primary"
            style={{ width: "100%", padding: "10px", fontSize: "0.95rem" }}
            disabled={loading}
          >
            {loading ? "Signing in..." : (
              <>
                <span>Sign In</span>
                <ArrowRight size={16} />
              </>
            )}
          </button>
        </form>

        {/* Quick Demo Access Bar */}
        <div style={{ marginTop: "28px", paddingTop: "20px", borderTop: "1px solid #334155" }}>
          <div style={{ fontSize: "0.75rem", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em", marginBottom: "10px", textAlign: "center" }}>
            Quick Sign-In (Demo Credentials)
          </div>
          <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
            <button
              type="button"
              onClick={() => handleQuickFill("hr@jasipa.ai", "admin123")}
              className="btn btn-outline"
              style={{ fontSize: "0.8rem", padding: "7px 10px" }}
            >
              <Briefcase size={14} color="#818cf8" />
              <span>HR Admin</span>
            </button>
            <button
              type="button"
              onClick={() => handleQuickFill("candidate@jasipa.ai", "candidate123")}
              className="btn btn-outline"
              style={{ fontSize: "0.8rem", padding: "7px 10px" }}
            >
              <UserCheck size={14} color="#34d399" />
              <span>Candidate</span>
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
