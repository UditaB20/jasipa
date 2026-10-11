import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, Info, X, XCircle, Inbox, RefreshCw } from "lucide-react";

/* ---------- Labels ---------- */

export const STAGES = {
  REGISTERED: { label: "Registered", tone: "" },
  APPLIED: { label: "Applied", tone: "" },
  MANUAL_REVIEW_REQUIRED: { label: "Resume needs review", tone: "danger" },
  RESUME_SCREENED: { label: "Screened", tone: "accent" },
  TECHNICAL_ASSESSED: { label: "Technical done", tone: "accent" },
  BEHAVIORAL_ASSESSED: { label: "Assessments done", tone: "accent" },
  PANEL_EVALUATED: { label: "Awaiting decision", tone: "warning" },
  BIAS_CHECKED: { label: "Awaiting decision", tone: "warning" },
  HUMAN_REVIEW_PENDING: { label: "Awaiting decision", tone: "warning" },
  INFO_REQUESTED: { label: "More info requested", tone: "warning" },
  DECIDED: { label: "Decided", tone: "success" },
};

export const RECOMMENDATIONS = {
  PROCEED_TO_HUMAN_REVIEW: { label: "Proceed", tone: "success", text: "Evidence meets the bar; a reviewer confirms." },
  HUMAN_REVIEW_REQUIRED: { label: "Needs careful review", tone: "warning", text: "Mixed or below-target evidence." },
  ADDITIONAL_INFORMATION_REQUIRED: { label: "Incomplete evidence", tone: "danger", text: "One or more stages are missing." },
};

export const BIAS = {
  STATISTICALLY_SUPPORTED_DISPARITY: { label: "Supported disparity", tone: "danger" },
  POTENTIAL_DISPARITY_INDICATOR: { label: "Disparity indicator", tone: "warning" },
  INSUFFICIENT_DATA: { label: "Insufficient data", tone: "" },
  NO_INDICATOR_DETECTED: { label: "No indicator", tone: "success" },
  REFERENCE_GROUP: { label: "Reference group", tone: "accent" },
};

export const DECISIONS = {
  APPROVE: { label: "Approved", tone: "success" },
  REJECT: { label: "Not selected", tone: "danger" },
  REQUEST_MORE_INFORMATION: { label: "More info requested", tone: "warning" },
};

export function Badge({ tone = "", children, dot = false, title }) {
  return (
    <span className={`badge ${tone ? `badge-${tone}` : ""}`} title={title}>
      {dot && <span className="dot" />}
      {children}
    </span>
  );
}

export const StageBadge = ({ stage }) => {
  const s = STAGES[stage] || { label: stage, tone: "" };
  return <Badge tone={s.tone} dot>{s.label}</Badge>;
};
export const RecommendationBadge = ({ value }) => {
  const r = RECOMMENDATIONS[value];
  return r ? <Badge tone={r.tone} title={r.text}>{r.label}</Badge> : <span className="dim">—</span>;
};
export const BiasBadge = ({ value }) => {
  const b = BIAS[value];
  return b ? <Badge tone={b.tone}>{b.label}</Badge> : <span className="dim">—</span>;
};

/* ---------- Layout ---------- */

export function PageHeader({ title, subtitle, actions, back }) {
  return (
    <header className="page-header">
      <div>
        {back}
        <h1 className="page-title">{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="header-actions">{actions}</div>}
    </header>
  );
}

export function Card({ title, subtitle, actions, children, pad = true, className = "" }) {
  return (
    <section className={`card ${className}`}>
      {(title || actions) && (
        <div className="card-header">
          <div>
            {title && <h2 className="card-title">{title}</h2>}
            {subtitle && <p className="card-sub">{subtitle}</p>}
          </div>
          {actions}
        </div>
      )}
      {pad ? <div className="card-body">{children}</div> : children}
    </section>
  );
}

export function Alert({ tone = "info", title, children, action }) {
  const Icon = { info: Info, success: CheckCircle2, warning: AlertTriangle, danger: XCircle }[tone] || Info;
  const color = { info: "var(--accent)", success: "var(--success)", warning: "var(--warning)", danger: "var(--danger)" }[tone];
  return (
    <div className={`alert alert-${tone}`} role={tone === "danger" ? "alert" : "status"}>
      <Icon size={16} color={color} />
      <div style={{ flex: 1 }}>
        {title && <div className="alert-title">{title}</div>}
        <div className="muted">{children}</div>
      </div>
      {action}
    </div>
  );
}

export function EmptyState({ icon: Icon = Inbox, title, children, action }) {
  return (
    <div className="empty">
      <Icon size={28} />
      <div className="empty-title">{title}</div>
      {children && <p className="empty-text">{children}</p>}
      {action && <div className="mt-16">{action}</div>}
    </div>
  );
}

