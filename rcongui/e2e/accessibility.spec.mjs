import AxeBuilder from "@axe-core/playwright";
import { expect, test } from "@playwright/test";
import { openDemoPage, VIEWPORTS } from "./helpers.mjs";

const routes = [
  { name: "dashboard", path: "/" },
  { name: "live operations", path: "/views/live" },
  { name: "map objectives", path: "/settings/maps/objectives" },
  { name: "Discord report bot", path: "/apps/discord-report-bot" },
];

for (const viewportName of ["mobile", "tablet", "desktop"]) {
  const viewport = VIEWPORTS[viewportName];

  test.describe(`${viewportName} accessibility`, () => {
    test.setTimeout(60_000);
    test.use({ viewport });

    for (const route of routes) {
      test(`${route.name} has no serious or critical automated violations`, async ({ page }, testInfo) => {
        await openDemoPage(page, route.path);

        const results = await new AxeBuilder({ page })
          .withTags(["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"])
          .analyze();

        await testInfo.attach("axe-results", {
          body: Buffer.from(JSON.stringify(results, null, 2)),
          contentType: "application/json",
        });

        const blockingViolations = results.violations.filter((violation) =>
          ["serious", "critical"].includes(violation.impact),
        );

        expect(
          blockingViolations,
          blockingViolations
            .map((violation) => `${violation.id}: ${violation.help} (${violation.nodes.length} nodes)`)
            .join("\n"),
        ).toEqual([]);
      });
    }
  });
}
