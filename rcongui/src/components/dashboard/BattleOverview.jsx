import { useEffect, useState } from "react";
import { Box, Button, Divider, Stack, Typography } from "@mui/material";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import MonitorHeartRoundedIcon from "@mui/icons-material/MonitorHeartRounded";
import ScheduleRoundedIcon from "@mui/icons-material/ScheduleRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import TimelineRoundedIcon from "@mui/icons-material/TimelineRounded";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { resolveMapImageName } from "@/utils/map-images.mjs";

const environmentNames = {
  de: {
    day: "Tag",
    night: "Nacht",
    dusk: "Abend",
    dawn: "Morgengrauen",
    rain: "Regen",
    overcast: "Bewölkt",
  },
  en: {
    day: "Day",
    night: "Night",
    dusk: "Dusk",
    dawn: "Dawn",
    rain: "Rain",
    overcast: "Overcast",
  },
  fr: {
    day: "Jour",
    night: "Nuit",
    dusk: "Crépuscule",
    dawn: "Aube",
    rain: "Pluie",
    overcast: "Couvert",
  },
};

const statusTones = {
  success: "success.main",
  warning: "warning.main",
  error: "error.main",
  neutral: "text.secondary",
};

function Metric({
  icon,
  label,
  value,
  helper,
  tone = "neutral",
  wrap = false,
}) {
  return (
    <Stack sx={{ minWidth: 120, flex: "1 1 120px" }} spacing={0.4}>
      <Typography
        variant="caption"
        color="primary.light"
        sx={{ textTransform: "uppercase" }}
      >
        {label}
      </Typography>
      <Stack direction="row" alignItems="center" spacing={0.8}>
        <Box sx={{ color: statusTones[tone], display: "flex" }}>{icon}</Box>
        <Typography
          variant="h5"
          sx={{
            minWidth: 0,
            whiteSpace: wrap ? "normal" : "nowrap",
            overflowWrap: wrap ? "anywhere" : "normal",
          }}
        >
          {value}
        </Typography>
      </Stack>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase" }}
      >
        {helper}
      </Typography>
    </Stack>
  );
}

