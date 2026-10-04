import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  getLogPresentation,
  normalizeLogDisplayPreferences,
} from "./log-display-preferences.mjs";

export function LogDisplaySettings({ value, onChange, disabled }) {
  const { t } = useTranslation();
  const presentation = getLogPresentation(value);
  const select = (key, label, options) => (
    <FormControl fullWidth size="small" disabled={disabled}>
      <InputLabel id={`log-display-${key}`}>{label}</InputLabel>
      <Select
        labelId={`log-display-${key}`}
        label={label}
        value={value[key]}
        onChange={(event) => onChange({ ...value, [key]: event.target.value })}
      >
        {options.map(([id, label]) => (
          <MenuItem key={id} value={id}>
            {label}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        {t("views.live.logDisplayHelp")}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
          gap: 2,
        }}
      >
        {select("fontSize", t("tableConfig.fontSize"), [
          ["small", t("tableConfig.small")],
          ["normal", t("tableConfig.normal")],
          ["large", t("tableConfig.large")],
        ])}
        {select("density", t("views.live.logSpacing"), [
          ["dense", t("views.live.compactRows")],
          ["normal", t("tableConfig.normal")],
          ["comfortable", t("tableConfig.comfortable")],
        ])}
      </Box>
      <Box data-theme-surface="panel"
        component="figure"
        aria-label={t("views.live.logPreview")}
        sx={{
          m: 0,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.default",
        }}
      >
        <Typography
          component="figcaption"
          variant="caption"
          sx={{ px: 1.25, py: 0.5 }}
        >
          {t("views.live.logPreview")}
        </Typography>
        {["logPreviewMessage", "logPreviewEvent"].map((key, index) => (
          <Box
            key={key}
            sx={{
              px: 1.25,
              py: presentation.paddingY,
              fontSize: presentation.fontSize,
              fontWeight: 300,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="caption" color="primary.light">
              21:23 · {index ? "MATCH" : "MESSAGE"}
            </Typography>
            <Box sx={{ mt: 0.5 }}>{t(`views.live.${key}`)}</Box>
          </Box>
        ))}
      </Box>
      <Button
        disabled={disabled}
        sx={{ alignSelf: "flex-start" }}
        onClick={() => onChange(normalizeLogDisplayPreferences())}
      >
        {t("views.live.resetLogDisplay")}
      </Button>
    </Stack>
  );
}
