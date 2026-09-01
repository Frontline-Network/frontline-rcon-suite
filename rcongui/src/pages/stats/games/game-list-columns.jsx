import dayjs from "dayjs";
import { Link } from "react-router-dom";
import { Box, Button, Typography } from "@mui/material";
import { getGameDuration } from "@/utils/lib";
import { SortableHeader } from "@/components/table/styles";
import { getMapIconSrc } from "@/utils/map-images.mjs";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";

export const createGameListColumns = (t) => [
{
  accessorKey: "id",
  header: "ID",
  cell: ({ cell }) => {
    const matchId = cell.getValue();
    return (
      <Button component={Link} to={`/stats/games/${matchId}`} variant="text">
        {matchId}
      </Button>
    );
  },
  meta: {
    variant: "short",
  },
},

{
  header: SortableHeader(t("stats.games.map")),
  id: "map",
  accessorKey: "map",
  minSize: 200,
  size: 200,
  filterFn: "mapFilter",
  cell: ({ cell }) => {
    const matchMap = cell.getValue();
    const size = 60;
    const ratio = 9 / 16;
    return (
      <Box
        sx={{
          display: "flex",
          flexDirection: "row",
          gap: 0.5,
          width: "max-content",
        }}
      >
        <img
          src={getMapIconSrc(matchMap)}
          width={size}
          height={size * ratio}
          alt=""
        />
        <Box sx={{ display: "flex", flexDirection: "column" }}>
          <Typography variant="body1" sx={{ fontWeight: 600, lineHeight: 1 }}>
            {matchMap.map.pretty_name}
          </Typography>
          <Typography
            variant="subtitle2"
            sx={{ display: "flex", flexDirection: "row", fontWeight: 400 }}
          >
            <Box component="span" sx={{ paddingRight: 0.5 }}>
              {getMapModeLabel(t, matchMap.game_mode)}
            </Box>
            <Box component="span">{getMapEnvironmentLabel(t, matchMap.environment)}</Box>
          </Typography>
        </Box>
      </Box>
    );
  },
  meta: {
    variant: "content",
  },
},

{
  header: t("stats.games.result"),
  id: "result",
  accessorFn: (row) =>
    `${row.result?.allied ?? "?"} - ${row.result?.axis ?? "?"}`,
  meta: {
    variant: "short",
  },
},

{
  header: SortableHeader(t("stats.games.start")),
  accessorKey: "start",
  cell: ({ cell }) => dayjs(cell.getValue()).format("L LT"),
  meta: {
    variant: "name",
  },
},

{
  header: SortableHeader(t("stats.games.duration")),
  accessorKey: "duration",
  cell: ({ row }) => getGameDuration(row.original.start, row.original.end),
},
];
