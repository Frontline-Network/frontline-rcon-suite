import {
  Accordion,
  AccordionActions,
  AccordionDetails,
  AccordionSummary,
  Alert,
  AlertTitle,
  Box,
  Button,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import PrecisionManufacturingOutlinedIcon from "@mui/icons-material/PrecisionManufacturingOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import SettingsApplicationsOutlinedIcon from "@mui/icons-material/SettingsApplicationsOutlined";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import { cmd } from "@/utils/fetchUtils";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import localizedFormat from "dayjs/plugin/localizedFormat";
import { Form, useLoaderData } from "react-router-dom";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { demoServices, isFakeMode } from "@/mirage/demo-data";
import SystemDiagnosticsLayout from "../system-diagnostics/SystemDiagnosticsLayout";
import { ControlSectionHeader } from "../general-group/ControlPageLayout";

dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);

export const loader = async () => {
  const services = isFakeMode() ? demoServices : await cmd.GET_SERVICES();
  let deadLetters = [];
  let diagnosticsPreview = null;
  let operationalHealth = null;
  if (!isFakeMode()) {
    try {
      deadLetters = await cmd.GET_WEBHOOK_DEAD_LETTERS();
    } catch {
      // Webhook queues are deliberately a separate permission. Operators who
      // cannot inspect them must still be able to use the services page.
    }
    try {
      diagnosticsPreview = await cmd.GET_SUPPORT_DIAGNOSTICS_PREVIEW();
    } catch {
      // Keep service controls available for older installations and custom roles.
    }
    try {
      operationalHealth = await cmd.GET_OPERATIONAL_HEALTH({
        params: { window_minutes: 15 },
      });
    } catch {
      // A missing health endpoint must not make service controls unavailable.
    }
  }
  return {
    services: services.map((service) => ({
      ...service,
      uptime: dayjs(service.start * 1000).from(service.now * 1000),
      title: service.name.replaceAll("_", " ").toUpperCase(),
      start: service.start ? dayjs(service.start * 1000).format("LLL") : null,
      stop: service.stop ? dayjs(service.stop * 1000).format("LLL") : null,
      now: dayjs(service.now * 1000).format("LLL"),
    })),
    deadLetters,
    diagnosticsPreview,
    operationalHealth,
  };
};

export const action = async ({ request }) => {
  const formData = Object.fromEntries(await request.formData());
  const data = await cmd.TOGGLE_SERVICE({ payload: formData });
  return data;
};

const stateColor = {
  RUNNING: "success",
  STOPPED: "default",
  FATAL: "error",
  EXITED: "info",
};

const serviceRoles = [
  { id: "rcon", match: /rcon/i, icon: DnsOutlinedIcon },
  { id: "worker", match: /worker/i, icon: PrecisionManufacturingOutlinedIcon },
  { id: "scheduler", match: /scheduler|schedule/i, icon: ScheduleOutlinedIcon },
];

const getServiceRole = (service) =>
  serviceRoles.find((role) => role.match.test(service?.name || "")) || {
    id: "generic",
    icon: SettingsApplicationsOutlinedIcon,
  };

const isRunning = (service) => service?.statename === "RUNNING";

const getStateLabel = (service, t) => {
  if (!service) return t("settings.services.missingDescription");
  if (service.statename === "RUNNING") return t("settings.services.started");
  if (service.statename === "FATAL") return t("settings.services.error");
  return t("settings.services.stopped");
};

function StatusMetric({ label, value, hint, tone = "text.primary" }) {
  return (
    <Box data-theme-surface="panel"
      sx={{
        minWidth: 0,
        p: 1.25,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Typography
        variant="overline"
        color="text.secondary"
        sx={{ display: "block", lineHeight: 1.3 }}
      >
        {label}
      </Typography>
      <Typography
        variant="h6"
        sx={{ color: tone, mt: 0.35, fontVariantNumeric: "tabular-nums" }}
      >
        {value}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: { xs: "none", sm: "block" } }}
      >
        {hint}
      </Typography>
    </Box>
  );
}

