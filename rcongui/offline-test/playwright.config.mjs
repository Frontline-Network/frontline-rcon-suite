import { defineConfig } from "@playwright/test";
import { fileURLToPath } from "node:url";

export default defineConfig({
  testDir: ".",
  testMatch: "*.spec.mjs",
  timeout: 30000,
  workers: 1,
  use: {
    baseURL: "http://127.0.0.1:13123",
    browserName: "chromium",
    launchOptions: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH
      ? { executablePath: process.env.PLAYWRIGHT_CHROMIUM_EXECUTABLE_PATH, args: ["--no-sandbox"] }
      : {},
  },
  webServer: {
    cwd: fileURLToPath(new URL("..", import.meta.url)),
    command: "node ./node_modules/vite/bin/vite.js --host 127.0.0.1 --port 13123 --strictPort",
    url: "http://127.0.0.1:13123/",
    env: { ...process.env, REACT_APP_API_URL: "/api/", REACT_APP_VERSION: "v0.9.12" },
    reuseExistingServer: false,
    timeout: 60000,
  },
});
