import {
  Box,
  Button,
  IconButton,
  LinearProgress,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { memo, useEffect, useState } from "react";
import { useLogsTableStore, useLogsSearchStore } from "@/stores/table-config";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import { TablePagination } from "@/components/table/TablePagination";
import { TableToolbar } from "@/components/table/TableToolbar";
import { useTranslation } from "react-i18next";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import OpenInFullOutlinedIcon from "@mui/icons-material/OpenInFullOutlined";
import CloseFullscreenOutlinedIcon from "@mui/icons-material/CloseFullscreenOutlined";
import CompactLogsList from "./compact-logs-list";
import { LogFiltersDialog } from "./log-filters-dialog";

const QUICK_FILTER_ACTIONS = {
  all: [],
  admin: ["ADMIN"],
  chat: ["CHAT"],
  teamkills: ["TEAM KILL"],
  kills: ["KILL"],
  match: ["MATCH"],
};

const getQuickFilterValue = (filters) => {
  if (!filters?.enabled) return "all";
  const selected = [...(filters.selected ?? [])].sort();
  return (
    Object.entries(QUICK_FILTER_ACTIONS).find(([, actions]) => {
      const expected = [...actions].sort();
      return (
        selected.length === expected.length &&
        selected.every((action, index) => action === expected[index])
      );
    })?.[0] ?? null
  );
};

function LogsTable({
  table,
  logsViewData,
  isFetching,
  isExpanded = false,
  onToggleExpanded,
  viewportSticky = false,
  displaySettings,
  onConfigure,
  settingsBusy,
}) {
  const { t } = useTranslation();
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const tableConfig = useLogsTableStore();
  const searchParams = useLogsSearchStore();
  const [playerOptions, setPlayerOptions] = useState({});
  const [selectedTeams, setSelectedTeams] = useState([]);

  const handleQuickFilter = (_event, value) => {
    if (!value) return;
    const selected = QUICK_FILTER_ACTIONS[value] ?? [];
    table.setPageIndex(0);
    tableConfig.setConfig((prev) => ({
      ...prev,
      filters: {
        ...prev.filters,
        actions: { enabled: selected.length > 0, selected },
      },
    }));
  };

  const applyFilters = (draft) => {
    table.setPageIndex(0);
    tableConfig.setConfig((prev) => ({
      ...prev,
      filters: {
        ...prev.filters,
        actions: { enabled: draft.enabled, selected: draft.actions },
      },
      highlighted: draft.highlighted,
      actions: draft.highlightActions,
    }));
    setSelectedTeams(draft.teams);
    setPlayerOptions((prev) =>
      Object.fromEntries(
        [...new Set([...Object.keys(prev), ...draft.players])].map((name) => [
          name,
          draft.players.includes(name),
        ])
      )
    );
    searchParams.setSearchParams(draft.query);
    setAdvancedFiltersOpen(false);
  };

  useEffect(() => {
    setPlayerOptions((prev) =>
      Object.fromEntries(
        [
          ...new Set([
            ...(logsViewData?.players ?? []),
            ...Object.keys(prev).filter((name) => prev[name]),
          ]),
        ].map((name) => [name, prev[name] ?? false])
      )
    );
  }, [logsViewData?.players]);

  useEffect(() => {
    table
      .getColumn("action")
      ?.setFilterValue(
        tableConfig.filters.actions.enabled
          ? tableConfig.filters.actions.selected
          : null
      );
  }, [
    table,
    tableConfig.filters.actions.enabled,
    tableConfig.filters.actions.selected,
  ]);
  useEffect(() => {
    const selected = Object.keys(playerOptions).filter(
      (name) => playerOptions[name]
    );
    table.getColumn("player_name_1")?.setFilterValue(selected);
    table.getColumn("player_name_2")?.setFilterValue(selected);
  }, [table, playerOptions]);
  useEffect(() => {
    table.getColumn("team")?.setFilterValue(selectedTeams);
  }, [table, selectedTeams]);

  return (
    <Box data-theme-surface="panel"
      component="section"
      data-testid="live-logs-panel"
      sx={(theme) => ({
        border: `1px solid ${theme.palette.divider}`,
        bgcolor: "background.paper",
        display: "flex",
        flexDirection: "column",
        fontWeight: 300,
        minWidth: 0,
        position: "relative",
        "& > :not(.live-log-content)": { flexShrink: 0 },
        // Keep the complete live protocol typographically calm and uniform.
        // Several event renderers and MUI controls otherwise reintroduce
        // medium or bold labels of their own.
        "& .MuiTypography-root, & .MuiButton-root, & .MuiToggleButton-root, & .MuiInputBase-input, & .MuiFormLabel-root, & .MuiFormControlLabel-label, & .MuiListItemText-root, & button, & a, & span":
          {
            fontWeight: "300 !important",
          },
        ...(viewportSticky
          ? {
              boxSizing: "border-box",
              height: "calc(100dvh - 16px)",
              maxHeight: "calc(100dvh - 16px)",
              minHeight: 0,
              overflow: "hidden",
              position: "sticky",
              top: theme.spacing(1),
              [theme.breakpoints.down("lg")]: {
                height: `calc(100dvh - ${theme.spacing(18)})`,
                maxHeight: `calc(100dvh - ${theme.spacing(18)})`,
                top: theme.spacing(17),
              },
            }
          : {}),
      })}
    >
      {isFetching ? (
        <LinearProgress
          sx={{
            position: "absolute",
            inset: "0 0 auto",
            zIndex: 9,
            height: 2,
          }}
        />
      ) : null}
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        sx={{
          px: 1.25,
          py: 1,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Typography variant="h6">{t("views.live.logs")}</Typography>
          <Box
            sx={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              bgcolor: "success.main",
            }}
          />
          <Typography variant="caption" sx={{ color: "success.light" }}>
            {t("views.live.liveNow")}
          </Typography>
        </Stack>
        <Stack direction="row" alignItems="center" spacing={0.5}>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            {table.getFilteredRowModel().rows.length} {t("views.live.events")}
          </Typography>
          {onToggleExpanded ? (
            <IconButton
              size="small"
              aria-label={
                isExpanded
                  ? t("views.live.restoreSplitView")
                  : t("views.live.maximizeLogs")
              }
              title={
                isExpanded
                  ? t("views.live.restoreSplitView")
                  : t("views.live.maximizeLogs")
              }
              onClick={onToggleExpanded}
            >
              {isExpanded ? (
                <CloseFullscreenOutlinedIcon fontSize="small" />
              ) : (
                <OpenInFullOutlinedIcon fontSize="small" />
              )}
            </IconButton>
          ) : null}
        </Stack>
      </Stack>

      <Stack
        spacing={1}
        sx={{ p: 1, borderBottom: "1px solid", borderColor: "divider" }}
      >
        <ToggleButtonGroup
          value={getQuickFilterValue(tableConfig.filters.actions)}
          exclusive
          onChange={handleQuickFilter}
          size="small"
          aria-label={t("views.live.eventFilters")}
          sx={{
            display: "flex",
            flexWrap: "wrap",
            gap: 0.5,
            "& .MuiToggleButton-root": {
              flex: "1 1 auto",
              minWidth: 72,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
            },
          }}
        >
          <ToggleButton value="all">{t("common.all")}</ToggleButton>
          <ToggleButton value="admin">{t("views.live.admin")}</ToggleButton>
          <ToggleButton value="chat">{t("views.live.chat")}</ToggleButton>
          <ToggleButton value="teamkills">
            {t("views.live.teamkills")}
          </ToggleButton>
          <ToggleButton value="kills">{t("views.live.kills")}</ToggleButton>
          <ToggleButton value="match">{t("views.live.match")}</ToggleButton>
        </ToggleButtonGroup>
        <DebouncedSearchInput
          placeholder={t("views.live.searchLogs")}
          onChange={(value) => {
            table.setPageIndex(0);
            table.getColumn("message")?.setFilterValue(value);
          }}
        />
      </Stack>

      <TableToolbar sx={{ borderLeft: 0, borderRight: 0, px: 0.5 }}>
        <Button
          size="small"
          startIcon={<TuneOutlinedIcon />}
          onClick={() => setAdvancedFiltersOpen(true)}
          aria-haspopup="dialog"
        >
          {t("views.live.advancedFilters")}
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <Button
          size="small"
          onClick={onConfigure}
          disabled={settingsBusy}
          sx={{ minHeight: 44 }}
        >
          {t("views.live.configureLogDisplay")}
        </Button>
      </TableToolbar>

      <Stack
        className="live-log-content"
        direction="column"
        spacing={0}
        sx={
          viewportSticky
            ? {
                flex: "1 1 auto",
                minHeight: 0,
                overflow: "hidden",
              }
            : undefined
        }
      >
        <CompactLogsList
          table={table}
          rows={table.getRowModel().rows}
          scrollable={viewportSticky}
          displaySettings={displaySettings}
          highlightedActions={
            tableConfig.highlighted ? tableConfig.actions : []
          }
        />
        <TableToolbar
          position="bottom"
          sx={{
            borderBottomWidth: "1px",
            borderBottomStyle: "solid",
            borderTop: "none",
            flex: "0 0 auto",
          }}
        >
          <TablePagination table={table} />
        </TableToolbar>
      </Stack>
      {advancedFiltersOpen ? (
        <LogFiltersDialog
          tableConfig={tableConfig}
          searchParams={searchParams}
          playerOptions={playerOptions}
          selectedTeams={selectedTeams}
          onApply={applyFilters}
          onClose={() => setAdvancedFiltersOpen(false)}
        />
      ) : null}
    </Box>
  );
}

export default memo(LogsTable);
