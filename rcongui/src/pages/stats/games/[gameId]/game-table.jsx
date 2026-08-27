import Table from "@/components/table/Table";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import {
  ButtonBase,
  Collapse,
  Divider,
  IconButton,
  Paper,
  Stack,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { useState } from "react";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import SettingsIcon from "@mui/icons-material/Settings";
import DownloadIcon from "@mui/icons-material/Download";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { TablePagination } from "@/components/table/TablePagination";
import { TableToolbar } from "@/components/table/TableToolbar";
import { Box, Typography } from "@mui/material";
import { downloadGame } from "@/features/download-game";
import { useGameDetailsTableStore } from "@/stores/table-config";
import { useTranslation } from "react-i18next";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";

const renderSubComponent = ({ row }, t, playerNames) => {
  // Create a custom component that renders the player's stats
  const statCategories = {
    combat: [
      {
        label: t("stats.gameDetails.metrics.kills"),
        value: row.original.kills,
      },
      { label: t("stats.gameDetails.deaths"), value: row.original.deaths },
      {
        label: "K/D",
        value: (row.original.kills / Math.max(row.original.deaths, 1)).toFixed(
          2
        ),
      },
      {
        label: t("stats.gameDetails.killsPerMinute"),
        value: row.original.kills_per_minute?.toFixed(2),
      },
    ],
    teamwork: [
      {
        label: t("stats.gameDetails.teamKills"),
        value: row.original.teamkills,
      },
      {
        label: t("stats.gameDetails.teamKillStreak"),
        value: row.original.teamkills_streak,
      },
      {
        label: t("stats.gameDetails.deathsByTeamKill"),
        value: row.original.deaths_by_tk,
      },
      {
        label: t("stats.gameDetails.teamDeathStreak"),
        value: row.original.deaths_by_tk_streak,
      },
    ],
    offense: [
      {
        label: t("stats.gameDetails.offensiveKills"),
        value: row.original.offensive_kills,
      },
      {
        label: t("stats.gameDetails.defensiveKills"),
        value: row.original.defensive_kills,
      },
    ],
  };

  const StatSection = ({ title, stats }) => (
    <Box>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        {title}
      </Typography>
      {stats.map(({ label, value }) => (
        <Box
          key={label}
          sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}
        >
          <Typography variant="body2">{label}:</Typography>
          <Typography variant="body2" sx={{ ml: 2 }}>
            {value}
          </Typography>
        </Box>
      ))}
    </Box>
  );

  const players = Object.entries(row.original.most_killed || {}).map(
    ([playerId, kills]) => (
      <Box
        key={playerId}
        sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}
      >
        <Typography variant="body2">
          {playerNames.get(playerId) || playerId}:
        </Typography>
        <Typography variant="body2" sx={{ ml: 2 }}>
          {kills}
        </Typography>
      </Box>
    )
  );

  const weapons = Object.entries(row.original.weapons || {}).map(
    ([weapon, kills]) => (
      <Box
        key={weapon}
        sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}
      >
        <Typography variant="body2">{weapon}:</Typography>
        <Typography variant="body2" sx={{ ml: 2 }}>
          {kills}
        </Typography>
      </Box>
    )
  );

  const deathsByWeapon = Object.entries(
    row.original.death_by_weapons || {}
  ).map(([weapon, deaths]) => (
    <Box
      key={weapon}
      sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}
    >
      <Typography variant="body2">{weapon}:</Typography>
      <Typography variant="body2" sx={{ ml: 2 }}>
        {deaths}
      </Typography>
    </Box>
  ));

  const deathsByPlayer = Object.entries(row.original.death_by || {}).map(
    ([playerId, deaths]) => (
      <Box
        key={playerId}
        sx={{ display: "flex", justifyContent: "space-between", py: 0.5 }}
      >
        <Typography variant="body2">
          {playerNames.get(playerId) || playerId}:
        </Typography>
        <Typography variant="body2" sx={{ ml: 2 }}>
          {deaths}
        </Typography>
      </Box>
    )
  );

  return (
    <Box
      sx={{
        p: 2,
        maxWidth: { xs: (theme) => theme.breakpoints.values.sm, lg: "100%" },
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          gap: { xs: 2, md: 4 },
          mb: 4,
        }}
      >
        <StatSection
          title={t("stats.gameDetails.combatStats")}
          stats={statCategories.combat}
        />
        <StatSection
          title={t("stats.gameDetails.teamworkStats")}
          stats={statCategories.teamwork}
        />
        <StatSection
          title={t("stats.gameDetails.objectiveStats")}
          stats={statCategories.offense}
        />
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(4, 1fr)" },
          gap: { xs: 2, md: 4 },
        }}
      >
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("stats.gameDetails.killsByPlayer")}
          </Typography>
          {players}
        </Box>
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("stats.gameDetails.killsByWeapon")}
          </Typography>
          {weapons}
        </Box>
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("stats.gameDetails.deathsByWeapon")}
          </Typography>
          {deathsByWeapon}
        </Box>
        <Box>
          <Typography variant="subtitle2" sx={{ mb: 1 }}>
            {t("stats.gameDetails.deathsByPlayer")}
          </Typography>
          {deathsByPlayer}
        </Box>
      </Box>
    </Box>
  );
};

