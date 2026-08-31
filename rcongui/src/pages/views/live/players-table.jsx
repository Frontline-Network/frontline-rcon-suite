import Table from "@/components/table/Table";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import {
  Box,
  Button,
  Collapse,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { memo, useCallback, useMemo, useState } from "react";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import SettingsIcon from "@mui/icons-material/Settings";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import UnfoldMoreIcon from "@mui/icons-material/UnfoldMore";
import UnfoldLessIcon from "@mui/icons-material/UnfoldLess";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import { TeamSelectionToolbar } from "./TeamSelectionToolbar";
import {
  ActionButton,
  ActionMenuButton,
} from "@/features/player-action/ActionMenu";
import {
  generatePlayerActions,
  kickAction,
  messageAction,
  punishAction,
} from "@/features/player-action/actions";
import TableColumnSelection from "@/components/table/TableColumnSelection";
import { TableToolbar } from "@/components/table/TableToolbar";
import { usePlayersTableStore } from "@/stores/table-config";
import { useTranslation } from "react-i18next";
import { getTeamkillRisk } from "@/utils/teamkill-risk.mjs";
import PlayerDetailPanel from "./player-detail-panel";
import PlayerTableLayout from "./player-table-layout";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import MobilePlayerList from "./mobile-player-list";

const getPlayerRowProps = (row) => ({
  "data-player-row": "true",
  "data-expanded": String(row.getIsExpanded()),
  sx: (theme) => ({
    bgcolor: "background.paper",
    borderBottom: `1px solid ${
      theme.vars
        ? `rgba(${theme.vars.palette.text.primaryChannel} / 0.12)`
        : theme.palette.divider
    }`,
    "& > td": {
      bgcolor: "background.paper",
    },
    "&:hover > td": {
      bgcolor: "action.hover",
    },
    ...(row.getIsSelected() && {
      borderBottomColor: "primary.dark",
      "& > td": {
        bgcolor: "action.selected",
      },
    }),
    ...(row.getIsExpanded() && {
      borderBottomColor: "primary.main",
      "& > td": {
        bgcolor: "action.selected",
      },
      "& > td:first-of-type": {
        bgcolor: "action.selected",
        boxShadow: `inset 3px 0 0 ${theme.palette.primary.main}`,
      },
      "& [aria-expanded='true']": {
        color: "primary.main",
      },
    }),
  }),
});

const PlayersTable = ({
  table,
  teamData,
  selectedPlayers,
  onColumnVisibilityChange,
  isFetching,
  preset,
  onPresetChange,
}) => {
  const { t } = useTranslation();
  const theme = useTheme();
  // The mobile command deck is capability-based rather than phone-only. A
  // narrow tablet does not have enough room for the desktop operations table
  // either, so it receives the same touch-native roster and action sheet.
  const isCompactOperations = useMediaQuery(theme.breakpoints.down("md"));
  const { openWithId } = usePlayerSidebar();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const [advancedFiltersOpen, setAdvancedFiltersOpen] = useState(false);
  const activeColumnFilters = table.getState().columnFilters;
  const teamFilter = table.getColumn("team")?.getFilterValue();
  const teamkillFilter = table.getColumn("team_kills")?.getFilterValue();
  const quickFilter = ["axis", "allies", "unassigned"].includes(teamFilter)
    ? teamFilter
    : teamkillFilter === "risk"
    ? "risk"
    : activeColumnFilters.length === 0
    ? "all"
    : null;

  const columnLabels = useMemo(
    () => ({
      select: t("views.table.selection"),
      details: t("common.details", { defaultValue: "Details" }),
      player_summary: t("views.table.playerSummary"),
      performance_summary: t("views.live.performance"),
      status_summary: t("views.live.status"),
      team: t("views.table.team"),
      unit: t("views.table.unit"),
      role: t("views.table.role"),
      level: t("views.table.level"),
      kills: t("views.table.kills"),
      deaths: t("views.table.deaths"),
      kpm: t("views.table.killsPerMinute"),
      team_kills: t("views.table.teamKills"),
      combat: t("views.table.combat"),
      offense: t("views.table.offense"),
      defense: t("views.table.defense"),
      support: t("views.table.support"),
      vehicle_kills: t("views.table.vehicleKills"),
      vehicles_destroyed: t("views.table.vehiclesDestroyed"),
      actions: t("common.actions"),
      platform: t("views.table.platform"),
      "clan-tag": t("views.table.clanTag"),
      name: t("views.table.nameOnly"),
      player_id: t("views.table.playerId"),
      active_ban: t("views.table.activeBan"),
      warnings: t("views.table.warnings"),
      watchlist: t("views.table.watchlist"),
      country: t("views.table.country"),
      vip: t("views.table.vip"),
      flags: t("views.table.flags"),
      visits: t("views.table.visits"),
      time: t("views.table.currentPlaytime"),
    }),
    [t]
  );

  const tableConfig = usePlayersTableStore();
  const setConfig = usePlayersTableStore((state) => state.setConfig);
  const setExpandedView = usePlayersTableStore(
    (state) => state.setExpandedView
  );

  const counts = useMemo(() => {
    const rows = table.options.data ?? [];
    return rows.reduce(
      (acc, player) => {
        acc.all += 1;
        if (player.team === "axis") acc.axis += 1;
        if (player.team === "allies") acc.allies += 1;
        if (player.team === "unassigned") acc.lobby += 1;
        if (getTeamkillRisk(player).count > 0) acc.risk += 1;
        return acc;
      },
      { all: 0, axis: 0, allies: 0, lobby: 0, risk: 0 }
    );
  }, [table.options.data]);

  const handleQuickFilter = (_event, value) => {
    const nextValue = value ?? "all";

    if (nextValue === "all") {
      table.resetColumnFilters();
      return;
    }

    table.getColumn("team")?.setFilterValue(undefined);
    table.getColumn("team_kills")?.setFilterValue(undefined);
    if (["axis", "allies", "unassigned"].includes(nextValue)) {
      table.getColumn("team")?.setFilterValue(nextValue);
    }
    if (nextValue === "risk") {
      table.getColumn("team_kills")?.setFilterValue("risk");
    }
  };

  const renderPlayerDetails = useCallback(
    ({ row }) => (
      <Box
        id={`live-player-details-${row.id}`}
        role="region"
        aria-label={t("views.live.playerDetails", {
          defaultValue: `Details zu ${row.original.name}`,
          name: row.original.name,
        })}
        onKeyDown={(event) => {
          if (event.key !== "Escape") return;
          event.stopPropagation();
          table.setExpanded({});
          window.requestAnimationFrame(() => {
            document
              .querySelector(`[aria-controls="live-player-details-${row.id}"]`)
              ?.focus();
          });
        }}
      >
        <PlayerDetailPanel
          player={row.original}
          onOpenProfile={(player) => openWithId(player.player_id)}
        />
      </Box>
    ),
    [openWithId, t, table]
  );

  return (
    <Box
      component="section"
      data-testid="live-players-panel"
      sx={(theme) => ({
        border: `1px solid ${theme.palette.divider}`,
        bgcolor: "background.paper",
        minWidth: 0,
      })}
    >
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        sx={{
          px: 1.25,
          py: { xs: 0.75, md: 1 },
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Stack direction="row" alignItems="center" spacing={0.75}>
          <Typography variant="h6">{t("views.live.players")}</Typography>
          <Typography variant="caption" sx={{ color: "text.secondary" }}>
            · {counts.all} {t("views.live.online")}
          </Typography>
          <Box
            sx={{
              width: 7,
              height: 7,
              borderRadius: "50%",
              bgcolor: "success.main",
            }}
          />
        </Stack>
        <Select
          value={preset}
          onChange={(event) => onPresetChange(event.target.value)}
          size="small"
          inputProps={{ "aria-label": t("views.live.columnPreset") }}
          sx={{ display: { xs: "none", md: "inline-flex" }, minWidth: 150 }}
        >
          <MenuItem value="operations">
            {t("views.live.operationsPreset")}
          </MenuItem>
          <MenuItem value="custom">{t("views.live.customPreset")}</MenuItem>
          <MenuItem value="all">{t("views.live.allColumnsPreset")}</MenuItem>
        </Select>
      </Stack>

      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        gap={1}
        sx={{
          p: { xs: 0.75, md: 1 },
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box
          sx={{ minWidth: { xs: "100%", md: 220 }, flex: { md: "1 1 280px" } }}
        >
          <DebouncedSearchInput
            placeholder={t("views.team.searchPlayer")}
            initialValue={
              table.getColumn("player_summary")?.getFilterValue() ?? ""
            }
            onChange={(value) =>
              table.getColumn("player_summary")?.setFilterValue(value)
            }
          />
        </Box>
        <FormControl
          size="small"
          sx={{ display: { xs: "flex", md: "none" }, width: "100%" }}
        >
          <InputLabel id="live-mobile-quick-filter-label">
            {t("views.live.quickFilters")}
          </InputLabel>
          <Select
            labelId="live-mobile-quick-filter-label"
            value={quickFilter ?? "custom"}
            label={t("views.live.quickFilters")}
            onChange={(event) => handleQuickFilter(null, event.target.value)}
          >
            {quickFilter === null ? (
              <MenuItem value="custom" disabled>
                {t("views.live.customPreset")}
              </MenuItem>
            ) : null}
            <MenuItem value="all">
              {t("common.all")} · {counts.all}
            </MenuItem>
            <MenuItem value="axis">
              {t("views.team.axis")} · {counts.axis}
            </MenuItem>
            <MenuItem value="allies">
              {t("views.team.allies")} · {counts.allies}
            </MenuItem>
            <MenuItem value="unassigned">
              {t("views.live.lobby")} · {counts.lobby}
            </MenuItem>
            <MenuItem value="risk">
              {t("views.live.suspicious")} · {counts.risk}
            </MenuItem>
          </Select>
        </FormControl>
        <Box
          sx={{
            display: { xs: "none", md: "block" },
            maxWidth: "100%",
          }}
        >
          <ToggleButtonGroup
            value={quickFilter}
            exclusive
            onChange={handleQuickFilter}
            size="small"
            aria-label={t("views.live.quickFilters")}
            sx={{
              display: "inline-flex",
              flexWrap: "wrap",
              gap: "1px",
              minWidth: 0,
              "& .MuiToggleButtonGroup-grouped": {
                border: "1px solid",
                borderColor: "divider",
                borderRadius: 0,
                flex: "0 0 auto",
                m: 0,
                minHeight: 44,
                whiteSpace: "nowrap",
              },
            }}
          >
            <ToggleButton value="all">
              {t("common.all")} {counts.all}
            </ToggleButton>
            <ToggleButton value="axis">
              {t("views.team.axis")} {counts.axis}
            </ToggleButton>
            <ToggleButton value="allies">
              {t("views.team.allies")} {counts.allies}
            </ToggleButton>
            <ToggleButton value="unassigned">
              {t("views.live.lobby")} {counts.lobby}
            </ToggleButton>
            <ToggleButton value="risk">
              {t("views.live.suspicious")} {counts.risk}
            </ToggleButton>
          </ToggleButtonGroup>
        </Box>
      </Stack>

      <TableToolbar
        sx={{
          borderLeft: 0,
          borderRight: 0,
          minHeight: { xs: 44, md: 48 },
          px: 0.5,
          py: { xs: 0, md: 0.5 },
        }}
      >
        <Button
          size="small"
          startIcon={<TuneOutlinedIcon />}
          onClick={() => setAdvancedFiltersOpen((open) => !open)}
          aria-expanded={advancedFiltersOpen}
        >
          {t("views.live.selectionFilters")}
        </Button>
        <Box sx={{ flexGrow: 1 }} />
        <IconButton
          size="small"
          aria-label={
            tableConfig.expandedView ? t("common.collapse") : t("common.expand")
          }
          onClick={() => setExpandedView(!tableConfig.expandedView)}
          sx={{ display: { xs: "none", md: "inline-flex" } }}
        >
          {tableConfig.expandedView ? <UnfoldLessIcon /> : <UnfoldMoreIcon />}
        </IconButton>
        <Box sx={{ display: { xs: "none", md: "contents" } }}>
          <TableColumnSelection
            table={table}
            onColumnVisibilityChange={onColumnVisibilityChange}
            getColumnLabel={(column) => columnLabels[column.id]}
          />
        </Box>
        <IconButton
          size="small"
          aria-label={t("common.settings")}
          onClick={() => setTableConfigDrawerOpen(true)}
        >
          <SettingsIcon />
        </IconButton>
      </TableToolbar>

      <Collapse in={advancedFiltersOpen}>
        <Box sx={{ borderBottom: "1px solid", borderColor: "divider" }}>
          {teamData ? (
            <TeamSelectionToolbar table={table} teamData={teamData} />
          ) : null}
        </Box>
      </Collapse>

      {isCompactOperations ? (
        <MobilePlayerList
          table={table}
          isFetching={isFetching}
          onOpenProfile={(player) => openWithId(player.player_id)}
        />
      ) : (
        <PlayerTableLayout data-testid="live-player-table-layout">
          <Table
            table={table}
            config={tableConfig}
            isFetching={isFetching}
            showTopScrollbar
            topScrollbarLabel={t("views.live.horizontalTableScroll")}
            rowProps={getPlayerRowProps}
            renderSubComponent={renderPlayerDetails}
          />
        </PlayerTableLayout>
      )}

      {selectedPlayers.length > 0 ? (
        <Stack
          data-testid="live-batch-actions"
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "stretch", sm: "center" }}
          gap={1}
          sx={(theme) => ({
            position: "sticky",
            bottom: 0,
            zIndex: 6,
            borderTop: `1px solid ${theme.palette.primary.dark}`,
            bgcolor: "background.paper",
            boxShadow: theme.shadows[1],
            px: 1.25,
            py: 1,
          })}
        >
          <Typography variant="subtitle2">
            {t("views.live.playersSelected", { count: selectedPlayers.length })}
          </Typography>
          <Button
            size="small"
            color="inherit"
            onClick={() => table.resetRowSelection()}
          >
            {t("views.live.clearSelection")}
          </Button>
          <Box sx={{ flexGrow: 1 }} />
          <ActionButton action={messageAction} recipients={selectedPlayers} />
          <ActionButton action={punishAction} recipients={selectedPlayers} />
          <ActionButton action={kickAction} recipients={selectedPlayers} />
          <ActionMenuButton
            actions={generatePlayerActions({
              multiAction: true,
              onlineAction: true,
            })}
            recipients={selectedPlayers}
            orientation="horizontal"
            disableRipple
            renderButton={(buttonProps) => (
              <Button
                {...buttonProps}
                size="small"
                variant="contained"
                endIcon={<MoreHorizIcon />}
              >
                {t("views.live.moreActions")}
              </Button>
            )}
          />
        </Stack>
      ) : null}

      <TableConfigDrawer
        name={t("views.live.players")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          setConfig(config);
        }}
        config={tableConfig}
      />
    </Box>
  );
};

export default memo(PlayersTable);
