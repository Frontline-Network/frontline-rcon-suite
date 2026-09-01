import { useCallback, useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  MenuItem,
  Select,
  Stack,
  Typography,
  useMediaQuery,
} from "@mui/material";
import FilterListIcon from "@mui/icons-material/FilterList";
import CloseIcon from "@mui/icons-material/Close";
import GroupIcon from "@mui/icons-material/Group";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import SettingsIcon from "@mui/icons-material/Settings";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import {
  getCoreRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";
import { teamsLiveQuery } from "@/queries/teams-live-query";
import Table from "@/components/table/Table";
import TableColumnSelection from "@/components/table/TableColumnSelection";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import PageHeader from "@/components/shared/PageHeader";
import {
  ActionMenu,
  ActionMenuButton,
} from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { useLiveSessionsTableStore } from "@/stores/table-config";
import { createLiveSessionColumns } from "./columns";
import LiveSessionInspector from "./LiveSessionInspector";
import {
  flattenLiveSessionPlayers,
  getLiveSessionRowId,
  liveSessionGlobalFilter,
} from "./live-session-utils";

const DEFAULT_COLUMN_VISIBILITY = {
  combat: false,
  offense: false,
  defense: false,
  support: false,
};

const SummaryItem = ({ label, value, color = "text.primary" }) => (
  <Box sx={{ minWidth: 92, flexShrink: 0, px: 1.25, py: 0.8 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
        display: "block",
        textTransform: "uppercase",
        letterSpacing: 0.8,
      }}
    >
      {label}
    </Typography>
    <Typography
      sx={{
        mt: 0.15,
        color,
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value}
    </Typography>
  </Box>
);

const FilterButton = ({ active, label, count, onClick, color }) => (
  <Button
    onClick={onClick}
    aria-pressed={active}
    sx={{
      position: "relative",
      minWidth: "max-content",
      flex: "0 0 auto",
      px: 1.5,
      py: 1,
      borderRadius: 0,
      whiteSpace: "nowrap",
      color: active ? color || "text.primary" : "text.secondary",
      "&::after": active
        ? {
            content: '""',
            position: "absolute",
            left: 0,
            right: 0,
            bottom: 0,
            height: 2,
            bgcolor: color || "primary.main",
          }
        : undefined,
    }}
  >
    {label}
    <Box
      component="span"
      sx={{ ml: 0.75, color: active ? "inherit" : "text.disabled" }}
    >
      {count}
    </Box>
  </Button>
);

export default function LiveSessionsPage() {
  const { t } = useTranslation();
  const wideInspector = useMediaQuery("(min-width:1280px)");
  const { data, isLoading, isFetching, error, dataUpdatedAt } = teamsLiveQuery({
    refetchInterval: 15 * 1000,
  });
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
  const columns = useMemo(() => createLiveSessionColumns(t), [t]);
  const singlePlayerActions = useMemo(
    () =>
      generatePlayerActions({
        multiAction: false,
        onlineAction: true,
      }),
    []
  );
  const tableConfig = useLiveSessionsTableStore();
  const setConfig = useLiveSessionsTableStore((state) => state.setConfig);
  const setColumnVisibility = useLiveSessionsTableStore(
    (state) => state.setColumnVisibility
  );
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const [mobileInspectorOpen, setMobileInspectorOpen] = useState(false);
  const [activeFilter, setActiveFilter] = useState("all");
  const [globalFilter, setGlobalFilter] = useState("");
  const [sorting, setSorting] = useState([{ id: "kdr", desc: true }]);
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);

  const players = useMemo(() => flattenLiveSessionPlayers(data), [data]);
  const counts = useMemo(() => {
    const leaderlessSquads = new Set(
      players
        .filter((player) => player.is_leaderless_squad)
        .map((player) => player.squad_key)
    );
    return {
      all: players.length,
      allies: players.filter((player) => player.team === "allies").length,
      axis: players.filter((player) => player.team === "axis").length,
      unassigned: players.filter((player) => player.team === "unassigned")
        .length,
      leaderless: leaderlessSquads.size,
    };
  }, [players]);

  const visiblePlayers = useMemo(() => {
    if (activeFilter === "leaderless") {
      return players.filter((player) => player.is_leaderless_squad);
    }
    if (["allies", "axis", "unassigned"].includes(activeFilter)) {
      return players.filter((player) => player.team === activeFilter);
    }
    return players;
  }, [activeFilter, players]);

  const table = useReactTable({
    data: visiblePlayers,
    columns,
    getRowId: getLiveSessionRowId,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    globalFilterFn: liveSessionGlobalFilter,
    enableRowSelection: true,
    state: {
      globalFilter,
      sorting,
      columnVisibility: {
        ...DEFAULT_COLUMN_VISIBILITY,
        ...(tableConfig.columnVisibility ?? {}),
      },
    },
    onGlobalFilterChange: setGlobalFilter,
    onSortingChange: setSorting,
    initialState: { pagination: { pageSize: 16 } },
    meta: {
      openPlayerActionMenu,
      activePlayerActionId: playerActionMenu.anchorEl
        ? playerActionMenu.player?.player_id
        : null,
    },
  });

  const filteredRows = table.getFilteredRowModel().rows;
  const selectedPlayer =
    players.find(
      (player) => getLiveSessionRowId(player) === selectedPlayerId
    ) ?? null;
  const selectedRecipients = table
    .getSelectedRowModel()
    .rows.map((row) => row.original);
  const pageIndex = table.getState().pagination.pageIndex;
  const pageSize = table.getState().pagination.pageSize;
  const rangeStart = filteredRows.length ? pageIndex * pageSize + 1 : 0;
  const rangeEnd = Math.min((pageIndex + 1) * pageSize, filteredRows.length);

  useEffect(() => {
    const stillVisible = visiblePlayers.some(
      (player) => getLiveSessionRowId(player) === selectedPlayerId
    );
    if (!stillVisible) {
      setSelectedPlayerId(
        visiblePlayers[0] ? getLiveSessionRowId(visiblePlayers[0]) : null
      );
    }
  }, [selectedPlayerId, visiblePlayers]);

  useEffect(() => {
    if (wideInspector) setMobileInspectorOpen(false);
  }, [wideInspector]);

  const handlePlayerSelect = (player) => {
    setSelectedPlayerId(getLiveSessionRowId(player));
    if (!wideInspector) setMobileInspectorOpen(true);
  };

  const filterOptions = [
    ["all", t("stats.liveSessions.filters.all"), counts.all, "primary.main"],
    [
      "allies",
      t("stats.liveSessions.filters.allies"),
      counts.allies,
      "info.main",
    ],
    ["axis", t("stats.liveSessions.filters.axis"), counts.axis, "error.main"],
    [
      "unassigned",
      t("stats.liveSessions.filters.unassigned"),
      counts.unassigned,
      "text.primary",
    ],
    [
      "leaderless",
      t("stats.liveSessions.filters.leaderless"),
      counts.leaderless,
      "warning.main",
    ],
  ];

  return (
    <Stack spacing={1.25} sx={{ width: "100%", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("stats.liveSessions.eyebrow")}
        title={t("stats.liveSessions.title")}
        subtitle={t("stats.liveSessions.subtitle")}
        actions={
          <Stack direction="row" alignItems="center" spacing={1}>
            <Box
              sx={{
                width: 7,
                height: 7,
                bgcolor: error ? "error.main" : "success.main",
              }}
            />
            <Typography variant="caption" color="text.secondary">
              {error
                ? t("stats.liveSessions.connectionError")
                : t("stats.liveSessions.updatedAt", {
                    time: dataUpdatedAt
                      ? dayjs(dataUpdatedAt).format("HH:mm:ss")
                      : "–",
                  })}
            </Typography>
          </Stack>
        }
      />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            md: "minmax(260px, 1fr) minmax(180px, .55fr) auto",
          },
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            p: 0.75,
            borderRight: { md: "1px solid" },
            borderColor: "divider",
          }}
        >
          <DebouncedSearchInput
            placeholder={t("stats.liveSessions.searchPlayer")}
            initialValue={globalFilter}
            onChange={setGlobalFilter}
            sx={{ width: "100%", maxWidth: "none" }}
          />
        </Box>

        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          sx={{
            px: 1,
            py: 0.75,
            borderRight: { md: "1px solid" },
            borderColor: "divider",
          }}
        >
          <FilterListIcon sx={{ fontSize: 17, color: "text.secondary" }} />
          <FormControl fullWidth size="small">
            <Select
              value={
                sorting[0]?.id === "time"
                  ? "time"
                  : sorting[0]?.id === "kills"
                  ? "kills"
                  : sorting[0]?.id === "name"
                  ? "name"
                  : "kdr"
              }
              onChange={(event) => {
                const id = event.target.value;
                setSorting([{ id, desc: id !== "name" }]);
              }}
              inputProps={{ "aria-label": t("stats.liveSessions.sorting") }}
              sx={{ borderRadius: 0 }}
            >
              <MenuItem value="kdr">{t("stats.liveSessions.sortKdr")}</MenuItem>
              <MenuItem value="kills">
                {t("stats.liveSessions.sortKills")}
              </MenuItem>
              <MenuItem value="time">
                {t("stats.liveSessions.sortTime")}
              </MenuItem>
              <MenuItem value="name">
                {t("stats.liveSessions.sortName")}
              </MenuItem>
            </Select>
          </FormControl>
        </Stack>

        <Stack
          direction="row"
          alignItems="stretch"
          sx={{
            minWidth: 0,
            width: "100%",
            overflowX: "auto",
            scrollbarWidth: "thin",
          }}
        >
          <SummaryItem
            label={t("stats.liveSessions.summary.allies")}
            value={counts.allies}
            color="info.main"
          />
          <Divider orientation="vertical" flexItem />
          <SummaryItem
            label={t("stats.liveSessions.summary.axis")}
            value={counts.axis}
            color="error.main"
          />
          <Divider orientation="vertical" flexItem />
          <ActionMenuButton
            actions={generatePlayerActions({
              multiAction: true,
              onlineAction: true,
            })}
            recipients={selectedRecipients}
            renderButton={(props) => (
              <Button
                {...props}
                disabled={!selectedRecipients.length}
                startIcon={<GroupIcon />}
                sx={{ height: "100%", minWidth: 118, borderRadius: 0 }}
              >
                {selectedRecipients.length
                  ? t("stats.liveSessions.selected", {
                      count: selectedRecipients.length,
                    })
                  : t("stats.liveSessions.noneSelected")}
              </Button>
            )}
          />
          <Divider orientation="vertical" flexItem />
          <TableColumnSelection
            table={table}
            onColumnVisibilityChange={setColumnVisibility}
            renderButton={(props) => (
              <Button
                {...props}
                startIcon={<ViewColumnIcon />}
                sx={{ height: "100%", borderRadius: 0, px: 1.25 }}
              >
                {t("stats.liveSessions.columns")}
              </Button>
            )}
          />
          <Divider orientation="vertical" flexItem />
          <IconButton
            aria-label={t("stats.liveSessions.tableSettings")}
            onClick={() => setTableConfigDrawerOpen(true)}
            sx={{ borderRadius: 0, px: 1.25 }}
          >
            <SettingsIcon fontSize="small" />
          </IconButton>
        </Stack>
      </Box>

      <Stack
        direction="row"
        sx={{
          overflowX: "auto",
          borderBottom: "1px solid",
          borderColor: "divider",
          scrollbarWidth: "thin",
        }}
      >
        {filterOptions.map(([id, label, count, color]) => (
          <FilterButton
            key={id}
            active={activeFilter === id}
            label={label}
            count={count}
            color={color}
            onClick={() => setActiveFilter(id)}
          />
        ))}
      </Stack>

      {error && (
        <Alert severity="error" sx={{ borderRadius: 0 }}>
          {t("stats.liveSessions.loadError")}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: wideInspector
            ? "minmax(0, 1fr) minmax(320px, 350px)"
            : "minmax(0, 1fr)",
          gap: 1.25,
          alignItems: "start",
          minWidth: 0,
        }}
      >
        <Box
          sx={{
            minWidth: 0,
            "& table th, & table td": {
              px: { xs: 0.5, sm: 0.875 },
            },
          }}
        >
          <Table
            table={table}
            config={tableConfig}
            isLoading={isLoading}
            isFetching={isFetching}
            rowProps={(row) => ({
              "data-interactive": "true",
              "data-inspected": String(
                getLiveSessionRowId(row.original) === selectedPlayerId
              ),
              tabIndex: 0,
              onClick: () => handlePlayerSelect(row.original),
              onKeyDown: (event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  handlePlayerSelect(row.original);
                }
              },
            })}
          />

          <Stack
            direction={{ xs: "column", sm: "row" }}
            alignItems={{ xs: "stretch", sm: "center" }}
            justifyContent="space-between"
            gap={1}
            sx={{
              minHeight: 48,
              px: 1.25,
              py: 0.75,
              border: "1px solid",
              borderTop: 0,
              borderColor: "divider",
              bgcolor: "background.paper",
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {t("stats.liveSessions.range", {
                from: rangeStart,
                to: rangeEnd,
                total: filteredRows.length,
              })}
            </Typography>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="flex-end"
              gap={0.5}
            >
              <IconButton
                aria-label={t("common.pagination.previous")}
                onClick={() => table.previousPage()}
                disabled={!table.getCanPreviousPage()}
                size="small"
                sx={{
                  borderRadius: 0,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <KeyboardArrowLeftIcon fontSize="small" />
              </IconButton>
              <Typography
                variant="caption"
                sx={{ minWidth: 62, textAlign: "center" }}
              >
                {t("common.pagination.page", {
                  current: pageIndex + 1,
                  total: Math.max(1, table.getPageCount()),
                })}
              </Typography>
              <IconButton
                aria-label={t("common.pagination.next")}
                onClick={() => table.nextPage()}
                disabled={!table.getCanNextPage()}
                size="small"
                sx={{
                  borderRadius: 0,
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                <KeyboardArrowRightIcon fontSize="small" />
              </IconButton>
              <FormControl size="small">
                <Select
                  value={pageSize}
                  onChange={(event) =>
                    table.setPageSize(Number(event.target.value))
                  }
                  inputProps={{
                    "aria-label": t("common.pagination.pageSize"),
                  }}
                  sx={{ borderRadius: 0 }}
                >
                  {[16, 25, 50, 100].map((size) => (
                    <MenuItem key={size} value={size}>
                      {t("common.pagination.show", { count: size })}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </Stack>
          </Stack>
        </Box>

        {wideInspector && (
          <Box sx={{ position: "sticky", top: 8 }}>
            <LiveSessionInspector player={selectedPlayer} t={t} />
          </Box>
        )}
      </Box>

      <Drawer
        anchor="right"
        open={!wideInspector && mobileInspectorOpen}
        onClose={() => setMobileInspectorOpen(false)}
        PaperProps={{
          sx: {
            width: { xs: "100%", sm: 390 },
            maxWidth: "100%",
            p: 1,
            bgcolor: "background.default",
          },
        }}
      >
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="space-between"
          sx={{ mb: 1, pl: 0.5 }}
        >
          <Typography
            sx={{
              fontSize: "0.8rem",
              fontWeight: 600,
              textTransform: "uppercase",
              letterSpacing: 1,
            }}
          >
            {t("stats.liveSessions.sessionDetails")}
          </Typography>
          <IconButton
            aria-label={t("common.close")}
            onClick={() => setMobileInspectorOpen(false)}
            sx={{ borderRadius: 0 }}
          >
            <CloseIcon />
          </IconButton>
        </Stack>
        <LiveSessionInspector player={selectedPlayer} t={t} />
      </Drawer>

      <TableConfigDrawer
        name={t("stats.liveSessions.tableSettings")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          if (config) setConfig(config);
        }}
        config={tableConfig}
      />
      {playerActionMenu.player ? (
        <ActionMenu
          actions={singlePlayerActions}
          recipients={playerActionMenu.player}
          anchorEl={playerActionMenu.anchorEl}
          setAnchorEl={setPlayerActionMenuAnchor}
          menuId="live-sessions-player-actions-menu"
          withProfile
        />
      ) : null}
    </Stack>
  );
}
