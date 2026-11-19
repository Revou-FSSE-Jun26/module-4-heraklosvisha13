import { defineConfig, devices } from "@playwright/test";

const FRONTEND_URL = process.env.E2E_BASE_URL ?? "http://localhost:3000";
const API_URL = process.env.E2E_API_URL ?? "http://localhost:5001/api";

export default defineConfig({
  testDir: "./e2e",
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 2 : 0,
  workers: process.env.CI ? 1 : undefined,
  reporter: [["list"], ["html", { open: "never" }]],
  expect: { timeout: 10_000 },
  use: {
    baseURL: FRONTEND_URL,
    trace: "on-first-retry",
    screenshot: "only-on-failure",
  },
  projects: [{ name: "chromium", use: { ...devices["Desktop Chrome"] } }],
  // Both servers are reused when already running. The backend needs a reachable
  // database (DATABASE_URL in backend/.env) with migrations applied.
  webServer: [
    {
      command: "../backend/venv/bin/python run.py",
      cwd: "../backend",
      url: `${API_URL}/health`,
      reuseExistingServer: true,
      timeout: 60_000,
    },
    {
      command: "npm run dev",
      url: FRONTEND_URL,
      env: {
        NEXT_PUBLIC_API_BASE_URL: API_URL,
        API_BASE_URL: API_URL,
      },
      reuseExistingServer: true,
      timeout: 120_000,
    },
  ],
});
