import { readFileSync } from "node:fs";
import { expect, test } from "@playwright/test";

const version = "v0.9.34";
test.skip(process.env.REVIEWED_REBUILD_TAG !== version, "v0.9.34 editorial rebuild");

test("Updates displays the complete reviewed German and English changelog", async ({ page, context }) => {
  const reviewed = readFileSync(new URL("../../docs/releases/v0.9.34.md", import.meta.url), "utf8").replace(/\r\n/g, "\n").trim();
  const login = await context.request.post("/api/login", {
    data: { username: "hotfix", password: "isolated-test-only" },
  });
  expect(login.ok()).toBe(true);
  const response = await context.request.get(`/api/get_update_channel?frontend_version=${version}`);
  expect(response.ok()).toBe(true);
  const { result } = await response.json();
  expect(result.source).toBe("bundled");
  const current = result.releases.find(entry => entry.current);
  expect(current?.tag_name).toBe(version);
  expect(current.body.replace(/\r\n/g, "\n").trim()).toBe(reviewed);

  await page.goto(`/updates?release=${version}`);
  const article = page.getByRole("article");
  for (const [, title] of reviewed.matchAll(/^#{2,3} (.+)$/gm)) {
    await expect(article.getByRole("heading", { name: title, exact: true })).toBeVisible();
  }
  await expect(article).toContainText("429 commits");
});
