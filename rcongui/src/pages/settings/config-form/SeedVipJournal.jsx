import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Divider, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { execute, get } from "@/utils/fetchUtils";
import "@/i18n/register-seed-vip-journal";

export default function SeedVipJournal() {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const has = (key) => permissions?.is_superuser ||
    permissions?.permissions?.some((entry) => entry.permission === key);
  const canInspect = !!has("can_view_vip_ids");
  const canReview = !!has("can_add_vip");
  const [journal, setJournal] = useState({ total: 0, results: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await get("get_seed_vip_journal?status=review&limit=50");
      const data = await response.json();
      if (data.failed || data.error || !data.result) throw new Error();
      setJournal(data.result);
      setError("");
    } catch {
      setError(t("seedVipJournal.loadError"));
    }
  }, [t]);

  useEffect(() => {
    if (canInspect) load();
  }, [canInspect, load]);

  async function acknowledge(row) {
    if (!window.confirm(t("seedVipJournal.confirmPrompt"))) return;
    setBusy(true);
    try {
      const response = await execute("acknowledge_seed_vip_review", { grant_id: row.id });
      const data = await response.json();
      if (data.failed || data.error || data.result !== true) throw new Error();
      await load();
    } catch {
      setError(t("seedVipJournal.saveError"));
    } finally {
      setBusy(false);
    }
  }

  if (!canInspect) return null;
  return (
    <Box data-testid="seed-vip-review-journal" sx={{ border: 1, borderColor: "divider", p: 2 }}>
      <Stack spacing={1.5}>
        <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
          <Typography variant="subtitle1" fontWeight={700}>{t("seedVipJournal.title")}</Typography>
          <Button size="small" onClick={load} disabled={busy}>{t("seedVipJournal.refresh")}</Button>
        </Stack>
        <Typography variant="body2" color="text.secondary">{t("seedVipJournal.help")}</Typography>
        {error && <Alert severity="error">{error}</Alert>}
        {!error && journal.results.length === 0 && <Typography variant="body2">{t("seedVipJournal.empty")}</Typography>}
        {journal.results.map((row) => (
          <Box key={row.id}>
            <Divider sx={{ mb: 1 }} />
            <Stack direction={{ xs: "column", sm: "row" }} justifyContent="space-between" gap={1}>
              <Box>
                <Typography variant="body2"><strong>{t("seedVipJournal.player")}:</strong> {row.player_name} ({row.player_id})</Typography>
                <Typography variant="body2"><strong>{t("seedVipJournal.target")}:</strong> {row.target ? new Date(row.target).toLocaleString(i18n.resolvedLanguage) : "—"}</Typography>
              </Box>
              {canReview && <Button variant="outlined" size="small" disabled={busy} onClick={() => acknowledge(row)}>{t("seedVipJournal.confirm")}</Button>}
            </Stack>
          </Box>
        ))}
        {journal.total > journal.results.length && <Typography variant="body2">{t("seedVipJournal.more", { count: journal.total - journal.results.length })}</Typography>}
      </Stack>
    </Box>
  );
}
