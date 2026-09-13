import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
  useMediaQuery,
} from "@mui/material";
import ReportProblemRoundedIcon from "@mui/icons-material/ReportProblemRounded";
import PersonRoundedIcon from "@mui/icons-material/PersonRounded";
import SportsEsportsRoundedIcon from "@mui/icons-material/SportsEsportsRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import DoneRoundedIcon from "@mui/icons-material/DoneRounded";
import BlockRoundedIcon from "@mui/icons-material/BlockRounded";
import BackHandRoundedIcon from "@mui/icons-material/BackHandRounded";
import DnsRoundedIcon from "@mui/icons-material/DnsRounded";
import PersonOffRoundedIcon from "@mui/icons-material/PersonOffRounded";
import ScheduleRoundedIcon from "@mui/icons-material/ScheduleRounded";
import SyncRoundedIcon from "@mui/icons-material/SyncRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import FiberManualRecordRoundedIcon from "@mui/icons-material/FiberManualRecordRounded";
import { useTheme } from "@mui/material/styles";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useSearchParams } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import PageHeader from "@/components/shared/PageHeader";
import PageState from "@/components/shared/PageState";
import VotePanel from "@/pages/settings/leadership-votes/VotePanel";
import { useAuth } from "@/hooks/useAuth";
import { canUse } from "@/pages/views/live-map/api";

const STATUS_TONES = {
  new: "warning",
  claimed: "info",
  resolved: "success",
  dismissed: "default",
};

const FILTERS = ["new", "claimed", "done", "dismissed", "all"];
const ACTIVE_STATUSES = new Set(["new", "claimed"]);

const getSubject = (incident) =>
  incident?.primary_subject ?? incident?.subjects?.[0];

const getStatusBorderColor = (theme, status) => {
  if (status === "new") return theme.palette.warning.main;
  if (status === "claimed") return theme.palette.info.main;
  if (status === "resolved") return theme.palette.success.main;
  return theme.palette.divider;
};

const formatTime = (value, locale) => {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "–";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(timestamp);
};

const formatAge = (value, locale) => {
  const timestamp = Date.parse(value);
  if (!Number.isFinite(timestamp)) return "–";
  const delta = timestamp - Date.now();
  const absolute = Math.abs(delta);
  const units =
    absolute >= 86400000
      ? ["day", 86400000]
      : absolute >= 3600000
      ? ["hour", 3600000]
      : ["minute", 60000];
  return new Intl.RelativeTimeFormat(locale, { numeric: "auto" }).format(
    Math.round(delta / units[1]),
    units[0]
  );
};

const statusForFilter = (filter) => {
  if (filter === "done") return "resolved";
  if (filter === "all") return null;
  return filter;
};

const MetricCard = ({ icon: Icon, label, value }) => (
  <Box
    sx={{
      alignItems: "center",
      bgcolor: "background.paper",
      border: "1px solid",
      borderColor: "divider",
      display: "grid",
      gap: 1,
      gridTemplateColumns: "auto minmax(0, 1fr)",
      minHeight: 72,
      px: 1.5,
      py: 1.25,
    }}
  >
    <Icon color="primary" sx={{ fontSize: 22 }} />
    <Box sx={{ minWidth: 0 }}>
      <Typography color="text.secondary" variant="caption">
        {label}
      </Typography>
      <Typography sx={{ lineHeight: 1.1 }} variant="h6">
        {value}
      </Typography>
    </Box>
  </Box>
);

