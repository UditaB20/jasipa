import React from "react";
import {
  LayoutDashboard,
  Briefcase,
  Users,
  FileCheck2,
  Scale,
  UserCheck2,
  History,
  Terminal,
  PlayCircle,
  GraduationCap,
  FileText,
  Code,
  MessageSquare,
  CheckCircle2
} from "lucide-react";

export default function Sidebar({ activePage, setActivePage, currentRole, pendingReviewCount = 0 }) {
  let menuItems = [];

  if (currentRole === "STUDENT") {
    menuItems = [
      { id: "student-portal", label: "My Application & Resume", icon: GraduationCap },
      { id: "assessments", label: "Technical Assessment Room", icon: Code },
      { id: "student-portal-status", label: "My Application Status", icon: CheckCircle2 }
    ];
  } else if (currentRole === "REVIEWER") {
    menuItems = [
      { 
        id: "reviews", 
        label: "Human Review Station", 
        icon: UserCheck2, 
        badge: pendingReviewCount > 0 ? pendingReviewCount : null,
        badgeColor: "#f59e0b"
      },
      { id: "candidates", label: "Candidate Dossiers", icon: Users },
      { id: "bias", label: "Bias & Cohort Analytics", icon: Scale },
      { id: "audit", label: "Audit Trail & Memory", icon: History },
      { id: "demo-runner", label: "Live Demo Walkthrough", icon: PlayCircle, highlight: true }
    ];
  } else {
    // HR_ADMIN (Full Workspace)
    menuItems = [
      { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
      { id: "jobs", label: "Job Descriptions & Rubrics", icon: Briefcase },
      { id: "candidates", label: "Candidate Pipeline", icon: Users },
      { id: "assessments", label: "Assessment Room", icon: FileCheck2 },
      { 
        id: "reviews", 
        label: "Human Review Station", 
        icon: UserCheck2, 
        badge: pendingReviewCount > 0 ? pendingReviewCount : null,
        badgeColor: "#f59e0b"
      },
      { id: "bias", label: "Bias & Cohort Analytics", icon: Scale },
      { id: "audit", label: "Audit Trail & Memory", icon: History },
      { id: "mcp", label: "MCP ATS Tools", icon: Terminal },
      { id: "demo-runner", label: "Live Demo Walkthrough", icon: PlayCircle, highlight: true }
    ];
  }

  return (
    <aside
      style={{
        width: "260px",
        background: "rgba(15, 23, 42, 0.7)",
        backdropFilter: "blur(16px)",
        borderRight: "1px solid rgba(255, 255, 255, 0.08)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "20px 14px",
        minHeight: "calc(100vh - 65px)",
      }}
    >
      <nav style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
        <p style={{ fontSize: "0.68rem", fontWeight: "700", textTransform: "uppercase", color: "#64748b", padding: "0 12px 6px 12px", letterSpacing: "0.08em" }}>
          {currentRole === "STUDENT" ? "Candidate Workspace" : currentRole === "REVIEWER" ? "Reviewer Station" : "HR Administration"}
        </p>

        {menuItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id || (item.id === "student-portal-status" && activePage === "student-portal");
          
          return (
            <button
              key={item.id}
              onClick={() => {
                if (item.id === "student-portal-status") {
                  setActivePage("student-portal");
                } else {
                  setActivePage(item.id);
                }
              }}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "10px 12px",
                borderRadius: "9px",
                fontSize: "0.85rem",
                fontWeight: isActive ? "600" : "500",
                color: isActive ? "#fff" : item.highlight ? "#38bdf8" : "#94a3b8",
                background: isActive 
                  ? "linear-gradient(90deg, rgba(99, 102, 241, 0.25) 0%, rgba(99, 102, 241, 0.05) 100%)" 
                  : item.highlight
                  ? "rgba(56, 189, 248, 0.06)"
                  : "transparent",
                border: isActive 
                  ? "1px solid rgba(99, 102, 241, 0.4)" 
                  : item.highlight
                  ? "1px solid rgba(56, 189, 248, 0.2)"
                  : "1px solid transparent",
                cursor: "pointer",
                transition: "all 0.2s",
                textAlign: "left",
                width: "100%",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Icon size={18} color={isActive ? "#818cf8" : item.highlight ? "#38bdf8" : "#94a3b8"} />
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span
                  style={{
                    background: item.badgeColor || "#6366f1",
                    color: "#000",
                    fontWeight: "700",
                    fontSize: "0.7rem",
                    padding: "2px 7px",
                    borderRadius: "9999px",
                  }}
                >
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Footer Info */}
      <div
        style={{
          padding: "12px",
          background: "rgba(30, 41, 59, 0.4)",
          borderRadius: "10px",
          border: "1px solid rgba(255, 255, 255, 0.05)",
        }}
      >
        <p style={{ fontSize: "0.72rem", color: "#94a3b8", fontWeight: "600" }}>
          Active Mode: <span style={{ color: currentRole === "STUDENT" ? "#22d3ee" : currentRole === "REVIEWER" ? "#34d399" : "#818cf8" }}>{currentRole}</span>
        </p>
        <p style={{ fontSize: "0.68rem", color: "#64748b", marginTop: "4px" }}>
          Role-Based Access Control (RBAC) Active
        </p>
      </div>
    </aside>
  );
}
