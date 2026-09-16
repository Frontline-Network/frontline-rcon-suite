import { useEffect, useState } from "react";
import { Alert, Box, Button, Chip, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { copy } from "./copy";
import { translateLeadershipResult } from "./result-copy";

export default function VotePanel({ vote, canCancel, onCancel, pending }) {
  const { t, i18n } = useTranslation();
  const c = copy[i18n.language?.startsWith("de") ? "de" : "en"];
  const [now, setNow] = useState(Date.now());
  const running = ["confirming", "warning", "active", "inviting"].includes(
    vote.status
  );
  useEffect(() => {
    if (!running) return;
    const timer = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(timer);
  }, [running]);
  const left = Math.max(0, Math.ceil((vote.ends_at * 1000 - now) / 1000));
  const tone =
    vote.status === "unknown"
      ? "warning"
      : vote.status === "kicked"
      ? "success"
      : "info";
  return (
    <Stack
      spacing={1.5}
      sx={{
        p: 2,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
        <Typography component="h3" variant="h6">
          {c.title} ·{" "}
          {vote.target_role === "commander"
            ? "Commander"
            : `Squad ${vote.squad}`}
        </Typography>
        <Chip
          size="small"
          variant="outlined"
          label={vote.mode === "active" ? c.activeMode : c.dryRun}
        />
        <Chip
          size="small"
          color={tone}
          label={c.statuses[vote.status] || vote.status}
        />
      </Stack>
      <Typography>
        {c.target}: {vote.target_name} ·{" "}
        {vote.team === "allies" || vote.team === "axis"
          ? t(`settingsPanels.autobalancer.${vote.team}`)
          : vote.team}
      </Typography>
      <Typography sx={{ overflowWrap: "anywhere" }}>
        {c.reason}: „{vote.reason || c.none}“
      </Typography>
      <Typography>
        {c.yes}: {vote.yes || 0} · {c.no}: {vote.no || 0} · {c.required}:{" "}
        {vote.required ?? "–"} /{" "}
        {vote.participant_count ?? Object.keys(vote.electorate || {}).length}
      </Typography>
      <Typography>{running ? `${left} ${c.remaining}` : ""}</Typography>
      {vote.result && (
        <Alert severity={tone}>
          {c.result}:{" "}
          {translateLeadershipResult(vote.result, i18n.resolvedLanguage)}
        </Alert>
      )}
      {Object.keys(vote.electorate || {}).length > 0 && (
        <Box component="details">
          <Typography component="summary" sx={{ cursor: "pointer" }}>
            {c.ballots} · {c.electorate}
          </Typography>
          {Object.entries(vote.electorate).map(([id, player]) => (
            <Typography
              key={id}
              variant="body2"
              sx={{ overflowWrap: "anywhere", py: 0.5 }}
            >
              {player.name || id}:{" "}
              {player.valid === false
                ? c.invalid
                : vote.ballots?.[id]
                ? vote.ballots[id].yes
                  ? c.yes
                  : c.no
                : c.none}
            </Typography>
          ))}
        </Box>
      )}
      {canCancel &&
        ["confirming", "warning", "inviting", "active", "executing"].includes(
          vote.status
        ) && (
          <Button
            variant="outlined"
            disabled={pending}
            onClick={onCancel}
            sx={{ alignSelf: "flex-start" }}
          >
            {c.cancel}
          </Button>
        )}
    </Stack>
  );
}
import "@/i18n/register-settings-panels";
