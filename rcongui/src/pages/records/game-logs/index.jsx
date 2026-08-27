import { cmd } from "@/utils/fetchUtils";
import Grid from "@mui/material/Grid2";
import { DesktopDateTimePicker } from "@mui/x-date-pickers/DesktopDateTimePicker";
import { AdapterDayjs } from "@mui/x-date-pickers/AdapterDayjs";
import { LocalizationProvider } from "@mui/x-date-pickers/LocalizationProvider";
import {
  Autocomplete,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  IconButton,
  Stack,
  TextField,
  Typography,
  useMediaQuery,
} from "@mui/material";
import InputLabel from "@mui/material/InputLabel";
import MenuItem from "@mui/material/MenuItem";
import FormControl from "@mui/material/FormControl";
import Select from "@mui/material/Select";
import FormControlLabel from "@mui/material/FormControlLabel";
import Switch from "@mui/material/Switch";
import { useMemo, useState } from "react";
import {
  Form,
  useLoaderData,
  useNavigation,
  useSubmit,
} from "react-router-dom";
import { getLogsColumns } from "./columns";
import {
  getCoreRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  useReactTable,
} from "@tanstack/react-table";
import LiveLogsTable from "@/components/live-logs/LiveLogsTable";
import { useGlobalStore } from "@/stores/global-state";
import dayjs from "dayjs";
import { TableToolbar } from "@/components/table/TableToolbar";
import { TablePagination } from "@/components/table/TablePagination";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import downloadLogs from "./download";
import DownloadIcon from "@mui/icons-material/Download";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import KeyboardArrowDownRoundedIcon from "@mui/icons-material/KeyboardArrowDownRounded";
import { logActions } from "@/utils/lib";
import timezonePlugin from "dayjs/plugin/timezone";
import utcPlugin from "dayjs/plugin/utc";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { demoHistoricalLogs, isFakeMode } from "@/mirage/demo-data";
import {
  GAME_LOG_PLAYER_ACTION_MENU_ID,
  GameLogPlayerActionMenu,
  useGameLogPlayerActionMenu,
} from "./shared-player-action-menu";

dayjs.extend(timezonePlugin);
dayjs.extend(utcPlugin);

/*
IT'S POST REQUEST !!!

There is not server side pagination !!!

game log example {
    "content": "[VLK] Dorfieee (76561198178339671)",
    "creation_time": "2025-02-10T18:30:37.535809",
    "event_time": "2025-02-10T18:28:15", 
    "id": 503822,
    "player1_id": "76561198178339671",
    "player1_name": "[VLK] Dorfieee",
    "player2_id": null,
    "player2_name": null,
    "raw": "[46 ms (1739212095)] DISCONNECTED [VLK] Dorfieee (76561198178339671)",
    "server": "1",
    "type": "DISCONNECTED",
    "version": 1,
    "weapon": null
}

live log example {
    "action": "DISCONNECTED",
    "event_time": "2025-02-10T21:02:26",
    "line_without_time": "DISCONNECTED Snuffff (b9b23e7f120d1a00d482fba507a81cc8)",
    "message": "Snuffff (b9b23e7f120d1a00d482fba507a81cc8)",
    "player_id_1": "b9b23e7f120d1a00d482fba507a81cc8",
    "player_id_2": null,
    "player_name_1": "Snuffff", 
    "player_name_2": null,
    "raw": "[1.89 sec (1739221346)] DISCONNECTED Snuffff (b9b23e7f120d1a00d482fba507a81cc8)",
    "relative_time_ms": -2221.716,
    "sub_content": null,
    "timestamp_ms": 1739221346000,
    "version": 1,
    "weapon": null
}

params {
  player_name
  action
  player_id
  from
  till
  limit
  time_sort
  exact_player
  exact_action
  server_filter
}

*/

const actionOptions = Object.keys(logActions).map((option) => ({
  label: logActions[option],
  name: option,
}));

const removeLogPlayerIds = (message = "") =>
  message.replace(
    /\((?:(?:Axis|Allies)\/)?(?:[0-9]{17}|[A-Z0-9]{16})\)/g,
    ""
  );

