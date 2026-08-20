import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import HistoryIcon from "@mui/icons-material/History";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import { useTranslation } from "react-i18next";
import { getGeneralSettingMetadata } from "./setting-metadata";

const valuesEqual = (left, right) =>
  JSON.stringify(left) === JSON.stringify(right);

const formatValue = (value, unit, t) => {
  if (unit === "boolean") {
    return t(value ? "common.enabled" : "common.disabled");
  }
  if (unit === "thresholds") {
    return Array.isArray(value)
      ? value.map(([players, votes]) => `${players} → ${votes}`).join(" · ")
      : t("common.unknown");
  }
  if (value === null || value === undefined) return t("common.unknown");
  return t(`settingEffect.units.${unit}`, { value });
};

export default function SettingEffectSummary({
  settingKey,
  serverValue,
  draftValue,
  dataUpdatedAt,
  canChange,
  onUseRecommended,
}) {
  const { t, i18n } = useTranslation();
  const metadata = getGeneralSettingMetadata(settingKey);
  if (!metadata) return null;

  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const hasUnsavedChanges = !valuesEqual(serverValue, draftValue);
  const lastRead = dataUpdatedAt
    ? new Date(dataUpdatedAt).toLocaleString(language)
    : t("settingEffect.notAvailable");

  return (
    <Stack
      spacing={1.25}
      data-testid={`setting-effect-${settingKey}`}
      sx={{
        mt: 2,
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        useFlexGap
        flexWrap="wrap"
      >
        <Box sx={{ minWidth: 0, flex: "1 1 10rem" }}>
          <Typography variant="caption" color="text.secondary">
            {t("settingEffect.serverValue")}
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {formatValue(serverValue, metadata.unit, t)}
          </Typography>
        </Box>
        <Box sx={{ minWidth: 0, flex: "1 1 10rem" }}>
          <Typography variant="caption" color="text.secondary">
            {t("settingEffect.draftValue")}
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {formatValue(draftValue, metadata.unit, t)}
          </Typography>
        </Box>
        <Box sx={{ minWidth: 0, flex: "1 1 10rem" }}>
          <Typography variant="caption" color="text.secondary">
            {t("settingEffect.recommendedValue")}
          </Typography>
          <Typography variant="body2" fontWeight={700}>
            {metadata.recommendedValue === null
              ? t("settingEffect.notDocumented")
              : formatValue(metadata.recommendedValue, metadata.unit, t)}
          </Typography>
        </Box>
      </Stack>

      {hasUnsavedChanges && (
        <Alert severity="info" icon={<InfoOutlinedIcon fontSize="inherit" />}>
          {t("settingEffect.unsaved")}
        </Alert>
      )}

      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
        <Chip
          icon={<SportsEsportsIcon />}
          label={t("settingEffect.games")}
          size="small"
          variant="outlined"
        />
        <Chip
          icon={<CheckCircleOutlineIcon />}
          label={t("settingEffect.appliesImmediately")}
          size="small"
          variant="outlined"
        />
        <Chip
          icon={<HistoryIcon />}
          label={t("settingEffect.lastRead", { time: lastRead })}
          size="small"
          variant="outlined"
        />
      </Stack>

      <Typography variant="caption" color="text.secondary">
        {t(`settingEffect.conflicts.${metadata.conflictKey}`)}
      </Typography>

      <Divider />
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        justifyContent="space-between"
        alignItems={{ sm: "center" }}
      >
        <Typography variant="caption" color="text.secondary">
          {t("settingEffect.auditUnavailable")}
        </Typography>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={0.5}>
          <Button
            size="small"
            variant="text"
            onClick={() => onUseRecommended(serverValue)}
            disabled={!canChange || !hasUnsavedChanges}
          >
            {t("settingEffect.discardDraft")}
          </Button>
          {metadata.recommendedValue !== null && (
            <Button
              size="small"
              variant="text"
              onClick={() => onUseRecommended(metadata.recommendedValue)}
              disabled={
                !canChange || valuesEqual(draftValue, metadata.recommendedValue)
              }
            >
              {t("settingEffect.useRecommended")}
            </Button>
          )}
        </Stack>
      </Stack>
    </Stack>
  );
}
