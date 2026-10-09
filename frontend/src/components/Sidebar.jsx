import React from "react";
import { 
  LayoutDashboard, 
  Briefcase, 
  Users, 
  Code2, 
  UserCheck, 
  Scale, 
  History,
  Settings,
  BrainCircuit
} from "lucide-react";

export default function Sidebar({ activePage, setActivePage, pendingReviewCount = 0 }) {
  const navItems = [
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "jobs", label: "Jobs", icon: Briefcase },
    { id: "candidates", label: "Candidates", icon: Users },
    { id: "assessments", label: "Assessment Submissions", icon: Code2 },
    { 
      id: "reviews", 
      label: "Human Reviews", 
      icon: UserCheck,
      badge: pendingReviewCount > 0 ? pendingReviewCount : null,
      badgeColor: "warning"
    },
    { id: "bias", label: "Bias Monitor", icon: Scale },
    { id: "learning", label: "Hiring Outcomes", icon: BrainCircuit },
    { id: "audit", label: "Audit Logs", icon: History },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  return (
    <aside
      style={{
        width: "240px",
        background: "#0f172a",
        borderRight: "1px solid #334155",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "16px 12px",
        minHeight: "calc(100vh - 57px)",
        flexShrink: 0
      }}
    >
      <nav style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <div style={{ padding: "8px 12px 6px", fontSize: "0.75rem", fontWeight: "600", color: "#64748b", textTransform: "uppercase", letterSpacing: "0.05em" }}>
          Recruitment
        </div>
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = activePage === item.id;

          return (
            <button
              key={item.id}
              onClick={() => setActivePage(item.id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                padding: "9px 12px",
                borderRadius: "6px",
                border: "none",
                background: isActive ? "#1e293b" : "transparent",
                color: isActive ? "#ffffff" : "#94a3b8",
                fontWeight: isActive ? "600" : "500",
                fontSize: "0.875rem",
                cursor: "pointer",
                textAlign: "left",
                transition: "all 0.15s ease",
              }}
              onMouseEnter={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "rgba(255, 255, 255, 0.03)";
                  e.currentTarget.style.color = "#f8fafc";
                }
              }}
              onMouseLeave={(e) => {
                if (!isActive) {
                  e.currentTarget.style.background = "transparent";
                  e.currentTarget.style.color = "#94a3b8";
                }
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <Icon size={18} color={isActive ? "#818cf8" : "#64748b"} />
                <span>{item.label}</span>
              </div>

              {item.badge && (
                <span className={`badge badge-${item.badgeColor || 'primary'}`} style={{ fontSize: "0.7rem", padding: "1px 7px" }}>
                  {item.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {/* Bottom Minimal System Tag */}
      <div style={{ padding: "12px", borderTop: "1px solid #1e293b" }}>
        <div style={{ display: "flex", alignItems: "center", gap: "8px", fontSize: "0.75rem", color: "#64748b" }}>
          <span style={{ width: "6px", height: "6px", borderRadius: "50%", background: "#10b981" }} />
          <span>System Healthy</span>
        </div>
      </div>
    </aside>
  );
}
