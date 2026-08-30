import { useEffect, useMemo, useState } from "react";
import { Box, IconButton, Stack } from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useGlobalStore } from "@/stores/global-state";
import { getGameLabel, normalizeGame } from "@/utils/game-context";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { UserActions } from "../sidebar/UserActions";
import LanguageSelector from "../LanguageSelector";
import CommandRail, { COMMAND_RAIL_WIDTH } from "./CommandRail";
import ContextNavigationPanel from "./ContextNavigationPanel";
import ServerRailSwitcher from "./ServerRailSwitcher";
import { buildCommandRailWorkspaces } from "./command-rail-navigation";
import { doesNavigationRouteMatch } from "./command-rail-workspaces.mjs";

const workspaceCodes = {
  home: "HOME",
  live: "LIVE",
  moderation: "MOD",
  "game-operations": "OPS",
  automation: "AUTO",
  analytics: "DATA",
  integrations: "LINK",
  system: "SYS",
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
  [CONNECTION_STATE.UNKNOWN]: "text.disabled",
  [CONNECTION_STATE.DISABLED]: "text.disabled",
};

const getTranslatedLinkLabel = (link, t) =>
  link.translationKey
    ? t(link.translationKey)
    : link.name || link.label || link.to;

const getCurrentLinkId = (pathname, workspaces) =>
  workspaces
    .flatMap((workspace) => workspace.links)
    .filter((link) => doesNavigationRouteMatch(pathname, link.to))
    .sort((left, right) => right.to.length - left.to.length)[0]?.to ?? null;

const getInitialWorkspaceId = (workspaces) => {
  const routeWorkspace = workspaces.find((workspace) => workspace.isActive);
  if (routeWorkspace && !routeWorkspace.directRoute) return routeWorkspace.id;
  return (
    workspaces.find((workspace) => workspace.id === "live")?.id ??
    workspaces.find((workspace) => !workspace.directRoute)?.id ??
    routeWorkspace?.id ??
    null
  );
};

export default function MobileCommandNavigation({ open, onClose }) {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const serverState = useGlobalStore((state) => state.serverState);
  const workspaces = useMemo(
    () =>
      buildCommandRailWorkspaces({
        pathname: location.pathname,
        permissions,
        includeLocked: true,
      }),
    [location.pathname, permissions]
  );
  const initialWorkspaceId = useMemo(
    () => getInitialWorkspaceId(workspaces),
    [workspaces]
  );
  const [selectedWorkspaceId, setSelectedWorkspaceId] =
    useState(initialWorkspaceId);

  useEffect(() => {
    if (open) setSelectedWorkspaceId(initialWorkspaceId);
  }, [initialWorkspaceId, open]);

  const selectedWorkspace =
    workspaces.find((workspace) => workspace.id === selectedWorkspaceId) ??
    workspaces.find((workspace) => !workspace.directRoute) ??
    null;
  const routeWorkspaceId =
    workspaces.find((workspace) => workspace.isActive)?.id ?? null;
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
  const selectedSections = selectedWorkspace?.sections ?? [];
  const sections = selectedSections.map((section) => ({
    id: section.id,
    label:
      selectedSections.length === 1 &&
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
  const panelTitleKey =
    selectedSections.length === 1 && selectedSections[0]?.labelTranslationKey
      ? selectedSections[0].labelTranslationKey
      : selectedWorkspace?.labelTranslationKey;
  const currentLinkId = getCurrentLinkId(location.pathname, workspaces);

  const closeAfterNavigation = () =>
    window.requestAnimationFrame(() => onClose?.());

  const handleWorkspaceChange = (workspaceId) => {
    const workspace = workspaces.find((entry) => entry.id === workspaceId);
    if (!workspace) return;
    if (workspace.directRoute) {
      navigate(workspace.directRoute);
      closeAfterNavigation();
      return;
    }
    setSelectedWorkspaceId(workspaceId);
  };

  const handleItemSelect = (_itemId, item) => {
    if (!item?.href || item.locked) return;
    navigate(item.href);
    closeAfterNavigation();
  };

  if (!selectedWorkspace) return null;

  return (
    <Box
      data-testid="mobile-command-navigation"
      sx={{ display: "flex", width: "100%", height: "100%", minHeight: 0 }}
    >
      <CommandRail
        height="100%"
        workspaces={workspaces.map((workspace) => ({
          id: workspace.id,
          workspaceId: workspace.id,
          label: t(workspace.labelTranslationKey),
          icon: workspace.icon,
          disabled: !workspace.directRoute && workspace.links.length === 0,
          expanded:
            !workspace.directRoute && workspace.id === selectedWorkspace.id,
          ariaControls:
            !workspace.directRoute && workspace.id === selectedWorkspace.id
              ? "mobile-navigation-context"
              : undefined,
        }))}
        activeWorkspaceId={selectedWorkspace.id}
        currentWorkspaceId={routeWorkspaceId}
        onWorkspaceChange={handleWorkspaceChange}
        topSlot={<ServerRailSwitcher />}
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
        bottomSlot={
          <Stack spacing={0.25} sx={{ alignItems: "center" }}>
            <LanguageSelector touchSafe square />
            <UserActions compact />
          </Stack>
        }
      />

      <ContextNavigationPanel
        id="mobile-navigation-context"
        presentation="mobile"
        width={`calc(100vw - ${COMMAND_RAIL_WIDTH}px)`}
        height="100%"
        workspaceLabel={t(panelTitleKey)}
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
        headerAction={
          <IconButton
            aria-label={t("common.close")}
            onClick={onClose}
            sx={(theme) => ({
              width: 44,
              height: 44,
              borderRadius: "0 !important",
              border: "1px solid",
              borderColor: "divider",
              color: "text.secondary",
              "&:hover": {
                color: "primary.light",
                bgcolor: "action.hover",
              },
              "&:focus-visible": {
                outline: `2px solid ${theme.palette.primary.main}`,
                outlineOffset: -2,
              },
            })}
          >
            <CloseRoundedIcon />
          </IconButton>
        }
        onKeyDown={(event) => {
          if (event.key === "Escape") onClose?.();
        }}
      />
    </Box>
  );
}
