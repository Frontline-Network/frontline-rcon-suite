import { useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { gameQueryOptions } from "@/queries/game-query";
import PlayersTable from "./game-table";
import {
  useReactTable,
  getCoreRowModel,
  getFilteredRowModel,
  getSortedRowModel,
  getExpandedRowModel,
  getPaginationRowModel,
} from "@tanstack/react-table";
import { createGameColumns } from "./game-columns";
import { useCallback, useMemo, useState } from "react";
import dayjs from "dayjs";
import { Typography, Box, Paper } from "@mui/material";
import Grid from "@mui/material/Grid2";
import { useTranslation } from "react-i18next";
import { ActionMenu } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";

const HISTORICAL_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: false,
});

export const StatCard = ({ playerStats, statsKey, limit = 10 }) => {
  const { t } = useTranslation();
  const title = t(`stats.gameDetails.metrics.${statsKey}`, {
    defaultValue: statsKey.replace("_", " ").toUpperCase(),
  });
  return (
    <Grid size={{ xs: 12, sm: 6, md: 4, xl: 2 }}>
      <Paper sx={{ p: 2 }}>
        <Typography variant="h6" sx={{ mb: 2 }}>
          {t("stats.gameDetails.topStat", { stat: title })}
        </Typography>
        {[...playerStats]
          .sort((a, b) => b[statsKey] - a[statsKey])
          .slice(0, limit)
          .map(
            (player, i) =>
              player[statsKey] > 0 && (
                <Box
                  key={player.player_id}
                  sx={{
                    display: "flex",
                    justifyContent: "space-between",
                    mb: 1,
                  }}
                >
                  <Typography variant="body2">
                    {i === 0
                      ? `🥇 ${player.player}`
                      : i === 1
                      ? `🥈 ${player.player}`
                      : i === 2
                      ? `🥉 ${player.player}`
                      : (i + 1).toString() + ". " + player.player}
                  </Typography>
                  <Box sx={{ flexGrow: 1, minWidth: 10 }} />
                  <Typography variant="body2" color="primary">
                    {player[statsKey]}
                  </Typography>
                </Box>
              )
          )}
      </Paper>
    </Grid>
  );
};

export const CompletedGameDetails = ({ mapLayer, result, start, end, id }) => {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        display: "flex",
        justifyContent: "space-between",
        alignItems: "center",
        mb: 4,
      }}
    >
      <Box>
        <Typography variant="h4" sx={{ mb: 2 }}>
          {mapLayer.map.pretty_name}
        </Typography>
        {result && (
          <Typography variant="h5" sx={{ color: "text.secondary" }}>
            {t("stats.gameDetails.score")}:{" "}
            <Box component="span" sx={{ color: "primary.main" }}>
              {t("views.team.allies")} {result?.allied ?? "?"}
            </Box>{" "}
            :{" "}
            <Box component="span" sx={{ color: "error.main" }}>
              {result?.axis ?? "?"} {t("views.team.axis")}
            </Box>
          </Typography>
        )}
      </Box>
      <Box sx={{ textAlign: "right" }}>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          {dayjs(start).format("L LT")}
        </Typography>
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          {t("stats.gameDetails.duration")}:{" "}
          {dayjs.duration(dayjs(end) - dayjs(start)).format("HH:mm")}
        </Typography>
        <Typography variant="subtitle2" color="text.secondary">
          {t("stats.gameDetails.gameId")}: {id}
        </Typography>
      </Box>
    </Box>
  );
};

export const GameTable = ({ playerStats, columns }) => {
  const [playersRowSelection, setPlayersRowSelection] = useState({});
  const [playerActionMenu, setPlayerActionMenu] = useState({
    anchorEl: null,
    player: null,
  });
  const openPlayerActionMenu = useCallback((anchorEl, player) => {
    setPlayerActionMenu({ anchorEl, player });
  }, []);
  const setPlayerActionMenuAnchor = useCallback((anchorEl) => {
    setPlayerActionMenu((current) => ({ ...current, anchorEl }));
  }, []);
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 100,
  });

  const table = useReactTable({
    data: playerStats,
    columns: columns,
    getRowCanExpand: () => true,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    onRowSelectionChange: setPlayersRowSelection,
    getExpandedRowModel: getExpandedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onPaginationChange: setPagination,
    getRowId: (row) => row.player_id,
    meta: {
      openPlayerActionMenu,
      activePlayerActionId: playerActionMenu.anchorEl
        ? playerActionMenu.player?.player_id
        : null,
    },
    initialState: {
      sorting: [{ id: "time", desc: true }],
    },
    state: {
      rowSelection: playersRowSelection,
      pagination,
    },
  });

  const selectedPlayers = useMemo(() => {
    return Object.keys(playersRowSelection)
      .map((key) => {
        return (
          table.getSelectedRowModel().rows.find((row) => row.id === key)
            ?.original ?? null
        );
      })
      .filter(Boolean)
      .map((playerRow) => ({
        player_id: playerRow.player_id,
        name: playerRow.player,
      }));
  }, [playersRowSelection, table.getSelectedRowModel().rows]);

  return (
    <>
      <PlayersTable table={table} selectedPlayers={selectedPlayers} />
      {playerActionMenu.player ? (
        <ActionMenu
          actions={HISTORICAL_PLAYER_ACTIONS}
          recipients={playerActionMenu.player}
          anchorEl={playerActionMenu.anchorEl}
          setAnchorEl={setPlayerActionMenuAnchor}
          menuId="completed-game-player-actions-menu"
        />
      ) : null}
    </>
  );
};

const CompletedGamePage = () => {
  const { t } = useTranslation();
  const columns = useMemo(() => createGameColumns(t), [t]);
  const { gameId } = useParams();

  const { data, isLoading, error } = useQuery({
    ...gameQueryOptions.detail(gameId),
  });

  if (isLoading) {
    return <div>{t("common.loading")}</div>;
  }

  if (error) {
    return (
      <div>{t("stats.gameDetails.loadError", { message: error.message })}</div>
    );
  }

  return (
    <div>
      <Box sx={{ p: 4 }}>
        <CompletedGameDetails
          mapLayer={data.map}
          result={data.result}
          start={data.start}
          end={data.end}
          id={data.id}
        />
        <Grid container spacing={3} sx={{ mb: 4 }}>
          <StatCard playerStats={data.player_stats} statsKey="kills" />
          <StatCard playerStats={data.player_stats} statsKey="combat" />
          <StatCard playerStats={data.player_stats} statsKey="support" />
          <StatCard playerStats={data.player_stats} statsKey="offense" />
          <StatCard playerStats={data.player_stats} statsKey="defense" />
          <StatCard playerStats={data.player_stats} statsKey="kills_streak" />
        </Grid>
        <GameTable playerStats={data.player_stats} columns={columns} />
      </Box>
    </div>
  );
};

export default CompletedGamePage;
