import React from "react";
import { AlertTriangle, CheckCircle2, Info } from "lucide-react";

export default function BiasAlertBanner({ biasCheck }) {
  if (!biasCheck) return null;

  const isFlagged = biasCheck.flag_status === "FLAGGED";

  return (
    <div
      style={{
        padding: "16px 20px",
        borderRadius: "12px",
        background: isFlagged 
          ? "linear-gradient(135deg, rgba(245, 158, 11, 0.15) 0%, rgba(245, 158, 11, 0.05) 100%)"
          : "linear-gradient(135deg, rgba(16, 185, 129, 0.15) 0%, rgba(16, 185, 129, 0.05) 100%)",
        border: isFlagged 
          ? "1px solid rgba(245, 158, 11, 0.4)" 
          : "1px solid rgba(16, 185, 129, 0.3)",
        display: "flex",
        alignItems: "flex-start",
        gap: "14px",
        marginBottom: "16px",
      }}
    >
      <div
        style={{
          width: "36px",
          height: "36px",
          borderRadius: "8px",
          background: isFlagged ? "rgba(245, 158, 11, 0.2)" : "rgba(16, 185, 129, 0.2)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          flexShrink: 0,
        }}
      >
        {isFlagged ? (
          <AlertTriangle size={20} color="#f59e0b" />
        ) : (
          <CheckCircle2 size={20} color="#10b981" />
        )}
      </div>

      <div style={{ flex: 1 }}>
        <div style={{ display: "flex", alignItems: "center", gap: "10px", marginBottom: "4px" }}>
          <h4
            style={{
              fontSize: "0.9rem",
              fontWeight: "700",
              color: isFlagged ? "#fbbf24" : "#34d399",
            }}
          >
            {isFlagged ? "Bias Checker Warning: Cohort Disparity Flagged" : "Bias Check Cleared: Statistical Parity Verified"}
          </h4>
          <span
            style={{
              fontSize: "0.7rem",
              fontWeight: "600",
              padding: "2px 8px",
              borderRadius: "9999px",
              background: isFlagged ? "rgba(245, 158, 11, 0.25)" : "rgba(16, 185, 129, 0.25)",
              color: isFlagged ? "#f59e0b" : "#10b981",
            }}
          >
            {biasCheck.flag_status}
          </span>
        </div>

        <p style={{ fontSize: "0.8rem", color: "#cbd5e1", lineHeight: "1.4" }}>
          {biasCheck.reason || "Evaluated candidate outcome against historical cohort baseline."}
        </p>

        <div
          style={{
            marginTop: "8px",
            fontSize: "0.72rem",
            color: "#94a3b8",
            display: "flex",
            alignItems: "center",
            gap: "6px",
          }}
        >
          <Info size={13} />
          <span>
            Governance Notice: Bias flags never modify or auto-reject candidates. They provide evidence context for the Human Reviewer.
          </span>
        </div>
      </div>
    </div>
  );
}
