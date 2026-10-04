import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

export default defineConfig({
  testDir: ".", testMatch: "*.spec.mjs", workers: 1, retries: 0,
  timeout: 45_000, expect: { timeout: 10_000 },
  reporter: [["list"], ["json", { outputFile: fileURLToPath(new URL("./release-test-results/results.json", import.meta.url)) }]],
  outputDir: "release-test-results/artifacts",
  use: {
    baseURL: process.env.RELEASE_SMOKE_URL || "http://127.0.0.1:8049",
    viewport: { width: 1440, height: 1000 }, locale: "de-DE",
    screenshot: "only-on-failure", trace: "retain-on-failure",
  },
});
