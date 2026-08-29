import { useMemo, useState } from "react";
import {
  Box,
  Button,
  ButtonBase,
  Collapse,
  FormControl,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DownloadIcon from "@mui/icons-material/Download";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import SettingsIcon from "@mui/icons-material/Settings";
import ViewColumnIcon from "@mui/icons-material/ViewColumn";
import { useTranslation } from "react-i18next";

import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import Table from "@/components/table/Table";
import TableColumnSelection from "@/components/table/TableColumnSelection";
import TableConfigDrawer from "@/components/table/TableConfigDrawer";
import { TablePagination } from "@/components/table/TablePagination";
import { TableToolbar } from "@/components/table/TableToolbar";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { downloadGame } from "@/features/download-game";
import { useGameDetailsTableStore } from "@/stores/table-config";
import {
  formatRoleLabel,
  formatSquadLabel,
} from "@/pages/views/live/player-display-labels";

import {
  getHistoricalRole,
  getHistoricalSquad,
  normalizeHistoricalTeam,
} from "./game-detail-utils";

const LEDGER_BORDER = "rgba(214, 184, 112, 0.2)";

const teamLabel = (t, side) => {
  if (side === "allies") return t("views.team.allies");
  if (side === "axis") return t("views.team.axis");
  if (side === "mixed") return t("stats.gameDetails.mixedTeam");
  return t("stats.gameDetails.unknownTeam");
};

const teamColor = (side) => {
  if (side === "allies") return "info.light";
  if (side === "axis") return "error.light";
  if (side === "mixed") return "warning.light";
  return "text.secondary";
};

const csvHeaders = (t) => [
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
];

const StatSection = ({ title, stats }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography
      variant="overline"
      color="primary.main"
      sx={{ display: "block", mb: 0.75 }}
    >
      {title}
    </Typography>
    <Stack>
      {stats.map(({ label, value }) => (
        <Box
          key={label}
          sx={{
            display: "flex",
            justifyContent: "space-between",
            gap: 2,
            py: 0.45,
            borderBottom: "1px solid",
            borderColor: LEDGER_BORDER,
          }}
        >
          <Typography variant="body2" color="text.secondary">
            {label}
          </Typography>
          <Typography
            variant="body2"
            sx={{ fontVariantNumeric: "tabular-nums" }}
          >
            {value ?? "–"}
          </Typography>
        </Box>
      ))}
    </Stack>
  </Box>
);

const DetailList = ({ title, values }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography
      variant="overline"
      color="primary.main"
      sx={{ display: "block", mb: 0.75 }}
    >
      {title}
    </Typography>
    {values.length ? (
      <Stack>
        {values.map(({ id, label, value }) => (
          <Box
            key={id}
            sx={{
              display: "grid",
              gridTemplateColumns: "minmax(0, 1fr) auto",
              gap: 1,
              py: 0.45,
              borderBottom: "1px solid",
              borderColor: LEDGER_BORDER,
            }}
          >
            <Typography variant="body2" color="text.secondary" noWrap>
              {label}
            </Typography>
            <Typography variant="body2">{value}</Typography>
          </Box>
        ))}
      </Stack>
    ) : (
      <Typography variant="body2" color="text.disabled">
        –
      </Typography>
    )}
  </Box>
);

const renderSubComponent = ({ row }, t, playerNames) => {
  const player = row.original;
  const ratio = Number(player.kill_death_ratio);
  const kpm = Number(player.kills_per_minute);
  const statCategories = {
    combat: [
      { label: t("stats.gameDetails.metrics.kills"), value: player.kills },
      { label: t("stats.gameDetails.deaths"), value: player.deaths },
      {
        label: "K/D",
        value: Number.isFinite(ratio) ? ratio.toFixed(2) : "–",
      },
      {
        label: t("stats.gameDetails.killsPerMinute"),
        value: Number.isFinite(kpm) ? kpm.toFixed(2) : "–",
      },
    ],
    teamwork: [
      { label: t("stats.gameDetails.teamKills"), value: player.teamkills },
      {
        label: t("stats.gameDetails.teamKillStreak"),
        value: player.teamkills_streak,
      },
      {
        label: t("stats.gameDetails.deathsByTeamKill"),
        value: player.deaths_by_tk,
      },
      {
        label: t("stats.gameDetails.teamDeathStreak"),
        value: player.deaths_by_tk_streak,
      },
    ],
    objective: [
      {
        label: t("stats.gameDetails.metrics.offense"),
        value: player.offense,
      },
      {
        label: t("stats.gameDetails.metrics.defense"),
        value: player.defense,
      },
      {
        label: t("stats.gameDetails.metrics.combat"),
        value: player.combat,
      },
      {
        label: t("stats.gameDetails.metrics.support"),
        value: player.support,
      },
    ],
  };

  const keyedValues = (record, resolveLabel) =>
    Object.entries(record || {}).map(([id, value]) => ({
      id,
      label: resolveLabel(id),
      value,
    }));

  return (
    <Box
      id={row.id + "-details"}
      sx={{
        p: { xs: 1.5, md: 2 },
        bgcolor: "rgba(255,255,255,0.015)",
        borderLeft: "2px solid",
        borderColor: "primary.main",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          gap: { xs: 2, md: 3 },
          mb: 2.5,
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
          stats={statCategories.objective}
        />
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, minmax(0, 1fr))",
            lg: "repeat(4, minmax(0, 1fr))",
          },
          gap: { xs: 2, md: 3 },
        }}
      >
        <DetailList
          title={t("stats.gameDetails.killsByPlayer")}
          values={keyedValues(
            player.most_killed,
            (id) => playerNames.get(id) || id
          )}
        />
        <DetailList
          title={t("stats.gameDetails.killsByWeapon")}
          values={keyedValues(player.weapons, (id) => id)}
        />
        <DetailList
          title={t("stats.gameDetails.deathsByWeapon")}
          values={keyedValues(player.death_by_weapons, (id) => id)}
        />
        <DetailList
          title={t("stats.gameDetails.deathsByPlayer")}
          values={keyedValues(
            player.death_by,
            (id) => playerNames.get(id) || id
          )}
        />
      </Box>
    </Box>
  );
};

