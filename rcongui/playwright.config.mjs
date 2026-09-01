import { defineConfig } from "@playwright/test";

const baseURL = process.env.PLAYWRIGHT_BASE_URL || "http://127.0.0.1:3000";

export default defineConfig({
  testDir: "./e2e",
  outputDir: "./test-results",
  snapshotPathTemplate: "{testDir}/{testFilePath}-snapshots/{arg}{ext}",
  fullyParallel: true,
  forbidOnly: Boolean(process.env.CI),
  // CI failures should surface quickly and deterministically. Retrying every
  // failing route can turn a broken shell into an hour-long feedback loop.
  retries: 0,
  // Vite serves a large, route-split admin application in fake mode. Running
  // several browsers against the two-core hosted runner makes initial route
  // compilation slower rather than faster and can race late fixture loads.
  // One CI worker keeps the release gate deterministic; local runs may still
  // use Playwright's automatically selected worker count.
  workers: process.env.CI ? 1 : undefined,
  timeout: process.env.CI ? 60_000 : 30_000,
  expect: {
    timeout: process.env.CI ? 12_000 : 8_000,
    toHaveScreenshot: {
      animations: "disabled",
      caret: "hide",
      // Chromium's font rasterization differs slightly between Windows and
      // the Linux CI runner. Structural and semantic assertions remain strict.
      maxDiffPixelRatio: 0.025,
    },
  },
  reporter: process.env.CI
    ? [["line"], ["html", { open: "never", outputFolder: "playwright-report" }]]
    : [
        ["list"],
        ["html", { open: "never", outputFolder: "playwright-report" }],
      ],
  use: {
    baseURL,
    locale: "de-DE",
    timezoneId: "Europe/Berlin",
    colorScheme: "dark",
    reducedMotion: "reduce",
    screenshot: "only-on-failure",
    trace: "retain-on-failure",
    video: "retain-on-failure",
  },
  projects: [
    {
      name: "chromium",
      use: { browserName: "chromium" },
    },
  ],
  // CI owns the Vite process explicitly so a completed browser suite cannot
  // be held open by an orphaned npm child process. Local runs keep the
  // convenient Playwright-managed fake server.
  webServer: process.env.CI
    ? undefined
    : {
        command: "npm run dev:fake -- --host 127.0.0.1 --port 3000",
        url: baseURL,
        // Reusing an arbitrary local server can silently capture snapshots from
        // the normal live mode instead of the deterministic fake backend.
        reuseExistingServer: false,
        timeout: 120_000,
        stdout: "pipe",
        stderr: "pipe",
      },
});
