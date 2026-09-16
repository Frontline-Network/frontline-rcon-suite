import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";

export default function ArchiveDialog({
  open,
  onClose,
  round,
  detection,
  mutation,
  t,
}) {
  const { i18n } = useTranslation();
  const [retentionDays, setRetentionDays] = useState(30);
  const [reason, setReason] = useState("");
  useEffect(() => {
    if (open) {
      setRetentionDays(30);
      setReason(
        detection
          ? `${t("reviewPattern")}: ${
              detection.player_name || detection.player_id
            }`
          : ""
      );
    }
  }, [open, detection]);
  const submit = () => {
    mutation.mutate(
      {
        path: "archives",
        data: {
          round_id: round.round_id,
          retention_days: retentionDays,
          reason,
          ...(detection?.review?.incident_id
            ? { incident_id: detection.review.incident_id }
            : {}),
        },
      },
      { onSuccess: onClose }
    );
  };
  return (
    <Dialog open={open} onClose={onClose} fullWidth maxWidth="sm">
      <DialogTitle>
        {detection ? t("saveInvestigation") : t("saveRound")}
      </DialogTitle>
      <DialogContent>
        <Stack gap={2} sx={{ pt: 1 }}>
          <Typography variant="body2">
            {round ? new Date(round.start * 1000).toLocaleString(i18n.resolvedLanguage) : "–"} ·{" "}
            {t("fullRound")}
          </Typography>
          <TextField
            select
            label={t("retentionPeriod")}
            value={retentionDays}
            onChange={(event) => setRetentionDays(Number(event.target.value))}
          >
            <MenuItem value={30}>30 {t("days")}</MenuItem>
            <MenuItem value={90}>90 {t("days")}</MenuItem>
          </TextField>
          <TextField
            required
            multiline
            minRows={3}
            label={t("reason")}
            value={reason}
            inputProps={{ maxLength: 1000 }}
            onChange={(event) => setReason(event.target.value)}
            helperText={t("archiveNoCopy")}
          />
        </Stack>
      </DialogContent>
      <DialogActions>
        <Button onClick={onClose}>{t("cancel")}</Button>
        <Button
          variant="contained"
          disabled={!reason.trim() || mutation.isPending || !round}
          onClick={submit}
        >
          {t("secure")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
