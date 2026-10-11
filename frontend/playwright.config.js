// End-to-end tests against the real stack: a freshly seeded SQLite database (Kaggle dataset import),
// the FastAPI backend with its agents and sandbox, and the Vite frontend.
import { defineConfig, devices } from "@playwright/test";

const API = "http://localhost:8001";
const DB = "sqlite:///./e2e.db";

export default defineConfig({
  testDir: "./e2e",
  timeout: 90_000,
  fullyParallel: false,
  workers: 1,
  reporter: [["list"], ["json", { outputFile: "../docs/test-results/e2e-results.json" }]],
  use: { baseURL: "http://localhost:5175", viewport: { width: 1280, height: 800 }, trace: "retain-on-failure" },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"], viewport: { width: 1280, height: 800 } } }],
  webServer: [
    {
      cwd: "../backend",
      command: `sh -c "rm -rf e2e.db e2e_uploads && DATABASE_URL=${DB} UPLOAD_DIR=./e2e_uploads .venv/bin/python scripts/seed_data.py --demo-accounts --per-category 6 && DATABASE_URL=${DB} UPLOAD_DIR=./e2e_uploads .venv/bin/uvicorn app.main:app --port 8001"`,
      url: `${API}/health`,
      env: { LLM_PROVIDER: "mock", GEMINI_API_KEY: "", CORS_ORIGINS: '["http://localhost:5175"]', SECRET_KEY: "e2e-only-secret-key-not-for-production" },
      timeout: 120_000,
      reuseExistingServer: false,
    },
    {
      command: "npx vite --port 5175 --strictPort",
      url: "http://localhost:5175",
      env: { VITE_API_URL: API },
      timeout: 60_000,
      reuseExistingServer: false,
    },
  ],
});