const PlayersTable = ({ table, selectedPlayers, onColumnVisibilityChange }) => {
  const { t } = useTranslation();
  const [tableConfigDrawerOpen, setTableConfigDrawerOpen] = useState(false);
  const tableConfig = useGameDetailsTableStore();
  const setConfig = useGameDetailsTableStore((state) => state.setConfig);
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const [expandedPlayerId, setExpandedPlayerId] = useState(null);
  const playerNames = useMemo(
    () =>
      new Map(
        table.options.data.map((player) => [player.player_id, player.player])
      ),
    [table.options.data]
  );
  const roleOptions = useMemo(
    () =>
      [
        ...new Set(table.options.data.map(getHistoricalRole).filter(Boolean)),
      ].sort((a, b) => a.localeCompare(b)),
    [table.options.data]
  );
  const teamFilter = table.getColumn("team")?.getFilterValue() ?? "all";
  const roleFilter = table.getColumn("role")?.getFilterValue() ?? "all";
  const rows = table.getRowModel().rows;

  const updateFilter = (columnId, value) => {
    table
      .getColumn(columnId)
      ?.setFilterValue(value === "all" ? undefined : value);
    table.setPageIndex(0);
    table.resetRowSelection();
  };

  return (
    <Box
      component="section"
      aria-labelledby="completed-game-players-heading"
      sx={{
        border: "1px solid",
        borderColor: LEDGER_BORDER,
        bgcolor: "rgba(8, 12, 9, 0.78)",
        overflow: "hidden",
      }}
    >
      <Typography
        component="h2"
        id="completed-game-players-heading"
        variant="overline"
        color="primary.main"
        sx={{
          display: "flex",
          alignItems: "center",
          minHeight: 36,
          px: 1.5,
          fontWeight: 900,
          letterSpacing: "0.11em",
          borderBottom: "1px solid",
          borderColor: LEDGER_BORDER,
        }}
      >
        {t("stats.gameDetails.playerAnalysis")}
      </Typography>
      <TableToolbar
        sx={{
          border: 0,
          borderBottom: "1px solid",
          borderColor: LEDGER_BORDER,
          flexWrap: "wrap",
          minHeight: 48,
        }}
      >
        <DebouncedSearchInput
          placeholder={t("stats.liveSessions.searchPlayer")}
          initialValue={table.getColumn("name")?.getFilterValue() ?? ""}
          onChange={(value) => {
            table.getColumn("name")?.setFilterValue(value);
            table.setPageIndex(0);
          }}
          sx={{
            flex: { xs: "1 1 100%", md: "1 1 280px" },
            maxWidth: { md: 360 },
            "& .MuiOutlinedInput-root": { borderRadius: 0, height: 48 },
            "& fieldset": { borderTop: 0, borderBottom: 0, borderLeft: 0 },
          }}
        />
        <FormControl
          size="small"
          sx={{
            flex: { xs: "1 1 50%", sm: "0 0 170px" },
            "& .MuiOutlinedInput-root": { borderRadius: 0, height: 48 },
          }}
        >
          <Select
            value={teamFilter}
            onChange={(event) => updateFilter("team", event.target.value)}
            inputProps={{ "aria-label": t("stats.gameDetails.teamFilter") }}
          >
            <MenuItem value="all">{t("stats.gameDetails.allTeams")}</MenuItem>
            <MenuItem value="allies">{t("views.team.allies")}</MenuItem>
            <MenuItem value="axis">{t("views.team.axis")}</MenuItem>
            <MenuItem value="review">
              {t("stats.gameDetails.teamReview")}
            </MenuItem>
          </Select>
        </FormControl>
        {table.getColumn("role") ? (
          <FormControl
            size="small"
            sx={{
              flex: { xs: "1 1 50%", sm: "0 0 170px" },
              "& .MuiOutlinedInput-root": { borderRadius: 0, height: 48 },
            }}
          >
            <Select
              value={roleFilter}
              onChange={(event) => updateFilter("role", event.target.value)}
              inputProps={{ "aria-label": t("stats.gameDetails.roleFilter") }}
            >
              <MenuItem value="all">{t("stats.gameDetails.allRoles")}</MenuItem>
              {roleOptions.map((role) => (
                <MenuItem key={role} value={role}>
                  {formatRoleLabel(t, role)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        ) : null}
        <Box sx={{ flex: { md: 1 } }} />
        {selectedPlayers.length ? (
          <ActionMenuButton
            actions={generatePlayerActions({
              multiAction: true,
              onlineAction: false,
            })}
            recipients={selectedPlayers}
            renderButton={(props) => (
              <Button
                {...props}
                startIcon={<GroupsOutlinedIcon />}
                sx={{ minHeight: 48, borderRadius: 0, px: 1.5 }}
              >
                {t("stats.gameDetails.selectedPlayers", {
                  count: selectedPlayers.length,
                })}
              </Button>
            )}
          />
        ) : null}
        <Button
          startIcon={<DownloadIcon />}
          onClick={() => downloadGame(table.options.data, csvHeaders(t))}
          sx={{ minHeight: 48, borderRadius: 0, px: 1.5 }}
        >
          {t("stats.gameDetails.csvExport")}
        </Button>
        <TableColumnSelection
          table={table}
          onColumnVisibilityChange={onColumnVisibilityChange}
          renderButton={(props) => (
            <Button
              {...props}
              startIcon={<ViewColumnIcon />}
              sx={{ minHeight: 48, borderRadius: 0, px: 1.5 }}
            >
              {t("stats.gameDetails.columns")}
            </Button>
          )}
        />
        <IconButton
          aria-label={t("stats.gameDetails.tableSettings")}
          onClick={() => setTableConfigDrawerOpen(true)}
          sx={{ width: 48, height: 48, borderRadius: 0 }}
        >
          <SettingsIcon fontSize="small" />
        </IconButton>
      </TableToolbar>

      {compact ? (
        rows.length ? (
          <Stack
            component="div"
            aria-label={t("stats.liveGame.playerStatistics")}
            gap={0}
          >
            {rows.map((row) => {
              const player = row.original;
              const expanded = expandedPlayerId === player.player_id;
              const side = normalizeHistoricalTeam(player.team);
              const role = getHistoricalRole(player);
              const squad = getHistoricalSquad(player);
              return (
                <Paper
                  key={player.player_id}
                  variant="outlined"
                  sx={{
                    borderRadius: 0,
                    borderWidth: 0,
                    borderBottom: "1px solid",
                    borderColor: LEDGER_BORDER,
                    bgcolor: "transparent",
                  }}
                >
                  <Stack
                    direction="row"
                    alignItems="center"
                    sx={{ minHeight: 58, pr: 0.5 }}
                  >
                    <ButtonBase
                      aria-expanded={expanded}
                      aria-controls={
                        expanded ? row.id + "-mobile-details" : undefined
                      }
                      aria-label={
                        player.player +
                        " " +
                        (expanded ? t("common.close") : t("common.open"))
                      }
                      onClick={() =>
                        setExpandedPlayerId(expanded ? null : player.player_id)
                      }
                      sx={{
                        display: "grid",
                        gridTemplateColumns:
                          "28px minmax(0, 1fr) repeat(3, 34px)",
                        alignItems: "center",
                        flex: 1,
                        minWidth: 0,
                        minHeight: 58,
                        textAlign: "left",
                      }}
                    >
                      <ChevronRightIcon
                        sx={{
                          transform: expanded ? "rotate(90deg)" : "none",
                          transition: "transform 120ms",
                        }}
                      />
                      <Box
                        sx={{
                          minWidth: 0,
                          maxWidth: "100%",
                          overflow: "hidden",
                        }}
                      >
                        <Typography
                          variant="body2"
                          noWrap
                          sx={{ display: "block" }}
                        >
                          {player.player}
                        </Typography>
                        <Typography
                          variant="caption"
                          color={teamColor(side)}
                          noWrap
                          sx={{ display: "block", maxWidth: "100%" }}
                        >
                          {[
                            teamLabel(t, side),
                            squad ? formatSquadLabel(squad) : null,
                            role ? formatRoleLabel(t, role) : null,
                          ]
                            .filter(Boolean)
                            .join(" · ")}
                        </Typography>
                      </Box>
                      {[
                        ["K", player.kills ?? 0],
                        ["T", player.deaths ?? 0],
                        ["TK", player.teamkills ?? 0],
                      ].map(([label, value]) => (
                        <Box key={label} sx={{ textAlign: "center" }}>
                          <Typography
                            variant="caption"
                            color="text.secondary"
                            display="block"
                          >
                            {label}
                          </Typography>
                          <Typography
                            variant="body2"
                            color={
                              label === "TK" && Number(value) > 0
                                ? "error.main"
                                : "text.primary"
                            }
                          >
                            {value}
                          </Typography>
                        </Box>
                      ))}
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
                      aria-label={t("stats.gameDetails.playerActions", {
                        player: player.player,
                      })}
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
                      sx={{ minWidth: 44, minHeight: 44, borderRadius: 0 }}
                    >
                      <MoreHorizIcon />
                    </IconButton>
                  </Stack>
                  <Collapse in={expanded} unmountOnExit>
                    <Box id={row.id + "-mobile-details"}>
                      {renderSubComponent({ row }, t, playerNames)}
                    </Box>
                  </Collapse>
                </Paper>
              );
            })}
          </Stack>
        ) : (
          <Typography color="text.secondary" sx={{ p: 3, textAlign: "center" }}>
            {t("stats.gameDetails.noPlayersFound")}
          </Typography>
        )
      ) : (
        <Table
          table={table}
          config={tableConfig}
          renderSubComponent={(props) =>
            renderSubComponent(props, t, playerNames)
          }
          showTopScrollbar
          topScrollbarLabel={t("stats.gameDetails.scrollColumns")}
        />
      )}

      <Stack
        component="footer"
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{
          minHeight: 48,
          px: 1.5,
          py: 0.5,
          borderTop: "1px solid",
          borderColor: LEDGER_BORDER,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {t("stats.gameDetails.playersShown", {
            shown: table.getFilteredRowModel().rows.length,
            total: table.options.data.length,
          })}
        </Typography>
        <TablePagination table={table} />
      </Stack>

      <TableConfigDrawer
        name={t("stats.gameDetails.playerAnalysis")}
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

export default PlayersTable;
