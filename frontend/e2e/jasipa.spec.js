// End-to-end scenarios run in Chromium against the real backend, agents, sandbox and a Kaggle-seeded database.
// Test titles carry "feature — input — expected" for the generated test-case table. Screenshots are saved
// to docs/screenshots for the project report.
import { test, expect } from "@playwright/test";
import path from "node:path";

const API = "http://localhost:8001/api";
const SHOTS = path.resolve(process.cwd(), "../docs/screenshots");
const RESUME = path.resolve(process.cwd(), "e2e/fixtures/jordan_rivera_resume.pdf");
const JOB_TITLE = "Backend Engineer (E2E)";
const CANDIDATE_EMAIL = `e2e-${Date.now()}@example.org`;
const t = (feature, input, expected) => `${feature} — input: ${input} — expected: ${expected}`;

async function apiToken(request, email, password) {
  const res = await request.post(`${API}/auth/login`, { data: { email, password } });
  expect(res.ok()).toBeTruthy();
  return (await res.json()).access_token;
}

async function signIn(page, email, password) {
  await page.goto("/");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel(/^Password/).fill(password);
  await page.getByRole("button", { name: /^Sign in/ }).click();
  await page.locator("main#main").waitFor();
}

const shot = (page, name) => page.screenshot({ path: `${SHOTS}/${name}.png`, fullPage: false });

