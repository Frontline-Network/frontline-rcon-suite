import { useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  FormControlLabel,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { logActions } from "@/utils/lib";
import { isValidLogQueryLimit } from "./log-display-preferences.mjs";

// Mounted only while open: live polling must never replace an unfinished draft.
export function LogFiltersDialog({
  tableConfig,
  searchParams,
  playerOptions,
  selectedTeams,
  onApply,
  onClose,
}) {
  const { t } = useTranslation();
  const [section, setSection] = useState("view");
  const [draft, setDraft] = useState(() => ({
    enabled: tableConfig.filters.actions.enabled,
    actions: [...tableConfig.filters.actions.selected],
    players: Object.keys(playerOptions).filter((name) => playerOptions[name]),
    teams: [...selectedTeams],
    highlighted: tableConfig.highlighted,
    highlightActions: [...tableConfig.actions],
    query: {
      enabled: searchParams.enabled,
      actions: [...searchParams.actions],
      players: [...searchParams.players],
      inclusive_filter: searchParams.inclusive_filter,
      limit: searchParams.limit,
    },
  }));
  const update = (patch) => setDraft((current) => ({ ...current, ...patch }));
  const updateQuery = (patch) =>
    setDraft((current) => ({
      ...current,
      query: { ...current.query, ...patch },
    }));
  const validLimit = isValidLogQueryLimit(draft.query.limit);
  const picker = (
    id,
    label,
    values,
    options,
    onChange,
    getOptionLabel = (value) => value
  ) => (
    <Autocomplete
      id={`live-log-filter-${id}`}
      multiple
      disableCloseOnSelect
      options={[...new Set([...options, ...values])]}
      value={values}
      onChange={(_, values) => onChange(values)}
      size="small"
      limitTags={3}
      getOptionLabel={getOptionLabel}
      noOptionsText={t("common.noData")}
      renderInput={(params) => <TextField {...params} label={label} />}
      sx={{ "& .MuiAutocomplete-tag": { maxWidth: "100%" } }}
    />
  );
  const actionPicker = (id, label, values, onChange) =>
    picker(id, label, values, Object.keys(logActions), onChange, (action) =>
      `${logActions[action] ?? ""} ${action}`.trim()
    );
  const toggle = (label, checked, onChange) => (
    <FormControlLabel
      sx={{ m: 0, minHeight: 44 }}
      label={label}
      control={
        <Switch
          checked={checked}
          onChange={(_, checked) => onChange(checked)}
        />
      }
    />
  );
  return (
    <Dialog
      open
      onClose={onClose}
      fullWidth
      maxWidth="sm"
      aria-labelledby="live-log-filter-title"
    >
      <DialogTitle id="live-log-filter-title">
        {t("views.live.advancedFilters")}
      </DialogTitle>
      <Tabs
        value={section}
        onChange={(_, value) => setSection(value)}
        variant="fullWidth"
        aria-label={t("views.live.logFilterSections")}
      >
        <Tab
          id="log-filter-tab-view"
          aria-controls="log-filter-panel-view"
          value="view"
          label={t("views.live.logViewFilters")}
        />
        <Tab
          id="log-filter-tab-query"
          aria-controls="log-filter-panel-query"
          value="query"
          label={t("views.live.logQueryFilters")}
        />
      </Tabs>
      <DialogContent dividers>
        <Box
          role="tabpanel"
          id="log-filter-panel-view"
          aria-labelledby="log-filter-tab-view"
          hidden={section !== "view"}
        >
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              {t("views.live.logViewFilterHelp")}
            </Typography>
            {toggle(
              t("views.live.logActionFilterEnabled"),
              draft.enabled,
              (enabled) => update({ enabled })
            )}
            {actionPicker(
              "actions",
              t("views.live.filterActions"),
              draft.actions,
              (actions) => update({ actions, enabled: actions.length > 0 })
            )}
            {picker(
              "teams",
              t("views.live.logFilterTeams"),
              draft.teams,
              ["Axis", "Allies"],
              (teams) => update({ teams }),
              (team) =>
                t(team === "Axis" ? "views.team.axis" : "views.team.allies")
            )}
            {picker(
              "players",
              t("views.live.logFilterPlayers"),
              draft.players,
              Object.keys(playerOptions),
              (players) => update({ players })
            )}
            {toggle(
              t("selection.logHighlight"),
              draft.highlighted,
              (highlighted) => update({ highlighted })
            )}
            {actionPicker(
              "highlights",
              t("views.live.logHighlightActions"),
              draft.highlightActions,
              (highlightActions) =>
                update({
                  highlightActions,
                  highlighted: highlightActions.length > 0,
                })
            )}
            <Button
              sx={{ alignSelf: "flex-start" }}
              onClick={() =>
                update({
                  enabled: false,
                  actions: [],
                  teams: [],
                  players: [],
                  highlighted: false,
                  highlightActions: [],
                })
              }
            >
              {t("views.live.resetLogViewFilters")}
            </Button>
          </Stack>
        </Box>
        <Box
          role="tabpanel"
          id="log-filter-panel-query"
          aria-labelledby="log-filter-tab-query"
          hidden={section !== "query"}
        >
          <Stack spacing={2}>
            <Typography variant="body2" color="text.secondary">
              {t("views.live.logQueryFilterHelp")}
            </Typography>
            {toggle(
              t("views.live.logQueryFilterEnabled"),
              draft.query.enabled,
              (enabled) => updateQuery({ enabled })
            )}
            <FormControl size="small" fullWidth>
              <InputLabel id="log-query-mode-label">
                {t("views.live.filterMode")}
              </InputLabel>
              <Select
                labelId="log-query-mode-label"
                label={t("views.live.filterMode")}
                value={draft.query.inclusive_filter ? "inclusive" : "exclusive"}
                onChange={(event) =>
                  updateQuery({
                    inclusive_filter: event.target.value === "inclusive",
                  })
                }
              >
                <MenuItem value="inclusive">
                  {t("views.live.logIncludeSelected")}
                </MenuItem>
                <MenuItem value="exclusive">
                  {t("views.live.logExcludeSelected")}
                </MenuItem>
              </Select>
            </FormControl>
            {actionPicker(
              "query-actions",
              t("views.live.filterActions"),
              draft.query.actions,
              (actions) => updateQuery({ actions })
            )}
            {picker(
              "query-players",
              t("views.live.logFilterPlayers"),
              draft.query.players,
              Object.keys(playerOptions),
              (players) => updateQuery({ players })
            )}
            <TextField
              size="small"
              fullWidth
              type="number"
              label={t("views.live.logQueryLimit")}
              value={draft.query.limit}
              onChange={(event) => updateQuery({ limit: event.target.value })}
              error={!validLimit}
              helperText={t(
                validLimit
                  ? "views.live.logQueryLimitHelp"
                  : "views.live.logQueryLimitError"
              )}
              inputProps={{ min: 10, max: 100000, step: 1 }}
            />
            <Button
              sx={{ alignSelf: "flex-start" }}
              onClick={() =>
                updateQuery({
                  enabled: true,
                  actions: [],
                  players: [],
                  inclusive_filter: true,
                  limit: 500,
                })
              }
            >
              {t("views.live.resetLogQueryFilters")}
            </Button>
          </Stack>
        </Box>
      </DialogContent>
      <DialogActions
        sx={{ flexWrap: "wrap", "& .MuiButton-root": { minHeight: 44 } }}
      >
        <Button onClick={onClose}>{t("common.cancel")}</Button>
        <Button
          variant="contained"
          disabled={!validLimit}
          onClick={() =>
            onApply({
              ...draft,
              query: { ...draft.query, limit: Number(draft.query.limit) },
            })
          }
        >
          {t("views.live.applyLogFilters")}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
