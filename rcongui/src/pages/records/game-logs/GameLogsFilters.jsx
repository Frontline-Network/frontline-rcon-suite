import { useMemo, useState } from "react";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Collapse,
  FormControl,
  FormControlLabel,
  InputAdornment,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import SearchIcon from "@mui/icons-material/Search";
import TuneIcon from "@mui/icons-material/Tune";
import FilterAltOffIcon from "@mui/icons-material/FilterAltOff";
import { DesktopDateTimePicker } from "@mui/x-date-pickers/DesktopDateTimePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import { Form, useNavigation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import dayjs from "dayjs";
import { useGlobalStore } from "@/stores/global-state";
import { logActions } from "@/utils/lib";
import { EVENT_CATEGORIES, getCategoryCounts } from "./event-utils";

const actionOptions = Object.keys(logActions).map((name) => ({ name }));

const getPresetDates = (preset, logs) => {
  const now = dayjs();
  if (preset === "1h") return { from: now.subtract(1, "hour"), till: now };
  if (preset === "6h") return { from: now.subtract(6, "hour"), till: now };
  if (preset === "24h") return { from: now.subtract(24, "hour"), till: now };
  if (preset === "last_round") {
    const roundStart = logs.find(
      (log) => String(log.type).toUpperCase() === "MATCH START"
    );
    const fallbackStart = logs.length
      ? logs.reduce(
          (earliest, log) =>
            dayjs(log.event_time).isBefore(earliest)
              ? dayjs(log.event_time)
              : earliest,
          dayjs(logs[0].event_time)
        )
      : now.subtract(2, "hour");
    return {
      from: roundStart ? dayjs(roundStart.event_time) : fallbackStart,
      till: now,
    };
  }
  if (preset === "all") return { from: null, till: null };
  return null;
};

const filterShellSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.paper",
  "& .MuiOutlinedInput-root, & .MuiButton-root, & .MuiChip-root": {
    borderRadius: 0,
  },
};

