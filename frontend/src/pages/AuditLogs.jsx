import { useMemo, useState } from "react";
import { History, Search, ShieldCheck, ShieldAlert } from "lucide-react";
import { getAuditLogs, verifyAuditChain } from "../services/api";
import { Alert, Card, Drawer, EmptyState, ErrorState, PageHeader, PageLoading, Spinner, fmtDateTime, useAsync } from "../components/ui";

export default function AuditLogs() {
  const { data: logs, loading, error, reload } = useAsync(() => getAuditLogs(null, 500), []);
  const [integrity, setIntegrity] = useState(null);
  const [verifying, setVerifying] = useState(false);
  const [search, setSearch] = useState("");
  const [stage, setStage] = useState("");
  const [selected, setSelected] = useState(null);

  const stages = useMemo(() => Array.from(new Set((logs || []).map((l) => l.stage))).sort(), [logs]);
  const visible = useMemo(() => {
    const q = search.trim().toLowerCase();
    return (logs || []).filter((l) => (!stage || l.stage === stage) &&
      (!q || [l.event, l.agent, l.candidate_id, l.stage].some((v) => v?.toLowerCase().includes(q))));
  }, [logs, search, stage]);

  const verify = async () => {
    setVerifying(true);
    try { setIntegrity(await verifyAuditChain()); } catch (err) { setIntegrity({ verified: false, issues: [], error: err.message }); } finally { setVerifying(false); }
  };

  if (loading && !logs) return <PageLoading />;
  if (error) return <ErrorState error={error} onRetry={reload} />;

  return (
    <div className="page">
      <PageHeader title="Audit log" subtitle="Append-only record of agent outputs, bias checks, configuration changes and human decisions. Each entry is hash-chained to the previous one."
        actions={<button className="btn btn-secondary" onClick={verify} disabled={verifying}>{verifying ? <Spinner /> : <ShieldCheck size={15} />}Verify integrity</button>} />

      {integrity && (
        <div className="mb-16">
          {integrity.verified
            ? <Alert tone="success" title="Ledger verified">All {integrity.total_audited} entries match their hashes and link to the previous entry.</Alert>
            : <Alert tone="danger" title="Integrity problem detected">{integrity.error || `${integrity.issues.length} issue(s): ${integrity.issues.slice(0, 3).map((i) => `#${i.seq ?? "?"} ${i.problem.toLowerCase()}`).join("; ")}`}</Alert>}
        </div>
      )}

      <div className="row wrap mb-16">
        <div className="input-icon" style={{ flex: "1 1 260px" }}><Search size={15} />
          <input className="input" placeholder="Search events, agents or candidate IDs" value={search} onChange={(e) => setSearch(e.target.value)} aria-label="Search audit log" /></div>
        <select className="select" style={{ width: 220 }} value={stage} onChange={(e) => setStage(e.target.value)} aria-label="Filter by stage">
          <option value="">All stages</option>{stages.map((s) => <option key={s} value={s}>{s.replace(/_/g, " ").toLowerCase()}</option>)}
        </select>
      </div>

      <Card pad={false}>
        {visible.length === 0 ? <EmptyState icon={History} title="No matching entries" /> : (
          <div className="table-wrap">
            <table className="table">
              <thead><tr><th className="right">#</th><th>When</th><th>Event</th><th className="hide-sm">Actor</th><th className="hide-sm">Candidate</th></tr></thead>
              <tbody>
                {visible.map((l) => (
                  <tr key={l.log_id} className="clickable" onClick={() => setSelected(l)}>
                    <td className="right num dim">{l.seq ?? "—"}</td>
                    <td className="nowrap muted">{fmtDateTime(l.timestamp)}</td>
                    <td><div className="cell-title">{l.event}</div><div className="cell-sub">{l.stage.replace(/_/g, " ").toLowerCase()}</div></td>
                    <td className="hide-sm muted">{l.agent}</td>
                    <td className="hide-sm">{l.candidate_id ? <a href={`#/candidates/${l.candidate_id}`} onClick={(e) => e.stopPropagation()} className="mono xs nowrap">{l.candidate_id}</a> : <span className="dim">—</span>}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </Card>
      <p className="xs dim mt-12">Showing the latest {logs.length} entries.</p>

      {selected && (
        <Drawer title={`Entry #${selected.seq ?? ""}`} onClose={() => setSelected(null)}>
          <div className="stack">
            <dl className="kv">
              <dt>Event</dt><dd>{selected.event}</dd>
              <dt>Actor</dt><dd>{selected.agent}</dd>
              <dt>Produced by</dt><dd>{selected.model_name || "—"}</dd>
              <dt>Rubric version</dt><dd>{selected.rubric_version || "—"}</dd>
              <dt>Time</dt><dd>{fmtDateTime(selected.timestamp)}</dd>
              <dt>Entry hash</dt><dd className="mono xs" style={{ wordBreak: "break-all" }}>{selected.entry_hash}</dd>
              <dt>Previous hash</dt><dd className="mono xs" style={{ wordBreak: "break-all" }}>{selected.prev_hash}</dd>
            </dl>
            <div><div className="section-title">Input</div><pre className="block">{JSON.stringify(selected.input_reference, null, 2)}</pre></div>
            <div><div className="section-title">Output</div><pre className="block">{JSON.stringify(selected.output, null, 2)}</pre></div>
            {integrity && !integrity.verified && integrity.issues.some((i) => i.log_id === selected.log_id) &&
              <Alert tone="danger" title="This entry failed verification"><ShieldAlert size={14} /> Its content or link does not match the chain.</Alert>}
          </div>
        </Drawer>
      )}
    </div>
  );
}
