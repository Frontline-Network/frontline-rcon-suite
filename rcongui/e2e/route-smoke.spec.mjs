import { expect, test } from "@playwright/test";
import {
  collectRuntimeErrors,
  expectNoHorizontalPageOverflow,
  openDemoPage,
  VIEWPORTS,
} from "./helpers.mjs";

const routes = [
  { name: "dashboard", path: "/" },
  { name: "live operations", path: "/views/live" },
  { name: "team overview", path: "/views/team" },
  { name: "player records", path: "/records/players" },
  { name: "map objectives", path: "/settings/maps/objectives" },
  { name: "services", path: "/settings/services" },
  { name: "apps", path: "/apps" },
  { name: "Discord report bot", path: "/apps/discord-report-bot" },
];

for (const [viewportName, viewport] of Object.entries(VIEWPORTS)) {
  test.describe(`${viewportName} ${viewport.width}px`, () => {
    test.use({ viewport });

    for (const route of routes) {
      test(`${route.name} renders without a route or runtime error`, async ({ page }) => {
        const runtimeErrors = collectRuntimeErrors(page);

        await openDemoPage(page, route.path);
        await expectNoHorizontalPageOverflow(page);

        expect(runtimeErrors, runtimeErrors.join("\n")).toEqual([]);
      });
    }
  });
}
