import Table from "@/components/table/Table";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import {
  Box,
  Button,
  Collapse,
  IconButton,
  MenuItem,
  Select,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { memo, useMemo, useState } from "react";
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
      player_summary: t("views.table.playerSummary"),
      assignment: t("views.live.assignment"),
      performance_summary: t("views.live.performance"),
      status_summary: t("views.live.status"),
      team: t("views.table.team"),
      unit: t("views.table.unit"),
      role: t("views.table.role"),
      level: t("views.table.level"),
      kills: t("views.table.kills"),
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
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
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
          aria-label={t("views.live.columnPreset")}
          sx={{ minWidth: 150 }}
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
        sx={{ p: 1, borderBottom: "1px solid", borderColor: "divider" }}
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
        <ToggleButtonGroup
          value={quickFilter}
          exclusive
          onChange={handleQuickFilter}
          size="small"
          aria-label={t("views.live.quickFilters")}
          sx={{
            flexWrap: "wrap",
            gap: "1px",
            maxWidth: "100%",
            "& .MuiToggleButtonGroup-grouped": {
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
              m: 0,
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
      </Stack>

      <TableToolbar sx={{ borderLeft: 0, borderRight: 0, px: 0.5 }}>
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
        >
          {tableConfig.expandedView ? <UnfoldLessIcon /> : <UnfoldMoreIcon />}
        </IconButton>
        <TableColumnSelection
          table={table}
          onColumnVisibilityChange={onColumnVisibilityChange}
          getColumnLabel={(column) => columnLabels[column.id]}
        />
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

      <Table
        table={table}
        config={tableConfig}
        isFetching={isFetching}
        showTopScrollbar
        topScrollbarLabel={t("views.live.horizontalTableScroll")}
      />

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
