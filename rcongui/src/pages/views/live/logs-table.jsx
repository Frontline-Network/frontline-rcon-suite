import {
  Box,
  Button,
  Collapse,
  Divider,
  IconButton,
  LinearProgress,
  List,
  ListItem,
  ListItemText,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import { Fragment, memo, useEffect, useState } from "react";
import { useLogsTableStore, useLogsSearchStore } from "@/stores/table-config";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import SettingsIcon from "@mui/icons-material/Settings";
import { logActions as _logActions } from "@/utils/lib";
import { LogActionSelectionMenu } from "@/components/table/selection/LogActionSelectionMenu";
import { LogPlayerSelectionMenu } from "@/components/table/selection/LogPlayerSelectionMenu";
import { LogActionQuerySelectionMenu } from "@/components/table/selection/LogActionQuerySelectionMenu";
import DeleteIcon from "@mui/icons-material/Delete";
import { TablePagination } from "@/components/table/TablePagination";
import { TableToolbar } from "@/components/table/TableToolbar";
import TableAddons from "@/components/table/TableAddons";
import { LogActionHighlightMenu } from "@/components/table/selection/LogActionHighlightMenu";
import { LogTeamSelectionMenu } from "@/components/table/selection/LogTeamSelectionMenu";
import { useTranslation } from "react-i18next";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import OpenInFullOutlinedIcon from "@mui/icons-material/OpenInFullOutlined";
import CloseFullscreenOutlinedIcon from "@mui/icons-material/CloseFullscreenOutlined";
import CompactLogsList from "./compact-logs-list";

const logActions = Object.entries(_logActions).reduce((acc, [name]) => {
  acc[name] = false;
  return acc;
}, {});

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

const updateActionSelection = (action) => (prev) => {
  const isToggled = prev.actions.includes(action);
  const actions = isToggled
    ? prev.actions.filter((aAction) => aAction !== action)
    : prev.actions.concat(action);
  return {
    ...prev,
    actions,
  };
};

const updateFilterActionSelection = (action) => (prev) => {
  const isToggled = prev.filters.actions.selected.includes(action);
  const actions = isToggled
    ? prev.filters.actions.selected.filter((aAction) => aAction !== action)
    : prev.filters.actions.selected.concat(action);
  return {
    ...prev,
    filters: {
      ...prev.filters,
      actions: {
        ...prev.filters.actions,
        selected: actions,
      },
    },
  };
};

function LogsTable({
  table,
  logsViewData,
  isFetching,
  isExpanded = false,
  onToggleExpanded,
  viewportSticky = false,
}) {
  const { t } = useTranslation();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);

  const tableConfig = useLogsTableStore();
  const searchParams = useLogsSearchStore();
  const setParamsFilterEnabled = useLogsSearchStore(
    (state) => state.setEnabled
  );

  const [playerOptions, setPlayerOptions] = useState({});

  const [selectedTeams, setSelectedTeams] = useState([]);

  const handleFilterChange = (fn) => {
    table.setPageIndex(0);
    fn();
  };

  const handleTableConfigClick = () => {
    // toggle config drawer
    setTableConfigDrawerOpen((prev) => !prev);
  };

  const handleClientActionFilterChange = (actionName) => {
    tableConfig.setConfig(updateFilterActionSelection(actionName));
  };

  const handleClientActionFilterToggle = () => {
    handleFilterChange(() => {
      tableConfig.setConfig((prev) => ({
        ...prev,
        filters: {
          ...prev.filters,
          actions: {
            ...prev.filters.actions,
            enabled: !prev.filters.actions.enabled,
          },
        },
      }));
    });
  };

  const handleQuickFilter = (_event, value) => {
    if (!value) return;
    const selected = QUICK_FILTER_ACTIONS[value] ?? [];
    handleFilterChange(() => {
      tableConfig.setConfig((prev) => ({
        ...prev,
        filters: {
          ...prev.filters,
          actions: {
            enabled: selected.length > 0,
            selected,
          },
        },
      }));
    });
  };

  const handleClientPlayerFilterChange = (playerName) => {
    handleFilterChange(() => {
      setPlayerOptions((prev) => ({
        ...prev,
        [playerName]: !prev[playerName],
      }));
    });
  };

  const handleQueryActionParamSelect = (action) => {
    handleFilterChange(() => {
      searchParams.setSearchParams(updateActionSelection(action));
    });
  };

  const handleHighlightActionSelect = (action) => {
    tableConfig.setConfig(updateActionSelection(action));
  };

  const handleClientHighlightActionToggle = () => {
    tableConfig.setConfig((prev) => ({
      ...prev,
      highlighted: !prev.highlighted,
    }));
  };

  const handleQueryLimitInputBlur = (event) => {
    const [min, max] = [10, 100_000];
    const inputValue = Number(event.target.value);
    const limit = inputValue < min ? min : inputValue > max ? max : inputValue;
    handleFilterChange(() => {
      searchParams.setSearchParams((prev) => ({
        ...prev,
        limit,
      }));
    });
  };

  const handleQueryInclusiveFilterChange = (e, mode) => {
    if (mode === null) return; // the active value was selected
    console.log(mode);
    handleFilterChange(() => {
      searchParams.setSearchParams((prev) => ({
        ...prev,
        inclusive_filter: mode === "exclusive" ? false : true,
      }));
    });
  };

  useEffect(() => {
    const incomingPlayers =
      logsViewData?.players?.reduce((acc, player) => {
        acc[player] = false;
        return acc;
      }, {}) ?? {};
    setPlayerOptions((prev) => {
      for (const [name, selected] of Object.entries(prev)) {
        if (name in incomingPlayers) {
          incomingPlayers[name] = selected;
        }
      }
      return incomingPlayers;
    });
  }, [logsViewData?.players]);

  useEffect(() => {
    if (tableConfig.filters.actions.enabled) {
      table
        .getColumn("action")
        ?.setFilterValue(tableConfig.filters.actions.selected);
    } else {
      table.getColumn("action")?.setFilterValue(null);
    }
  }, [
    tableConfig.filters.actions.selected,
    tableConfig.filters.actions.enabled,
  ]);

  useEffect(() => {
    const selectedPlayers = Object.entries(playerOptions)
      .filter(([_, selected]) => selected)
      .map(([name]) => name);
    table.getColumn("player_name_1")?.setFilterValue(selectedPlayers);
    table.getColumn("player_name_2")?.setFilterValue(selectedPlayers);
  }, [playerOptions]);

  const highlightedActionOptions = Object.entries(logActions).reduce(
    (acc, [name]) => {
      acc[name] = tableConfig.actions.includes(name);
      return acc;
    },
    {}
  );

  const filterActionOptions = Object.entries(logActions).reduce(
    (acc, [name]) => {
      acc[name] = tableConfig.filters.actions.selected.includes(name);
      return acc;
    },
    {}
  );

  const searchQueryParamsOptions = Object.entries(logActions).reduce(
    (acc, [name]) => {
      acc[name] = searchParams.actions.includes(name);
      return acc;
    },
    {}
  );

  const handleTeamSelect = (team) => {
    handleFilterChange(() => {
      setSelectedTeams((prev) => {
        const isSelected = prev.includes(team);
        if (isSelected) {
          return prev.filter((t) => t !== team);
        }
        return [...prev, team];
      });
    });
  };

  useEffect(() => {
    table.getColumn("team")?.setFilterValue(selectedTeams);
  }, [selectedTeams]);

  return (
    <Box
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
            handleFilterChange(() => {
              table.getColumn("message")?.setFilterValue(value);
            });
          }}
        />
      </Stack>

      <TableToolbar sx={{ borderLeft: 0, borderRight: 0, px: 0.5 }}>
        <Button
          size="small"
          startIcon={<TuneOutlinedIcon />}
          onClick={() => setAdvancedFiltersOpen((open) => !open)}
          aria-expanded={advancedFiltersOpen}
          aria-controls="live-log-advanced-filters"
        >
          {t("views.live.advancedFilters")}
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <IconButton
          size="small"
          aria-label={t("common.settings")}
          onClick={handleTableConfigClick}
        >
          <SettingsIcon />
        </IconButton>
      </TableToolbar>

      <Collapse
        in={advancedFiltersOpen}
        id="live-log-advanced-filters"
        role="region"
        aria-label={t("views.live.advancedFilters")}
        sx={{
          overflowX: "hidden",
          "& .MuiStack-root, & .MuiButtonGroup-root": {
            flexWrap: "wrap",
            maxWidth: "100%",
          },
        }}
      >
        <TableAddons>
          <LogActionSelectionMenu
            actionOptions={filterActionOptions}
            onActionSelect={handleClientActionFilterChange}
            toggleValue={tableConfig.filters.actions.enabled}
            onToggle={handleClientActionFilterToggle}
          />
          <LogTeamSelectionMenu
            selectedTeams={selectedTeams}
            onTeamSelect={handleTeamSelect}
          />
          <LogPlayerSelectionMenu
            actionOptions={playerOptions}
            onActionSelect={handleClientPlayerFilterChange}
          />
          <LogActionHighlightMenu
            actionOptions={highlightedActionOptions}
            onActionSelect={handleHighlightActionSelect}
            toggleValue={tableConfig.highlighted}
            onToggle={handleClientHighlightActionToggle}
          />
        </TableAddons>
      </Collapse>

      <Stack
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
        />
        <TableToolbar
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
      <TableConfigDrawer
        name={t("views.live.logs")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          tableConfig.setConfig(config);
        }}
        config={tableConfig}
      >
        <Typography sx={{ fontWeight: 500 }}>
          {t("views.live.persistentLogFilters")}
        </Typography>
        <Divider flexItem />
        <div>
          <Typography
            sx={{
              mb: 1,
              fontSize: "0.85rem",
              textTransform: "uppercase",
              letterSpacing: 1.5,
            }}
          >
            {t("views.live.filterMode")}
          </Typography>
          <ToggleButtonGroup
            value={searchParams.inclusive_filter ? "inclusive" : "exclusive"}
            exclusive
            onChange={handleQueryInclusiveFilterChange}
            aria-label={t("views.live.filterMode")}
            fullWidth
          >
            <ToggleButton
              value="inclusive"
              aria-label={t("views.live.inclusiveFilters")}
            >
              {t("views.live.inclusive")}
            </ToggleButton>
            <ToggleButton
              value="exclusive"
              aria-label={t("views.live.exclusiveFilters")}
            >
              {t("views.live.exclusive")}
            </ToggleButton>
          </ToggleButtonGroup>
        </div>
        <div>
          <Typography
            sx={{
              mb: 1,
              fontSize: "0.85rem",
              textTransform: "uppercase",
              letterSpacing: 1.5,
            }}
          >
            {t("views.live.filterActions")}
          </Typography>
          <LogActionQuerySelectionMenu
            actionOptions={searchQueryParamsOptions}
            selectedActions={searchParams.actions}
            onActionSelect={handleQueryActionParamSelect}
            toggleValue={searchParams.enabled}
            onToggle={setParamsFilterEnabled}
          />
          <List dense={true} disablePadding={true}>
            {searchParams.actions.map((action, i) => (
              <Fragment key={action}>
                {i !== 0 && <Divider component="li" />}
                <ListItem
                  disableGutters={true}
                  secondaryAction={
                    <IconButton
                      edge="end"
                      aria-label={t("common.delete")}
                      onClick={() => handleQueryActionParamSelect(action)}
                    >
                      <DeleteIcon />
                    </IconButton>
                  }
                >
                  <ListItemText
                    primary={`${_logActions[action]} - ${action}`}
                  />
                </ListItem>
              </Fragment>
            ))}
            {searchParams.actions.length === 0 && (
              <ListItem disableGutters={true}>
                <ListItemText primary={t("views.live.noActionFilters")} />
              </ListItem>
            )}
          </List>
        </div>
        <div>
          <Typography
            sx={{
              mb: 1,
              fontSize: "0.85rem",
              textTransform: "uppercase",
              letterSpacing: 1.5,
            }}
          >
            {t("views.live.logQueryLimit")}
          </Typography>
          <TextField
            fullWidth
            defaultValue={searchParams.limit}
            onBlur={handleQueryLimitInputBlur}
            placeholder={t("views.live.logQueryLimit")}
            type="number"
            size="small"
          />
        </div>
      </TableConfigDrawer>
    </Box>
  );
}

export default memo(LogsTable);