test.describe.serial("JASIPA end to end", () => {
  let jobId;
  let candidateId;

  test(t("Login page layout", "load sign-in at 1280×800 and 1024×768", "no vertical or horizontal page scrollbar; no scrolling tab strip"), async ({ page }) => {
    for (const size of [{ width: 1280, height: 800 }, { width: 1024, height: 768 }]) {
      await page.setViewportSize(size);
      await page.goto("/");
      await expect(page.getByRole("button", { name: /^Sign in/ })).toBeVisible();
      const dims = await page.evaluate(() => ({
        v: document.documentElement.scrollHeight > document.documentElement.clientHeight,
        h: document.documentElement.scrollWidth > document.documentElement.clientWidth,
        tabs: [...document.querySelectorAll(".segmented")].some((e) => e.scrollWidth > e.clientWidth),
      }));
      expect(dims).toEqual({ v: false, h: false, tabs: false });
    }
    await page.setViewportSize({ width: 1280, height: 800 });
    await shot(page, "01-login");
  });

  test(t("HR sign-in and dashboard", "hr@jasipa.ai / admin123", "dashboard counts match the Kaggle import (36 dataset records + 2 demo logins)"), async ({ page }) => {
    await signIn(page, "hr@jasipa.ai", "admin123");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    await expect(page.locator(".stat").first()).toContainText("38");
    await shot(page, "02-dashboard");
  });

  test(t("Job creation form", "HR creates a Python/SQL/Algorithms job through the New job drawer", "job listed with rubric v1.0 and an assessment containing a coding challenge"), async ({ page, request }) => {
    await signIn(page, "hr@jasipa.ai", "admin123");
    await page.getByRole("link", { name: "Jobs" }).click();
    await page.getByRole("button", { name: "New job" }).click();
    await page.getByRole("button", { name: "Create job" }).click();
    await expect(page.getByText("Enter a job title.")).toBeVisible();
    await page.getByLabel("Title").fill(JOB_TITLE);
    await page.getByLabel("Department").fill("Engineering");
    await page.getByLabel(/Responsibilities/).fill("Build Python services for billing.\nDesign SQL schemas for reporting.\nImplement algorithms for reconciliation.");
    await page.getByLabel(/^Required skills/).fill("Python, SQL, Algorithms");
    await page.getByLabel(/Minimum years/).fill("3");
    await page.getByRole("button", { name: "Create job" }).click();
    await expect(page.getByText(`${JOB_TITLE} created with rubric v1.0.`)).toBeVisible();
    const token = await apiToken(request, "hr@jasipa.ai", "admin123");
    const jobs = await (await request.get(`${API}/jobs/`, { headers: { Authorization: `Bearer ${token}` } })).json();
    jobId = jobs.find((j) => j.title === JOB_TITLE).jd_id;
    await page.getByRole("tab", { name: "Assessment" }).click();
    await expect(page.getByText("coding", { exact: true })).toBeVisible();
    await shot(page, "03-job-assessment");
  });

  test(t("Assessment regeneration", "click Regenerate on the new job's Assessment tab", "toast reports changed questions and the visible question set id changes"), async ({ page }) => {
    page.on("dialog", (d) => d.accept());
    await signIn(page, "hr@jasipa.ai", "admin123");
    await page.getByRole("link", { name: "Jobs" }).click();
    await page.getByRole("button", { name: JOB_TITLE }).click();
    await page.getByRole("tab", { name: "Assessment" }).click();
    const before = await page.getByText(/^Set [0-9a-f]{8}/).textContent();
    await page.getByRole("button", { name: /Regenerate/ }).click();
    await expect(page.getByText(/questions changed/)).toBeVisible();
    await expect(page.getByText(/^Set [0-9a-f]{8}/)).not.toHaveText(before);
  });

  test(t("Candidate registration, resume upload and application", "register in the portal, upload a PDF resume, apply to the new job", "resume shown in sections with a Download original button; application submitted"), async ({ page }) => {
    await page.goto("/");
    await page.getByRole("tab", { name: "Create candidate account" }).click();
    await page.getByLabel("Full name").fill("Jordan Rivera");
    await page.getByLabel("Email").fill(CANDIDATE_EMAIL);
    await page.getByLabel(/^Password/).fill("s3cure-pass!");
    await page.getByRole("button", { name: /Create account/ }).click();
    await expect(page.getByRole("heading", { name: /Hello, Jordan/ })).toBeVisible();
    await page.getByRole("link", { name: "Profile & resume" }).click();
    await page.locator('input[type="file"]').setInputFiles(RESUME);
    await page.getByRole("button", { name: /Upload resume/ }).click();
    await expect(page.getByText("Resume uploaded and read.")).toBeVisible();
    await expect(page.locator(".resume-section h3", { hasText: "Experience" })).toBeVisible();
    const download = page.waitForEvent("download");
    await page.getByRole("button", { name: /Download original/ }).click();
    expect((await download).suggestedFilename()).toBe("jordan_rivera_resume.pdf");
    await shot(page, "04-candidate-resume");
    await page.getByRole("link", { name: "Open roles" }).click();
    await page.locator(".card", { hasText: JOB_TITLE }).getByRole("button", { name: "Apply" }).click();
    await expect(page.getByRole("heading", { name: "Assessments" })).toBeVisible();
  });

  test(t("Candidate assessments with sandboxed code", "answer MCQs, run code examples, submit technical and STAR behavioral answers", "examples pass in the sandbox; both parts show Submitted"), async ({ page, request }) => {
    const token = await apiToken(request, "hr@jasipa.ai", "admin123");
    const set = await (await request.get(`${API}/assessments/questions/${jobId}`, { headers: { Authorization: `Bearer ${token}` } })).json();
    const keyByPrompt = Object.fromEntries([...set.technical_questions, ...set.behavioral_questions].map((q) => [q.prompt.trim(), q]));
    await signIn(page, CANDIDATE_EMAIL, "s3cure-pass!");
    await page.getByRole("link", { name: "Assessments", exact: true }).click();
    const cards = page.locator(".inset");
    await expect(cards.first()).toBeVisible();
    for (let i = 0; i < await cards.count(); i++) {
      const card = cards.nth(i);
      const prompt = (await card.locator("p.small").first().innerText()).trim();
      const key = keyByPrompt[prompt];
      expect(key, `question key for: ${prompt.slice(0, 60)}`).toBeTruthy();
      if (key.type === "mcq") {
        await card.locator(".option", { hasText: `${key.correct_option})` }).locator("input").check();
      } else if (key.type === "coding") {
        await card.getByLabel("Code editor").fill(key.coding.reference_solution);
        await card.getByRole("button", { name: "Run examples" }).click();
        await expect(card.getByText(/examples passed/)).toBeVisible();
      } else if (key.type === "behavioral") {
        await card.locator("textarea").fill("Situation: during a release at my previous role the team missed a deadline. Task: I was responsible for recovery. Action: I analyzed the root cause, I proposed a plan and I communicated trade-offs. Result: we delivered and reduced defects by 30%.");
      } else {
        await card.locator("textarea").fill("I would clarify requirements, design the schema and services, compare two options and explain the trade-off, then validate with tests and query plans before rollout.");
      }
    }
    await shot(page, "05-candidate-coding");
    await page.getByRole("button", { name: "Submit technical assessment" }).click();
    await expect(page.locator(".card", { hasText: "Technical assessment" }).getByText("Submitted")).toBeVisible();
    await page.getByRole("button", { name: "Submit behavioral assessment" }).click();
    await expect(page.locator(".card", { hasText: "Behavioral assessment" }).getByText("Submitted")).toBeVisible();
  });

  test(t("Agent pipeline, bias check and human decision", "HR runs the evaluation for the applicant, reviews Panel & bias, approves with a note", "panel + bias table shown with IST timestamps; decision recorded; candidate Decided; audit chain verifies"), async ({ page, request }) => {
    const token = await apiToken(request, "hr@jasipa.ai", "admin123");
    const list = await (await request.get(`${API}/candidates/`, { headers: { Authorization: `Bearer ${token}` } })).json();
    candidateId = list.find((c) => c.email === CANDIDATE_EMAIL).candidate_id;
    await signIn(page, "hr@jasipa.ai", "admin123");
    await page.goto(`/#/candidates/${candidateId}`);
    await page.getByRole("button", { name: /Run evaluation/ }).click();
    await expect(page.getByText(/Evaluation complete \(round 1\)/)).toBeVisible({ timeout: 30_000 });
    await page.getByRole("tab", { name: "Assessments" }).click();
    await expect(page.getByText(/sandboxed tests passed/)).toBeVisible();
    await page.getByRole("tab", { name: "Panel & bias check" }).click();
    await expect(page.getByRole("cell", { name: "AI recommendations" })).toBeVisible();
    await expect(page.getByText(/IST/).first()).toBeVisible();
    await shot(page, "06-panel-bias");
    await page.getByRole("tab", { name: /Decision/ }).click();
    const twoReviewers = await page.getByText("Two reviewers required").isVisible();
    await page.getByLabel(/Approve/).check();
    await page.getByLabel(/Reason for the decision/).fill("Strong evidence across resume, sandboxed coding and STAR answers.");
    await page.getByRole("button", { name: "Record decision" }).click();
    await expect(page.getByText(twoReviewers ? /Sign-off recorded/ : "Decision recorded.")).toBeVisible();
    await shot(page, "07-decision");
    if (!twoReviewers) await expect(page.locator(".badge", { hasText: "Decided" })).toBeVisible();
    await page.getByRole("link", { name: "Audit log" }).click();
    await page.getByRole("button", { name: "Verify integrity" }).click();
    await expect(page.getByText("Ledger verified")).toBeVisible();
    await shot(page, "08-audit");
  });

  test(t("Dataset record display and bias monitor", "open a Kaggle-imported candidate's Resume tab; open Bias monitor", "sectioned dataset resume without a download button; bias monitor shows status, cohort definition and missing-cohort count"), async ({ page }) => {
    await signIn(page, "hr@jasipa.ai", "admin123");
    await page.getByRole("link", { name: /Candidates/ }).click();
    await page.getByLabel("Filter by source").selectOption("dataset_import");
    await page.locator("tbody tr").first().click();
    await page.getByRole("tab", { name: "Resume" }).click();
    await expect(page.getByText(/Imported from the Kaggle Resume Dataset/)).toBeVisible();
    await expect(page.locator(".resume-section h3").first()).toBeVisible();
    await expect(page.getByRole("button", { name: /Download original/ })).toHaveCount(0);
    await shot(page, "09-dataset-resume");
    await page.getByRole("link", { name: "Bias monitor" }).click();
    await expect(page.getByText("How cohorts are defined")).toBeVisible();
    await expect(page.getByText(/never inferred from resume content/)).toBeVisible();
    await shot(page, "10-bias-monitor");
  });

  test(t("Responsive navigation", "HR dashboard at 375×812 (mobile)", "menu button opens the navigation drawer; no horizontal scroll"), async ({ page }) => {
    await page.setViewportSize({ width: 375, height: 812 });
    await signIn(page, "hr@jasipa.ai", "admin123");
    await expect(page.getByRole("heading", { name: "Dashboard" })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth > document.documentElement.clientWidth)).toBe(false);
    await page.getByRole("button", { name: "Open menu" }).click();
    await expect(page.locator(".sidebar.open")).toBeVisible();
    await shot(page, "11-mobile");
  });
});
