import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import dayjs from "dayjs";
import { Action, SortableHeader, TextButton } from "@/components/table/styles";
import { generatePlayerActions } from "@/features/player-action/actions";
import { LogMessage } from "@/components/shared/LogMessage";
import { getLogTeam, getTeamColor } from "@/utils/lib";
import { Box } from "@mui/material";
import { alpha } from "@mui/material/styles";
import { getThemeTeamColor } from "@/themes/teamColors";

const TIME_FORMAT = "HH:mm:ss, MMM DD";

const playerNameFilter = (row, columnId, filterValue = []) => {
  // If no filter value, show all rows
  if (!filterValue.length) return true;

  const player1 = row.original.player_name_1;
  const player2 = row.original.player_name_2;

  // Check if either player name matches the filter value
  return filterValue.includes(player1) || filterValue.includes(player2);
};

const actionFilter = (row, columnId, filterValue = []) => {
  if (!filterValue) return true;
  const anyStartsWith = filterValue.some((action) => {
    switch (action) {
      case "CHAT":
      case "ADMIN":
      case "VOTE":
      case "MATCH":
        return row.original.action.startsWith(action);
      default:
        return row.original.action === action;
    }
  });
  return anyStartsWith;
};

const teamFilter = (row, columnId, filterValue = []) => {
  if (!filterValue.length) return true;
  const team = row.getValue(columnId);
  return filterValue.includes(team);
};

// Column definitions for the log table
export const getLogsColumns = (t) => [
  {
    header: SortableHeader(t("views.table.time")),
    accessorKey: "timestamp_ms",
    cell: ({ row }) => {
      return dayjs(row.original.timestamp_ms).format(TIME_FORMAT);
    },
    meta: {
      variant: "time",
    },
  },
  {
    header: SortableHeader(t("views.table.team")),
    id: "team",
    accessorFn: (log) => getLogTeam(log),
    filterFn: teamFilter,
    cell: ({ getValue, row }) => {
      const team = getValue();
      if (!team) return null;
      return (
        <Box
          sx={(theme) => {
            const teamColor = getThemeTeamColor(theme, team);
            return {
              backgroundColor: alpha(teamColor, 0.82),
              border: `1px solid ${teamColor}`,
              textTransform: "uppercase",
              fontWeight: "bold",
              fontSize: "0.75em",
              color: theme.palette.getContrastText(teamColor),
              padding: "0.15em 0.25em",
              textAlign: "center",
            };
          }}
        >
          {team}
        </Box>
      );
    },
    meta: {
      variant: "short",
    },
  },
  {
    header: t("views.table.thisPlayer"),
    accessorKey: "player_name_1",
    cell: ({ row }) => {
      return row.original.player_name_1 && row.original.player_id_1 ? (
        <ActionMenuButton
          actions={generatePlayerActions({
            multiAction: false,
            onlineAction: true,
          })}
          withProfile
          recipients={{
            player_id: row.original.player_id_1,
            name: row.original.player_name_1,
          }}
          renderButton={(props) => (
            <TextButton {...props}>{row.original.player_name_1}</TextButton>
          )}
        />
      ) : row.original.player_name_1 ? (
        <span>{row.original.player_name_1}</span>
      ) : null;
    },
    filterFn: playerNameFilter,
    meta: {
      variant: "action",
    },
  },
  {
    header: t("views.table.action"),
    accessorKey: "action",
    id: "action",
    cell: ({ row }) => {
      return <Action type={row.original.action}>{row.original.action}</Action>;
    },
    filterFn: actionFilter,
    meta: {
      variant: "action",
    },
  },
  {
    header: t("views.table.otherPlayer"),
    accessorKey: "player_name_2",
    filterFn: playerNameFilter,
    cell: ({ row }) => {
      return row.original.player_name_2 && row.original.player_id_2 ? (
        <ActionMenuButton
          actions={generatePlayerActions({
            multiAction: false,
            onlineAction: true,
          })}
          withProfile
          recipients={{
            player_id: row.original.player_id_2,
            name: row.original.player_name_2,
          }}
          renderButton={(props) => (
            <TextButton {...props}>{row.original.player_name_2}</TextButton>
          )}
        />
      ) : row.original.player_name_2 ? (
        <span>{row.original.player_name_2}</span>
      ) : null;
    },
    meta: {
      variant: "name",
    },
  },
  {
    header: t("views.table.message"),
    id: "message_with_id",
    accessorKey: "message",
    cell: ({ row }) => {
      return (
        <LogMessage log={row.original} colored={true} include_ids={true} />
      );
    },
  },
  {
    header: t("views.table.message"),
    id: "message",
    accessorKey: "message",
    cell: ({ row }) => {
      return <LogMessage log={row.original} colored={false} />;
    },
  },
  {
    header: t("views.table.fullMessage"),
    id: "full_message",
    accessorKey: "message",
    meta: {
      size: "full",
      variant: "content",
    },
  },
  {
    header: t("views.table.shortMessage"),
    id: "short_message",
    accessorKey: "message",
    cell: ({ row }) => {
      return <LogMessage log={row.original} colored={false} short={true} />;
    },
  },
];
