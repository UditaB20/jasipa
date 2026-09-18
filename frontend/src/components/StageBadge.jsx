import React from "react";

const STAGE_CONFIGS = {
  APPLIED: { label: "Applied", bg: "rgba(148, 163, 184, 0.15)", text: "#94a3b8", border: "rgba(148, 163, 184, 0.3)" },
  RESUME_SCREENED: { label: "Resume Screened", bg: "rgba(6, 182, 212, 0.15)", text: "#06b6d4", border: "rgba(6, 182, 212, 0.3)" },
  TECHNICAL_ASSESSED: { label: "Technical Assessed", bg: "rgba(59, 130, 246, 0.15)", text: "#60a5fa", border: "rgba(59, 130, 246, 0.3)" },
  BEHAVIORAL_ASSESSED: { label: "Behavioral Assessed", bg: "rgba(168, 85, 247, 0.15)", text: "#c084fc", border: "rgba(168, 85, 247, 0.3)" },
  PANEL_EVALUATED: { label: "Panel Evaluated", bg: "rgba(99, 102, 241, 0.15)", text: "#818cf8", border: "rgba(99, 102, 241, 0.3)" },
  BIAS_CHECKED: { label: "Bias Checked", bg: "rgba(245, 158, 11, 0.15)", text: "#fbbf24", border: "rgba(245, 158, 11, 0.3)" },
  HUMAN_REVIEW_PENDING: { label: "Human Review Pending", bg: "rgba(245, 158, 11, 0.2)", text: "#f59e0b", border: "rgba(245, 158, 11, 0.5)" },
  DECIDED: { label: "Decision Recorded", bg: "rgba(16, 185, 129, 0.15)", text: "#34d399", border: "rgba(16, 185, 129, 0.4)" },
  MANUAL_REVIEW_REQUIRED: { label: "Manual Review Req.", bg: "rgba(244, 63, 94, 0.2)", text: "#fb7185", border: "rgba(244, 63, 94, 0.4)" }
};

export default function StageBadge({ stage }) {
  const config = STAGE_CONFIGS[stage] || {
    label: stage,
    bg: "rgba(255, 255, 255, 0.1)",
    text: "#fff",
    border: "rgba(255, 255, 255, 0.2)"
  };

  return (
    <span
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
        padding: "3px 10px",
        borderRadius: "9999px",
        fontSize: "0.75rem",
        fontWeight: "600",
        backgroundColor: config.bg,
        color: config.text,
        border: `1px solid ${config.border}`,
        letterSpacing: "0.02em",
        whiteSpace: "nowrap"
      }}
    >
      <span
        style={{
          width: "6px",
          height: "6px",
          borderRadius: "50%",
          backgroundColor: config.text
        }}
      />
      {config.label}
    </span>
  );
}
