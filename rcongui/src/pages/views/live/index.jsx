import {
  useCallback,
  useEffect,
  useLayoutEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { cmd } from "@/utils/fetchUtils";
import { getColumns as getPlayersColumns } from "./players-columns";
import { extractPlayers, extractTeamState } from "@/utils/extractPlayers";
import { useLoaderData } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import PlayersTable from "./players-table";
import LogsTable from "./logs-table";
import { getLogsColumns } from "./logs-columns";
import {
  useLogsSearchStore,
  useLogsTableStore,
} from "@/stores/table-config";
import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import { normalizePlayerProfile } from "@/utils/lib";
import {
  getCoreRowModel,
  getExpandedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import InfoPanel from "./info-panel";
import { Box, IconButton, Stack, Tooltip, Typography } from "@mui/material";
import KeyboardArrowDownIcon from "@mui/icons-material/KeyboardArrowDown";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import DisbandSquadDialog from "@/features/player-action/DisbandSquad";
import MessageAllDialog from "@/features/player-action/MessageAll";
import { useTranslation } from "react-i18next";
import { getActiveBanStatus } from "./active-ban";
import { useGlobalStore } from "@/stores/global-state";
import { LiveCommandBar } from "./live-workspace";
import { ActionMenu } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { LiveBalanceCard } from "./live-balance-card";
import { LiveViewSettings, useLiveViewPreferences } from "./live-view-settings";
import { getPlayerColumnVisibility } from "./player-table-preferences.mjs";

const interval = 15 * 1000;
const UNASSIGNED = "unassigned";
const SPLIT_MIN_CONTENT_WIDTH = 1120;
const ONLINE_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: true,
});

// Keep route navigation immediate. React Query owns the single log request and
// renders the existing loading state instead of blocking navigation and then
// immediately repeating the request with the user's persisted filters.
export const loader = () => ({ initialLogsView: undefined });

