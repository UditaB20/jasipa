import { describe, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { tc } from "../test/tc";

vi.mock("../services/api", () => ({
  getCandidates: vi.fn(), getJobs: vi.fn(), uploadResume: vi.fn(),
}));
import * as api from "../services/api";
import CandidatesList, { validateResumeFile } from "./CandidatesList";
import { ToastProvider } from "../components/ui";

const file = (name, size) => ({ name, size });
const candidates = [
  { candidate_id: "a", name: "Kaggle resume #1", email: "kaggle-1@dataset.invalid", source: "dataset_import", dataset_category: "HR", current_stage: "RESUME_SCREENED", skills_extracted: ["Payroll"], target_jd_id: "J1", created_at: "2026-10-11T03:00:00" },
  { candidate_id: "b", name: "Robin Portal", email: "robin@example.org", source: "candidate_portal", current_stage: "HUMAN_REVIEW_PENDING", skills_extracted: ["Python"], target_jd_id: "J1", created_at: "2026-10-11T04:00:00" },
];

beforeEach(() => {
  api.getCandidates.mockResolvedValue(candidates);
  api.getJobs.mockResolvedValue([{ jd_id: "J1", title: "HR Specialist" }]);
});

describe("Candidates page", () => {
  tc("Resume upload – client-side file validation", "exe file; 6 MB PDF; empty DOCX; valid PDF", "type, size and empty errors; null for a valid file", () => {
    expect(validateResumeFile(file("cv.exe", 10))).toMatch(/PDF or Word/);
    expect(validateResumeFile(file("cv.pdf", 6 * 1024 * 1024))).toMatch(/larger than 5 MB/);
    expect(validateResumeFile(file("cv.docx", 0))).toMatch(/empty/);
    expect(validateResumeFile(file("cv.pdf", 2048))).toBeNull();
  });
  tc("Candidates list – provenance and filters", "one dataset record and one portal applicant; filter by source and stage", "dataset row labelled 'Kaggle dataset · HR'; filters narrow the list", async () => {
    render(<ToastProvider><CandidatesList /></ToastProvider>);
    expect(await screen.findByText("Kaggle dataset · HR")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Filter by source"), { target: { value: "candidate_portal" } });
    expect(screen.queryByText("Kaggle resume #1")).not.toBeInTheDocument();
    expect(screen.getByText("Robin Portal")).toBeInTheDocument();
    fireEvent.change(screen.getByLabelText("Filter by stage"), { target: { value: "decided" } });
    expect(screen.getByText("No candidates match these filters")).toBeInTheDocument();
  });
  tc("Add-candidate form – validation", "submit the drawer with no name, invalid email and no file", "inline errors for name, email and file; upload API not called", async () => {
    render(<ToastProvider><CandidatesList /></ToastProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Add candidate/ }));
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "not-an-email" } });
    fireEvent.click(screen.getByRole("button", { name: "Add and screen" }));
    expect(await screen.findByText("Enter the candidate's full name.")).toBeInTheDocument();
    expect(screen.getByText("Enter a valid email address.")).toBeInTheDocument();
    expect(screen.getByText("Choose a resume file.")).toBeInTheDocument();
    expect(api.uploadResume).not.toHaveBeenCalled();
  });
  tc("Add-candidate form – server error handling", "valid form; API rejects with 'This file is not a valid PDF document.'", "error shown inside the drawer; drawer stays open", async () => {
    api.uploadResume.mockRejectedValue(new Error("This file is not a valid PDF document."));
    const { container } = render(<ToastProvider><CandidatesList /></ToastProvider>);
    fireEvent.click(await screen.findByRole("button", { name: /Add candidate/ }));
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Jordan Rivera" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "jordan@example.com" } });
    const input = container.ownerDocument.querySelector('input[type="file"]');
    fireEvent.change(input, { target: { files: [new File(["%PDF-fake"], "cv.pdf", { type: "application/pdf" })] } });
    fireEvent.click(screen.getByRole("button", { name: "Add and screen" }));
    await waitFor(() => expect(screen.getByText("Upload failed")).toBeInTheDocument());
    expect(screen.getByText("This file is not a valid PDF document.")).toBeInTheDocument();
  });
});
