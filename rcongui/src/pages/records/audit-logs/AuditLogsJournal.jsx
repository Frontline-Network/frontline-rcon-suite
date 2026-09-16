import { Box, ButtonBase, Stack, Typography } from "@mui/material";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import AdminPanelSettingsOutlinedIcon from "@mui/icons-material/AdminPanelSettingsOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import SettingsApplicationsOutlinedIcon from "@mui/icons-material/SettingsApplicationsOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { groupAuditEntriesByDate } from "./audit-utils";

const categoryIcons = {
  moderation: GavelOutlinedIcon,
  maps: MapOutlinedIcon,
  access: AdminPanelSettingsOutlinedIcon,
  settings: TuneOutlinedIcon,
  system: SettingsApplicationsOutlinedIcon,
};

const statusMeta = {
  success: { color: "success.main", icon: CheckCircleOutlineIcon },
  failed: { color: "error.main", icon: ErrorOutlineIcon },
  partial: { color: "warning.main", icon: ErrorOutlineIcon },
  unknown: { color: "text.secondary", icon: HelpOutlineIcon },
};

const ellipsisSx = {
  minWidth: 0,
  overflow: "hidden",
  textOverflow: "ellipsis",
  whiteSpace: "nowrap",
};

const desktopGrid = {
  display: { xs: "none", md: "grid" },
  gridTemplateColumns:
    "100px minmax(230px, 1.55fr) minmax(165px, 1fr) minmax(125px, .8fr) 118px 30px",
  gap: 1,
  alignItems: "center",
};

const formatGroupDate = (value, t) => {
  if (value === "unknown") return t("records.auditLogs.unknownDate");
  const date = dayjs(value);
  const prefix = date.isSame(dayjs(), "day")
    ? t("records.auditLogs.today")
    : date.isSame(dayjs().subtract(1, "day"), "day")
    ? t("records.auditLogs.yesterday")
    : null;
  const formatted = date.format("LL");
  return prefix ? `${prefix} · ${formatted}` : formatted;
};

function AuditRow({ entry, selected, onSelect }) {
  const { t } = useTranslation();
  const CategoryIcon =
    categoryIcons[entry.category] || SettingsApplicationsOutlinedIcon;
  const status = statusMeta[entry.status] || statusMeta.unknown;
  const StatusIcon = status.icon;
  const time = dayjs(entry.creation_time);
  const idPreview = entry.target.id
    ? entry.target.id.length > 12
      ? `${entry.target.id.slice(0, 7)}…${entry.target.id.slice(-4)}`
      : entry.target.id
    : null;

  return (
    <ButtonBase
      component="button"
      onClick={() => onSelect(entry)}
      aria-selected={selected}
      aria-label={`${entry.actionLabel}, ${entry.target.label}, ${t(
        `records.auditLogs.statuses.${entry.status}`
      )}`}
      data-testid="audit-log-row"
      sx={{
        width: "100%",
        minWidth: 0,
        minHeight: { xs: 64, md: 50 },
        px: { xs: 1, md: 1.25 },
        py: { xs: 0.65, md: 0.4 },
        textAlign: "left",
        borderRadius: 0,
        borderLeft: "2px solid",
        borderLeftColor: selected ? "primary.main" : "transparent",
        borderBottom: "1px solid",
        borderBottomColor: "divider",
        bgcolor: selected ? "action.selected" : "transparent",
        color: "text.primary",
        "&:hover": { bgcolor: selected ? "action.selected" : "action.hover" },
        "&:focus-visible": {
          outline: "2px solid",
          outlineColor: "primary.main",
          outlineOffset: -2,
        },
      }}
    >
      <Box sx={{ ...desktopGrid, width: "100%" }}>
        <Typography
          variant="caption"
          sx={{ fontVariantNumeric: "tabular-nums" }}
        >
          {time.isValid() ? time.format("HH:mm:ss") : "–"}
        </Typography>

        <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
          <Box
            sx={{
              width: 28,
              height: 28,
              display: "grid",
              placeItems: "center",
              flexShrink: 0,
              border: "1px solid",
              borderColor: "divider",
              color: selected ? "primary.main" : "text.secondary",
            }}
          >
            <CategoryIcon sx={{ fontSize: 16 }} />
          </Box>
          <Box minWidth={0}>
            <Typography variant="body2" sx={{ ...ellipsisSx, fontWeight: 600 }}>
              {entry.actionLabel}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ ...ellipsisSx, display: "block", fontFamily: "monospace" }}
            >
              {entry.command || t("records.auditLogs.unknownAction")}
            </Typography>
          </Box>
        </Stack>

        <Box minWidth={0}>
          <Typography variant="body2" sx={ellipsisSx}>
            {entry.target.label}
          </Typography>
          {idPreview && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={ellipsisSx}
            >
              {idPreview}
            </Typography>
          )}
        </Box>

        <Typography variant="body2" sx={ellipsisSx}>
          {entry.username || t("records.auditLogs.unknownUser")}
        </Typography>

        <Stack
          direction="row"
          alignItems="center"
          gap={0.55}
          sx={{ color: status.color }}
        >
          <StatusIcon sx={{ fontSize: 16 }} />
          <Typography variant="caption" sx={{ fontWeight: 700 }}>
            {t(`records.auditLogs.statuses.${entry.status}`)}
          </Typography>
        </Stack>
        <ChevronRightIcon
          sx={{
            fontSize: 18,
            color: selected ? "primary.main" : "text.secondary",
            transform: selected ? "rotate(90deg)" : "none",
          }}
        />
      </Box>

      <Box
        sx={{
          display: { xs: "grid", md: "none" },
          width: "100%",
          gridTemplateColumns: "52px minmax(0, 1fr) 24px",
          gap: 1,
          alignItems: "center",
        }}
      >
        <Typography
          variant="caption"
          sx={{ fontVariantNumeric: "tabular-nums" }}
        >
          {time.isValid() ? time.format("HH:mm") : "–"}
        </Typography>
        <Box minWidth={0}>
          <Stack direction="row" alignItems="center" gap={0.7} minWidth={0}>
            <CategoryIcon
              sx={{ fontSize: 15, color: "text.secondary", flexShrink: 0 }}
            />
            <Typography variant="body2" sx={{ ...ellipsisSx, fontWeight: 600 }}>
              {entry.actionLabel}
            </Typography>
          </Stack>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ ...ellipsisSx, display: "block" }}
          >
            {entry.target.label} ·{" "}
            {entry.username || t("records.auditLogs.unknownUser")}
          </Typography>
        </Box>
        <StatusIcon
          aria-label={t(`records.auditLogs.statuses.${entry.status}`)}
          sx={{ fontSize: 17, color: status.color }}
        />
      </Box>
    </ButtonBase>
  );
}