const IncidentCard = ({ incident, isSelected, onOpen }) => {
  const { t, i18n } = useTranslation();
  const subject = getSubject(incident);
  const target = subject?.name ?? incident.target_name;
  const reporter = incident.reporter_name || t("incidents.unknownReporter");

  return (
    <Box
      component="article"
      sx={(theme) => ({
        bgcolor: isSelected ? "action.selected" : "background.paper",
        border: "1px solid",
        borderColor: isSelected ? "primary.main" : "divider",
        borderLeft: `3px solid ${getStatusBorderColor(theme, incident.status)}`,
      })}
    >
      <Button
        aria-pressed={isSelected}
        color="inherit"
        onClick={() => onOpen(incident)}
        sx={{
          display: "block",
          minHeight: 128,
          p: 1.5,
          textAlign: "left",
          width: "100%",
        }}
      >
        <Stack spacing={1.1}>
          <Stack
            direction="row"
            alignItems="flex-start"
            justifyContent="space-between"
            gap={1}
          >
            <Box sx={{ minWidth: 0 }}>
              <Typography component="h2" variant="subtitle1" noWrap>
                {target || t("incidents.generalReport")}
              </Typography>
              <Typography color="text.secondary" variant="caption">
                {t("incidents.server", { number: incident.server_number })} ·{" "}
                {formatAge(incident.created_at, i18n.language)}
              </Typography>
            </Box>
            <Chip
              color={STATUS_TONES[incident.status] || "default"}
              label={t(`incidents.status.${incident.status}`)}
              size="small"
            />
          </Stack>
          <Typography
            variant="body2"
            sx={{
              display: "-webkit-box",
              overflow: "hidden",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: 2,
            }}
          >
            {incident.reason || incident.raw_message || t("incidents.noReason")}
          </Typography>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="space-between"
            gap={1}
          >
            <Stack
              direction="row"
              alignItems="center"
              spacing={0.75}
              color="text.secondary"
              sx={{ minWidth: 0 }}
            >
              <PersonRoundedIcon sx={{ fontSize: 16 }} />
              <Typography variant="caption" noWrap>
                {incident.assigned_to
                  ? t("incidents.assignedTo", { name: incident.assigned_to })
                  : reporter}
              </Typography>
            </Stack>
            <ChevronRightRoundedIcon
              color={isSelected ? "primary" : "disabled"}
            />
          </Stack>
        </Stack>
      </Button>
    </Box>
  );
};

const DetailField = ({ label, children }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography color="text.secondary" variant="caption">
      {label}
    </Typography>
    <Typography variant="body2">{children}</Typography>
  </Box>
);