function ServiceDependencyFlow({ services }) {
  const { t } = useTranslation();

  return (
    <Box data-theme-surface="panel"
      component="section"
      aria-labelledby="service-dependency-title"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          px: 1.5,
          py: 1.25,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography id="service-dependency-title" variant="subtitle2">
          {t("settings.services.health.title")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
          {t("settings.services.subtitle")}
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            md: "minmax(0, 1fr) 32px minmax(0, 1fr) 32px minmax(0, 1fr)",
          },
          gap: { xs: 0.75, md: 0 },
          alignItems: "stretch",
          p: 1.25,
        }}
      >
        {serviceRoles.map((role, index) => {
          const service = services.find((item) => role.match.test(item.name));
          const Icon = role.icon;
          const running = isRunning(service);
          return (
            <Box key={role.id} sx={{ display: "contents" }}>
              <Stack data-theme-surface="panel"
                direction="row"
                alignItems="center"
                spacing={1}
                sx={{
                  minWidth: 0,
                  p: 1.25,
                  border: "1px solid",
                  borderColor: service && !running ? "error.main" : "divider",
                  bgcolor:
                    service && !running ? "action.hover" : "background.default",
                }}
              >
                <Box data-theme-surface="control"
                  sx={{
                    width: 36,
                    height: 36,
                    display: "grid",
                    placeItems: "center",
                    flexShrink: 0,
                    border: "1px solid",
                    borderColor: running ? "success.main" : "divider",
                    color: running ? "success.main" : "text.secondary",
                  }}
                >
                  <Icon fontSize="small" />
                </Box>
                <Box minWidth={0}>
                  <Typography variant="subtitle2" noWrap>
                    {service?.title || role.id.toUpperCase()}
                  </Typography>
                  <Typography
                    variant="caption"
                    sx={{
                      display: "block",
                      color: running
                        ? "success.main"
                        : service
                        ? "error.main"
                        : "text.secondary",
                    }}
                  >
                    {getStateLabel(service, t)}
                  </Typography>
                </Box>
              </Stack>
              {index < serviceRoles.length - 1 && (
                <Box
                  aria-hidden="true"
                  sx={{
                    display: "grid",
                    placeItems: "center",
                    color: "text.secondary",
                    transform: { xs: "rotate(90deg)", md: "none" },
                    minHeight: { xs: 24, md: "auto" },
                  }}
                >
                  <ArrowForwardIcon fontSize="small" />
                </Box>
              )}
            </Box>
          );
        })}
      </Box>
    </Box>
  );
}

function ServiceControl({ service }) {
  const { t } = useTranslation();
  const role = getServiceRole(service);
  const Icon = role.icon;
  const running = isRunning(service);
  const StateIcon = running ? CheckCircleOutlineIcon : ErrorOutlineIcon;

  return (
    <Accordion defaultExpanded={!running} disableGutters>
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        aria-controls={`${service.name}-content`}
        id={`${service.name}-header`}
        sx={{
          minHeight: 58,
          "& .MuiAccordionSummary-content": { minWidth: 0 },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          spacing={1.25}
          minWidth={0}
          width="100%"
        >
          <Box data-theme-surface="control"
            sx={{
              width: 36,
              height: 36,
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
              border: "1px solid",
              borderColor: "divider",
              color: running ? "success.main" : "text.secondary",
            }}
          >
            <Icon fontSize="small" />
          </Box>
          <Box minWidth={0} sx={{ flexGrow: 1 }}>
            <Typography variant="subtitle2" noWrap>
              {service.title}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              component="div"
            >
              {service.info || t("settings.services.missingDescription")}
            </Typography>
          </Box>
          <Chip
            size="small"
            icon={<StateIcon />}
            color={stateColor[service.statename] || "default"}
            label={getStateLabel(service, t)}
            sx={{ flexShrink: 0 }}
          />
        </Stack>
      </AccordionSummary>

      <AccordionDetails id={`${service.name}-content`}>
        <Stack spacing={1.25}>
          {service.spawnerr && (
            <Alert severity="error">
              <AlertTitle>{t("settings.services.error")}</AlertTitle>
              {service.spawnerr}
            </Alert>
          )}

          <Box data-theme-surface="panel"
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(3, minmax(0, 1fr))",
              },
              border: "1px solid",
              borderColor: "divider",
              "& > *:not(:last-child)": {
                borderRight: { sm: "1px solid" },
                borderBottom: { xs: "1px solid", sm: 0 },
                borderColor: "divider",
              },
            }}
          >
            {[
              [
                t("settings.services.started"),
                running ? service.uptime : t("settings.services.notRunning"),
              ],
              [t("settings.services.startedAt"), service.start || "–"],
              [t("settings.services.stoppedAt"), service.stop || "–"],
            ].map(([label, value]) => (
              <Box key={label} sx={{ p: 1 }}>
                <Typography variant="overline" color="text.secondary">
                  {label}
                </Typography>
                <Typography variant="body2" sx={{ mt: 0.25 }}>
                  {value}
                </Typography>
              </Box>
            ))}
          </Box>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: "28px minmax(0, 1fr)",
              gap: 1,
              p: 1.25,
              borderLeft: "2px solid",
              borderColor: running ? "warning.main" : "success.main",
              bgcolor: "background.default",
            }}
          >
            <AccessTimeIcon sx={{ fontSize: 18, color: "text.secondary" }} />
            <Box>
              <Typography variant="subtitle2">
                {t("settings.services.impactTitle")}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.25 }}
              >
                {service.info || t("settings.services.missingDescription")}
              </Typography>
            </Box>
          </Box>
        </Stack>
      </AccordionDetails>

      <AccordionActions
        sx={{ px: 1.5, py: 1, borderTop: "1px solid", borderColor: "divider" }}
      >
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ mr: "auto" }}
        >
          {running ? t("settings.services.stop") : t("settings.services.start")}
        </Typography>
        <Form method="POST">
          <input name="service_name" value={service.name} hidden readOnly />
          <Button
            type="submit"
            variant="contained"
            color={running ? "secondary" : "primary"}
            name="action"
            value={running ? "stop" : "start"}
          >
            {running
              ? t("settings.services.stop")
              : t("settings.services.start")}
          </Button>
        </Form>
      </AccordionActions>
    </Accordion>
  );
}

