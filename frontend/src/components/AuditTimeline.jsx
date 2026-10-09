import React, { useState } from "react";
import { ChevronDown, ChevronRight, Clock, Bot, User, CheckCircle2, ShieldCheck, Key } from "lucide-react";
import { verifyAuditHashChain } from "../services/api";

export default function AuditTimeline({ timeline = [] }) {
  const [expandedId, setExpandedId] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [verificationResult, setVerificationResult] = useState(null);

  const handleVerifyChain = async () => {
    try {
      setVerifying(true);
      const res = await verifyAuditHashChain();
      setVerificationResult(res);
    } catch (err) {
      setVerificationResult({ verified: false, error: err.message });
    } finally {
      setVerifying(false);
    }
  };

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
    <div style={{ display: "flex", flexDirection: "column", gap: "16px", position: "relative" }}>
      {/* Cryptographic Hash Verification Header */}
      <div
        className="glass-card"
        style={{
          padding: "12px 18px",
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          background: "linear-gradient(90deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%)",
          border: "1px solid rgba(56, 189, 248, 0.2)",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <ShieldCheck size={20} color="#38bdf8" />
          <div>
            <span style={{ fontSize: "0.85rem", fontWeight: "700", color: "#f8fafc" }}>
              Cryptographic SHA-256 Tamper-Evident Hash Chain
            </span>
            <p style={{ fontSize: "0.72rem", color: "#94a3b8", margin: 0 }}>
              Append-only audit ledger with cryptographic forward-linkage.
            </p>
          </div>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {verificationResult && (
            <span
              style={{
                fontSize: "0.75rem",
                fontWeight: "600",
                color: verificationResult.verified ? "#34d399" : "#f87171",
                display: "flex",
                alignItems: "center",
                gap: "6px",
              }}
            >
              <CheckCircle2 size={16} />
              {verificationResult.verified
                ? `Chain Verified (${verificationResult.total_entries_verified} blocks)`
                : "Integrity Failed"}
            </span>
          )}
          <button
            onClick={handleVerifyChain}
            disabled={verifying}
            className="btn btn-secondary"
            style={{ fontSize: "0.75rem", padding: "6px 12px", border: "1px solid rgba(56, 189, 248, 0.4)" }}
          >
            {verifying ? "Verifying Hash Chain..." : "Verify Hash Integrity"}
          </button>
        </div>
      </div>

      {/* Vertical timeline connector */}
      <div
        style={{
          position: "absolute",
          top: "80px",
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
                {item.entry_hash && (
                  <span
                    style={{
                      fontFamily: "monospace",
                      fontSize: "0.68rem",
                      background: "rgba(56, 189, 248, 0.1)",
                      color: "#38bdf8",
                      padding: "2px 6px",
                      borderRadius: "4px",
                      border: "1px solid rgba(56, 189, 248, 0.2)",
                      display: "flex",
                      alignItems: "center",
                      gap: "4px",
                    }}
                  >
                    <Key size={10} />
                    {item.entry_hash.slice(0, 10)}...
                  </span>
                )}
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
                {item.entry_hash && (
                  <div
                    style={{
                      marginBottom: "10px",
                      padding: "8px 12px",
                      borderRadius: "6px",
                      background: "rgba(15, 23, 42, 0.6)",
                      border: "1px solid rgba(255, 255, 255, 0.06)",
                    }}
                  >
                    <div style={{ color: "#94a3b8", fontSize: "0.7rem", fontWeight: "600" }}>
                      SHA-256 Provenance Hashes:
                    </div>
                    <div style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#38bdf8" }}>
                      Entry Hash: {item.entry_hash}
                    </div>
                    {item.prev_hash && (
                      <div style={{ fontFamily: "monospace", fontSize: "0.7rem", color: "#64748b" }}>
                        Prev Hash:  {item.prev_hash}
                      </div>
                    )}
                  </div>
                )}

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
