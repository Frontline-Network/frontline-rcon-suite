import { useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Slider,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import AddIcon from "@mui/icons-material/Add";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import LinkOutlinedIcon from "@mui/icons-material/LinkOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import RemoveIcon from "@mui/icons-material/Remove";
import RedeemOutlinedIcon from "@mui/icons-material/RedeemOutlined";
import SettingsOutlinedIcon from "@mui/icons-material/SettingsOutlined";
import { useTranslation } from "react-i18next";
import StableNumberField from "./StableNumberField";
import SeedVipJournal from "./SeedVipJournal";

const ROOT = "settings.configForms.seedVip.workbench";

const surfaceSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.default",
  borderRadius: 0,
};

const secondsFromParts = (value = {}) =>
  Number(value.seconds || 0) +
  Number(value.minutes || 0) * 60 +
  Number(value.hours || 0) * 3600;

const minutesFromParts = (value = {}) =>
  Math.round(secondsFromParts(value) / 60);

const minuteParts = (minutes) => {
  const safeMinutes = Math.max(0, Math.round(Number(minutes) || 0));
  return {
    seconds: 0,
    minutes: safeMinutes % 60,
    hours: Math.floor(safeMinutes / 60),
  };
};

const rewardMinutes = (value = {}) =>
  Number(value.minutes || 0) +
  Number(value.hours || 0) * 60 +
  Number(value.days || 0) * 1440 +
  Number(value.weeks || 0) * 10080;

const rewardPartsForDays = (days) => ({
  minutes: 0,
  hours: 0,
  days: Math.max(0, Math.round(Number(days) || 0)),
  weeks: 0,
});

