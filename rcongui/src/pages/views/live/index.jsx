import { useLayoutEffect, useMemo, useRef, useState } from "react";
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
  usePlayersTableStore,
  useLogsTableStore,
} from "@/stores/table-config";
import { teamsLiveQueryOptions } from "@/queries/teams-live-query";
import { normalizePlayerProfile } from "@/utils/lib";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import InfoPanel from "./info-panel";
import { Box, Stack, Typography } from "@mui/material";
import DisbandSquadDialog from "@/features/player-action/DisbandSquad";
import MessageAllDialog from "@/features/player-action/MessageAll";
import { useTranslation } from "react-i18next";
import { getActiveBanStatus } from "./active-ban";
import { useGlobalStore } from "@/stores/global-state";
import { LiveCommandBar } from "./live-workspace";

const interval = 15 * 1000;
const UNASSIGNED = "unassigned";
const SPLIT_MIN_CONTENT_WIDTH = 1120;

const PLAYER_COLUMN_IDS = [
  "select",
  "player_summary",
  "assignment",
  "performance_summary",
  "status_summary",
  "team",
  "unit",
  "role",
  "level",
  "kills",
  "kpm",
  "team_kills",
  "combat",
  "offense",
  "defense",
  "support",
  "vehicle_kills",
  "vehicles_destroyed",
  "actions",
  "platform",
  "clan-tag",
  "name",
  "player_id",
  "active_ban",
  "warnings",
  "watchlist",
  "country",
  "vip",
  "flags",
  "visits",
  "time",
];

const OPERATIONS_COLUMNS = new Set([
  "select",
  "player_summary",
  "assignment",
  "performance_summary",
  "status_summary",
  "time",
  "actions",
]);

const COMPOSITE_COLUMNS = new Set([
  "assignment",
  "performance_summary",
  "status_summary",
]);

const getPresetVisibility = (preset, customVisibility) => {
  if (preset === "custom") return customVisibility;
  return PLAYER_COLUMN_IDS.reduce((visibility, id) => {
    if (preset === "operations") visibility[id] = OPERATIONS_COLUMNS.has(id);
    if (preset === "all")
      visibility[id] =
        id !== "player_id" && id !== "name" && !COMPOSITE_COLUMNS.has(id);
    return visibility;
  }, {});
};

export const loader = async () => {
  if (import.meta.env.MODE === "fake") {
    return {
      initialLogsView: {
        result: { actions: [], players: [], logs: [] },
      },
    };
  }
  const response = await cmd.GET_LIVE_LOGS({
    payload: {
      end: 250,
      filter_action: [],
      filter_player: [],
      inclusive_filter: true,
    },
  });

  return { initialLogsView: response };
};

const Live = () => {
  const { t } = useTranslation();
  const { initialLogsView } = useLoaderData();
  const playersColumns = useMemo(() => getPlayersColumns(t), [t]);
  const logsColumns = useMemo(() => getLogsColumns(t), [t]);
  const workspaceRef = useRef(null);
  const [contentWidth, setContentWidth] = useState(null);
  // Every visit starts in the operator-focused split workspace. Switching to
  // the player or log focus remains possible for the current page session.
  const [layoutMode, setLayoutMode] = useState("split");
  const [playerPreset, setPlayerPreset] = useState("operations");

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

  const gameState = useGlobalStore((state) => state.gameState);

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
  const [playersColumnFilters, setPlayersColumnFilters] = useState([]);
  const playersTableConfig = usePlayersTableStore();
  const setPlayersTableConfig = usePlayersTableStore(
    (state) => state.setConfig
  );
  const playersColumnVisibility = useMemo(
    () =>
      getPresetVisibility(playerPreset, playersTableConfig.columnVisibility),
    [playerPreset, playersTableConfig.columnVisibility]
  );

  const handlePlayersColumnVisibilityChange = (columnId, isVisible) => {
    const columnVisibility = {
      ...playersColumnVisibility,
      [columnId]: isVisible,
    };

    setPlayerPreset("custom");
    setPlayersTableConfig((prev) => ({ ...prev, columnVisibility }));
  };

  const playersTable = useReactTable({
    data: playersData,
    columns: playersColumns,
    onSortingChange: setPlayersSorting,
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getCoreRowModel: getCoreRowModel(),
    onRowSelectionChange: setPlayersRowSelection,
    onColumnFiltersChange: setPlayersColumnFilters,
    onColumnVisibilityChange: (updater) => {
      const next =
        typeof updater === "function"
          ? updater(playersColumnVisibility)
          : updater;
      setPlayerPreset("custom");
      setPlayersTableConfig((prev) => ({ ...prev, columnVisibility: next }));
    },
    getRowId: (row) => row.player_id,
    state: {
      sorting: playersSorting,
      rowSelection: playersRowSelection,
      columnFilters: playersColumnFilters,
      columnVisibility: playersColumnVisibility,
    },
  });

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
    playersTable.resetColumnFilters();
    playersTable.getColumn(columnId)?.setFilterValue(value);
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
        gameData={gameData}
        playerCount={playersData.length}
        isFetching={isTeamFetching || isLogsFetching}
        layoutMode={effectiveLayout}
        onLayoutModeChange={setLayoutMode}
        splitDisabled={!splitAvailable}
      />

      <InfoPanel
        gameData={gameData}
        playersData={playersData}
        onFilter={handleStatusFilter}
      />

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
            onColumnVisibilityChange={handlePlayersColumnVisibilityChange}
            isFetching={isTeamFetching}
            preset={playerPreset}
            onPresetChange={setPlayerPreset}
          />
        ) : null}

        {showLogs ? (
          <LogsTable
            table={logsTable}
            logsViewData={logsView}
            isFetching={isLogsFetching}
            isExpanded={effectiveLayout === "logs"}
            onToggleExpanded={handleToggleLogsExpanded}
          />
        ) : null}
      </Box>

    </Box>
  );
};

export default Live;
