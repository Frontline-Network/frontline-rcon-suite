import { Fragment, useEffect, useMemo, useState } from "react";
import {
  Avatar,
  Box,
  Button,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  IconButton,
  Link,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import BlockIcon from "@mui/icons-material/Block";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import EditOutlinedIcon from "@mui/icons-material/EditOutlined";
import ExpandLessIcon from "@mui/icons-material/ExpandLess";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import OpenInNewIcon from "@mui/icons-material/OpenInNew";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import ReportOutlinedIcon from "@mui/icons-material/ReportOutlined";
import TimerOffOutlinedIcon from "@mui/icons-material/TimerOffOutlined";
import { List } from "immutable";
import moment from "moment";
import "moment/locale/de";
import { useTranslation } from "react-i18next";
import makePlayerProfileUrl from "../../utils/makePlayerProfileUrl";
import BlacklistRecordCreateDialog from "./BlacklistRecordCreateDialog";
import { handle_http_errors, postData, showResponse } from "@/utils/fetchUtils";

const copyText = (text, fallbackMessage) => {
  if (!navigator.clipboard) {
    window.alert(fallbackMessage);
    return;
  }
  navigator.clipboard
    .writeText(text)
    .catch(() => window.alert(fallbackMessage));
};

const DetailItem = ({ label, children, wide = false }) => (
  <Box sx={{ minWidth: 0, gridColumn: wide ? "1 / -1" : "auto" }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
        display: "block",
        mb: 0.35,
        textTransform: "uppercase",
        letterSpacing: "0.06em",
      }}
    >
      {label}
    </Typography>
    <Box sx={{ color: "text.primary", overflowWrap: "anywhere" }}>
      {children}
    </Box>
  </Box>
);

const ActionIcon = ({ title, children, ...props }) => (
  <Tooltip title={title} arrow>
    <IconButton
      size="small"
      {...props}
      sx={{ borderRadius: 0, color: "text.secondary", ...props.sx }}
    >
      {children}
    </IconButton>
  </Tooltip>
);

const getIntlLocale = (language) =>
  language?.toLowerCase().startsWith("de") ? "de-DE" : "en-US";

const formatRelativeDate = (date, language) => {
  const diff = date.valueOf() - Date.now();
  const absolute = Math.abs(diff);
  const minute = 60 * 1000;
  const hour = 60 * minute;
  const day = 24 * hour;
  const month = 30 * day;
  const year = 365 * day;

  let unit = "minute";
  let divisor = minute;
  if (absolute >= year) {
    unit = "year";
    divisor = year;
  } else if (absolute >= month) {
    unit = "month";
    divisor = month;
  } else if (absolute >= day) {
    unit = "day";
    divisor = day;
  } else if (absolute >= hour) {
    unit = "hour";
    divisor = hour;
  }

  return new Intl.RelativeTimeFormat(getIntlLocale(language), {
    numeric: "auto",
  }).format(Math.round(diff / divisor), unit);
};

const formatDateTime = (date, language) =>
  new Intl.DateTimeFormat(getIntlLocale(language), {
    dateStyle: "medium",
    timeStyle: "short",
  }).format(date.toDate());

