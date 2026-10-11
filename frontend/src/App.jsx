import { useCallback, useEffect, useState } from "react";
import { Briefcase, History, LayoutDashboard, Menu, Scale, Settings, TrendingUp, Users, FileText, ClipboardList, UserRound } from "lucide-react";
import Sidebar from "./components/Sidebar";
import { ToastProvider, useHashRoute } from "./components/ui";
import { getDashboard } from "./services/api";
import LoginPage from "./pages/LoginPage";
import Dashboard from "./pages/Dashboard";
import JobDescriptions from "./pages/JobDescriptions";
import CandidatesList from "./pages/CandidatesList";
import CandidateDetail from "./pages/CandidateDetail";
import BiasAnalytics from "./pages/BiasAnalytics";
import LearningPage from "./pages/LearningPage";
import AuditLogs from "./pages/AuditLogs";
import SettingsPage from "./pages/SettingsPage";
import CandidatePortal from "./pages/CandidatePortal";

function readStoredUser() {
  try {
    const token = localStorage.getItem("token");
    const user = JSON.parse(localStorage.getItem("user") || "null");
    if (!token || !user) return null;
    // Drop sessions whose JWT has already expired instead of showing a broken app.
    const payload = JSON.parse(atob(token.split(".")[1].replace(/-/g, "+").replace(/_/g, "/")));
    return payload.exp * 1000 > Date.now() ? user : null;
  } catch {
    return null;
  }
}

function HRApp({ user, onLogout }) {
  const [path] = useHashRoute("/dashboard");
  const [menuOpen, setMenuOpen] = useState(false);
  const [awaiting, setAwaiting] = useState(0);
  const [route, query = ""] = path.split("?");
  const parts = route.split("/").filter(Boolean);
  const section = parts[0] || "dashboard";

  const refreshCount = useCallback(() => {
    getDashboard().then((d) => setAwaiting(d.awaiting_decision)).catch(() => {});
  }, []);
  useEffect(() => { refreshCount(); }, [refreshCount, path]);

  const items = [
    { section: "Hiring" },
    { id: "dashboard", label: "Dashboard", icon: LayoutDashboard },
    { id: "candidates", label: "Candidates", icon: Users, count: awaiting },
    { id: "jobs", label: "Jobs", icon: Briefcase },
    { section: "Governance" },
    { id: "bias", label: "Bias monitor", icon: Scale },
    { id: "outcomes", label: "Hiring outcomes", icon: TrendingUp },
    { id: "audit", label: "Audit log", icon: History },
    { id: "settings", label: "Settings", icon: Settings },
  ];

  let page;
  if (section === "candidates" && parts[1]) page = <CandidateDetail candidateId={parts[1]} user={user} onDecision={refreshCount} />;
  else if (section === "candidates") page = <CandidatesList initialFilter={new URLSearchParams(query).get("stage") || ""} />;
  else if (section === "jobs") page = <JobDescriptions />;
  else if (section === "bias") page = <BiasAnalytics />;
  else if (section === "outcomes") page = <LearningPage user={user} />;
  else if (section === "audit") page = <AuditLogs />;
  else if (section === "settings") page = <SettingsPage user={user} />;
  else page = <Dashboard />;

  return (
    <Shell items={items} active={section} user={user} onLogout={onLogout} menuOpen={menuOpen} setMenuOpen={setMenuOpen} subtitle="Hiring workspace">
      {page}
    </Shell>
  );
}

function CandidateApp({ user, onLogout }) {
  const [path] = useHashRoute("/overview");
  const [menuOpen, setMenuOpen] = useState(false);
  const section = path.split("?")[0].split("/").filter(Boolean)[0] || "overview";
  const items = [
    { id: "overview", label: "My application", icon: ClipboardList },
    { id: "jobs", label: "Open roles", icon: Briefcase },
    { id: "assessments", label: "Assessments", icon: FileText },
    { id: "profile", label: "Profile & resume", icon: UserRound },
  ];
  return (
    <Shell items={items} active={section} user={user} onLogout={onLogout} menuOpen={menuOpen} setMenuOpen={setMenuOpen} subtitle="Candidate portal">
      <CandidatePortal section={section} user={user} />
    </Shell>
  );
}

function Shell({ items, active, user, onLogout, menuOpen, setMenuOpen, subtitle, children }) {
  return (
    <div className="shell">
      <a className="skip-link" href="#main" onClick={(e) => { e.preventDefault(); document.getElementById("main")?.focus(); }}>Skip to content</a>
      <Sidebar items={items} active={active} user={user} onLogout={onLogout} open={menuOpen} onNavigate={() => setMenuOpen(false)} subtitle={subtitle} />
      <div className="main">
        <div className="topbar">
          <div className="row"><div className="brand-mark" style={{ width: 26, height: 26, fontSize: 13 }}>J</div><strong>JASIPA</strong></div>
          <button className="btn btn-ghost btn-sm" onClick={() => setMenuOpen(!menuOpen)} aria-label="Open menu"><Menu size={18} /></button>
        </div>
        {menuOpen && <div style={{ position: "fixed", inset: 0, zIndex: 40 }} onClick={() => setMenuOpen(false)} />}
        <main id="main" tabIndex={-1} style={{ outline: "none" }}>{children}</main>
      </div>
    </div>
  );
}

export default function App() {
  const [user, setUser] = useState(readStoredUser);
  const [expired, setExpired] = useState(false);

  const logout = useCallback((sessionExpired = false) => {
    localStorage.removeItem("token");
    localStorage.removeItem("user");
    setUser(null);
    setExpired(sessionExpired === true);
    window.location.hash = "";
  }, []);

  useEffect(() => {
    const onExpired = () => logout(true);
    window.addEventListener("jasipa:session-expired", onExpired);
    return () => window.removeEventListener("jasipa:session-expired", onExpired);
  }, [logout]);

  const onLogin = (session) => {
    localStorage.setItem("token", session.access_token);
    localStorage.setItem("user", JSON.stringify(session.user));
    setExpired(false);
    window.location.hash = session.user.role === "HR" ? "/dashboard" : "/overview";
    setUser(session.user);
  };

  return (
    <ToastProvider>
      {!user ? <LoginPage onLogin={onLogin} sessionExpired={expired} />
        : user.role === "HR" ? <HRApp user={user} onLogout={() => logout()} />
        : <CandidateApp user={user} onLogout={() => logout()} />}
    </ToastProvider>
  );
}
