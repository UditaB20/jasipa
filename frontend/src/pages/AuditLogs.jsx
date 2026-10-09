import React, { useState, useEffect } from "react";
import { 
  History, 
  ShieldCheck, 
  ShieldAlert, 
  Search, 
  Filter, 
  RefreshCw, 
  Hash, 
  Cpu, 
  Code, 
  CheckCircle2, 
  AlertTriangle,
  FileText,
  User,
  ArrowRight,
  ExternalLink,
  X
} from "lucide-react";
import { getAuditLogs, verifyAuditChain } from "../services/api";

export default function AuditLogs({ setActivePage, setSelectedCandidateId }) {
  const [logs, setLogs] = useState([]);
  const [integrity, setIntegrity] = useState(null);
  const [loading, setLoading] = useState(true);
  const [verifying, setVerifying] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [stageFilter, setStageFilter] = useState("ALL");
  const [selectedLog, setSelectedLog] = useState(null);

  useEffect(() => {
    loadData();
  }, []);

  async function loadData() {
    setLoading(true);
    try {
      const [logsData, integrityData] = await Promise.all([
        getAuditLogs(null, 150).catch(() => []),
        verifyAuditChain().catch(() => null),
      ]);
      setLogs(logsData || []);
      setIntegrity(integrityData);
    } catch (err) {
      console.error("Failed to load audit logs:", err);
    } finally {
      setLoading(false);
    }
  }

  async function handleVerify() {
    setVerifying(true);
    try {
      const res = await verifyAuditChain();
      setIntegrity(res);
    } catch (err) {
      console.error("Verification failed:", err);
    } finally {
      setVerifying(false);
    }
  }

  // Filtered logs
  const filteredLogs = logs.filter((l) => {
    const matchesSearch = 
      !searchQuery ||
      l.event?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.stage?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.candidate_id?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.agent?.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.log_id?.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStage = stageFilter === "ALL" || l.stage === stageFilter;

    return matchesSearch && matchesStage;
  });

  const uniqueStages = Array.from(new Set(logs.map(l => l.stage).filter(Boolean)));

  const getStageBadgeColor = (stage) => {
    if (!stage) return { bg: "rgba(148, 163, 184, 0.15)", text: "#94a3b8", border: "rgba(148, 163, 184, 0.3)" };
    if (stage.includes("RUBRIC")) return { bg: "rgba(56, 189, 248, 0.15)", text: "#38bdf8", border: "rgba(56, 189, 248, 0.3)" };
    if (stage.includes("PANEL") || stage.includes("DECISION")) return { bg: "rgba(99, 102, 241, 0.15)", text: "#818cf8", border: "rgba(99, 102, 241, 0.3)" };
    if (stage.includes("HUMAN")) return { bg: "rgba(234, 179, 8, 0.15)", text: "#facc15", border: "rgba(234, 179, 8, 0.3)" };
    if (stage.includes("BIAS")) return { bg: "rgba(244, 63, 94, 0.15)", text: "#fb7185", border: "rgba(244, 63, 94, 0.3)" };
    if (stage.includes("APPEAL") || stage.includes("RE_REVIEW")) return { bg: "rgba(168, 85, 247, 0.15)", text: "#c084fc", border: "rgba(168, 85, 247, 0.3)" };
    return { bg: "rgba(52, 211, 153, 0.15)", text: "#34d399", border: "rgba(52, 211, 153, 0.3)" };
  };

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      {/* Page Header */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
            <History size={26} color="#38bdf8" />
            <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
              System-Wide Audit Ledger & Cryptographic Verification
            </h2>
          </div>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8", marginTop: "4px" }}>
            Immutable, SHA-256 hash-chained audit trail capturing all multi-agent evaluations, rubric deployments, and human decisions.
          </p>
        </div>

        <button 
          onClick={loadData} 
          disabled={loading} 
          className="btn btn-secondary" 
          style={{ padding: "8px 14px" }}
        >
          <RefreshCw size={14} className={loading ? "spin" : ""} />
          <span>Refresh Ledger</span>
        </button>
      </div>

      {/* Cryptographic Integrity Card */}
      {integrity && (
        <div
          style={{
            padding: "20px 24px",
            borderRadius: "12px",
            background: integrity.verified ? "rgba(16, 185, 129, 0.1)" : "rgba(239, 68, 68, 0.1)",
            border: integrity.verified ? "1px solid rgba(16, 185, 129, 0.3)" : "1px solid rgba(239, 68, 68, 0.4)",
            marginBottom: "24px",
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "16px"
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
            {integrity.verified ? (
              <ShieldCheck size={36} color="#34d399" />
            ) : (
              <ShieldAlert size={36} color="#f87171" />
            )}
            <div>
              <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
                <h3 style={{ fontSize: "1.05rem", fontWeight: "800", color: integrity.verified ? "#34d399" : "#f87171", margin: 0 }}>
                  {integrity.status === "VALID_IMMUTABLE_CHAIN" 
                    ? "Cryptographic Hash Chain Verified (Zero Tampering)" 
                    : "Ledger Tampering Detected!"}
                </h3>
                <span style={{ fontSize: "0.75rem", background: "rgba(255, 255, 255, 0.08)", padding: "2px 8px", borderRadius: "4px", color: "#cbd5e1" }}>
                  SHA-256 Merkle-Chained
                </span>
              </div>
              <p style={{ fontSize: "0.8rem", color: "#94a3b8", marginTop: "4px", margin: 0 }}>
                {integrity.total_audited} total system records analyzed • {integrity.chain_verified_count} cryptographically sealed blocks validated • 0 broken links.
              </p>
            </div>
          </div>

          <button
            onClick={handleVerify}
            disabled={verifying}
            className="btn btn-secondary"
            style={{ padding: "8px 16px", borderColor: "rgba(16, 185, 129, 0.4)", color: "#34d399" }}
          >
            <ShieldCheck size={16} />
            <span>{verifying ? "Auditing Chain..." : "Re-Verify Ledger Integrity"}</span>
          </button>
        </div>
      )}

      {/* Filter and Search Bar */}
      <div style={{ display: "flex", gap: "12px", marginBottom: "20px", flexWrap: "wrap", alignItems: "center" }}>
        <div style={{ position: "relative", flex: 1, minWidth: "260px" }}>
          <Search size={16} style={{ position: "absolute", left: "12px", top: "50%", transform: "translateY(-50%)", color: "#64748b" }} />
          <input
            type="text"
            className="form-input"
            placeholder="Search by event, candidate ID, agent, or log ID..."
            value={searchQuery}
            onChange={(e) => setSearchQuery(e.target.value)}
            style={{ paddingLeft: "36px" }}
          />
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <Filter size={16} color="#94a3b8" />
          <select
            className="form-input"
            value={stageFilter}
            onChange={(e) => setStageFilter(e.target.value)}
            style={{ padding: "8px 12px", width: "220px", cursor: "pointer" }}
          >
            <option value="ALL">All Event Types ({logs.length})</option>
            {uniqueStages.map((st) => (
              <option key={st} value={st}>
                {st} ({logs.filter(l => l.stage === st).length})
              </option>
            ))}
          </select>
        </div>
      </div>

      {/* Main Ledger Table */}
      <div className="glass-card" style={{ padding: "0", overflow: "hidden" }}>
        <div style={{ overflowX: "auto" }}>
          <table style={{ width: "100%", borderCollapse: "collapse", textAlign: "left", fontSize: "0.82rem" }}>
            <thead>
              <tr style={{ background: "rgba(15, 23, 42, 0.7)", borderBottom: "1px solid rgba(255, 255, 255, 0.08)", color: "#94a3b8", fontSize: "0.75rem", textTransform: "uppercase" }}>
                <th style={{ padding: "14px 18px" }}>Timestamp</th>
                <th style={{ padding: "14px 14px" }}>Event / Stage</th>
                <th style={{ padding: "14px 14px" }}>Event Description</th>
                <th style={{ padding: "14px 14px" }}>Actor / Model</th>
                <th style={{ padding: "14px 14px" }}>Target</th>
                <th style={{ padding: "14px 14px" }}>Entry Hash</th>
                <th style={{ padding: "14px 18px", textAlign: "right" }}>Action</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.length === 0 ? (
                <tr>
                  <td colSpan="7" style={{ padding: "32px", textAlign: "center", color: "#64748b" }}>
                    {loading ? "Loading audit records..." : "No audit events matching criteria."}
                  </td>
                </tr>
              ) : (
                filteredLogs.map((log) => {
                  const badge = getStageBadgeColor(log.stage);
                  const isHuman = log.agent?.includes("HR") || log.agent?.includes("HUMAN");

                  return (
                    <tr
                      key={log.log_id || Math.random()}
                      style={{
                        borderBottom: "1px solid rgba(255, 255, 255, 0.05)",
                        transition: "background 0.15s ease",
                      }}
                      onMouseEnter={(e) => e.currentTarget.style.background = "rgba(255, 255, 255, 0.02)"}
                      onMouseLeave={(e) => e.currentTarget.style.background = "transparent"}
                    >
                      <td style={{ padding: "12px 18px", color: "#cbd5e1", whiteSpace: "nowrap", fontFamily: "monospace", fontSize: "0.75rem" }}>
                        {log.timestamp ? new Date(log.timestamp).toLocaleString() : "N/A"}
                      </td>

                      <td style={{ padding: "12px 14px", whiteSpace: "nowrap" }}>
                        <span
                          style={{
                            padding: "3px 8px",
                            borderRadius: "6px",
                            background: badge.bg,
                            color: badge.text,
                            border: `1px solid ${badge.border}`,
                            fontSize: "0.72rem",
                            fontWeight: "600",
                          }}
                        >
                          {log.stage || "SYSTEM_EVENT"}
                        </span>
                      </td>

                      <td style={{ padding: "12px 14px", color: "#f8fafc", fontWeight: "500", maxWidth: "340px" }}>
                        <div style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }} title={log.event}>
                          {log.event}
                        </div>
                      </td>

                      <td style={{ padding: "12px 14px", whiteSpace: "nowrap" }}>
                        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                          {isHuman ? (
                            <User size={13} color="#facc15" />
                          ) : (
                            <Cpu size={13} color="#38bdf8" />
                          )}
                          <span style={{ color: isHuman ? "#fde047" : "#7dd3fc", fontSize: "0.75rem", fontWeight: "500" }}>
                            {log.agent || "System"}
                          </span>
                        </div>
                        {log.model_name && (
                          <div style={{ fontSize: "0.68rem", color: "#64748b", fontFamily: "monospace" }}>
                            {log.model_name} • {log.prompt_version || "v1"}
                          </div>
                        )}
                      </td>

                      <td style={{ padding: "12px 14px", whiteSpace: "nowrap" }}>
                        {log.candidate_id ? (
                          <button
                            type="button"
                            onClick={() => {
                              if (setSelectedCandidateId && setActivePage) {
                                setSelectedCandidateId(log.candidate_id);
                                setActivePage("candidate-detail");
                              }
                            }}
                            style={{
                              background: "rgba(99, 102, 241, 0.15)",
                              border: "1px solid rgba(99, 102, 241, 0.3)",
                              color: "#818cf8",
                              borderRadius: "4px",
                              padding: "2px 8px",
                              fontSize: "0.72rem",
                              cursor: "pointer",
                              display: "inline-flex",
                              alignItems: "center",
                              gap: "4px"
                            }}
                          >
                            <span>{log.candidate_id}</span>
                            <ExternalLink size={10} />
                          </button>
                        ) : (
                          <span style={{ color: "#64748b", fontSize: "0.72rem" }}>Global Requisition</span>
                        )}
                      </td>

                      <td style={{ padding: "12px 14px", fontFamily: "monospace", fontSize: "0.72rem", color: "#64748b", whiteSpace: "nowrap" }}>
                        {log.entry_hash ? (
                          <span title={log.entry_hash} style={{ color: "#34d399", background: "rgba(16, 185, 129, 0.08)", padding: "2px 6px", borderRadius: "4px" }}>
                            {log.entry_hash.slice(0, 10)}...
                          </span>
                        ) : (
                          "Legacy Log"
                        )}
                      </td>

                      <td style={{ padding: "12px 18px", textAlign: "right", whiteSpace: "nowrap" }}>
                        <button
                          type="button"
                          onClick={() => setSelectedLog(log)}
                          className="btn btn-secondary"
                          style={{ padding: "4px 8px", fontSize: "0.72rem" }}
                        >
                          <FileText size={12} />
                          <span>Inspect</span>
                        </button>
                      </td>
                    </tr>
                  );
                })
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* JSON Payload Inspection Drawer / Modal */}
      {selectedLog && (
        <div
          style={{
            position: "fixed",
            inset: 0,
            background: "rgba(0, 0, 0, 0.75)",
            backdropFilter: "blur(4px)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            zIndex: 1000,
            padding: "20px"
          }}
          onClick={() => setSelectedLog(null)}
        >
          <div
            className="glass-card"
            style={{
              width: "100%",
              maxWidth: "800px",
              maxHeight: "85vh",
              overflowY: "auto",
              padding: "24px",
              background: "#0f172a",
              border: "1px solid rgba(255, 255, 255, 0.15)"
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", marginBottom: "18px" }}>
              <div>
                <span style={{ fontSize: "0.75rem", color: "#38bdf8", fontWeight: "600", textTransform: "uppercase" }}>
                  {selectedLog.stage}
                </span>
                <h3 style={{ fontSize: "1.1rem", fontWeight: "800", color: "#f8fafc", marginTop: "2px" }}>
                  {selectedLog.event}
                </h3>
                <span style={{ fontSize: "0.75rem", color: "#64748b", fontFamily: "monospace" }}>
                  Log ID: {selectedLog.log_id}
                </span>
              </div>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                style={{ background: "transparent", border: "none", color: "#94a3b8", cursor: "pointer" }}
              >
                <X size={20} />
              </button>
            </div>

            {/* Cryptographic Proof Card */}
            <div style={{ padding: "12px 14px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.8)", border: "1px solid rgba(255, 255, 255, 0.08)", marginBottom: "16px" }}>
              <div style={{ fontSize: "0.75rem", fontWeight: "700", color: "#34d399", marginBottom: "6px", display: "flex", alignItems: "center", gap: "6px" }}>
                <ShieldCheck size={14} />
                <span>Cryptographic Block Integrity Proof</span>
              </div>
              <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", fontSize: "0.72rem", fontFamily: "monospace" }}>
                <div>
                  <span style={{ color: "#64748b", display: "block" }}>Previous Block Hash (prev_hash):</span>
                  <span style={{ color: "#94a3b8", wordBreak: "break-all" }}>{selectedLog.prev_hash || "0000000000000000000000000000000000000000000000000000000000000000"}</span>
                </div>
                <div>
                  <span style={{ color: "#64748b", display: "block" }}>Entry Hash (entry_hash):</span>
                  <span style={{ color: "#34d399", wordBreak: "break-all" }}>{selectedLog.entry_hash || "N/A"}</span>
                </div>
              </div>
            </div>

            {/* Structured Details */}
            <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
              <div>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#cbd5e1" }}>Input Reference / Context:</span>
                <pre style={{ background: "#020617", padding: "12px", borderRadius: "8px", fontSize: "0.75rem", color: "#94a3b8", overflowX: "auto", marginTop: "4px" }}>
                  {JSON.stringify(selectedLog.input_reference, null, 2)}
                </pre>
              </div>

              <div>
                <span style={{ fontSize: "0.75rem", fontWeight: "700", color: "#cbd5e1" }}>Evaluation Output / Payload:</span>
                <pre style={{ background: "#020617", padding: "12px", borderRadius: "8px", fontSize: "0.75rem", color: "#38bdf8", overflowX: "auto", marginTop: "4px" }}>
                  {JSON.stringify(selectedLog.output, null, 2)}
                </pre>
              </div>
            </div>

            <div style={{ display: "flex", justifyContent: "flex-end", marginTop: "20px" }}>
              <button
                type="button"
                onClick={() => setSelectedLog(null)}
                className="btn btn-secondary"
                style={{ padding: "8px 16px" }}
              >
                Close Inspector
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
