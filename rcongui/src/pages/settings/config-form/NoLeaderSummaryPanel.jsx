import { Alert, Box, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

const formatStage = (count, interval, t) => {
  if (Number(count) === 0)
    return t("settings.configForms.workbench.flow.disabled");
  if (Number(count) === -1) {
    return t("settings.configForms.workbench.flow.unlimited", { interval });
  }
  return t("settings.configForms.workbench.flow.count", { count, interval });
};

function FlowRow({ number, title, value }) {
  return (
    <Stack direction="row" spacing={1.25} alignItems="flex-start">
      <Box
        sx={{
          display: "grid",
          placeItems: "center",
          flex: "0 0 auto",
          width: 25,
          height: 25,
          borderRadius: "50%",
          bgcolor: "primary.main",
          color: "primary.contrastText",
          fontSize: 12,
          fontWeight: 900,
        }}
      >
        {number}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="body2" fontWeight={850}>
          {title}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {value}
        </Typography>
      </Box>
    </Stack>
  );
}

export default function NoLeaderSummaryPanel({ data }) {
  const { t } = useTranslation();
  const kickReachable = Boolean(
    data?.kick_after_max_punish && Number(data?.number_of_punishments) > 0
  );

  return (
    <Box
      component="aside"
      aria-label={t("settings.configForms.workbench.flow.title")}
    >
      <Typography component="h2" variant="subtitle1" fontWeight={900}>
        {t("settings.configForms.workbench.flow.title")}
      </Typography>
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ display: "block", mt: 2, mb: 1.5 }}
      >
        {t("settings.configForms.workbench.flow.sequence")}
      </Typography>
      <Stack spacing={1.75}>
        <FlowRow
          number={1}
          title={t("settings.configForms.workbench.flow.warn")}
          value={formatStage(
            data?.number_of_warnings,
            data?.warning_interval_seconds,
            t
          )}
        />
        <FlowRow
          number={2}
          title={t("settings.configForms.workbench.flow.punish")}
          value={formatStage(
            data?.number_of_punishments,
            data?.punish_interval_seconds,
            t
          )}
        />
        <FlowRow
          number={3}
          title={t("settings.configForms.workbench.flow.kick")}
          value={
            data?.kick_after_max_punish
              ? t("settings.configForms.workbench.flow.afterSeconds", {
                  seconds: data?.kick_grace_period_seconds,
                })
              : t("settings.configForms.workbench.flow.disabled")
          }
        />
      </Stack>
      <Divider sx={{ my: 2.5 }} />
      <Typography variant="overline" color="text.secondary">
        {t("settings.configForms.workbench.flow.reachability")}
      </Typography>
      <Alert
        severity={kickReachable ? "success" : "warning"}
        sx={{ mt: 1, borderRadius: 0 }}
      >
        {t(
          kickReachable
            ? "settings.configForms.workbench.flow.reachable"
            : "settings.configForms.workbench.flow.unreachable"
        )}
      </Alert>
    </Box>
  );
}
