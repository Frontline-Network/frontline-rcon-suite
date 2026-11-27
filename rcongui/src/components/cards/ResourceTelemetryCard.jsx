import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Grid2 as Grid,
  LinearProgress,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import {
  DeveloperBoard as CpuIcon,
  Memory as RamIcon,
  Storage as DiskIcon,
  ExpandMore as ExpandMoreIcon,
} from "@mui/icons-material";
import { LineChart } from "@mui/x-charts/LineChart";
import { useTheme } from "@mui/material/styles";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import { useSystemUsage } from "@/features/system-usage/SystemUsageProvider";
import {
  formatMemorySize,
  memoryBytes,
  memoryDisplay,
  memoryHistoryDisplay,
  rconMemoryDisplay,
} from "@/features/system-usage/memoryDisplay";

const percentageDefinitions = [
  {
    key: "cpu",
    dataKey: "cpu_usage",
    historyKey: "cpu_percent",
    colorKey: "primary",
    icon: CpuIcon,
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

const ResourceTelemetryCard = ({ embedded = false }) => {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const {
    data: system,
    isLoading,
    isError,
    isFetching,
    refetch,
  } = useSystemUsage();
  const locale = i18n.resolvedLanguage || "de";
  const formatNumber = (value, maximumFractionDigits = 2) =>
    new Intl.NumberFormat(locale, { maximumFractionDigits }).format(value);
  const formatDateTime = (value) => {
    const date = value ? new Date(value) : null;
    return !date || Number.isNaN(date.getTime())
      ? t("common.unknown")
      : new Intl.DateTimeFormat(locale, {
          dateStyle: "short",
          timeStyle: "medium",
        }).format(date);
  };
  const staleAfterSeconds = Math.max(
    60,
    (Number(system?.poll_after_seconds) || 15) * 3
  );
  const isStale =
    Boolean(system) &&
    (Number(system.data_age_seconds) > staleAfterSeconds || isError);
  const ram = rconMemoryDisplay(system?.rcon_ram_usage, t, locale, {
    stale: isStale,
  });
  const backend = memoryDisplay(system?.ram_usage, t, locale);
  const backendAvailable =
    ["cgroup_v1", "cgroup_v2"].includes(system?.ram_usage?.source) &&
    system?.ram_usage?.available !== false &&
    memoryBytes(system.ram_usage) != null;
  const backendValue = backendAvailable
    ? backend.capacity ||
      formatMemorySize(memoryBytes(system.ram_usage), locale)
    : null;
  const warnings = (system?.warnings || []).filter(
    (warning) => warning.metric !== "ram" || backendAvailable
  );
  const baseState = isLoading
    ? "loading"
    : isError && !system
    ? "unavailable"
    : isStale
    ? "stale"
    : system?.status || "unavailable";
  const state =
    (baseState === "ok" && !ram.available) ||
    (baseState === "unavailable" && ram.available)
      ? "partial"
      : baseState;
  const metricLabel = (key) =>
    key === "ram" ? backend.label : t(`dashboard.resources.metrics.${key}`);
  const warningText = warnings
    .map((warning) => {
      const metric = system?.[`${warning.metric}_usage`];
      return t("dashboard.resources.warningDetail", {
        metric: metricLabel(warning.metric),
        percent: Number.isFinite(metric?.percent)
          ? formatNumber(metric.percent, 1)
          : t("common.unknown"),
        threshold: warning.threshold_percent,
      });
    })
    .join(" ");

  const metrics = [
    { ...percentageDefinitions[0], metric: system?.cpu_usage },
    { key: "ram", icon: RamIcon },
    { ...percentageDefinitions[1], metric: system?.disk_usage },
  ];
  const history = useMemo(
    () =>
      (system?.history || [])
        .map((sample) => ({ ...sample, time: new Date(sample.sampled_at) }))
        .filter((sample) => !Number.isNaN(sample.time.getTime())),
    [system?.history]
  );
  const ramHistory = memoryHistoryDisplay(history, locale);
  const percentageSeries = percentageDefinitions.map((definition) => ({
    label: t(`dashboard.resources.metrics.${definition.key}`),
    color: theme.palette[definition.colorKey].main,
    data: history.map((sample) =>
      Number.isFinite(sample[definition.historyKey])
        ? sample[definition.historyKey]
        : null
    ),
    showMark: history.length < 10,
    curve: "linear",
    valueFormatter: (value) =>
      value == null ? t("common.unknown") : `${formatNumber(value, 1)} %`,
  }));
  const historySummary = percentageDefinitions
    .map((definition) => {
      const values = history
        .map((sample) => sample[definition.historyKey])
        .filter(Number.isFinite);
      return values.length
        ? t("dashboard.resources.historySummaryMetric", {
            metric: t(`dashboard.resources.metrics.${definition.key}`),
            minimum: formatNumber(Math.min(...values), 1),
            maximum: formatNumber(Math.max(...values), 1),
          })
        : null;
    })
    .filter(Boolean)
    .join(" ");
  const xAxis = [
    {
      data: history.map((sample) => sample.time),
      scaleType: "time",
      valueFormatter: (value) =>
        new Intl.DateTimeFormat(locale, {
          hour: "2-digit",
          minute: "2-digit",
        }).format(value),
    },
  ];
  const sourceLabel = (source) =>
    t(`dashboard.resources.sources.${source || "unavailable"}`, {
      defaultValue: source || t("common.unknown"),
    });

  return (
    <Card
      data-testid="resource-telemetry-card"
      sx={{
        height: "100%",
        ...(embedded
          ? { boxShadow: "none", backgroundImage: "none", border: 0 }
          : {}),
      }}
    >
      <CardHeader
        title={embedded ? undefined : t("dashboard.resources.title")}
        subheader={t("dashboard.resources.rconRamDescription")}
        action={
          <Chip
            size="small"
            color={statusColor[state]}
            label={t(`dashboard.resources.states.${state}`)}
            data-testid="resource-status"
          />
        }
      />
      <CardContent sx={{ pt: 0, px: { xs: 1, sm: 2 } }}>
        {state !== "ok" && state !== "loading" && (
          <Alert
            severity={alertSeverity[state] || "info"}
            sx={{ mb: 2 }}
            action={
              ["stale", "unavailable", "partial"].includes(state) ? (
                <Button
                  component={state === "stale" ? "button" : Link}
                  to={state === "stale" ? undefined : "/settings/services"}
                  color="inherit"
                  size="small"
                  onClick={state === "stale" ? () => refetch() : undefined}
                >
                  {state === "stale"
                    ? t("common.retry")
                    : t("dashboard.resources.openServices")}
                </Button>
              ) : null
            }
          >
            {warningText || t(`dashboard.resources.messages.${state}`)}
          </Alert>
        )}
        <Grid container spacing={1.5}>
          {metrics.map(({ key, icon: MetricIcon, metric }) => {
            const available =
              key === "ram"
                ? ram.available
                : metric?.available !== false &&
                  Number.isFinite(metric?.percent);
            const label = key === "ram" ? ram.label : metricLabel(key);
            const percentage =
              available && key !== "ram" ? Math.round(metric.percent) : null;
            const usedTotal =
              available &&
              Number.isFinite(metric?.used) &&
              Number.isFinite(metric?.total)
                ? t("dashboard.resources.usedTotal", {
                    used: formatNumber(metric.used),
                    total: formatNumber(metric.total),
                    unit:
                      metric.unit === "cores"
                        ? t("dashboard.resources.units.cores")
                        : metric.unit || "",
                  })
                : t("common.unknown");
            return (
              <Grid key={key} size={{ xs: 12, md: 4 }}>
                <Box
                  data-testid={key === "ram" ? "rcon-ram-metric" : undefined}
                  sx={{
                    p: 1.5,
                    height: "100%",
                    border: "1px solid",
                    borderColor: "divider",
                    borderRadius: 1,
                  }}
                >
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    spacing={1}
                  >
                    <Stack direction="row" alignItems="center" spacing={0.75}>
                      <MetricIcon fontSize="small" color="action" />
                      <Typography variant="subtitle2">{label}</Typography>
                    </Stack>
                    <Typography variant="h6" sx={{ whiteSpace: "nowrap" }}>
                      {key === "ram"
                        ? ram.value || "—"
                        : percentage == null
                        ? "—"
                        : `${percentage} %`}
                    </Typography>
                  </Stack>
                  {key === "ram" ? (
                    <>
                      {!ram.available && (
                        <Typography
                          variant="body2"
                          color="text.secondary"
                          sx={{ mt: 1 }}
                        >
                          {ram.unavailableText}
                        </Typography>
                      )}
                      {ram.workingSet && (
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          {t("dashboard.resources.workingSetMemory", {
                            used: ram.workingSet,
                          })}
                        </Typography>
                      )}
                      {ram.reclaimable && (
                        <Tooltip
                          title={t("dashboard.resources.inactiveFileCacheHint")}
                        >
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            sx={{ display: "block", mt: 0.5 }}
                          >
                            {t("dashboard.resources.inactiveFileCache", {
                              used: ram.reclaimable,
                            })}
                          </Typography>
                        </Tooltip>
                      )}
                    </>
                  ) : (
                    <>
                      <LinearProgress
                        variant="determinate"
                        value={available ? metric.percent : 0}
                        aria-label={label}
                        aria-valuetext={
                          percentage == null
                            ? t("common.unknown")
                            : t("dashboard.resources.percentUsed", {
                                percent: percentage,
                              })
                        }
                        sx={{
                          mt: 1,
                          height: 6,
                          bgcolor: "action.disabledBackground",
                          "& .MuiLinearProgress-bar": {
                            bgcolor:
                              metric?.severity === "critical"
                                ? "error.main"
                                : metric?.severity === "warning"
                                ? "warning.main"
                                : "success.main",
                          },
                        }}
                      />
                      <Typography variant="body2" sx={{ mt: 1 }}>
                        {usedTotal}
                      </Typography>
                    </>
                  )}
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ display: "block", mt: 0.5 }}
                  >
                    {t("dashboard.resources.source", {
                      source:
                        key === "ram"
                          ? sourceLabel("rcon_services")
                          : sourceLabel(metric?.source),
                    })}
                  </Typography>
                </Box>
              </Grid>
            );
          })}
        </Grid>

        <Accordion
          disableGutters
          elevation={0}
          sx={{
            mt: 1.5,
            bgcolor: "transparent",
            "&:before": { display: "none" },
          }}
        >
          <AccordionSummary
            expandIcon={<ExpandMoreIcon />}
            aria-controls="rcon-memory-breakdown"
            id="rcon-memory-breakdown-title"
          >
            <Typography variant="subtitle2">
              {t("dashboard.resources.memoryBreakdown")}
            </Typography>
          </AccordionSummary>
          <AccordionDetails
            id="rcon-memory-breakdown"
            data-testid="rcon-memory-breakdown"
          >
            {ram.available ? (
              <>
                <Stack
                  direction={{ xs: "column", sm: "row" }}
                  spacing={2}
                  sx={{ mb: 1 }}
                >
                  <Typography variant="body2">
                    {t("dashboard.resources.dedicatedMemory")}:{" "}
                    <strong>{ram.dedicated || "—"}</strong>
                  </Typography>
                  <Typography variant="body2">
                    {t("dashboard.resources.sharedMemory")}:{" "}
                    <strong>{ram.shared || "—"}</strong>
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.resources.sharedMemoryExplanation")}
                </Typography>
                {["dedicated", "shared"].map((scope) => (
                  <Box key={scope} sx={{ mt: 1 }}>
                    <Typography variant="caption" color="text.secondary">
                      {t(
                        `dashboard.resources.${
                          scope === "dedicated"
                            ? "dedicatedMemory"
                            : "sharedMemory"
                        }`
                      )}
                    </Typography>
                    {ram.components
                      .filter((item) => item.scope === scope)
                      .map((item) => (
                        <Stack
                          key={item.service}
                          direction="row"
                          justifyContent="space-between"
                          spacing={2}
                          sx={{ py: 0.4 }}
                        >
                          <Typography variant="body2">
                            {t(
                              `dashboard.resources.componentNames.${item.service}`,
                              { defaultValue: item.service }
                            )}
                          </Typography>
                          <Typography
                            variant="body2"
                            sx={{ whiteSpace: "nowrap" }}
                          >
                            {formatMemorySize(item.used_bytes, locale)}
                          </Typography>
                        </Stack>
                      ))}
                  </Box>
                ))}
              </>
            ) : (
              <Typography variant="body2">{ram.unavailableText}</Typography>
            )}
            {backendValue && (
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 1.5 }}
                data-testid="backend-memory-detail"
              >
                {t("dashboard.resources.backendMemoryDetail")}: {backendValue}
              </Typography>
            )}
          </AccordionDetails>
        </Accordion>

        <Divider sx={{ my: 1.5 }} />
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          spacing={0.5}
          sx={{ mb: 1 }}
        >
          <Typography variant="subtitle2">
            {t("dashboard.resources.history")}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.resources.range", {
              minutes: Math.max(
                0,
                Math.round(Number(system?.range?.seconds || 0) / 60)
              ),
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
              height={155}
              margin={{ left: 48, right: 12, top: 28, bottom: 24 }}
              xAxis={xAxis}
              yAxis={[
                { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
              ]}
              series={percentageSeries}
              grid={{ horizontal: true }}
              skipAnimation
            />
          </Box>
        ) : (
          <Alert severity="info">
            {t("dashboard.resources.historyUnavailable")}
          </Alert>
        )}

        <Typography variant="subtitle2" sx={{ mt: 1.5 }}>
          {t("dashboard.resources.rconMemoryHistory")}
        </Typography>
        {ramHistory.available ? (
          <Box
            role="img"
            data-testid="rcon-memory-history"
            aria-label={t("dashboard.resources.memoryHistorySummary", {
              minimum: ramHistory.minimum,
              maximum: ramHistory.maximum,
            })}
            sx={{ minWidth: 0 }}
          >
            <LineChart
              aria-hidden="true"
              height={160}
              margin={{ left: 65, right: 12, top: 25, bottom: 24 }}
              xAxis={xAxis}
              yAxis={[
                {
                  min: 0,
                  valueFormatter: (value) =>
                    `${formatNumber(value, 1)} ${ramHistory.unit}`,
                },
              ]}
              series={[
                {
                  label: ram.label,
                  color: theme.palette.success.main,
                  data: ramHistory.data,
                  curve: "linear",
                  showMark:
                    ramHistory.data.filter((value) => value != null).length <
                    10,
                  valueFormatter: (value) =>
                    value == null
                      ? t("common.unknown")
                      : `${formatNumber(value, 2)} ${ramHistory.unit}`,
                },
              ]}
              grid={{ horizontal: true }}
              skipAnimation
            />
          </Box>
        ) : (
          <Alert severity="info">
            {t("dashboard.resources.historyUnavailable")}
          </Alert>
        )}
        <Stack
          direction={{ xs: "column", sm: "row" }}
          justifyContent="space-between"
          spacing={0.5}
          sx={{ mt: 1 }}
        >
          <Typography variant="caption" color="text.secondary">
            {t("dashboard.resources.sampledAt", {
              time: formatDateTime(
                system?.rcon_ram_usage?.sampled_at || system?.sampled_at
              ),
            })}
            {isFetching ? ` · ${t("dashboard.resources.refreshing")}` : ""}
          </Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default ResourceTelemetryCard;