const getRecordView = (record, t, language) => {
  const momentLocale = language?.toLowerCase().startsWith("de") ? "de" : "en";
  const player = record.get("player");
  const names = player.get("names", List());
  const name = names.getIn([0, "name"], t("common.unknown"));
  const playerId = player.get("player_id");
  const blacklist = record.get("blacklist");
  const expiresAt = record.get("expires_at")
    ? moment(record.get("expires_at")).locale(momentLocale)
    : null;
  const createdAt = moment(record.get("created_at")).locale(momentLocale);
  const isExpired =
    !record.get("is_active") || Boolean(expiresAt?.isBefore(moment()));
  const avatar = player.getIn(["steaminfo", "profile", "avatar"]);

  let statusLabel = t("records.blacklists.activePermanent");
  if (isExpired) {
    statusLabel = expiresAt
      ? t("records.blacklists.expiredSince", {
          duration: formatRelativeDate(expiresAt, language),
        })
      : t("records.blacklists.statusOptions.expired");
  } else if (expiresAt) {
    statusLabel = t("records.blacklists.activeUntil", {
      duration: formatRelativeDate(expiresAt, language),
    });
  }

  const servers = blacklist?.get("servers");
  const serverLabel =
    servers === null || servers === undefined
      ? t("records.blacklists.allServers")
      : servers.size === 0
      ? t("records.blacklists.noServers")
      : servers
          .map((server) =>
            t("records.blacklists.serverNumber", { number: server })
          )
          .join(", ");

  return {
    id: record.get("id"),
    player,
    names,
    name,
    playerId,
    avatar,
    blacklist,
    blacklistName: blacklist?.get("name") || t("common.unknown"),
    sync: blacklist?.get("sync"),
    serverLabel,
    reason: String(
      record.get("formatted_reason") || record.get("reason") || ""
    ),
    createdAt,
    createdAtFormatted: formatDateTime(createdAt, language),
    createdRelative: formatRelativeDate(createdAt, language),
    expiresAt,
    expiresAtFormatted: expiresAt ? formatDateTime(expiresAt, language) : null,
    isExpired,
    isPermanent: !expiresAt,
    statusLabel,
    admin: record.get("admin_name") || t("common.unknown"),
  };
};

const groupRecords = (records, t, language) => {
  const groups = [
    { key: "today", label: t("records.blacklists.groups.today"), records: [] },
    {
      key: "recent",
      label: t("records.blacklists.groups.recent"),
      records: [],
    },
    { key: "older", label: t("records.blacklists.groups.older"), records: [] },
  ];
  const sevenDaysAgo = moment().subtract(7, "days").startOf("day");

  records.forEach((record) => {
    const view = getRecordView(record, t, language);
    if (view.createdAt.isSame(moment(), "day"))
      groups[0].records.push({ record, view });
    else if (view.createdAt.isAfter(sevenDaysAgo))
      groups[1].records.push({ record, view });
    else groups[2].records.push({ record, view });
  });

  return groups.filter((group) => group.records.length);
};