function ValueStepper({ label, value, min = 0, max, disabled, onChange }) {
  const update = (next) =>
    onChange(Math.min(max ?? Number.MAX_SAFE_INTEGER, Math.max(min, next)));
  return (
    <Stack spacing={0.5} sx={{ minWidth: 150 }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Stack data-theme-surface="control"
        direction="row"
        alignItems="stretch"
        sx={{ border: "1px solid", borderColor: "divider", minHeight: 42 }}
      >
        <IconButton
          size="small"
          aria-label={`${label} -`}
          disabled={disabled || Number(value) <= min}
          onClick={() => update(Number(value) - 1)}
          sx={{ width: 42, borderRadius: 0 }}
        >
          <RemoveIcon fontSize="small" />
        </IconButton>
        <StableNumberField
          value={value}
          disabled={disabled}
          onChange={update}
          inputProps={{ min, max, "aria-label": label }}
          variant="standard"
          InputProps={{ disableUnderline: true }}
          sx={{
            flex: 1,
            minWidth: 58,
            "& input": { textAlign: "center", fontWeight: 850, px: 0.5 },
          }}
        />
        <IconButton
          size="small"
          aria-label={`${label} +`}
          disabled={disabled || (max !== undefined && Number(value) >= max)}
          onClick={() => update(Number(value) + 1)}
          sx={{ width: 42, borderRadius: 0 }}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Stack>
    </Stack>
  );
}

function PresetButtons({
  values,
  value,
  unit,
  renderLabel,
  disabled,
  onChange,
}) {
  return (
    <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
      {values.map((preset) => (
        <Button
          key={preset}
          size="small"
          variant={Number(value) === preset ? "contained" : "outlined"}
          disabled={disabled}
          onClick={() => onChange(preset)}
          sx={{ minWidth: 64 }}
        >
          {renderLabel ? renderLabel(preset) : `${preset} ${unit}`}
        </Button>
      ))}
    </Stack>
  );
}

function DurationSlider({
  title,
  help,
  value,
  presets,
  max = 120,
  showHeading = true,
  disabled,
  onChange,
}) {
  const { t } = useTranslation();
  const sliderMax = Math.max(max, Math.ceil((Number(value) || 0) / 15) * 15);
  return (
    <Stack spacing={1.25}>
      {showHeading && (
        <Box>
          <Typography variant="subtitle2" fontWeight={850}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {help}
          </Typography>
        </Box>
      )}
      <PresetButtons
        values={presets}
        value={value}
        unit="Min."
        disabled={disabled}
        onChange={onChange}
      />
      <Stack direction="row" spacing={2} alignItems="center">
        <Slider
          value={Math.min(Number(value) || 0, sliderMax)}
          min={0}
          max={sliderMax}
          step={5}
          disabled={disabled}
          valueLabelDisplay="auto"
          valueLabelFormat={(next) =>
            t("settingsPanels.game.minutes", { count: next })
          }
          onChange={(_, next) => onChange(next)}
          aria-label={title}
          sx={{
            ml: 0.5,
            "& .MuiSlider-rail, & .MuiSlider-track, & .MuiSlider-thumb": {
              borderRadius: 0,
            },
          }}
        />
        <Typography
          component="output"
          variant="body2"
          fontWeight={850}
          sx={{ minWidth: 82, textAlign: "right", color: "primary.main" }}
        >
          {t("settingsPanels.game.minutes", { count: value })}
        </Typography>
      </Stack>
    </Stack>
  );
}

function BriefStep({ icon, label }) {
  return (
    <Stack
      direction="row"
      spacing={1}
      alignItems="center"
      sx={{ minWidth: 0, flex: "1 1 180px" }}
    >
      <Box
        sx={{ color: "primary.main", display: "grid", placeItems: "center" }}
      >
        {icon}
      </Box>
      <Typography variant="body2" fontWeight={750}>
        {label}
      </Typography>
    </Stack>
  );
}

function OutcomeBrief({ data }) {
  const { t } = useTranslation();
  const allies = data?.requirements?.max_allies ?? 0;
  const axis = data?.requirements?.max_axis ?? 0;
  const minimumMinutes = minutesFromParts(
    data?.requirements?.minimum_play_time
  );
  const days = Math.round(rewardMinutes(data?.reward?.timeframe) / 1440);
  const online = Boolean(data?.requirements?.online_when_seeded);
  const equalTeamTargets = allies === axis;
  return (
    <Box data-theme-surface="panel" sx={{ ...surfaceSx, overflow: "hidden" }}>
      <Box sx={{ px: { xs: 1.5, md: 2 }, py: 1.5 }}>
        <Typography variant="subtitle1" color="primary.main" fontWeight={850}>
          {t(`${ROOT}.brief.title`)}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>
          {t(
            equalTeamTargets
              ? `${ROOT}.brief.sentenceEqual`
              : `${ROOT}.brief.sentenceSplit`,
            {
              target: allies,
              allies,
              axis,
              minutes: minimumMinutes,
              count: days,
              days,
            }
          )}
        </Typography>
      </Box>
      <Divider />
      <Stack
        direction="row"
        spacing={1.5}
        useFlexGap
        flexWrap="wrap"
        divider={
          <ChevronRightIcon
            fontSize="small"
            sx={{ color: "text.disabled", alignSelf: "center" }}
          />
        }
        sx={{ px: { xs: 1.5, md: 2 }, py: 1.6 }}
      >
        <BriefStep
          icon={<Groups2OutlinedIcon />}
          label={t(
            equalTeamTargets
              ? `${ROOT}.brief.teamTargetEqual`
              : `${ROOT}.brief.teamTarget`,
            { count: allies, allies, axis }
          )}
        />
        <BriefStep
          icon={<AccessTimeOutlinedIcon />}
          label={t(`${ROOT}.brief.playTime`, { minutes: minimumMinutes })}
        />
        <BriefStep
          icon={<PersonOutlineIcon />}
          label={t(
            online ? `${ROOT}.brief.online` : `${ROOT}.brief.accumulated`
          )}
        />
        <BriefStep
          icon={<RedeemOutlinedIcon />}
          label={t(`${ROOT}.brief.reward`, { count: days, days })}
        />
      </Stack>
    </Box>
  );
}

function OperationSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const locales = ["de_DE", "de", "en_US", "en"];
  const currentLocale = data.language || "";
  const options = locales.includes(currentLocale)
    ? locales
    : [currentLocale, ...locales].filter(Boolean);
  const pollingFields = [
    {
      name: "poll_time_seeding",
      label: t(`${ROOT}.operation.during`),
      help: t(`${ROOT}.operation.duringHelp`),
      presets: [15, 30, 60, 120],
    },
    {
      name: "poll_time_seeded",
      label: t(`${ROOT}.operation.after`),
      help: t(`${ROOT}.operation.afterHelp`),
      presets: [60, 300, 600, 900],
    },
  ];

  return (
    <Stack spacing={2}>
      <Box data-theme-surface="panel" sx={{ ...surfaceSx, p: { xs: 1.5, md: 2 } }}>
        <TextField
          select
          fullWidth
          label={t(`${ROOT}.operation.language`)}
          value={currentLocale}
          disabled={disabled}
          onChange={(event) => patch({ language: event.target.value })}
          helperText={t(`${ROOT}.operation.languageHelp`)}
        >
          {options.map((locale) => (
            <MenuItem key={locale} value={locale}>
              {locale.startsWith("de")
                ? t(`${ROOT}.operation.german`)
                : locale.startsWith("en")
                ? t(`${ROOT}.operation.english`)
                : locale.startsWith("fr")
                ? "Français"
                : locale}
              {locale.includes("_") ? ` · ${locale}` : ""}
            </MenuItem>
          ))}
        </TextField>
      </Box>
      {pollingFields.map((field) => (
        <Box data-theme-surface="panel" key={field.name} sx={{ ...surfaceSx, p: { xs: 1.5, md: 2 } }}>
          <Stack spacing={1.25}>
            <Box>
              <Typography variant="subtitle2" fontWeight={850}>
                {field.label}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {field.help}
              </Typography>
            </Box>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1.25}
              alignItems={{ xs: "stretch", sm: "center" }}
            >
              <PresetButtons
                values={field.presets}
                value={data[field.name]}
                unit="Sek."
                disabled={disabled}
                onChange={(value) => patch({ [field.name]: value })}
              />
              <StableNumberField
                size="small"
                label={t(`${ROOT}.custom`)}
                value={data[field.name] ?? 0}
                disabled={disabled}
                onChange={(value) => patch({ [field.name]: value })}
                inputProps={{ min: 0, step: 5 }}
                sx={{ width: { xs: "100%", sm: 150 }, ml: { sm: "auto" } }}
              />
            </Stack>
            {Number(data[field.name]) === 0 && (
              <Alert severity="warning">
                {t(`${ROOT}.operation.zeroWarning`)}
              </Alert>
            )}
          </Stack>
        </Box>
      ))}
    </Stack>
  );
}

