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
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { demoServices, isFakeMode } from "@/mirage/demo-data";

dayjs.extend(relativeTime);
dayjs.extend(localizedFormat);

export const loader = async () => {
  const services = isFakeMode() ? demoServices : await cmd.GET_SERVICES();
  return services.map((service) => ({
    ...service,
    uptime: dayjs(service.start * 1000).from(service.now * 1000),
    title: service.name.replaceAll("_", " ").toUpperCase(),
    start: dayjs(service.start * 1000).format("LLL"),
    stop: dayjs(service.stop * 1000).format("LLL"),
    now: dayjs(service.now * 1000).format("LLL"),
  }));
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
  const services = useLoaderData();
  const { t } = useTranslation();

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
