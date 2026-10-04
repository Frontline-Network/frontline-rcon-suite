import { useState } from "react";
import {
  Box,
  Button,
  Collapse,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import PersonSearchIcon from "@mui/icons-material/PersonSearch";
import dayjs from "dayjs";
import utcPlugin from "dayjs/plugin/utc";
import { useTranslation } from "react-i18next";
import { useClipboard } from "@/hooks/useClipboard";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { formatTechnicalData } from "./audit-utils";

dayjs.extend(utcPlugin);

const statusMeta = {
  success: { color: "success.main", icon: CheckCircleOutlineIcon },
  failed: { color: "error.main", icon: ErrorOutlineIcon },
  partial: { color: "warning.main", icon: ErrorOutlineIcon },
  unknown: { color: "text.secondary", icon: HelpOutlineIcon },
};

const labelForArgument = (key, t) => {
  const known = {
    player_name: t("records.auditLogs.argumentLabels.playerName"),
    player_id: t("records.auditLogs.argumentLabels.playerId"),
    message: t("records.auditLogs.argumentLabels.message"),
    reason: t("records.auditLogs.argumentLabels.reason"),
    duration: t("records.auditLogs.argumentLabels.duration"),
    map_name: t("records.auditLogs.argumentLabels.map"),
    map: t("records.auditLogs.argumentLabels.map"),
    squad_name: t("records.auditLogs.argumentLabels.squad"),
    team_name: t("records.auditLogs.argumentLabels.team"),
    service_name: t("records.auditLogs.argumentLabels.service"),
    server_number: t("records.auditLogs.argumentLabels.server"),
  };
  return known[key] || key.replaceAll("_", " ");
};

const displayValue = (value, t) => {
  if (value === null || value === undefined || value === "") return "–";
  if (typeof value === "boolean") {
    return value
      ? t("records.auditLogs.boolean.yes")
      : t("records.auditLogs.boolean.no");
  }
  if (typeof value === "object") return JSON.stringify(value);
  return String(value);
};

function CopyAction({ value, label }) {
  const { isClipboardAvailable, isCopied, copyToClipboard } = useClipboard();
  const { t } = useTranslation();
  if (!isClipboardAvailable || !value) return null;

  return (
    <Tooltip title={isCopied ? t("common.copied") : label || t("common.copy")}>
      <IconButton
        size="small"
        onClick={() => copyToClipboard(String(value))}
        aria-label={label || t("common.copy")}
        sx={{ borderRadius: 0 }}
      >
        {isCopied ? (
          <DoneAllIcon color="success" sx={{ fontSize: 15 }} />
        ) : (
          <ContentCopyIcon sx={{ fontSize: 15 }} />
        )}
      </IconButton>
    </Tooltip>
  );
}

function DetailRow({ label, children, copyValue }) {
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(92px, .7fr) minmax(0, 1.3fr)",
        gap: 1,
        alignItems: "center",
        minHeight: 29,
      }}
    >
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
      >
        {label}
      </Typography>
      <Stack direction="row" alignItems="center" minWidth={0}>
        <Typography
          variant="body2"
          component="div"
          sx={{ minWidth: 0, overflowWrap: "anywhere", flexGrow: 1 }}
        >
          {children}
        </Typography>
        {copyValue && <CopyAction value={copyValue} />}
      </Stack>
    </Box>
  );
}

