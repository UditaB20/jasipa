import { describe, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, within } from "@testing-library/react";
import { tc } from "../test/tc";

vi.mock("../services/api", () => ({
  getCandidate: vi.fn(), getJobs: vi.fn(), getDecisionStatus: vi.fn(), runFullGraph: vi.fn(), runScreenResume: vi.fn(),
  submitDecision: vi.fn(), downloadResume: vi.fn(),
}));
import * as api from "../services/api";
import CandidateDetail, { BiasCheckCard } from "./CandidateDetail";
import { ToastProvider } from "../components/ui";

const bias = {
  check_id: "b1", flag_status: "POTENTIAL_DISPARITY_INDICATOR", created_at: "2026-10-11T03:00:00", reason: "x",
  cohort_breakdown: { candidate_cohort: "Cohort_B", checks: [
    { check_type: "selection_rate_ai_recommendation", flag_status: "POTENTIAL_DISPARITY_INDICATOR", reason: "detail", pool_status: "POTENTIAL_DISPARITY_INDICATOR",
      pool_summary: "Disparity detected for Cohort_B.", group: { cohort_name: "Cohort_B", n: 6, impact_ratio: 0.5, fisher_p_value: 0.5671 } },
    { check_type: "selection_rate_human_decision", flag_status: "INSUFFICIENT_DATA", reason: "detail", pool_status: "INSUFFICIENT_DATA",
      pool_summary: "Insufficient data.", group: null, sample_size: 0 },
    { check_type: "decision_rationale_language", flag_status: "NO_INDICATOR_DETECTED", reason: "detail" }] },
};
const panel = { decision_id: "d1", recommendation: "PROCEED_TO_HUMAN_REVIEW", merged_score: 82, resume_score: 80, skill_score: 85, culture_score: 80,
  strengths: ["s"], gaps: ["g"], disagreements: [], evidence: ["e"], rubric_version: "1.0", round_number: 1, created_at: "2026-10-11T03:00:00" };

beforeEach(() => {
  api.getCandidate.mockResolvedValue({ candidate_id: "c1", name: "Robin Portal", email: "robin@example.org", source: "candidate_portal", current_stage: "HUMAN_REVIEW_PENDING",
    target_jd_id: "J1", experience_years: 6, skills_extracted: [], screening_results: [], assessments: [], panel_decisions: [panel], bias_checks: [bias],
    human_reviews: [], audit_logs: [], resume_text: "Summary\nBackend engineer.", resume_sections: [{ title: "Summary", lines: ["Backend engineer."] }],
    has_original_file: true, resume_original_filename: "cv.pdf" });
  api.getJobs.mockResolvedValue([{ jd_id: "J1", title: "Backend Engineer" }]);
  api.getDecisionStatus.mockResolvedValue({ can_decide: true, decision_id: "d1", requires_two_reviewers: false, signoffs: [], blocking_reason: null });
});

describe("Candidate dossier", () => {
  tc("Panel & bias UI – concise metrics", "bias check with a flagged AI-stage cohort and an insufficient human stage", "one row per check with cohort, n, impact ratio, Fisher p; pool summary stated once", () => {
    render(<BiasCheckCard bias={bias} />);
    const row = screen.getByText("AI recommendations").closest("tr");
    expect(within(row).getByText("Cohort_B")).toBeInTheDocument();
    expect(within(row).getByText("0.50")).toBeInTheDocument();
    expect(within(row).getByText("0.567")).toBeInTheDocument();
    expect(within(row).getByText("not statistically significant")).toBeInTheDocument();
    expect(screen.getAllByText(/Disparity detected for Cohort_B/)).toHaveLength(1);
    expect(screen.getAllByText("Insufficient data").length).toBeGreaterThan(0);
  });
  tc("Resume tab – original download offered", "candidate with an uploaded file", "sectioned resume and a 'Download original' button that calls the download API", async () => {
    api.downloadResume.mockResolvedValue(new Blob(["%PDF"]));
    globalThis.URL.createObjectURL = vi.fn(() => "blob:x");
    globalThis.URL.revokeObjectURL = vi.fn();
    render(<ToastProvider><CandidateDetail candidateId="c1" /></ToastProvider>);
    fireEvent.click(await screen.findByRole("tab", { name: "Resume" }));
    expect(screen.getByRole("heading", { name: "Summary" })).toBeInTheDocument();
    fireEvent.click(screen.getByRole("button", { name: /Download original/ }));
    expect(api.downloadResume).toHaveBeenCalledWith("c1");
  });
  tc("Decision form – validation", "Record decision with no choice, then with a 5-character note", "'Choose a decision' then the 10-character rule; API not called", async () => {
    render(<ToastProvider><CandidateDetail candidateId="c1" /></ToastProvider>);
    fireEvent.click(await screen.findByRole("tab", { name: /Decision/ }));
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(await screen.findByText("Choose a decision.")).toBeInTheDocument();
    fireEvent.click(screen.getByLabelText(/Approve/));
    fireEvent.change(screen.getByLabelText(/Reason for the decision/), { target: { value: "short" } });
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    expect(await screen.findByText(/at least 10 characters/)).toBeInTheDocument();
    expect(api.submitDecision).not.toHaveBeenCalled();
  });
  tc("Decision form – submission", "Approve with a valid note", "decision API called with the latest panel decision id", async () => {
    api.submitDecision.mockResolvedValue({ outcome: "FINAL", status: { current_stage: "DECIDED" } });
    render(<ToastProvider><CandidateDetail candidateId="c1" /></ToastProvider>);
    fireEvent.click(await screen.findByRole("tab", { name: /Decision/ }));
    fireEvent.click(screen.getByLabelText(/Approve/));
    fireEvent.change(screen.getByLabelText(/Reason for the decision/), { target: { value: "Strong evidence across all stages." } });
    fireEvent.click(screen.getByRole("button", { name: "Record decision" }));
    await vi.waitFor(() => expect(api.submitDecision).toHaveBeenCalledWith({ candidate_id: "c1", decision: "APPROVE", notes: "Strong evidence across all stages.", decision_id: "d1" }));
  });
});
