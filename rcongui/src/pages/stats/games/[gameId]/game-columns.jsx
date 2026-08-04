import {
  Box,
  Checkbox,
  IconButton,
  styled,
} from "@mui/material";
import dayjs from "dayjs";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { CountryFlag } from "@/components/shared/CountryFlag";
import { SortableHeader } from "@/components/table/styles";
import ArrowDownwardIcon from '@mui/icons-material/ArrowDownward';
import ArrowRightIcon from '@mui/icons-material/ArrowRight';

export const Square = styled(Box)(({ theme }) => ({
  display: "flex",
  alignItems: "start",
  justifyContent: "center",
  width: 16,
  height: 16,
  lineHeight: "16px",
  fontWeight: "bold",
  backgroundColor: theme.palette.background.paper,
}));

const Center = styled(Box)(() => ({
  display: "grid",
  justifyItems: "center",
  alignContent: "center",
}));

export const createGameColumns = (t) => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        checked={table.getIsAllRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllRowsSelectedHandler()}
        size="small"
        sx={{
          p: 0,
        }}
      />
    ),
    cell: ({ row }) => (
      <div>
        <Checkbox
          checked={row.getIsSelected()}
          disabled={!row.getCanSelect()}
          indeterminate={row.getIsSomeSelected()}
          onChange={row.getToggleSelectedHandler()}
          size="small"
          sx={{
            p: 0,
          }}
        />
      </div>
    ),
    meta: {
      variant: "icon",
    },
  },
  {
    id: "country",
    header: SortableHeader("🌎", t("records.players.country")),
    accessorKey: "steaminfo.country",
    cell: ({ row }) => {
      return row.original.steaminfo?.country && row.original.steaminfo?.country !== "private" ? (
        <CountryFlag country={row.original.steaminfo.country} />
      ) : null;
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "actions",
    header: <span title={t("common.actions")}>🛠️</span>,
    accessorKey: "actions",
    cell: ({ row }) => {
      return (
        <ActionMenuButton
          actions={generatePlayerActions()}
          recipients={{ name: row.original.player, player_id: row.original.player_id }}
          orientation="horizontal"
          disableRipple={true}
          sx={{
            width: 12,
            height: 12,
          }}
        />
      );
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "name",
    header: SortableHeader(t("stats.gameDetails.csv.name"), t("stats.gameDetails.csv.name")),
    accessorKey: "player",
    cell: ({ row }) => {
      return (
        <Box>
          <span>{row.original.player}</span>
        </Box>
      );
    },
    meta: {
      variant: "fullname",
    },
    children: [

    ]
  },
  {
    id: 'expander',
    header: () => null,
    cell: ({ row }) => {
      return row.getCanExpand() ? (
        <IconButton
          size="small"
          sx={{
            p: 0,
            width: 12,
            height: 12,
          }}
          onClick={row.getToggleExpandedHandler()}
        >
          {row.getIsExpanded() ? <ArrowDownwardIcon fontSize="small" /> : <ArrowRightIcon fontSize="small"  />}
        </IconButton>
      ) : (
        '🔵'
      )
    },
  },
  {
    id: "kd",
    header: SortableHeader("K/D", `${t("stats.gameDetails.metrics.kills")} / ${t("stats.gameDetails.deaths")}`),
    accessorKey: "kill_death_ratio",
    cell: ({ row }) => {
      return <>{row.original.kill_death_ratio}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "kpm",
    header: SortableHeader("K/M", t("stats.gameDetails.killsPerMinute")),
    accessorKey: "kills_per_minute",
    cell: ({ row }) => {
      return <>{row.original.kills_per_minute}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "kills",
    header: SortableHeader(t("stats.gameDetails.metrics.kills"), t("stats.gameDetails.metrics.kills")),
    accessorKey: "kills",
    cell: ({ row }) => {
      return <>{row.original.kills}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "deaths",
    header: SortableHeader(t("stats.gameDetails.deaths"), t("stats.gameDetails.deaths")),
    accessorKey: "deaths",
    cell: ({ row }) => {
      return <>{row.original.deaths}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "tk",
    header: SortableHeader("TKs", t("stats.gameDetails.teamKills")),
    accessorKey: "teamkills",
    cell: ({ row }) => {
      return <>{row.original.teamkills}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "tk_streak",
    header: SortableHeader("TK-Serie", t("stats.gameDetails.teamKillStreak")),
    accessorKey: "teamkills_streak",
    cell: ({ row }) => {
      return <>{row.original.teamkills_streak}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "td",
    header: SortableHeader("TT", t("stats.gameDetails.deathsByTeamKill")),
    accessorKey: "deaths_by_tk",
    cell: ({ row }) => {
      return <>{row.original.deaths_by_tk}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "td_streak",
    header: SortableHeader("TT-Serie", t("stats.gameDetails.teamDeathStreak")),
    accessorKey: "deaths_by_tk_streak",
    cell: ({ row }) => {
      return <>{row.original.deaths_by_tk_streak}</>;
    },
    meta: {
      variant: "short",
    }
  },
  {
    id: "time",
    header: SortableHeader(t("records.playerDetails.time"), t("stats.gameDetails.duration")),
    accessorFn: (row) => row.time_seconds ?? row.time ?? 0,
    aggregationFn: "mean",
    cell: ({ row }) => {
      const seconds = Number(
        row.original.time_seconds ?? row.original.time ?? 0,
      );
      return (
        <>
          {dayjs
            .duration(Number.isFinite(seconds) && seconds >= 0 ? seconds : 0, "seconds")
            .format("H:mm")}
        </>
      );
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "player_id",
    header: t("stats.gameDetails.csv.playerId"),
    accessorKey: "player_id",
    cell: ({ row }) => {
      return <>{row.original.player_id}</>;
    },
  }
];
