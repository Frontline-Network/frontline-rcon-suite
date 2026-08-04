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
import {
  faMicrochip,
  faHardDrive,
  faMemory,
} from "@fortawesome/free-solid-svg-icons";
import { byUsage } from "./utils";
import { useTranslation } from "react-i18next";
import { demoSystemUsage, isFakeMode } from "@/mirage/demo-data";

const SystemUsage = () => {
  const { t } = useTranslation();
  const { data: system, isLoading } = useQuery({
    queryKey: [{ queryIdentified: "get_system_usage" }],
    queryFn: isFakeMode() ? () => Promise.resolve(demoSystemUsage) : cmd.GET_SYSTEM_USAGE,
    refetchInterval: 15 * 1000,
  });

  const metrics = system ? [
    { key: "CPU", icon: faMicrochip, value: system.cpu_usage?.percent, tooltip: `CPU: ${system.cpu_usage?.percent ?? 0}%` },
    { key: "RAM", icon: faMemory, value: system.ram_usage?.percent, tooltip: `RAM: ${system.ram_usage?.percent ?? 0}%` },
    { key: "SSD", icon: faHardDrive, value: system.disk_usage?.percent, tooltip: `SSD: ${system.disk_usage?.percent ?? 0}%` },
  ] : [];

  return (
    <ListItem disableGutters sx={{ display: "block", pb: 1.25 }}>
      <Typography variant="caption" color="primary.light" sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}>
        {t("sidebar.system")}
      </Typography>
      <Stack spacing={0.8}>
        {(isLoading ? ["CPU", "RAM", "SSD"].map((key) => ({ key, value: 0 })) : metrics).map((metric) => (
          <Tooltip key={metric.key} title={metric.tooltip || t("common.loading")} placement="right">
            <Box>
              <Stack direction="row" alignItems="center" spacing={0.8}>
                {metric.icon && <FontAwesomeIcon icon={metric.icon} color={byUsage(metric.value || 0)} />}
                <Typography variant="caption" sx={{ width: 28 }}>{metric.key}</Typography>
                <LinearProgress
                  variant="determinate"
                  value={metric.value || 0}
                  sx={{ flexGrow: 1, height: 4, bgcolor: "grey.800", "& .MuiLinearProgress-bar": { bgcolor: "secondary.main" } }}
                />
                <Typography variant="caption" sx={{ width: 32, textAlign: "right" }}>{Math.round(metric.value || 0)}%</Typography>
              </Stack>
            </Box>
          </Tooltip>
        ))}
      </Stack>
    </ListItem>
  );
};

export default SystemUsage;
