import { Alert, Chip, Stack, Typography } from "@mui/material";
import DnsRoundedIcon from "@mui/icons-material/DnsRounded";
import SportsEsportsRoundedIcon from "@mui/icons-material/SportsEsportsRounded";
import ScheduleRoundedIcon from "@mui/icons-material/ScheduleRounded";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { getGameLabel } from "@/utils/game-context";

const stateColors = {
  [CONNECTION_STATE.ONLINE]: "success",
  [CONNECTION_STATE.PARTIAL]: "warning",
  [CONNECTION_STATE.STALE]: "warning",
  [CONNECTION_STATE.OFFLINE]: "error",
  [CONNECTION_STATE.LOADING]: "default",
  [CONNECTION_STATE.UNKNOWN]: "default",
  [CONNECTION_STATE.DISABLED]: "default",
};

export function useAdminActionContext() {
  const serverState = useGlobalStore((state) => state.serverState);
  const status = useGlobalStore((state) => state.status);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const identity = serverState || status;

  return {
    serverName: identity?.short_name || identity?.name || null,
    serverNumber: identity?.server_number ?? null,
    gameLabel: getGameLabel(identity?.game),
    crcon: connectionHealth.crcon,
    gameServer: connectionHealth.gameServer,
    canExecute:
      connectionHealth.crcon.state === CONNECTION_STATE.ONLINE &&
      connectionHealth.gameServer.state === CONNECTION_STATE.ONLINE,
  };
}

export default function AdminActionContext({ context }) {
  const { t, i18n } = useTranslation();
  const defaultContext = useAdminActionContext();
  const value = context || defaultContext;
  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const lastSuccessAt = value.gameServer.lastSuccessAt;
  const lastUpdated = lastSuccessAt
    ? new Date(lastSuccessAt).toLocaleString(language)
    : t("actions.context.noLiveData");

  return (
    <Stack data-theme-surface="panel"
      spacing={1.25}
      data-testid="admin-action-context"
      sx={{
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      <Typography variant="overline" color="primary.light">
        {t("actions.context.title")}
      </Typography>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        useFlexGap
        flexWrap="wrap"
      >
        <Chip
          icon={<DnsRoundedIcon />}
          label={`${value.serverName || t("dashboard.unknownServer")} · ${
            value.serverNumber != null
              ? t("sidebar.serverNumber", { number: value.serverNumber })
              : t("matchStatus.unknownServerNumber")
          }`}
          variant="outlined"
        />
        <Chip
          icon={<SportsEsportsRoundedIcon />}
          label={value.gameLabel || t("common.unknown")}
          variant="outlined"
        />
        <Chip
          label={`CRCON · ${t(`connectionStates.${value.crcon.state}`)}`}
          color={stateColors[value.crcon.state]}
          variant="outlined"
        />
        <Chip
          label={`${t("sidebar.gameServer")} · ${t(
            `connectionStates.${value.gameServer.state}`
          )}`}
          color={stateColors[value.gameServer.state]}
          variant="outlined"
        />
      </Stack>
      <Stack direction="row" spacing={0.75} alignItems="center">
        <ScheduleRoundedIcon color="disabled" fontSize="small" />
        <Typography variant="caption" color="text.secondary">
          {t("actions.context.lastUpdated", { time: lastUpdated })}
        </Typography>
      </Stack>
      {!value.canExecute && (
        <Alert severity="warning">
          {t("actions.context.connectionBlocked")}
        </Alert>
      )}
    </Stack>
  );
}
