import { useEffect, useMemo, useRef, useState } from "react";
import { Box, List, Popover, Typography, useMediaQuery } from "@mui/material";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { useGlobalStore } from "@/stores/global-state";
import { getGameLabel, normalizeGame } from "@/utils/game-context";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import ConnectionStatus from "../sidebar/ConnectionStatus";
import SystemUsage from "../sidebar/SystemUsage";
import { UserActions } from "../sidebar/UserActions";
import CommandRail, { COMMAND_RAIL_WIDTH } from "./CommandRail";
import ContextNavigationPanel, {
  CONTEXT_NAVIGATION_PANEL_WIDTH,
} from "./ContextNavigationPanel";
import ServerRailSwitcher from "./ServerRailSwitcher";
import { buildCommandRailWorkspaces } from "./command-rail-navigation";
import { doesNavigationRouteMatch } from "./command-rail-workspaces.mjs";

const PERSISTENT_NAVIGATION_MEDIA = "(min-width: 1280px)";
const PANEL_ID = "desktop-navigation-panel";

const workspaceCodes = {
  home: "OVR",
  live: "LIVE",
  moderation: "MOD",
  "game-operations": "OPS",
  automation: "AUT",
  analytics: "ANA",
  integrations: "INT",
  system: "SYS",
};

const workspaceTitleTranslationKeys = {
  live: "navigation.groups.liveOperations",
  moderation: "navigation.groups.playersModeration",
  "game-operations": "navigation.groups.mapsGameOperations",
  automation: "navigation.groups.automation",
  analytics: "navigation.groups.logsAnalytics",
  integrations: "navigation.workspaces.integrations",
  system: "navigation.workspaces.system",
};

const compactSectionTranslationKeys = {
  live: "navigation.contextSections.operations",
  moderation: "navigation.contextSections.management",
  "game-operations": "navigation.contextSections.gameOperations",
  automation: "navigation.contextSections.rules",
  analytics: "navigation.contextSections.analysis",
};

const connectionStateColors = {
  [CONNECTION_STATE.ONLINE]: "success.main",
  [CONNECTION_STATE.PARTIAL]: "warning.main",
  [CONNECTION_STATE.STALE]: "warning.main",
  [CONNECTION_STATE.OFFLINE]: "error.main",
  [CONNECTION_STATE.LOADING]: "info.main",
  [CONNECTION_STATE.UNKNOWN]: "text.disabled",
  [CONNECTION_STATE.DISABLED]: "text.disabled",
};

const getTranslatedLinkLabel = (link, t) =>
  link.translationKey ? t(link.translationKey) : link.name;

const getCurrentLinkId = (pathname, workspaces) =>
  workspaces
    .flatMap((workspace) => workspace.links)
    .filter((link) => doesNavigationRouteMatch(pathname, link.to))
    .sort((left, right) => right.to.length - left.to.length)[0]?.to ?? null;