const IncidentDetail = ({
  incident,
  dismissConfirmation,
  mutation,
  onDismissCancel,
  onDismissConfirm,
  onDismissRequest,
  onOperation,
}) => {
  const { t, i18n } = useTranslation();
  const dismissCancelRef = useRef(null);
  const { permissions } = useAuth();
  const subject = getSubject(incident);
  const target = subject?.name ?? incident?.target_name;

  useEffect(() => {
    if (!dismissConfirmation) return;
    window.requestAnimationFrame(() => dismissCancelRef.current?.focus());
  }, [dismissConfirmation]);

  if (!incident) {
    return (
      <Stack
        alignItems="center"
        justifyContent="center"
        spacing={1.5}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          minHeight: 360,
          p: 4,
          textAlign: "center",
        }}
      >
        <ReportProblemRoundedIcon color="disabled" sx={{ fontSize: 36 }} />
        <Typography component="h2" variant="h6">
          {t("incidents.detail.emptyTitle")}
        </Typography>
        <Typography color="text.secondary" variant="body2">
          {t("incidents.detail.emptyDescription")}
        </Typography>
      </Stack>
    );
  }

  const nextStep =
    incident.status === "new"
      ? t("incidents.nextStep.claim")
      : incident.status === "claimed"
      ? t("incidents.nextStep.resolve")
      : t("incidents.nextStep.review");

  return (
    <Box
      component="section"
      aria-labelledby="incident-detail-title"
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box sx={{ borderBottom: "1px solid", borderColor: "divider", p: 2 }}>
        <Stack direction="row" justifyContent="space-between" gap={2}>
          <Box sx={{ minWidth: 0 }}>
            <Typography color="primary.main" variant="overline">
              {t("incidents.detail.eyebrow")}
            </Typography>
            <Typography
              id="incident-detail-title"
              component="h2"
              variant="h5"
              noWrap
            >
              {target || t("incidents.generalReport")}
            </Typography>
          </Box>
          <Chip
            color={STATUS_TONES[incident.status] || "default"}
            label={t(`incidents.status.${incident.status}`)}
            size="small"
          />
        </Stack>
        <Stack
          direction="row"
          spacing={1}
          flexWrap="wrap"
          useFlexGap
          sx={{ mt: 1.5 }}
        >
          <Chip
            icon={<SportsEsportsRoundedIcon />}
            label={t("incidents.server", { number: incident.server_number })}
            size="small"
            variant="outlined"
          />
          <Chip
            icon={<ScheduleRoundedIcon />}
            label={formatAge(incident.created_at, i18n.language)}
            size="small"
            variant="outlined"
          />
          <Chip
            label={t(`incidents.sources.${incident.source || "unknown"}`)}
            size="small"
            variant="outlined"
          />
        </Stack>
      </Box>

      <Stack spacing={2} sx={{ p: 2 }}>
        {incident.leadership_vote && (
          <VotePanel
            vote={incident.leadership_vote}
            canCancel={canUse(permissions, "can_claim_admin_incidents")}
            pending={mutation.isPending}
            onCancel={() => onOperation("cancel_leadership_vote")}
          />
        )}
        <Box>
          <Typography color="text.secondary" variant="caption">
            {t("incidents.reason")}
          </Typography>
          <Typography
            id="incident-detail-description"
            variant="body1"
            sx={{ mt: 0.5 }}
          >
            {incident.reason || incident.raw_message || t("incidents.noReason")}
          </Typography>
        </Box>

        <Box
          sx={{
            bgcolor: "background.default",
            border: "1px solid",
            borderColor: "divider",
            display: "grid",
            gap: 2,
            gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" },
            p: 1.5,
          }}
        >
          <DetailField label={t("incidents.reporter")}>
            {incident.reporter_name || t("incidents.unknownReporter")}
          </DetailField>
          <DetailField label={t("incidents.assignee")}>
            {incident.assigned_to || t("incidents.unassigned")}
          </DetailField>
          <DetailField label={t("incidents.detail.received")}>
            {formatTime(incident.created_at, i18n.language)}
          </DetailField>
          <DetailField label={t("incidents.updated")}>
            {formatTime(incident.updated_at, i18n.language)}
          </DetailField>
        </Box>

        {incident.raw_message && incident.raw_message !== incident.reason ? (
          <Box>
            <Typography color="text.secondary" variant="caption">
              {t("incidents.detail.original")}
            </Typography>
            <Typography
              component="pre"
              variant="body2"
              sx={{
                bgcolor: "background.default",
                border: "1px solid",
                borderColor: "divider",
                fontFamily: "monospace",
                m: 0,
                mt: 0.5,
                overflowWrap: "anywhere",
                p: 1.5,
                whiteSpace: "pre-wrap",
              }}
            >
              {incident.raw_message}
            </Typography>
          </Box>
        ) : null}

        <Box
          sx={{ borderLeft: "3px solid", borderColor: "primary.main", pl: 1.5 }}
        >
          <Typography color="text.secondary" variant="caption">
            {t("incidents.detail.nextAction")}
          </Typography>
          <Typography variant="body2">{nextStep}</Typography>
        </Box>

        {dismissConfirmation ? (
          <Alert severity="warning">
            <strong>{t("incidents.dismissConfirmationTitle")}</strong>
            <br />
            {t("incidents.dismissConfirmationBody")}
          </Alert>
        ) : null}
        {mutation.isError ? (
          <Alert severity="error">{t("incidents.updateFailed")}</Alert>
        ) : null}
      </Stack>

      <Divider />
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="flex-end"
        gap={1}
        sx={{ bgcolor: "background.default", p: 1.5 }}
      >
        {dismissConfirmation ? (
          <>
            <Button
              ref={dismissCancelRef}
              color="inherit"
              disabled={mutation.isPending}
              onClick={onDismissCancel}
              sx={{ minHeight: 44 }}
            >
              {t("common.cancel")}
            </Button>
            <Button
              color="warning"
              disabled={mutation.isPending}
              onClick={onDismissConfirm}
              variant="contained"
              sx={{ minHeight: 44 }}
            >
              {t("incidents.actions.confirmDismiss")}
            </Button>
          </>
        ) : (
          <>
            {incident.status === "new" ? (
              <Button
                startIcon={<BackHandRoundedIcon />}
                disabled={mutation.isPending}
                onClick={() => onOperation("claim")}
                variant="contained"
                sx={{ minHeight: 44 }}
              >
                {t("incidents.actions.claim")}
              </Button>
            ) : null}
            {ACTIVE_STATUSES.has(incident.status) ? (
              <Button
                color="inherit"
                startIcon={<BlockRoundedIcon />}
                disabled={mutation.isPending}
                onClick={onDismissRequest}
                variant="outlined"
                sx={{ minHeight: 44 }}
              >
                {t("incidents.actions.dismiss")}
              </Button>
            ) : null}
            {ACTIVE_STATUSES.has(incident.status) ? (
              <Button
                startIcon={<DoneRoundedIcon />}
                disabled={mutation.isPending}
                onClick={() => onOperation("resolved")}
                variant="contained"
                sx={{ minHeight: 44 }}
              >
                {t("incidents.actions.resolve")}
              </Button>
            ) : null}
            {!ACTIVE_STATUSES.has(incident.status) ? (
              <Typography
                color="text.secondary"
                sx={{ alignSelf: "center", py: 1 }}
                variant="body2"
              >
                {t("incidents.detail.completedHint")}
              </Typography>
            ) : null}
          </>
        )}
      </Stack>
    </Box>
  );
};

