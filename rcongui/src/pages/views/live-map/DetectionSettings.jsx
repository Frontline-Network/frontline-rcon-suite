import { useEffect, useState } from "react";
import {
  Box,
  Button,
  FormControlLabel,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";

const fields = [
  ["min_kills", "minimumKills"],
  ["killrate_infantry", "infantryKpm"],
  ["killrate_mg", "mgKpm"],
  ["killrate_armor", "armorKpm"],
  ["killrate_artillery", "artilleryKpm"],
  ["burst_kills", "burstKills"],
  ["burst_unique_victims", "burstVictims"],
  ["burst_seconds", "burstSeconds"],
  ["movement_mps", "movementMps"],
  ["movement_consecutive", "movementConsecutive"],
];

export default function DetectionSettings({ settings, mutation, t }) {
  const [draft, setDraft] = useState(null);
  useEffect(() => {
    if (settings) setDraft(settings);
  }, [settings]);
  if (!draft) return null;
  const updateProfile = (key, value) =>
    setDraft((current) => ({
      ...current,
      detection_profile: { ...current.detection_profile, [key]: Number(value) },
    }));
  return (
    <Box
      component="details"
      sx={{
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        p: 1.5,
        mt: 1,
      }}
    >
      <Typography
        component="summary"
        fontWeight={800}
        sx={{ cursor: "pointer" }}
      >
        {t("detectionSettings")}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ my: 1 }}>
        {t("detectionSettingsHelp")}
      </Typography>
      <Stack direction="row" useFlexGap flexWrap="wrap" gap={1}>
        <FormControlLabel
          label={t("archiveEnabled")}
          control={
            <Switch
              checked={draft.archive_enabled}
              onChange={(_, value) =>
                setDraft({ ...draft, archive_enabled: value })
              }
            />
          }
        />
        <FormControlLabel
          label={t("detectionEnabled")}
          control={
            <Switch
              checked={draft.detection_enabled}
              onChange={(_, value) =>
                setDraft({ ...draft, detection_enabled: value })
              }
            />
          }
        />
      </Stack>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))",
          gap: 1,
          my: 1,
        }}
      >
        {fields.map(([key, label]) => (
          <TextField
            key={key}
            size="small"
            type="number"
            label={t(label)}
            value={draft.detection_profile[key]}
            onChange={(event) => updateProfile(key, event.target.value)}
          />
        ))}
      </Box>
      <Button
        variant="contained"
        disabled={mutation.isPending}
        onClick={() => mutation.mutate({ path: "settings", data: draft })}
      >
        {t("applyProfile")}
      </Button>
    </Box>
  );
}
