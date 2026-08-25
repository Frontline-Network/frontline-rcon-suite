import { useEffect, useState } from "react";
import { Box, Skeleton, Stack, Typography } from "@mui/material";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import TimerRoundedIcon from "@mui/icons-material/TimerRounded";
import DnsRoundedIcon from "@mui/icons-material/DnsRounded";
import { alpha } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { getGameLabel } from "@/utils/game-context";

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
  divider = false,
  grow = false,
  tone = "primary.main",
}) => (
  <Stack
    direction="row"
    spacing={0.75}
    title={`${label}: ${value}`}
    sx={{
      alignItems: "center",
      minWidth: 0,
      flex: grow ? "1 1 150px" : "0 0 auto",
      gridArea: area,
      height: "100%",
      px: { xs: 1, sm: 1.25 },
      py: { xs: 0.75, sm: 0.8 },
      borderLeft: divider ? "1px solid" : 0,
      borderColor: "divider",
      ...(compact && area === "server"
        ? { borderBottom: "1px solid", borderBottomColor: "divider" }
        : {}),
      ...(compact && area === "players"
        ? { borderBottom: "1px solid", borderBottomColor: "divider" }
        : {}),
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
          display: "block",
          color: "text.secondary",
          fontSize: { xs: "0.56rem", sm: "0.59rem" },
          lineHeight: 1,
          letterSpacing: "0.055em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          mt: 0.25,
          fontSize: { xs: "0.75rem", sm: "0.8rem" },
          fontWeight: 700,
          lineHeight: 1.15,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
        }}
      >
        {value}
      </Typography>
    </Box>
  </Stack>
);

const ServerStatus = ({ compact = false }) => {
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
      return `${value} · ${t("connectionStates.stale")}`;
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

  return (
    <Box
      role="status"
      aria-label={t("matchStatus.ariaLabel")}
      data-testid="global-match-status"
      data-connection-state={gameDataState}
      sx={(theme) => ({
        width: compact ? "100%" : "min(100%, 680px)",
        minWidth: 0,
        border: "1px solid",
        borderLeftWidth: 3,
        borderColor: alpha(theme.palette.text.primary, 0.13),
        borderLeftColor: identityTone,
        borderRadius: 0.75,
        bgcolor: alpha(theme.palette.background.paper, 0.82),
        boxShadow: `0 8px 24px ${alpha(theme.palette.common.black, 0.14)}`,
        overflow: "hidden",
      })}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateAreas: compact
            ? '"server players" "map time"'
            : '"server players map time"',
          gridTemplateColumns: compact
            ? "minmax(0, 1fr) minmax(84px, auto)"
            : "minmax(170px, 1.25fr) auto minmax(150px, 1fr) auto",
          alignItems: "center",
          minWidth: 0,
        }}
      >
        {!isInitialLoading ? (
          <>
            <StatusItem
              icon={<DnsRoundedIcon />}
              label={`${serverNumber} · ${gameLabel}`}
              value={serverLabel}
              area="server"
              compact={compact}
              grow
              tone={identityTone}
            />
            <StatusItem
              icon={<GroupsRoundedIcon />}
              label={t("matchStatus.players")}
              value={players}
              area="players"
              compact={compact}
              divider
            />
            <StatusItem
              icon={<MapRoundedIcon />}
              label={t("matchStatus.map")}
              value={mapName}
              area="map"
              compact={compact}
              divider={!compact}
              grow
            />
            <StatusItem
              icon={<TimerRoundedIcon />}
              label={t("matchStatus.remaining")}
              value={displayLiveValue(
                gameState ? formatRemainingTime(timeRemaining) : null,
                connectionHealth.gameState
              )}
              area="time"
              compact={compact}
              divider
            />
          </>
        ) : (
          <>
            <Skeleton variant="rounded" width={74} height={30} />
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
