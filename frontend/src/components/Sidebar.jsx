import { LogOut } from "lucide-react";
import { initials } from "./ui";

export default function Sidebar({ items, active, onNavigate, user, onLogout, open, subtitle }) {
  return (
    <aside className={`sidebar ${open ? "open" : ""}`} aria-label="Main navigation">
      <div className="brand">
        <div className="brand-mark">J</div>
        <div>
          <div className="brand-name">JASIPA</div>
          <div className="brand-sub">{subtitle}</div>
        </div>
      </div>
      <nav className="nav">
        {items.map((item) =>
          item.section ? (
            <div key={item.section} className="nav-label">{item.section}</div>
          ) : (
            <a key={item.id} href={`#/${item.id}`} className={`nav-item ${active === item.id ? "active" : ""}`}
              aria-current={active === item.id ? "page" : undefined} onClick={() => onNavigate?.()}>
              <item.icon size={17} />
              <span>{item.label}</span>
              {item.count ? <span className="count">{item.count}</span> : null}
            </a>
          )
        )}
      </nav>
      <div className="sidebar-foot">
        <div className="avatar">{initials(user?.name)}</div>
        <div className="user-meta">
          <div className="name">{user?.name}</div>
          <div className="role">{user?.role === "HR" ? "HR team" : "Candidate"}</div>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={onLogout} title="Sign out" aria-label="Sign out"><LogOut size={15} /></button>
      </div>
    </aside>
  );
}