export default function AuditLogsJournal({ entries, selectedKey, onSelect }) {
  const { t } = useTranslation();
  const groups = groupAuditEntriesByDate(entries);

  if (!entries.length) {
    return (
      <Box
        sx={{
          display: "grid",
          placeItems: "center",
          minHeight: 280,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          p: 3,
          textAlign: "center",
        }}
      >
        <Box>
          <Typography variant="h6">
            {t("records.auditLogs.emptyTitle")}
          </Typography>
          <Typography color="text.secondary" sx={{ mt: 0.5 }}>
            {t("records.auditLogs.emptyDescription")}
          </Typography>
        </Box>
      </Box>
    );
  }

  return (
    <Box
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        minWidth: 0,
      }}
    >
      <Box
        sx={{
          ...desktopGrid,
          minHeight: 40,
          px: 1.25,
          borderBottom: "1px solid",
          borderColor: "divider",
          color: "text.secondary",
        }}
      >
        <Typography variant="overline">
          {t("records.auditLogs.time")}
        </Typography>
        <Typography variant="overline">
          {t("records.auditLogs.actionColumn")}
        </Typography>
        <Typography variant="overline">
          {t("records.auditLogs.target")}
        </Typography>
        <Typography variant="overline">
          {t("records.auditLogs.userColumn")}
        </Typography>
        <Typography variant="overline">
          {t("records.auditLogs.result")}
        </Typography>
        <span />
      </Box>

      {groups.map((group) => (
        <Box key={group.date}>
          <Stack
            direction="row"
            alignItems="center"
            sx={{
              minHeight: 35,
              px: 1.25,
              bgcolor: "background.default",
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="overline" sx={{ fontWeight: 800 }}>
              {formatGroupDate(group.date, t)}
            </Typography>
            <Box sx={{ flexGrow: 1 }} />
            <Typography variant="caption" color="text.secondary">
              {t("records.auditLogs.entryCount", { count: group.items.length })}
            </Typography>
          </Stack>
          {group.items.map((entry) => (
            <AuditRow
              key={entry.key}
              entry={entry}
              selected={selectedKey === entry.key}
              onSelect={onSelect}
            />
          ))}
        </Box>
      ))}
    </Box>
  );
}
