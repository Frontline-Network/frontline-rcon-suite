import { useEffect, useState } from "react";
import { Box, Skeleton, Stack, Tooltip, Typography } from "@mui/material";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import TimerRoundedIcon from "@mui/icons-material/TimerRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { alpha } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { getGameLabel } from "@/utils/game-context";
import ServerRailSwitcher from "@/components/layout/navigation/ServerRailSwitcher";

const formatRemainingTime = (seconds) => {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const remainingSeconds = value % 60;

  return [hours, minutes, remainingSeconds]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
};

const stateTones = {
  [CONNECTION_STATE.ONLINE]: "success.main",
  [CONNECTION_STATE.PARTIAL]: "warning.main",
  [CONNECTION_STATE.STALE]: "warning.main",
  [CONNECTION_STATE.OFFLINE]: "error.main",
  [CONNECTION_STATE.LOADING]: "info.main",
  [CONNECTION_STATE.UNKNOWN]: "text.disabled",
  [CONNECTION_STATE.DISABLED]: "text.disabled",
};

const StatusItem = ({
  icon,
  label,
  value,
  area,
  compact = false,
  toolbar = false,
  statusNote,
  divider = false,
  grow = false,
  tone = "primary.main",
}) => (
  <Stack
    direction="row"
    spacing={0.75}
    title={`${label}: ${value}${statusNote ? ` · ${statusNote}` : ""}`}
    data-status-field={area}
    sx={{
      alignItems: "center",
      minWidth: 0,
      flex: grow ? "1 1 150px" : "0 0 auto",
      gridArea: area,
      height: "100%",
      px: compact ? 0.75 : { xs: 1, sm: 1.25 },
      py: toolbar ? 0.375 : compact ? 0.5 : { xs: 0.75, sm: 0.8 },
      borderLeft: divider ? "1px solid" : 0,
      borderColor: "divider",
    }}
  >
    <Box
      sx={{
        display: "flex",
        color: tone,
        flexShrink: 0,
        "& svg": { fontSize: { xs: 16, sm: 18 } },
      }}
    >
      {icon}
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Typography
        variant="caption"
        sx={{
          display: "flex",
          alignItems: "center",
          gap: 0.5,
          color: "text.secondary",
          fontSize: toolbar
            ? "0.625rem"
            : compact
            ? "0.52rem"
            : { xs: "0.56rem", sm: "0.59rem" },
          lineHeight: 1,
          letterSpacing: "0.055em",
          textTransform: "uppercase",
        }}
      >
        {label}
        {statusNote && (
          <Tooltip title={statusNote}>
            <WarningAmberRoundedIcon
              role="img"
              aria-hidden={false}
              aria-label={statusNote}
              sx={{ fontSize: 12, color: "warning.main" }}
            />
          </Tooltip>
        )}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          mt: 0.25,
          fontSize: toolbar
            ? { xs: "0.75rem", sm: "0.8125rem" }
            : compact
            ? "0.7rem"
            : { xs: "0.75rem", sm: "0.8rem" },
          fontWeight: 700,
          fontVariantNumeric: "tabular-nums",
          lineHeight: 1.15,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          ...(toolbar && area === "map"
            ? {
                whiteSpace: "normal",
                display: "-webkit-box",
                WebkitLineClamp: 2,
                WebkitBoxOrient: "vertical",
              }
            : {}),
        }}
      >
        {value}
      </Typography>
    </Box>
  </Stack>
);

