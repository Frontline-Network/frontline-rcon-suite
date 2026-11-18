import { execFileSync } from "node:child_process";
import { expect, test } from "@playwright/test";
import { openDemoPage } from "./helpers.mjs";

const backend = process.env.BARRICADE_BROWSER_TEST_CONTAINER;
test.skip(!backend, "requires disposable isolated API bridge");
function invoke(action, input = "") {
  const output = execFileSync("docker", ["exec", "-i", backend, "python", "/opt/barricade-browser-bridge.py", action],
    { input, encoding: "utf8", timeout: 20000 });
  return JSON.parse(output.trim().split("\n").at(-1));
}

test("operator can inspect an interrupted send through the real API and PostgreSQL", async ({ page }) => {
  test.setTimeout(90_000);
  await page.route("**/*", async (route) => {
    const url = new URL(route.request().url());
    if (url.hostname !== "127.0.0.1" && url.hostname !== "localhost") return route.abort();
    const command = url.pathname.split("/").at(-1);
    if (["get_barricade_scan_reviews", "get_barricade_scan_status", "resolve_barricade_scan_review"].includes(command)) {
      const action = command === "get_barricade_scan_status" ? "status" : command.startsWith("get_") ? "get" : "post";
      const result = invoke(action, route.request().postData() || "");
      return route.fulfill({ status: result.status, contentType: "application/json", body: JSON.stringify(result.body) });
    }
    return route.continue();
  });
  const main = await openDemoPage(page, "/records/blacklists/manage", { language: "en" });
  await main.getByRole("button", { name: "Review Barricade scans", exact: true }).click();
  const panel = main.getByTestId("barricade-scan-review");
  await expect(panel.getByText("The scan may still be sending.", { exact: false })).toBeVisible({ timeout: 30_000 });
  await panel.getByRole("combobox", { name: "Decision" }).click();
  await expect(page.getByRole("option", { name: "Authorize another scan" })).toHaveCount(0);
  await page.getByRole("option", { name: "Check delivery state" }).click();
  await panel.getByLabel("Reason").fill("Synthetic interrupted delivery");
  await panel.getByRole("button", { name: "Save decision" }).click();
  await expect(panel.getByText("Confirmation is missing.", { exact: false })).toBeVisible({ timeout: 30_000 });
  expect(invoke("audit")).toEqual({ status: "review", decision: "recover", actor: "Operator" });
});
