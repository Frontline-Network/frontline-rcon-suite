import React, { useMemo, useState } from "react";
import {
  Button,
  ButtonGroup,
  OutlinedInput,
  Slider,
  Stack,
  Typography,
} from "@mui/material";
import RestoreRoundedIcon from "@mui/icons-material/RestoreRounded";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import MapAutocomplete from "@/components/shared/MapAutocomplete";
import { cmd } from "@/utils/fetchUtils";
import {
  ControlActionBar,
  ControlPageLayout,
  ControlRow,
  ControlSectionHeader,
  RowStatus,
} from "../ControlPageLayout";
import { getMaxValue, getMinValue, getStep } from "../utils";

const clone = (value) => JSON.parse(JSON.stringify(value));

function TimerControl({ settingKey, value, disabled, onChange, onUseDefault }) {
  return (
    <Stack direction="row" spacing={1} alignItems="center">
      <Slider
        value={Number(value)}
        min={getMinValue(settingKey)}
        max={getMaxValue(settingKey)}
        step={getStep(settingKey)}
        disabled={disabled}
        onChange={(_, next) => onChange(next)}
        aria-label={settingKey}
        size="small"
        sx={{ flex: 1, minWidth: 120 }}
      />
      <OutlinedInput
        value={value}
        type="number"
        size="small"
        disabled={disabled}
        inputProps={{
          min: getMinValue(settingKey),
          max: getMaxValue(settingKey),
          step: getStep(settingKey),
          "aria-label": settingKey,
        }}
        onChange={(event) => {
          const next = Number(event.target.value);
          if (!Number.isNaN(next)) onChange(next);
        }}
        sx={{ width: 72, borderRadius: 0 }}
      />
      <Button
        variant="outlined"
        size="small"
        startIcon={<RestoreRoundedIcon />}
        disabled={disabled}
        onClick={onUseDefault}
        sx={{ borderRadius: 0, whiteSpace: "nowrap" }}
      >
        Standard
      </Button>
    </Stack>
  );
}

function ToggleButtons({ value, onChange, disabled }) {
  return (
    <ButtonGroup
      size="small"
      disabled={disabled}
      sx={{ "& .MuiButton-root": { minWidth: 96, borderRadius: 0 } }}
    >
      <Button
        variant={!value ? "contained" : "outlined"}
        color={!value ? "inherit" : "primary"}
        onClick={() => onChange(false)}
      >
        Inaktiv
      </Button>
      <Button
        variant={value ? "contained" : "outlined"}
        onClick={() => onChange(true)}
      >
        Aktiv
      </Button>
    </ButtonGroup>
  );
}