const Services = () => {
  const {
    services,
    deadLetters: initialDeadLetters,
    diagnosticsPreview,
    operationalHealth: initialOperationalHealth,
  } = useLoaderData();
  const { t } = useTranslation();
  const [deadLetters, setDeadLetters] = useState(initialDeadLetters);
  const [retryingId, setRetryingId] = useState(null);
  const [operationalHealth, setOperationalHealth] = useState(
    initialOperationalHealth
  );
  const [healthWindow, setHealthWindow] = useState(15);

  const summary = useMemo(() => {
    const running = services.filter(isRunning).length;
    const affected = services.length - running;
    const healthState = operationalHealth?.overall_state;
    const healthy = healthState ? healthState === "healthy" : affected === 0;
    return { running, affected, healthy };
  }, [operationalHealth?.overall_state, services]);

  const refreshOperationalHealth = async (windowMinutes) => {
    setHealthWindow(windowMinutes);
    try {
      setOperationalHealth(
        await cmd.GET_OPERATIONAL_HEALTH({
          params: { window_minutes: windowMinutes },
        })
      );
    } catch (error) {
      toast.error(error?.message || t("settings.services.health.failed"));
    }
  };

  const retryDeadLetter = async (id) => {
    setRetryingId(id);
    try {
      const retried = await cmd.RETRY_WEBHOOK_DEAD_LETTER({
        payload: { dead_letter_id: id },
      });
      if (retried?.result) {
        setDeadLetters((entries) => entries.filter((entry) => entry.id !== id));
        toast.success(t("settings.services.webhooks.retrySuccess"));
      } else {
        toast.error(t("settings.services.webhooks.retryMissing"));
      }
    } catch (error) {
      toast.error(
        error?.message || t("settings.services.webhooks.retryFailed")
      );
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <SystemDiagnosticsLayout>
      <ControlSectionHeader
        title={t("settings.services.title")}
        description={t("settings.services.subtitle")}
      />
      <Stack
        spacing={1.25}
        sx={{
          p: { xs: 1, md: 1.5 },
          "& .MuiAccordion-root": {
            border: "1px solid",
            borderColor: "divider",
            boxShadow: "none",
            bgcolor: "background.paper",
            "&::before": { display: "none" },
          },
          "& .MuiButton-root, & .MuiChip-root": { borderRadius: 0 },
        }}
      >
        <Box
          component="section"
          aria-label={t("settings.services.health.title")}
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "repeat(3, minmax(0, 1fr))",
              lg: "repeat(3, minmax(0, 1fr))",
            },
            gap: 0.75,
          }}
        >
          <StatusMetric
            label={t("settings.services.health.title")}
            value={`${summary.running}/${services.length}`}
            hint={t("settings.services.subtitle")}
            tone={summary.healthy ? "success.main" : "error.main"}
          />
          <StatusMetric
            label={t("settings.services.error")}
            value={summary.affected}
            hint={t("settings.services.hint")}
            tone={summary.affected ? "error.main" : "success.main"}
          />
          <StatusMetric
            label={t("settings.services.health.components.discord_outbox")}
            value={deadLetters.length}
            hint={t("settings.services.webhooks.hint", {
              count: deadLetters.length,
            })}
            tone={deadLetters.length ? "warning.main" : "text.primary"}
          />
        </Box>

        <ServiceDependencyFlow services={services} />

        {operationalHealth && (
          <Alert
            severity={
              operationalHealth.overall_state === "healthy"
                ? "success"
                : operationalHealth.overall_state === "critical"
                ? "error"
                : "warning"
            }
          >
            <AlertTitle>{t("settings.services.health.title")}</AlertTitle>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              gap={1}
              alignItems={{ sm: "center" }}
              flexWrap="wrap"
            >
              {[5, 15, 60].map((minutes) => (
                <Button
                  key={minutes}
                  size="small"
                  variant={healthWindow === minutes ? "contained" : "outlined"}
                  onClick={() => refreshOperationalHealth(minutes)}
                >
                  {t("settings.services.health.window", { minutes })}
                </Button>
              ))}
              {Object.entries(operationalHealth.components || {}).map(
                ([name, component]) => (
                  <Chip
                    key={name}
                    size="small"
                    color={
                      component.state === "healthy"
                        ? "success"
                        : component.state === "offline"
                        ? "error"
                        : "warning"
                    }
                    label={`${t(`settings.services.health.components.${name}`, {
                      defaultValue: name,
                    })}: ${component.state}`}
                  />
                )
              )}
            </Stack>
            <Typography variant="body2" sx={{ mt: 1 }}>
              {t("settings.services.health.lastCheck", {
                time: new Date(operationalHealth.generated_at).toLocaleString(),
              })}
            </Typography>
          </Alert>
        )}

        {diagnosticsPreview && (
          <Alert
            severity="info"
            action={
              <Button href="/api/download_support_diagnostics" component="a">
                {t("settings.services.diagnostics.download")}
              </Button>
            }
          >
            <AlertTitle>{t("settings.services.diagnostics.title")}</AlertTitle>
            <Typography variant="body2">
              {t("settings.services.diagnostics.scope", {
                bytes: diagnosticsPreview.estimated_bytes,
                services: diagnosticsPreview.service_count,
                history: diagnosticsPreview.history_samples,
              })}
            </Typography>
            <Typography variant="body2" sx={{ mt: 0.5 }}>
              {t("settings.services.diagnostics.omitted")}
            </Typography>
          </Alert>
        )}

        {deadLetters.length > 0 && (
          <Alert severity="warning">
            <AlertTitle>{t("settings.services.webhooks.title")}</AlertTitle>
            <Stack gap={1}>
              <Typography variant="body2">
                {t("settings.services.webhooks.hint", {
                  count: deadLetters.length,
                })}
              </Typography>
              {deadLetters.map((entry) => (
                <Stack
                  key={entry.id}
                  direction={{ xs: "column", sm: "row" }}
                  alignItems={{ sm: "center" }}
                  justifyContent="space-between"
                  gap={1}
                >
                  <Typography variant="body2">
                    {entry.server_number} · {entry.message_type} ·{" "}
                    {entry.reason} · {dayjs(entry.failed_at).format("LLL")}
                  </Typography>
                  <Button
                    size="small"
                    variant="outlined"
                    disabled={retryingId === entry.id}
                    onClick={() => retryDeadLetter(entry.id)}
                  >
                    {t("settings.services.webhooks.retry")}
                  </Button>
                </Stack>
              ))}
            </Stack>
          </Alert>
        )}

        <Box
          sx={{
            display: "flex",
            alignItems: { xs: "flex-start", sm: "center" },
            flexDirection: { xs: "column", sm: "row" },
            gap: 1,
            pt: 0.5,
          }}
        >
          <Box sx={{ flexGrow: 1 }}>
            <Typography variant="subtitle1">
              {t("settings.services.title")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("settings.services.subtitle")}
            </Typography>
          </Box>
          <Button href="/api/logs" component="a" variant="outlined">
            {t("settings.services.searchLogs")}
          </Button>
        </Box>

        <Stack spacing={0.75}>
          {services.map((service) => (
            <ServiceControl key={service.name} service={service} />
          ))}
        </Stack>

        <Alert severity="info">{t("settings.services.hint")}</Alert>
      </Stack>
    </SystemDiagnosticsLayout>
  );
};

export default Services;
