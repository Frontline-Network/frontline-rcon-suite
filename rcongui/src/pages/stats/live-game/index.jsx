import { cmd } from "@/utils/fetchUtils";
import { createGameColumns } from "../games/[gameId]/game-columns";
import { useLoaderData } from "react-router-dom";
import {
  Stack,
  Typography,
  Accordion,
  AccordionSummary,
  AccordionDetails,
} from "@mui/material";
import { GameTable } from "../games/[gameId]";
import { StatCard } from "../games/[gameId]";
import Grid from "@mui/material/Grid2";
import { gameQueryOptions } from "@/queries/game-query";
import { useQuery } from "@tanstack/react-query";
import { Board } from "@/components/game/Board";
import dayjs from "dayjs";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { useTranslation } from "react-i18next";
import { useMemo } from "react";
import PageHeader from "@/components/shared/PageHeader";
import { demoMapLayers, demoScorePlayers, isFakeMode } from "@/mirage/demo-data";

export const loader = async () => {
  if (isFakeMode()) {
    return {
      stats: { stats: demoScorePlayers },
      game: { time_remaining: 3427, score: { allied: 3, axis: 2 }, current_map: demoMapLayers[0], player_count_by_team: { allied: 43, axis: 43 } },
    };
  }
  const stats = await cmd.GET_LIVE_GAME();
  const game = await cmd.GET_PUBLIC_GAME_STATE();
  return { stats, game };
};

const LiveGamePage = () => {
  const { t } = useTranslation();
  const columns = useMemo(() => createGameColumns(t), [t]);
  const initialData = useLoaderData();

  const {
    data: { stats },
    isLoading: statsIsLoading,
  } = useQuery({
    ...gameQueryOptions.live(),
    initialData: initialData.stats,
  });

  const { data: game, isLoading: gameIsLoading } = useQuery({
    ...gameQueryOptions.publicState(),
    initialData: initialData.game,
  });

  if (statsIsLoading || gameIsLoading) {
    return <div>{t("common.loading")}</div>;
  }

  return (
    <Stack gap={3}>
      <PageHeader
        eyebrow={t("stats.liveGame.eyebrow")}
        title={t("stats.liveGame.title")}
        subtitle={t("stats.liveGame.subtitle")}
      />
      <section id="game-board">
        <Board
          data={{
            // convert seconds to "HH:mm:ss"
            raw_time_remaining: dayjs
              .duration(game.time_remaining, "seconds")
              .format("HH:mm:ss"),
            allied_score: game.score.allied,
            axis_score: game.score.axis,
            current_map: game.current_map,
            num_allied_players: game.player_count_by_team.allied,
            num_axis_players: game.player_count_by_team.axis,
          }}
        />
      </section>

      <Accordion>
        <AccordionSummary expandIcon={<ExpandMoreIcon />}>
          <Typography>{t("stats.liveGame.playerStatistics")}</Typography>
        </AccordionSummary>
        <AccordionDetails>
          <Grid container spacing={3} sx={{ mb: 4 }}>
            <StatCard playerStats={stats} statsKey="kills" />
            <StatCard playerStats={stats} statsKey="combat" />
            <StatCard playerStats={stats} statsKey="support" />
            <StatCard playerStats={stats} statsKey="offense" />
            <StatCard playerStats={stats} statsKey="defense" />
            <StatCard playerStats={stats} statsKey="kills_streak" />
          </Grid>
        </AccordionDetails>
      </Accordion>

      <section id="players-table">
        <GameTable playerStats={stats} columns={columns} />
      </section>
    </Stack>
  );
};

export default LiveGamePage;
