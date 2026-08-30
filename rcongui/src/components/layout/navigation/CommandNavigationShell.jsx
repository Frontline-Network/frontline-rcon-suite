import { useEffect, useMemo, useRef, useState } from "react";
import {
  Box,
  List,
  Popover,
  Stack,
  Typography,
  useMediaQuery,
} from "@mui/material";
import MonitorHeartOutlinedIcon from "@mui/icons-material/MonitorHeartOutlined";
import { useLocation, useNavigate } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { useAppStore } from "@/stores/app-state";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import SelectContent from "../SelectContent";
import FrontlineBrand from "../FrontlineBrand";
import AboutDialog from "../sidebar/About";
import ConnectionStatus from "../sidebar/ConnectionStatus";
import SystemUsage from "../sidebar/SystemUsage";
import { UserActions } from "../sidebar/UserActions";
import CommandRail, { COMMAND_RAIL_WIDTH } from "./CommandRail";
import ContextNavigationPanel, {
  CONTEXT_NAVIGATION_PANEL_WIDTH,
} from "./ContextNavigationPanel";
import { buildCommandRailWorkspaces } from "./command-rail-navigation";
import { doesNavigationRouteMatch } from "./command-rail-workspaces.mjs";

const PERSISTENT_NAVIGATION_MEDIA = "(min-width: 1280px)";
const DESKTOP_NAVIGATION_MEDIA = "(min-width: 900px)";
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

function StatusSquare({ color }) {
  return (
    <Box
      aria-hidden
      component="span"
      sx={{
        width: 7,
        height: 7,
        flexShrink: 0,
        bgcolor: color,
        border: "1px solid",
        borderColor: "background.default",
      }}
    />
  );
}

function ServerDock({ connectionHealth, t }) {
  const gameServerState =
    connectionHealth?.gameServer?.state ?? CONNECTION_STATE.UNKNOWN;
  const crconState = connectionHealth?.crcon?.state ?? CONNECTION_STATE.UNKNOWN;

  return (
    <Stack spacing={0.75}>
      <Typography
        variant="caption"
        sx={{ color: "primary.light", textTransform: "uppercase" }}
      >
        {t("sidebar.server")}
      </Typography>
      <SelectContent />
      <Stack
        direction="row"
        divider={
          <Box
            aria-hidden
            sx={{ width: "1px", alignSelf: "stretch", bgcolor: "divider" }}
          />
        }
        spacing={1}
        sx={{ color: "text.secondary" }}
      >
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <StatusSquare color={connectionStateColors[gameServerState]} />
          <Typography variant="caption">{t("sidebar.gameServer")}</Typography>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <StatusSquare color={connectionStateColors[crconState]} />
          <Typography variant="caption">CRCON</Typography>
        </Stack>
      </Stack>
    </Stack>
  );
}

export default function CommandNavigationShell() {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const openPanel = useAppStore((state) => state.openDrawer);
  const setPanelOpen = useAppStore((state) => state.setDrawerOpen);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const persistent = useMediaQuery(PERSISTENT_NAVIGATION_MEDIA);
  const [selectedWorkspaceId, setSelectedWorkspaceId] = useState(null);
  const [searchValue, setSearchValue] = useState("");
  const [healthAnchor, setHealthAnchor] = useState(null);
  const searchInputRef = useRef(null);
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

  const routeWorkspaceId =
    workspaces.find((workspace) => workspace.isActive)?.id ??
    workspaces[0]?.id ??
    null;

  useEffect(() => {
    if (routeWorkspaceId) setSelectedWorkspaceId(routeWorkspaceId);
  }, [routeWorkspaceId]);

  const effectiveWorkspaceId = selectedWorkspaceId || routeWorkspaceId;
  const selectedWorkspace =
    workspaces.find((workspace) => workspace.id === effectiveWorkspaceId) ??
    workspaces[0] ??
    null;

  const keyHintLabel = useMemo(() => {
    if (typeof navigator === "undefined") return "Ctrl+K";
    const platform = navigator.userAgentData?.platform || navigator.platform;
    return /mac|iphone|ipad|ipod/i.test(platform) ? "⌘K" : "Ctrl+K";
  }, []);

  const focusSearch = () => {
    window.requestAnimationFrame(() => {
      window.requestAnimationFrame(() => searchInputRef.current?.focus());
    });
  };

  useEffect(() => {
    const handleShortcut = (event) => {
      if (!window.matchMedia(DESKTOP_NAVIGATION_MEDIA).matches) return;
      const key = String(event.key || "").toLowerCase();
      const isApple = keyHintLabel === "⌘K";
      if (key !== "k" || (isApple ? !event.metaKey : !event.ctrlKey)) return;

      event.preventDefault();
      setPanelOpen(true);
      focusSearch();
    };

    window.addEventListener("keydown", handleShortcut, { capture: true });
    return () =>
      window.removeEventListener("keydown", handleShortcut, { capture: true });
  }, [keyHintLabel, setPanelOpen]);

  const railWorkspaces = workspaces.map((workspace) => ({
    id: workspace.id,
    workspaceId: workspace.id,
    label: t(workspace.labelTranslationKey),
    ariaLabel: t(workspace.labelTranslationKey),
    icon: workspace.icon,
    ariaControls: PANEL_ID,
    expanded: openPanel && workspace.id === effectiveWorkspaceId,
  }));

  const mapWorkspaceItems = (workspace) =>
    workspace.links.map((link) => ({
      id: link.to,
      href: link.to,
      label: getTranslatedLinkLabel(link, t),
      icon: link.icon,
      locked: link.locked,
      lockedReason: link.locked ? t("navigation.permissionMissing") : undefined,
    }));

  const sections = searchValue.trim()
    ? workspaces.map((workspace) => ({
        id: workspace.id,
        label: t(workspace.labelTranslationKey),
        items: mapWorkspaceItems(workspace),
      }))
    : selectedWorkspace
    ? [
        {
          id: selectedWorkspace.id,
          items: mapWorkspaceItems(selectedWorkspace),
        },
      ]
    : [];

  const currentLinkId = getCurrentLinkId(location.pathname, workspaces);

  const handleWorkspaceChange = (workspaceId, event) => {
    lastWorkspaceTriggerRef.current = event?.currentTarget ?? null;
    const isSameWorkspace = workspaceId === effectiveWorkspaceId;

    setSelectedWorkspaceId(workspaceId);
    setSearchValue("");
    setPanelOpen(isSameWorkspace && openPanel ? false : true);
  };

  const handleItemSelect = (_itemId, item) => {
    if (!item?.href || item.locked) return;
    navigate(item.href);
    setSearchValue("");
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
            workspaceLabel={t(selectedWorkspace.labelTranslationKey)}
            workspaceCode={workspaceCodes[selectedWorkspace.id]}
            sections={sections}
            activeItemId={currentLinkId}
            onItemSelect={handleItemSelect}
            ariaLabel={t("navigation.primary")}
            searchValue={searchValue}
            onSearchChange={setSearchValue}
            searchPlaceholder={t("navigation.search")}
            emptyMessage={t("navigation.noResults")}
            searchHint={keyHintLabel}
            searchInputRef={searchInputRef}
            onKeyDown={(event) => {
              if (event.key === "Escape" && !persistent) closeOverlayPanel();
            }}
            topSlot={<FrontlineBrand textOnly />}
            headerSlot={
              <ServerDock connectionHealth={connectionHealth} t={t} />
            }
            footerSlot={
              <List dense disablePadding sx={{ color: "text.secondary" }}>
                <AboutDialog />
              </List>
            }
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
