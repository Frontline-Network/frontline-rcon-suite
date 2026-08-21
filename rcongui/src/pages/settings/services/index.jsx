import {
  Button,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
  AccordionActions,
  Chip,
  Stack,
  Alert,
  Divider,
  AlertTitle,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { cmd } from "@/utils/fetchUtils";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";
import localizedFormat from "dayjs/plugin/localizedFormat";
import { Form, useLoaderData } from "react-router-dom";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import PageHeader from "@/components/shared/PageHeader";
import { demoServices, isFakeMode } from "@/mirage/demo-data";

dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);

export const loader = async () => {
  const services = isFakeMode() ? demoServices : await cmd.GET_SERVICES();
  let deadLetters = [];
  if (!isFakeMode()) {
    try {
      deadLetters = await cmd.GET_WEBHOOK_DEAD_LETTERS();
    } catch {
      // Webhook queues are deliberately a separate permission. Operators who
      // cannot inspect them must still be able to use the services page.
    }
  }
  return {
    services: services.map((service) => ({
      ...service,
      uptime: dayjs(service.start * 1000).from(service.now * 1000),
      title: service.name.replaceAll("_", " ").toUpperCase(),
      start: dayjs(service.start * 1000).format("LLL"),
      stop: dayjs(service.stop * 1000).format("LLL"),
      now: dayjs(service.now * 1000).format("LLL"),
    })),
    deadLetters,
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

const isRunning = (service) => service.statename === "RUNNING";

const Services = () => {
  const { services, deadLetters: initialDeadLetters } = useLoaderData();
  const { t } = useTranslation();
  const [deadLetters, setDeadLetters] = useState(initialDeadLetters);
  const [retryingId, setRetryingId] = useState(null);

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
      toast.error(error?.message || t("settings.services.webhooks.retryFailed"));
    } finally {
      setRetryingId(null);
    }
  };

  return (
    <Stack sx={{ maxWidth: (theme) => theme.breakpoints.values.md }}>
      <PageHeader
        eyebrow={t("settings.services.eyebrow")}
        title={t("settings.services.title")}
        subtitle={t("settings.services.subtitle")}
      />
      <Alert
        sx={{ mb: 2 }}
        severity="info"
        action={
          <Button href="/api/logs" component={"a"}>
            {t("settings.services.searchLogs")}
          </Button>
        }
      >
        {t("settings.services.hint")}
      </Alert>
      {deadLetters.length > 0 && (
        <Alert severity="warning" sx={{ mb: 2 }}>
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
                  {entry.server_number} · {entry.message_type} · {entry.reason} ·{" "}
                  {dayjs(entry.failed_at).format("LLL")}
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
      {services.map((service) => {
        return (
          <Accordion key={service.name}>
            <AccordionSummary
              expandIcon={<ExpandMoreIcon />}
              aria-controls={`${service.name}-content`}
              id={`${service.name}-header`}
            >
              <Stack direction={"row"} gap={1} sx={{ minWidth: 300 }}>
                <Chip
                  sx={{ flexBasis: 80 }}
                  color={stateColor[service.statename]}
                  label={service.statename}
                />
                <Typography>{service.title}</Typography>
              </Stack>
            </AccordionSummary>

            <AccordionDetails>
              <Stack component={"section"} gap={4}>
                {service.spawnerr && (
                  <Alert severity="error">
                    <AlertTitle>{t("settings.services.error")}</AlertTitle>
                    {service.spawnerr}
                  </Alert>
                )}
                <Stack
                  direction={"row"}
                  alignItems={"center"}
                  flexWrap={true}
                  gap={1}
                >
                  <Typography variant="caption">
                    {`${isRunning(service) ? t("settings.services.started") : t("settings.services.stopped")} ${
                      service.uptime
                    }`}
                  </Typography>
                  <Divider orientation="vertical" flexItem />
                  <Typography variant="caption">
                    {t("settings.services.stoppedAt")} {service.stop}
                  </Typography>
                  <Divider orientation="vertical" flexItem />
                  <Typography variant="caption">
                    {t("settings.services.startedAt")} {service.start}
                  </Typography>
                </Stack>
              </Stack>
              <Divider sx={{ my: 0.5 }} orientation="horizontal" flexItem />
              <Typography>
                {service.info || t("settings.services.missingDescription")}
              </Typography>
            </AccordionDetails>

            <AccordionActions>
              <Form method="POST">
                <input
                  name={"service_name"}
                  value={service.name}
                  hidden
                  readOnly
                />
                <Button
                  type="submit"
                  variant="contained"
                  color={isRunning(service) ? "secondary" : "primary"}
                  name={"action"}
                  value={isRunning(service) ? "stop" : "start"}
                >
                  {isRunning(service) ? t("settings.services.stop") : t("settings.services.start")}
                </Button>
              </Form>
            </AccordionActions>
          </Accordion>
        );
      })}
    </Stack>
  );
};

export default Services;
