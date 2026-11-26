import { Alert, Box, Button, Card, CardContent, CardHeader, Chip, Divider, Grid2 as Grid, LinearProgress, Stack, Typography } from "@mui/material";
import { DeveloperBoard as CpuIcon, Memory as RamIcon, Storage as DiskIcon } from "@mui/icons-material";
import { LineChart } from "@mui/x-charts/LineChart";
import { useTheme } from "@mui/material/styles";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { useSystemUsage } from "@/features/system-usage/SystemUsageProvider";
import { memoryDisplay } from "@/features/system-usage/memoryDisplay";

const metricDefinitions = [
  {
    key: "cpu",
    dataKey: "cpu_usage",
    historyKey: "cpu_percent",
    colorKey: "primary",
    icon: CpuIcon,
  },
  {
    key: "ram",
    dataKey: "ram_usage",
    historyKey: "ram_percent",
    colorKey: "success",
    icon: RamIcon,
  },
  {
    key: "disk",
    dataKey: "disk_usage",
    historyKey: "disk_percent",
    colorKey: "info",
    icon: DiskIcon,
  },
];

const statusColor = {
  ok: "success",
  warning: "warning",
  critical: "error",
  partial: "warning",
  stale: "warning",
  unavailable: "default",
  loading: "default",
};

const alertSeverity = {
  warning: "warning",
  critical: "error",
  partial: "warning",
  stale: "warning",
  unavailable: "info",
};

