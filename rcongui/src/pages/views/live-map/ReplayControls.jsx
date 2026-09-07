import {
  Box,
  Button,
  MenuItem,
  Slider,
  Stack,
  Tab,
  Tabs,
  TextField,
  Typography,
} from "@mui/material";

export default function ReplayControls({
  t,
  language,
  mode,
  onMode,
  rounds,
  roundId,
  onRound,
  historyEnd,
  onHistoryEnd,
  onLoad,
  loading,
  replay,
  range,
  playing,
  onPlaying,
  onSeek,
  onSeekCommitted,
  onStep,
  speed,
  onSpeed,
  eventMarks,
  markerCounts,
  onLive,
}) {
  const available =
    mode === "archive" ? rounds.filter((r) => r.archive) : rounds;
  return (
    <Box>
      <Tabs
        value={mode}
        onChange={(_, value) => onMode(value)}
        variant="scrollable"
      >
        <Tab value="live" label={t("live")} />
        <Tab value="replay" label={t("replay")} />
        <Tab value="archive" label={t("archives")} />
      </Tabs>
      {mode !== "live" && (
        <Stack gap={1} sx={{ p: 1.5 }}>
          <Stack
            direction="row"
            useFlexGap
            flexWrap="wrap"
            gap={1}
            alignItems="center"
          >
            <TextField
              size="small"
              select
              label={t("round")}
              value={roundId}
              onChange={(event) => onRound(event.target.value)}
              sx={{ minWidth: 240, flex: "1 1 240px" }}
            >
              {available.map((round) => (
                <MenuItem key={round.round_id} value={round.round_id}>
                  {new Date(round.end * 1000).toLocaleString(language)}
                  {round.archive ? ` · ${t("secured")}` : ""}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              size="small"
              type="datetime-local"
              label={t("time")}
              value={historyEnd}
              onChange={(event) => onHistoryEnd(event.target.value)}
              slotProps={{ inputLabel: { shrink: true } }}
            />
            <Button disabled={loading || !roundId} onClick={onLoad}>
              {t("history")}
            </Button>
            <Button variant="contained" onClick={onLive}>
              {t("backLive")}
            </Button>
          </Stack>
          {replay !== null && range && (
            <>
              <Stack
                direction="row"
                useFlexGap
                flexWrap="wrap"
                gap={0.5}
                alignItems="center"
              >
                <Button size="small" onClick={() => onStep("sample", -1)}>
                  {t("previousSample")}
                </Button>
                <Button size="small" onClick={() => onStep("seconds", -10)}>
                  −10 s
                </Button>
                <Button
                  size="small"
                  variant="outlined"
                  onClick={() => onPlaying(!playing)}
                >
                  {t(playing ? "pause" : "play")}
                </Button>
                <Button size="small" onClick={() => onStep("seconds", 10)}>
                  +10 s
                </Button>
                <Button size="small" onClick={() => onStep("sample", 1)}>
                  {t("nextSample")}
                </Button>
                <TextField
                  size="small"
                  select
                  label={t("speed")}
                  value={speed}
                  onChange={(event) => onSpeed(Number(event.target.value))}
                  sx={{ width: 92 }}
                >
                  {[0.5, 1, 2, 4].map((value) => (
                    <MenuItem key={value} value={value}>
                      {value}×
                    </MenuItem>
                  ))}
                </TextField>
                <Typography
                  variant="body2"
                  sx={{ ml: "auto", fontVariantNumeric: "tabular-nums" }}
                >
                  {new Date(replay * 1000).toLocaleString(language)}
                </Typography>
              </Stack>
              <Slider
                aria-label={t("time")}
                min={range.start}
                max={range.end}
                value={Math.max(range.start, Math.min(replay, range.end))}
                marks={eventMarks}
                onChange={(_, value) => onSeek(value)}
                onChangeCommitted={(_, value) => onSeekCommitted(value)}
                valueLabelDisplay="auto"
                valueLabelFormat={(value) =>
                  new Date(value * 1000).toLocaleTimeString(language)
                }
              />
              <Typography variant="caption" color="text.secondary">
                {t("timelineHelp")}
              </Typography>
              <Stack direction="row" useFlexGap flexWrap="wrap" gap={1.5}>
                {["kill", "teamkill", "data_gap", "detection"].map(
                  (kind) =>
                    (markerCounts[kind] || 0) > 0 && (
                      <Typography key={kind} variant="caption" fontWeight={700}>
                        {t(kind)}: {markerCounts[kind]}
                      </Typography>
                    )
                )}
              </Stack>
            </>
          )}
        </Stack>
      )}
    </Box>
  );
}