const JournalRow = ({ view, expanded, onToggle, onCopyId, onOpenProfile }) => {
  const { t } = useTranslation();
  const statusIcon = view.isExpired ? (
    <BlockIcon fontSize="inherit" />
  ) : view.isPermanent ? (
    <CheckCircleOutlineIcon fontSize="inherit" />
  ) : (
    <AccessTimeIcon fontSize="inherit" />
  );

  return (
    <Box
      data-blacklist-row
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "minmax(0, 1fr) auto",
          xl: "minmax(190px, 1.1fr) minmax(145px, .75fr) minmax(200px, 1.35fr) minmax(138px, .7fr) minmax(152px, .8fr) auto",
        },
        alignItems: "center",
        minHeight: 56,
        borderBottom: "1px solid",
        borderColor: "divider",
        bgcolor: expanded ? "action.selected" : "background.paper",
        opacity: view.isExpired ? 0.72 : 1,
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Box
        role="button"
        tabIndex={0}
        aria-expanded={expanded}
        onClick={onToggle}
        onKeyDown={(event) => {
          if (event.key === "Enter" || event.key === " ") {
            event.preventDefault();
            onToggle();
          }
        }}
        sx={{
          display: "contents",
          cursor: "pointer",
          "&:focus-visible > *": {
            outline: "1px solid",
            outlineColor: "primary.main",
            outlineOffset: -1,
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          sx={{ minWidth: 0, px: 1.25, py: 0.75 }}
        >
          <Box
            aria-hidden
            sx={{
              width: 8,
              height: 8,
              flex: "0 0 auto",
              bgcolor: view.isExpired ? "text.disabled" : "success.main",
            }}
          />
          <Avatar
            src={view.avatar}
            variant="square"
            sx={{ width: 34, height: 34, fontSize: 15 }}
          >
            {view.name.slice(0, 1).toUpperCase()}
          </Avatar>
          <Box sx={{ minWidth: 0 }}>
            <Typography noWrap sx={{ fontWeight: 600 }}>
              {view.name}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              noWrap
              sx={{ fontVariantNumeric: "tabular-nums" }}
            >
              {view.playerId}
            </Typography>
          </Box>
        </Stack>
        <Box sx={{ display: { xs: "none", xl: "block" }, minWidth: 0, px: 1 }}>
          <Typography noWrap>{view.blacklistName}</Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {view.serverLabel}
          </Typography>
        </Box>
        <Typography
          color="text.secondary"
          sx={{ display: { xs: "none", xl: "block" }, minWidth: 0, px: 1 }}
          noWrap
        >
          {view.reason}
        </Typography>
        <Box sx={{ display: { xs: "none", xl: "block" }, minWidth: 0, px: 1 }}>
          <Typography noWrap>{view.admin}</Typography>
          <Typography variant="caption" color="text.secondary" noWrap>
            {view.createdRelative}
          </Typography>
        </Box>
        <Stack
          direction="row"
          alignItems="center"
          gap={0.75}
          sx={{
            px: { xs: 0.5, xl: 1 },
            color: view.isExpired ? "text.secondary" : "primary.main",
            whiteSpace: "nowrap",
          }}
        >
          <Box component="span" sx={{ display: "inline-flex", fontSize: 17 }}>
            {statusIcon}
          </Box>
          <Typography
            variant="caption"
            sx={{ color: "inherit", display: { xs: "none", sm: "block" } }}
          >
            {view.statusLabel}
          </Typography>
        </Stack>
      </Box>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="flex-end"
        sx={{ pr: 0.5 }}
      >
        <ActionIcon
          title={t("records.blacklists.copyPlayerId")}
          onClick={onCopyId}
        >
          <ContentCopyIcon fontSize="small" />
        </ActionIcon>
        <ActionIcon
          title={t("records.blacklists.openPlayerProfile")}
          onClick={onOpenProfile}
        >
          <PersonOutlineIcon fontSize="small" />
        </ActionIcon>
        <ActionIcon
          title={expanded ? t("common.collapse") : t("common.expand")}
          onClick={onToggle}
        >
          {expanded ? (
            <ExpandLessIcon fontSize="small" />
          ) : (
            <ExpandMoreIcon fontSize="small" />
          )}
        </ActionIcon>
      </Stack>
    </Box>
  );
};

const CaseFile = ({ view, onEdit, onExpire, onDelete }) => {
  const { t } = useTranslation();
  const aliases = view.names.map((name) => name.get("name")).join(", ");
  const profileUrl = makePlayerProfileUrl(view.playerId, view.name);
  const report = `${t("records.blacklists.reportName")}: ${view.name}\n${t(
    "records.blacklists.playerId"
  )}: ${view.playerId}\nSteam URL: ${profileUrl}\n${t(
    "records.blacklists.issueType"
  )}:\n${t("records.blacklists.description")}:\n${t(
    "records.blacklists.evidence"
  )}:`;

  return (
    <Box
      sx={{
        borderBottom: "1px solid",
        borderLeft: "2px solid",
        borderColor: "primary.main",
        bgcolor: "rgba(118, 126, 113, 0.08)",
        p: { xs: 1.25, md: 1.5 },
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "minmax(0, 1.25fr) minmax(0, .75fr) auto",
          },
          gap: { xs: 2, xl: 3 },
          alignItems: "start",
        }}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
            gap: 1.5,
          }}
        >
          <DetailItem label={t("records.blacklists.aliases")}>
            {aliases || t("common.unknown")}
          </DetailItem>
          <DetailItem label={t("records.blacklists.createdBy")}>
            {view.admin}
          </DetailItem>
          <DetailItem label={t("records.blacklists.fullReason")} wide>
            <Typography>{view.reason}</Typography>
          </DetailItem>
          <DetailItem label={t("records.blacklists.affectedServers")}>
            {view.serverLabel}
          </DetailItem>
          <DetailItem label={t("records.blacklists.createdAt")}>
            {view.createdAtFormatted}
          </DetailItem>
          <DetailItem label={t("records.blacklists.synchronization")}>
            {t(
              `records.blacklists.syncMethods.${view.sync}`,
              view.sync || t("common.unknown")
            )}
          </DetailItem>
          <DetailItem label={t("records.blacklists.expirationDate")}>
            {view.expiresAt
              ? view.expiresAtFormatted
              : t("records.blacklists.permanent")}
          </DetailItem>
        </Box>

        <Stack gap={1}>
          <DetailItem label={t("records.blacklists.entryId")}>
            #{view.id}
          </DetailItem>
          <Button
            variant="outlined"
            color="inherit"
            startIcon={<ContentCopyIcon />}
            onClick={() =>
              copyText(view.playerId, t("records.blacklists.clipboardHttps"))
            }
            sx={{ justifyContent: "flex-start", borderRadius: 0 }}
          >
            {t("records.blacklists.copyPlayerId")}
          </Button>
          <Button
            component={Link}
            href={profileUrl}
            target="_blank"
            rel="noreferrer"
            variant="outlined"
            color="inherit"
            startIcon={<OpenInNewIcon />}
            sx={{ justifyContent: "flex-start", borderRadius: 0 }}
          >
            {t("records.blacklists.openSteamProfile")}
          </Button>
          <Button
            variant="outlined"
            color="inherit"
            startIcon={<ReportOutlinedIcon />}
            onClick={() =>
              copyText(report, t("records.blacklists.clipboardHttps"))
            }
            sx={{ justifyContent: "flex-start", borderRadius: 0 }}
          >
            {t("records.blacklists.copyReport")}
          </Button>
        </Stack>

        <Stack gap={0.75} sx={{ minWidth: { xl: 190 } }}>
          <Button
            variant="contained"
            startIcon={<EditOutlinedIcon />}
            onClick={onEdit}
            sx={{ borderRadius: 0 }}
          >
            {t("common.edit")}
          </Button>
          <Button
            variant="contained"
            startIcon={<TimerOffOutlinedIcon />}
            onClick={onExpire}
            disabled={view.isExpired}
            sx={{ borderRadius: 0 }}
          >
            {t("records.blacklists.endBan")}
          </Button>
          <Button
            variant="outlined"
            color="error"
            startIcon={<DeleteOutlineIcon />}
            onClick={onDelete}
            sx={{ mt: 1, borderRadius: 0 }}
          >
            {t("common.delete")}
          </Button>
        </Stack>
      </Box>
    </Box>
  );
};

