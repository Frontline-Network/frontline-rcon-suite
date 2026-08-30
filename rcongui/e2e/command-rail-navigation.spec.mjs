import { expect, test } from "@playwright/test";
import { readFileSync } from "node:fs";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";
import {
  commandRailWorkspaceDefinitions,
  doesNavigationRouteMatch,
  findActiveCommandRailWorkspaceId,
  normalizeNavigationPathname,
} from "../src/components/layout/navigation/command-rail-workspaces.mjs";

const currentDirectory = dirname(fileURLToPath(import.meta.url));
const navigationSource = readFileSync(
  resolve(currentDirectory, "../src/components/Header/nav-data.js"),
  "utf8"
);

test.describe("command rail workspace contract", () => {
  test("marks the overview workspace as a direct destination", () => {
    expect(commandRailWorkspaceDefinitions[0]).toMatchObject({
      id: "home",
      directRoute: "/",
    });
  });

  test("groups every existing navigation group exactly once", () => {
    const taskGroupsSource = navigationSource.slice(
      navigationSource.indexOf("const taskGroupDefinitions"),
      navigationSource.indexOf("const linkPermissionKeys")
    );
    const existingGroupIds = [
      "root",
      ...[...taskGroupsSource.matchAll(/id: "([^"]+)"/g)].map(
        ([, groupId]) => groupId
      ),
    ];
    const groupedIds = commandRailWorkspaceDefinitions.flatMap(
      ({ groupIds }) => groupIds
    );

    expect(new Set(groupedIds).size).toBe(groupedIds.length);
    expect([...groupedIds].sort()).toEqual([...existingGroupIds].sort());
  });

  test("keeps root matching exact and nested configuration routes contextual", () => {
    expect(doesNavigationRouteMatch("/", "/")).toBe(true);
    expect(doesNavigationRouteMatch("/views/live", "/")).toBe(false);
    expect(
      doesNavigationRouteMatch(
        "/settings/maps/votemap/settings?tab=rules",
        "/settings/maps/votemap"
      )
    ).toBe(true);
    expect(normalizeNavigationPathname("settings/general/#health")).toBe(
      "/settings/general"
    );
  });

  test("selects the workspace with the most specific matching route", () => {
    const entries = [
      { workspaceId: "home", route: "/" },
      { workspaceId: "game-operations", route: "/settings/maps/votemap" },
      {
        workspaceId: "system",
        route: "/settings/maps/votemap/settings",
      },
    ];

    expect(
      findActiveCommandRailWorkspaceId(
        "/settings/maps/votemap/settings/advanced",
        entries
      )
    ).toBe("system");
    expect(findActiveCommandRailWorkspaceId("/unknown", entries)).toBeNull();
  });

  test("filters protected destinations unless locked links are explicit", async ({
    page,
  }) => {
    await page.goto("/");

    const result = await page.evaluate(async () => {
      const { buildCommandRailWorkspaces } = await import(
        "/src/components/layout/navigation/command-rail-navigation.js"
      );
      const summarize = (workspaces) =>
        workspaces.flatMap((workspace) =>
          workspace.links.map((link) => ({
            route: link.to,
            isAccessible: link.isAccessible,
            locked: link.locked,
          }))
        );

      return {
        safeDefault: summarize(
          buildCommandRailWorkspaces({
            pathname: "/views/live",
            permissions: { permissions: [] },
          })
        ),
        discoverable: summarize(
          buildCommandRailWorkspaces({
            pathname: "/views/live",
            permissions: { permissions: [] },
            includeLocked: true,
          })
        ),
        superuser: summarize(
          buildCommandRailWorkspaces({
            pathname: "/views/live",
            permissions: { is_superuser: true, permissions: [] },
          })
        ),
      };
    });

    expect(result.safeDefault).not.toContainEqual(
      expect.objectContaining({ route: "/views/live" })
    );
    expect(result.discoverable).toContainEqual({
      route: "/views/live",
      isAccessible: false,
      locked: true,
    });
    expect(result.superuser).toContainEqual({
      route: "/views/live",
      isAccessible: true,
      locked: false,
    });
  });
});