export default function AuditLogInspector({
  entry,
  serverLabel,
  onClose,
  defaultRawOpen = false,
}) {
  const { t } = useTranslation();
  const [rawOpen, setRawOpen] = useState(defaultRawOpen);
  const { openWithId } = usePlayerSidebar();

  if (!entry) {
    return (
      <Box data-theme-surface="panel"
        sx={{
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          p: 2,
          minHeight: 160,
        }}
      >
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ fontWeight: 800 }}
        >
          {t("records.auditLogs.details")}
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 1 }}>
          {t("records.auditLogs.selectRow")}
        </Typography>
      </Box>
    );
  }

  const meta = statusMeta[entry.status] || statusMeta.unknown;
  const StatusIcon = meta.icon;
  const argumentEntries = Object.entries(entry.arguments || {}).filter(
    ([, value]) => value !== "" && value !== null && value !== undefined
  );
  const rawData = formatTechnicalData({
    command: entry.command,
    arguments: entry.arguments,
    result: entry.result,
  });
  const localTime = dayjs(entry.creation_time);

  return (
    <Box data-theme-surface="panel"
      className="wardogs-panel"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        minWidth: 0,
        "& .MuiButton-root, & .MuiIconButton-root": { borderRadius: 0 },
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        sx={{
          minHeight: 44,
          px: 1.5,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ fontWeight: 800, letterSpacing: "0.08em" }}
        >
          {t("records.auditLogs.details")}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        {onClose && (
          <Button size="small" color="inherit" onClick={onClose}>
            {t("common.close")}
          </Button>
        )}
      </Stack>

      <Box sx={{ p: 1.5 }}>
        <Stack spacing={0.75} sx={{ pb: 1.25 }}>
          <Stack direction="row" justifyContent="space-between" gap={1}>
            <Typography variant="h6" sx={{ lineHeight: 1.15 }}>
              {entry.actionLabel}
            </Typography>
            <Stack
              direction="row"
              alignItems="center"
              gap={0.5}
              sx={{ color: meta.color, flexShrink: 0 }}
            >
              <StatusIcon sx={{ fontSize: 17 }} />
              <Typography variant="caption" sx={{ fontWeight: 700 }}>
                {t(`records.auditLogs.statuses.${entry.status}`)}
              </Typography>
            </Stack>
          </Stack>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontFamily: "monospace" }}
          >
            {entry.command || t("records.auditLogs.unknownAction")}
          </Typography>
        </Stack>

        <Divider />
        <Stack spacing={0.25} sx={{ py: 1.25 }}>
          <DetailRow label={t("records.auditLogs.userColumn")}>
            {entry.username || t("records.auditLogs.unknownUser")}
          </DetailRow>
          <DetailRow label={t("records.auditLogs.target")}>
            {entry.target.label}
          </DetailRow>
          {entry.target.id && (
            <DetailRow
              label={t("records.auditLogs.playerId")}
              copyValue={entry.target.id}
            >
              {entry.target.id}
            </DetailRow>
          )}
          <DetailRow label={t("records.auditLogs.server")}>
            {serverLabel || t("records.auditLogs.serverUnknown")}
          </DetailRow>
          <DetailRow label={t("records.auditLogs.time")}>
            {localTime.isValid() ? localTime.format("L · LTS") : "–"}
          </DetailRow>
          <DetailRow label={t("records.auditLogs.utcTime")}>
            {localTime.isValid() ? localTime.utc().format("L · LTS") : "–"}
          </DetailRow>
          {entry.id && (
            <DetailRow
              label={t("records.auditLogs.auditId")}
              copyValue={entry.id}
            >
              {entry.id}
            </DetailRow>
          )}
        </Stack>

        {entry.target.id && (
          <Button
            size="small"
            variant="outlined"
            startIcon={<PersonSearchIcon />}
            onClick={() => openWithId(entry.target.id)}
            sx={{ mb: 1.25 }}
          >
            {t("records.auditLogs.openProfile")}
          </Button>
        )}

        <Divider />
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ display: "block", pt: 1.25, fontWeight: 800 }}
        >
          {t("records.auditLogs.submittedValues")}
        </Typography>
        <Stack data-theme-surface="panel"
          divider={<Divider flexItem />}
          sx={{ mt: 0.25, border: "1px solid", borderColor: "divider" }}
        >
          {argumentEntries.length ? (
            argumentEntries.map(([key, value]) => (
              <Box key={key} sx={{ px: 1, py: 0.65 }}>
                <DetailRow label={labelForArgument(key, t)}>
                  {displayValue(value, t)}
                </DetailRow>
              </Box>
            ))
          ) : (
            <Typography color="text.secondary" variant="body2" sx={{ p: 1 }}>
              {t("records.auditLogs.noArguments")}
            </Typography>
          )}
        </Stack>

        <Typography
          variant="overline"
          color="primary.main"
          sx={{ display: "block", pt: 1.25, fontWeight: 800 }}
        >
          {t("records.auditLogs.result")}
        </Typography>
        <Stack direction="row" alignItems="center" gap={0.75} sx={{ py: 0.5 }}>
          <StatusIcon sx={{ color: meta.color, fontSize: 17 }} />
          <Typography variant="body2">
            {entry.status === "unknown"
              ? t("records.auditLogs.resultUnknown")
              : t(`records.auditLogs.resultMessages.${entry.status}`)}
          </Typography>
        </Stack>

        <Divider sx={{ my: 1 }} />
        <Button
          fullWidth
          color="inherit"
          onClick={() => setRawOpen((open) => !open)}
          endIcon={
            <KeyboardArrowDownIcon
              sx={{ transform: rawOpen ? "rotate(180deg)" : "none" }}
            />
          }
          aria-expanded={rawOpen}
          sx={{ justifyContent: "space-between", color: "text.secondary" }}
        >
          {t("records.auditLogs.rawData")}
        </Button>
        <Collapse in={rawOpen}>
          <Box data-theme-surface="panel"
            sx={{
              position: "relative",
              mt: 0.75,
              p: 1,
              pr: 4,
              bgcolor: "background.default",
              border: "1px solid",
              borderColor: "divider",
              overflow: "auto",
              maxHeight: 260,
            }}
          >
            <Box sx={{ position: "absolute", top: 3, right: 3 }}>
              <CopyAction
                value={rawData}
                label={t("records.auditLogs.copyRaw")}
              />
            </Box>
            <Typography
              component="pre"
              variant="caption"
              sx={{
                m: 0,
                fontFamily: "monospace",
                whiteSpace: "pre-wrap",
                overflowWrap: "anywhere",
              }}
            >
              {rawData}
            </Typography>
          </Box>
        </Collapse>
      </Box>
    </Box>
  );
}
