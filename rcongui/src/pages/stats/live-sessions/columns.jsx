import { Box, Checkbox, IconButton, Tooltip } from "@mui/material";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import {
  getColoredFactionIconSrc,
  getPlayerTier,
  getTierColors,
} from "@/utils/lib";
import { SortableHeader } from "@/components/table/styles";
import { useThemedImages } from "@/hooks/useThemedImages";
import { getRoleIconKey } from "@/constants/roles";
import {
  formatSessionDuration,
  getPlayerKdr,
  getPlayerSessionSeconds,
  getRoleLabel,
  getTeamLabel,
} from "./live-session-utils";

const Center = ({ children }) => (
  <Box sx={{ display: "grid", placeItems: "center", minWidth: 20 }}>
    {children}
  </Box>
);

const Level = ({ value }) => {
  const tier = getPlayerTier(value);
  return (
    <Box
      sx={{
        color: (theme) => getTierColors(theme.palette.mode)[tier],
        fontVariantNumeric: "tabular-nums",
        textAlign: "right",
      }}
    >
      {value ?? "–"}
    </Box>
  );
};

const ScoreCell = ({ value }) => (
  <Box sx={{ fontVariantNumeric: "tabular-nums", textAlign: "right" }}>
    {Number(value) || 0}
  </Box>
);

