import { canAccessNavLink, navMenus } from "@/components/Header/nav-data";
import {
  commandRailWorkspaceDefinitions,
  findActiveCommandRailWorkspaceId,
} from "./command-rail-workspaces.mjs";

const indexNavigationGroups = (navigationTree) =>
  new Map(navigationTree.map((group) => [group.id, group]));

const getWorkspaceLinks = (definition, navigationGroups) =>
  definition.groupIds.flatMap(
    (groupId) => navigationGroups.get(groupId)?.links ?? []
  );

const getWorkspaceIcon = (definition, navigationGroups) => {
  const iconSource = navigationGroups.get(definition.iconSourceGroupId);
  return iconSource?.icon ?? iconSource?.links?.[0]?.icon ?? null;
};

const createWorkspaceRouteEntries = (navigationTree = navMenus) => {
  const navigationGroups = indexNavigationGroups(navigationTree);

  return commandRailWorkspaceDefinitions.flatMap((definition) =>
    getWorkspaceLinks(definition, navigationGroups).map((link) => ({
      workspaceId: definition.id,
      route: link.to,
    }))
  );
};

export const getActiveCommandRailWorkspaceId = (
  pathname,
  navigationTree = navMenus
) =>
  findActiveCommandRailWorkspaceId(
    pathname,
    createWorkspaceRouteEntries(navigationTree)
  );

/**
 * Builds the permission-aware view model consumed by a command rail.
 *
 * Protected destinations are hidden by default. Callers that intentionally
 * retain today's discoverable-but-locked behaviour must opt in via
 * `includeLocked`; every returned link then carries explicit accessibility
 * state so it cannot accidentally be rendered as a working link.
 */
export const buildCommandRailWorkspaces = ({
  pathname = "/",
  permissions,
  includeLocked = false,
  navigationTree = navMenus,
} = {}) => {
  const navigationGroups = indexNavigationGroups(navigationTree);
  const activeWorkspaceId = getActiveCommandRailWorkspaceId(
    pathname,
    navigationTree
  );

  return commandRailWorkspaceDefinitions
    .map((definition) => {
      const links = getWorkspaceLinks(definition, navigationGroups)
        .map((link) => {
          const isAccessible = canAccessNavLink(link, permissions);
          return {
            ...link,
            isAccessible,
            locked: !isAccessible,
          };
        })
        .filter((link) => includeLocked || link.isAccessible);

      return {
        id: definition.id,
        labelTranslationKey: definition.labelTranslationKey,
        icon: getWorkspaceIcon(definition, navigationGroups),
        links,
        directRoute: definition.directRoute ?? null,
        defaultRoute: links[0]?.to ?? null,
        isActive: definition.id === activeWorkspaceId,
      };
    })
    .filter((workspace) => workspace.links.length > 0 || workspace.isActive);
};

export const getCommandRailWorkspaceById = (workspaceId, options = {}) =>
  buildCommandRailWorkspaces(options).find(
    (workspace) => workspace.id === workspaceId
  ) ?? null;

export { commandRailWorkspaceDefinitions };
