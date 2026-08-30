import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

test("server name settings load and save through the demo API", async ({
  page,
}) => {
  const runtimeErrors = collectRuntimeErrors(page);
  await page.setViewportSize(VIEWPORTS.desktop);
  const main = await openDemoPage(page, "/settings/server-name");

  const serverName = main.getByRole("textbox", { name: "Servername" });
  await expect(serverName).toHaveValue("[GER] Frontline Network | #2");
  await expect(serverName).not.toHaveValue(/<!DOCTYPE|<html/i);

  await serverName.fill("[GER] Frontline Testserver | #2");
  const saveButton = main.getByRole("button", {
    name: "Änderungen speichern",
  });
  await expect(saveButton).toBeEnabled();
  await saveButton.click();
  await expect(saveButton).toBeDisabled();

  await main
    .getByRole("button", { name: "SFTP-Konfiguration", exact: true })
    .click();
  await expect(main.getByRole("textbox", { name: "SFTP-Host" })).toHaveValue(
    "127.0.0.1"
  );
  await expect(main.getByRole("spinbutton", { name: "Port" })).toHaveValue(
    "10011"
  );

  await expectNoHorizontalPageOverflow(page);
  expect(
    runtimeErrors.filter((error) => !error.startsWith("console: Warning:"))
  ).toEqual([]);
});
