import { useEffect, useMemo, useRef, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  IconButton,
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
import { useTheme } from "@mui/material/styles";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { cmd } from "@/utils/fetchUtils";
import PageHeader from "@/components/shared/PageHeader";
import PageState from "@/components/shared/PageState";

const STATUS_TONES = {
  new: "warning",
  claimed: "info",
  resolved: "success",
  dismissed: "default",
};

const ACTIVE_STATUSES = new Set(["new", "claimed"]);

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

const IncidentCard = ({ incident, onOpen }) => {
  const { t, i18n } = useTranslation();
  const subject = incident.primary_subject ?? incident.subjects?.[0];
  const target = subject?.name ?? incident.target_name;
  const reporter = incident.reporter_name || t("incidents.unknownReporter");

  return (
    <Box
      component="article"
      sx={(theme) => ({
        border: `1px solid ${theme.palette.divider}`,
        borderLeft: `3px solid ${getStatusBorderColor(theme, incident.status)}`,
        bgcolor: "background.paper",
      })}
    >
      <Button
        color="inherit"
        onClick={() => onOpen(incident)}
        sx={{ display: "block", minHeight: 112, p: 1.5, textAlign: "left", width: "100%" }}
      >
        <Stack spacing={1}>
          <Stack direction="row" alignItems="flex-start" justifyContent="space-between" gap={1}>
            <Box sx={{ minWidth: 0 }}>
              <Typography component="h2" variant="subtitle1" noWrap>
                {target || t("incidents.generalReport")}
              </Typography>
              <Typography color="text.secondary" variant="caption">
                {t("incidents.server", { number: incident.server_number })} · {formatTime(incident.updated_at, i18n.language)}
              </Typography>
            </Box>
            <Chip
              color={STATUS_TONES[incident.status] || "default"}
              label={t(`incidents.status.${incident.status}`)}
              size="small"
            />
          </Stack>
          <Typography variant="body2" sx={{ display: "-webkit-box", overflow: "hidden", WebkitBoxOrient: "vertical", WebkitLineClamp: 2 }}>
            {incident.reason || incident.raw_message || t("incidents.noReason")}
          </Typography>
          <Stack direction="row" alignItems="center" spacing={0.75} color="text.secondary">
            <PersonRoundedIcon sx={{ fontSize: 16 }} />
            <Typography variant="caption">{reporter}</Typography>
            {incident.assigned_to ? (
              <Typography variant="caption">· {t("incidents.assignedTo", { name: incident.assigned_to })}</Typography>
            ) : null}
          </Stack>
        </Stack>
      </Button>
    </Box>
  );
};

export default function IncidentsPage() {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));
  const queryClient = useQueryClient();
  const [filter, setFilter] = useState("new");
  const [selected, setSelected] = useState(null);
  const [dismissConfirmation, setDismissConfirmation] = useState(false);
  const dismissCancelRef = useRef(null);

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
  const filtered = useMemo(() => {
    if (filter === "new") return incidents.filter((item) => item.status === "new");
    if (filter === "claimed") return incidents.filter((item) => item.status === "claimed");
    if (filter === "done") return incidents.filter((item) => item.status === "resolved");
    if (filter === "dismissed") return incidents.filter((item) => item.status === "dismissed");
    return incidents;
  }, [filter, incidents]);

  useEffect(() => {
    if (!dismissConfirmation) return;
    window.requestAnimationFrame(() => dismissCancelRef.current?.focus());
  }, [dismissConfirmation]);

  return (
    <Box component="section" aria-labelledby="incidents-title" sx={{ pb: 2 }}>
      <PageHeader
        eyebrow={t("incidents.eyebrow")}
        title={t("incidents.title")}
        subtitle={t("incidents.subtitle")}
        titleId="incidents-title"
      />

      <Tabs
        value={filter}
        onChange={(_event, value) => setFilter(value)}
        variant="scrollable"
        scrollButtons={false}
        aria-label={t("incidents.filters")}
        sx={{ mb: 1.5 }}
      >
        <Tab value="new" label={`${t("incidents.tabs.new")} ${incidents.filter((item) => item.status === "new").length}`} />
        <Tab value="claimed" label={`${t("incidents.tabs.claimed")} ${incidents.filter((item) => item.status === "claimed").length}`} />
        <Tab value="done" label={t("incidents.tabs.done")} />
        <Tab value="dismissed" label={t("incidents.tabs.dismissed")} />
        <Tab value="all" label={t("common.all")} />
      </Tabs>

      {query.isLoading ? (
        <PageState kind="loading" title={t("common.loading")} />
      ) : query.isError ? (
        <PageState
          kind="error"
          title={t("incidents.loadFailed")}
          action={{ label: t("common.retry"), onClick: () => query.refetch() }}
        />
      ) : filtered.length === 0 ? (
        <PageState
          kind="empty"
          title={t("incidents.emptyTitle")}
          description={t("incidents.emptyDescription")}
        />
      ) : (
        <Stack spacing={1}>{filtered.map((incident) => <IncidentCard key={incident.id} incident={incident} onOpen={setSelected} />)}</Stack>
      )}

      <Dialog
        fullScreen={fullScreen}
        fullWidth
        maxWidth="sm"
        open={Boolean(selected)}
        onClose={() => {
          setSelected(null);
          setDismissConfirmation(false);
        }}
        aria-labelledby="incident-detail-title"
        aria-describedby="incident-detail-description"
      >
        {selected ? (
          <>
            <DialogTitle
              id="incident-detail-title"
              sx={{
                pb: 1.5,
                pr: 7,
                pt: fullScreen
                  ? "calc(16px + env(safe-area-inset-top))"
                  : 2,
              }}
            >
              {selected.target_name || selected.primary_subject?.name || t("incidents.generalReport")}
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
                  top: fullScreen
                    ? "calc(6px + env(safe-area-inset-top))"
                    : 6,
                }}
              >
                <CloseRoundedIcon />
              </IconButton>
            </DialogTitle>
            <DialogContent dividers>
              <Stack spacing={2}>
                <Stack direction="row" spacing={1} flexWrap="wrap" useFlexGap>
                  <Chip color={STATUS_TONES[selected.status] || "default"} label={t(`incidents.status.${selected.status}`)} size="small" />
                  <Chip icon={<SportsEsportsRoundedIcon />} label={t("incidents.server", { number: selected.server_number })} size="small" variant="outlined" />
                </Stack>
                <Box>
                  <Typography color="text.secondary" variant="caption">{t("incidents.reason")}</Typography>
                  <Typography id="incident-detail-description" variant="body1">{selected.reason || selected.raw_message || t("incidents.noReason")}</Typography>
                </Box>
                <Divider />
                <Stack spacing={0.5}>
                  <Typography variant="body2"><strong>{t("incidents.reporter")}:</strong> {selected.reporter_name || t("incidents.unknownReporter")}</Typography>
                  <Typography variant="body2"><strong>{t("incidents.assignee")}:</strong> {selected.assigned_to || t("incidents.unassigned")}</Typography>
                  <Typography variant="body2"><strong>{t("incidents.updated")}:</strong> {formatTime(selected.updated_at, i18n.language)}</Typography>
                </Stack>
                {dismissConfirmation ? (
                  <Alert severity="warning">
                    <strong>{t("incidents.dismissConfirmationTitle")}</strong>
                    <br />
                    {t("incidents.dismissConfirmationBody")}
                  </Alert>
                ) : null}
                {mutation.isError ? <Alert severity="error">{t("incidents.updateFailed")}</Alert> : null}
              </Stack>
            </DialogContent>
            <DialogActions sx={{ flexWrap: "wrap", gap: 1, p: 1.5, pb: "calc(12px + env(safe-area-inset-bottom))" }}>
              {dismissConfirmation ? (
                <>
                  <Button
                    ref={dismissCancelRef}
                    color="inherit"
                    disabled={mutation.isPending}
                    onClick={() => setDismissConfirmation(false)}
                    sx={{ minHeight: 44 }}
                  >
                    {t("common.cancel")}
                  </Button>
                  <Button
                    color="warning"
                    disabled={mutation.isPending}
                    onClick={() => mutation.mutate({ incident: selected, operation: "dismissed" })}
                    variant="contained"
                    sx={{ minHeight: 44 }}
                  >
                    {t("incidents.actions.confirmDismiss")}
                  </Button>
                </>
              ) : (
                <>
                  {selected.status === "new" ? <Button startIcon={<BackHandRoundedIcon />} disabled={mutation.isPending} onClick={() => mutation.mutate({ incident: selected, operation: "claim" })} sx={{ minHeight: 44 }}>{t("incidents.actions.claim")}</Button> : null}
                  {ACTIVE_STATUSES.has(selected.status) ? <Button color="inherit" startIcon={<BlockRoundedIcon />} disabled={mutation.isPending} onClick={() => setDismissConfirmation(true)} sx={{ minHeight: 44 }}>{t("incidents.actions.dismiss")}</Button> : null}
                  {ACTIVE_STATUSES.has(selected.status) ? <Button variant="contained" startIcon={<DoneRoundedIcon />} disabled={mutation.isPending} onClick={() => mutation.mutate({ incident: selected, operation: "resolved" })} sx={{ minHeight: 44 }}>{t("incidents.actions.resolve")}</Button> : null}
                </>
              )}
            </DialogActions>
          </>
        ) : null}
      </Dialog>
    </Box>
  );
}