function ThresholdEditor({ values, disabled, onChange }) {
  const { t } = useTranslation();
  const [draft, setDraft] = useState("");
  const normalized = Array.isArray(values) ? values : [];
  const addValue = () => {
    const next = Number(draft);
    if (!Number.isInteger(next) || next < 1 || next > 100) return;
    if (normalized.includes(next)) return;
    onChange([...normalized, next].sort((a, b) => a - b));
    setDraft("");
  };
  return (
    <Stack spacing={1}>
      <Stack direction="row" spacing={0.75} useFlexGap flexWrap="wrap">
        {normalized.map((value) => (
          <Chip
            key={value}
            label={t(`${ROOT}.requirements.players`, { count: value })}
            onDelete={
              disabled
                ? undefined
                : () => onChange(normalized.filter((item) => item !== value))
            }
            variant="outlined"
            sx={{ borderRadius: 0 }}
          />
        ))}
        {normalized.length === 0 && (
          <Typography variant="body2" color="text.secondary">
            {t(`${ROOT}.requirements.noAnnouncements`)}
          </Typography>
        )}
      </Stack>
      <Stack direction="row" spacing={0.75} sx={{ maxWidth: 280 }}>
        <TextField
          size="small"
          type="number"
          label={t(`${ROOT}.requirements.ownValue`)}
          value={draft}
          disabled={disabled}
          onChange={(event) => setDraft(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              addValue();
            }
          }}
          inputProps={{ min: 1, max: 100 }}
        />
        <IconButton
          aria-label={t(`${ROOT}.requirements.addThreshold`)}
          disabled={disabled || !draft}
          onClick={addValue}
          sx={{ border: "1px solid", borderColor: "divider", borderRadius: 0 }}
        >
          <AddIcon />
        </IconButton>
      </Stack>
    </Stack>
  );
}

function RequirementsSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const [coupled, setCoupled] = useState(
    () => data?.requirements?.max_allies === data?.requirements?.max_axis
  );
  const requirements = data.requirements || {};
  const minimumMinutes = minutesFromParts(requirements.minimum_play_time);
  const bufferMinutes = minutesFromParts(requirements.buffer);
  const updateRequirements = (next) =>
    patch({ requirements: { ...requirements, ...next } });
  const updateTarget = (side, value) => {
    const next = { [`max_${side}`]: value };
    if (coupled) next[side === "allies" ? "max_axis" : "max_allies"] = value;
    updateRequirements(next);
  };

  return (
    <Stack spacing={2}>
      <OutcomeBrief data={data} />
      <Box data-theme-surface="panel" sx={{ ...surfaceSx, overflow: "hidden" }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "240px minmax(0, 1fr)" },
          }}
        >
          <Box
            sx={{
              p: 1.75,
              borderRight: { md: "1px solid" },
              borderColor: "divider",
            }}
          >
            <Typography variant="subtitle2" fontWeight={850}>
              {t(`${ROOT}.requirements.targetTitle`)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(`${ROOT}.requirements.targetHelp`)}
            </Typography>
          </Box>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1.5}
            alignItems={{ xs: "stretch", sm: "flex-end" }}
            sx={{ p: 1.75 }}
          >
            <ValueStepper
              label={t(`${ROOT}.requirements.allies`)}
              value={requirements.max_allies ?? 0}
              max={50}
              disabled={disabled}
              onChange={(value) => updateTarget("allies", value)}
            />
            <ValueStepper
              label={t(`${ROOT}.requirements.axis`)}
              value={requirements.max_axis ?? 0}
              max={50}
              disabled={disabled}
              onChange={(value) => updateTarget("axis", value)}
            />
            <Button
              variant={coupled ? "contained" : "outlined"}
              startIcon={<LinkOutlinedIcon />}
              disabled={disabled}
              onClick={() => setCoupled((current) => !current)}
              sx={{ minHeight: 42, ml: { sm: "auto" } }}
            >
              {t(`${ROOT}.requirements.couple`)}
            </Button>
          </Stack>
        </Box>
        <Divider />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "240px minmax(0, 1fr)" },
          }}
        >
          <Box
            sx={{
              p: 1.75,
              borderRight: { md: "1px solid" },
              borderColor: "divider",
            }}
          >
            <Typography variant="subtitle2" fontWeight={850}>
              {t(`${ROOT}.requirements.playTime`)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(`${ROOT}.requirements.playTimeHelp`)}
            </Typography>
          </Box>
          <Box sx={{ p: 1.75 }}>
            <DurationSlider
              title={t(`${ROOT}.requirements.playTime`)}
              help={t(`${ROOT}.requirements.playTimeControlHelp`)}
              value={minimumMinutes}
              presets={[0, 15, 30, 45, 60]}
              showHeading={false}
              disabled={disabled}
              onChange={(value) =>
                updateRequirements({ minimum_play_time: minuteParts(value) })
              }
            />
          </Box>
        </Box>
        <Divider />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "240px minmax(0, 1fr)" },
          }}
        >
          <Box
            sx={{
              p: 1.75,
              borderRight: { md: "1px solid" },
              borderColor: "divider",
            }}
          >
            <Typography variant="subtitle2" fontWeight={850}>
              {t(`${ROOT}.requirements.eligibility`)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(`${ROOT}.requirements.eligibilityHelp`)}
            </Typography>
          </Box>
          <Box sx={{ p: 1.75 }}>
            <ToggleButtonGroup
              exclusive
              fullWidth
              value={requirements.online_when_seeded ? "online" : "accumulate"}
              disabled={disabled}
              onChange={(_, next) => {
                if (next)
                  updateRequirements({ online_when_seeded: next === "online" });
              }}
              aria-label={t(`${ROOT}.requirements.eligibility`)}
            >
              <ToggleButton value="online">
                {t(`${ROOT}.requirements.onlineAtEnd`)}
              </ToggleButton>
              <ToggleButton value="accumulate">
                {t(`${ROOT}.requirements.duringSeeding`)}
              </ToggleButton>
            </ToggleButtonGroup>
          </Box>
        </Box>
        <Divider />
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "240px minmax(0, 1fr)" },
          }}
        >
          <Box
            sx={{
              p: 1.75,
              borderRight: { md: "1px solid" },
              borderColor: "divider",
            }}
          >
            <Typography variant="subtitle2" fontWeight={850}>
              {t(`${ROOT}.requirements.announcements`)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(`${ROOT}.requirements.announcementsHelp`)}
            </Typography>
          </Box>
          <Box sx={{ p: 1.75 }}>
            <ThresholdEditor
              values={data.player_announce_thresholds}
              disabled={disabled}
              onChange={(player_announce_thresholds) =>
                patch({ player_announce_thresholds })
              }
            />
          </Box>
        </Box>
      </Box>

      <Box data-theme-surface="panel" sx={surfaceSx}>
        <Button
          fullWidth
          color="inherit"
          startIcon={<SettingsOutlinedIcon />}
          endIcon={
            <ExpandMoreIcon
              sx={{
                ml: "auto",
                transform: advancedOpen ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 160ms ease",
              }}
            />
          }
          onClick={() => setAdvancedOpen((open) => !open)}
          aria-expanded={advancedOpen}
          sx={{ justifyContent: "flex-start", px: 1.75, py: 1.25 }}
        >
          {t(`${ROOT}.advanced`)}
        </Button>
        <Collapse in={advancedOpen}>
          <Divider />
          <Stack spacing={2} sx={{ p: 1.75 }}>
            <DurationSlider
              title={t(`${ROOT}.requirements.buffer`)}
              help={t(`${ROOT}.requirements.bufferHelp`)}
              value={bufferMinutes}
              presets={[0, 5, 10, 15, 30]}
              max={60}
              disabled={disabled}
              onChange={(value) =>
                updateRequirements({ buffer: minuteParts(value) })
              }
            />
            <Alert severity="info">
              {t(`${ROOT}.requirements.legacyHelp`)}
            </Alert>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <ValueStepper
                label={t(`${ROOT}.requirements.legacyAllies`)}
                value={requirements.min_allies ?? 0}
                max={50}
                disabled={disabled}
                onChange={(value) => updateRequirements({ min_allies: value })}
              />
              <ValueStepper
                label={t(`${ROOT}.requirements.legacyAxis`)}
                value={requirements.min_axis ?? 0}
                max={50}
                disabled={disabled}
                onChange={(value) => updateRequirements({ min_axis: value })}
              />
            </Stack>
          </Stack>
        </Collapse>
      </Box>
    </Stack>
  );
}

function RewardSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const [advancedOpen, setAdvancedOpen] = useState(false);
  const reward = data.reward || {};
  const totalMinutes = rewardMinutes(reward.timeframe);
  const currentDays = Math.max(0, Math.round(totalMinutes / 1440));
  const sliderMax = Math.max(30, currentDays);
  const updateReward = (next) => patch({ reward: { ...reward, ...next } });
  const setDays = (days) =>
    updateReward({ timeframe: rewardPartsForDays(days) });
  const outcome = reward.cumulative
    ? t(`${ROOT}.reward.previewCumulative`, {
        count: currentDays,
        days: currentDays,
      })
    : t(`${ROOT}.reward.previewReplace`, {
        count: currentDays,
        days: currentDays,
      });

  return (
    <Stack spacing={2}>
      <Box data-theme-surface="panel" sx={{ ...surfaceSx, p: { xs: 1.5, md: 2 } }}>
        <Typography variant="overline" color="text.secondary">
          {t(`${ROOT}.reward.duration`)}
        </Typography>
        <Typography variant="h3" fontWeight={850} sx={{ mt: 0.25 }}>
          {t(`${ROOT}.reward.days`, { count: currentDays })}
        </Typography>
        <Stack spacing={1.25} sx={{ mt: 2 }}>
          <PresetButtons
            values={[1, 3, 7, 14, 30]}
            value={currentDays}
            renderLabel={(preset) =>
              t(`${ROOT}.reward.days`, { count: preset })
            }
            disabled={disabled}
            onChange={setDays}
          />
          <Slider
            value={Math.min(currentDays, sliderMax)}
            min={1}
            max={sliderMax}
            step={1}
            disabled={disabled}
            valueLabelDisplay="auto"
            valueLabelFormat={(next) =>
              t(`${ROOT}.reward.days`, { count: next })
            }
            onChange={(_, next) => setDays(next)}
            aria-label={t(`${ROOT}.reward.duration`)}
            sx={{
              mx: 0.5,
              "& .MuiSlider-rail, & .MuiSlider-track, & .MuiSlider-thumb": {
                borderRadius: 0,
              },
            }}
          />
        </Stack>
      </Box>

      <Box data-theme-surface="panel" sx={{ ...surfaceSx, p: { xs: 1.5, md: 2 } }}>
        <Typography variant="subtitle2" fontWeight={850} sx={{ mb: 1 }}>
          {t(`${ROOT}.reward.existingVip`)}
        </Typography>
        <ToggleButtonGroup
          exclusive
          fullWidth
          value={reward.cumulative ? "cumulative" : "replace"}
          disabled={disabled}
          onChange={(_, next) => {
            if (next) updateReward({ cumulative: next === "cumulative" });
          }}
        >
          <ToggleButton value="cumulative">
            {t(`${ROOT}.reward.extend`)}
          </ToggleButton>
          <ToggleButton value="replace">
            {t(`${ROOT}.reward.recalculate`)}
          </ToggleButton>
        </ToggleButtonGroup>
        <Alert
          severity="success"
          icon={<RedeemOutlinedIcon />}
          sx={{ mt: 1.5 }}
        >
          {outcome}
        </Alert>
      </Box>

      <Box data-theme-surface="panel" sx={surfaceSx}>
        <Button
          fullWidth
          color="inherit"
          startIcon={<SettingsOutlinedIcon />}
          endIcon={
            <ExpandMoreIcon
              sx={{
                ml: "auto",
                transform: advancedOpen ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 160ms ease",
              }}
            />
          }
          onClick={() => setAdvancedOpen((open) => !open)}
          aria-expanded={advancedOpen}
          sx={{ justifyContent: "flex-start", px: 1.75, py: 1.25 }}
        >
          {t(`${ROOT}.reward.advanced`)}
        </Button>
        <Collapse in={advancedOpen}>
          <Divider />
          <Stack spacing={2} sx={{ p: 1.75 }}>
            <TextField
              fullWidth
              label={t(`${ROOT}.reward.entryName`)}
              value={reward.player_name_format_not_current_vip || ""}
              disabled={disabled}
              onChange={(event) =>
                updateReward({
                  player_name_format_not_current_vip: event.target.value,
                })
              }
              helperText={t(`${ROOT}.reward.entryPreview`, {
                name: (
                  reward.player_name_format_not_current_vip || "{player_name}"
                ).replace("{player_name}", "FLN_Raven"),
              })}
            />
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1.5}>
              <FormControlLabel
                control={
                  <Switch
                    checked={Boolean(data.nice_time_delta)}
                    disabled={disabled}
                    onChange={(event) =>
                      patch({ nice_time_delta: event.target.checked })
                    }
                  />
                }
                label={t(`${ROOT}.reward.niceDuration`)}
              />
              <FormControlLabel
                control={
                  <Switch
                    checked={Boolean(data.nice_expiration_date)}
                    disabled={disabled}
                    onChange={(event) =>
                      patch({ nice_expiration_date: event.target.checked })
                    }
                  />
                }
                label={t(`${ROOT}.reward.niceExpiry`)}
              />
            </Stack>
            <Alert severity="info">
              {t(`${ROOT}.reward.forwardCompatibility`)}
            </Alert>
          </Stack>
        </Collapse>
      </Box>
    </Stack>
  );
}