const ResourceTelemetryCard = () => {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const { data: system, isLoading, isError, isFetching, refetch } = useSystemUsage();
  const locale = i18n.resolvedLanguage || "de";
  const ram = memoryDisplay(system?.ram_usage, t, locale);
  const metricLabel = (key) => key === "ram" ? ram.label : t(`dashboard.resources.metrics.${key}`);

  const formatNumber = (value, maximumFractionDigits = 2) => new Intl.NumberFormat(locale, { maximumFractionDigits }).format(value);
  const formatDateTime = (value) => {
    const date = value ? new Date(value) : null;
    if (!date || Number.isNaN(date.getTime())) return t("common.unknown");
    return new Intl.DateTimeFormat(locale, {
      dateStyle: "short",
      timeStyle: "medium",
    }).format(date);
  };

  const staleAfterSeconds = Math.max(60, (Number(system?.poll_after_seconds) || 15) * 3);
  const isStale = Boolean(system) && Number(system?.data_age_seconds) > staleAfterSeconds;
  const state = isLoading ? "loading" : isError && !system ? "unavailable" : isStale || (isError && system) ? "stale" : system?.status || "unavailable";

  const metrics = metricDefinitions.map((definition) => {
    const metric = system?.[definition.dataKey];
    const available = metric?.available !== false && Number.isFinite(metric?.percent);
    return { ...definition, metric, available };
  });

  const history = useMemo(
    () =>
      (system?.history || [])
        .map((sample) => ({
          ...sample,
          time: new Date(sample.sampled_at),
        }))
        .filter((sample) => !Number.isNaN(sample.time.getTime())),
    [system?.history]
  );
  const historySeries = metricDefinitions.map((definition) => ({
    label: t(`dashboard.resources.metrics.${definition.key}`),
    color: theme.palette[definition.colorKey].main,
    data: history.map((sample) => (Number.isFinite(sample[definition.historyKey]) ? sample[definition.historyKey] : null)),
    showMark: history.length < 10,
    curve: "linear",
    valueFormatter: (value) => (value == null ? t("common.unknown") : `${formatNumber(value, 1)} %`),
  }));
  const historySummary = metricDefinitions
    .map((definition) => {
      const values = history.map((sample) => sample[definition.historyKey]).filter(Number.isFinite);
      if (!values.length) return null;
      return t("dashboard.resources.historySummaryMetric", {
        metric: t(`dashboard.resources.metrics.${definition.key}`),
        minimum: formatNumber(Math.min(...values), 1),
        maximum: formatNumber(Math.max(...values), 1),
      });
    })
    .filter(Boolean)
    .join(" ");

  const sourceLabel = (source) =>
    t(`dashboard.resources.sources.${source || "unavailable"}`, {
      defaultValue: source || t("common.unknown"),
    });
  const metricUnit = (metric) => (metric?.unit === "cores" ? t("dashboard.resources.units.cores") : metric?.unit || "");
  const metricValue = (metric, available) =>
    available && Number.isFinite(metric?.used) && Number.isFinite(metric?.total)
      ? t("dashboard.resources.usedTotal", {
          used: formatNumber(metric.used),
          total: formatNumber(metric.total),
          unit: metricUnit(metric),
        })
      : t("common.unknown");

  const warningText = (system?.warnings || [])
    .map((warning) => {
      const metric = system?.[`${warning.metric}_usage`];
      return t("dashboard.resources.warningDetail", {
        metric: metricLabel(warning.metric),
        percent: Number.isFinite(metric?.percent) ? formatNumber(metric.percent, 1) : t("common.unknown"),
        threshold: warning.threshold_percent,
      });
    })
    .join(" ");

  return (
    <Card data-testid="resource-telemetry-card" sx={{ height: "100%" }}>
      <CardHeader title={t("dashboard.resources.title")} subheader={t("dashboard.resources.subtitle")} action={<Chip size="small" color={statusColor[state]} label={t(`dashboard.resources.states.${state}`)} data-testid="resource-status" />} />
      <CardContent sx={{ pt: 0 }}>
        {state !== "ok" && state !== "loading" && (
          <Alert
            severity={alertSeverity[state] || "info"}
            sx={{ mb: 2 }}
            action={
              ["stale", "unavailable", "partial"].includes(state) ? (
                <Button component={state === "stale" ? "button" : Link} to={state === "stale" ? undefined : "/settings/services"} color="inherit" size="small" onClick={state === "stale" ? () => refetch() : undefined}>
                  {state === "stale" ? t("common.retry") : t("dashboard.resources.openServices")}
                </Button>
              ) : null
            }
          >
            {warningText || t(`dashboard.resources.messages.${state}`)}
          </Alert>
        )}

        <Grid container spacing={1.5}>
          {metrics.map(({ key, icon: MetricIcon, metric, available }) => {
            const progressColor = metric?.severity === "critical" ? "error.main" : metric?.severity === "warning" ? "warning.main" : available ? "success.main" : "text.disabled";
            const percentage = available ? Math.round(metric.percent) : null;

            return (
              <Grid key={key} size={{ xs: 12, md: 4 }}>
                <Box
                  sx={{
                    p: 1.5,
                    height: "100%",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                  }}
                >
                  <Stack direction="row" alignItems="center" justifyContent="space-between" spacing={1}>
                    <Stack direction="row" alignItems="center" spacing={0.75}>
                      <MetricIcon fontSize="small" color="action" />
                      <Typography variant="subtitle2">{metricLabel(key)}</Typography>
                    </Stack>
                    <Typography variant="h6">{percentage == null ? "—" : `${percentage} %`}</Typography>
                  </Stack>
                  <LinearProgress
                    variant="determinate"
                    value={available ? metric.percent : 0}
                    aria-label={metricLabel(key)}
                    aria-valuetext={
                      available
                        ? t("dashboard.resources.percentUsed", {
                            percent: percentage,
                          })
                        : t("common.unknown")
                    }
                    sx={{
                      mt: 1,
                      height: 6,
                      bgcolor: "action.disabledBackground",
                      "& .MuiLinearProgress-bar": { bgcolor: progressColor },
                    }}
                  />
                  <Typography variant="body2" sx={{ mt: 1 }}>
                    {key === "ram" && ram.capacity ? ram.capacity : metricValue(metric, available)}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("dashboard.resources.source", {
                      source: sourceLabel(metric?.source),
                    })}
                  </Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>

        <Divider sx={{ my: 2 }} />
        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={0.5} sx={{ mb: 1 }}>
          <Typography variant="subtitle2">{t("dashboard.resources.history")}</Typography>
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.resources.range", {
              minutes: Math.max(0, Math.round(Number(system?.range?.seconds || 0) / 60)),
              interval: Number(system?.range?.sample_interval_seconds || 0),
            })}
          </Typography>
        </Stack>

        {history.length >= 2 ? (
          <Box
            role="img"
            aria-label={t("dashboard.resources.historySummary", {
              summary: historySummary,
            })}
            sx={{ minWidth: 0 }}
          >
            <LineChart
              aria-hidden="true"
              height={190}
              margin={{ left: 48, right: 12, top: 28, bottom: 24 }}
              xAxis={[
                {
                  data: history.map((sample) => sample.time),
                  scaleType: "time",
                  valueFormatter: (value) =>
                    new Intl.DateTimeFormat(locale, {
                      hour: "2-digit",
                      minute: "2-digit",
                    }).format(value),
                },
              ]}
              yAxis={[
                {
                  min: 0,
                  max: 100,
                  valueFormatter: (value) => `${value} %`,
                },
              ]}
              series={historySeries}
              grid={{ horizontal: true }}
              skipAnimation
            />
          </Box>
        ) : (
          <Alert severity="info">{t("dashboard.resources.historyUnavailable")}</Alert>
        )}

        <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" spacing={0.5} sx={{ mt: 1 }}>
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.resources.sampledAt", {
              time: formatDateTime(system?.sampled_at),
            })}
            {isFetching ? ` · ${t("dashboard.resources.refreshing")}` : ""}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.resources.thresholds")}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default ResourceTelemetryCard;
