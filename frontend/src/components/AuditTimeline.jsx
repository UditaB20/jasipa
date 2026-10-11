import { useState } from "react";
import { ChevronDown, ChevronRight, History } from "lucide-react";
import { EmptyState, fmtDateTime } from "./ui";

const HUMAN = /^(HUMAN_REVIEWER|HR )/;

export default function AuditTimeline({ entries = [] }) {
  const [open, setOpen] = useState(null);
  if (!entries.length) {
    return <EmptyState icon={History} title="No recorded events">Agent outputs and human actions for this candidate will appear here.</EmptyState>;
  }
  return (
    <ol className="timeline" style={{ listStyle: "none" }}>
      {entries.map((entry) => {
        const id = entry.log_id;
        const expanded = open === id;
        const human = HUMAN.test(entry.agent || "");
        return (
          <li key={id} className="tl-item">
            <span className={`tl-dot ${human ? "current" : "done"}`} />
            <div>
              <button className="link-btn row" style={{ color: "var(--text)", fontWeight: 550, textAlign: "left" }}
                onClick={() => setOpen(expanded ? null : id)} aria-expanded={expanded}>
                {expanded ? <ChevronDown size={14} /> : <ChevronRight size={14} />}
                {entry.event}
              </button>
              <div className="xs dim mt-4">
                {fmtDateTime(entry.timestamp)} · {entry.agent}
                {entry.model_name && entry.model_name !== "n/a" ? ` · ${entry.model_name}` : ""}
                {entry.rubric_version ? ` · rubric v${entry.rubric_version}` : ""}
              </div>
              {expanded && (
                <div className="grid grid-2 mt-8">
                  <div><div className="xs dim mb-4">Input</div><pre className="block">{JSON.stringify(entry.input_reference, null, 2)}</pre></div>
                  <div><div className="xs dim mb-4">Output</div><pre className="block">{JSON.stringify(entry.output, null, 2)}</pre></div>
                </div>
              )}
            </div>
          </li>
        );
      })}
    </ol>
  );
}
