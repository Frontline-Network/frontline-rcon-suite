import { useCallback, useEffect, useState } from "react";
import { Alert, Box, Button, Divider, MenuItem, Stack, TextField, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { execute, get } from "@/utils/fetchUtils";
import "@/i18n/register-barricade-scan-review";

function ReviewRow({ row, canReview, busy, onSave }) {
  const { t, i18n } = useTranslation();
  const [decision, setDecision] = useState("");
  const [reason, setReason] = useState("");
  return <Box>
    <Divider sx={{ mb: 1 }} />
    <Stack spacing={1}>
      <Typography variant="body2">{t("barricadeScanReview.player")}: {row.player_id} · {row.game} · {new Date(row.updated_at).toLocaleString(i18n.resolvedLanguage)}</Typography>
      <Typography variant="body2">{t("barricadeScanReview.integration")}: {row.integration_id}</Typography>
      <Alert severity="info">{t(`barricadeScanReview.cause.${["activation_ambiguous", "activation_unknown"].includes(row.review_cause) ? row.review_cause : "uncertain_delivery"}`)}</Alert>
      {canReview && <>
        <TextField select size="small" label={t("barricadeScanReview.decision")} value={decision} onChange={(event) => setDecision(event.target.value)}>
          <MenuItem value="" disabled>{t("barricadeScanReview.choose")}</MenuItem>
          {["confirmed", "dismissed", "retry"].map((value) => <MenuItem key={value} value={value}>{t(`barricadeScanReview.${value}`)}</MenuItem>)}
        </TextField>
        {decision === "retry" && <Alert severity="warning">{t("barricadeScanReview.retryWarning")}</Alert>}
        <TextField size="small" label={t("barricadeScanReview.reason")} value={reason} onChange={(event) => setReason(event.target.value)} inputProps={{ maxLength: 1000 }} />
        <Box><Button variant="outlined" disabled={busy || !decision || !reason.trim()} onClick={() => onSave(row, decision, reason.trim())}>{t("barricadeScanReview.save")}</Button></Box>
      </>}
    </Stack>
  </Box>;
}

export default function BarricadeScanReview() {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const has = (key) => permissions?.is_superuser || permissions?.permissions?.some((entry) => entry.permission === key);
  const canInspect = !!has("can_view_blacklists");
  const canReview = !!has("can_change_blacklists");
  const [journal, setJournal] = useState({ total: 0, results: [] });
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [offset, setOffset] = useState(0);
  const load = useCallback(async () => {
    try {
      const response = await get(`get_barricade_scan_reviews?limit=50&offset=${offset}`);
      const data = await response.json();
      if (!response.ok || data.failed || data.error || !data.result) throw new Error();
      setJournal(data.result);
      setError("");
    } catch { setError(t("barricadeScanReview.loadError")); }
  }, [t, offset]);
  useEffect(() => { if (canInspect) load(); }, [canInspect, load]);
  async function save(row, decision, reason) {
    setBusy(true);
    try {
      const response = await execute("resolve_barricade_scan_review", { delivery_id: row.id, integration_id: row.integration_id, decision, reason });
      const data = await response.json();
      if (!response.ok || data.failed || data.error || data.result !== true) throw new Error();
      if (journal.results.length === 1 && offset > 0) setOffset(Math.max(0, offset - 50));
      else await load();
    } catch { setError(t("barricadeScanReview.saveError")); }
    finally { setBusy(false); }
  }
  if (!canInspect) return null;
  return <Box component="section" data-testid="barricade-scan-review" sx={{ border: 1, borderColor: "divider", p: 2 }}>
    <Stack spacing={1.5}>
      <Stack direction="row" justifyContent="space-between" alignItems="center" gap={1}>
        <Typography variant="subtitle1" fontWeight={700}>{t("barricadeScanReview.title")}</Typography>
        <Button size="small" onClick={load} disabled={busy}>{t("barricadeScanReview.refresh")}</Button>
      </Stack>
      <Typography variant="body2" color="text.secondary">{t("barricadeScanReview.help")}</Typography>
      {error && <Alert severity="error">{error}</Alert>}
      {!error && !journal.results.length && <Typography variant="body2">{t("barricadeScanReview.empty")}</Typography>}
      {journal.results.map((row) => <ReviewRow key={row.id} row={row} canReview={canReview} busy={busy} onSave={save} />)}
      {journal.total > 50 && <Stack direction="row" spacing={1}>
        <Button disabled={busy || offset === 0} onClick={() => setOffset(Math.max(0, offset - 50))}>{t("barricadeScanReview.previous")}</Button>
        <Button disabled={busy || offset + journal.results.length >= journal.total} onClick={() => setOffset(offset + 50)}>{t("barricadeScanReview.next")}</Button>
      </Stack>}
    </Stack>
  </Box>;
}