export default function BattleOverview() {
  const { t, i18n } = useTranslation();
  const status = useGlobalStore((state) => state.status);
  const serverState = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const currentMap = gameState?.current_map;
  const [mapImageFailed, setMapImageFailed] = useState(false);
  const requestedLanguage = (i18n.resolvedLanguage || "de").split("-")[0];
  const language = environmentNames[requestedLanguage] ? requestedLanguage : "de";
  const mapName = currentMap?.pretty_name || t("matchStatus.unknownMap");
  const mode = currentMap?.game_mode || t("common.unknown");
  const environment = currentMap?.environment
    ? environmentNames[language][currentMap.environment] ||
      currentMap.environment
    : t("common.unknown");
  const imageName = resolveMapImageName(currentMap);
  const serverName =
    status?.name ||
    status?.short_name ||
    serverState?.name ||
    serverState?.short_name ||
    t("dashboard.unknownServer");
  const currentPlayers = status?.current_players;
  const maxPlayers = status?.max_players;
  const players =
    currentPlayers != null && maxPlayers != null
      ? `${currentPlayers}/${maxPlayers}`
      : t("common.unknown");
  const matchTime = gameState
    ? dayjs
        .duration(Number(gameState.time_remaining) || 0, "seconds")
        .format("HH:mm:ss")
    : t("common.unknown");
  const gameServerHealth = connectionHealth.gameServer;
  const statusKey = gameServerHealth.state;
  const statusValue = t(`connectionStates.${statusKey}`);
  const statusTone =
    {
      [CONNECTION_STATE.ONLINE]: "success",
      [CONNECTION_STATE.PARTIAL]: "warning",
      [CONNECTION_STATE.STALE]: "warning",
      [CONNECTION_STATE.OFFLINE]: "error",
    }[statusKey] || "neutral";
  const statusHelper = gameServerHealth.lastSuccessAt
    ? t("dashboard.lastUpdated", {
        time: new Date(gameServerHealth.lastSuccessAt).toLocaleTimeString(
          language
        ),
      })
    : t("dashboard.noLiveData");

  useEffect(() => {
    setMapImageFailed(false);
  }, [imageName]);

  return (
    <Box data-theme-surface="panel"
      data-testid="battle-overview"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        overflow: "hidden",
      }}
    >
      <Stack direction={{ xs: "column", lg: "row" }}>
        <Stack sx={{ flex: "1 1 62%", p: { xs: 2, md: 3 } }} spacing={2.2}>
          <Stack direction="row" alignItems="center" spacing={1.2}>
            <Typography
              variant="caption"
              color="primary.light"
              sx={{ textTransform: "uppercase" }}
            >
              {t("dashboard.situation")}
            </Typography>
            <Divider sx={{ flexGrow: 1, borderColor: "primary.dark" }} />
          </Stack>
          <Box>
            <Typography variant="h3" sx={{ textTransform: "uppercase" }}>
              {serverName}
            </Typography>
            <Typography
              color="primary.main"
              sx={{
                mt: 0.6,
                fontWeight: 800,
                letterSpacing: "0.16em",
                textTransform: "uppercase",
              }}
            >
              {mapName} · {mode} · {environment}
            </Typography>
          </Box>
          <Stack
            direction="row"
            flexWrap="wrap"
            divider={<Divider orientation="vertical" flexItem />}
            spacing={2}
            useFlexGap
          >
            <Metric
              icon={<GroupsRoundedIcon />}
              label={t("dashboard.players")}
              value={players}
              helper={
                maxPlayers != null
                  ? t("dashboard.maximumPlayers", { count: maxPlayers })
                  : t("dashboard.noLiveData")
              }
            />
            <Metric
              icon={<MonitorHeartRoundedIcon />}
              label={t("dashboard.status")}
              value={statusValue}
              helper={statusHelper}
              tone={statusTone}
            />
            <Metric
              icon={<ScheduleRoundedIcon />}
              label={t("dashboard.matchTime")}
              value={matchTime}
              helper={
                gameState
                  ? t("dashboard.currentRound")
                  : t("dashboard.noLiveData")
              }
            />
            <Metric
              icon={<MapRoundedIcon />}
              label={t("dashboard.currentMap")}
              value={mapName}
              helper={environment}
              wrap
            />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button
              component={Link}
              to="/views/live"
              variant="contained"
              startIcon={<TimelineRoundedIcon />}
              sx={{ flex: 1 }}
            >
              {t("dashboard.openLive")}
            </Button>
            <Button
              component={Link}
              to="/settings/general"
              variant="outlined"
              startIcon={<SettingsRoundedIcon />}
              sx={{ flex: 1 }}
            >
              {t("dashboard.manageServer")}
            </Button>
          </Stack>
        </Stack>
        {imageName && !mapImageFailed ? (
          <Box
            component="img"
            src={`/maps/${imageName}`}
            onError={() => setMapImageFailed(true)}
            alt={`${mapName} · ${environment}`}
            sx={{
              flex: "1 1 44%",
              width: { xs: "100%", lg: "44%" },
              minHeight: { xs: 210, lg: 360 },
              maxHeight: 410,
              objectFit: "cover",
              borderLeft: { lg: "1px solid" },
              borderTop: { xs: "1px solid", lg: 0 },
              borderColor: "divider",
              filter: "saturate(0.72) contrast(1.08) brightness(0.72)",
            }}
          />
        ) : (
          <Stack
            role="img"
            aria-label={t("dashboard.mapImageUnavailable")}
            alignItems="center"
            justifyContent="center"
            spacing={1.5}
            sx={{
              flex: "1 1 44%",
              width: { xs: "100%", lg: "44%" },
              minHeight: { xs: 210, lg: 360 },
              maxHeight: 410,
              borderLeft: { lg: "1px solid" },
              borderTop: { xs: "1px solid", lg: 0 },
              borderColor: "divider",
              color: "text.secondary",
              bgcolor: "background.default",
            }}
          >
            <MapRoundedIcon sx={{ fontSize: 54 }} />
            <Typography variant="body2">
              {t("dashboard.mapImageUnavailable")}
            </Typography>
          </Stack>
        )}
      </Stack>
    </Box>
  );
}
