import { describe, expect } from "vitest";
import { biasPresentation, fmtDate, fmtDateTime, fmtP, fmtRatio, parseTimestamp, resumeSections } from "./format";
import { tc } from "../test/tc";

describe("Date formatting (IST)", () => {
  tc("Date formatting – naive API timestamp", "'2026-10-11T03:36:19' (UTC, no zone)", "parsed as UTC, shown as 11 Oct 2026, 09:06 am IST", () => {
    expect(parseTimestamp("2026-10-11T03:36:19").toISOString()).toBe("2026-10-11T03:36:19.000Z");
    expect(fmtDateTime("2026-10-11T03:36:19")).toBe("11 Oct 2026, 09:06 am IST");
  });
  tc("Date formatting – day boundary", "'2026-10-11T20:00:00Z'", "date rolls over to 12 Oct in IST", () => {
    expect(fmtDate("2026-10-11T20:00:00Z")).toBe("12 Oct 2026");
  });
  tc("Date formatting – explicit offsets and microseconds", "'2026-10-11T03:36:19.123456' and '2026-10-11T09:06:19+05:30'", "both resolve to the same IST time", () => {
    expect(fmtDateTime("2026-10-11T03:36:19.123456")).toBe(fmtDateTime("2026-10-11T09:06:19+05:30"));
  });
  tc("Date formatting – missing or invalid values", "null, '' and 'not-a-date'", "an em dash, no exception", () => {
    for (const v of [null, "", "not-a-date"]) expect(fmtDateTime(v)).toBe("—");
  });
});

describe("Bias presentation", () => {
  tc("Bias labels – three states", "the four stored statuses", "Disparity detected / No indicator detected / Insufficient data with significance qualifiers", () => {
    expect(biasPresentation("STATISTICALLY_SUPPORTED_DISPARITY")).toMatchObject({ label: "Disparity detected", qualifier: "statistically significant", tone: "danger" });
    expect(biasPresentation("POTENTIAL_DISPARITY_INDICATOR")).toMatchObject({ label: "Disparity detected", qualifier: "not statistically significant" });
    expect(biasPresentation("NO_INDICATOR_DETECTED")).toMatchObject({ label: "No indicator detected", qualifier: null });
    expect(biasPresentation("INSUFFICIENT_DATA")).toMatchObject({ label: "Insufficient data" });
  });
  tc("Bias labels – non-cohort checks", "rationale-language and threshold checks flagged", "labelled as proxy language / threshold gap, not as cohort disparity", () => {
    expect(biasPresentation("POTENTIAL_DISPARITY_INDICATOR", "decision_rationale_language").label).toBe("Proxy language found");
    expect(biasPresentation("POTENTIAL_DISPARITY_INDICATOR", "threshold_consistency").label).toBe("Threshold gap");
  });
  tc("Bias metrics formatting", "ratio 0.5, p 0.0004, p null", "'0.50', '< 0.001', '—'", () => {
    expect(fmtRatio(0.5)).toBe("0.50");
    expect(fmtP(0.0004)).toBe("< 0.001");
    expect(fmtP(null)).toBe("—");
  });
});

describe("Resume sections", () => {
  tc("Resume display – fallback without sections", "plain text with blank lines, no section data", "one untitled section with one line per paragraph", () => {
    expect(resumeSections([], "Line one\n\nLine two")).toEqual([{ title: null, key: "body", lines: ["Line one", "Line two"] }]);
    expect(resumeSections(null, "")).toEqual([]);
  });
});