export default function CommandNavigationShell() {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const openPanel = useAppStore((state) => state.openDrawer);
  const setPanelOpen = useAppStore((state) => state.setDrawerOpen);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const serverState = useGlobalStore((state) => state.serverState);
  const persistent = useMediaQuery(PERSISTENT_NAVIGATION_MEDIA);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [healthAnchor, setHealthAnchor] = useState(null);
  const lastWorkspaceTriggerRef = useRef(null);

  const workspaces = useMemo(
    () =>
      buildCommandRailWorkspaces({
        pathname: location.pathname,
        permissions,
        includeLocked: true,
      }),
    [location.pathname, permissions]
  );

  const routeWorkspace =
    workspaces.find((workspace) => workspace.isActive) ?? workspaces[0] ?? null;
  const routeWorkspaceId = routeWorkspace?.id ?? null;
  const routeWorkspaceDirectRoute = routeWorkspace?.directRoute ?? null;

  useEffect(() => {
    if (!routeWorkspaceId) return;

    setSelectedWorkspaceId(routeWorkspaceId);
    if (routeWorkspaceDirectRoute) setPanelOpen(false);
  }, [routeWorkspaceDirectRoute, routeWorkspaceId, setPanelOpen]);

  const effectiveWorkspaceId = selectedWorkspaceId || routeWorkspaceId;
  const selectedWorkspace =
    workspaces.find((workspace) => workspace.id === effectiveWorkspaceId) ??
    workspaces[0] ??
    null;

  const railWorkspaces = workspaces.map((workspace) => ({
    id: workspace.id,
    workspaceId: workspace.id,
    label: t(workspace.labelTranslationKey),
    ariaLabel: t(workspace.labelTranslationKey),
    icon: workspace.icon,
    ariaControls: workspace.directRoute ? undefined : PANEL_ID,
    expanded: workspace.directRoute
      ? undefined
      : openPanel && workspace.id === effectiveWorkspaceId,
  }));

  const selectedWorkspaceSections = selectedWorkspace?.sections ?? [];
  const sections = selectedWorkspaceSections.map((section) => ({
    id: section.id,
    label:
      selectedWorkspaceSections.length === 1 &&
      compactSectionTranslationKeys[selectedWorkspace.id]
        ? t(compactSectionTranslationKeys[selectedWorkspace.id])
        : section.labelTranslationKey
        ? t(section.labelTranslationKey)
        : undefined,
    items: section.links.map((link) => ({
      id: link.to,
      href: link.to,
      label: getTranslatedLinkLabel(link, t),
      icon: link.icon,
      locked: link.locked,
      lockedReason: link.locked ? t("navigation.permissionMissing") : undefined,
    })),
  }));

  const currentLinkId = getCurrentLinkId(location.pathname, workspaces);

  const handleWorkspaceChange = (workspaceId, event) => {
    lastWorkspaceTriggerRef.current = event?.currentTarget ?? null;
    const workspace = workspaces.find((entry) => entry.id === workspaceId);

    if (workspace?.directRoute) {
      navigate(workspace.directRoute);
      setSelectedWorkspaceId(workspaceId);
      setPanelOpen(false);
      return;
    }

    const isSameWorkspace = workspaceId === effectiveWorkspaceId;
    setSelectedWorkspaceId(workspaceId);
    setPanelOpen(isSameWorkspace && openPanel ? false : true);
  };

  const handleItemSelect = (_itemId, item) => {
    if (!item?.href || item.locked) return;
    navigate(item.href);
    if (!persistent) setPanelOpen(false);
  };

  const closeOverlayPanel = () => {
    setPanelOpen(false);
    window.requestAnimationFrame(() => {
      const fallbackTrigger = document.querySelector(
        `[data-workspace-id="${effectiveWorkspaceId}"]`
      );
      (lastWorkspaceTriggerRef.current || fallbackTrigger)?.focus();
    });
  };

  const gameServerState =
    connectionHealth?.gameServer?.state ?? CONNECTION_STATE.UNKNOWN;
  const crconState = connectionHealth?.crcon?.state ?? CONNECTION_STATE.UNKNOWN;
  const gameLabel = getGameLabel(normalizeGame(serverState?.game));
  const serverContext = [
    t("sidebar.serverNumber", { number: serverState?.server_number ?? "–" }),
    gameLabel,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <Box
      component="aside"
      aria-label={t("navigation.primary")}
      sx={{
        display: { xs: "none", md: "flex" },
        position: "relative",
        width: COMMAND_RAIL_WIDTH,
        minWidth: COMMAND_RAIL_WIDTH,
        height: "100dvh",
        flexShrink: 0,
        zIndex: (theme) => theme.zIndex.drawer,
        transition: (theme) =>
          theme.transitions.create("width", {
            duration: theme.transitions.duration.shorter,
          }),
        "@media (min-width: 1280px)": {
          width: openPanel
            ? COMMAND_RAIL_WIDTH + CONTEXT_NAVIGATION_PANEL_WIDTH
            : COMMAND_RAIL_WIDTH,
          minWidth: openPanel
            ? COMMAND_RAIL_WIDTH + CONTEXT_NAVIGATION_PANEL_WIDTH
            : COMMAND_RAIL_WIDTH,
        },
      }}
    >
      <CommandRail
        workspaces={railWorkspaces}
        activeWorkspaceId={effectiveWorkspaceId}
        currentWorkspaceId={routeWorkspaceId}
        onWorkspaceChange={handleWorkspaceChange}
        topSlot={<ServerRailSwitcher />}
        utilityItems={[
          {
            id: "health",
            label: t("sidebar.system"),
            ariaLabel: t("sidebar.system"),
            icon: <MonitorHeartOutlinedIcon />,
          },
        ]}
        onUtilityActivate={(itemId, event) => {
          if (itemId === "health") setHealthAnchor(event.currentTarget);
        }}
        statusItems={[
          {
            id: "gameserver",
            label: `${t("sidebar.gameServer")} · ${t(
              `connectionStates.${gameServerState}`
            )}`,
            color: connectionStateColors[gameServerState],
          },
          {
            id: "crcon",
            label: `CRCON · ${t(`connectionStates.${crconState}`)}`,
            color: connectionStateColors[crconState],
          },
        ]}
        bottomSlot={<UserActions compact />}
      />

      {openPanel && selectedWorkspace && (
        <Box
          sx={(theme) => ({
            position: "fixed",
            top: 0,
            bottom: 0,
            left: COMMAND_RAIL_WIDTH,
            zIndex: theme.zIndex.drawer,
            boxShadow: theme.shadows[8],
            "@media (min-width: 1280px)": {
              position: "relative",
              inset: "auto",
              boxShadow: "none",
            },
          })}
        >
          <ContextNavigationPanel
            id={PANEL_ID}
            presentation={persistent ? "persistent" : "overlay"}
            workspaceLabel={t(
              workspaceTitleTranslationKeys[selectedWorkspace.id] ||
                selectedWorkspace.labelTranslationKey
            )}
            workspaceCode={workspaceCodes[selectedWorkspace.id]}
            workspaceDescription={serverContext}
            sections={sections}
            activeItemId={currentLinkId}
            onItemSelect={handleItemSelect}
            ariaLabel={t("navigation.primary")}
            emptyMessage={t("navigation.noResults")}
            statusItems={[
              {
                id: "system",
                label: `${t("navigation.panelStatus.system")} ${t(
                  `connectionStates.${crconState}`
                )}`,
                color: connectionStateColors[crconState],
              },
              {
                id: "data",
                label: `${t("navigation.panelStatus.data")} ${t(
                  `connectionStates.${gameServerState}`
                )}`,
              },
            ]}
            onKeyDown={(event) => {
              if (event.key === "Escape" && !persistent) closeOverlayPanel();
            }}
          />
        </Box>
      )}

      <Popover
        open={Boolean(healthAnchor)}
        anchorEl={healthAnchor}
        onClose={() => setHealthAnchor(null)}
        anchorOrigin={{ vertical: "center", horizontal: "right" }}
        transformOrigin={{ vertical: "center", horizontal: "left" }}
        slotProps={{
          paper: {
            sx: {
              width: 280,
              ml: 1,
              borderRadius: 0,
              border: "1px solid",
              borderColor: "divider",
              backgroundImage: "none",
              bgcolor: "background.paper",
            },
          },
        }}
      >
        <Box sx={{ px: 1.5, pt: 1.5 }}>
          <Typography variant="h6">{t("sidebar.system")}</Typography>
        </Box>
        <List dense sx={{ px: 1.5, color: "text.secondary" }}>
          <ConnectionStatus />
          <SystemUsage />
        </List>
      </Popover>
    </Box>
  );
}
