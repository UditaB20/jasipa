import { describe, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { tc } from "../test/tc";

vi.mock("../services/api", () => ({
  getJobs: vi.fn(), getJobRubric: vi.fn(), getRubricVersions: vi.fn(), createJob: vi.fn(),
  getQuestionSet: vi.fn(), regenerateQuestionSet: vi.fn(), updateJobRubric: vi.fn(),
}));
import * as api from "../services/api";
import JobDescriptions from "./JobDescriptions";
import { ToastProvider } from "../components/ui";

const job = { jd_id: "J1", title: "Financial Analyst", department: "Finance", description: "Build models.\nReport variances.", required_skills: ["Excel"], preferred_skills: [], min_experience: 2, rubric_version: "1.0", created_at: "2026-10-11T03:00:00" };
const set = (id, prompt, created) => ({ question_set_id: id, created_at: created, rubric_version: "1.0", generator: "template", generation_notes: [],
  technical_questions: [{ question_id: "TECH_Q1", type: "scenario", competency_or_skill: "Excel", proficiency: "intermediate", prompt }], behavioral_questions: [] });

beforeEach(() => {
  vi.spyOn(window, "confirm").mockReturnValue(true);
  api.getJobs.mockResolvedValue([job]);
});

async function openAssessment() {
  render(<ToastProvider><JobDescriptions /></ToastProvider>);
  fireEvent.click(await screen.findByRole("tab", { name: "Assessment" }));
  await screen.findByText("Old question about Excel");
}

describe("Assessment regeneration (job page)", () => {
  tc("Regenerate – success", "Regenerate clicked; API returns a new set with 1 of 1 questions changed", "new question shown, old one gone, toast reports the change", async () => {
    api.getQuestionSet.mockResolvedValueOnce(set("old-set-0001", "Old question about Excel", "2026-10-11T03:00:00"))
      .mockResolvedValue(set("new-set-0002", "New question about Excel", "2026-10-11T03:05:00"));
    api.regenerateQuestionSet.mockResolvedValue({ ...set("new-set-0002", "New question about Excel", "2026-10-11T03:05:00"), changed_questions: 1, total_questions: 1 });
    await openAssessment();
    fireEvent.click(screen.getByRole("button", { name: /Regenerate/ }));
    expect(await screen.findByText("New question about Excel")).toBeInTheDocument();
    expect(screen.queryByText("Old question about Excel")).not.toBeInTheDocument();
    expect(await screen.findByText(/1 of 1 questions changed/)).toBeInTheDocument();
  });
  tc("Regenerate – failure is not reported as success", "API rejects with 409 'No different questions could be generated…'", "error alert shown, old questions kept, no success toast", async () => {
    api.getQuestionSet.mockResolvedValue(set("old-set-0001", "Old question about Excel", "2026-10-11T03:00:00"));
    api.regenerateQuestionSet.mockRejectedValue(new Error("No different questions could be generated for this job's current skills and rubric."));
    await openAssessment();
    fireEvent.click(screen.getByRole("button", { name: /Regenerate/ }));
    expect(await screen.findByText(/Regeneration failed/)).toBeInTheDocument();
    expect(screen.getByText("Old question about Excel")).toBeInTheDocument();
    expect(screen.queryByText(/questions changed/)).not.toBeInTheDocument();
  });
  tc("Regenerate – cancelled confirmation", "user dismisses the confirmation dialog", "regenerate API not called", async () => {
    window.confirm.mockReturnValue(false);
    api.getQuestionSet.mockResolvedValue(set("old-set-0001", "Old question about Excel", "2026-10-11T03:00:00"));
    await openAssessment();
    fireEvent.click(screen.getByRole("button", { name: /Regenerate/ }));
    await waitFor(() => expect(api.regenerateQuestionSet).not.toHaveBeenCalled());
  });
  tc("Rubric editor – weight validation", "stage weights edited to 50/40/20 (sum 110)", "warning shown and save disabled", async () => {
    api.getJobRubric.mockResolvedValue({ version: "1.0", resume_weight: 0.4, skill_weight: 0.4, culture_weight: 0.2,
      criteria: { technical_scoring: { mcq_weight: 30, coding_weight: 40, short_answer_weight: 30, passing_threshold: 70 },
        behavioral_scoring: { competencies: [{ competency: "Communication", max_points: 100 }] } } });
    api.getRubricVersions.mockResolvedValue([{ rubric_id: "r1", version: "1.0", resume_weight: 0.4, skill_weight: 0.4, culture_weight: 0.2, created_at: "2026-10-11T03:00:00" }]);
    render(<ToastProvider><JobDescriptions /></ToastProvider>);
    fireEvent.click(await screen.findByRole("tab", { name: "Scoring rubric" }));
    fireEvent.change(await screen.findByLabelText("Resume %"), { target: { value: "50" } });
    expect(screen.getByText(/Stage weights add up to 110%/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: /Save as new version/ })).toBeDisabled();
  });
});
