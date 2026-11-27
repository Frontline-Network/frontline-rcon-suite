import {
  ListItem,
  Tooltip,
  Stack,
  Typography,
  LinearProgress,
  ButtonBase,
} from "@mui/material";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import { faMicrochip } from "@fortawesome/free-solid-svg-icons/faMicrochip";
import { faHardDrive } from "@fortawesome/free-solid-svg-icons/faHardDrive";
import { faMemory } from "@fortawesome/free-solid-svg-icons/faMemory";
import { useState } from "react";
import { byUsage } from "./utils";
import { useTranslation } from "react-i18next";
import { useSystemUsage } from "@/features/system-usage/SystemUsageProvider";
import {
  formatMemorySize,
  rconMemoryDisplay,
} from "@/features/system-usage/memoryDisplay";
import SystemUsageDialog from "@/features/system-usage/SystemUsageDialog";

const SystemUsage = () => {
  const { t, i18n } = useTranslation();
  const { data: system, isLoading, isError } = useSystemUsage();
  const [detailsOpen, setDetailsOpen] = useState(false);
  const locale = i18n.resolvedLanguage;
  const stale =
    isError ||
    Number(system?.data_age_seconds) >
      Math.max(60, (Number(system?.poll_after_seconds) || 15) * 3);
  const ram = rconMemoryDisplay(system?.rcon_ram_usage, t, locale, { stale });
  const percentages = [
    { key: "CPU", icon: faMicrochip, metric: system?.cpu_usage },
    { key: "SSD", icon: faHardDrive, metric: system?.disk_usage },
  ];
  const tooltip = (
    <Stack spacing={0.5} sx={{ maxWidth: 330 }}>
      <Typography variant="caption">
        {t("dashboard.resources.rconRamDescription")}
      </Typography>
      {ram.available ? (
        <>
          <Typography variant="caption">
            {t("dashboard.resources.dedicatedMemory")}: {ram.dedicated || "—"}
          </Typography>
          <Typography variant="caption">
            {t("dashboard.resources.sharedMemory")}: {ram.shared || "—"}
          </Typography>
          <Typography variant="caption">
            {t("dashboard.resources.sharedMemoryExplanation")}
          </Typography>
          {ram.workingSet && (
            <Typography variant="caption">
              {t("dashboard.resources.workingSetMemory", {
                used: ram.workingSet,
              })}
            </Typography>
          )}
          {ram.reclaimable && (
            <Typography variant="caption">
              {t("dashboard.resources.inactiveFileCacheHint")}
            </Typography>
          )}
          {ram.components.map((item) => (
            <Typography key={item.service} variant="caption">
              {t("dashboard.resources.componentMemory", {
                service: t(
                  `dashboard.resources.componentNames.${item.service}`,
                  { defaultValue: item.service }
                ),
                used: formatMemorySize(item.used_bytes, locale),
              })}
            </Typography>
          ))}
        </>
      ) : (
        <Typography variant="caption">{ram.unavailableText}</Typography>
      )}
    </Stack>
  );

  const percentageRow = ({ key, icon, metric }) => {
    const available =
      metric?.available !== false && Number.isFinite(metric?.percent);
    const value = available ? Math.round(metric.percent) : null;
    return (
      <Tooltip
        key={key}
        title={available ? `${key}: ${value}%` : t("common.unknown")}
        placement="right"
      >
        <Stack direction="row" alignItems="center" spacing={0.8}>
          <FontAwesomeIcon
            icon={icon}
            color={byUsage(available ? metric.percent : null)}
          />
          <Typography variant="caption" sx={{ minWidth: 28 }}>
            {key}
          </Typography>
          <LinearProgress
            aria-label={key}
            aria-valuetext={available ? `${value}%` : t("common.unknown")}
            variant="determinate"
            value={available ? metric.percent : 0}
            sx={{
              flexGrow: 1,
              height: 4,
              bgcolor: "grey.800",
              "& .MuiLinearProgress-bar": { bgcolor: "secondary.main" },
            }}
          />
          <Typography variant="caption" sx={{ width: 32, textAlign: "right" }}>
            {value == null ? "—" : `${value}%`}
          </Typography>
        </Stack>
      </Tooltip>
    );
  };

  return (
    <>
      <ListItem disableGutters sx={{ display: "block", pb: 1.25 }}>
        <Typography
          variant="caption"
          color="primary.light"
          sx={{ display: "block", mb: 0.75, textTransform: "uppercase" }}
        >
          {t("sidebar.system")}
        </Typography>
        <Stack spacing={0.8}>
          {percentageRow(percentages[0])}
          <Tooltip title={tooltip} placement="right">
            <ButtonBase
              onClick={() => setDetailsOpen(true)}
              aria-label={[
                ram.label,
                ram.value || ram.unavailableText,
                t("dashboard.resources.memoryDetails"),
              ].join(" · ")}
              data-testid="sidebar-rcon-memory"
              sx={{
                width: "100%",
                display: "block",
                textAlign: "left",
                borderRadius: 0.5,
                "&.Mui-focusVisible": {
                  outline: "2px solid",
                  outlineColor: "primary.main",
                  outlineOffset: 3,
                },
              }}
            >
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                spacing={0.8}
              >
                <Stack direction="row" alignItems="center" spacing={0.8}>
                  <FontAwesomeIcon icon={faMemory} />
                  <Typography variant="caption">{ram.label}</Typography>
                </Stack>
                <Typography variant="caption" sx={{ textAlign: "right" }}>
                  {isLoading ? t("common.loading") : ram.value || "—"}
                </Typography>
              </Stack>
              {ram.reclaimable && (
                <Typography
                  variant="caption"
                  color="text.secondary"
                  data-testid="sidebar-rcon-file-cache"
                  sx={{ display: "block", ml: 2.5, lineHeight: 1.4 }}
                >
                  {t("dashboard.resources.inactiveFileCache", {
                    used: ram.reclaimable,
                  })}
                </Typography>
              )}
            </ButtonBase>
          </Tooltip>
          {percentageRow(percentages[1])}
        </Stack>
      </ListItem>
      {detailsOpen && (
        <SystemUsageDialog onClose={() => setDetailsOpen(false)} />
      )}
    </>
  );
};

export default SystemUsage;
