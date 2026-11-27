import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

test.use({ viewport: VIEWPORTS.desktop });

async function openSystem(page, options = {}) {
  await openDemoPage(page, "/", options);
  await expect(page.getByTestId("resource-telemetry-card")).toHaveCount(0);
  await page
    .getByRole("button", {
      name: options.language === "fr" ? "Système" : "System",
      exact: true,
    })
    .and(page.locator("button:not([data-workspace-id])"))
    .click();
  return page.getByTestId("sidebar-rcon-memory");
}

test("only service RAM is displayed; 10 GiB raw charge and all file cache stay hidden", async ({
  page,
}) => {
  const errors = collectRuntimeErrors(page);
  const memory = await openSystem(page);
  const instance = memory.getByTestId("sidebar-instance-memory");
  await expect(instance).toContainText("Instanz-RAM");
  await expect(instance).toContainText("598 MiB");
  await expect(instance).not.toContainText(/GiB|Dateicache/);
  await expect(memory.getByTestId("sidebar-shared-memory")).toBeVisible();
  await expect(memory.getByTestId("sidebar-shared-memory")).toContainText(
    "1,1 GiB"
  );
  await expect(memory).not.toContainText("%");
  await expect(memory.getByRole("progressbar")).toHaveCount(0);
  await expect(memory.getByTestId("sidebar-rcon-file-cache")).toHaveCount(0);
  await expect(memory).not.toContainText(/10,4 GiB|8,72 GiB|7 GiB|Dateicache/);
  await memory.hover();
  const tooltip = page.getByRole("tooltip");
  await expect(tooltip).toBeVisible();
  await expect(tooltip).not.toContainText(/10,4 GiB|8,72 GiB|7 GiB|Dateicache/);
  await memory.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog).toBeVisible();
  const ram = dialog.getByTestId("rcon-ram-metric");
  await expect(ram).toContainText("598 MiB");
  await expect(ram).not.toContainText(/GiB|Dateicache/);
  await expect(dialog.getByTestId("shared-memory-metric")).toContainText(
    "1,1 GiB"
  );
  await expect(dialog.getByTestId("service-group-memory-metric")).toContainText(
    "1,68 GiB"
  );
  await expect(dialog.getByTestId("service-group-file-cache")).toHaveCount(0);
  await expect(dialog.getByTestId("memory-charge-metric")).toHaveCount(0);
  await expect(dialog).not.toContainText(
    /10,4 GiB|8,72 GiB|7 GiB|Dateicache|Backend-Belegung/
  );
  await expect(ram).not.toContainText("%");
  await expect(ram.getByRole("progressbar")).toHaveCount(0);
  await dialog
    .getByRole("button", { name: "Speicher aufschlüsseln", exact: true })
    .click();
  const breakdown = dialog.getByTestId("rcon-memory-breakdown");
  await expect(breakdown).toContainText("Eigene Dienste: 598 MiB");
  await expect(breakdown).toContainText("Gemeinsam genutzte Dienste: 1,1 GiB");
  await expect(breakdown).toContainText("Datenbank");
  await expect(breakdown).toContainText("830,4 MiB");
  await expect(breakdown).toContainText("185 MiB");
  await expect(breakdown.getByTestId("backend-memory-detail")).toHaveCount(0);
  await expect(dialog).not.toContainText(
    /10,4 GiB|8,72 GiB|7 GiB|Dateicache|256 MiB von/
  );
  const history = dialog.getByTestId("rcon-memory-history");
  await expect(history).toBeVisible();
  await expect(history).toHaveAttribute("aria-label", /GiB/);
  await expect(history).toHaveAttribute("aria-label", /Dienst-RAM/);
  await expect(history).not.toHaveAttribute("aria-label", /10,4 GiB|8,72 GiB/);
  await expect(history).toContainText("Dienst-RAM gesamt");
  await expectNoHorizontalPageOverflow(page);
  await dialog.getByRole("button", { name: "Schließen", exact: true }).click();
  await expect(page.getByRole("dialog")).toHaveCount(0);
  await expect(memory).toBeVisible();
  expect(errors).toEqual([]);
});

