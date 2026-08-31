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
import ResourceTelemetryCard from "@/components/cards/ResourceTelemetryCard";
import BattleOverview from "@/components/dashboard/BattleOverview";
import { Box, Divider, Stack, Typography, useMediaQuery } from "@mui/material";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import MobileOperationsHub from "@/pages/mobile/operations";

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

const OPERATIONS_RESOURCE_SIZE = {
  xs: 12,
  lg: 7,
};

const OPERATIONS_SERVICE_SIZE = {
  xs: 12,
  lg: 5,
};

const DashboardSection = ({ title, testId }) => (
  <Grid size={LARGE_CARD_SIZE}>
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.5}
      data-testid={testId}
      sx={{ pt: 0.5 }}
    >
      <Typography
        component="h2"
        variant="overline"
        color="primary.main"
        sx={{ fontWeight: 700, whiteSpace: "nowrap" }}
      >
        {title}
      </Typography>
      <Divider sx={{ flexGrow: 1 }} />
    </Stack>
  </Grid>
);

const Dashboard = () => {
  const { t, i18n } = useTranslation();
  const status = useGlobalStore((state) => state.status);

  const { data: logs = [] } = useQuery({
    queryKey: ["logs", "dashboard"],
    queryFn: async () => {
      const rawLogs = await cmd.GET_DASHBOARD_LOGS({
        payload: {
          end: 15000,
          per_action_limit: 100,
        },
      });

      const logs = rawLogs.result.groups.map(({ group, logs }) => ({
        group,
        logs: logs.map((log) => ({
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

      const adminLogs = rawLogs.result.admin_logs.map((log) => ({
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

      logs.unshift({
        group: "ADMIN_REPORTS",
        labelKey: "dashboard.adminReports",
        icon: "🚨",
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
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ sm: "end" }}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography
            component="h1"
            variant="h3"
            sx={{ textTransform: "uppercase" }}
          >
            {t("dashboard.title")}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ textTransform: "uppercase" }}
          >
            {t("dashboard.subtitle")}
          </Typography>
        </Box>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ textTransform: "uppercase", mt: { xs: 1, sm: 0 } }}
        >
          {dayjs()
            .locale(i18n.resolvedLanguage || "de")
            .format("dddd, D. MMMM YYYY")}
        </Typography>
      </Stack>

      <BattleOverview />

      <Grid container sx={{ overflow: "hidden", mt: 2 }} spacing={2}>
        <DashboardSection
          title={t("dashboard.sections.operations")}
          testId="dashboard-section-operations"
        />

        <Grid size={OPERATIONS_RESOURCE_SIZE}>
          <ResourceTelemetryCard />
        </Grid>

        <Grid size={OPERATIONS_SERVICE_SIZE}>
          <ServicesCard />
        </Grid>

        <Grid size={SMALL_CARD_SIZE}>
          <MapRotationCard />
        </Grid>

        <DashboardSection
          title={t("dashboard.sections.moderation")}
          testId="dashboard-section-moderation"
        />

        <Grid size={SMALL_CARD_SIZE}>
          <AutomodsCard />
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

        <DashboardSection
          title={t("dashboard.sections.configuration")}
          testId="dashboard-section-configuration"
        />

        <Grid size={LARGE_CARD_SIZE}>
          <ServerSettingsCard />
        </Grid>

        <DashboardSection
          title={t("dashboard.sections.analysis")}
          testId="dashboard-section-analysis"
        />

        <Grid size={MEDIUM_CARD_SIZE}>
          <GamesCard games={games.slice(0, 15)} />
        </Grid>

        <Grid size={MEDIUM_CARD_SIZE}>
          <MapStatsCard games={games} />
        </Grid>

        <DashboardSection
          title={t("dashboard.sections.apps")}
          testId="dashboard-section-apps"
        />

        <Grid size={LARGE_CARD_SIZE}>
          <FrontlineAppCard />
        </Grid>
      </Grid>
    </Box>
  );
};

const ResponsiveDashboard = () => {
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));
  return compact ? <MobileOperationsHub /> : <Dashboard />;
};

export default ResponsiveDashboard;