const MobileGameLogList = ({ table }) => {
  const { t } = useTranslation();
  const rows = table.getRowModel().rows;

  if (rows.length === 0) {
    return (
      <Typography color="text.secondary" sx={{ py: 4, textAlign: "center" }}>
        {t("common.noResults")}
      </Typography>
    );
  }

  return (
    <Stack component="ol" aria-label={t("records.gameLogs.title")} sx={{ listStyle: "none", m: 0, p: 0 }}>
      {rows.map((row) => {
        const log = row.original;
        const player1TriggerKey = `${row.id}:player1-mobile`;
        const player2TriggerKey = `${row.id}:player2-mobile`;
        const time = dayjs
          .utc(log.event_time)
          .tz(Intl.DateTimeFormat().resolvedOptions().timeZone)
          .format(t("common.logDateTimeFormat"));
        return (
          <Box
            component="li"
            key={log.id ?? row.id}
            sx={(theme) => ({
              borderBottom: `1px solid ${theme.palette.divider}`,
              px: 1.25,
              py: 1.1,
              "&:first-of-type": { borderTop: `1px solid ${theme.palette.divider}` },
            })}
          >
            <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
              <Typography color="text.secondary" variant="caption">{time}</Typography>
              <Chip label={log.type || t("common.unknown")} size="small" variant="outlined" />
            </Stack>
            <Stack direction="row" alignItems="center" flexWrap="wrap" gap={0.75} sx={{ mt: 0.5 }}>
              {log.player1_name && log.player1_id ? (
                <Button
                  aria-controls={
                    table.options.meta?.activePlayerActionKey ===
                    player1TriggerKey
                      ? GAME_LOG_PLAYER_ACTION_MENU_ID
                      : undefined
                  }
                  aria-expanded={
                    table.options.meta?.activePlayerActionKey ===
                    player1TriggerKey
                      ? "true"
                      : undefined
                  }
                  aria-haspopup="true"
                  color="inherit"
                  data-testid="game-log-player-action-trigger"
                  onClick={(event) =>
                    table.options.meta?.openPlayerActionMenu?.(
                      event.currentTarget,
                      { player_id: log.player1_id, name: log.player1_name },
                      {
                        onlineAction: true,
                        triggerKey: player1TriggerKey,
                      }
                    )
                  }
                  size="small"
                  sx={{ minHeight: 44, px: 0.5 }}
                >
                  {log.player1_name}
                </Button>
              ) : log.player1_name ? (
                <Typography variant="body2" sx={{ minHeight: 44, display: "flex", alignItems: "center" }}>
                  {log.player1_name}
                </Typography>
              ) : null}
              {log.player2_name ? (
                <>
                  <Typography aria-hidden color="text.secondary">→</Typography>
                  {log.player2_id ? (
                    <Button
                      aria-controls={
                        table.options.meta?.activePlayerActionKey ===
                        player2TriggerKey
                          ? GAME_LOG_PLAYER_ACTION_MENU_ID
                          : undefined
                      }
                      aria-expanded={
                        table.options.meta?.activePlayerActionKey ===
                        player2TriggerKey
                          ? "true"
                          : undefined
                      }
                      aria-haspopup="true"
                      color="inherit"
                      data-testid="game-log-player-action-trigger"
                      onClick={(event) =>
                        table.options.meta?.openPlayerActionMenu?.(
                          event.currentTarget,
                          { player_id: log.player2_id, name: log.player2_name },
                          {
                            onlineAction: true,
                            triggerKey: player2TriggerKey,
                          }
                        )
                      }
                      size="small"
                      sx={{ minHeight: 44, px: 0.5 }}
                    >
                      {log.player2_name}
                    </Button>
                  ) : (
                    <Typography variant="body2" sx={{ minHeight: 44, display: "flex", alignItems: "center" }}>
                      {log.player2_name}
                    </Typography>
                  )}
                </>
              ) : null}
            </Stack>
            {log.content ? (
              <Typography sx={{ overflowWrap: "anywhere" }} variant="body2">
                {removeLogPlayerIds(log.content)}
              </Typography>
            ) : null}
          </Box>
        );
      })}
    </Stack>
  );
};

