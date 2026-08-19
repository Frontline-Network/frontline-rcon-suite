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
import { getGameLabel } from "@/utils/game";

const formatRemainingTime = (seconds) => {
  const value = Math.max(0, Math.floor(Number(seconds) || 0));
  const hours = Math.floor(value / 3600);
  const minutes = Math.floor((value % 3600) / 60);
  const remainingSeconds = value % 60;

  return [hours, minutes, remainingSeconds]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
};

const StatusItem = ({
  icon,
  label,
  value,
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
    }}
  >
    <Box
      sx={{
        display: "flex",
        color: tone,
        flexShrink: 0,
        "& svg": { fontSize: { xs: 17, sm: 19 } },
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
          fontSize: "0.62rem",
          lineHeight: 1,
          letterSpacing: "0.04em",
          textTransform: "uppercase",
        }}
      >
        {label}
      </Typography>
      <Typography
        variant="body2"
        sx={{
          mt: 0.25,
          fontSize: { xs: "0.76rem", sm: "0.82rem" },
          fontWeight: 700,
          lineHeight: 1.1,
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
  const serverState = useGlobalStore((state) => state.status);
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
    if (!gameState || timeRemaining <= 0) return undefined;

    const interval = window.setInterval(() => {
      setTimeRemaining((value) => Math.max(0, value - 1));
    }, 1000);

    return () => window.clearInterval(interval);
  }, [gameState, timeRemaining <= 0]);

  const hasPlayerData =
    serverState?.current_players != null && serverState?.max_players != null;
  const players = hasPlayerData
    ? `${serverState.current_players}/${serverState.max_players}`
    : t("common.unknown");
  const mapName =
    gameState?.current_map?.pretty_name ?? t("matchStatus.unknownMap");
  const identity = serverConnection || serverState;
  const gameLabel = getGameLabel(identity?.game) || t("common.unknown");
  const serverLabel =
    identity?.short_name || identity?.name || t("dashboard.unknownServer");
  const serverNumber =
    identity?.server_number != null
      ? t("sidebar.serverNumber", { number: identity.server_number })
      : t("matchStatus.unknownServerNumber");
  const isInitialLoading =
    connectionHealth.crcon.state === CONNECTION_STATE.LOADING && !identity;
  const gameServerTone =
    {
      [CONNECTION_STATE.ONLINE]: "success.main",
      [CONNECTION_STATE.STALE]: "warning.main",
      [CONNECTION_STATE.OFFLINE]: "error.main",
    }[connectionHealth.gameServer.state] || "text.disabled";

  return (
    <Box
      role="status"
      aria-label={t("matchStatus.ariaLabel")}
      data-testid="global-match-status"
      sx={(theme) => ({
        width: compact ? "100%" : "min(100%, 680px)",
        minWidth: 0,
        px: { xs: 1.25, sm: 1.5 },
        py: 0.75,
        border: "1px solid",
        borderColor: alpha(theme.palette.primary.main, 0.28),
        borderRadius: 1.5,
        bgcolor: alpha(theme.palette.primary.main, 0.055),
        boxShadow: `inset 3px 0 0 ${theme.palette.primary.main}`,
      })}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: compact
            ? "minmax(0, 1fr) minmax(82px, auto)"
            : "minmax(150px, 1.4fr) auto minmax(110px, 1fr) auto",
          alignItems: "center",
          columnGap: { xs: 1, sm: 1.5 },
          rowGap: 1,
          minWidth: 0,
        }}
      >
        {!isInitialLoading ? (
          <>
            <StatusItem
              icon={<DnsRoundedIcon />}
              label={`${serverNumber} · ${gameLabel}`}
              value={serverLabel}
              grow
              tone={gameServerTone}
            />
            <StatusItem
              icon={<GroupsRoundedIcon />}
              label={t("matchStatus.players")}
              value={players}
            />
            <StatusItem
              icon={<MapRoundedIcon />}
              label={t("matchStatus.map")}
              value={mapName}
              grow
            />
            <StatusItem
              icon={<TimerRoundedIcon />}
              label={t("matchStatus.remaining")}
              value={
                gameState
                  ? formatRemainingTime(timeRemaining)
                  : t("common.unknown")
              }
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