export default function GameControlMatrix({ loaderData }) {
  const { t } = useTranslation();
  const sections = [
    { key: "weather", label: t("settings.game.dynamicWeather") },
    { key: "match", label: t("settings.game.matchTimers") },
    { key: "warmup", label: t("settings.game.warmupTimers") },
  ];
  const initialTimers = useMemo(() => {
    const values = {};
    Object.entries(loaderData.timers.match).forEach(([mode, timer]) => {
      values[`match_${mode}_timer`] = Number(timer.default);
    });
    Object.entries(loaderData.timers.warmup).forEach(([mode, timer]) => {
      values[`warmup_${mode}_timer`] = Number(timer.default);
    });
    return values;
  }, [loaderData.timers]);
  const initialWeather = useMemo(
    () => ({ map_name: loaderData.maps[0]?.id || "", enabled: false }),
    [loaderData.maps]
  );
  const [active, setActive] = useState("weather");
  const [baseline, setBaseline] = useState(() => clone(initialTimers));
  const [draft, setDraft] = useState(() => clone(initialTimers));
  const [weatherBaseline, setWeatherBaseline] = useState(() =>
    clone(initialWeather)
  );
  const [weatherDraft, setWeatherDraft] = useState(() => clone(initialWeather));
  const [timerActions, setTimerActions] = useState({});
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);

  const timerRows = useMemo(
    () => ({
      match: Object.keys(loaderData.timers.match).map((mode) => ({
        key: `match_${mode}_timer`,
        mode,
        title: t("settings.game.matchTimer", {
          mode: t(`views.team.gameModes.${mode}`, { defaultValue: mode }),
        }),
        description:
          mode === "offensive"
            ? t("settings.game.offensiveTimerDescription")
            : t("settings.game.matchTimerDescription"),
        set: cmd.SET_MATCH_TIMER,
        remove: cmd.REMOVE_MATCH_TIMER,
      })),
      warmup: Object.keys(loaderData.timers.warmup).map((mode) => ({
        key: `warmup_${mode}_timer`,
        mode,
        title: t("settings.game.warmupTimer", {
          mode: t(`views.team.gameModes.${mode}`, { defaultValue: mode }),
        }),
        description: t("settings.game.warmupTimerDescription"),
        set: cmd.SET_WARMUP_TIMER,
        remove: cmd.REMOVE_WARMUP_TIMER,
      })),
    }),
    [loaderData.timers, t]
  );

  const weatherDirty =
    JSON.stringify(weatherBaseline) !== JSON.stringify(weatherDraft);
  const dirtyTimerKeys = Object.keys(draft).filter(
    (key) => draft[key] !== baseline[key] || timerActions[key] === "remove"
  );
  const dirtyCount = dirtyTimerKeys.length + (weatherDirty ? 1 : 0);

  const updateTimer = (key, value) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setTimerActions((current) => ({ ...current, [key]: "set" }));
    setErrors((current) => ({ ...current, [key]: undefined }));
  };

  const reset = () => {
    setDraft(clone(baseline));
    setWeatherDraft(clone(weatherBaseline));
    setTimerActions({});
    setErrors({});
  };

  const save = async () => {
    setSaving(true);
    const failed = {};
    if (weatherDirty) {
      try {
        await cmd.SET_DYNAMIC_WEATHER_ENABLED({
          payload: weatherDraft,
          throwRouteError: false,
        });
        setWeatherBaseline(clone(weatherDraft));
      } catch (error) {
        failed.weather = error.message;
      }
    }

    for (const section of ["match", "warmup"]) {
      for (const row of timerRows[section]) {
        if (!dirtyTimerKeys.includes(row.key)) continue;
        try {
          if (timerActions[row.key] === "remove") {
            await row.remove({
              payload: { game_mode: row.mode },
              throwRouteError: false,
            });
          } else {
            await row.set({
              payload: { game_mode: row.mode, length: draft[row.key] },
              throwRouteError: false,
            });
          }
          setBaseline((current) => ({ ...current, [row.key]: draft[row.key] }));
          setTimerActions((current) => ({ ...current, [row.key]: undefined }));
        } catch (error) {
          failed[row.key] = error.message;
        }
      }
    }
    setErrors(failed);
    setSaving(false);
    if (Object.keys(failed).length) {
      toast.error("Einige Spielwerte konnten nicht gespeichert werden.");
    } else {
      toast.success("Spiel- und Rundenwerte wurden gespeichert.");
    }
  };

  return (
    <>
      <ControlPageLayout
        sections={sections}
        active={active}
        onChange={setActive}
      >
        {active === "weather" ? (
          <>
            <ControlSectionHeader
              title={t("settings.game.dynamicWeather")}
              description={t("settings.game.dynamicWeatherDescription")}
            />
            <ControlRow
              title={t("maps.current")}
              description="Wähle die Karte, für die dynamisches Wetter geändert werden soll."
              value={
                <MapAutocomplete
                  options={loaderData.maps}
                  selected={weatherDraft.map_name}
                  onSelect={(map_name) =>
                    setWeatherDraft((current) => ({ ...current, map_name }))
                  }
                  label={t("maps.current")}
                />
              }
              meta="Kartenspezifisch"
              status={<RowStatus dirty={weatherDirty} error={errors.weather} />}
            />
            <ControlRow
              title={t("settings.game.dynamicWeatherToggle")}
              description={t("settings.game.dynamicWeatherDescription")}
              value={
                <ToggleButtons
                  value={weatherDraft.enabled}
                  onChange={(enabled) =>
                    setWeatherDraft((current) => ({ ...current, enabled }))
                  }
                  disabled={saving}
                />
              }
              meta={weatherDraft.enabled ? "Dynamisch" : "Statisch"}
              status={<RowStatus dirty={weatherDirty} error={errors.weather} />}
            />
          </>
        ) : (
          <>
            <ControlSectionHeader
              title={sections.find((section) => section.key === active)?.label}
              description={
                active === "match"
                  ? "Lege die Dauer der jeweiligen Spielmodi fest."
                  : "Lege die Vorbereitungszeit vor dem Rundenstart fest."
              }
            />
            {timerRows[active].map((row) => {
              const dirty =
                draft[row.key] !== baseline[row.key] ||
                timerActions[row.key] === "remove";
              return (
                <ControlRow
                  key={row.key}
                  title={row.title}
                  description={row.description}
                  value={
                    <TimerControl
                      settingKey={row.key}
                      value={draft[row.key]}
                      disabled={saving}
                      onChange={(value) => updateTimer(row.key, value)}
                      onUseDefault={() =>
                        setTimerActions((current) => ({
                          ...current,
                          [row.key]: "remove",
                        }))
                      }
                    />
                  }
                  meta={
                    timerActions[row.key] === "remove"
                      ? "Serverstandard wird verwendet"
                      : `${draft[row.key]} Minuten`
                  }
                  status={<RowStatus dirty={dirty} error={errors[row.key]} />}
                />
              );
            })}
          </>
        )}
      </ControlPageLayout>

      <Stack spacing={0.35} sx={{ mt: 1.25 }}>
        <Typography variant="caption" color="text.secondary">
          {t("settings.game.timerExample")}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("settings.game.changeNote")}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t("settings.game.removeTimerNote")}
        </Typography>
      </Stack>
      <ControlActionBar
        dirtyCount={dirtyCount}
        onReset={reset}
        onSave={save}
        saving={saving}
      />
    </>
  );
}
