import { cmd } from "@/utils/fetchUtils";
import {
  ListItem,
  Tooltip,
  Stack,
  Typography,
  Box,
  LinearProgress,
} from "@mui/material";
import { useQuery } from "@tanstack/react-query";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrochip } from "@fortawesome/free-solid-svg-icons/faMicrochip";
import { faHardDrive } from "@fortawesome/free-solid-svg-icons/faHardDrive";
import { faMemory } from "@fortawesome/free-solid-svg-icons/faMemory";
import { byUsage } from "./utils";
import { useTranslation } from "react-i18next";
import { demoSystemUsage, isFakeMode } from "@/mirage/demo-data";

const SystemUsage = () => {
  const { t } = useTranslation();
  const { data: system, isLoading } = useQuery({
    queryKey: [{ queryIdentified: "get_system_usage" }],
    queryFn: isFakeMode()
      ? () => Promise.resolve(demoSystemUsage)
      : cmd.GET_SYSTEM_USAGE,
    staleTime: 10 * 1000,
    refetchInterval: (query) =>
      Math.max(10, Number(query.state.data?.poll_after_seconds) || 15) * 1000,
    refetchIntervalInBackground: false,
  });

  const metrics = system
    ? [
        {
          key: "CPU",
          icon: faMicrochip,
          value: system.cpu_usage?.percent,
          available: system.cpu_usage?.available !== false,
          tooltip:
            system.cpu_usage?.percent == null
              ? t("common.unknown")
              : `CPU: ${system.cpu_usage.percent}%`,
        },
        {
          key: "RAM",
          icon: faMemory,
          value: system.ram_usage?.percent,
          available: system.ram_usage?.available !== false,
          tooltip:
            system.ram_usage?.percent == null
              ? t("common.unknown")
              : `RAM: ${system.ram_usage.percent}%`,
        },
        {
          key: "SSD",
          icon: faHardDrive,
          value: system.disk_usage?.percent,
          available: system.disk_usage?.available !== false,
          tooltip:
            system.disk_usage?.percent == null
              ? t("common.unknown")
              : `SSD: ${system.disk_usage.percent}%`,
        },
      ]
    : [];

  return (
    <ListItem disableGutters sx={{ display: "block", pb: 1.25 }}>
      <Typography
        variant="caption"
        color="primary.light"
        sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}
      >
        {t("sidebar.system")}
      </Typography>
      <Stack spacing={0.8}>
        {(isLoading
          ? ["CPU", "RAM", "SSD"].map((key) => ({
              key,
              value: null,
              available: false,
            }))
          : metrics
        ).map((metric) => {
          const available =
            metric.available !== false && Number.isFinite(metric.value);
          const roundedValue = available ? Math.round(metric.value) : null;
          const valueText = isLoading
            ? t("common.loading")
            : available
            ? `${roundedValue}%`
            : t("common.unknown");

          return (
            <Tooltip
              key={metric.key}
              title={metric.tooltip || t("common.loading")}
              placement="right"
            >
              <Box>
                <Stack direction="row" alignItems="center" spacing={0.8}>
                  {metric.icon && (
                    <FontAwesomeIcon
                      icon={metric.icon}
                      color={byUsage(available ? metric.value : null)}
                    />
                  )}
                  <Typography variant="caption" sx={{ width: 28 }}>
                    {metric.key}
                  </Typography>
                  <LinearProgress
                    aria-label={metric.key}
                    aria-valuetext={valueText}
                    variant="determinate"
                    value={available ? metric.value : 0}
                    sx={{
                      flexGrow: 1,
                      height: 4,
                      bgcolor: "grey.800",
                      "& .MuiLinearProgress-bar": { bgcolor: "secondary.main" },
                    }}
                  />
                  <Typography
                    variant="caption"
                    sx={{ width: 32, textAlign: "right" }}
                  >
                    {available ? `${roundedValue}%` : "—"}
                  </Typography>
                </Stack>
              </Box>
            </Tooltip>
          );
        })}
      </Stack>
    </ListItem>
  );
};

export default SystemUsage;
