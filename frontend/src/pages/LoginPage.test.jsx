import { describe, expect, vi } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import { tc } from "../test/tc";

vi.mock("../services/api", () => ({ login: vi.fn(), register: vi.fn() }));
import * as api from "../services/api";
import LoginPage from "./LoginPage";

describe("Login page", () => {
  tc("Login – successful sign-in", "demo HR account selected and submitted", "login API called with the account; onLogin receives the session", async () => {
    api.login.mockResolvedValue({ access_token: "t", user: { role: "HR", name: "Sarah" } });
    const onLogin = vi.fn();
    render(<LoginPage onLogin={onLogin} />);
    fireEvent.click(screen.getByText("hr@jasipa.ai"));
    fireEvent.click(screen.getByRole("button", { name: /^Sign in/ }));
    await waitFor(() => expect(onLogin).toHaveBeenCalledWith({ access_token: "t", user: { role: "HR", name: "Sarah" } }));
    expect(api.login).toHaveBeenCalledWith("hr@jasipa.ai", "admin123");
  });
  tc("Login – wrong credentials", "API rejects with 'Incorrect email or password.'", "error alert shown; onLogin not called", async () => {
    api.login.mockRejectedValue(new Error("Incorrect email or password."));
    const onLogin = vi.fn();
    render(<LoginPage onLogin={onLogin} />);
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "x@y.com" } });
    fireEvent.change(screen.getByLabelText("Password"), { target: { value: "bad" } });
    fireEvent.click(screen.getByRole("button", { name: /^Sign in/ }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Incorrect email or password.");
    expect(onLogin).not.toHaveBeenCalled();
  });
  tc("Registration – password length (boundary)", "7-character password on the create-account form", "validation message; register API not called", async () => {
    render(<LoginPage onLogin={vi.fn()} />);
    fireEvent.click(screen.getByRole("tab", { name: "Create candidate account" }));
    fireEvent.change(screen.getByLabelText("Full name"), { target: { value: "Robin" } });
    fireEvent.change(screen.getByLabelText("Email"), { target: { value: "robin@example.org" } });
    fireEvent.change(screen.getByLabelText(/^Password/), { target: { value: "1234567" } });
    fireEvent.click(screen.getByRole("button", { name: /Create account/ }));
    expect(await screen.findByText("Use a password with at least 8 characters.")).toBeInTheDocument();
    expect(api.register).not.toHaveBeenCalled();
  });
  tc("Login – no tab scrollbar", "segmented sign-in/register control", "rendered as a non-scrolling segmented control (no .tabs strip)", () => {
    const { container } = render(<LoginPage onLogin={vi.fn()} />);
    expect(container.querySelector(".segmented")).not.toBeNull();
    expect(container.querySelector(".tabs")).toBeNull();
  });
});
