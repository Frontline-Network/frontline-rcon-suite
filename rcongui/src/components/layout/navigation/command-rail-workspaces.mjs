const freezeWorkspace = (workspace) =>
  Object.freeze({
    ...workspace,
    groupIds: Object.freeze([...workspace.groupIds]),
  });

/**
 * Stable, task-oriented workspaces for the Frontline command rail.
 *
 * The group ids deliberately point at the existing `navMenus` tree. This
 * keeps routes and permission metadata in one authoritative place while the
 * rail provides a smaller primary-navigation layer above it.
 */
export const commandRailWorkspaceDefinitions = Object.freeze(
  [
    {
      id: "home",
      labelTranslationKey: "navigation.workspaces.home",
      groupIds: ["root"],
      iconSourceGroupId: "root",
    },
    {
      id: "live",
      labelTranslationKey: "navigation.workspaces.live",
      groupIds: ["live-operations"],
      iconSourceGroupId: "live-operations",
    },
    {
      id: "moderation",
      labelTranslationKey: "navigation.workspaces.moderation",
      groupIds: ["players-moderation"],
      iconSourceGroupId: "players-moderation",
    },
    {
      id: "game-operations",
      labelTranslationKey: "navigation.workspaces.gameOperations",
      groupIds: ["maps-game-operations"],
      iconSourceGroupId: "maps-game-operations",
    },
    {
      id: "automation",
      labelTranslationKey: "navigation.workspaces.automation",
      groupIds: ["automation"],
      iconSourceGroupId: "automation",
    },
    {
      id: "analytics",
      labelTranslationKey: "navigation.workspaces.analytics",
      groupIds: ["logs-analytics"],
      iconSourceGroupId: "logs-analytics",
    },
    {
      id: "integrations",
      labelTranslationKey: "navigation.workspaces.integrations",
      groupIds: ["apps-setup", "integrations"],
      iconSourceGroupId: "integrations",
    },
    {
      id: "system",
      labelTranslationKey: "navigation.workspaces.system",
      groupIds: ["server-configuration", "system-diagnostics"],
      iconSourceGroupId: "server-configuration",
    },
  ].map(freezeWorkspace)
);

export const normalizeNavigationPathname = (pathname = "/") => {
  const path = String(pathname || "/").split(/[?#]/, 1)[0] || "/";
  const withLeadingSlash = path.startsWith("/") ? path : `/${path}`;

  if (withLeadingSlash === "/") return "/";
  return withLeadingSlash.replace(/\/+$/, "") || "/";
};

export const doesNavigationRouteMatch = (pathname, route) => {
  const normalizedPathname = normalizeNavigationPathname(pathname);
  const normalizedRoute = normalizeNavigationPathname(route);

  if (normalizedRoute === "/") return normalizedPathname === "/";
  return (
    normalizedPathname === normalizedRoute ||
    normalizedPathname.startsWith(`${normalizedRoute}/`)
  );
};

/**
 * Returns the workspace owning the most specific matching route.
 * Nested pages such as `/settings/maps/votemap/settings` therefore remain in
 * the same workspace as their existing parent navigation destination.
 */
export const findActiveCommandRailWorkspaceId = (
  pathname,
  workspaceRouteEntries
) => {
  const matches = workspaceRouteEntries
    .filter(({ route }) => doesNavigationRouteMatch(pathname, route))
    .sort(
      (left, right) =>
        normalizeNavigationPathname(right.route).length -
        normalizeNavigationPathname(left.route).length
    );

  return matches[0]?.workspaceId ?? null;
};
