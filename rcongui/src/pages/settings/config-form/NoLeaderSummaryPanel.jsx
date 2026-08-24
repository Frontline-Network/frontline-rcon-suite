import {
  Alert,
  AlertTitle,
  Box,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
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
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "25px 85px minmax(0, 1fr)",
        gap: 0.625,
        alignItems: "center",
      }}
    >
      <Box
        aria-hidden="true"
        sx={{
          display: "grid",
          placeItems: "center",
          width: 25,
          height: 25,
          border: "1px solid",
          borderColor: "primary.main",
          borderRadius: "50%",
          color: "primary.main",
          fontSize: 12,
          fontWeight: 900,
        }}
      >
        {number}
      </Box>
      <Typography sx={{ fontSize: 11.5 }} fontWeight={850}>
        {title}
      </Typography>
      <Typography
        color="text.secondary"
        sx={{ fontSize: 10.5, whiteSpace: "nowrap" }}
      >
        {value}
      </Typography>
    </Box>
  );
}

const getReachability = (data) => {
  if (!data?.kick_after_max_punish) return "disabled";
  if (Number(data?.number_of_warnings) === -1) return "warningsUnlimited";
  if (Number(data?.number_of_punishments) === -1) return "punishmentsUnlimited";
  if (Number(data?.number_of_punishments) <= 0) return "punishmentsSkipped";
  return "reachable";
};

export default function NoLeaderSummaryPanel({ data }) {
  const { t } = useTranslation();
  const reachability = getReachability(data);
  const kickReachable = reachability === "reachable";
  const kickConfigured = Boolean(data?.kick_after_max_punish);

  return (
    <Box
      component="aside"
      aria-label={t("settings.configForms.workbench.flow.title")}
    >
      <Typography
        component="h2"
        variant="h6"
        fontWeight={900}
        sx={{ textTransform: "uppercase" }}
      >
        {t("settings.configForms.workbench.flow.title")}
      </Typography>
      <Typography
        variant="overline"
        color="text.primary"
        sx={{ display: "block", mt: 0, mb: 1.5 }}
      >
        {t("settings.configForms.workbench.flow.sequence")}
      </Typography>
      <Stack spacing={2}>
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
          value={
            Number(data?.number_of_punishments) === 0
              ? t("settings.configForms.workbench.flow.disabled")
              : t("settings.configForms.workbench.flow.punishAction")
          }
        />
        <FlowRow
          number={3}
          title={t("settings.configForms.workbench.flow.kick")}
          value={
            kickConfigured
              ? t("settings.configForms.workbench.flow.kickAfterSeconds", {
                  seconds: data?.kick_grace_period_seconds,
                })
              : t("settings.configForms.workbench.flow.disabled")
          }
        />
      </Stack>
      <Divider sx={{ my: 1.5 }} />
      <Typography variant="overline" color="text.primary">
        {t("settings.configForms.workbench.flow.reachability")}
      </Typography>
      <Alert
        severity={
          kickReachable ? "success" : kickConfigured ? "warning" : "info"
        }
        sx={{ mt: 0.25, borderRadius: 0.75, alignItems: "flex-start" }}
      >
        <AlertTitle sx={{ mb: 0.5, fontWeight: 850 }}>
          {t(
            `settings.configForms.workbench.flow.reachabilityStates.${reachability}.title`
          )}
        </AlertTitle>
        {t(
          `settings.configForms.workbench.flow.reachabilityStates.${reachability}.description`
        )}
      </Alert>
    </Box>
  );
}
