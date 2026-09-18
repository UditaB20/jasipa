import React from "react";
import { ShieldCheck, Sparkles, Layers, GraduationCap, Briefcase, UserCheck } from "lucide-react";

export default function Navbar({ currentRole, setCurrentRole, activePage, setActivePage }) {
  const handleRoleChange = (role) => {
    setCurrentRole(role);
    if (role === "STUDENT") {
      setActivePage("student-portal");
    } else if (role === "REVIEWER") {
      setActivePage("reviews");
    } else {
      setActivePage("dashboard");
    }
  };

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "14px 28px",
        background: "rgba(15, 23, 42, 0.8)",
        backdropFilter: "blur(16px)",
        borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
        position: "sticky",
        top: 0,
        zIndex: 50,
      }}
    >
      {/* Brand & Governance Badge */}
      <div style={{ display: "flex", alignItems: "center", gap: "18px" }}>
        <div 
          onClick={() => currentRole === "STUDENT" ? setActivePage("student-portal") : setActivePage("dashboard")}
          style={{ display: "flex", alignItems: "center", gap: "10px", cursor: "pointer" }}
        >
          <div
            style={{
              width: "36px",
              height: "36px",
              borderRadius: "10px",
              background: "linear-gradient(135deg, #6366f1 0%, #06b6d4 100%)",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              boxShadow: "0 0 15px rgba(99, 102, 241, 0.4)",
            }}
          >
            <Layers size={20} color="#fff" />
          </div>
          <div>
            <h1 style={{ fontSize: "1.15rem", fontWeight: "800", letterSpacing: "-0.02em", color: "#f8fafc" }}>
              JASIPA <span style={{ fontSize: "0.8rem", color: "#06b6d4", fontWeight: "600" }}>v1.0</span>
            </h1>
            <p style={{ fontSize: "0.7rem", color: "#94a3b8", fontWeight: "500" }}>
              Job Applicant Screening & Interview Panel Agent
            </p>
          </div>
        </div>

        {/* Strict Governance Rule Pill */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            background: "rgba(16, 185, 129, 0.12)",
            border: "1px solid rgba(16, 185, 129, 0.3)",
            padding: "4px 12px",
            borderRadius: "9999px",
            fontSize: "0.72rem",
            color: "#34d399",
            fontWeight: "600",
          }}
        >
          <ShieldCheck size={14} />
          <span>Governance: Zero Autonomous Rejection</span>
        </div>
      </div>

      {/* Right Controls: 3-Way Role Switcher & Live Demo */}
      <div style={{ display: "flex", alignItems: "center", gap: "14px" }}>
        {/* Quick 1-Click Demo Launcher */}
        <button
          onClick={() => setActivePage("demo-runner")}
          className="btn btn-primary"
          style={{
            padding: "6px 14px",
            fontSize: "0.8rem",
            background: "linear-gradient(135deg, #ec4899 0%, #8b5cf6 100%)",
          }}
        >
          <Sparkles size={15} />
          <span>1-Click Live Demo</span>
        </button>

        {/* 3-Way Role Switcher (RBAC) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            background: "rgba(30, 41, 59, 0.8)",
            borderRadius: "8px",
            padding: "3px",
            border: "1px solid rgba(255, 255, 255, 0.1)",
          }}
        >
          <button
            onClick={() => handleRoleChange("STUDENT")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: "600",
              border: "none",
              cursor: "pointer",
              background: currentRole === "STUDENT" ? "#06b6d4" : "transparent",
              color: currentRole === "STUDENT" ? "#000" : "#94a3b8",
              transition: "all 0.2s",
            }}
          >
            <GraduationCap size={14} />
            <span>Student / Candidate</span>
          </button>

          <button
            onClick={() => handleRoleChange("HR_ADMIN")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: "600",
              border: "none",
              cursor: "pointer",
              background: currentRole === "HR_ADMIN" ? "#6366f1" : "transparent",
              color: currentRole === "HR_ADMIN" ? "#fff" : "#94a3b8",
              transition: "all 0.2s",
            }}
          >
            <Briefcase size={14} />
            <span>HR Admin</span>
          </button>

          <button
            onClick={() => handleRoleChange("REVIEWER")}
            style={{
              display: "flex",
              alignItems: "center",
              gap: "6px",
              padding: "5px 12px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: "600",
              border: "none",
              cursor: "pointer",
              background: currentRole === "REVIEWER" ? "#10b981" : "transparent",
              color: currentRole === "REVIEWER" ? "#fff" : "#94a3b8",
              transition: "all 0.2s",
            }}
          >
            <UserCheck size={14} />
            <span>Reviewer</span>
          </button>
        </div>

        {/* Active Role Indicator */}
        <div style={{ display: "flex", alignItems: "center", gap: "6px", fontSize: "0.75rem", color: "#94a3b8" }}>
          <span style={{ width: "8px", height: "8px", borderRadius: "50%", background: "#10b981", boxShadow: "0 0 8px #10b981" }} />
          <span>{currentRole} Mode</span>
        </div>
      </div>
    </header>
  );
}
