import { useGlobalStore } from "@/stores/global-state";
import { cmd } from "@/utils/fetchUtils";
import Grid from "@mui/material/Grid2";
import { useQuery } from "@tanstack/react-query";
import LogsCard from "@/components/shared/card/LogsCard";
import ServerSettingsCard from "@/components/cards/ServerSettingsCard";
import ServicesCard from "@/components/cards/ServicesCard";
import MapRotationCard from "@/components/cards/MapRotationCard";
import VIPWatchedCard from "@/components/cards/VIPWatchedCard";
import FlaggedPlayersCard from "@/components/cards/FlaggedPlayersCard";
import ModeratorsCard from "@/components/cards/ModeratorsCard";
import GamesCard from "@/components/cards/GamesCard";
import MapStatsCard from "@/components/cards/MapStatsCard";
import AutomodsCard from "@/components/cards/AutomodsCard";
import FrontlineAppCard from "@/components/cards/FrontlineAppCard";
import BattleOverview from "@/components/dashboard/BattleOverview";
import { Box, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";

const SMALL_CARD_SIZE = {
  xs: 12,
  md: 6,
  xl: 3,
};

const MEDIUM_CARD_SIZE = {
  xs: 12,
  xl: 6,
};

const LARGE_CARD_SIZE = {
  xs: 12,
};

const Dashboard = () => {
  const { t, i18n } = useTranslation();
  const status = useGlobalStore((state) => state.status);

  const { data: logs = [] } = useQuery({
    queryKey: ["logs", "dashboard"],
    queryFn: async () => {
      const rawLogs = await cmd.GET_LIVE_LOGS({
        payload: {
          end: 15000,
          filter_action: [],
          filter_player: [],
          inclusive_filter: true,
        },
      });

      const logs = Object.entries(
        rawLogs.result.logs.reduce((acc, log) => {
          acc[log.action] = (acc[log.action] || []).concat(log);
          return acc;
        }, {})
      ).map(([action, logs]) => ({
        group: action,
        logs: logs.slice(0, 100).map((log) => ({
          user_1: {
            id: log.player_id_1,
            name: log.player_name_1,
          },
          user_2: {
            id: log.player_id_2,
            name: log.player_name_2,
          },
          message: log.message,
          timestamp: log.timestamp_ms,
          action: log.action,
        })),
      }));

      const adminLogs = rawLogs.result.logs
        .filter(
          (log) =>
            log.action.startsWith("CHAT") && log.message.includes("!admin")
        )
        .map((log) => ({
          user_1: {
            id: log.player_id_1,
            name: log.player_name_1,
          },
          user_2: {
            id: log.player_id_2,
            name: log.player_name_2,
          },
          message: log.message,
          timestamp: log.timestamp_ms,
          action: log.action,
        }));

      logs.push({
        group: "ADMIN",
        label: `Admin (${adminLogs.length})`,
        logs: adminLogs,
      });

      return logs;
    },
  });

  const { data: games = [] } = useQuery({
    queryKey: ["games", "dashboard"],
    enabled: status !== null,
    queryFn: async () => {
      const result = await cmd.GET_COMPLETED_GAMES({
        params: { page: 1, limit: 100 },
      });
      if (!result?.maps) return [];

      return result.maps.filter(
        (game) => game.server_number === status.server_number
      );
    },
  });

  return (
    <Box sx={{ py: { xs: 2, md: 2.5 } }}>
      <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" alignItems={{ sm: "end" }} sx={{ mb: 2 }}>
        <Box>
          <Typography variant="h3" sx={{ textTransform: "uppercase" }}>{t("dashboard.title")}</Typography>
          <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase" }}>{t("dashboard.subtitle")}</Typography>
        </Box>
        <Typography variant="caption" color="text.secondary" sx={{ textTransform: "uppercase", mt: { xs: 1, sm: 0 } }}>
          {dayjs().locale(i18n.resolvedLanguage || "de").format("dddd, D. MMMM YYYY")}
        </Typography>
      </Stack>

      <BattleOverview />

      <Grid container sx={{ overflow: "hidden", mt: 2 }} spacing={2}>
      <Grid size={LARGE_CARD_SIZE}>
        <FrontlineAppCard />
      </Grid>
      <Grid size={SMALL_CARD_SIZE}>
        <ServerSettingsCard />
      </Grid>

      <Grid size={SMALL_CARD_SIZE}>
        <AutomodsCard />
      </Grid>

      <Grid size={MEDIUM_CARD_SIZE}>
        <ServicesCard />
      </Grid>

      <Grid size={SMALL_CARD_SIZE}>
        <MapRotationCard />
      </Grid>

      <Grid size={SMALL_CARD_SIZE}>
        <VIPWatchedCard />
      </Grid>

      <Grid size={SMALL_CARD_SIZE}>
        <FlaggedPlayersCard />
      </Grid>

      <Grid size={SMALL_CARD_SIZE}>
        <ModeratorsCard />
      </Grid>

      <Grid size={LARGE_CARD_SIZE}>
        <LogsCard logs={logs} />
      </Grid>

      <Grid size={MEDIUM_CARD_SIZE}>
        <GamesCard games={games.slice(0, 15)} />
      </Grid>

      <Grid size={MEDIUM_CARD_SIZE}>
        <MapStatsCard games={games} />
      </Grid>
      </Grid>
    </Box>
  );
};

export default Dashboard;
