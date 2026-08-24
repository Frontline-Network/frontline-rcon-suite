import { Alert, Box, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

const hasValue = (value) => {
  if (value === undefined || value === null || value === "") return false;
  if (Array.isArray(value)) return value.length > 0;
  if (typeof value === "object") return Object.keys(value).length > 0;
  return value !== false;
};

const formatCountStage = (count, interval, t) => {
  if (count === undefined || count === null)
    return t("settings.configForms.workbench.profileSummary.configured", {
      configured: 0,
      total: 1,
    });
  if (Number(count) === 0)
    return t("settings.configForms.workbench.profileSummary.disabled");
  if (Number(count) === -1)
    return t("settings.configForms.workbench.profileSummary.unlimited", {
      interval: interval ?? 0,
    });
  return t("settings.configForms.workbench.profileSummary.count", {
    count,
    interval: interval ?? 0,
  });
};

const summarizeSection = (section, data, t) => {
  if (section.id === "operation") {
    if (data?.enabled === false)
      return t("settings.configForms.workbench.profileSummary.inactive");
    if (data?.dry_run)
      return t("settings.configForms.workbench.profileSummary.test");
    return t("settings.configForms.workbench.profileSummary.active");
  }
  if (section.id === "warnings")
    return formatCountStage(
      data?.number_of_warnings,
      data?.warning_interval_seconds,
      t
    );
  if (section.id === "punishments")
    return formatCountStage(
      data?.number_of_punishments,
      data?.punish_interval_seconds,
      t
    );
  if (section.id === "kick") {
    if (data?.kick_after_max_punish === false)
      return t("settings.configForms.workbench.profileSummary.disabled");
    return t("settings.configForms.workbench.profileSummary.kick", {
      seconds: data?.kick_grace_period_seconds ?? 0,
    });
  }
  if (section.id === "schedule" && data?.interval_minutes !== undefined) {
    return t("settings.configForms.workbench.profileSummary.intervalMinutes", {
      count: data.interval_minutes,
    });
  }

  const configured = section.fields.filter((name) =>
    hasValue(data?.[name])
  ).length;
  return t("settings.configForms.workbench.profileSummary.configured", {
    configured,
    total: section.fields.length,
  });
};

function FlowRow({ number, title, value }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "25px minmax(74px, 0.8fr) minmax(0, 1.2fr)",
        gap: 0.75,
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
      <Typography color="text.secondary" sx={{ fontSize: 10.5 }}>
        {value}
      </Typography>
    </Box>
  );
}

export default function ConfigProfileSummaryPanel({ profile, data }) {
  const { t } = useTranslation();
  const preferred = profile.summarySectionIds || [];
  const sections = preferred
    .map((id) => profile.sections.find((section) => section.id === id))
    .filter(Boolean)
    .slice(0, 4);

  return (
    <Box
      component="aside"
      aria-label={t("settings.configForms.workbench.profileSummary.title")}
    >
      <Typography
        component="h2"
        variant="h6"
        fontWeight={900}
        sx={{ textTransform: "uppercase" }}
      >
        {t("settings.configForms.workbench.profileSummary.title")}
      </Typography>
      <Typography
        variant="overline"
        color="text.primary"
        sx={{ display: "block", mb: 1.5 }}
      >
        {t("settings.configForms.workbench.profileSummary.sequence")}
      </Typography>
      <Stack spacing={2}>
        {sections.map((section, index) => (
          <FlowRow
            key={section.id}
            number={index + 1}
            title={t(section.titleKey)}
            value={summarizeSection(section, data, t)}
          />
        ))}
      </Stack>
      <Divider sx={{ my: 1.5 }} />
      <Alert severity={data?.enabled === false ? "info" : "success"}>
        {data?.enabled === false
          ? t("settings.configForms.workbench.profileSummary.inactiveNotice")
          : t("settings.configForms.workbench.profileSummary.activeNotice")}
      </Alert>
    </Box>
  );
}
