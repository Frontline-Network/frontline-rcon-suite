import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { execute, get } from "@/utils/fetchUtils";
import "@/i18n/register-blacklist-sync-review";

export default function BlacklistSyncReview() {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const has = (key) => permissions?.is_superuser ||
    permissions?.permissions?.some((entry) => entry.permission === key);
  const canInspect = !!has("can_view_blacklists");
  const canReview = !!has("can_change_blacklists");
  const [journal, setJournal] = useState({ total: 0, results: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const load = useCallback(async () => {
    try {
      const response = await get("get_blacklist_sync_reviews?limit=50");
      const data = await response.json();
      if (data.failed || data.error || !data.result) throw new Error();
      setJournal(data.result);
      setError("");
    } catch {
      setError(t("blacklistSyncReview.loadError"));
    }
  }, [t]);
  useEffect(() => { if (canInspect) load(); }, [canInspect, load]);

  async function acknowledge(row) {
    if (!window.confirm(t("blacklistSyncReview.confirmPrompt"))) return;
    setBusy(true);
    try {
      const response = await execute("acknowledge_blacklist_sync_review", { delivery_id: row.id });
      const data = await response.json();
      if (data.failed || data.error || data.result !== true) throw new Error();
      await load();
    } catch {
      setError(t("blacklistSyncReview.saveError"));
    } finally {
      setBusy(false);
    }
  }

  if (!canInspect) return null;
  return (
    <Box component="section" data-testid="blacklist-sync-review" sx={{ border: 1, borderColor: "divider", p: 2 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
          <Typography variant="subtitle1" fontWeight={700}>{t("blacklistSyncReview.title")}</Typography>
          <Button size="small" onClick={load} disabled={busy}>{t("blacklistSyncReview.refresh")}</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">{t("blacklistSyncReview.help")}</Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {!error && journal.results.length === 0 && <Typography variant="body2">{t("blacklistSyncReview.empty")}</Typography>}
        {journal.results.map((row) => (
          <Box key={row.id}>
            <Divider sx={{ mb: 1 }} />
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="body2"><strong>{t("blacklistSyncReview.operation")}:</strong> {row.command} · {new Date(row.updated_at).toLocaleString(i18n.resolvedLanguage)}</Typography>
                <Typography variant="body2">{row.reason?.startsWith("overlapping") ? t("blacklistSyncReview.overlap") : t("blacklistSyncReview.uncertain")}</Typography>
                <details><summary>{t("blacklistSyncReview.details")}</summary><Box component="pre" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}>{JSON.stringify(row.payload, null, 2)}</Box></details>
              </Box>
              {canReview && <Button variant="outlined" size="small" disabled={busy} onClick={() => acknowledge(row)}>{t("blacklistSyncReview.confirm")}</Button>}
            </Stack>
          </Box>
        ))}
        {journal.total > journal.results.length && <Typography variant="body2">{t("blacklistSyncReview.more", { count: journal.total - journal.results.length })}</Typography>}
      </Stack>
    </Box>
  );
}
