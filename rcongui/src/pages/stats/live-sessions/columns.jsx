import { Box, Checkbox, IconButton, styled } from "@mui/material";
import dayjs from "dayjs";
import {
  getColoredFactionIconSrc,
  getPlayerTier,
  getTierColors,
} from "@/utils/lib";
import { SortableHeader } from "@/components/table/styles";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import { useThemedImages } from "@/hooks/useThemedImages";

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

const LevelColored = styled(Box, {
  shouldForwardProp: (prop) => prop !== "level",
})((styledProps) => {
  const level = styledProps.level;
  if (!level) return {};
  const tier = getPlayerTier(level);
  // Use theme-aware tier color
  return {
    color: (theme) => getTierColors(theme.palette.mode)[tier],
  };
});

const Center = styled(Box)(() => ({
  display: "grid",
  justifyItems: "center",
  alignContent: "center",
}));

export const createLiveSessionColumns = (t) => [
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
    accessorKey: "team",
    id: "team",
    header: SortableHeader("T", t("stats.liveSessions.team")),
    cell: ({ row }) => {
      return (
        <Center>
          <Square>
            {row.original.faction ? (
              <img
                src={getColoredFactionIconSrc(row.original.faction)}
                width={16}
                height={16}
                alt={row.original.faction}
                title={row.original.faction}
              />
            ) : (
              <span>{"-"}</span>
            )}
          </Square>
        </Center>
      );
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "unit",
    header: SortableHeader("U", t("stats.liveSessions.unit")),
    accessorKey: "unit_name",
    // Group by unit name and team
    // getGroupingValue: (row) => `${row.original.unit_name ?? "-"}-${row.original.team}`,
    cell: ({ row }) => {
      return (
        <>
          <Center>
            <Square>{row.original.unit_name?.toUpperCase() ?? "-"}</Square>
          </Center>
        </>
      );
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "role",
    header: SortableHeader("R", t("stats.liveSessions.role")),
    accessorKey: "role",
    cell: ({ row }) => {
      const themedImg = useThemedImages();
      const iconKey = row.original.type ?? row.original.role;

      return row.team !== "neutral" ? (
        <Center>
          <Square>
            <img
              src={themedImg.getRoleIconSrc(iconKey)}
              width={16}
              height={16}
              alt={iconKey}
              title={iconKey}
            />
          </Square>
        </Center>
      ) : null;
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "level",
    header: SortableHeader("LVL", t("stats.liveSessions.level")),
    accessorKey: "level",
    aggregationFn: "mean",
    cell: ({ row }) => {
      return (
        <LevelColored level={row.original.level}>
          {row.original.level}
        </LevelColored>
      );
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "actions",
    header: <span title={t("common.actions")}>🛠️</span>,
    accessorKey: "actions",
    cell: ({ row, table }) => {
      if (row.getCanExpand())
        return (
          <IconButton
            aria-expanded={row.getIsExpanded()}
            aria-label={
              row.getIsExpanded()
                ? t("views.team.collapseSquadNamed", {
                    name: row.original.unit_name,
                  })
                : t("views.team.expandSquadNamed", {
                    name: row.original.unit_name,
                  })
            }
            size="small"
            sx={{ p: 0, width: 16, height: 16, fontSize: 12 }}
            onClick={row.getToggleExpandedHandler()}
          >
            {row.getIsExpanded() ? <ExpandMoreIcon /> : <ChevronRightIcon />}
          </IconButton>
        );

      const actionMenuOpen =
        table.options.meta?.activePlayerActionId === row.original.player_id;
      return (
        <IconButton
          aria-controls={
            actionMenuOpen ? "live-sessions-player-actions-menu" : undefined
          }
          aria-expanded={actionMenuOpen ? "true" : undefined}
          aria-haspopup="true"
          aria-label={t("actions.menu")}
          data-testid="live-sessions-player-action-trigger"
          disableRipple
          onClick={(event) =>
            table.options.meta?.openPlayerActionMenu?.(
              event.currentTarget,
              row.original
            )
          }
          size="small"
          sx={{ width: 20, height: 20 }}
        >
          <MoreHorizIcon sx={{ fontSize: 16 }} />
        </IconButton>
      );
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "name",
    header: SortableHeader(
      t("stats.liveSessions.name"),
      t("stats.liveSessions.name")
    ),
    accessorKey: "name",
    cell: ({ row }) => {
      return (
        <Box
          sx={{
            textOverflow: "ellipsis",
            overflow: "hidden",
            textWrap: "nowrap",
            width: "20ch",
          }}
        >
          <span>{row.original.name}</span>
        </Box>
      );
    },
  },
  {
    id: "kills",
    header: SortableHeader("K", t("stats.liveSessions.kills")),
    accessorKey: "kills",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.kills}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "deaths",
    header: SortableHeader("D", t("stats.liveSessions.deaths")),
    accessorKey: "deaths",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.deaths}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "combat",
    header: SortableHeader("C", t("stats.liveSessions.combatScore")),
    accessorKey: "combat",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.combat}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "offense",
    header: SortableHeader("O", t("stats.liveSessions.offenseScore")),
    accessorKey: "offense",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.offense}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "defense",
    header: SortableHeader("D", t("stats.liveSessions.defenseScore")),
    accessorKey: "defense",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.defense}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "support",
    header: SortableHeader("S", t("stats.liveSessions.supportScore")),
    accessorKey: "support",
    aggregationFn: "sum",
    cell: ({ row }) => {
      return <>{row.original.support}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "time",
    header: SortableHeader(
      t("records.playerDetails.time"),
      t("stats.liveSessions.currentPlaytime")
    ),
    accessorKey: "profile.current_playtime_seconds",
    aggregationFn: "mean",
    cell: ({ row }) => {
      return (
        <>
          {dayjs
            .duration(row.original.profile.current_playtime_seconds, "seconds")
            .format("H:mm")}
        </>
      );
    },
    meta: {
      variant: "short",
    },
  },
];