for (const mode of [
  "rcon_unavailable",
  "rcon_missing",
  "stale",
  "host_fallback",
]) {
  test(`${mode} never substitutes backend or host usage for the RCON total`, async ({
    page,
  }) => {
    const memory = await openSystem(page, { query: { demo_resources: mode } });
    await expect(memory).toContainText("—");
    await expect(memory).not.toContainText(
      /598 MiB|10,4 GiB|32 GiB|64 GiB|256 MiB/
    );
    await expect(memory.getByTestId("sidebar-rcon-file-cache")).toHaveCount(0);
    await memory.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByTestId("rcon-ram-metric")).toContainText(
      mode === "stale" ? "veraltet" : "nicht verfügbar"
    );
    await expect(dialog.getByTestId("rcon-ram-metric")).not.toContainText(
      /32 GiB|64 GiB|256 MiB/
    );
    await dialog
      .getByRole("button", { name: "Speicher aufschlüsseln", exact: true })
      .click();
    if (mode === "host_fallback") {
      await expect(dialog.getByTestId("backend-memory-detail")).toHaveCount(0);
      await expect(dialog).not.toContainText(/Host-RAM|32 GiB|64 GiB/);
    }
  });
}

for (const [language, label, breakdown] of [
  ["en", "Instance RAM", "Show memory breakdown"],
  ["fr", "RAM de l'instance", "Afficher le détail de la mémoire"],
]) {
  test(`memory details are translated into ${language}`, async ({ page }) => {
    const memory = await openSystem(page, { language });
    await expect(memory).toContainText(label);
    await memory.click();
    const dialog = page.getByRole("dialog");
    await expect(dialog.getByTestId("rcon-ram-metric")).toContainText(label);
    await dialog.getByRole("button", { name: breakdown, exact: true }).click();
    await expect(dialog.getByTestId("rcon-memory-breakdown")).toContainText(
      "598 MiB"
    );
    await expect(dialog).not.toContainText("dashboard.resources.");
  });
}

test("raw backend pressure does not surface as service RAM pressure", async ({
  page,
}) => {
  const memory = await openSystem(page, {
    query: { demo_resources: "warning" },
  });
  await memory.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByRole("alert")).toHaveCount(0);
  await expect(dialog).not.toContainText(/Backend-RAM|86 %|Dateicache/);
  await expect(dialog.getByTestId("rcon-ram-metric")).not.toContainText("%");
});

test("missing service measurements never substitute raw charge or old raw history", async ({
  page,
}) => {
  const memory = await openSystem(page, {
    query: { demo_resources: "cache_unknown" },
  });
  await expect(memory.getByTestId("sidebar-instance-memory")).toContainText(
    "—"
  );
  await expect(memory.getByTestId("sidebar-shared-memory")).toContainText("—");
  await expect(memory).not.toContainText(
    /598 MiB|10,4 GiB|8,72 GiB|7 GiB|Dateicache/
  );
  await memory.click();
  const dialog = page.getByRole("dialog");
  await expect(dialog.getByTestId("rcon-ram-metric")).toContainText(
    "nicht verfügbar"
  );
  await expect(dialog.getByTestId("rcon-memory-history")).toHaveCount(0);
  await expect(dialog.getByTestId("service-group-memory-metric")).toContainText(
    "—"
  );
  await expect(dialog).not.toContainText(
    /10,4 GiB|8,72 GiB|7 GiB|Dateicache|256 MiB von/
  );
});

test("fresh RCON telemetry survives unavailable local CPU and backend metrics", async ({
  page,
}) => {
  const memory = await openSystem(page, {
    query: { demo_resources: "local_unavailable" },
  });
  await expect(memory).toContainText("598 MiB");
  await expect(memory.getByTestId("sidebar-rcon-file-cache")).toHaveCount(0);
  await memory.click();
  await expect(
    page.getByRole("dialog").getByTestId("rcon-ram-metric")
  ).toContainText("598 MiB");
  await expect(page.getByTestId("backend-memory-detail")).toHaveCount(0);
});

test("memory dialog fits a narrow viewport", async ({ page }) => {
  const memory = await openSystem(page);
  await memory.click();
  await expect(page.getByTestId("resource-telemetry-card")).toBeVisible();
  await page.setViewportSize(VIEWPORTS.mobile);
  await page
    .getByRole("button", { name: "Speicher aufschlüsseln", exact: true })
    .click();
  await expectNoHorizontalPageOverflow(page);
  const dialog = await page.getByRole("dialog").boundingBox();
  expect(dialog.x).toBeGreaterThanOrEqual(0);
  expect(dialog.x + dialog.width).toBeLessThanOrEqual(VIEWPORTS.mobile.width);
});
