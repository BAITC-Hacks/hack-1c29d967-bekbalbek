import { defineConfig } from "@playwright/test";

// Runs against a live stack: `make api` (OPENAI_MODEL=scripted:auto works without a key) and `pnpm dev`.
export default defineConfig({
  testDir: "e2e",
  timeout: 90_000,
  expect: { timeout: 15_000 },
  reporter: "list",
  outputDir: "e2e/results",
  use: {
    baseURL: process.env.E2E_BASE_URL ?? "http://localhost:5173",
    viewport: { width: 1440, height: 900 },
    screenshot: "only-on-failure",
  },
});