export default function GameLogsFilters({
  fields,
  logs,
  category,
  onCategoryChange,
  onSubmit,
  onReset,
}) {
  const { t } = useTranslation();
  const navigation = useNavigation();
  const server = useGlobalStore((state) => state.serverState);
  const otherServers = useGlobalStore((state) => state.servers);
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [formFields, setFormFields] = useState({
    player_query: fields.player_id || fields.player_name || "",
    action: fields.action || "",
    limit: fields.limit || 500,
    time_sort: fields.time_sort || "desc",
    exact_player:
      fields.exact_player === true || fields.exact_player === "true",
    exact_action:
      fields.exact_action === true || fields.exact_action === "true",
    server_filter: fields.server_filter || "",
    from: fields.from ? dayjs(fields.from) : null,
    till: fields.till ? dayjs(fields.till) : null,
    time_preset: fields.from || fields.till ? "custom" : "all",
  });

  const serverOptions = useMemo(() => {
    const items = [server, ...(otherServers || [])].filter(Boolean);
    const unique = new Map();
    items.forEach((item) => unique.set(String(item.server_number), item));
    return [...unique.values()].map((item) => ({
      label: item.short_name || item.name,
      value: String(item.server_number),
    }));
  }, [server, otherServers]);

  const categoryCounts = useMemo(() => getCategoryCounts(logs), [logs]);
  const selectedServer = serverOptions.find(
    (option) => option.value === String(formFields.server_filter)
  );

  const updateField = (name, value) => {
    setFormFields((current) => ({ ...current, [name]: value }));
  };

  const handlePresetChange = (event) => {
    const preset = event.target.value;
    const dates = getPresetDates(preset, logs);
    setFormFields((current) => ({
      ...current,
      time_preset: preset,
      ...(dates || {}),
    }));
    if (preset === "custom") setAdvancedOpen(true);
  };

  const handleClear = () => {
    setFormFields({
      player_query: "",
      action: "",
      limit: 500,
      time_sort: "desc",
      exact_player: false,
      exact_action: false,
      server_filter: "",
      from: null,
      till: null,
      time_preset: "all",
    });
    setAdvancedOpen(false);
    onCategoryChange("all");
    onReset();
  };

  return (
    <Form onSubmit={onSubmit}>
      <Box sx={filterShellSx}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "minmax(220px, 1.5fr) minmax(170px, .8fr)",
              lg: "minmax(260px, 1.4fr) minmax(180px, .8fr) minmax(190px, 1fr) auto auto",
            },
            gap: 1,
            p: 1,
            alignItems: "stretch",
          }}
        >
          <TextField
            name="player_query"
            value={formFields.player_query}
            onChange={(event) =>
              updateField("player_query", event.target.value)
            }
            label={t("records.gameLogs.timeline.playerSearch")}
            placeholder={t("records.gameLogs.timeline.playerSearch")}
            size="small"
            InputProps={{
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon fontSize="small" />
                </InputAdornment>
              ),
            }}
          />

          <FormControl size="small">
            <InputLabel id="game-log-time-preset-label">
              {t("records.gameLogs.timeline.timeRange")}
            </InputLabel>
            <Select
              labelId="game-log-time-preset-label"
              value={formFields.time_preset}
              label={t("records.gameLogs.timeline.timeRange")}
              onChange={handlePresetChange}
            >
              <MenuItem value="last_round">
                {t("records.gameLogs.timeline.lastRound")}
              </MenuItem>
              <MenuItem value="1h">
                {t("records.gameLogs.timeline.lastHour")}
              </MenuItem>
              <MenuItem value="6h">
                {t("records.gameLogs.timeline.lastSixHours")}
              </MenuItem>
              <MenuItem value="24h">
                {t("records.gameLogs.timeline.lastDay")}
              </MenuItem>
              <MenuItem value="all">
                {t("records.gameLogs.timeline.allTime")}
              </MenuItem>
              <MenuItem value="custom">
                {t("records.gameLogs.timeline.customRange")}
              </MenuItem>
            </Select>
          </FormControl>

          <FormControl size="small">
            <InputLabel id="game-log-server-label">
              {t("records.gameLogs.server")}
            </InputLabel>
            <Select
              labelId="game-log-server-label"
              name="server_filter"
              value={formFields.server_filter}
              onChange={(event) =>
                updateField("server_filter", event.target.value)
              }
              label={t("records.gameLogs.server")}
            >
              <MenuItem value="">{t("records.gameLogs.allServers")}</MenuItem>
              {serverOptions.map((option) => (
                <MenuItem key={option.value} value={option.value}>
                  {option.label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>

          <Button
            type="submit"
            variant="contained"
            disabled={navigation.state === "loading"}
            sx={{ minHeight: 40, px: 2.5 }}
          >
            {navigation.state === "loading"
              ? t("records.gameLogs.timeline.filtering")
              : t("records.gameLogs.timeline.filter")}
          </Button>
          <Button
            type="button"
            variant="outlined"
            startIcon={<TuneIcon />}
            onClick={() => setAdvancedOpen((open) => !open)}
            aria-expanded={advancedOpen}
            sx={{ minHeight: 40, px: 2 }}
          >
            {t("records.gameLogs.timeline.advanced")}
          </Button>
        </Box>

        <Box
          role="tablist"
          aria-label={t("records.gameLogs.timeline.eventCategories")}
          sx={{
            display: "flex",
            overflowX: "auto",
            borderTop: "1px solid",
            borderColor: "divider",
            scrollbarWidth: "thin",
          }}
        >
          {EVENT_CATEGORIES.map((item) => {
            const selected = category === item.id;
            return (
              <Button
                key={item.id}
                role="tab"
                aria-selected={selected}
                onClick={() => onCategoryChange(item.id)}
                color="inherit"
                sx={{
                  minWidth: "max-content",
                  minHeight: 42,
                  px: 2,
                  borderBottom: "2px solid",
                  borderBottomColor: selected ? "primary.main" : "transparent",
                  color: selected ? "text.primary" : "text.secondary",
                  bgcolor: selected ? "action.selected" : "transparent",
                }}
              >
                {t(`records.gameLogs.timeline.categories.${item.labelKey}`)}
                <Typography
                  component="span"
                  variant="caption"
                  sx={{ ml: 0.75, color: "inherit" }}
                >
                  {categoryCounts[item.id] || 0}
                </Typography>
              </Button>
            );
          })}
        </Box>

        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          useFlexGap
          flexWrap="wrap"
          sx={{
            minHeight: 42,
            px: 1,
            py: 0.75,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          <Chip
            variant="outlined"
            size="small"
            label={`${t("records.gameLogs.server")}: ${
              selectedServer?.label || t("records.gameLogs.allServers")
            }`}
          />
          <Chip
            variant="outlined"
            size="small"
            label={`${t("records.gameLogs.timeline.timeRange")}: ${t(
              `records.gameLogs.timeline.presets.${formFields.time_preset}`
            )}`}
          />
          {formFields.action && (
            <Chip
              variant="outlined"
              size="small"
              label={`${t("records.gameLogs.action")}: ${formFields.action}`}
              onDelete={() => updateField("action", "")}
            />
          )}
          <Box sx={{ flexGrow: 1 }} />
          <Button
            type="button"
            size="small"
            color="inherit"
            startIcon={<FilterAltOffIcon />}
            onClick={handleClear}
            sx={{ color: "text.secondary" }}
          >
            {t("records.gameLogs.timeline.clearAll")}
          </Button>
        </Stack>

        <Collapse in={advancedOpen}>
          <LocalizationProvider dateAdapter={AdapterDayjs}>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, minmax(0, 1fr))",
                  xl: "repeat(4, minmax(0, 1fr))",
                },
                gap: 1,
                p: 1,
                borderTop: "1px solid",
                borderColor: "divider",
                bgcolor: "background.default",
              }}
            >
              <Stack spacing={0.5}>
                <Autocomplete
                  freeSolo
                  options={actionOptions}
                  getOptionLabel={(option) =>
                    typeof option === "string" ? option : option.name
                  }
                  value={
                    actionOptions.find(
                      (option) => option.name === formFields.action
                    ) ||
                    formFields.action ||
                    null
                  }
                  onChange={(event, value) =>
                    updateField(
                      "action",
                      typeof value === "string" ? value : value?.name || ""
                    )
                  }
                  onInputChange={(event, value, reason) => {
                    if (reason === "input") updateField("action", value);
                  }}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      size="small"
                      label={t("records.gameLogs.action")}
                    />
                  )}
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={formFields.exact_action}
                      onChange={(event) =>
                        updateField("exact_action", event.target.checked)
                      }
                    />
                  }
                  label={t("records.gameLogs.timeline.exactAction")}
                />
              </Stack>

              <Stack spacing={0.5}>
                <TextField
                  size="small"
                  type="number"
                  label={t("records.gameLogs.timeline.maxLoaded")}
                  value={formFields.limit}
                  inputProps={{ min: 1, max: 5000 }}
                  onChange={(event) => updateField("limit", event.target.value)}
                />
                <FormControlLabel
                  control={
                    <Switch
                      size="small"
                      checked={formFields.exact_player}
                      onChange={(event) =>
                        updateField("exact_player", event.target.checked)
                      }
                    />
                  }
                  label={t("records.gameLogs.timeline.exactPlayer")}
                />
              </Stack>

              <DesktopDateTimePicker
                value={formFields.from}
                label={t("records.gameLogs.from")}
                onChange={(value) => {
                  updateField("from", value);
                  updateField("time_preset", "custom");
                }}
                format="YYYY/MM/DD HH:mm"
                ampm={false}
                slotProps={{ textField: { size: "small", fullWidth: true } }}
              />
              <DesktopDateTimePicker
                value={formFields.till}
                label={t("records.gameLogs.until")}
                onChange={(value) => {
                  updateField("till", value);
                  updateField("time_preset", "custom");
                }}
                format="YYYY/MM/DD HH:mm"
                ampm={false}
                slotProps={{ textField: { size: "small", fullWidth: true } }}
              />
              <FormControl size="small">
                <InputLabel id="game-log-sort-label">
                  {t("records.gameLogs.sort")}
                </InputLabel>
                <Select
                  labelId="game-log-sort-label"
                  value={formFields.time_sort}
                  onChange={(event) =>
                    updateField("time_sort", event.target.value)
                  }
                  label={t("records.gameLogs.sort")}
                >
                  <MenuItem value="desc">
                    {t("records.gameLogs.newest")}
                  </MenuItem>
                  <MenuItem value="asc">
                    {t("records.gameLogs.oldest")}
                  </MenuItem>
                </Select>
              </FormControl>
            </Box>
          </LocalizationProvider>
        </Collapse>
      </Box>

      <input type="hidden" name="action" value={formFields.action} />
      <input type="hidden" name="limit" value={formFields.limit} />
      <input type="hidden" name="time_sort" value={formFields.time_sort} />
      <input
        type="hidden"
        name="exact_player"
        value={String(formFields.exact_player)}
      />
      <input
        type="hidden"
        name="exact_action"
        value={String(formFields.exact_action)}
      />
      <input
        type="hidden"
        name="from"
        value={formFields.from?.isValid() ? formFields.from.toISOString() : ""}
      />
      <input
        type="hidden"
        name="till"
        value={formFields.till?.isValid() ? formFields.till.toISOString() : ""}
      />
    </Form>
  );
}
