import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  FormLabel,
  IconButton,
  Radio,
  RadioGroup,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Tooltip,
  Typography,
  useMediaQuery,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import CheckRoundedIcon from "@mui/icons-material/CheckRounded";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ColorLensRoundedIcon from "@mui/icons-material/ColorLensRounded";
import DarkModeRoundedIcon from "@mui/icons-material/DarkModeRounded";
import DesktopWindowsRoundedIcon from "@mui/icons-material/DesktopWindowsRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import LightModeRoundedIcon from "@mui/icons-material/LightModeRounded";
import RestartAltRoundedIcon from "@mui/icons-material/RestartAltRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { useMutation } from "@tanstack/react-query";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

import { useAppStore } from "@/stores/app-state";
import {
  APPEARANCE_PRESETS,
  appearancesEqual,
  DEFAULT_APPEARANCE,
  isValidHexColor,
  normalizeAppearance,
} from "@/themes/appearance";
import { cmd } from "@/utils/fetchUtils";

const presetIds = [
  "frontline-gold",
  "tactical-blue",
  "signal-green",
  "command-red",
  "neutral",
];

function PreviewState({ color, icon, label }) {
  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="center"
      sx={(theme) => ({
        minWidth: 0,
        px: 1,
        py: 0.75,
        border: "1px solid",
        borderColor: alpha(theme.palette[color].main, 0.42),
        borderLeftWidth: 3,
        bgcolor: alpha(theme.palette[color].main, 0.08),
        color: `${color}.main`,
      })}
    >
      {icon}
      <Typography variant="caption" sx={{ color: "text.primary" }}>
        {label}
      </Typography>
    </Stack>
  );
}

