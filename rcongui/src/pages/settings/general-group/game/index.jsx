import React from "react";
import { Divider, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useLoaderData } from "react-router-dom";
import { DynamicWeatherSettings, SliderTimer } from "../components";
import { cmd } from "@/utils/fetchUtils";
import SelfImprovementIcon from "@mui/icons-material/SelfImprovement";
import TimerIcon from "@mui/icons-material/Timer";
import CloudIcon from "@mui/icons-material/Cloud";
import { useTranslation } from "react-i18next";

function GameTimersSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();

  return (
    <Stack gap={2}>
      <Divider>{t("settings.game.dynamicWeather")}</Divider>
      <Grid container spacing={1}>
        <DynamicWeatherSettings
          options={loaderData.maps}
          settingKey={`map_name`}
          title={t("settings.game.dynamicWeatherToggle")}
          subheader={t("settings.game.dynamicWeatherDescription")}
          icon={CloudIcon}
          mutationFn={cmd.SET_DYNAMIC_WEATHER_ENABLED}
        />
      </Grid>
      <Divider>{t("settings.game.matchTimers")}</Divider>
      <Grid container spacing={1}>
        {Object.keys(loaderData.timers.match).map((gameMode) => (
          <SliderTimer
            key={`match_${gameMode}_timer`}
            settingKey={`match_${gameMode}_timer`}
            gameMode={gameMode}
            title={t("settings.game.matchTimer", { mode: t(`views.team.gameModes.${gameMode}`, { defaultValue: gameMode }) })}
            subheader={gameMode === "offensive" ? t("settings.game.offensiveTimerDescription") : t("settings.game.matchTimerDescription")}
            icon={TimerIcon}
            setTimer={cmd.SET_MATCH_TIMER}
            removeTimer={cmd.REMOVE_MATCH_TIMER}
            initialData={loaderData.timers.match[gameMode].default}
          />
        ))}
      </Grid>
      <Divider>{t("settings.game.warmupTimers")}</Divider>
      <Grid container spacing={1}>
        {Object.keys(loaderData.timers.warmup).map((gameMode) => (
          <SliderTimer
            key={`warmup_${gameMode}_timer`}
            settingKey={`warmup_${gameMode}_timer`}
            gameMode={gameMode}
            title={t("settings.game.warmupTimer", { mode: t(`views.team.gameModes.${gameMode}`, { defaultValue: gameMode }) })}
            subheader={t("settings.game.warmupTimerDescription")}
            icon={SelfImprovementIcon}
            setTimer={cmd.SET_WARMUP_TIMER}
            removeTimer={cmd.REMOVE_WARMUP_TIMER}
            initialData={loaderData.timers.warmup[gameMode].default}
          />
        ))}
      </Grid>
      <Typography variant="body2" color="text.secondary" component="div">
        <em>{t("settings.game.timerExample")}</em>
      </Typography>
      <Typography variant="body2" color="text.secondary" component="div">
        <em>{t("settings.game.changeNote")}</em>
      </Typography>
      <Typography variant="body2" color="text.secondary" component="div">
        <em>{t("settings.game.removeTimerNote")}</em>
      </Typography>
    </Stack>
  );
}

export default GameTimersSettings;
