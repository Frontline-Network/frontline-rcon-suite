import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { execute, get } from "@/utils/fetchUtils";
import "@/i18n/register-automod-action-review";

export default function AutomodActionReview() {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const has = (key) => permissions?.is_superuser || permissions?.permissions?.some((entry) => entry.permission === key);
  const canInspect = !!has("can_view_player_profile");
  const canReview = canInspect && !!has("can_run_raw_commands");
  const [journal, setJournal] = useState({ results: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const response = await get("get_pending_automod_actions?limit=50");
      const data = await response.json();
      if (data.failed || data.error || !data.result) throw new Error();
      setJournal(data.result);
      setError("");
    } catch { setError(t("automodActionReview.loadError")); }
  }, [t]);
  useEffect(() => { if (canInspect) load(); }, [canInspect, load]);

  async function review(row) {
    if (!window.confirm(t("automodActionReview.confirm"))) return;
    const reason = window.prompt(t("automodActionReview.reason"));
    if (!reason?.trim()) return;
    setBusy(true);
    try {
      const response = await execute("review_pending_automod_action", { player_id: row.player_id, token: row.token, reason: reason.trim() });
      const data = await response.json();
      if (data.failed || data.error || data.result !== true) throw new Error();
      await load();
    } catch { setError(t("automodActionReview.saveError")); }
    finally { setBusy(false); }
  }

  if (!canInspect || (!error && journal.results.length === 0)) return null;
  return (
    <Box component="section" data-testid="automod-action-review" sx={{ border: 1, borderColor: "warning.main", p: 2 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
          <Typography variant="subtitle1" fontWeight={700}>{t("automodActionReview.title")}</Typography>
          <Button size="small" onClick={load} disabled={busy}>{t("automodActionReview.refresh")}</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">{t("automodActionReview.help")}</Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {journal.results.map((row) => <Box key={row.token}>
          <Divider sx={{ mb: 1 }} />
          <Stack spacing={1}>
            <Typography variant="body2"><strong>{t("automodActionReview.player")}:</strong> {row.player_id === "*" ? t("automodActionReview.allPlayers") : row.player_id}</Typography>
            {row.player_id === "*" && <Alert severity="warning">{t("automodActionReview.legacyHold")}</Alert>}
            <Typography variant="body2"><strong>{t("automodActionReview.time")}:</strong> {new Date(row.updated_at).toLocaleString(i18n.resolvedLanguage)}</Typography>
            {row.actions.map((item) => <Typography key={`${item.rule}:${item.action}`} variant="body2"><strong>{t("automodActionReview.action")}:</strong> {t(`automodActionReview.rules.${item.rule}`, { defaultValue: item.rule })} · {t(`automodActionReview.actions.${item.action}`, { defaultValue: item.action })}</Typography>)}
            {canReview && <Box><Button variant="outlined" size="small" disabled={busy} onClick={() => review(row)}>{t("automodActionReview.release")}</Button></Box>}
          </Stack>
        </Box>)}
        {journal.more && <Typography variant="body2">{t("automodActionReview.more")}</Typography>}
      </Stack>
    </Box>
  );
}
