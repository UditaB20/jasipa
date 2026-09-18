import React, { useState } from "react";
import { ChevronDown, ChevronRight, Clock, Bot, User, CheckCircle2 } from "lucide-react";

export default function AuditTimeline({ timeline = [] }) {
  const [expandedId, setExpandedId] = useState(null);

  if (!timeline || timeline.length === 0) {
    return (
      <div style={{ padding: "20px", textAlign: "center", color: "#64748b", fontSize: "0.85rem" }}>
        No audit events recorded for this candidate yet.
      </div>
    );
  }

  const toggleExpand = (id) => {
    setExpandedId(expandedId === id ? null : id);
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "12px", position: "relative" }}>
      {/* Vertical timeline connector */}
      <div
        style={{
          position: "absolute",
          top: "16px",
          bottom: "16px",
          left: "15px",
          width: "2px",
          background: "rgba(255, 255, 255, 0.08)",
          zIndex: 0,
        }}
      />

      {timeline.map((item, idx) => {
        const isExpanded = expandedId === item.log_id || idx === 0;
        const isHuman = item.agent?.includes("HUMAN");

        return (
          <div
            key={item.log_id || idx}
            className="glass-card"
            style={{
              marginLeft: "36px",
              padding: "14px 18px",
              position: "relative",
              zIndex: 1,
            }}
          >
            {/* Timeline bullet dot */}
            <div
              style={{
                position: "absolute",
                left: "-28px",
                top: "18px",
                width: "14px",
                height: "14px",
                borderRadius: "50%",
                background: isHuman ? "#10b981" : "#6366f1",
                border: "3px solid #0f172a",
                boxShadow: isHuman ? "0 0 10px #10b981" : "0 0 10px #6366f1",
              }}
            />

            <div
              onClick={() => toggleExpand(item.log_id)}
              style={{
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                cursor: "pointer",
              }}
            >
              <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
                <div
                  style={{
                    padding: "5px",
                    borderRadius: "6px",
                    background: isHuman ? "rgba(16, 185, 129, 0.15)" : "rgba(99, 102, 241, 0.15)",
                    color: isHuman ? "#34d399" : "#818cf8",
                  }}
                >
                  {isHuman ? <User size={16} /> : <Bot size={16} />}
                </div>

                <div>
                  <h4 style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
                    {item.event}
                  </h4>
                  <p style={{ fontSize: "0.72rem", color: "#94a3b8" }}>
                    Agent: <span style={{ color: "#cbd5e1", fontWeight: "600" }}>{item.agent}</span> • Stage: <span style={{ color: "#38bdf8" }}>{item.stage}</span>
                    {item.rubric_version && ` • Rubric v${item.rubric_version}`}
                  </p>
                </div>
              </div>

              <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                <span style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "0.7rem", color: "#64748b" }}>
                  <Clock size={12} />
                  {new Date(item.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit", second: "2-digit" })}
                </span>
                {isExpanded ? <ChevronDown size={16} color="#94a3b8" /> : <ChevronRight size={16} color="#94a3b8" />}
              </div>
            </div>

            {/* Expandable JSON payload details */}
            {isExpanded && (
              <div
                style={{
                  marginTop: "14px",
                  paddingTop: "12px",
                  borderTop: "1px solid rgba(255, 255, 255, 0.08)",
                  fontSize: "0.75rem",
                }}
              >
                <div style={{ marginBottom: "8px" }}>
                  <span style={{ color: "#94a3b8", fontWeight: "600" }}>Input Reference / Context:</span>
                  <pre
                    style={{
                      background: "rgba(15, 23, 42, 0.9)",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      color: "#a5f3fc",
                      marginTop: "4px",
                      overflowX: "auto",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                    }}
                  >
                    {JSON.stringify(item.input_reference, null, 2)}
                  </pre>
                </div>

                <div>
                  <span style={{ color: "#94a3b8", fontWeight: "600" }}>Agent Output Payload:</span>
                  <pre
                    style={{
                      background: "rgba(15, 23, 42, 0.9)",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      color: "#86efac",
                      marginTop: "4px",
                      overflowX: "auto",
                      border: "1px solid rgba(255, 255, 255, 0.05)",
                    }}
                  >
                    {JSON.stringify(item.output, null, 2)}
                  </pre>
                </div>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
