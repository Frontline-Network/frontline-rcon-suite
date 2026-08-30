import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const navigationSource = readFileSync(
  resolve(currentDirectory, "../src/components/Header/nav-data.js"),
  "utf8"
);

const consolidatedLegacyRoutes = [
  "/settings/others/chat-commands",
  "/settings/others/crcon",
  "/settings/others/game-server",
  "/settings/others/gtx-server",
  "/settings/others/log-stream",
  "/settings/others/rcon-chat-commands",
  "/settings/others/scoreboard",
  "/settings/others/steam",
  "/settings/others/watch-kill-rate",
  "/settings/webhooks/admin-ping",
  "/settings/webhooks/audit",
  "/settings/webhooks/camera",
  "/settings/webhooks/chat",
  "/settings/webhooks/kills",
  "/settings/webhooks/log-line",
  "/settings/webhooks/watchlist",
];

test.describe("task-oriented navigation contract", () => {
  test("groups every existing destination once without a catch-all section", () => {
    const rawDefinitions = navigationSource.slice(
      navigationSource.indexOf("const rawNavMenus"),
      navigationSource.indexOf("const linkTranslationKeys")
    );
    const definitions = navigationSource.slice(
      navigationSource.indexOf("const taskGroupDefinitions"),
      navigationSource.indexOf("const linkPermissionKeys")
    );
    const rawRoutes = [...rawDefinitions.matchAll(/to: "(\/[^\"]*)"/g)].map(
      ([, route]) => route
    );
    const routes = [...definitions.matchAll(/"(\/[^\"]+)"/g)].map(
      ([, route]) => route
    );

    expect(definitions).not.toContain('id: "others"');
    expect(new Set(routes).size).toBe(routes.length);
    expect([...routes, "/", ...consolidatedLegacyRoutes].sort()).toEqual(
      rawRoutes.sort()
    );
    expect(routes).toEqual(
      expect.not.arrayContaining(consolidatedLegacyRoutes)
    );
    expect(routes).toEqual(
      expect.arrayContaining([
        "/views/live",
        "/records/players",
        "/settings/maps/rotation",
        "/apps/discord-report-bot",
        "/settings/general",
        "/records/audit-logs",
        "/settings/integrations",
        "/settings/services",
      ])
    );
  });

  test("uses absolute statistics routes", () => {
    expect(navigationSource).toContain('to: "/stats/live-sessions"');
    expect(navigationSource).toContain('to: "/stats/live-game"');
    expect(navigationSource).toContain('to: "/stats/games"');
    expect(navigationSource).not.toMatch(/to: "stats\//);
  });

  test("groups map changes with maps and game operations", () => {
    const liveOperations = navigationSource.slice(
      navigationSource.indexOf('id: "live-operations"'),
      navigationSource.indexOf('id: "players-moderation"')
    );
    const mapsGameOperations = navigationSource.slice(
      navigationSource.indexOf('id: "maps-game-operations"'),
      navigationSource.indexOf('id: "automation"')
    );

    expect(liveOperations).not.toContain('"/settings/maps/change"');
    expect(mapsGameOperations).toContain('"/settings/maps/change"');
  });

  test("keeps app setup separate from webhook integrations", () => {
    const appSetup = navigationSource.slice(
      navigationSource.indexOf('id: "apps-setup"'),
      navigationSource.indexOf('id: "integrations"')
    );
    const integrations = navigationSource.slice(
      navigationSource.indexOf('id: "integrations"'),
      navigationSource.indexOf('id: "server-configuration"')
    );

    expect(appSetup).toContain('translationKey: "navigation.groups.appsSetup"');
    expect(appSetup).toContain('"/apps"');
    expect(appSetup).toContain('"/apps/discord-report-bot"');
    expect(integrations).not.toContain('"/apps"');
    expect(integrations).not.toContain('"/apps/discord-report-bot"');
  });
});

test.describe("permission-aware navigation", () => {
  test.use({ viewport: VIEWPORTS.desktop });

  test("keeps a protected destination discoverable and explains why a viewer cannot open it", async ({
    page,
  }) => {
    await openDemoPage(page, "/", { query: { demo_role: "viewer" } });

    const rail = page.getByTestId("desktop-command-rail");
    const navigation = page.getByTestId("desktop-navigation-panel");
    await rail.getByRole("button", { name: "Live" }).click();

    const liveView = navigation.getByRole("button", { name: "Live-Ansicht" });
    await expect(liveView).toHaveAttribute("aria-disabled", "true");
    await expect(
      navigation.getByRole("link", { name: "Live-Ansicht" })
    ).toHaveCount(0);

    await liveView.focus();
    await expect(
      page.getByRole("tooltip", {
        name: "Diese Seite ist sichtbar, aber dir fehlt die erforderliche Berechtigung.",
      })
    ).toBeVisible();
  });

  test("keeps protected destinations as links for a superuser", async ({
    page,
  }) => {
    await openDemoPage(page, "/");

    const rail = page.getByTestId("desktop-command-rail");
    const navigation = page.getByTestId("desktop-navigation-panel");
    await rail.getByRole("button", { name: "Live" }).click();
    await expect(
      navigation.getByRole("link", { name: "Live-Ansicht" })
    ).toHaveAttribute("href", "/views/live");
  });

  test("shows map changes under maps and game operations", async ({ page }) => {
    await openDemoPage(page, "/");

    const rail = page.getByTestId("desktop-command-rail");
    const navigation = page.getByTestId("desktop-navigation-panel");
    await rail.getByRole("button", { name: "Live" }).click();
    await expect(
      navigation.getByRole("link", { name: "Karte wechseln" })
    ).toHaveCount(0);

    await rail.getByRole("button", { name: "Spielbetrieb" }).click();
    await expect(
      navigation.getByRole("link", { name: "Karte wechseln" })
    ).toHaveAttribute("href", "/settings/maps/change");
  });

  test("selects only the current app entry", async ({ page }) => {
    await openDemoPage(page, "/apps/discord-report-bot");

    const rail = page.getByTestId("desktop-command-rail");
    const navigation = page.getByTestId("desktop-navigation-panel");
    await rail.getByRole("button", { name: "Integrationen" }).click();

    const frontlineApp = navigation.getByRole("link", {
      name: "Frontline App",
    });
    const discordReportBot = navigation.getByRole("link", {
      name: "Discord Report Bot",
    });

    await expect(frontlineApp).not.toHaveClass(/active/);
    await expect(frontlineApp).not.toHaveAttribute("aria-current", "page");
    await expect(discordReportBot).toHaveClass(/active/);
    await expect(discordReportBot).toHaveAttribute("aria-current", "page");
  });
});

test.describe("task-oriented mobile navigation", () => {
  test.use({ viewport: VIEWPORTS.mobile });

  test("keeps the task groups usable in the full-width drawer", async ({
    page,
  }) => {
    await openDemoPage(page, "/");
    await page.getByRole("button", { name: "Navigation öffnen" }).click();

    const navigation = page.getByRole("navigation", {
      name: "Hauptnavigation",
    });
    const playersGroup = navigation.getByRole("button", {
      name: "Moderation",
    });
    await expect(playersGroup).toBeVisible();
    await expect(playersGroup).toHaveCSS("min-height", "44px");
    await playersGroup.click();
    await expect(
      navigation.getByRole("link", { name: "Spieler" })
    ).toBeVisible();

    await navigation.getByRole("button", { name: "Spielbetrieb" }).click();
    await expect(
      navigation.getByRole("link", { name: "Karte wechseln" })
    ).toBeVisible();
  });
});
