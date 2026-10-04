import React from "react";
import {
  Box,
  Button,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { useTranslation } from "react-i18next";

export function ControlPageLayout({
  sections,
  active,
  onChange,
  children,
  navigationWidth = "190px",
}) {
  const theme = useTheme();
  const { t } = useTranslation();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  return (
    <Box data-theme-surface="panel"
      className="wardogs-control-layout"
      sx={{
        display: { xs: "block", md: "grid" },
        gridTemplateColumns: `${navigationWidth} minmax(0, 1fr)`,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      {compact ? (
        <FormControl fullWidth size="small" sx={{ p: 1 }}>
          <InputLabel id="control-page-section-label" sx={{ ml: 1 }}>
            {t("common.section")}
          </InputLabel>
          <Select
            id="control-page-section"
            labelId="control-page-section-label"
            value={active}
            label={t("common.section")}
            onChange={(event) => onChange(event.target.value)}
            sx={{ borderRadius: 0 }}
          >
            {sections.map((section) => (
              <MenuItem
                key={section.key}
                value={section.key}
                disabled={section.disabled}
              >
                {section.label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      ) : (
        <Stack
          className="wardogs-control-navigation"
          sx={{ borderRight: "1px solid", borderColor: "divider" }}
        >
          {sections.map((section) => {
            const selected = section.key === active;
            return (
              <Button
                key={section.key}
                onClick={() => onChange(section.key)}
                disabled={section.disabled}
                sx={{
                  justifyContent: "flex-start",
                  minHeight: 58,
                  px: 2,
                  borderRadius: 0,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  borderLeft: "2px solid",
                  borderLeftColor: selected ? "primary.main" : "transparent",
                  bgcolor: selected ? "action.selected" : "transparent",
                  color: selected ? "primary.main" : "text.secondary",
                  textTransform: "none",
                  textAlign: "left",
                  whiteSpace: "normal",
                  lineHeight: 1.3,
                  letterSpacing: "0.01em",
                  fontWeight: selected ? 800 : 700,
                }}
              >
                {section.label}
              </Button>
            );
          })}
        </Stack>
      )}
      <Box sx={{ minWidth: 0 }}>{children}</Box>
    </Box>
  );
}

export function ControlSectionHeader({ title, description, action }) {
  return (
    <Stack
      className="wardogs-control-header"
      direction={{ xs: "column", sm: "row" }}
      spacing={1.5}
      justifyContent="space-between"
      alignItems={{ sm: "center" }}
      sx={{ p: 1.75, borderBottom: "1px solid", borderColor: "divider" }}
    >
      <Box>
        <Typography variant="h6" sx={{ textTransform: "uppercase" }}>
          {title}
        </Typography>
        {description && (
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.25 }}>
            {description}
          </Typography>
        )}
      </Box>
      {action}
    </Stack>
  );
}

export function ControlRow({
  title,
  description,
  value,
  meta,
  status,
  disabled = false,
}) {
  return (
    <Box
      className="wardogs-control-row"
      sx={{
        display: { xs: "flex", lg: "grid" },
        flexDirection: "column",
        gridTemplateColumns: "minmax(220px, 1fr) minmax(280px, 1.6fr) 150px",
        alignItems: { lg: "center" },
        gap: { xs: 1.25, lg: 0 },
        minHeight: 78,
        px: 1.75,
        py: { xs: 1.5, lg: 1 },
        borderBottom: "1px solid",
        borderColor: "divider",
        opacity: disabled ? 0.55 : 1,
        "& > *": { px: { lg: 1 } },
      }}
    >
      <Box>
        <Typography variant="body2" fontWeight={800}>
          {title}
        </Typography>
        {description && (
          <Typography variant="caption" color="text.secondary">
            {description}
          </Typography>
        )}
      </Box>
      <Box sx={{ minWidth: 0 }}>{value}</Box>
      <Stack spacing={0.25}>
        {meta && (
          <Typography variant="caption" color="text.secondary">
            {meta}
          </Typography>
        )}
        {status}
      </Stack>
    </Box>
  );
}

export function ControlActionBar({
  dirtyCount,
  onReset,
  onSave,
  saving,
  saveDisabled,
}) {
  const { t } = useTranslation();
  return (
    <Stack data-theme-surface="panel"
      className="wardogs-action-bar"
      direction={{ xs: "column", sm: "row" }}
      spacing={1}
      alignItems={{ sm: "center" }}
      sx={{
        position: "sticky",
        bottom: 0,
        zIndex: 5,
        mt: 1.5,
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
        boxShadow: 3,
      }}
    >
      <Stack
        direction="row"
        spacing={0.75}
        alignItems="center"
        sx={{ mr: "auto" }}
        className="wardogs-control-action-status"
      >
        {dirtyCount ? (
          <WarningAmberRoundedIcon color="warning" />
        ) : (
          <CheckCircleOutlineRoundedIcon color="success" />
        )}
        <Typography variant="body2" fontWeight={800}>
          {dirtyCount
            ? t("settingsPanels.controls.unsaved", { count: dirtyCount })
            : t("settingsPanels.controls.noChanges")}
        </Typography>
      </Stack>
      <Button
        variant="outlined"
        disabled={!dirtyCount || saving}
        onClick={onReset}
        sx={{ borderRadius: 0 }}
      >
        {t("settingsPanels.controls.reset")}
      </Button>
      <Button
        variant="contained"
        disabled={!dirtyCount || saving || saveDisabled}
        onClick={onSave}
        sx={{ borderRadius: 0, minWidth: 210 }}
      >
        {t(
          saving
            ? "settingsPanels.controls.saving"
            : "settingsPanels.controls.save"
        )}
      </Button>
    </Stack>
  );
}

export function RowStatus({ dirty, error }) {
  const { t } = useTranslation();
  return (
    <Stack
      direction="row"
      spacing={0.6}
      alignItems="center"
      color={error ? "error.main" : dirty ? "warning.main" : "success.main"}
    >
      {error || dirty ? (
        <WarningAmberRoundedIcon fontSize="small" />
      ) : (
        <CheckCircleOutlineRoundedIcon fontSize="small" />
      )}
      <Typography variant="body2" fontWeight={700} color="inherit">
        {t(
          error
            ? "settingsPanels.controls.failed"
            : dirty
            ? "settingsPanels.controls.changed"
            : "settingsPanels.controls.saved"
        )}
      </Typography>
    </Stack>
  );
}
import "@/i18n/register-settings-panels";