export default function AppearanceSettingsDialog({ open, onClose }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));
  const appearance = useAppStore((state) => state.appearance);
  const setAppearance = useAppStore((state) => state.setAppearance);
  const setAppearancePreview = useAppStore(
    (state) => state.setAppearancePreview
  );
  const clearAppearancePreview = useAppStore(
    (state) => state.clearAppearancePreview
  );
  const [draft, setDraft] = useState(() => normalizeAppearance(appearance));

  const mutation = useMutation({
    mutationFn: (value) => cmd.SET_OWN_APPEARANCE(value),
  });

  useEffect(() => {
    if (!open) return;
    const next = normalizeAppearance(appearance);
    setDraft(next);
    setAppearancePreview(next);
  }, [appearance, open, setAppearancePreview]);

  useEffect(() => {
    if (
      open &&
      (draft.preset !== "custom" || isValidHexColor(draft.customAccent))
    ) {
      setAppearancePreview(draft);
    }
  }, [draft, open, setAppearancePreview]);

  const customColorValid = isValidHexColor(draft.customAccent);
  const dirty = useMemo(
    () => !appearancesEqual(draft, appearance),
    [appearance, draft]
  );

  const updateDraft = (changes) =>
    setDraft((current) => normalizeAppearance({ ...current, ...changes }));

  const closeWithoutSaving = () => {
    clearAppearancePreview();
    onClose();
  };

  const save = async () => {
    if (!customColorValid) return;
    const normalized = normalizeAppearance(draft);
    try {
      const response = await mutation.mutateAsync(normalized);
      setAppearance(normalizeAppearance(response?.result || normalized));
      toast.success(t("appearance.saved"));
    } catch {
      // Older installations can still retain the account-scoped browser
      // fallback until the new preference endpoint is available.
      setAppearance(normalized);
      toast.warn(t("appearance.savedLocally"));
    }
    clearAppearancePreview();
    onClose();
  };

  return (
    <Dialog
      open={open}
      onClose={closeWithoutSaving}
      fullScreen={fullScreen}
      fullWidth
      maxWidth="md"
      aria-labelledby="appearance-dialog-title"
      PaperProps={{
        sx: {
          maxHeight: fullScreen ? "100dvh" : "min(92dvh, 860px)",
          border: "1px solid",
          borderColor: "divider",
          backgroundImage: "none",
        },
      }}
    >
      <DialogTitle
        id="appearance-dialog-title"
        sx={{ pr: 7, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <Stack direction="row" spacing={1.25} alignItems="center">
          <ColorLensRoundedIcon color="primary" />
          <Box>
            <Typography component="h2" variant="h6">
              {t("appearance.title")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("appearance.subtitle")}
            </Typography>
          </Box>
        </Stack>
        <IconButton
          onClick={closeWithoutSaving}
          aria-label={t("common.close")}
          sx={{ position: "absolute", right: 12, top: 12 }}
        >
          <CloseRoundedIcon />
        </IconButton>
      </DialogTitle>

      <DialogContent sx={{ p: { xs: 2, sm: 3 } }}>
        <Stack spacing={3}>
          <Box component="section" aria-labelledby="appearance-presets-title">
            <Typography id="appearance-presets-title" variant="subtitle1">
              {t("appearance.presets.title")}
            </Typography>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              {t("appearance.presets.description")}
            </Typography>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "repeat(2, minmax(0, 1fr))",
                  sm: "repeat(5, minmax(0, 1fr))",
                },
                gap: 1,
              }}
            >
              {presetIds.map((id) => {
                const preset = APPEARANCE_PRESETS[id];
                const selected = draft.preset === id;
                return (
                  <ButtonBase
                    key={id}
                    onClick={() => updateDraft({ preset: id })}
                    aria-pressed={selected}
                    sx={(muiTheme) => ({
                      position: "relative",
                      minHeight: 82,
                      p: 1.25,
                      display: "flex",
                      flexDirection: "column",
                      alignItems: "flex-start",
                      justifyContent: "space-between",
                      border: "1px solid",
                      borderColor: selected
                        ? muiTheme.palette.primary.main
                        : muiTheme.palette.divider,
                      bgcolor: selected
                        ? alpha(muiTheme.palette.primary.main, 0.1)
                        : muiTheme.palette.background.paper,
                      boxShadow: selected
                        ? `inset 0 0 0 1px ${muiTheme.palette.primary.main}`
                        : "none",
                      "&:focus-visible": {
                        outline: `3px solid ${alpha(
                          muiTheme.palette.primary.main,
                          0.5
                        )}`,
                        outlineOffset: 2,
                      },
                    })}
                  >
                    <Stack direction="row" spacing={0.5}>
                      {[preset.accent, preset.dark.paper, preset.light.background].map(
                        (color) => (
                          <Box
                            key={color}
                            sx={{
                              width: 18,
                              height: 18,
                              bgcolor: color,
                              border: "1px solid",
                              borderColor: "divider",
                            }}
                          />
                        )
                      )}
                    </Stack>
                    <Typography variant="caption" sx={{ textAlign: "left" }}>
                      {t(`appearance.presets.${id}`)}
                    </Typography>
                    {selected ? (
                      <CheckRoundedIcon
                        color="primary"
                        fontSize="small"
                        sx={{ position: "absolute", right: 6, top: 6 }}
                      />
                    ) : null}
                  </ButtonBase>
                );
              })}
            </Box>
          </Box>

          <Divider />

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
              gap: 3,
            }}
          >
            <Stack spacing={2.5}>
              <FormControl component="fieldset">
                <FormLabel component="legend">{t("appearance.mode.title")}</FormLabel>
                <ToggleButtonGroup
                  exclusive
                  fullWidth
                  size="small"
                  value={draft.mode}
                  onChange={(_event, mode) => mode && updateDraft({ mode })}
                  aria-label={t("appearance.mode.title")}
                  sx={{ mt: 1 }}
                >
                  <ToggleButton value="light">
                    <LightModeRoundedIcon fontSize="small" sx={{ mr: 0.75 }} />
                    {t("appearance.mode.light")}
                  </ToggleButton>
                  <ToggleButton value="dark">
                    <DarkModeRoundedIcon fontSize="small" sx={{ mr: 0.75 }} />
                    {t("appearance.mode.dark")}
                  </ToggleButton>
                  <ToggleButton value="system">
                    <DesktopWindowsRoundedIcon fontSize="small" sx={{ mr: 0.75 }} />
                    {t("appearance.mode.system")}
                  </ToggleButton>
                </ToggleButtonGroup>
              </FormControl>

              <FormControl component="fieldset">
                <FormLabel component="legend">
                  {t("appearance.colorVision.title")}
                </FormLabel>
                <RadioGroup
                  value={draft.colorVision}
                  onChange={(event) =>
                    updateDraft({ colorVision: event.target.value })
                  }
                  sx={{ mt: 0.5 }}
                >
                  {["standard", "deuteranopia", "protanopia", "tritanopia"].map(
                    (id) => (
                      <FormControlLabel
                        key={id}
                        value={id}
                        control={<Radio size="small" />}
                        label={t(`appearance.colorVision.${id}`)}
                      />
                    )
                  )}
                </RadioGroup>
                <Typography variant="caption" color="text.secondary">
                  {t("appearance.colorVision.description")}
                </Typography>
              </FormControl>
            </Stack>

            <Stack spacing={2.5}>
              <Box>
                <Typography variant="subtitle2">
                  {t("appearance.custom.title")}
                </Typography>
                <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
                  {t("appearance.custom.description")}
                </Typography>
                <Stack direction="row" spacing={1} alignItems="flex-start">
                  <Tooltip title={t("appearance.custom.picker")}>
                    <Box
                      component="label"
                      sx={{
                        width: 48,
                        height: 40,
                        p: 0.5,
                        border: "1px solid",
                        borderColor: "divider",
                        bgcolor: "background.paper",
                        cursor: "pointer",
                      }}
                    >
                      <Box
                        component="input"
                        type="color"
                        value={
                          customColorValid
                            ? draft.customAccent
                            : DEFAULT_APPEARANCE.customAccent
                        }
                        aria-label={t("appearance.custom.picker")}
                        onChange={(event) =>
                          updateDraft({
                            preset: "custom",
                            customAccent: event.target.value,
                          })
                        }
                        sx={{ width: "100%", height: "100%", p: 0, border: 0 }}
                      />
                    </Box>
                  </Tooltip>
                  <TextField
                    size="small"
                    fullWidth
                    label={t("appearance.custom.hex")}
                    value={draft.customAccent}
                    error={!customColorValid}
                    helperText={
                      customColorValid
                        ? t("appearance.custom.contrastHint")
                        : t("appearance.custom.invalid")
                    }
                    inputProps={{ maxLength: 7, spellCheck: false }}
                    onChange={(event) =>
                      setDraft((current) => ({
                        ...current,
                        preset: "custom",
                        customAccent: event.target.value,
                      }))
                    }
                    onBlur={() =>
                      customColorValid &&
                      setDraft((current) => normalizeAppearance(current))
                    }
                  />
                </Stack>
              </Box>

              <Box aria-labelledby="appearance-preview-title">
                <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
                  <VisibilityRoundedIcon fontSize="small" />
                  <Typography id="appearance-preview-title" variant="subtitle2">
                    {t("appearance.preview.title")}
                  </Typography>
                </Stack>
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                    gap: 0.75,
                  }}
                >
                  <Button variant="contained" size="small">
                    {t("appearance.preview.primary")}
                  </Button>
                  <Chip
                    color="primary"
                    variant="outlined"
                    label={t("appearance.preview.selected")}
                    icon={<CheckRoundedIcon />}
                    sx={{ borderRadius: 0, justifyContent: "flex-start" }}
                  />
                  <PreviewState
                    color="info"
                    icon={<InfoOutlinedIcon fontSize="small" />}
                    label={t("appearance.preview.info")}
                  />
                  <PreviewState
                    color="success"
                    icon={<CheckRoundedIcon fontSize="small" />}
                    label={t("appearance.preview.success")}
                  />
                  <PreviewState
                    color="warning"
                    icon={<WarningAmberRoundedIcon fontSize="small" />}
                    label={t("appearance.preview.warning")}
                  />
                  <PreviewState
                    color="error"
                    icon={<ErrorOutlineRoundedIcon fontSize="small" />}
                    label={t("appearance.preview.error")}
                  />
                </Box>
              </Box>
            </Stack>
          </Box>

          <Alert severity="info" icon={<InfoOutlinedIcon />}>
            {t("appearance.accessibilityHint")}
          </Alert>
        </Stack>
      </DialogContent>

      <DialogActions
        sx={{
          px: { xs: 2, sm: 3 },
          py: 1.5,
          borderTop: "1px solid",
          borderColor: "divider",
          justifyContent: "space-between",
          flexWrap: "wrap",
          gap: 1,
        }}
      >
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            startIcon={<RestartAltRoundedIcon />}
            onClick={() => setDraft(normalizeAppearance(appearance))}
            disabled={!dirty}
          >
            {t("appearance.restoreSaved")}
          </Button>
          <Button
            size="small"
            color="inherit"
            onClick={() => setDraft(normalizeAppearance(DEFAULT_APPEARANCE))}
          >
            {t("appearance.restoreDefault")}
          </Button>
        </Stack>
        <Stack direction="row" spacing={1} alignItems="center">
          {dirty ? (
            <Typography variant="caption" color="warning.main" role="status">
              {t("appearance.unsaved")}
            </Typography>
          ) : null}
          <Button onClick={closeWithoutSaving} color="inherit">
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            startIcon={<SaveRoundedIcon />}
            onClick={save}
            disabled={!dirty || !customColorValid || mutation.isPending}
          >
            {t("appearance.apply")}
          </Button>
        </Stack>
      </DialogActions>
    </Dialog>
  );
}
