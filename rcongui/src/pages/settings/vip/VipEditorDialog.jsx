import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  DesktopDateTimePicker,
  LocalizationProvider,
} from "@mui/x-date-pickers";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import PlayerSearchField from "@/components/form/custom/PlayerSearchField";
import Padlock from "@/components/shared/Padlock";
import { INDEFINITE_EXPIRATION, isVipIndefinite } from "./vip-utils";

const createEmptyForm = () => ({
  description: "",
  player_id: "",
  expiration: dayjs().add(5, "minutes"),
});

export default function VipEditorDialog({
  open,
  initialVip,
  isSaving,
  mutationScope,
  onClose,
  onSave,
}) {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const [form, setForm] = useState(createEmptyForm);
  const [indefinitely, setIndefinitely] = useState(false);
  const [attemptedSubmit, setAttemptedSubmit] = useState(false);

  const isEditing = Boolean(initialVip?.player_id);
  const isValid = useMemo(
    () =>
      Boolean(form.description.trim()) &&
      Boolean(form.player_id.trim()) &&
      (indefinitely ||
        (form.expiration?.isValid?.() && form.expiration.isAfter(dayjs()))),
    [form, indefinitely]
  );

  useEffect(() => {
    if (!open) return;
    setAttemptedSubmit(false);
    if (!initialVip) {
      setForm(createEmptyForm());
      setIndefinitely(false);
      return;
    }

    const permanent = isVipIndefinite(initialVip.vip_expiration);
    setIndefinitely(permanent);
    setForm({
      description: initialVip.name || "",
      player_id: initialVip.player_id || "",
      expiration: permanent
        ? dayjs().add(5, "minutes")
        : dayjs(initialVip.vip_expiration),
    });
  }, [initialVip, open]);

  const handlePlayerSelect = (player) => {
    const name = player.names?.[0]?.name || player.name || "";
    setForm((current) => ({
      ...current,
      description: name,
      player_id: player.player_id || current.player_id,
    }));
  };

  const handleSubmit = () => {
    setAttemptedSubmit(true);
    if (!isValid) return;
    onSave({
      description: form.description.trim(),
      player_id: form.player_id.trim(),
      expiration: indefinitely ? null : form.expiration,
    });
  };

  return (
    <Dialog
      open={open}
      onClose={isSaving ? undefined : onClose}
      fullWidth
      maxWidth="sm"
      fullScreen={fullScreen}
      PaperProps={{ sx: { borderRadius: 0 } }}
    >
      <DialogTitle sx={{ pb: 1 }}>
        <Typography
          component="span"
          variant="overline"
          color="primary.main"
          sx={{ display: "block", letterSpacing: "0.14em" }}
        >
          {t("records.vips.vipRecord")}
        </Typography>
        {isEditing ? t("records.vips.edit") : t("records.vips.addVip")}
      </DialogTitle>
      <DialogContent dividers sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Stack gap={2}>
          {!isEditing ? (
            <Box>
              <Typography variant="subtitle2" sx={{ mb: 1 }}>
                {t("records.vips.searchPlayer")}
              </Typography>
              <PlayerSearchField
                onSelect={handlePlayerSelect}
                disableAddBtn
                direction={{ xs: "column", sm: "row" }}
              />
            </Box>
          ) : null}

          <Stack direction={{ xs: "column", sm: "row" }} gap={1.25}>
            <TextField
              fullWidth
              required
              label={t("records.vips.playerName")}
              value={form.description}
              error={attemptedSubmit && !form.description.trim()}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  description: event.target.value,
                }))
              }
            />
            <TextField
              fullWidth
              required
              disabled={isEditing}
              label={t("records.vips.playerId")}
              value={form.player_id}
              error={attemptedSubmit && !form.player_id.trim()}
              onChange={(event) =>
                setForm((current) => ({
                  ...current,
                  player_id: event.target.value,
                }))
              }
            />
          </Stack>

          <LocalizationProvider
            dateAdapter={AdapterDayjs}
            adapterLocale={i18n.resolvedLanguage === "en" ? "en" : "de"}
            localeText={{ fieldOpenPickerLabel: t("common.chooseDate") }}
          >
            <DesktopDateTimePicker
              value={form.expiration}
              onChange={(expiration) =>
                setForm((current) => ({ ...current, expiration }))
              }
              format="LLL"
              label={t("records.vips.expiration")}
              maxDateTime={dayjs(INDEFINITE_EXPIRATION)}
              disabled={indefinitely}
              disablePast
              slotProps={{
                textField: {
                  fullWidth: true,
                  error:
                    attemptedSubmit &&
                    !indefinitely &&
                    (!form.expiration?.isValid?.() ||
                      !form.expiration.isAfter(dayjs())),
                },
                openPickerButton: {
                  "aria-label": t("common.chooseDate"),
                  title: t("common.chooseDate"),
                },
              }}
            />
          </LocalizationProvider>

          <Padlock
            checked={indefinitely}
            handleChange={setIndefinitely}
            label={t("records.vips.neverExpires")}
          />

          <Alert severity="info" variant="outlined" sx={{ borderRadius: 0 }}>
            {t("records.vips.scopeHint", {
              scope:
                mutationScope === "multi"
                  ? t("records.vips.allServers")
                  : t("records.vips.thisServer"),
            })}
          </Alert>
        </Stack>
      </DialogContent>
      <DialogActions sx={{ p: 1.5 }}>
        <Button onClick={onClose} disabled={isSaving}>
          {t("common.cancel")}
        </Button>
        <Button
          variant="contained"
          onClick={handleSubmit}
          disabled={isSaving}
          sx={{ minWidth: 140 }}
        >
          {isSaving ? t("records.vips.saving") : t("common.save")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
