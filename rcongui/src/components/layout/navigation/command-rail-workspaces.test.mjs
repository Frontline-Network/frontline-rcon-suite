import assert from "node:assert/strict";
import test from "node:test";
import {
  commandRailWorkspaceDefinitions,
  doesNavigationRouteMatch,
  findActiveCommandRailWorkspaceId,
  normalizeNavigationPathname,
} from "./command-rail-workspaces.mjs";

test("command rail workspaces use stable, unique ids and source groups", () => {
  const workspaceIds = commandRailWorkspaceDefinitions.map(({ id }) => id);
  const groupIds = commandRailWorkspaceDefinitions.flatMap(
    ({ groupIds: sourceGroupIds }) => sourceGroupIds
  );

  assert.equal(new Set(workspaceIds).size, workspaceIds.length);
  assert.equal(new Set(groupIds).size, groupIds.length);
  assert.deepEqual(workspaceIds, [
    "home",
    "live",
    "moderation",
    "game-operations",
    "automation",
    "analytics",
    "integrations",
    "system",
  ]);
});

test("navigation path normalization removes query, hash and trailing slashes", () => {
  assert.equal(
    normalizeNavigationPathname("settings/maps/votemap/?tab=pool#active"),
    "/settings/maps/votemap"
  );
  assert.equal(normalizeNavigationPathname("/"), "/");
});

test("the dashboard route only matches exactly", () => {
  assert.equal(doesNavigationRouteMatch("/", "/"), true);
  assert.equal(doesNavigationRouteMatch("/views/live", "/"), false);
});

test("nested routes remain in the workspace of their most specific parent", () => {
  const entries = [
    { workspaceId: "home", route: "/" },
    { workspaceId: "game-operations", route: "/settings/maps/votemap" },
    {
      workspaceId: "system",
      route: "/settings/maps/votemap/settings",
    },
  ];

  assert.equal(
    findActiveCommandRailWorkspaceId(
      "/settings/maps/votemap/settings/advanced",
      entries
    ),
    "system"
  );
  assert.equal(findActiveCommandRailWorkspaceId("/unknown", entries), null);
});
