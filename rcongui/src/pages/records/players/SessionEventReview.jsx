import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, LinearProgress, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { execute, get } from "@/utils/fetchUtils";
import "@/i18n/register-session-event-review";

export default function SessionEventReview() {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const has = (key) => permissions?.is_superuser ||
    permissions?.permissions?.some((entry) => entry.permission === key);
  const canInspect = !!has("can_view_player_profile");
  const canResolve = canInspect && !!has("can_run_raw_commands");
  const [journal, setJournal] = useState(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const response = await get("get_pending_session_events?limit=50");
      const data = await response.json();
      if (data.failed || data.error || !data.result) throw new Error();
      setJournal(data.result);
      setError("");
    } catch {
      setError(t("sessionEventReview.loadError"));
    }
  }, [t]);
  useEffect(() => { if (canInspect) load(); }, [canInspect, load]);

  async function resolve(row, decision, sessionId) {
    const confirmKey = { link: "confirmLink", create: "confirmCreate", discard: "confirmDiscard" }[decision];
    if (!window.confirm(t(`sessionEventReview.${confirmKey}`))) return;
    const reason = window.prompt(t("sessionEventReview.reasonPrompt"));
    if (!reason?.trim()) return;
    setBusy(true);
    try {
      const response = await execute("resolve_pending_session_event", {
        player_id: row.player_id || "", event_kind: row.kind, event_us: row.event_us,
        ...(row.fingerprint ? { fingerprint: row.fingerprint } : {}),
        decision, reason: reason.trim(), ...(sessionId ? { session_id: sessionId } : {}),
      });
      const data = await response.json();
      if (data.failed || data.error || data.result !== true) throw new Error();
      await load();
    } catch {
      setError(t("sessionEventReview.saveError"));
    } finally {
      setBusy(false);
    }
  }

  if (!canInspect) return <Typography>{t("sessionEventReview.noAccess")}</Typography>;
  return (
    <Box component="section" data-testid="session-event-review" sx={{ p: 2 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
          <Typography component="h1" variant="h5">{t("sessionEventReview.title")}</Typography>
          <Button size="small" onClick={load} disabled={busy}>{t("sessionEventReview.refresh")}</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">{t("sessionEventReview.help")}</Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {!error && !journal && <LinearProgress aria-label={t("sessionEventReview.title")} />}
        {!error && journal?.results.length === 0 && <Typography>{t("sessionEventReview.empty")}</Typography>}
        {journal?.results.map((row) => (
          <Box key={row.fingerprint || `${row.kind}:${row.player_id}:${row.event_us}`}>
            <Divider sx={{ mb: 1 }} />
            <Stack spacing={1}>
              <Typography variant="body2"><strong>{t("sessionEventReview.player")}:</strong> {row.player_id || row.player_name || t("sessionEventReview.unknownIdentity")}</Typography>
              <Typography variant="body2"><strong>{t("sessionEventReview.event")}:</strong> {t(`sessionEventReview.${row.event_kind || row.kind}`)} · {new Date(row.event_time).toLocaleString(i18n.resolvedLanguage)}</Typography>
              {row.kind === "unidentified" && <Alert severity="warning">{t("sessionEventReview.unidentified")} {row.raw}</Alert>}
              {row.kind === "connect" && !row.identity_exists && <Alert severity="warning">{t("sessionEventReview.missingIdentity")}</Alert>}
              {row.legacy_candidates?.map((candidate) => (
                <Stack key={candidate.id} direction={{ xs: "column", sm: "row" }} alignItems={{ sm: "center" }} gap={1}>
                  <Typography variant="body2">{t("sessionEventReview.legacy")}: {candidate.start} – {candidate.end || t("sessionEventReview.noEnd")}</Typography>
                  {canResolve && <Button variant="outlined" size="small" disabled={busy} onClick={() => resolve(row, "link", candidate.id)}>{t("sessionEventReview.link", { id: candidate.id })}</Button>}
                </Stack>
              ))}
              {canResolve && <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
                {row.kind === "connect" && row.identity_exists && <Button variant="outlined" size="small" disabled={busy} onClick={() => resolve(row, "create")}>{t("sessionEventReview.create")}</Button>}
                <Button variant="outlined" size="small" disabled={busy} onClick={() => resolve(row, "discard")}>{t("sessionEventReview.discard")}</Button>
              </Stack>}
            </Stack>
          </Box>
        ))}
        {(journal?.more_connects || journal?.more_disconnects || journal?.more_unidentified) && <Typography variant="body2">{t("sessionEventReview.more")}</Typography>}
      </Stack>
    </Box>
  );
}
