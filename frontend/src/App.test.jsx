import { describe, expect, vi, beforeEach } from "vitest";
import { render, screen, act } from "@testing-library/react";
import { tc } from "./test/tc";

vi.mock("./services/api", () => ({
  getDashboard: vi.fn(), login: vi.fn(), register: vi.fn(), getCandidates: vi.fn(), getJobs: vi.fn(),
}));
import * as api from "./services/api";
import App from "./App";

const token = (exp) => `x.${btoa(JSON.stringify({ exp }))}.y`;
const summary = { total_candidates: 50, open_jobs: 6, awaiting_decision: 2, bias_attention: 0,
  pipeline: [{ label: "Applied", count: 2 }, { label: "Screened", count: 48 }], awaiting_list: [] };

beforeEach(() => {
  api.getDashboard.mockResolvedValue(summary);
  api.getCandidates.mockResolvedValue([]);
  api.getJobs.mockResolvedValue([]);
});

describe("App shell", () => {
  tc("Session – restore after refresh", "valid stored HR token and user", "dashboard shown without signing in again; awaiting count in navigation", async () => {
    localStorage.setItem("token", token(Date.now() / 1000 + 3600));
    localStorage.setItem("user", JSON.stringify({ role: "HR", name: "Sarah Connor", email: "hr@jasipa.ai" }));
    render(<App />);
    expect(await screen.findByRole("heading", { name: "Dashboard" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Candidates/ })).toHaveTextContent("2");
  });
  tc("Session – expired token", "stored token whose exp is in the past", "sign-in page shown", () => {
    localStorage.setItem("token", token(Date.now() / 1000 - 10));
    localStorage.setItem("user", JSON.stringify({ role: "HR", name: "Sarah" }));
    render(<App />);
    expect(screen.getByRole("button", { name: /^Sign in/ })).toBeInTheDocument();
  });
  tc("Navigation – hash routing", "valid HR session; hash changed to #/candidates", "Candidates page rendered and its nav link marked current", async () => {
    localStorage.setItem("token", token(Date.now() / 1000 + 3600));
    localStorage.setItem("user", JSON.stringify({ role: "HR", name: "Sarah" }));
    render(<App />);
    await screen.findByRole("heading", { name: "Dashboard" });
    await act(async () => { window.location.hash = "/candidates"; window.dispatchEvent(new HashChangeEvent("hashchange")); });
    expect(await screen.findByRole("heading", { name: "Candidates" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: /Candidates/ })).toHaveAttribute("aria-current", "page");
  });
  tc("Session – expiry during use", "API signals jasipa:session-expired", "user returned to sign-in with an expiry message", async () => {
    localStorage.setItem("token", token(Date.now() / 1000 + 3600));
    localStorage.setItem("user", JSON.stringify({ role: "HR", name: "Sarah" }));
    render(<App />);
    await screen.findByRole("heading", { name: "Dashboard" });
    await act(async () => { window.dispatchEvent(new Event("jasipa:session-expired")); });
    expect(await screen.findByText(/Your session expired/)).toBeInTheDocument();
  });
});
