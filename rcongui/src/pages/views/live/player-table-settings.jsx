import { useState } from "react";
import {
  Box,
  Button,
  Checkbox,
  Chip,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import {
  FIXED_PLAYER_COLUMNS,
  PLAYER_COLUMN_GROUPS,
  PLAYER_COLUMN_IDS,
  getPlayerColumnVisibility,
  getPlayerTablePresentation,
  normalizePlayerTablePreferences,
  setPlayerColumnVisible,
} from "./player-table-preferences.mjs";

export function PlayerTableSettings({ value, onChange, disabled }) {
  const { t } = useTranslation();
  const [search, setSearch] = useState("");
  const visibility = getPlayerColumnVisibility(value);
  const presentation = getPlayerTablePresentation(value);
  const groups = Object.entries(PLAYER_COLUMN_GROUPS)
    .map(([group, columns]) => [
      group,
      Object.entries(columns).filter(
        ([id, label]) =>
          !FIXED_PLAYER_COLUMNS.includes(id) &&
          t(label)
            .toLocaleLowerCase()
            .includes(search.trim().toLocaleLowerCase())
      ),
    ])
    .filter(([, columns]) => columns.length > 0);
  const select = (key, label, options) => (
    <FormControl size="small" fullWidth disabled={disabled}>
      <InputLabel id={`players-display-${key}`}>{label}</InputLabel>
      <Select
        labelId={`players-display-${key}`}
        label={label}
        value={value[key]}
        onChange={(event) => onChange({ ...value, [key]: event.target.value })}
      >
        {options.map(([id, text]) => (
          <MenuItem key={id} value={id}>
            {text}
          </MenuItem>
        ))}
      </Select>
    </FormControl>
  );
  return (
    <Stack spacing={2}>
      <Typography variant="body2" color="text.secondary">
        {t("views.live.playerTableHelp")}
      </Typography>
      {select("preset", t("views.live.columnPreset"), [
        ["operations", t("views.live.operationsPreset")],
        ["all", t("views.live.allColumnsPreset")],
        ["custom", t("views.live.customPreset")],
      ])}
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
        {select("density", t("views.live.rowSpacing"), [
          ["dense", t("views.live.compactRows")],
          ["normal", t("tableConfig.normal")],
          ["comfortable", t("tableConfig.comfortable")],
        ])}
      </Box>
      <Box
        component="figure"
        aria-label={t("views.live.tablePreview")}
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
          sx={{ px: 1, py: 0.5, display: "block", color: "text.secondary" }}
        >
          {t("views.live.tablePreview")}
        </Typography>
        <Box
          sx={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            px: 1.5,
            minHeight: presentation.rowHeight,
            fontSize: presentation.fontSize,
            fontWeight: 300,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          <span>{t("views.live.samplePlayer")}</span>
          <span>12 / 4</span>
        </Box>
      </Box>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        flexWrap="wrap"
      >
        <Typography component="h3" variant="subtitle2">
          {t("selection.columns")}
        </Typography>
        <Chip
          size="small"
          label={t("views.live.visibleColumnsCount", {
            count: Object.values(visibility).filter(Boolean).length,
            total: PLAYER_COLUMN_IDS.length,
          })}
        />
      </Stack>
      <Typography variant="caption" color="text.secondary">
        {t("views.live.fixedColumnsHelp")}
      </Typography>
      <TextField
        size="small"
        label={t("views.live.searchColumns")}
        value={search}
        disabled={disabled}
        onChange={(event) => setSearch(event.target.value)}
        type="search"
        fullWidth
      />
      {groups.map(([group, columns]) => (
        <Box
          component="fieldset"
          key={group}
          sx={{
            border: "1px solid",
            borderColor: "divider",
            p: 1.25,
            m: 0,
            minWidth: 0,
          }}
        >
          <Typography
            component="legend"
            variant="caption"
            sx={{ px: 0.5, fontWeight: 700 }}
          >
            {t(`views.live.columnGroups.${group}`)}
          </Typography>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
              columnGap: 1,
            }}
          >
            {columns.map(([id, label]) => (
              <FormControlLabel
                key={id}
                sx={{
                  m: 0,
                  minHeight: 44,
                  "& .MuiFormControlLabel-label": { fontSize: "0.875rem" },
                }}
                label={t(label)}
                control={
                  <Checkbox
                    size="small"
                    disabled={disabled}
                    checked={visibility[id]}
                    onChange={(_, checked) =>
                      onChange(setPlayerColumnVisible(value, id, checked))
                    }
                  />
                }
              />
            ))}
          </Box>
        </Box>
      ))}
      {groups.length === 0 && (
        <Typography variant="body2">
          {t("views.live.noMatchingColumns")}
        </Typography>
      )}
      <Button
        disabled={disabled}
        onClick={() => onChange(normalizePlayerTablePreferences())}
        sx={{ alignSelf: "flex-start" }}
      >
        {t("views.live.resetPlayerTable")}
      </Button>
    </Stack>
  );
}
