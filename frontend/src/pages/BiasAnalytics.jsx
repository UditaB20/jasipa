import React, { useState, useEffect } from "react";
import { Scale, AlertTriangle, CheckCircle2, TrendingUp, BarChart3, Info } from "lucide-react";
import { getCohortAnalytics } from "../services/api";

export default function BiasAnalytics() {
  const [analytics, setAnalytics] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    loadAnalytics();
  }, []);

  async function loadAnalytics() {
    try {
      const data = await getCohortAnalytics();
      setAnalytics(data);
    } catch (err) {
      console.error("Error loading bias analytics:", err);
    } finally {
      setLoading(false);
    }
  }

  return (
    <div style={{ padding: "28px", maxWidth: "1400px", margin: "0 auto" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "24px" }}>
        <div>
          <h2 style={{ fontSize: "1.4rem", fontWeight: "800", color: "#f8fafc" }}>
            Bias & Cohort Disparity Analytics
          </h2>
          <p style={{ fontSize: "0.85rem", color: "#94a3b8" }}>
            Evaluates statistical parity and the 4/5ths (80%) disparate impact standard across evaluated candidate cohorts.
          </p>
        </div>

        <button onClick={loadAnalytics} className="btn btn-secondary" style={{ padding: "8px 14px" }}>
          <span>Refresh Metrics</span>
        </button>
      </div>

      {/* Summary Alert */}
      {analytics && (
        <div
          style={{
            padding: "18px 22px",
            borderRadius: "12px",
            background: analytics.disparity_detected ? "rgba(244, 63, 94, 0.12)" : "rgba(16, 185, 129, 0.12)",
            border: analytics.disparity_detected ? "1px solid rgba(244, 63, 94, 0.3)" : "1px solid rgba(16, 185, 129, 0.3)",
            marginBottom: "24px",
            display: "flex",
            alignItems: "center",
            gap: "14px",
          }}
        >
          {analytics.disparity_detected ? (
            <AlertTriangle size={24} color="#fb7185" />
          ) : (
            <CheckCircle2 size={24} color="#34d399" />
          )}
          <div>
            <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: analytics.disparity_detected ? "#fb7185" : "#34d399" }}>
              {analytics.disparity_detected ? "Cohort Disparity Flagged in Talent Pool" : "Statistical Parity Maintained"}
            </h3>
            <p style={{ fontSize: "0.8rem", color: "#cbd5e1", marginTop: "2px" }}>
              {analytics.summary}
            </p>
          </div>
        </div>
      )}

      {/* Cohort Cards */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: "20px", marginBottom: "28px" }}>
        {analytics?.cohorts?.map((c) => (
          <div key={c.cohort_name} className="glass-card" style={{ padding: "20px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "10px" }}>
              <h3 style={{ fontSize: "1rem", fontWeight: "700", color: "#f8fafc" }}>
                {c.cohort_name}
              </h3>
              <span
                style={{
                  fontSize: "0.7rem",
                  fontWeight: "600",
                  padding: "2px 8px",
                  borderRadius: "9999px",
                  background: c.flagged_disparity ? "rgba(244, 63, 94, 0.2)" : "rgba(16, 185, 129, 0.2)",
                  color: c.flagged_disparity ? "#fb7185" : "#34d399",
                }}
              >
                {c.flagged_disparity ? "Disparity Flagged" : "Parity Cleared"}
              </span>
            </div>

            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px", marginTop: "14px" }}>
              <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)" }}>
                <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Total Evaluated</div>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: "#f8fafc" }}>{c.total_candidates}</div>
              </div>

              <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)" }}>
                <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Average Score</div>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: "#38bdf8" }}>{c.average_score}/100</div>
              </div>

              <div style={{ padding: "10px", borderRadius: "8px", background: "rgba(15, 23, 42, 0.6)", gridColumn: "span 2" }}>
                <div style={{ fontSize: "0.72rem", color: "#94a3b8" }}>Recommendation Rate (Proceed)</div>
                <div style={{ fontSize: "1.2rem", fontWeight: "800", color: c.flagged_disparity ? "#fbbf24" : "#34d399" }}>
                  {Math.round(c.proceed_rate * 100)}%
                </div>
              </div>
            </div>
          </div>
        ))}
      </div>

      {/* Governance Explanatory Card */}
      <div className="glass-card" style={{ padding: "22px" }}>
        <h3 style={{ fontSize: "0.95rem", fontWeight: "700", color: "#f8fafc", marginBottom: "8px" }}>
          About the 4/5ths Rule (80% Disparate Impact Standard)
        </h3>
        <p style={{ fontSize: "0.8rem", color: "#94a3b8", lineHeight: "1.6" }}>
          In employment governance, the four-fifths rule states that a selection rate for any group which is less than 80% of the selection rate for the highest group is generally regarded as evidence of adverse impact. In JASIPA, detected disparities never reject candidates; instead, they generate explicit audit warnings on candidate evidence dockets to safeguard fair human evaluation.
        </p>
      </div>
    </div>
  );
}
