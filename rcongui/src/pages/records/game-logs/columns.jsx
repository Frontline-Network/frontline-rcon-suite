import dayjs from "dayjs";
import { Action, SortableHeader, TextButton } from "@/components/table/styles";
import { GAME_LOG_PLAYER_ACTION_MENU_ID } from "./shared-player-action-menu";

const removePlayerIds = (message) => {
  // Combine both regex patterns into one
  return message.replace(
    /\((?:(?:Axis|Allies)\/)?(?:[0-9]{17}|[A-Z0-9]{16})\)/g,
    ""
  );
};

const playerNameFilter = (row, columnId, filterValue = []) => {
  // If no filter value, show all rows
  if (!filterValue.length) return true;
  
  const player1 = row.original.player1_name;
  const player2 = row.original.player2_name;
  
  // Check if either player name matches the filter value
  return filterValue.includes(player1) || filterValue.includes(player2);
};

// Column definitions for the log table
export const getLogsColumns = (t) => [
  {
    header: SortableHeader(t("views.table.time")),
    accessorKey: "event_time",
    cell: ({ row }) => {
      return dayjs
        .utc(row.original.event_time)
        .tz(Intl.DateTimeFormat().resolvedOptions().timeZone)
        .format(t("common.logDateTimeFormat"));
    },
    meta: {
      variant: "time"
    },
  },
  {
    header: t("views.table.thisPlayer"),
    accessorKey: "player1_name",
    cell: ({ row, table }) => {
      const triggerKey = `${row.id}:player1`;
      const actionMenuOpen =
        table.options.meta?.activePlayerActionKey === triggerKey;
      return row.original.player1_name && row.original.player1_id ? (
        <TextButton
          aria-controls={
            actionMenuOpen ? GAME_LOG_PLAYER_ACTION_MENU_ID : undefined
          }
          aria-expanded={actionMenuOpen ? "true" : undefined}
          aria-haspopup="true"
          data-testid="game-log-player-action-trigger"
          onClick={(event) =>
            table.options.meta?.openPlayerActionMenu?.(
              event.currentTarget,
              {
                player_id: row.original.player1_id,
                name: row.original.player1_name,
              },
              { onlineAction: true, triggerKey }
            )
          }
        >
          {row.original.player1_name}
        </TextButton>
      ) : row.original.player1_name ? <span>{row.original.player1_name}</span> : null;
    },
    filterFn: playerNameFilter,
    meta: {
      variant: "name"
    },
  },
  {
    header: t("views.table.action"),
    accessorKey: "type",
    id: "type",
    cell: ({ row }) => {
      return <Action type={row.original.type}>{row.original.type}</Action>;
    },
    filterFn: "arrIncludesSome",
    meta: {
      variant: "action"
    },
  },
  {
    header: t("views.table.otherPlayer"),
    accessorKey: "player2_name",
    filterFn: playerNameFilter,
    cell: ({ row, table }) => {
      const triggerKey = `${row.id}:player2`;
      const actionMenuOpen =
        table.options.meta?.activePlayerActionKey === triggerKey;
      return row.original.player2_name && row.original.player2_id ? (
        <TextButton
          aria-controls={
            actionMenuOpen ? GAME_LOG_PLAYER_ACTION_MENU_ID : undefined
          }
          aria-expanded={actionMenuOpen ? "true" : undefined}
          aria-haspopup="true"
          data-testid="game-log-player-action-trigger"
          onClick={(event) =>
            table.options.meta?.openPlayerActionMenu?.(
              event.currentTarget,
              {
                player_id: row.original.player2_id,
                name: row.original.player2_name,
              },
              { onlineAction: false, triggerKey }
            )
          }
        >
          {row.original.player2_name}
        </TextButton>
      ) : row.original.player2_name ? <span>{row.original.player2_name}</span> : null;
    },
    meta: {
      variant: "name"
    },
  },
  {
    header: t("views.table.message"),
    accessorKey: "content",
    meta: {
      size: "full",
      variant: "content",
    },
    cell: ({ row }) => {
      return removePlayerIds(row.original.content);
    },
  },
];