export default function IncidentsPage() {
  const [searchParams] = useSearchParams();
  const requestedIncident = searchParams.get("incident");
  const openedIncident = useRef(null);
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const isMobile = useMediaQuery(theme.breakpoints.down("md"));
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState(requestedIncident ? "all" : "new");
  const [selected, setSelected] = useState(null);
  const [dismissConfirmation, setDismissConfirmation] = useState(false);

  const query = useQuery({
    queryKey: ["mobile-incidents"],
    queryFn: () => cmd.GET_MOBILE_INCIDENTS({ params: { limit: 100 } }),
    refetchInterval: 15000,
    refetchIntervalInBackground: false,
  });

  const mutation = useMutation({
    mutationFn: ({ incident, operation }) =>
      cmd.UPDATE_MOBILE_INCIDENT({
        incidentId: incident.id,
        payload: { operation, revision: incident.revision },
      }),
    onSuccess: (response) => {
      const updated = response?.result ?? response;
      setSelected(updated);
      setDismissConfirmation(false);
      queryClient.setQueryData(["mobile-incidents"], (current = []) =>
        current.map((item) => (item.id === updated.id ? updated : item))
      );
    },
  });

  const incidents = Array.isArray(query.data) ? query.data : [];
  useEffect(() => {
    if (!requestedIncident || openedIncident.current === requestedIncident) return;
    const item = incidents.find(incident => incident.id === requestedIncident);
    if (item) { setSelected(item); openedIncident.current = requestedIncident; }
  }, [requestedIncident, incidents]);
  const counts = useMemo(
    () =>
      Object.fromEntries(
        ["new", "claimed", "resolved", "dismissed"].map((status) => [
          status,
          incidents.filter((item) => item.status === status).length,
        ])
      ),
    [incidents]
  );

  const filtered = useMemo(() => {
    const status = statusForFilter(filter);
    return status
      ? incidents.filter((item) => item.status === status)
      : incidents;
  }, [filter, incidents]);

  const activeIncidents = useMemo(
    () => incidents.filter((item) => ACTIVE_STATUSES.has(item.status)),
    [incidents]
  );
  const oldestOpen = useMemo(
    () =>
      activeIncidents.reduce((oldest, item) => {
        if (!oldest) return item;
        return Date.parse(item.created_at) < Date.parse(oldest.created_at)
          ? item
          : oldest;
      }, null),
    [activeIncidents]
  );
  const affectedServers = useMemo(
    () => new Set(activeIncidents.map((item) => item.server_number)).size,
    [activeIncidents]
  );
  const unassigned = activeIncidents.filter((item) => !item.assigned_to).length;
  const detailIncident = selected || (!isMobile ? filtered[0] : null);

  useEffect(() => {
    setSelected(null);
    setDismissConfirmation(false);
  }, [filter]);

  useEffect(() => {
    if (!selected) return;
    const current = incidents.find((item) => item.id === selected.id);
    if (current && current.revision !== selected.revision) setSelected(current);
  }, [incidents, selected]);

  const filterLabel = (filterValue) => {
    if (filterValue === "all") return `${t("common.all")} ${incidents.length}`;
    const status = statusForFilter(filterValue);
    return `${t(`incidents.tabs.${filterValue}`)} ${counts[status] || 0}`;
  };

  const operate = (operation) => {
    if (!detailIncident) return;
    mutation.mutate({ incident: detailIncident, operation });
  };

  const detail = (
    <IncidentDetail
      incident={detailIncident}
      dismissConfirmation={dismissConfirmation}
      mutation={mutation}
      onDismissCancel={() => setDismissConfirmation(false)}
      onDismissConfirm={() => operate("dismissed")}
      onDismissRequest={() => setDismissConfirmation(true)}
      onOperation={operate}
    />
  );

  return (
    <Box component="section" aria-labelledby="incidents-title" sx={{ pb: 2 }}>
      <PageHeader
        eyebrow={t("incidents.eyebrow")}
        title={t("incidents.title")}
        subtitle={t("incidents.subtitle")}
        titleId="incidents-title"
        actions={
          <Stack direction="row" spacing={1} alignItems="center">
            <Chip
              icon={<FiberManualRecordRoundedIcon color="success" />}
              label={t("incidents.liveUpdates")}
              size="small"
              variant="outlined"
            />
            <Button
              disabled={query.isFetching}
              onClick={() => query.refetch()}
              startIcon={<SyncRoundedIcon />}
              variant="outlined"
            >
              {t("common.refresh")}
            </Button>
          </Stack>
        }
      />

      <Box
        aria-label={t("incidents.summary")}
        sx={{
          display: "grid",
          gap: 1,
          gridTemplateColumns: {
            xs: "repeat(2, minmax(0, 1fr))",
            sm: "repeat(4, minmax(0, 1fr))",
          },
          mb: 2,
        }}
      >
        <MetricCard
          icon={ReportProblemRoundedIcon}
          label={t("incidents.metrics.open")}
          value={activeIncidents.length}
        />
        <MetricCard
          icon={PersonOffRoundedIcon}
          label={t("incidents.metrics.unassigned")}
          value={unassigned}
        />
        <MetricCard
          icon={DnsRoundedIcon}
          label={t("incidents.metrics.servers")}
          value={affectedServers}
        />
        <MetricCard
          icon={ScheduleRoundedIcon}
          label={t("incidents.metrics.oldest")}
          value={
            oldestOpen ? formatAge(oldestOpen.created_at, i18n.language) : "–"
          }
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gap: 2,
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            md: "minmax(0, 0.9fr) minmax(380px, 1.1fr)",
          },
        }}
      >
        <Box
          component="section"
          aria-labelledby="incident-queue-title"
          sx={{ minWidth: 0 }}
        >
          <Stack
            direction="row"
            alignItems="baseline"
            justifyContent="space-between"
            gap={1}
            sx={{ mb: 1 }}
          >
            <Box>
              <Typography id="incident-queue-title" component="h2" variant="h6">
                {t("incidents.queue.title")}
              </Typography>
              <Typography color="text.secondary" variant="body2">
                {t("incidents.queue.description")}
              </Typography>
            </Box>
            <Chip label={filtered.length} size="small" />
          </Stack>

          {isMobile ? (
            <FormControl fullWidth size="small" sx={{ mb: 1.5 }}>
              <InputLabel id="incident-filter-label">
                {t("incidents.filters")}
              </InputLabel>
              <Select
                labelId="incident-filter-label"
                label={t("incidents.filters")}
                value={filter}
                onChange={(event) => setFilter(event.target.value)}
              >
                {FILTERS.map((value) => (
                  <MenuItem key={value} value={value}>
                    {filterLabel(value)}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <Tabs
              value={filter}
              onChange={(_event, value) => setFilter(value)}
              variant="fullWidth"
              aria-label={t("incidents.filters")}
              sx={{
                mb: 1.5,
                borderBottom: "1px solid",
                borderColor: "divider",
              }}
            >
              {FILTERS.map((value) => (
                <Tab
                  key={value}
                  value={value}
                  label={filterLabel(value)}
                  sx={{ minWidth: 0, px: 1, whiteSpace: "nowrap" }}
                />
              ))}
            </Tabs>
          )}

          {query.isLoading ? (
            <PageState kind="loading" title={t("common.loading")} />
          ) : query.isError ? (
            <PageState
              kind="error"
              title={t("incidents.loadFailed")}
              action={{
                label: t("common.retry"),
                onClick: () => query.refetch(),
              }}
            />
          ) : filtered.length === 0 ? (
            <PageState
              kind="empty"
              title={t("incidents.emptyTitle")}
              description={t("incidents.emptyDescription")}
            />
          ) : (
            <Stack spacing={1}>
              {filtered.map((incident) => (
                <IncidentCard
                  key={incident.id}
                  incident={incident}
                  isSelected={detailIncident?.id === incident.id}
                  onOpen={setSelected}
                />
              ))}
            </Stack>
          )}
        </Box>

        {!isMobile ? (
          <Box
            component="aside"
            aria-label={t("incidents.detail.panel")}
            sx={{ minWidth: 0 }}
          >
            <Box sx={{ position: "sticky", top: 16 }}>{detail}</Box>
          </Box>
        ) : null}
      </Box>

      <Dialog
        fullScreen
        open={isMobile && Boolean(selected)}
        onClose={() => {
          setSelected(null);
          setDismissConfirmation(false);
        }}
        aria-labelledby="mobile-incident-detail-title"
        aria-describedby="incident-detail-description"
        slotProps={{ paper: { sx: { borderRadius: 0 } } }}
      >
        <DialogTitle
          id="mobile-incident-detail-title"
          sx={{
            borderBottom: "1px solid",
            borderColor: "divider",
            pb: 1.5,
            pr: 7,
            pt: "calc(16px + env(safe-area-inset-top))",
          }}
        >
          {t("incidents.detail.mobileTitle")}
          <IconButton
            aria-label={t("common.close")}
            onClick={() => {
              setSelected(null);
              setDismissConfirmation(false);
            }}
            sx={{
              minHeight: 44,
              minWidth: 44,
              position: "absolute",
              right: 6,
              top: "calc(6px + env(safe-area-inset-top))",
            }}
          >
            <CloseRoundedIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, pb: "env(safe-area-inset-bottom)" }}>
          {detail}
        </DialogContent>
      </Dialog>
    </Box>
  );
}
