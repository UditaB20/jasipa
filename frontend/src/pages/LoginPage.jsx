import { useState } from "react";
import { ArrowRight } from "lucide-react";
import { login, register } from "../services/api";
import { Alert, Field, Spinner } from "../components/ui";

const DEMO_ACCOUNTS = [
  { label: "HR lead", email: "hr@jasipa.ai", password: "admin123" },
  { label: "Second reviewer", email: "reviewer@jasipa.ai", password: "reviewer123" },
  { label: "Candidate (demo login)", email: "student@jasipa.ai", password: "student123" },
  { label: "Second candidate (demo)", email: "candidate@jasipa.ai", password: "candidate123" },
];

export default function LoginPage({ onLogin, sessionExpired }) {
  const [mode, setMode] = useState("signin");
  const [form, setForm] = useState({ name: "", email: "", password: "" });
  const [error, setError] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (key) => (e) => setForm({ ...form, [key]: e.target.value });

  const submit = async (e) => {
    e.preventDefault();
    setError(null);
    if (mode === "register" && form.password.length < 8) {
      setError("Use a password with at least 8 characters.");
      return;
    }
    setBusy(true);
    try {
      const session = mode === "signin" ? await login(form.email, form.password) : await register(form);
      onLogin(session);
    } catch (err) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="auth">
      <div className="auth-inner">
        <div className="row" style={{ justifyContent: "center", marginBottom: 20 }}>
          <div className="brand-mark">J</div>
          <div>
            <div className="brand-name">JASIPA</div>
            <div className="brand-sub">Candidate screening and interview panel</div>
          </div>
        </div>
        <div className="card auth-card">
          <div className="segmented" role="tablist" aria-label="Account">
            {[["signin", "Sign in"], ["register", "Create candidate account"]].map(([id, label]) => (
              <button key={id} type="button" role="tab" aria-selected={mode === id} className={mode === id ? "active" : ""}
                onClick={() => { setMode(id); setError(null); }}>{label}</button>
            ))}
          </div>
          {sessionExpired && !error && <div className="mb-16"><Alert tone="warning">Your session expired. Sign in again to continue.</Alert></div>}
          {error && <div className="mb-16"><Alert tone="danger">{error}</Alert></div>}
          <form onSubmit={submit} className="stack" noValidate={false}>
            {mode === "register" && (
              <Field label="Full name">
                <input className="input" value={form.name} onChange={set("name")} required minLength={2} autoComplete="name" />
              </Field>
            )}
            <Field label="Email">
              <input className="input" type="email" value={form.email} onChange={set("email")} required autoComplete="email" />
            </Field>
            <Field label="Password" hint={mode === "register" ? "At least 8 characters." : undefined}>
              <input className="input" type="password" value={form.password} onChange={set("password")} required
                autoComplete={mode === "signin" ? "current-password" : "new-password"} />
            </Field>
            <button className="btn btn-primary btn-block" type="submit" disabled={busy} style={{ height: 38 }}>
              {busy ? <Spinner /> : null}
              {mode === "signin" ? "Sign in" : "Create account"}
              {!busy && <ArrowRight size={15} />}
            </button>
          </form>
          {mode === "register" && (
            <p className="xs dim mt-16">Recruiters review every application. Automated scores support their review but never make the decision.</p>
          )}
        </div>

        {import.meta.env.DEV && mode === "signin" && (
          <div style={{ marginTop: 16 }}>
            <div className="xs dim" style={{ marginBottom: 8 }}>Demo accounts (development build only)</div>
            <div className="demo-accounts">
              {DEMO_ACCOUNTS.map((a) => (
                <button key={a.email} type="button" className="demo-account" onClick={() => setForm({ ...form, email: a.email, password: a.password })}>
                  <span>{a.label}</span><span>{a.email}</span>
                </button>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
