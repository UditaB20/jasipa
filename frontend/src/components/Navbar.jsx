import React from "react";
import { LogOut, Shield, User } from "lucide-react";

export default function Navbar({ currentUser, onLogout }) {
  const isHR = currentUser?.role === "HR";

  return (
    <header
      style={{
        display: "flex",
        alignItems: "center",
        justifyContent: "space-between",
        padding: "12px 28px",
        background: "#0f172a",
        borderBottom: "1px solid #334155",
        position: "sticky",
        top: 0,
        zIndex: 40,
      }}
    >
      {/* Brand */}
      <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
        <div
          style={{
            width: "32px",
            height: "32px",
            borderRadius: "8px",
            background: isHR ? "#4f46e5" : "#059669",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
          }}
        >
          <Shield size={18} color="#ffffff" />
        </div>
        <div>
          <h1 style={{ fontSize: "1.1rem", fontWeight: "700", color: "#f8fafc", lineHeight: "1.2" }}>
            JASIPA
          </h1>
          <p style={{ fontSize: "0.75rem", color: "#94a3b8" }}>
            {isHR ? "Talent & Interview Panel System" : "Candidate Career Portal"}
          </p>
        </div>
      </div>

      {/* Right Controls: User Name, Role Label, Logout */}
      <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
        {/* User Info */}
        <div style={{ display: "flex", alignItems: "center", gap: "10px" }}>
          <div
            style={{
              width: "32px",
              height: "32px",
              borderRadius: "50%",
              background: "#1e293b",
              border: "1px solid #334155",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
            }}
          >
            <User size={16} color="#94a3b8" />
          </div>
          <div style={{ textAlign: "right" }}>
            <div style={{ fontSize: "0.85rem", fontWeight: "600", color: "#f8fafc" }}>
              {currentUser?.name || "Authenticated User"}
            </div>
            <div style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
              <span
                className={`badge ${isHR ? "badge-primary" : "badge-success"}`}
                style={{ fontSize: "0.68rem", padding: "1px 8px" }}
              >
                {isHR ? "HR Admin" : "Candidate"}
              </span>
            </div>
          </div>
        </div>

        {/* Vertical divider */}
        <div style={{ width: "1px", height: "24px", background: "#334155" }} />

        {/* Logout Button */}
        <button
          onClick={onLogout}
          className="btn btn-outline"
          style={{ padding: "6px 12px", fontSize: "0.8rem", gap: "6px" }}
          title="Sign out of your account"
        >
          <LogOut size={14} />
          <span>Logout</span>
        </button>
      </div>
    </header>
  );
}
