import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const openRules = async (page) => {
  const main = await openDemoPage(page, "/settings/others/name-kicks");
  const shell = main.getByTestId("config-page-shell");
  const editor = shell.getByTestId("name-kick-rules-editor");
  if (!(await editor.isVisible())) {
    await shell
      .getByRole("navigation", { name: "Konfigurationsbereiche" })
      .getByRole("button", { name: /^Regeln/ })
      .click();
  }
  await expect(editor).toBeVisible();
  return shell;
};

test("name filter templates work in the normal form without JSON escaping", async ({
  page,
}) => {
  const runtimeErrors = collectRuntimeErrors(page);
  const shell = await openRules(page);
  const unreadablePreset = shell.getByTestId("name-kick-preset-unreadable");

  await unreadablePreset.click();
  await expect(unreadablePreset).toHaveAttribute("aria-pressed", "true");

  const testName = shell.getByTestId("name-kick-test-name");
  await testName.fill("★★★");
  await expect(shell.getByTestId("name-kick-test-result")).toContainText(
    "würde entfernt"
  );

  await testName.fill("[FLN]Biene");
  await expect(shell.getByTestId("name-kick-test-result")).toContainText(
    "würde den Namensfilter passieren"
  );
  await expect(shell.getByTestId("config-save-button")).toBeEnabled();

  await shell
    .getByTestId("config-mode-toggle")
    .getByRole("button", { name: "JSON (erweitert)" })
    .click();
  await expect(shell.getByTestId("config-json-editor")).toContainText(
    "a-zA-Z0-9"
  );
  expect(
    runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
  ).toEqual([]);
});

test("an empty custom expression blocks saving", async ({ page }) => {
  const shell = await openRules(page);
  const firstRule = shell.getByTestId("name-kick-rule-0");

  await firstRule.fill("");
  await expect(
    shell.getByText(/leere RegEx würde jeden Spielernamen/i)
  ).toBeVisible();
  await expect(shell.getByTestId("config-save-button")).toBeDisabled();
});

test("name filter templates stay usable on mobile", async ({ page }) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  const shell = await openRules(page);

  await expect(shell.getByTestId("name-kick-preset-unreadable")).toBeVisible();
  await expectNoHorizontalPageOverflow(page);
});
