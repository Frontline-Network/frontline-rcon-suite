import { Box, Typography, useMediaQuery } from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";

import OperationsOverview from "@/components/dashboard/OperationsOverview";
import MobileOperationsHub from "@/pages/mobile/operations";
import { useGlobalStore } from "@/stores/global-state";
import { cmd } from "@/utils/fetchUtils";
import { useTheme } from "@mui/material/styles";
import PageHeader from "@/components/shared/PageHeader";

const normalizeDashboardLogs = (rawLogs) => {
  const groups = (rawLogs?.result?.groups ?? []).map(({ group, logs }) => ({
    group,
    logs: (logs ?? []).map((log) => ({
      user_1: { id: log.player_id_1, name: log.player_name_1 },
      user_2: { id: log.player_id_2, name: log.player_name_2 },
      message: log.message,
      timestamp: log.timestamp_ms,
      action: log.action,
    })),
  }));

  const adminLogs = (rawLogs?.result?.admin_logs ?? []).map((log) => ({
    user_1: { id: log.player_id_1, name: log.player_name_1 },
    user_2: { id: log.player_id_2, name: log.player_name_2 },
    message: log.message,
    timestamp: log.timestamp_ms,
    action: log.action,
  }));

  groups.unshift({
    group: "ADMIN_REPORTS",
    labelKey: "dashboard.adminReports",
    logs: adminLogs,
  });

  return groups;
};

const Dashboard = () => {
  const { t, i18n } = useTranslation();
  const isWardogs = useTheme().frontline?.appearance?.preset === "wardogs";
  const status = useGlobalStore((state) => state.status);

  const { data: logs = [], isLoading: logsLoading } = useQuery({
    queryKey: ["logs", "dashboard"],
    enabled: status !== null,
    queryFn: async () =>
      normalizeDashboardLogs(
        await cmd.GET_DASHBOARD_LOGS({
          payload: { end: 15000, per_action_limit: 100 },
        })
      ),
  });

  return (
    <Box sx={{ py: isWardogs ? 0 : { xs: 2, md: 2.5 } }}>
      <PageHeader
        title={t("dashboard.title")}
        subtitle={t("dashboard.operations.subtitle")}
        actions={
          <Typography variant="caption" color="text.secondary">
            {dayjs()
              .locale(i18n.resolvedLanguage || "de")
              .format("dddd, D. MMMM YYYY")}
          </Typography>
        }
      />

      <OperationsOverview logs={logs} logsLoading={logsLoading} />
    </Box>
  );
};

const ResponsiveDashboard = () => {
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));
  return compact ? <MobileOperationsHub /> : <Dashboard />;
};

export default ResponsiveDashboard;
