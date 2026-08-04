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

const environmentNames = {
  de: { day: "Tag", night: "Nacht", dusk: "Abend", dawn: "Morgengrauen", rain: "Regen", overcast: "Bewölkt" },
  en: { day: "Day", night: "Night", dusk: "Dusk", dawn: "Dawn", rain: "Rain", overcast: "Overcast" },
};

function Metric({ icon, label, value, helper, status, wrap = false }) {
  return (
    <Stack sx={{ minWidth: 120, flex: "1 1 120px" }} spacing={0.4}>
      <Typography variant="caption" color="primary.light" sx={{ textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Stack direction="row" alignItems="center" spacing={0.8}>
        <Box sx={{ color: status ? "success.main" : "primary.main", display: "flex" }}>{icon}</Box>
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
      <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase" }}>
        {helper}
      </Typography>
    </Stack>
  );
}

export default function BattleOverview() {
  const { t, i18n } = useTranslation();
  const status = useGlobalStore((state) => state.status);
  const gameState = useGlobalStore((state) => state.gameState);
  const currentMap = gameState?.current_map;
  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const mapName = currentMap?.pretty_name || "Foy";
  const mode = currentMap?.game_mode || "warfare";
  const environment = environmentNames[language][currentMap?.environment] || currentMap?.environment || environmentNames[language].night;
  const imageName = currentMap?.image_name || "foy-night.webp";
  const serverName = status?.name || status?.short_name || "[GER] Frontline Network | #2";
  const currentPlayers = status?.current_players ?? 0;
  const maxPlayers = status?.max_players ?? 100;
  const matchTime = dayjs.duration(gameState?.time_remaining || 0, "seconds").format("HH:mm:ss");

  return (
    <Box
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
            <Typography variant="caption" color="primary.light" sx={{ textTransform: "uppercase" }}>
              {t("dashboard.situation")}
            </Typography>
            <Divider sx={{ flexGrow: 1, borderColor: "primary.dark" }} />
          </Stack>
          <Box>
            <Typography variant="h3" sx={{ textTransform: "uppercase" }}>{serverName}</Typography>
            <Typography color="primary.main" sx={{ mt: 0.6, fontWeight: 800, letterSpacing: "0.16em", textTransform: "uppercase" }}>
              {mapName} · {mode} · {environment}
            </Typography>
          </Box>
          <Stack direction="row" flexWrap="wrap" divider={<Divider orientation="vertical" flexItem />} spacing={2} useFlexGap>
            <Metric icon={<GroupsRoundedIcon />} label={t("dashboard.players")} value={`${currentPlayers}/${maxPlayers}`} helper={`Max. ${maxPlayers}`} />
            <Metric icon={<MonitorHeartRoundedIcon />} label={t("dashboard.status")} value={t("common.online")} helper={t("dashboard.healthy")} status />
            <Metric icon={<ScheduleRoundedIcon />} label={t("dashboard.matchTime")} value={matchTime} helper={t("dashboard.currentRound")} />
            <Metric icon={<MapRoundedIcon />} label={t("dashboard.currentMap")} value={mapName} helper={environment} wrap />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
            <Button component={Link} to="/views/live" variant="contained" startIcon={<TimelineRoundedIcon />} sx={{ flex: 1 }}>
              {t("dashboard.openLive")}
            </Button>
            <Button component={Link} to="/settings/general" variant="outlined" startIcon={<SettingsRoundedIcon />} sx={{ flex: 1 }}>
              {t("dashboard.manageServer")}
            </Button>
          </Stack>
        </Stack>
        <Box
          component="img"
          src={`/maps/${imageName}`}
          onError={(event) => { event.currentTarget.src = "/maps/foy-night.webp"; }}
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
      </Stack>
    </Box>
  );
}