const BlacklistRecordGrid = ({ blacklists, records, onRefresh }) => {
  const { t, i18n } = useTranslation();
  const [expandedId, setExpandedId] = useState(null);
  const [editDialogOpen, setEditDialogOpen] = useState(false);
  const [editDialogInitialValues, setEditDialogInitialValues] = useState();
  const [confirmation, setConfirmation] = useState(null);
  const groups = useMemo(
    () => groupRecords(records, t, i18n.resolvedLanguage || "de"),
    [records, t, i18n.resolvedLanguage]
  );

  useEffect(() => {
    if (!records.size) {
      setExpandedId(null);
      return;
    }
    if (!records.some((record) => record.get("id") === expandedId)) {
      setExpandedId(records.getIn([0, "id"]));
    }
  }, [expandedId, records]);

  const editRecord = (record) => {
    setEditDialogInitialValues({
      recordId: record.get("id"),
      blacklistId: record.getIn(["blacklist", "id"]),
      playerId: record.getIn(["player", "player_id"]),
      expiresAt: record.get("expires_at"),
      reason: record.get("reason"),
    });
    setEditDialogOpen(true);
  };

  const submitEdit = (data) => {
    const recordId = editDialogInitialValues.recordId;
    postData(`${process.env.REACT_APP_API_URL}edit_blacklist_record`, {
      record_id: recordId,
      blacklist_id: data.blacklistId,
      player_id: data.playerId,
      expires_at: data.expiresAt,
      reason: data.reason,
    })
      .then((response) =>
        showResponse(response, `Record ${recordId} was edited`, true)
      )
      .then((result) => result && !result.failed && onRefresh())
      .catch(handle_http_errors);
  };

  const runConfirmation = () => {
    const { type, record } = confirmation;
    const recordId = record.get("id");
    const endpoint =
      type === "delete" ? "delete_blacklist_record" : "edit_blacklist_record";
    const payload =
      type === "delete"
        ? { record_id: recordId }
        : { record_id: recordId, expires_at: moment().utc() };

    setConfirmation(null);
    postData(`${process.env.REACT_APP_API_URL}${endpoint}`, payload)
      .then((response) =>
        showResponse(response, `Record ${recordId} was edited`, true)
      )
      .then((result) => result && !result.failed && onRefresh())
      .catch(handle_http_errors);
  };

  if (!records.size) {
    return (
      <Box data-theme-surface="panel"
        sx={{
          border: "1px solid",
          borderColor: "divider",
          p: 4,
          textAlign: "center",
          bgcolor: "background.paper",
        }}
      >
        <Typography color="text.secondary">
          {t("records.blacklists.noRecords")}
        </Typography>
      </Box>
    );
  }

  return (
    <Fragment>
      <Stack gap={1.25}>
        {groups.map((group) => (
          <Box key={group.key}>
            <Typography
              variant="caption"
              color="primary.main"
              sx={{
                display: "block",
                px: 1.25,
                pb: 0.65,
                textTransform: "uppercase",
                letterSpacing: "0.09em",
                fontWeight: 700,
              }}
            >
              {group.label}
            </Typography>
            <Box data-theme-surface="group"
              sx={{
                border: "1px solid",
                borderColor: "divider",
                borderBottom: 0,
              }}
            >
              {group.records.map(({ record, view }) => {
                const expanded = expandedId === view.id;
                const profileUrl = makePlayerProfileUrl(
                  view.playerId,
                  view.name
                );
                return (
                  <Fragment key={view.id}>
                    <JournalRow
                      view={view}
                      expanded={expanded}
                      onToggle={() => setExpandedId(expanded ? null : view.id)}
                      onCopyId={(event) => {
                        event.stopPropagation();
                        copyText(
                          view.playerId,
                          t("records.blacklists.clipboardHttps")
                        );
                      }}
                      onOpenProfile={(event) => {
                        event.stopPropagation();
                        window.open(
                          profileUrl,
                          "_blank",
                          "noopener,noreferrer"
                        );
                      }}
                    />
                    <Collapse in={expanded} timeout="auto" unmountOnExit>
                      <CaseFile
                        view={view}
                        onEdit={() => editRecord(record)}
                        onExpire={() =>
                          setConfirmation({ type: "expire", record, view })
                        }
                        onDelete={() =>
                          setConfirmation({ type: "delete", record, view })
                        }
                      />
                    </Collapse>
                  </Fragment>
                );
              })}
            </Box>
          </Box>
        ))}
      </Stack>

      <BlacklistRecordCreateDialog
        open={editDialogOpen}
        setOpen={setEditDialogOpen}
        blacklists={blacklists}
        initialValues={editDialogInitialValues}
        onSubmit={submitEdit}
        titleText={t("records.blacklists.editRecord")}
        submitText={t("common.save")}
        disablePlayerId
      />

      <Dialog
        open={Boolean(confirmation)}
        onClose={() => setConfirmation(null)}
        PaperProps={{
          sx: { borderRadius: 0, border: "1px solid", borderColor: "divider" },
        }}
      >
        <DialogTitle>
          {confirmation?.type === "delete"
            ? t("records.blacklists.confirmDeleteTitle")
            : t("records.blacklists.confirmExpireTitle")}
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {confirmation?.type === "delete"
              ? t("records.blacklists.confirmDeleteDescription", {
                  name: confirmation?.view?.name,
                })
              : t("records.blacklists.confirmExpireDescription", {
                  name: confirmation?.view?.name,
                })}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setConfirmation(null)}>
            {t("common.cancel")}
          </Button>
          <Button
            onClick={runConfirmation}
            color={confirmation?.type === "delete" ? "error" : "primary"}
            variant="contained"
            startIcon={
              confirmation?.type === "delete" ? (
                <DeleteOutlineIcon />
              ) : (
                <TimerOffOutlinedIcon />
              )
            }
          >
            {confirmation?.type === "delete"
              ? t("common.delete")
              : t("records.blacklists.endBan")}
          </Button>
        </DialogActions>
      </Dialog>
    </Fragment>
  );
};

export default BlacklistRecordGrid;
