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

  test("opens the overview directly without a secondary navigation panel", async ({
    page,
  }) => {
    await openDemoPage(page, "/views/live");

    const overview = page
      .getByTestId("desktop-command-rail")
      .getByRole("button", { name: "Übersicht" });
    await overview.click();

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByTestId("desktop-navigation-panel")).toHaveCount(0);
    await expect(overview).toHaveAttribute("aria-current", "page");
    await expect(overview).not.toHaveAttribute("aria-controls");
  });

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

    await liveView.hover();
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

  test("renders the compact mission index without legacy search or server card", async ({
    page,
  }) => {
    await openDemoPage(page, "/");

    const rail = page.getByTestId("desktop-command-rail");
    await expect(page.getByTestId("desktop-navigation-panel")).toHaveCount(0);
    await rail.getByRole("button", { name: "Live" }).click();
    const navigation = page.getByTestId("desktop-navigation-panel");

    await expect(
      navigation.getByRole("heading", { name: "Live-Betrieb" })
    ).toBeVisible();
    await expect(
      navigation.getByText("Betrieb", { exact: true })
    ).toBeVisible();
    await expect(navigation.getByText(/Server 2 · HLL/)).toBeVisible();
    await expect(
      navigation.getByRole("link", { name: "Live-Ansicht" })
    ).toHaveCSS("border-radius", "0px");
    await expect(
      navigation.getByPlaceholder("Navigation durchsuchen …")
    ).toHaveCount(0);
    await expect(
      navigation.getByRole("combobox", { name: "Server auswählen" })
    ).toHaveCount(0);
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

    const navigation = page.getByTestId("desktop-navigation-panel");
    await expect(navigation).toBeVisible();

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

  test("uses the operations hub as the mobile start destination", async ({
    page,
  }) => {
    await openDemoPage(page, "/");

    await expect(page).toHaveURL(/\/$/);
    await expect(page.getByRole("heading", { name: "Betrieb" })).toBeVisible();
    await expect(page.getByRole("button", { name: "Betrieb" })).toHaveAttribute(
      "aria-current",
      "page"
    );
  });

  test("uses the same compact workspace index on mobile", async ({ page }) => {
    await openDemoPage(page, "/views/live");
    await page.getByRole("button", { name: "Navigation öffnen" }).click();

    const navigation = page.getByTestId("mobile-command-navigation");
    await expect(navigation).toBeVisible();
    await expect(page.getByTestId("global-server-switcher")).toBeVisible();
    await expect(navigation.getByTestId("global-server-switcher")).toHaveCount(
      0
    );
    await expect(
      navigation.getByPlaceholder("Navigation durchsuchen …")
    ).toHaveCount(0);
    await expect(
      navigation.getByRole("heading", { name: "Live-Betrieb" })
    ).toBeVisible();
    await expect(
      navigation.getByRole("link", { name: "Live-Ansicht" })
    ).toHaveCSS("border-radius", "0px");
  });

  test("switches workspaces and closes after mobile navigation", async ({
    page,
  }) => {
    await openDemoPage(page, "/");
    await page.getByRole("button", { name: "Navigation öffnen" }).click();

    const navigation = page.getByTestId("mobile-command-navigation");
    const moderation = navigation.getByRole("button", {
      name: "Moderation",
      exact: true,
    });
    await moderation.click();
    await expect(
      navigation.getByRole("link", { name: "Spieler" })
    ).toBeVisible();

    await navigation
      .getByRole("button", { name: "Spielbetrieb", exact: true })
      .click();
    const changeMap = navigation.getByRole("link", {
      name: "Karte wechseln",
    });
    await expect(changeMap).toBeVisible();
    await changeMap.click();
    await expect(page).toHaveURL(/\/settings\/maps\/change$/);
    await expect(page.getByTestId("mobile-command-navigation")).toHaveCount(0);
  });

  test("provides a clear parent route on mobile detail pages", async ({
    page,
  }) => {
    await openDemoPage(page, "/stats/games/fln-demo-1");

    await expect(page.getByTestId("mobile-route-back")).toHaveAttribute(
      "href",
      "/stats/games"
    );
  });
});
