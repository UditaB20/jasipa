import { it } from "vitest";

/** Registers a test whose title carries the documentation fields used by scripts/test_report.py. */
export function tc(feature, input, expected, fn) {
  it(`${feature} — input: ${input} — expected: ${expected}`, fn);
}