const Live = () => {
  const { t } = useTranslation();
  const { initialLogsView } = useLoaderData();
  const liveViewSettings = useLiveViewPreferences();
  const [displaySettingsOpen, setDisplaySettingsOpen] = useState(false);
  const [displaySection, setDisplaySection] = useState("status");
  const openDisplaySettings = (section) => {
    setDisplaySection(section);
    setDisplaySettingsOpen(true);
  };
  const gameState = useGlobalStore((state) => state.gameState);
  const factionByTeam = useMemo(
    () => ({
      allies: gameState?.current_map?.map?.allies?.name ?? "allies",
      axis: gameState?.current_map?.map?.axis?.name ?? "axis",
      unassigned: "unknown",
    }),
    [
      gameState?.current_map?.map?.allies?.name,
      gameState?.current_map?.map?.axis?.name,
    ]
  );
  const playersColumns = useMemo(() => {
    const baseColumns = getPlayersColumns(t, factionByTeam);
    const detailsColumn = {
      id: "details",
      header: null,
      cell: ({ row, table }) => {
        const isExpanded = row.getIsExpanded();
        const label = isExpanded
          ? t("views.live.hidePlayerDetails", {
              defaultValue: `Details zu ${row.original.name} schließen`,
              name: row.original.name,
            })
          : t("views.live.showPlayerDetails", {
              defaultValue: `Details zu ${row.original.name} anzeigen`,
              name: row.original.name,
            });

        return (
          <Tooltip arrow title={label}>
            <IconButton
              aria-controls={`live-player-details-${row.id}`}
              aria-expanded={isExpanded}
              aria-label={label}
              onClick={() =>
                table.setExpanded(isExpanded ? {} : { [row.id]: true })
              }
              size="small"
              sx={{ p: 0.25 }}
            >
              {isExpanded ? (
                <KeyboardArrowDownIcon fontSize="small" />
              ) : (
                <KeyboardArrowRightIcon fontSize="small" />
              )}
            </IconButton>
          </Tooltip>
        );
      },
      meta: {
        variant: "icon",
        sticky: "left",
        stickyOffset: "2.25rem",
      },
    };

    const leadingColumnIds = ["select", "team", "unit", "player_summary"];
    const columnsById = new Map(
      baseColumns.map((column) => [column.id, column])
    );
    const orderedColumns = [
      ...leadingColumnIds.map((id) => columnsById.get(id)).filter(Boolean),
      ...baseColumns.filter((column) => !leadingColumnIds.includes(column.id)),
    ];

    return [orderedColumns[0], detailsColumn, ...orderedColumns.slice(1)];
  }, [factionByTeam, t]);
  const logsColumns = useMemo(() => getLogsColumns(t), [t]);
  const workspaceRef = useRef(null);
  const [contentWidth, setContentWidth] = useState(null);
  // Every visit starts in the operator-focused split workspace. Switching to
  // the player or log focus remains possible for the current page session.
  const [layoutMode, setLayoutMode] = useState("split");
  const [playerActionMenu, setPlayerActionMenu] = useState({
    anchorEl: null,
    player: null,
  });
  const openPlayerActionMenu = useCallback((anchorEl, player) => {
    setPlayerActionMenu({ anchorEl, player });
  }, []);
  const setPlayerActionMenuAnchor = useCallback((anchorEl) => {
    setPlayerActionMenu((current) => ({ ...current, anchorEl }));
  }, []);

  useLayoutEffect(() => {
    const workspace = workspaceRef.current;
    if (!workspace) return undefined;

    const updateContentWidth = (width) => {
      const nextWidth = Math.round(width);
      if (nextWidth <= 0) return;
      setContentWidth((previousWidth) =>
        previousWidth === nextWidth ? previousWidth : nextWidth
      );
    };

    updateContentWidth(workspace.getBoundingClientRect().width);

    if (typeof ResizeObserver === "undefined") {
      const handleWindowResize = () =>
        updateContentWidth(workspace.getBoundingClientRect().width);
      window.addEventListener("resize", handleWindowResize);
      return () => window.removeEventListener("resize", handleWindowResize);
    }

    const resizeObserver = new ResizeObserver(([entry]) => {
      updateContentWidth(entry.contentRect.width);
    });
    resizeObserver.observe(workspace);
    return () => resizeObserver.disconnect();
  }, []);

  const splitAvailable =
    contentWidth !== null && contentWidth >= SPLIT_MIN_CONTENT_WIDTH;

  const { data: teamData, isFetching: isTeamFetching } = useQuery({
    ...teamsLiveQueryOptions,
    staleTime: 5 * 1000,
    refetchInterval: 10 * 1000,
  });

  const playersData = useMemo(() => {
    if (!teamData) return [];
    return extractPlayers(teamData).map((player) => {
      const normalizedPlayer = {
        ...player,
        profile: normalizePlayerProfile(player.profile),
      };
      return {
        ...normalizedPlayer,
        activeBanStatus: getActiveBanStatus(normalizedPlayer),
      };
    });
  }, [teamData]);

  const logsSearchParams = useLogsSearchStore();

  const { data: logsView, isFetching: isLogsFetching } = useQuery({
    queryKey: [
      "logs",
      "live",
      {
        end: logsSearchParams.limit,
        filter_action: logsSearchParams.enabled ? logsSearchParams.actions : [],
        filter_player: logsSearchParams.enabled ? logsSearchParams.players : [],
        inclusive_filter: logsSearchParams.inclusive_filter,
      },
    ],
    queryFn: () =>
      cmd.GET_LIVE_LOGS({
        payload: {
          end: logsSearchParams.limit,
          filter_action: logsSearchParams.enabled
            ? logsSearchParams.actions
            : [],
          filter_player: logsSearchParams.enabled
            ? logsSearchParams.players
            : [],
          inclusive_filter: logsSearchParams.inclusive_filter,
        },
      }),
    select: (response) => response.result,
    initialData: initialLogsView,
    refetchInterval: interval,
  });

  const gameData = useMemo(() => {
    if (gameState && teamData) {
      return {
        ...gameState,
        allies: {
          ...extractTeamState(teamData?.allies ?? {}),
          ...(teamData?.allies ?? {}),
        },
        axis: {
          ...extractTeamState(teamData?.axis ?? {}),
          ...(teamData?.axis ?? {}),
        },
        [UNASSIGNED]: {
          ...extractTeamState(teamData?.[UNASSIGNED] ?? {}),
          ...(teamData?.[UNASSIGNED] ?? {}),
        },
      };
    }
    return null;
  }, [gameState, teamData]);

  const [playersSorting, setPlayersSorting] = useState([
    { id: "time", desc: true },
  ]);
  const [playersRowSelection, setPlayersRowSelection] = useState({});
  const [playersExpanded, setPlayersExpanded] = useState({});
  const [playersColumnFilters, setPlayersColumnFilters] = useState([]);
  const playersTableConfig = liveViewSettings.preferences.players_table;
  const playersColumnVisibility = useMemo(
    () => getPlayerColumnVisibility(playersTableConfig),
    [playersTableConfig]
  );

  const playersTable = useReactTable({
    data: playersData,
    columns: playersColumns,
    onSortingChange: setPlayersSorting,
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getCoreRowModel: getCoreRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getRowCanExpand: () => true,
    onExpandedChange: setPlayersExpanded,
    onRowSelectionChange: setPlayersRowSelection,
    onColumnFiltersChange: setPlayersColumnFilters,
    getRowId: (row) => row.player_id,
    meta: {
      openPlayerActionMenu,
      activePlayerActionId: playerActionMenu.anchorEl
        ? playerActionMenu.player?.player_id
        : null,
    },
    state: {
      sorting: playersSorting,
      rowSelection: playersRowSelection,
      expanded: playersExpanded,
      columnFilters: playersColumnFilters,
      columnVisibility: playersColumnVisibility,
    },
  });

  useEffect(() => {
    const onlineIds = new Set(playersData.map((player) => player.player_id));
    setPlayersExpanded((current) => {
      const [expandedId] = Object.keys(current).filter((id) => current[id]);
      if (!expandedId || onlineIds.has(expandedId)) return current;
      return {};
    });
  }, [playersData]);

  const [logsFiltering, setLogsFiltering] = useState([]);
  const logsTableConfig = useLogsTableStore();
  const setLogsTableConfig = useLogsTableStore((state) => state.setConfig);
  const setPagination = useLogsTableStore((state) => state.setPagination);
  const logsColumnVisibility = logsTableConfig.columnVisibility;

  const logsTable = useReactTable({
    data: logsView?.logs ?? [],
    columns: logsColumns,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onColumnFiltersChange: setLogsFiltering,
    onColumnVisibilityChange: (updater) => {
      const next =
        typeof updater === "function" ? updater(logsColumnVisibility) : updater;
      setLogsTableConfig((prev) => ({ ...prev, columnVisibility: next }));
    },
    onPaginationChange: (updater) => {
      const next =
        typeof updater === "function"
          ? updater(logsTableConfig.pagination)
          : updater;
      setPagination(next);
    },
    autoResetPageIndex: false,
    state: {
      columnFilters: logsFiltering,
      columnVisibility: logsColumnVisibility,
      pagination: logsTableConfig.pagination,
    },
  });

  const selectedPlayers = useMemo(
    () => playersTable.getSelectedRowModel().rows.map((row) => row.original),
    [playersRowSelection, playersTable]
  );

  const effectiveLayout =
    !splitAvailable && layoutMode === "split" ? "players" : layoutMode;
  const showPlayers = effectiveLayout !== "logs";
  const showLogs = effectiveLayout !== "players";

  const handleToggleLogsExpanded = () => {
    setLayoutMode((currentMode) => {
      if (currentMode !== "logs") return "logs";
      return splitAvailable ? "split" : "players";
    });
  };

  const handleStatusFilter = ({ columnId, value }) => {
    setLayoutMode("players");

    const currentFilters = playersTable.getState().columnFilters;
    const isAlreadyActive =
      currentFilters.length === 1 &&
      currentFilters[0].id === columnId &&
      JSON.stringify(currentFilters[0].value) === JSON.stringify(value);

    playersTable.resetColumnFilters();
    if (!isAlreadyActive) {
      playersTable.getColumn(columnId)?.setFilterValue(value);
    }
  };

  return (
    <Box
      ref={workspaceRef}
      data-testid="live-operations"
      sx={(theme) => ({
        minWidth: 0,
        "& .MuiButton-root, & .MuiIconButton-root, & .MuiToggleButton-root": {
          minHeight: 36,
        },
        [theme.breakpoints.down("lg")]: {
          "& .MuiButton-root, & .MuiIconButton-root, & .MuiToggleButton-root": {
            minWidth: 44,
            minHeight: 44,
          },
          "& .MuiInputBase-root": { minHeight: 44 },
        },
      })}
    >
      <LiveCommandBar
        layoutMode={effectiveLayout}
        onLayoutModeChange={setLayoutMode}
        splitDisabled={!splitAvailable}
        settingsControl={
          <LiveViewSettings
            key={liveViewSettings.userName}
            settings={liveViewSettings}
            open={displaySettingsOpen}
            onOpen={openDisplaySettings}
            onClose={() => setDisplaySettingsOpen(false)}
            section={displaySection}
            onSectionChange={setDisplaySection}
          />
        }
      />

      <InfoPanel
        gameData={gameData}
        playersData={playersData}
        onFilter={handleStatusFilter}
        activeFilters={playersColumnFilters}
        visibility={liveViewSettings.preferences.cards}
      />

      <LiveBalanceCard teams={teamData} settings={liveViewSettings} />

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        spacing={1}
        sx={{ mb: 1 }}
      >
        <Typography variant="caption" sx={{ color: "text.secondary" }}>
          {t("views.live.serverActions")}
        </Typography>
        <Stack direction="row" alignItems="center" spacing={1}>
          <MessageAllDialog />
          <DisbandSquadDialog />
        </Stack>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns:
            showPlayers && showLogs
              ? "minmax(0, 72fr) minmax(360px, 28fr)"
              : "minmax(0, 1fr)",
          gap: 1,
          alignItems: "start",
          minWidth: 0,
        }}
      >
        {showPlayers ? (
          <PlayersTable
            table={playersTable}
            teamData={teamData}
            selectedPlayers={selectedPlayers}
            isFetching={isTeamFetching}
            tableConfig={playersTableConfig}
            onConfigure={() => openDisplaySettings("players")}
            settingsBusy={liveViewSettings.mutation.isPending}
          />
        ) : null}

        {showLogs ? (
          <Box
            data-testid="live-logs-rail"
            sx={{ alignSelf: "stretch", minWidth: 0 }}
          >
            <LogsTable
              table={logsTable}
              logsViewData={logsView}
              isFetching={isLogsFetching}
              isExpanded={effectiveLayout === "logs"}
              onToggleExpanded={handleToggleLogsExpanded}
              viewportSticky={effectiveLayout === "split"}
            />
          </Box>
        ) : null}
      </Box>

      {playerActionMenu.player ? (
        <ActionMenu
          actions={ONLINE_PLAYER_ACTIONS}
          recipients={playerActionMenu.player}
          anchorEl={playerActionMenu.anchorEl}
          setAnchorEl={setPlayerActionMenuAnchor}
          menuId="live-player-row-actions-menu"
        />
      ) : null}
    </Box>
  );
};

export default Live;
