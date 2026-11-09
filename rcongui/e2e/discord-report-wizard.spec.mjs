import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const steps = [
  { label: "Discord verbinden", testId: "discord-wizard-step-install" },
  { label: "Server erkennen", testId: "discord-wizard-step-guild" },
  { label: "Kanal & Rollen", testId: "discord-wizard-step-channelRoles" },
  { label: "Aktionen", testId: "discord-wizard-step-actions" },
  { label: "KI & Report-Admin", testId: "discord-wizard-step-ai" },
  { label: "Testen", testId: "discord-wizard-step-test" },
  { label: "Aktivieren", testId: "discord-wizard-step-activate" },
];

for (const language of ["de", "en"]) {
  for (const popupBlocked of [false, true]) {
    test(`Discord installation error stays visible (${language}, popup blocked: ${popupBlocked})`, async ({ page, context }) => {
      test.setTimeout(60_000);
      await page.setViewportSize(popupBlocked ? VIEWPORTS.mobile : VIEWPORTS.desktop);
      if (popupBlocked) {
        await page.addInitScript(() => { window.open = () => null; });
      }
      await openDemoPage(page, "/apps/discord-report-bot", {
        language,
        query: { demo_discord_install_error: "1" },
      });
      const install = page.getByTestId("discord-wizard-step-install").getByRole("button");
      const popupPromise = popupBlocked ? null : page.waitForEvent("popup");
      await install.click();
      const error = page.getByTestId("discord-install-error");
      await expect(error).toBeVisible();
      await expect(error).toContainText("CRCON pairing is invalid or expired");
      await expect(error).toContainText(language === "de" ? "Installations-ID" : "installation ID");
      await expect(install).toBeEnabled();
      if (popupPromise) {
        const popup = await popupPromise;
        await expect.poll(() => popup.isClosed()).toBe(true);
      }
      await expectNoHorizontalPageOverflow(page);

      // A retry replaces the failure with the next step; no real OAuth request.
      await context.route("https://discord.com/**", (route) => route.fulfill({ body: "OAuth test destination" }));
      await page.evaluate(() => {
        const url = new URL(window.location.href);
        url.searchParams.delete("demo_discord_install_error");
        window.history.replaceState(null, "", url);
        window.open = () => ({ opener: null, location: "", closed: false });
      });
      await install.click();
      await expect(page.getByTestId("discord-wizard-step-guild")).toBeVisible();
      await expect(error).toHaveCount(0);
    });
  }
}

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test.describe(`${viewportName} Discord wizard`, () => {
    test.use({ viewport });

    test("connected setup stays usable and truthful", async ({ page }) => {
      test.setTimeout(45_000);
      const runtimeErrors = collectRuntimeErrors(page);

      await openDemoPage(page, "/apps/discord-report-bot", {
        query: { demo_discord: "connected", demo_game: "hll_vietnam" },
      });

      await expect(
        page.getByText("Frontline #2 · #2 · Hell Let Loose: Vietnam")
      ).toBeVisible();
      await expect(page.getByText("Zentraler Broker")).toBeVisible();
      await expect(
        page.getByText("Frontline Network · #admin-reports")
      ).toBeVisible();

      const wizard = page.getByRole("navigation", {
        name: "Einrichtungsfortschritt Discord Report Bot",
      });
      for (const [index, step] of steps.entries()) {
        if (viewport.width < 600) {
          await wizard
            .getByRole("combobox", { name: "Aktueller Einrichtungsschritt" })
            .click();
          await page
            .getByRole("option", {
              name: `${index + 1}. ${step.label}`,
              exact: true,
            })
            .click();
        } else {
          await wizard
            .getByRole("button", { name: step.label, exact: true })
            .click();
        }
        await expect(page.getByTestId(step.testId)).toBeVisible();
        if (step.testId === "discord-wizard-step-ai") {
          const report = page.getByRole("region", {
            name: "Report-Admin – Kommunikation, Teamkills & Cheatprüfung",
          });
          await expect(report).toBeVisible();
          await expect(
            report.getByLabel("Report-Admin aktivieren", { exact: true })
          ).not.toBeChecked();
          const review = report.getByLabel(
            "Cheatmeldungen für Admins auswerten (keine automatische Sanktion)"
          );
          await expect(review).not.toBeChecked();
          await review.check();
          const reasonMode = report.getByRole("combobox", {
            name: "Einordnung des Meldegrunds",
          });
          await expect(reasonMode).toContainText("Bisherige Suchregeln");
          await reasonMode.click();
          await page
            .getByRole("option", {
              name: "KI – vollständigen Inhalt einordnen",
            })
            .click();
          await expect(
            report.getByText(/kein Suchwort-Fallback/)
          ).toBeVisible();
          await report
            .getByRole("button", { name: "Report-Regeln speichern" })
            .click();
          await expect(
            report.getByText("Gespeichert", { exact: true })
          ).toBeVisible();
          await expect(review).toBeChecked();
          await expect(reasonMode).toContainText(
            "KI – vollständigen Inhalt einordnen"
          );
          await expect(
            report.getByText(/60 Sekunden stiller Wartezeit/)
          ).toBeVisible();
          await expectNoHorizontalPageOverflow(page);
        }
      }

      await expectNoHorizontalPageOverflow(page);
      await expect(
        page.getByRole("heading", { name: "Führungsabstimmung", exact: true })
      ).toHaveCount(0);
      expect(runtimeErrors, runtimeErrors.join("\n")).toEqual([]);
    });
  });
}

test.describe("Discord wizard game context", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("keeps the active Hell Let Loose server visible", async ({ page }) => {
    await openDemoPage(page, "/apps/discord-report-bot", {
      query: { demo_discord: "connected", demo_game: "hll" },
    });

    await expect(
      page.getByText("Frontline #2 · #2 · Hell Let Loose")
    ).toBeVisible();
    await expect(
      page.getByText("Hell Let Loose: Vietnam", { exact: true })
    ).toHaveCount(0);
  });
});