const messageDefinitions = [
  ["seeding_in_progress_message", ["{player_count}"]],
  ["seeding_complete_message", []],
  ["player_count_message", ["{num_allied_players}", "{num_axis_players}"]],
  ["reward_player_message", ["{vip_reward}", "{vip_expiration}"]],
  ["reward_player_message_no_vip", []],
];

function MessagesSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const [openKey, setOpenKey] = useState(messageDefinitions[0][0]);
  const messages = data.player_messages || {};
  const updateMessages = (next) =>
    patch({ player_messages: { ...messages, ...next } });

  return (
    <Box data-theme-surface="panel" sx={{ ...surfaceSx, overflow: "hidden" }}>
      {messageDefinitions.map(([key, placeholders], index) => {
        const open = openKey === key;
        const value = messages[key] || "";
        return (
          <Box key={key}>
            {index > 0 && <Divider />}
            <Button
              fullWidth
              color="inherit"
              onClick={() => setOpenKey(open ? null : key)}
              endIcon={
                <ExpandMoreIcon
                  sx={{
                    ml: "auto",
                    transform: open ? "rotate(180deg)" : "rotate(0deg)",
                    transition: "transform 160ms ease",
                  }}
                />
              }
              sx={{ justifyContent: "flex-start", px: 1.75, py: 1.25 }}
            >
              <Box sx={{ textAlign: "left", minWidth: 0 }}>
                <Typography variant="subtitle2" fontWeight={850}>
                  {t(`settings.configForms.seedVip.fields.${key}.label`)}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {value || t(`${ROOT}.messages.empty`)}
                </Typography>
              </Box>
            </Button>
            <Collapse in={open}>
              <Stack spacing={1} sx={{ px: 1.75, pb: 1.75 }}>
                <TextField
                  fullWidth
                  multiline
                  minRows={3}
                  value={value}
                  disabled={disabled}
                  onChange={(event) =>
                    updateMessages({ [key]: event.target.value })
                  }
                />
                {placeholders.length > 0 && (
                  <Stack
                    direction="row"
                    spacing={0.6}
                    useFlexGap
                    flexWrap="wrap"
                  >
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ mr: 0.5 }}
                    >
                      {t(`${ROOT}.messages.placeholders`)}
                    </Typography>
                    {placeholders.map((placeholder) => (
                      <Chip
                        key={placeholder}
                        size="small"
                        label={placeholder.replace(/[{}]/g, "")}
                        variant="outlined"
                        disabled={disabled}
                        onClick={() =>
                          updateMessages({
                            [key]: `${value}${
                              value && !value.endsWith(" ") ? " " : ""
                            }${placeholder}`,
                          })
                        }
                        sx={{ borderRadius: 0 }}
                      />
                    ))}
                  </Stack>
                )}
              </Stack>
            </Collapse>
          </Box>
        );
      })}
    </Box>
  );
}

