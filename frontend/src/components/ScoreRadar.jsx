import React from "react";

export default function ScoreRadar({ resumeScore = 0, skillScore = 0, cultureScore = 0, mergedScore = 0 }) {
  const metrics = [
    { label: "Resume Fit", score: resumeScore, weight: "40%", color: "#06b6d4" },
    { label: "Technical Skill", score: skillScore, weight: "40%", color: "#6366f1" },
    { label: "Behavioral Alignment", score: cultureScore, weight: "20%", color: "#a855f7" },
  ];

  const getScoreColor = (score) => {
    if (score >= 80) return "#10b981";
    if (score >= 65) return "#f59e0b";
    return "#f43f5e";
  };

  return (
    <div className="glass-card" style={{ padding: "20px" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "16px" }}>
        <div>
          <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc" }}>
            Multi-Agent Score Synthesis
          </h3>
          <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
            JD-Anchored Rubric (40% Resume + 40% Tech + 20% Behavioral)
          </p>
        </div>

        {/* Big Merged Score Circle */}
        <div
          style={{
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            width: "64px",
            height: "64px",
            borderRadius: "50%",
            background: "rgba(15, 23, 42, 0.9)",
            border: `2px solid ${getScoreColor(mergedScore)}`,
            boxShadow: `0 0 15px ${getScoreColor(mergedScore)}40`,
          }}
        >
          <span style={{ fontSize: "1.2rem", fontWeight: "800", color: getScoreColor(mergedScore) }}>
            {mergedScore}
          </span>
          <span style={{ fontSize: "0.58rem", color: "#94a3b8", textTransform: "uppercase", fontWeight: "600" }}>
            Merged
          </span>
        </div>
      </div>

      {/* Breakdown Bars */}
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        {metrics.map((m) => (
          <div key={m.label}>
            <div style={{ display: "flex", justifyContent: "space-between", fontSize: "0.78rem", marginBottom: "4px" }}>
              <span style={{ color: "#cbd5e1", fontWeight: "600" }}>
                {m.label} <span style={{ color: "#64748b", fontWeight: "400" }}>({m.weight})</span>
              </span>
              <span style={{ color: m.color, fontWeight: "700" }}>
                {m.score}/100
              </span>
            </div>
            <div
              style={{
                width: "100%",
                height: "8px",
                background: "rgba(30, 41, 59, 0.8)",
                borderRadius: "9999px",
                overflow: "hidden",
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, m.score))}%`,
                  height: "100%",
                  background: `linear-gradient(90deg, ${m.color}80 0%, ${m.color} 100%)`,
                  borderRadius: "9999px",
                  transition: "width 0.6s cubic-bezier(0.16, 1, 0.3, 1)",
                }}
              />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