export const createLiveSessionColumns = (t) => [
  {
    id: "select",
    enableHiding: false,
    enableSorting: false,
    header: ({ table }) => (
      <Checkbox
        inputProps={{ "aria-label": t("common.selectAll") }}
        checked={table.getIsAllPageRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllPageRowsSelectedHandler()}
        size="small"
        sx={{ p: 0 }}
      />
    ),
    cell: ({ row }) => (
      <Checkbox
        inputProps={{
          "aria-label": t("common.selectPlayer", { name: row.original.name }),
        }}
        checked={row.getIsSelected()}
        onClick={(event) => event.stopPropagation()}
        onChange={row.getToggleSelectedHandler()}
        size="small"
        sx={{ p: 0 }}
      />
    ),
    meta: { variant: "icon" },
  },
  {
    id: "faction",
    accessorKey: "team",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.faction"),
      t("stats.liveSessions.faction")
    ),
    cell: ({ row }) => (
      <Center>
        <Tooltip title={getTeamLabel(t, row.original.team)}>
          <img
            src={getColoredFactionIconSrc(
              row.original.faction ?? row.original.team
            )}
            width={18}
            height={18}
            alt={getTeamLabel(t, row.original.team)}
          />
        </Tooltip>
      </Center>
    ),
    meta: {
      variant: "short",
      align: "center",
      label: t("stats.liveSessions.faction"),
    },
  },
  {
    id: "unit",
    accessorKey: "unit_name",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.unit"),
      t("stats.liveSessions.unit")
    ),
    cell: ({ row }) => (
      <Box sx={{ textTransform: "uppercase", whiteSpace: "nowrap" }}>
        {row.original.unit_name === "unassigned"
          ? "–"
          : row.original.unit_name || "–"}
      </Box>
    ),
    meta: { variant: "short", label: t("stats.liveSessions.unit") },
  },
  {
    id: "role",
    accessorKey: "role",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.role"),
      t("stats.liveSessions.role")
    ),
    cell: ({ row }) => {
      const themedImages = useThemedImages();
      const iconKey = getRoleIconKey(row.original.role);
      return (
        <Center>
          <Tooltip title={getRoleLabel(t, row.original.role)}>
            <img
              src={themedImages.getRoleIconSrc(iconKey)}
              width={18}
              height={18}
              alt={getRoleLabel(t, row.original.role)}
            />
          </Tooltip>
        </Center>
      );
    },
    meta: {
      variant: "short",
      align: "center",
      label: t("stats.liveSessions.role"),
    },
  },
  {
    id: "name",
    accessorKey: "name",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.name"),
      t("stats.liveSessions.name")
    ),
    cell: ({ row }) => (
      <Box
        sx={{
          minWidth: "12ch",
          maxWidth: "24ch",
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          color: "text.primary",
          fontWeight: 400,
        }}
        title={row.original.name}
      >
        {row.original.name}
      </Box>
    ),
  },
  {
    id: "level",
    accessorKey: "level",
    header: SortableHeader(
      t("stats.liveSessions.levelShort"),
      t("stats.liveSessions.level")
    ),
    cell: ({ row }) => <Level value={row.original.level} />,
    meta: {
      variant: "short",
      align: "right",
      label: t("stats.liveSessions.level"),
    },
  },
  {
    id: "kills",
    accessorKey: "kills",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.killsShort"),
      t("stats.liveSessions.kills")
    ),
    cell: ({ row }) => <ScoreCell value={row.original.kills} />,
    meta: {
      variant: "short",
      align: "right",
      label: t("stats.liveSessions.kills"),
    },
  },
  {
    id: "deaths",
    accessorKey: "deaths",
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.deathsShort"),
      t("stats.liveSessions.deaths")
    ),
    cell: ({ row }) => <ScoreCell value={row.original.deaths} />,
    meta: {
      variant: "short",
      align: "right",
      label: t("stats.liveSessions.deaths"),
    },
  },
  {
    id: "kdr",
    accessorFn: getPlayerKdr,
    enableHiding: false,
    header: SortableHeader("K/D", t("stats.liveSessions.kdr")),
    cell: ({ row }) => (
      <Box sx={{ fontVariantNumeric: "tabular-nums", textAlign: "right" }}>
        {getPlayerKdr(row.original).toFixed(2)}
      </Box>
    ),
    meta: {
      variant: "ratio",
      align: "right",
      label: t("stats.liveSessions.kdr"),
    },
  },
  ...[
    ["combat", "combatScore"],
    ["offense", "offenseScore"],
    ["defense", "defenseScore"],
    ["support", "supportScore"],
  ].map(([id, label]) => ({
    id,
    accessorKey: id,
    header: SortableHeader(
      t(`stats.liveSessions.${label}`),
      t(`stats.liveSessions.${label}`)
    ),
    cell: ({ row }) => <ScoreCell value={row.original[id]} />,
    meta: {
      variant: "short",
      align: "right",
      label: t(`stats.liveSessions.${label}`),
    },
  })),
  {
    id: "time",
    accessorFn: getPlayerSessionSeconds,
    enableHiding: false,
    header: SortableHeader(
      t("stats.liveSessions.timeShort"),
      t("stats.liveSessions.currentPlaytime")
    ),
    cell: ({ row }) => (
      <Box
        sx={{
          fontVariantNumeric: "tabular-nums",
          textAlign: "right",
          whiteSpace: "nowrap",
        }}
      >
        {formatSessionDuration(getPlayerSessionSeconds(row.original))}
      </Box>
    ),
    meta: {
      variant: "short",
      align: "right",
      label: t("stats.liveSessions.currentPlaytime"),
    },
  },
  {
    id: "actions",
    enableHiding: false,
    enableSorting: false,
    header: (
      <Box component="span" title={t("common.actions")} sx={{ display: "block", textAlign: "center" }}>
        •••
      </Box>
    ),
    cell: ({ row }) => (
      <ActionMenuButton
        actions={generatePlayerActions({
          multiAction: false,
          onlineAction: true,
        })}
        recipients={row.original}
        withProfile
        renderButton={(props) => (
          <IconButton
            {...props}
            size="small"
            onClick={(event) => {
              event.stopPropagation();
              props.onClick(event);
            }}
            sx={{ borderRadius: 0, p: 0.25 }}
          >
            <MoreHorizIcon sx={{ fontSize: 18 }} />
          </IconButton>
        )}
      />
    ),
    meta: { variant: "icon", align: "center" },
  },
];