export const loader = async ({ request }) => {
  const url = new URL(request.url);
  // Get params and set default values if not provided
  const player_name = url.searchParams.get("player_name") ?? "";
  const player_id = url.searchParams.get("player_id") ?? "";
  const action = url.searchParams.get("action") ?? "";
  const from = url.searchParams.get("from")
    ? dayjs(url.searchParams.get("from"))
    : null;
  const till = url.searchParams.get("till")
    ? dayjs(url.searchParams.get("till"))
    : null;
  const limit = url.searchParams.get("limit")
    ? Number(url.searchParams.get("limit"))
    : 500;
  const time_sort = url.searchParams.get("time_sort") ?? "desc";
  const exact_player = url.searchParams.get("exact_player") ?? false;
  const exact_action = url.searchParams.get("exact_action") ?? false;
  const server_filter = url.searchParams.get("server_filter") ?? "";

  const fields = {
    player_name,
    action,
    player_id,
    from,
    till,
    limit,
    time_sort,
    exact_player,
    exact_action,
    server_filter,
  };

  const response = isFakeMode()
    ? { result: demoHistoricalLogs }
    : await cmd.GET_HISTORICAL_LOGS({ payload: fields });

  const logs = response.result;

  return {
    logs,
    fields,
  };
};

const GameLogsPage = () => {
  const { t } = useTranslation();
  const { logs, fields } = useLoaderData();
  const submit = useSubmit();
  const compact = useMediaQuery((theme) => theme.breakpoints.down("md"));
  const hasActiveFilters = Boolean(
    fields.player_name ||
      fields.player_id ||
      fields.action ||
      fields.from ||
      fields.till ||
      fields.server_filter ||
      fields.exact_player ||
      fields.exact_action
  );
  const [filtersOpen, setFiltersOpen] = useState(hasActiveFilters);
  const playerActionMenu = useGameLogPlayerActionMenu();
  const logsColumns = useMemo(() => getLogsColumns(t), [t]);

  const table = useReactTable({
    data: logs ?? [],
    columns: logsColumns,
    getCoreRowModel: getCoreRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    meta: playerActionMenu.tableMeta,
    initialState: {
      pagination: {
        pageIndex: 0,
        pageSize: 100,
      },
    },
  });

  const handleSubmit = (e) => {
    e.preventDefault();
    const formData = new FormData(e.target);
    if (formData.get("server_filter") === "0") {
      formData.set("server_filter", "");
    }
    const fields = Object.fromEntries(formData);
    submit(fields, {
      method: "GET",
      replace: true,
    });
  };

  const handleDownload = () => {
    downloadLogs(logs);
  };

  return (
    <Stack spacing={1} sx={{ mt: 2 }}>
      <PageHeader
        eyebrow={t("records.gameLogs.eyebrow")}
        title={t("records.gameLogs.title")}
        subtitle={t("records.gameLogs.subtitle")}
      />
      {compact ? (
        <Button
          aria-controls="game-log-filters"
          aria-expanded={filtersOpen}
          onClick={() => setFiltersOpen((value) => !value)}
          startIcon={<TuneRoundedIcon />}
          endIcon={
            <KeyboardArrowDownRoundedIcon
              sx={{ transform: filtersOpen ? "rotate(180deg)" : "none" }}
            />
          }
          sx={{ justifyContent: "space-between", minHeight: 44 }}
          variant="outlined"
        >
          {t("records.gameLogs.filters", { defaultValue: "Protokolle filtern" })}
        </Button>
      ) : null}
      <Stack direction={{ xs: "column", lg: "row" }} spacing={1}>
      {compact ? (
        <Collapse in={filtersOpen}>
          <Box id="game-log-filters">
            <GameLogsForm compact fields={fields} onSubmit={handleSubmit} />
          </Box>
        </Collapse>
      ) : (
        <GameLogsForm fields={fields} onSubmit={handleSubmit} />
      )}
      <Stack sx={{ flexGrow: 1 }}>
        <TableToolbar>
          <DebouncedSearchInput
            placeholder={t("records.gameLogs.searchLogs")}
            onChange={(value) => {
              table.getColumn("content")?.setFilterValue(value);
            }}
            sx={{ maxWidth: (theme) => theme.breakpoints.values.sm }}
          />
          <Box sx={{ flexGrow: 1 }} />
          <TablePagination table={table} />
          <Divider flexItem orientation="vertical" />
          <IconButton
            size="small"
            variant="contained"
            color="primary"
            sx={{
              "&.MuiIconButton-root": {
                borderRadius: 0,
              },
            }}
            onClick={handleDownload}
            aria-label={t("records.gameLogs.download")}
            title={t("records.gameLogs.download")}
          >
            <DownloadIcon />
          </IconButton>
        </TableToolbar>
        {compact ? (
          <MobileGameLogList table={table} />
        ) : (
          <LiveLogsTable
            table={table}
            config={{ actions: [], fontSize: "small", density: "dense" }}
          />
        )}
        <TableToolbar>
          <Box sx={{ flexGrow: 1 }} />
          <TablePagination table={table} />
        </TableToolbar>
      </Stack>
      </Stack>
      <GameLogPlayerActionMenu controller={playerActionMenu} />
    </Stack>
  );
};