function WebhooksSection({ data, disabled, patch }) {
  const { t } = useTranslation();
  const hooks = Array.isArray(data.hooks) ? data.hooks : [];
  const updateHooks = (next) => patch({ hooks: next });
  return (
    <Stack spacing={1.5}>
      {hooks.length === 0 && (
        <Box data-theme-surface="panel" sx={{ ...surfaceSx, p: 3, textAlign: "center" }}>
          <NotificationsNoneOutlinedIcon
            color="primary"
            sx={{ fontSize: 34 }}
          />
          <Typography variant="subtitle1" fontWeight={850} sx={{ mt: 1 }}>
            {t(`${ROOT}.webhooks.emptyTitle`)}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {t(`${ROOT}.webhooks.emptyHelp`)}
          </Typography>
        </Box>
      )}
      {hooks.map((hook, index) => (
        <Stack data-theme-surface="panel"
          key={index}
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ xs: "stretch", sm: "center" }}
          sx={{ ...surfaceSx, p: 1.5 }}
        >
          <NotificationsNoneOutlinedIcon color="primary" />
          <TextField
            fullWidth
            type="url"
            label={t(`${ROOT}.webhooks.url`, { number: index + 1 })}
            value={hook?.url || ""}
            disabled={disabled}
            onChange={(event) =>
              updateHooks(
                hooks.map((item, itemIndex) =>
                  itemIndex === index
                    ? { ...item, url: event.target.value }
                    : item
                )
              )
            }
          />
          <IconButton
            aria-label={t(`${ROOT}.webhooks.delete`, { number: index + 1 })}
            disabled={disabled}
            onClick={() =>
              updateHooks(hooks.filter((_, itemIndex) => itemIndex !== index))
            }
            sx={{
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
            }}
          >
            <DeleteOutlineIcon />
          </IconButton>
        </Stack>
      ))}
      <Button
        variant="outlined"
        startIcon={<AddIcon />}
        disabled={disabled}
        onClick={() => updateHooks([...hooks, { url: "" }])}
        sx={{ alignSelf: "flex-start" }}
      >
        {t(`${ROOT}.webhooks.add`)}
      </Button>
    </Stack>
  );
}

export default function SeedVipConfigForm({
  data,
  activeSection,
  disabled = false,
  onChange,
}) {
  const patch = (nextData) => onChange?.(nextData);
  let content = null;
  if (activeSection === "operation")
    content = (
      <OperationSection data={data} disabled={disabled} patch={patch} />
    );
  if (activeSection === "requirements")
    content = (
      <RequirementsSection data={data} disabled={disabled} patch={patch} />
    );
  if (activeSection === "reward")
    content = <RewardSection data={data} disabled={disabled} patch={patch} />;
  if (activeSection === "messages")
    content = <MessagesSection data={data} disabled={disabled} patch={patch} />;
  if (activeSection === "notifications")
    content = <WebhooksSection data={data} disabled={disabled} patch={patch} />;

  return (
    <Stack
      spacing={2}
      data-testid="seed-vip-config-form"
      data-section={activeSection}
    >
      {content}
      {activeSection === "reward" && <SeedVipJournal />}
    </Stack>
  );
}
import "@/i18n/register-settings-panels";
