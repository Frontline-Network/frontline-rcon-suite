import { expect, test } from "@playwright/test";
import {
  openDemoPage,
  VIEWPORTS,
  expectNoHorizontalPageOverflow,
} from "./helpers.mjs";

const fixture = { demo_log_stacks: 1, demo_log_stack_size: 100 };
const stream = (page) =>
  page.getByRole("region", { name: "Live-Ereignisstrom", exact: true });
async function filters(page) {
  await page.getByRole("button", { name: /^Erweiterte Filter$/i }).click();
  const dialog = page.getByRole("dialog", { name: "Erweiterte Filter" });
  await expect(dialog).toBeVisible();
  return dialog;
}
async function apply(dialog) {
  await dialog.getByRole("button", { name: /^Übernehmen$/i }).click();
  await expect(dialog).toHaveCount(0);
}
async function pickAction(page, dialog, label, value) {
  const picker = dialog.getByRole("combobox", { name: label, exact: true });
  await picker.fill(value);
  await page.getByRole("option", { name: new RegExp(` ${value}$`) }).click();
  await picker.press("Escape");
}
async function display(page) {
  await page.getByRole("button", { name: /^Anzeige anpassen$/i }).click();
  const dialog = page.getByRole("dialog", { name: "Live-Ansicht anpassen" });
  await expect(
    dialog.getByRole("tab", { name: "Live-Protokoll", exact: true })
  ).toHaveAttribute("aria-selected", "true");
  await expect(
    dialog.getByRole("button", { name: /^Speichern$/i })
  ).toBeEnabled();
  return dialog;
}

test.use({ viewport: { width: 1920, height: 1000 } });

test("expanded filters open above the split rail, apply and cancel correctly", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", { query: fixture });
  let dialog = await filters(page);
  await pickAction(page, dialog, "Aktionen filtern", "CHAT");
  await apply(dialog);
  await expect(stream(page)).toContainText("Hallo Squad!");
  await expect(stream(page)).not.toContainText(
    "Dein Squad hat keinen Offizier"
  );
  dialog = await filters(page);
  await dialog
    .getByRole("button", { name: /^Ansichtsfilter zurücksetzen$/i })
    .click();
  await dialog.getByRole("button", { name: /^Abbrechen$/i }).click();
  await expect(stream(page)).toContainText("Hallo Squad!");
  await expect(stream(page)).not.toContainText(
    "Dein Squad hat keinen Offizier"
  );
  dialog = await filters(page);
  await dialog
    .getByRole("button", { name: /^Ansichtsfilter zurücksetzen$/i })
    .click();
  await pickAction(page, dialog, "Hervorgehobene Ereignisse", "MESSAGE");
  await apply(dialog);
  await expect(page.getByTestId("live-log-stack")).toHaveAttribute(
    "data-highlighted",
    "true"
  );
});

test("retrieval validates the limit and persists include/exclude filters", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", { query: fixture });
  let dialog = await filters(page);
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await dialog
    .getByRole("spinbutton", { name: "Abruflimit für Protokolle" })
    .fill("");
  await expect(
    dialog.getByRole("button", { name: /^Übernehmen$/i })
  ).toBeDisabled();
  await dialog
    .getByRole("spinbutton", { name: "Abruflimit für Protokolle" })
    .fill("250");
  await pickAction(page, dialog, "Aktionen filtern", "CHAT");
  await apply(dialog);
  await expect(stream(page)).toContainText("Hallo Squad!");
  await expect(stream(page)).not.toContainText(
    "Dein Squad hat keinen Offizier"
  );
  dialog = await filters(page);
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await dialog
    .getByRole("combobox", { name: "Filtermodus", exact: true })
    .click();
  await page
    .getByRole("option", {
      name: "Ausgewählte Ereignisse ausschließen",
      exact: true,
    })
    .click();
  await apply(dialog);
  await expect(stream(page)).toContainText("Dein Squad hat keinen Offizier");
  await page.reload();
  dialog = await filters(page);
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await expect(
    dialog.getByRole("spinbutton", { name: "Abruflimit für Protokolle" })
  ).toHaveValue("250");
  await expect(
    dialog.getByRole("combobox", { name: "Filtermodus", exact: true })
  ).toContainText("ausschließen");
});

test("account display settings survive reload and reach stacked details", async ({
  page,
}) => {
  await openDemoPage(page, "/views/live", { query: fixture });
  let dialog = await display(page);
  await dialog
    .getByRole("combobox", { name: "Schriftgröße", exact: true })
    .click();
  await page.getByRole("option", { name: "Groß", exact: true }).click();
  await dialog
    .getByRole("combobox", { name: "Meldungsabstand", exact: true })
    .click();
  await page.getByRole("option", { name: "Großzügig", exact: true }).click();
  await dialog.getByRole("button", { name: /^Speichern$/i }).click();
  await expect(dialog).toHaveCount(0);
  await page.reload();
  await page
    .getByRole("button", {
      name: "100 gleiche Meldungen · Einträge anzeigen",
      exact: true,
    })
    .click();
  const row = page
    .getByTestId("live-log-stack-details")
    .locator('li[role="listitem"]')
    .first();
  await expect(row).toHaveCSS("padding-top", "16px");
  await expect(row).toHaveCSS("font-size", "18.4px");
  await openDemoPage(page, "/views/live", {
    query: { ...fixture, demo_role: "viewer" },
  });
  dialog = await display(page);
  await expect(
    dialog.getByRole("combobox", { name: "Schriftgröße", exact: true })
  ).toContainText("Klein");
  await expect(
    dialog.getByRole("combobox", { name: "Meldungsabstand", exact: true })
  ).toContainText("Kompakt");
});

test("mobile filters and three display tabs fit and remain reachable", async ({
  page,
}) => {
  await page.setViewportSize(VIEWPORTS.mobile);
  await openDemoPage(page, "/views/live", { query: fixture });
  await page.getByRole("tab", { name: "Protokoll", exact: true }).click();
  let dialog = await filters(page);
  const bounds = await dialog.boundingBox();
  expect(bounds.width).toBeLessThanOrEqual(VIEWPORTS.mobile.width);
  await dialog.getByRole("tab", { name: "Datenabruf", exact: true }).click();
  await expect(
    dialog.getByRole("button", { name: /^Übernehmen$/i })
  ).toBeInViewport();
  await dialog.getByRole("button", { name: /^Abbrechen$/i }).click();
  dialog = await display(page);
  await expect(
    dialog.getByRole("tab", { name: "Live-Protokoll", exact: true })
  ).toBeVisible();
  await expect(
    dialog.getByRole("button", { name: /^Speichern$/i })
  ).toBeInViewport();
  await expectNoHorizontalPageOverflow(page);
});