const PlayersTable = ({ table, selectedPlayers }) => {
  const { t } = useTranslation();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const tableConfig = useGameDetailsTableStore();
  const setConfig = useGameDetailsTableStore((state) => state.setConfig);
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const [expandedPlayerId, setExpandedPlayerId] = useState(null);
  const playerNames = new Map(
    table.options.data.map((player) => [player.player_id, player.player])
  );

  const handleTableConfigClick = () => {
    setTableConfigDrawerOpen((prev) => !prev);
  };

  return (
    <div>
      <TableToolbar sx={compact ? { flexWrap: "wrap", gap: 1 } : undefined}>
        {!compact && (
          <ActionMenuButton
            actions={generatePlayerActions({
              multiAction: true,
              onlineAction: false,
            })}
            disabled={
              !table.getIsSomePageRowsSelected() &&
              !table.getIsAllRowsSelected()
            }
            recipients={selectedPlayers}
            orientation="horizontal"
            disableRipple={true}
            sx={{
              p: "1px 4px",
              height: "100%",
            }}
          />
        )}
        <DebouncedSearchInput
          placeholder={t("stats.liveSessions.searchPlayer")}
          initialValue={table.getColumn("name")?.getFilterValue() ?? ""}
          onChange={(value) => {
            table.getColumn("name")?.setFilterValue(value);
          }}
          sx={{
            maxWidth: compact ? "none" : 230,
            flex: compact ? "1 1 100%" : undefined,
          }}
        />
        {!compact && <TablePagination table={table} />}
        {!compact && <Divider flexItem orientation="vertical" />}
        {!compact && (
          <IconButton
            size="small"
            sx={{ p: 0.5, borderRadius: 0 }}
            aria-label={t("stats.gameDetails.download")}
            onClick={() =>
              downloadGame(table.options.data, [
                t("stats.gameDetails.csv.playerId"),
                t("stats.gameDetails.csv.name"),
                t("stats.gameDetails.metrics.kills"),
                t("stats.gameDetails.deaths"),
                "K/D",
                t("stats.gameDetails.csv.maxKillStreak"),
                t("stats.gameDetails.csv.killsPerMinute"),
                t("stats.gameDetails.csv.deathsPerMinute"),
                t("stats.gameDetails.csv.maxDeathStreak"),
                t("stats.gameDetails.csv.maxTeamKillStreak"),
                t("stats.gameDetails.csv.deathByTeamKill"),
                t("stats.gameDetails.csv.deathByTeamKillStreak"),
                t("stats.gameDetails.csv.longestLife"),
                t("stats.gameDetails.csv.shortestLife"),
                t("stats.gameDetails.csv.nemesis"),
                t("stats.gameDetails.csv.victim"),
                t("stats.gameDetails.csv.combat"),
                t("stats.gameDetails.csv.support"),
                t("stats.gameDetails.csv.defense"),
                t("stats.gameDetails.csv.offense"),
                t("stats.gameDetails.csv.weapons"),
                t("stats.gameDetails.csv.deathByWeapons"),
              ])
            }
          >
            <DownloadIcon sx={{ fontSize: 16 }} />
          </IconButton>
        )}
        {!compact && (
          <IconButton
            size="small"
            sx={{ p: 0.5, borderRadius: 0 }}
            aria-label={t("common.settings")}
            onClick={handleTableConfigClick}
          >
            <SettingsIcon sx={{ fontSize: 16 }} />
          </IconButton>
        )}
      </TableToolbar>
      {compact ? (
        <Stack
          component="section"
          aria-label={t("stats.liveGame.playerStatistics")}
          gap={0}
          sx={{ mt: 1 }}
        >
          {table.getRowModel().rows.map((row) => {
            const player = row.original;
            const expanded = expandedPlayerId === player.player_id;
            return (
              <Paper
                key={player.player_id}
                variant="outlined"
                sx={{
                  borderRadius: 0,
                  borderBottomWidth: expanded ? 1 : 0,
                  "&:last-child": { borderBottomWidth: 1 },
                }}
              >
                <Stack
                  direction="row"
                  alignItems="center"
                  sx={{ minHeight: 52, pr: 0.5 }}
                >
                  <ButtonBase
                    aria-expanded={expanded}
                    aria-label={`${player.player} ${
                      expanded ? t("common.close") : t("common.open")
                    }`}
                    onClick={() =>
                      setExpandedPlayerId(expanded ? null : player.player_id)
                    }
                    sx={{
                      display: "grid",
                      gridTemplateColumns: "32px minmax(0, 1fr) 42px 42px 36px",
                      alignItems: "center",
                      flex: 1,
                      minWidth: 0,
                      minHeight: 52,
                      textAlign: "left",
                    }}
                  >
                    <ChevronRightIcon
                      sx={{
                        transform: expanded ? "rotate(90deg)" : "none",
                        transition: "transform 120ms",
                      }}
                    />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography noWrap sx={{ fontWeight: 800 }}>
                        {player.player}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {player.steaminfo?.country || t("common.unknown")}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                      >
                        K
                      </Typography>
                      <Typography sx={{ fontWeight: 800 }}>
                        {player.kills ?? 0}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                      >
                        T
                      </Typography>
                      <Typography sx={{ fontWeight: 800 }}>
                        {player.deaths ?? 0}
                      </Typography>
                    </Box>
                    <Box sx={{ textAlign: "center" }}>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        display="block"
                      >
                        TK
                      </Typography>
                      <Typography
                        color={
                          (player.teamkills ?? 0) > 0
                            ? "error.main"
                            : "text.primary"
                        }
                        sx={{ fontWeight: 800 }}
                      >
                        {player.teamkills ?? 0}
                      </Typography>
                    </Box>
                  </ButtonBase>
                  <IconButton
                    aria-controls={
                      table.options.meta?.activePlayerActionId ===
                      player.player_id
                        ? "completed-game-player-actions-menu"
                        : undefined
                    }
                    aria-expanded={
                      table.options.meta?.activePlayerActionId ===
                      player.player_id
                        ? "true"
                        : undefined
                    }
                    aria-haspopup="true"
                    aria-label={t("actions.menu")}
                    data-testid="completed-game-player-action-trigger"
                    disableRipple
                    onClick={(event) =>
                      table.options.meta?.openPlayerActionMenu?.(
                        event.currentTarget,
                        {
                          name: player.player,
                          player_id: player.player_id,
                        }
                      )
                    }
                    sx={{ minWidth: 44, minHeight: 44 }}
                  >
                    <MoreHorizIcon />
                  </IconButton>
                </Stack>
                <Collapse in={expanded} unmountOnExit>
                  <Box
                    sx={{
                      borderTop: "1px solid",
                      borderColor: "divider",
                      p: 1.25,
                      bgcolor: "background.default",
                    }}
                  >
                    {renderSubComponent({ row }, t, playerNames)}
                  </Box>
                </Collapse>
              </Paper>
            );
          })}
        </Stack>
      ) : (
        <Table
          table={table}
          config={tableConfig}
          renderSubComponent={(props) =>
            renderSubComponent(props, t, playerNames)
          }
        />
      )}
      <TableConfigDrawer
        name={t("stats.gameDetails.title")}
        open={tableConfigDrawerOpen}
        onClose={(config) => {
          setTableConfigDrawerOpen(false);
          setConfig(config);
        }}
        config={tableConfig}
      />
    </div>
  );
};

export default PlayersTable;