const ServerStatus = ({ compact = false, variant = "default" }) => {
  const toolbar = variant === "toolbar";
  const { t } = useTranslation();
  const serverStatus = useGlobalStore((state) => state.status);
  const serverConnection = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const [timeRemaining, setTimeRemaining] = useState(
    Number(gameState?.time_remaining) || 0
  );

  useEffect(() => {
    setTimeRemaining(Number(gameState?.time_remaining) || 0);
  }, [gameState?.time_remaining]);

  useEffect(() => {
    if (
      !gameState ||
      timeRemaining <= 0 ||
      connectionHealth.gameState.state !== CONNECTION_STATE.ONLINE
    ) {
      return undefined;
    }

    const interval = window.setInterval(() => {
      setTimeRemaining((value) => Math.max(0, value - 1));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [connectionHealth.gameState.state, gameState, timeRemaining <= 0]);

  const displayLiveValue = (value, health) => {
    if (value === null || value === undefined || value === "") {
      return t("common.unknown");
    }
    if (health.state === CONNECTION_STATE.ONLINE) return value;
    if (health.state === CONNECTION_STATE.STALE) {
      return toolbar ? value : `${value} · ${t("connectionStates.stale")}`;
    }
    return t("common.unknown");
  };

  const hasPlayerData =
    serverStatus?.current_players != null && serverStatus?.max_players != null;
  const players = displayLiveValue(
    hasPlayerData
      ? `${serverStatus.current_players}/${serverStatus.max_players}`
      : null,
    connectionHealth.gameServer
  );
  const currentMapName = gameState?.current_map?.pretty_name;
  const mapName = currentMapName
    ? displayLiveValue(currentMapName, connectionHealth.gameState)
    : t("matchStatus.unknownMap");
  const identity = serverConnection || serverStatus;
  const gameLabel = getGameLabel(identity?.game) || t("common.unknown");
  const currentServerLabel = identity?.short_name || identity?.name;
  const serverLabel = currentServerLabel
    ? displayLiveValue(currentServerLabel, connectionHealth.crcon)
    : t("dashboard.unknownServer");
  const serverNumber =
    identity?.server_number != null
      ? t("sidebar.serverNumber", { number: identity.server_number })
      : t("matchStatus.unknownServerNumber");
  const isInitialLoading =
    connectionHealth.crcon.state === CONNECTION_STATE.LOADING && !identity;
  const identityTone =
    stateTones[connectionHealth.crcon.state] || "text.disabled";
  const gameDataState =
    connectionHealth.gameData?.state ?? CONNECTION_STATE.UNKNOWN;
  const hasTimeData =
    gameState?.time_remaining != null &&
    gameState.time_remaining !== "" &&
    Number.isFinite(Number(gameState.time_remaining));

  return (
    <Box
      role="status"
      aria-live={toolbar ? "off" : undefined}
      aria-label={t("matchStatus.ariaLabel")}
      data-testid="global-match-status"
      data-connection-state={gameDataState}
      sx={(theme) => ({
        width: toolbar || compact ? "100%" : "min(100%, 680px)",
        minWidth: 0,
        border: "1px solid",
        borderLeftWidth: 3,
        borderColor: alpha(theme.palette.text.primary, 0.13),
        borderLeftColor: toolbar
          ? stateTones[gameDataState] || "text.disabled"
          : identityTone,
        borderRadius: toolbar ? "8px" : 0,
        bgcolor: alpha(theme.palette.background.paper, 0.82),
        boxShadow: toolbar
          ? "none"
          : `0 8px 24px ${alpha(theme.palette.common.black, 0.14)}`,
        overflow: "hidden",
      })}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateAreas: toolbar
            ? '"players map time"'
            : '"server players map time"',
          gridTemplateColumns: toolbar
            ? "auto minmax(0, 1fr) auto"
            : compact
            ? "minmax(104px, 1.4fr) minmax(54px, auto) minmax(72px, 1fr) minmax(58px, auto)"
            : "minmax(170px, 1.25fr) auto minmax(150px, 1fr) auto",
          alignItems: "center",
          minWidth: 0,
          height: toolbar ? 46 : undefined,
        }}
      >
        {!isInitialLoading ? (
          <>
            {!toolbar && (
              <ServerRailSwitcher
                variant="status"
                compact={compact}
                label={`${serverNumber} · ${gameLabel}`}
                value={serverLabel}
                tone={identityTone}
              />
            )}
            <StatusItem
              icon={<GroupsRoundedIcon />}
              label={t("matchStatus.players")}
              value={players}
              area="players"
              compact={compact}
              toolbar={toolbar}
              statusNote={
                toolbar &&
                connectionHealth.gameServer.state === CONNECTION_STATE.STALE
                  ? t("connectionStates.stale")
                  : undefined
              }
              divider={!toolbar}
            />
            <StatusItem
              icon={<MapRoundedIcon />}
              label={t("matchStatus.map")}
              value={mapName}
              area="map"
              compact={compact}
              toolbar={toolbar}
              statusNote={
                toolbar &&
                connectionHealth.gameState.state === CONNECTION_STATE.STALE
                  ? t("connectionStates.stale")
                  : undefined
              }
              divider={!compact}
              grow
            />
            <StatusItem
              icon={<TimerRoundedIcon />}
              label={t("matchStatus.remaining")}
              value={displayLiveValue(
                hasTimeData ? formatRemainingTime(timeRemaining) : null,
                connectionHealth.gameState
              )}
              area="time"
              compact={compact}
              toolbar={toolbar}
              statusNote={
                toolbar &&
                connectionHealth.gameState.state === CONNECTION_STATE.STALE
                  ? t("connectionStates.stale")
                  : undefined
              }
              divider
            />
          </>
        ) : (
          <>
            {!toolbar && <Skeleton variant="rounded" width={74} height={30} />}
            <Skeleton variant="rounded" sx={{ flex: 1 }} height={30} />
            <Skeleton variant="rounded" width={82} height={30} />
            <Skeleton variant="rounded" width={82} height={30} />
          </>
        )}
      </Box>
    </Box>
  );
};

export default ServerStatus;