export function LoadingBlock({ rows = 4 }) {
  return (
    <div className="stack-sm" aria-busy="true" aria-label="Loading">
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skeleton" style={{ height: i === 0 ? 22 : 14, width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function PageLoading() {
  return (
    <div className="page">
      <div className="skeleton" style={{ height: 28, width: 260, marginBottom: 10 }} />
      <div className="skeleton" style={{ height: 14, width: 380, marginBottom: 28 }} />
      <div className="grid grid-4 mb-24">
        {[0, 1, 2, 3].map((i) => <div key={i} className="skeleton" style={{ height: 96, borderRadius: 14 }} />)}
      </div>
      <div className="skeleton" style={{ height: 280, borderRadius: 14 }} />
    </div>
  );
}

export function ErrorState({ error, onRetry }) {
  return (
    <div className="page">
      <Alert tone="danger" title="This page could not be loaded"
        action={onRetry && <button className="btn btn-secondary btn-sm" onClick={onRetry}><RefreshCw size={13} />Retry</button>}>
        {error?.message || String(error)}
      </Alert>
    </div>
  );
}

export function Tabs({ tabs, active, onChange }) {
  return (
    <div className="tabs" role="tablist">
      {tabs.map((t) => (
        <button key={t.id} role="tab" aria-selected={active === t.id} className={`tab ${active === t.id ? "active" : ""}`} onClick={() => onChange(t.id)}>
          {t.label}
          {t.badge != null && <Badge tone={t.badgeTone || ""}>{t.badge}</Badge>}
        </button>
      ))}
    </div>
  );
}

export function ScoreBar({ label, value, hint }) {
  const v = value == null ? null : Math.max(0, Math.min(100, Number(value)));
  const tone = v == null ? "" : v >= 75 ? "good" : v >= 50 ? "mid" : "low";
  return (
    <div className="score-row" title={hint}>
      <span className="muted">{label}</span>
      <div className="score-track"><div className={`score-fill ${tone}`} style={{ width: `${v ?? 0}%` }} /></div>
      <span className="num right" style={{ textAlign: "right", fontWeight: 600 }}>{v == null ? "—" : v.toFixed(0)}</span>
    </div>
  );
}

export function Spinner() {
  return <span className="spinner" aria-hidden="true" />;
}

export function Drawer({ title, onClose, children, footer }) {
  useEffect(() => {
    const onKey = (e) => e.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);
  return (
    <div className="overlay" onMouseDown={(e) => e.target === e.currentTarget && onClose()}>
      <div className="drawer" role="dialog" aria-modal="true" aria-label={title}>
        <div className="drawer-head">
          <h2 className="card-title" style={{ fontSize: 16 }}>{title}</h2>
          <button className="btn btn-ghost btn-sm" onClick={onClose} aria-label="Close"><X size={16} /></button>
        </div>
        <div className="drawer-body">{children}</div>
        {footer && <div className="drawer-foot">{footer}</div>}
      </div>
    </div>
  );
}

export function Field({ label, hint, error, children, className = "" }) {
  return (
    <label className={`field ${className}`}>
      <span className="label">{label}</span>
      {children}
      {error ? <span className="field-error">{error}</span> : hint && <span className="hint">{hint}</span>}
    </label>
  );
}

/* ---------- Hooks ---------- */

export function useAsync(loader, deps = []) {
  const [state, setState] = useState({ data: null, loading: true, error: null });
  const counter = useRef(0);
  const run = useCallback(async () => {
    const id = ++counter.current;
    setState((s) => ({ ...s, loading: true, error: null }));
    try {
      const data = await loader();
      if (id === counter.current) setState({ data, loading: false, error: null });
    } catch (error) {
      if (id === counter.current) setState({ data: null, loading: false, error });
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, deps);
  useEffect(() => { run(); }, [run]);
  return { ...state, reload: run };
}

export function useHashRoute(defaultPath) {
  const read = () => window.location.hash.replace(/^#/, "") || defaultPath;
  const [path, setPath] = useState(read);
  useEffect(() => {
    const onChange = () => setPath(read());
    window.addEventListener("hashchange", onChange);
    return () => window.removeEventListener("hashchange", onChange);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);
  const navigate = useCallback((to) => {
    window.location.hash = to;
    window.scrollTo({ top: 0 });
  }, []);
  return [path, navigate];
}

/* ---------- Toasts ---------- */

const ToastContext = createContext(() => {});
export const useToast = () => useContext(ToastContext);

export function ToastProvider({ children }) {
  const [toasts, setToasts] = useState([]);
  const push = useCallback((message, tone = "success") => {
    const id = Math.random().toString(36).slice(2);
    setToasts((t) => [...t, { id, message, tone }]);
    setTimeout(() => setToasts((t) => t.filter((x) => x.id !== id)), tone === "error" ? 7000 : 4000);
  }, []);
  return (
    <ToastContext.Provider value={push}>
      {children}
      <div className="toasts" aria-live="polite">
        {toasts.map((t) => (
          <div key={t.id} className={`toast ${t.tone}`}>
            {t.tone === "error" ? <XCircle size={16} /> : <CheckCircle2 size={16} />}
            <span>{t.message}</span>
          </div>
        ))}
      </div>
    </ToastContext.Provider>
  );
}

/* ---------- Formatting ---------- */

export const fmtDate = (value) => (value ? new Date(value).toLocaleDateString(undefined, { day: "numeric", month: "short", year: "numeric" }) : "—");
export const fmtDateTime = (value) => (value ? new Date(value).toLocaleString(undefined, { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" }) : "—");
export const fmtScore = (value) => (value == null ? "—" : Number(value).toFixed(1));
export const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
export const latest = (list) => (list && list.length ? list[list.length - 1] : null);