const GameLogsForm = ({ compact = false, fields, onSubmit }) => {
  const { t } = useTranslation();
  const navigation = useNavigation();
  const server = useGlobalStore((state) => state.serverState);
  const otherServers = useGlobalStore((state) => state.servers);
  const [formFields, setFormFields] = useState({
    player_name: fields.player_name || "",
    player_id: fields.player_id || "",
    action: fields.action || "",
    limit: fields.limit || 100,
    time_sort: fields.time_sort || "desc",
    exact_player: fields.exact_player || false,
    exact_action: fields.exact_action || false,
    server_filter: fields.server_filter || "",
    from: fields.from ? dayjs(fields.from) : null,
    till: fields.till ? dayjs(fields.till) : null,
  });

  const [actionInputValue, setActionInputValue] = useState("");

  const serverOptions = useMemo(() => {
    if (!server || !otherServers) return [];

    const options = [server, ...otherServers].map((server) => ({
      label: server.name,
      value: server.server_number,
    }));

    return options;
  }, [server, otherServers]);

  const handleInputChange = (e) => {
    const { name, value, checked } = e.target;

    let newValue = value;

    if (e.target.type === "checkbox") {
      newValue = checked;
    }

    setFormFields((prev) => ({
      ...prev,
      [name]: newValue,
    }));
  };

  const handleDateChange = (name) => (value) => {
    setFormFields((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleActionChange = (event, newValue) => {
    setFormFields((prev) => ({
      ...prev,
      action: newValue?.name || "",
    }));
  };

  const handleClear = () => {
    setActionInputValue("");
    setFormFields({
      player_name: "",
      player_id: "",
      action: "",
      limit: 100,
      time_sort: "desc",
      exact_player: false,
      exact_action: false,
      server_filter: "",
      from: null,
      till: null,
    });
  };

  return (
    <Grid
      container
      sx={{ width: "100%", maxWidth: { lg: "400px" }, flexGrow: 1 }}
    >
      <Grid size={12}>
        <Form onSubmit={onSubmit}>
          <Stack
            spacing={compact ? 1.25 : 2}
            sx={{
              border: compact ? "1px solid" : 0,
              borderColor: "divider",
              bgcolor: compact ? "background.paper" : "transparent",
              p: compact ? 1.25 : 2,
            }}
          >
            <TextField
              fullWidth
              label={t("records.gameLogs.playerId")}
              name="player_id"
              value={formFields.player_id}
              onChange={handleInputChange}
            />
            <Stack direction="row" alignItems="center" spacing={1}>
              <TextField
                fullWidth
                label={t("records.gameLogs.name")}
                name="player_name"
                value={formFields.player_name}
                onChange={handleInputChange}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={formFields.exact_player}
                    name="exact_player"
                    onChange={handleInputChange}
                    color="primary"
                  />
                }
                label={t("records.gameLogs.exact")}
                labelPlacement="end"
              />
            </Stack>

            <Stack direction="row" alignItems="center" spacing={1}>
              <Autocomplete
                openText={t("common.openOptions")}
                closeText={t("common.closeOptions")}
                clearText={t("common.clearSelection")}
                noOptionsText={t("common.noResults")}
                aria-labelledby="action_label"
                fullWidth
                freeSolo
                options={actionOptions}
                getOptionLabel={(option) => option.name}
                renderOption={(props, option) => {
                  const { key, ...optionProps } = props;
                  return (
                    <Box key={option.name} component="li" {...optionProps}>
                      {logActions[option.name]} {option.name}
                    </Box>
                  )
                }}
                value={actionOptions.find((o) => o.name === formFields.action) || null}
                onChange={handleActionChange}
                inputValue={actionInputValue}
                onInputChange={(event, newValue) => {
                  setActionInputValue(newValue);
                }}
                renderInput={(params) => (
                  <TextField name="action" {...params} label={t("records.gameLogs.action")} />
                )}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={formFields.exact_action}
                    name="exact_action"
                    onChange={handleInputChange}
                    color="primary"
                  />
                }
                label={t("records.gameLogs.exact")}
                labelPlacement="end"
              />
            </Stack>

            <FormControl fullWidth>
              <InputLabel id="server_filter_label">{t("records.gameLogs.server")}</InputLabel>
              <Select
                labelId="server_filter_label"
                name="server_filter"
                value={formFields.server_filter}
                onChange={handleInputChange}
                label={t("records.gameLogs.server")}
              >
                <MenuItem value={0}>{t("records.gameLogs.allServers")}</MenuItem>
                {serverOptions.map((option) => (
                  <MenuItem key={option.value} value={option.value}>
                    {option.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>

            <TextField
              fullWidth
                label={t("records.gameLogs.limit")}
              name="limit"
              type="number"
              value={formFields.limit}
              onChange={handleInputChange}
            />

            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <DesktopDateTimePicker
                localeText={{ openDatePickerDialogue: () => t("common.chooseDate") }}
                value={formFields?.from}
                label={t("records.gameLogs.from")}
                name="from"
                onChange={handleDateChange("from")}
                format="YYYY/MM/DD HH:mm"
                ampm={false}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </LocalizationProvider>

            <LocalizationProvider dateAdapter={AdapterDayjs}>
              <DesktopDateTimePicker
                localeText={{ openDatePickerDialogue: () => t("common.chooseDate") }}
                label={t("records.gameLogs.until")}
                name="till"
                onChange={handleDateChange("till")}
                format="YYYY/MM/DD HH:mm"
                ampm={false}
                value={formFields?.till}
                slotProps={{ textField: { fullWidth: true } }}
              />
            </LocalizationProvider>

            <FormControl fullWidth>
              <InputLabel id="time_sort_label">{t("records.gameLogs.sort")}</InputLabel>
              <Select
                labelId="time_sort_label"
                name="time_sort"
                value={formFields.time_sort}
                onChange={handleInputChange}
              >
                <MenuItem value={"desc"}>{t("records.gameLogs.newest")}</MenuItem>
                <MenuItem value={"asc"}>{t("records.gameLogs.oldest")}</MenuItem>
              </Select>
            </FormControl>

            <Button
              onClick={handleClear}
              variant="outlined"
              color="error"
              size="large"
            >
              {t("records.gameLogs.clear")}
            </Button>

            <Button
              fullWidth
              variant="contained"
              color="primary"
              size="large"
              type="submit"
              disabled={navigation.state === "loading"}
            >
              {t("common.search")}
            </Button>
          </Stack>
        </Form>
      </Grid>
    </Grid>
  );
};

export default GameLogsPage;
