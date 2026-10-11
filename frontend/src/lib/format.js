// Display formatting. All dates are shown in India Standard Time (Asia/Kolkata).
export const TIME_ZONE = "Asia/Kolkata";

const HAS_ZONE = /(Z|[+-]\d{2}:?\d{2})$/i;

/** Parses API timestamps. The backend stores naive UTC datetimes and serialises them without an offset,
 * so a timestamp without a zone is treated as UTC (JavaScript would otherwise read it as local time). */
export function parseTimestamp(value) {
  if (value == null || value === "") return null;
  if (value instanceof Date) return Number.isNaN(value.getTime()) ? null : value;
  if (typeof value === "number") return new Date(value);
  const text = String(value).trim();
  const iso = /^\d{4}-\d{2}-\d{2}T/.test(text) && !HAS_ZONE.test(text) ? `${text}Z` : text;
  const date = new Date(iso);
  return Number.isNaN(date.getTime()) ? null : date;
}

export function fmtDate(value) {
  const date = parseTimestamp(value);
  return date ? date.toLocaleDateString("en-IN", { day: "numeric", month: "short", year: "numeric", timeZone: TIME_ZONE }) : "—";
}

export function fmtDateTime(value) {
  const date = parseTimestamp(value);
  if (!date) return "—";
  return `${date.toLocaleString("en-IN", { day: "numeric", month: "short", year: "numeric", hour: "2-digit", minute: "2-digit", hour12: true, timeZone: TIME_ZONE })} IST`;
}

export const fmtScore = (value) => (value == null || Number.isNaN(Number(value)) ? "—" : Number(value).toFixed(1));
export const fmtPct = (value) => (value == null ? "—" : `${Math.round(Number(value) * 100)}%`);
export const fmtRatio = (value) => (value == null ? "—" : Number(value).toFixed(2));
export const fmtP = (value) => (value == null ? "—" : Number(value) < 0.001 ? "< 0.001" : Number(value).toFixed(3));
export const initials = (name = "") => name.split(/\s+/).filter(Boolean).slice(0, 2).map((p) => p[0]).join("").toUpperCase() || "?";
export const latest = (list) => (list && list.length ? list[list.length - 1] : null);

/* ---------- Bias presentation (three states + significance qualifier) ---------- */
const DISPLAY_FOR = {
  STATISTICALLY_SUPPORTED_DISPARITY: "DISPARITY_DETECTED", POTENTIAL_DISPARITY_INDICATOR: "DISPARITY_DETECTED",
  INSUFFICIENT_DATA: "INSUFFICIENT_DATA", NO_INDICATOR_DETECTED: "NO_INDICATOR_DETECTED", REFERENCE_GROUP: "NO_INDICATOR_DETECTED",
};
export const BIAS_DISPLAY = {
  DISPARITY_DETECTED: { label: "Disparity detected", tone: "warning" },
  NO_INDICATOR_DETECTED: { label: "No indicator detected", tone: "success" },
  INSUFFICIENT_DATA: { label: "Insufficient data", tone: "" },
};

/** Maps a stored bias status to {label, tone, qualifier}. Language checks are not cohort disparities. */
export function biasPresentation(status, checkType) {
  const display = DISPLAY_FOR[status] || "INSUFFICIENT_DATA";
  if (checkType === "decision_rationale_language" && display === "DISPARITY_DETECTED") {
    return { label: "Proxy language found", tone: "warning", qualifier: null };
  }
  if (checkType === "threshold_consistency" && display === "DISPARITY_DETECTED") {
    return { label: "Threshold gap", tone: "warning", qualifier: null };
  }
  const base = BIAS_DISPLAY[display];
  const qualifier = status === "STATISTICALLY_SUPPORTED_DISPARITY" ? "statistically significant"
    : status === "POTENTIAL_DISPARITY_INDICATOR" ? "not statistically significant" : null;
  return { ...base, tone: status === "STATISTICALLY_SUPPORTED_DISPARITY" ? "danger" : base.tone, qualifier };
}

/** Resume sections for display; falls back to splitting plain text into paragraphs. */
export function resumeSections(sections, text) {
  if (sections && sections.length) return sections;
  if (!text) return [];
  return [{ title: null, key: "body", lines: text.split(/\n+/).map((l) => l.trim()).filter(Boolean) }];
}
