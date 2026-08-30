import { Box, Checkbox, IconButton, Stack, Typography } from "@mui/material";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import PublicOutlinedIcon from "@mui/icons-material/PublicOutlined";
import dayjs from "dayjs";

import { CountryFlag } from "@/components/shared/CountryFlag";
import { SortableHeader } from "@/components/table/styles";
import {
  formatRoleLabel,
  formatSquadLabel,
} from "@/pages/views/live/player-display-labels";

import {
  getHistoricalRole,
  getHistoricalSquad,
  normalizeHistoricalTeam,
} from "./game-detail-utils";

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

const numericColumn = (id, label, title, accessorKey, valueFormatter) => ({
  id,
  header: SortableHeader(label, title),
  accessorKey,
  cell: ({ row }) => {
    const value = row.original[accessorKey];
    return valueFormatter ? valueFormatter(value, row.original) : value ?? "–";
  },
  meta: {
    variant: "short",
    align: "right",
    label: title || label,
  },
});

export const createGameColumns = (t, { showAssignments = false } = {}) => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllRowsSelectedHandler()}
        inputProps={{ "aria-label": t("stats.gameDetails.selectAllPlayers") }}
        size="small"
        sx={{ p: 0.75 }}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        checked={row.getIsSelected()}
        disabled={!row.getCanSelect()}
        indeterminate={row.getIsSomeSelected()}
        onChange={row.getToggleSelectedHandler()}
        inputProps={{
          "aria-label": t("stats.gameDetails.selectPlayer", {
            player: row.original.player,
          }),
        }}
        size="small"
        sx={{ p: 0.75 }}
      />
    ),
    enableHiding: false,
    meta: { variant: "icon", label: t("stats.gameDetails.selection") },
  },
  {
    id: "country",
    header: SortableHeader(
      <PublicOutlinedIcon sx={{ fontSize: 16 }} />,
      t("records.players.country")
    ),
    accessorKey: "steaminfo.country",
    cell: ({ row }) => {
      const country = row.original.steaminfo?.country;
      return country && country !== "private" && country !== "unknown" ? (
        <CountryFlag country={country} />
      ) : null;
    },
    meta: {
      variant: "icon",
      label: t("records.players.country"),
    },
  },
  {
    id: "name",
    header: SortableHeader(
      t("stats.gameDetails.csv.name"),
      t("stats.gameDetails.csv.name")
    ),
    accessorKey: "player",
    cell: ({ row }) => (
      <Stack direction="row" alignItems="center" sx={{ minWidth: 0 }}>
        <IconButton
          aria-expanded={row.getIsExpanded()}
          aria-controls={row.getIsExpanded() ? row.id + "-details" : undefined}
          aria-label={t("stats.gameDetails.togglePlayerDetails", {
            player: row.original.player,
          })}
          onClick={row.getToggleExpandedHandler()}
          sx={{ width: 36, height: 36, borderRadius: 0, flexShrink: 0 }}
        >
          <KeyboardArrowRightIcon
            sx={{
              fontSize: 18,
              transform: row.getIsExpanded() ? "rotate(90deg)" : "none",
              transition: "transform 120ms ease",
            }}
          />
        </IconButton>
        <Typography variant="body2" noWrap>
          {row.original.player}
        </Typography>
      </Stack>
    ),
    enableHiding: false,
    meta: {
      variant: "playerName",
      label: t("stats.gameDetails.csv.name"),
    },
  },
  {
    id: "team",
    header: SortableHeader(
      t("stats.gameDetails.team"),
      t("stats.gameDetails.team")
    ),
    accessorFn: (row) => normalizeHistoricalTeam(row.team),
    filterFn: (row, columnId, value) => {
      const side = row.getValue(columnId);
      return value === "review"
        ? side === "mixed" || side === "unknown"
        : side === value;
    },
    cell: ({ row }) => {
      const side = normalizeHistoricalTeam(row.original.team);
      return (
        <Typography
          variant="body2"
          color={teamColor(side)}
          sx={{ textTransform: "uppercase" }}
        >
          {teamLabel(t, side)}
        </Typography>
      );
    },
    meta: {
      variant: "name",
      label: t("stats.gameDetails.team"),
    },
  },
  ...(showAssignments
    ? [
        {
          id: "role",
          header: SortableHeader(
            t("stats.gameDetails.role"),
            t("stats.gameDetails.role")
          ),
          accessorFn: (row) => getHistoricalRole(row) ?? "",
          cell: ({ row }) =>
            formatRoleLabel(t, getHistoricalRole(row.original)),
          meta: {
            variant: "name",
            label: t("stats.gameDetails.role"),
          },
        },
        {
          id: "unit",
          header: SortableHeader(
            t("stats.gameDetails.squad"),
            t("stats.gameDetails.squad")
          ),
          accessorFn: (row) => getHistoricalSquad(row) ?? "",
          cell: ({ row }) => formatSquadLabel(getHistoricalSquad(row.original)),
          meta: {
            variant: "squadCompact",
            label: t("stats.gameDetails.squad"),
          },
        },
      ]
    : []),
  numericColumn(
    "kills",
    t("stats.gameDetails.metrics.kills"),
    t("stats.gameDetails.metrics.kills"),
    "kills"
  ),
  numericColumn(
    "deaths",
    t("stats.gameDetails.deaths"),
    t("stats.gameDetails.deaths"),
    "deaths"
  ),
  numericColumn(
    "kd",
    "K/D",
    t("stats.gameDetails.killDeathRatio"),
    "kill_death_ratio",
    (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "–")
  ),
  numericColumn(
    "kpm",
    "K/M",
    t("stats.gameDetails.killsPerMinute"),
    "kills_per_minute",
    (value) => (Number.isFinite(Number(value)) ? Number(value).toFixed(2) : "–")
  ),
  numericColumn("tk", "TKs", t("stats.gameDetails.teamKills"), "teamkills"),
  numericColumn(
    "tk_streak",
    t("stats.gameDetails.teamKillStreakShort"),
    t("stats.gameDetails.teamKillStreak"),
    "teamkills_streak"
  ),
  numericColumn(
    "td",
    "TT",
    t("stats.gameDetails.deathsByTeamKill"),
    "deaths_by_tk"
  ),
  numericColumn(
    "td_streak",
    t("stats.gameDetails.teamDeathStreakShort"),
    t("stats.gameDetails.teamDeathStreak"),
    "deaths_by_tk_streak"
  ),
  {
    id: "time",
    header: SortableHeader(
      t("records.playerDetails.time"),
      t("stats.gameDetails.duration")
    ),
    accessorFn: (row) => row.time_seconds ?? row.time ?? 0,
    cell: ({ row }) => {
      const seconds = Number(
        row.original.time_seconds ?? row.original.time ?? 0
      );
      return dayjs
        .duration(
          Number.isFinite(seconds) && seconds >= 0 ? seconds : 0,
          "seconds"
        )
        .format("H:mm");
    },
    meta: {
      variant: "short",
      align: "right",
      label: t("records.playerDetails.time"),
    },
  },
  {
    id: "player_id",
    header: t("stats.gameDetails.csv.playerId"),
    accessorKey: "player_id",
    cell: ({ row }) => (
      <Typography variant="caption" sx={{ fontFamily: "monospace" }}>
        {row.original.player_id}
      </Typography>
    ),
    meta: {
      variant: "time",
      label: t("stats.gameDetails.csv.playerId"),
    },
  },
  {
    id: "actions",
    header: (
      <Box component="span" title={t("common.actions")}>
        <MoreHorizIcon sx={{ fontSize: 18 }} />
      </Box>
    ),
    cell: ({ row, table }) => {
      const actionMenuOpen =
        table.options.meta?.activePlayerActionId === row.original.player_id;
      return (
        <IconButton
          aria-controls={
            actionMenuOpen ? "completed-game-player-actions-menu" : undefined
          }
          aria-expanded={actionMenuOpen ? "true" : undefined}
          aria-haspopup="true"
          aria-label={t("stats.gameDetails.playerActions", {
            player: row.original.player,
          })}
          data-testid="completed-game-player-action-trigger"
          disableRipple
          onClick={(event) =>
            table.options.meta?.openPlayerActionMenu?.(event.currentTarget, {
              name: row.original.player,
              player_id: row.original.player_id,
            })
          }
          sx={{ width: 40, height: 40, borderRadius: 0 }}
        >
          <MoreHorizIcon sx={{ fontSize: 18 }} />
        </IconButton>
      );
    },
    meta: {
      variant: "icon",
      label: t("common.actions"),
    },
  },
];
