import React, { useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  ButtonGroup,
  Chip,
  CircularProgress,
  Collapse,
  FormControl,
  InputLabel,
  MenuItem,
  OutlinedInput,
  Select,
  Slider,
  Stack,
  Tooltip,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CheckCircleOutlineRoundedIcon from "@mui/icons-material/CheckCircleOutlineRounded";
import ErrorOutlineRoundedIcon from "@mui/icons-material/ErrorOutlineRounded";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import RestartAltRoundedIcon from "@mui/icons-material/RestartAltRounded";
import SaveRoundedIcon from "@mui/icons-material/SaveRounded";
import TuneRoundedIcon from "@mui/icons-material/TuneRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { useQueryClient } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import { useAuth } from "@/hooks/useAuth";
import { useAdminActionContext } from "@/components/shared/AdminActionContext";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { getGeneralSettingMetadata } from "../setting-metadata";
import { getMaxValue, getMinValue, getStep } from "../utils";
import { GENERAL_KEY } from "../components";

const AUTO_VOTEKICK_KEY = "auto_votekick";

const deepClone = (value) => JSON.parse(JSON.stringify(value));
const valuesEqual = (left, right) =>
  JSON.stringify(left) === JSON.stringify(right);

const normalizeSettings = (settings, autokickSettings) => {
  const next = deepClone(settings || {});
  if (typeof next[GENERAL_KEY.votekick_thresholds] === "string") {
    next[GENERAL_KEY.votekick_thresholds] = JSON.parse(
      next[GENERAL_KEY.votekick_thresholds]
    );
  }
  next[AUTO_VOTEKICK_KEY] = {
    enabled: Boolean(autokickSettings?.enabled),
    minimum_ingame_mods: Number(autokickSettings?.minimum_ingame_mods ?? 0),
    minimum_online_mods: Number(autokickSettings?.minimum_online_mods ?? 0),
    condition: autokickSettings?.condition || "OR",
  };
  return next;
};

const settingCommands = {
  [GENERAL_KEY.team_switch_cooldown]: {
    payloadKey: "minutes",
    mutation: cmd.SET_TEAM_SWITCH_COOLDOWN,
  },
  [GENERAL_KEY.max_ping_autokick]: {
    payloadKey: "max_ms",
    mutation: cmd.SET_MAX_PING_AUTOKICK,
  },
  [GENERAL_KEY.queue_length]: {
    payloadKey: "value",
    mutation: cmd.APPLY_QUEUE_LENGTH,
  },
  [GENERAL_KEY.vip_slots_num]: {
    payloadKey: "value",
    mutation: cmd.APPLY_VIP_SLOTS_NUM,
  },
  [GENERAL_KEY.autobalance_enabled]: {
    payloadKey: "value",
    mutation: cmd.SET_AUTOBALANCE_ENABLED,
  },
  [GENERAL_KEY.autobalance_threshold]: {
    payloadKey: "max_diff",
    mutation: cmd.SET_AUTOBALANCE_THRESHOLD,
  },
  [GENERAL_KEY.idle_autokick_time]: {
    payloadKey: "minutes",
    mutation: cmd.SET_IDLE_AUTOKICK_TIME,
  },
  [GENERAL_KEY.votekick_enabled]: {
    payloadKey: "value",
    mutation: cmd.SET_VOTEKICK_ENABLED,
  },
  [GENERAL_KEY.votekick_thresholds]: {
    payloadKey: "threshold_pairs",
    mutation: cmd.SET_VOTEKICK_THRESHOLDS,
  },
  [AUTO_VOTEKICK_KEY]: {
    mutation: cmd.SET_VOTEKICK_AUTOTOGGLE_CONFIG,
  },
};

const formatValue = (value, unit, copy) => {
  if (unit === "boolean") return value ? copy.active : copy.inactive;
  if (unit === "thresholds") {
    return Array.isArray(value) ? `${value.length} ${copy.thresholds}` : "—";
  }
  if (value === null || value === undefined) return "—";
  return `${value} ${copy.unitLabels[unit] || ""}`.trim();
};

function StatusCell({ state, copy }) {
  const status = {
    saved: {
      icon: <CheckCircleOutlineRoundedIcon fontSize="small" />,
      color: "success.main",
      label: copy.saved,
    },
    dirty: {
      icon: <WarningAmberRoundedIcon fontSize="small" />,
      color: "warning.main",
      label: copy.changed,
    },
    pending: {
      icon: <CircularProgress size={16} color="inherit" />,
      color: "primary.main",
      label: copy.saving,
    },
    error: {
      icon: <ErrorOutlineRoundedIcon fontSize="small" />,
      color: "error.main",
      label: copy.failed,
    },
  }[state];

  return (
    <Stack
      direction="row"
      spacing={0.75}
      alignItems="center"
      color={status.color}
    >
      {status.icon}
      <Typography variant="body2" fontWeight={700} color="inherit">
        {status.label}
      </Typography>
    </Stack>
  );
}

function CompactSlider({ settingKey, value, disabled, onChange, ariaLabel }) {
  const step =
    settingKey === GENERAL_KEY.idle_autokick_time ? 1 : getStep(settingKey);
  const min = getMinValue(settingKey);
  const max = getMaxValue(settingKey);

  const commitInput = (raw) => {
    const numeric = Number(raw);
    if (Number.isNaN(numeric)) return;
    onChange(Math.max(min, Math.min(max, numeric)));
  };

  return (
    <Stack
      direction="row"
      spacing={1.25}
      alignItems="center"
      sx={{ width: "100%" }}
    >
      <Slider
        value={Number(value ?? min)}
        min={min}
        max={max}
        step={step}
        disabled={disabled}
        onChange={(_, next) => onChange(next)}
        aria-label={ariaLabel}
        size="small"
        sx={{ minWidth: 120, flex: 1 }}
      />
      <OutlinedInput
        value={value ?? ""}
        disabled={disabled}
        type="number"
        size="small"
        inputProps={{ min, max, step, "aria-label": ariaLabel }}
        onChange={(event) => commitInput(event.target.value)}
        sx={{ width: 72, borderRadius: 0 }}
      />
    </Stack>
  );
}

function CompactToggle({ value, disabled, onChange, copy, ariaLabel }) {
  return (
    <ButtonGroup
      size="small"
      disabled={disabled}
      aria-label={ariaLabel}
      sx={{ "& .MuiButton-root": { minWidth: 92, borderRadius: 0 } }}
    >
      <Button
        variant={!value ? "contained" : "outlined"}
        color={!value ? "inherit" : "primary"}
        onClick={() => onChange(false)}
      >
        {copy.inactive}
      </Button>
      <Button
        variant={value ? "contained" : "outlined"}
        onClick={() => onChange(true)}
      >
        {copy.active}
      </Button>
    </ButtonGroup>
  );
}

function ThresholdEditor({ value, disabled, onChange, copy }) {
  const updatePair = (index, position, raw) => {
    const pairs = deepClone(value || []);
    pairs[index][position] = Math.max(0, Number(raw) || 0);
    onChange(pairs);
  };

  const removePair = (index) =>
    onChange((value || []).filter((_, pairIndex) => pairIndex !== index));

  const addPair = () => {
    const pairs = deepClone(value || []);
    const lastPlayers = pairs.length ? Number(pairs[pairs.length - 1][0]) : -1;
    onChange([...pairs, [Math.min(lastPlayers + 10, 100), 1]]);
  };

  return (
    <Stack spacing={1.25} sx={{ py: 1 }}>
      {(value || []).map(([players, votes], index) => (
        <Stack
          key={`${players}-${index}`}
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ sm: "center" }}
        >
          <OutlinedInput
            value={players}
            type="number"
            size="small"
            disabled={disabled || index < (value || []).length - 1}
            inputProps={{ min: 0, max: 100, "aria-label": copy.minimumPlayers }}
            onChange={(event) => updatePair(index, 0, event.target.value)}
            startAdornment={
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ mr: 1 }}
              >
                {copy.from}
              </Typography>
            }
            sx={{ flex: 1, borderRadius: 0 }}
          />
          <OutlinedInput
            value={votes}
            type="number"
            size="small"
            disabled={disabled || index < (value || []).length - 1}
            inputProps={{ min: 1, max: 100, "aria-label": copy.requiredVotes }}
            onChange={(event) => updatePair(index, 1, event.target.value)}
            endAdornment={
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ ml: 1 }}
              >
                {copy.votes}
              </Typography>
            }
            sx={{ flex: 1, borderRadius: 0 }}
          />
          <Button
            variant="outlined"
            color="error"
            disabled={disabled || index < (value || []).length - 1}
            onClick={() => removePair(index)}
            sx={{ borderRadius: 0 }}
          >
            {copy.remove}
          </Button>
        </Stack>
      ))}
      <Button
        variant="outlined"
        disabled={disabled || (value || []).length >= 8}
        onClick={addPair}
        sx={{ alignSelf: "flex-start", borderRadius: 0 }}
      >
        {copy.addThreshold}
      </Button>
    </Stack>
  );
}

function AutoVotekickEditor({ value, disabled, onChange, copy }) {
  const setField = (field, next) => onChange({ ...value, [field]: next });
  return (
    <Stack spacing={1.5} sx={{ py: 1 }}>
      <CompactToggle
        value={Boolean(value.enabled)}
        disabled={disabled}
        onChange={(next) => setField("enabled", next)}
        copy={copy}
        ariaLabel={copy.autoVotekick}
      />
      <Stack direction={{ xs: "column", md: "row" }} spacing={1}>
        <OutlinedInput
          value={value.minimum_ingame_mods}
          type="number"
          size="small"
          disabled={disabled || !value.enabled}
          inputProps={{ min: 0, "aria-label": copy.ingameModerators }}
          onChange={(event) =>
            setField(
              "minimum_ingame_mods",
              Math.max(0, Number(event.target.value) || 0)
            )
          }
          startAdornment={
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              {copy.ingameShort}
            </Typography>
          }
          sx={{ flex: 1, borderRadius: 0 }}
        />
        <FormControl size="small" sx={{ minWidth: 104 }}>
          <InputLabel>{copy.logic}</InputLabel>
          <Select
            value={value.condition}
            label={copy.logic}
            disabled={disabled || !value.enabled}
            onChange={(event) => setField("condition", event.target.value)}
            sx={{ borderRadius: 0 }}
          >
            <MenuItem value="AND">AND</MenuItem>
            <MenuItem value="OR">OR</MenuItem>
          </Select>
        </FormControl>
        <OutlinedInput
          value={value.minimum_online_mods}
          type="number"
          size="small"
          disabled={disabled || !value.enabled}
          inputProps={{ min: 0, "aria-label": copy.onlineModerators }}
          onChange={(event) =>
            setField(
              "minimum_online_mods",
              Math.max(0, Number(event.target.value) || 0)
            )
          }
          startAdornment={
            <Typography variant="caption" color="text.secondary" sx={{ mr: 1 }}>
              {copy.onlineShort}
            </Typography>
          }
          sx={{ flex: 1, borderRadius: 0 }}
        />
      </Stack>
    </Stack>
  );
}

export default function OperationsMatrix({ settings, autokickSettings }) {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const actionContext = useAdminActionContext();
  const queryClient = useQueryClient();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const copy =
    i18n.resolvedLanguage === "en"
      ? {
          sections: ["Gameplay", "Access & slots", "Team balance", "Voting"],
          sectionKeys: ["gameplay", "access", "balance", "voting"],
          columnSetting: "Setting",
          columnValue: "Value",
          columnCurrent: "Last read",
          columnRecommendation: "Recommendation",
          columnStatus: "Status",
          saved: "Saved",
          changed: "Changed",
          saving: "Saving",
          failed: "Failed",
          active: "Active",
          inactive: "Inactive",
          thresholds: "thresholds",
          notDocumented: "Not documented",
          useRecommendation: "Use recommendation",
          edit: "Edit",
          close: "Close",
          reset: "Reset values",
          save: "Save changes",
          noChanges: "No unsaved changes",
          unsavedCount: "{{count}} unsaved changes",
          partial: "Some settings could not be saved and remain changed.",
          success: "All changes were sent successfully.",
          blocked:
            "The server connection must be online before settings can be sent.",
          unverified: "Values not verified",
          lastRead: "Last read",
          minimumPlayers: "Minimum players",
          requiredVotes: "Required votes",
          from: "From",
          votes: "votes",
          remove: "Remove",
          addThreshold: "Add threshold",
          autoVotekick: "Automatic votekick",
          ingameModerators: "In-game moderators",
          onlineModerators: "Online CRCON moderators",
          ingameShort: "In game",
          onlineShort: "Online",
          logic: "Logic",
          recommendationRange: "1–2 slots",
          pending: "Server apply pending",
          unitLabels: {
            minutes: "min",
            milliseconds: "ms",
            players: "players",
            slots: "slots",
          },
        }
      : {
          sections: [
            "Spielablauf",
            "Zugang & Plätze",
            "Teamausgleich",
            "Abstimmungen",
          ],
          sectionKeys: ["gameplay", "access", "balance", "voting"],
          columnSetting: "Einstellung",
          columnValue: "Wert",
          columnCurrent: "Zuletzt gelesen",
          columnRecommendation: "Empfehlung",
          columnStatus: "Status",
          saved: "Gespeichert",
          changed: "Geändert",
          saving: "Wird gespeichert",
          failed: "Fehlgeschlagen",
          active: "Aktiv",
          inactive: "Inaktiv",
          thresholds: "Schwellen",
          notDocumented: "Nicht dokumentiert",
          useRecommendation: "Empfehlung übernehmen",
          edit: "Bearbeiten",
          close: "Schließen",
          reset: "Werte zurücksetzen",
          save: "Änderungen speichern",
          noChanges: "Keine ungespeicherten Änderungen",
          unsavedCount: "{{count}} ungespeicherte Änderungen",
          partial:
            "Einige Einstellungen konnten nicht gespeichert werden und bleiben als geändert markiert.",
          success: "Alle Änderungen wurden erfolgreich gesendet.",
          blocked:
            "Die Serververbindung muss online sein, bevor Einstellungen gesendet werden können.",
          unverified: "Werte nicht verifiziert",
          lastRead: "Zuletzt gelesen",
          minimumPlayers: "Mindestanzahl Spieler",
          requiredVotes: "Benötigte Stimmen",
          from: "Ab",
          votes: "Stimmen",
          remove: "Entfernen",
          addThreshold: "Schwelle hinzufügen",
          autoVotekick: "Automatischer Votekick",
          ingameModerators: "Moderatoren im Spiel",
          onlineModerators: "CRCON-Moderatoren online",
          ingameShort: "Im Spiel",
          onlineShort: "Online",
          logic: "Logik",
          recommendationRange: "1–2 Plätze",
          pending: "Anwendung durch Server steht aus",
          unitLabels: {
            minutes: "Min.",
            milliseconds: "ms",
            players: "Spieler",
            slots: "Plätze",
          },
        };

  const initialValues = useMemo(
    () => normalizeSettings(settings, autokickSettings),
    [settings, autokickSettings]
  );
  const [baseline, setBaseline] = useState(() => initialValues);
  const [draft, setDraft] = useState(() => deepClone(initialValues));
  const [activeSection, setActiveSection] = useState("gameplay");
  const [expandedKey, setExpandedKey] = useState(null);
  const [pendingKeys, setPendingKeys] = useState([]);
  const [rowErrors, setRowErrors] = useState({});

  const canChange = (settingKey) => {
    if (settingKey === AUTO_VOTEKICK_KEY) return true;
    const permission = getGeneralSettingMetadata(settingKey)?.changePermission;
    return Boolean(
      permissions?.is_superuser ||
        permissions?.permissions?.some((item) => item.permission === permission)
    );
  };

  const rows = useMemo(
    () => [
      {
        key: GENERAL_KEY.team_switch_cooldown,
        section: "gameplay",
        kind: "slider",
        title: t("settings.general.cards.teamSwitchCooldown.title"),
        subtitle: t("settings.general.cards.teamSwitchCooldown.subtitle"),
      },
      {
        key: GENERAL_KEY.max_ping_autokick,
        section: "gameplay",
        kind: "slider",
        title: t("settings.general.cards.maxPingAutokick.title"),
        subtitle: t("settings.general.cards.maxPingAutokick.subtitle"),
      },
      {
        key: GENERAL_KEY.idle_autokick_time,
        section: "gameplay",
        kind: "slider",
        title: t("settings.general.cards.idleAutokick.title"),
        subtitle: t("settings.general.cards.idleAutokick.subtitle"),
      },
      {
        key: GENERAL_KEY.queue_length,
        section: "access",
        kind: "slider",
        title: t("settings.general.cards.queueLength.title"),
        subtitle: t("settings.general.cards.queueLength.subtitle"),
      },
      {
        key: GENERAL_KEY.vip_slots_num,
        section: "access",
        kind: "slider",
        title: t("settings.general.cards.vipSlots.title"),
        subtitle: t("settings.general.cards.vipSlots.subtitle"),
      },
      {
        key: GENERAL_KEY.autobalance_enabled,
        section: "balance",
        kind: "toggle",
        title: t("settings.general.cards.autobalance.title"),
        subtitle: t("settings.general.cards.autobalance.subtitle"),
      },
      {
        key: GENERAL_KEY.autobalance_threshold,
        section: "balance",
        kind: "slider",
        dependentOn: GENERAL_KEY.autobalance_enabled,
        title: t("settings.general.cards.autobalanceThreshold.title"),
        subtitle: t("settings.general.cards.autobalanceThreshold.subtitle"),
      },
      {
        key: GENERAL_KEY.votekick_enabled,
        section: "voting",
        kind: "toggle",
        title: t("settings.general.cards.votekick.title"),
        subtitle: t("settings.general.cards.votekick.subtitle"),
      },
      {
        key: GENERAL_KEY.votekick_thresholds,
        section: "voting",
        kind: "thresholds",
        dependentOn: GENERAL_KEY.votekick_enabled,
        title: t("settings.general.cards.votekickThresholds.title"),
        subtitle: t("settings.general.cards.votekickThresholds.subtitle"),
      },
      {
        key: AUTO_VOTEKICK_KEY,
        section: "voting",
        kind: "autoVotekick",
        title: t("settings.general.cards.autoVotekick.title"),
        subtitle: t("settings.general.cards.autoVotekick.subtitle"),
      },
    ],
    [t]
  );

  const visibleRows = rows.filter((row) => row.section === activeSection);
  const dirtyKeys = rows
    .filter((row) => !valuesEqual(baseline[row.key], draft[row.key]))
    .map((row) => row.key);
  const editableDirtyKeys = dirtyKeys.filter((key) => canChange(key));
  const isSaving = pendingKeys.length > 0;

  const setValue = (key, value) => {
    setDraft((current) => ({ ...current, [key]: value }));
    setRowErrors((current) => ({ ...current, [key]: undefined }));
  };

  const resetAll = () => {
    setDraft(deepClone(baseline));
    setExpandedKey(null);
    setRowErrors({});
  };

  const saveAll = async () => {
    const keys = [...editableDirtyKeys];
    if (!keys.length || isSaving) return;
    const failed = {};
    let pendingServerApply = false;

    for (const key of keys) {
      setPendingKeys((current) => [...current, key]);
      const config = settingCommands[key];
      try {
        const payload =
          key === AUTO_VOTEKICK_KEY
            ? draft[key]
            : { [config.payloadKey]: draft[key] };
        const response = await config.mutation({
          payload,
          throwRouteError: false,
        });
        pendingServerApply =
          pendingServerApply || response?.result?.state === "pending";
        setBaseline((current) => ({
          ...current,
          [key]: deepClone(draft[key]),
        }));
      } catch (error) {
        failed[key] = error?.message || copy.failed;
      } finally {
        setPendingKeys((current) => current.filter((item) => item !== key));
      }
    }

    setRowErrors(failed);
    queryClient.invalidateQueries({
      queryKey: [{ queryIdentifier: "get_server_settings" }],
    });
    queryClient.invalidateQueries({
      queryKey: [{ queryIdentifier: "get_votekick_autotoggle_config" }],
    });

    if (Object.keys(failed).length) toast.error(copy.partial);
    else if (pendingServerApply) toast.info(copy.pending);
    else toast.success(copy.success);
  };

  const lastRead = actionContext.gameServer.lastSuccessAt
    ? new Date(actionContext.gameServer.lastSuccessAt).toLocaleString(
        i18n.resolvedLanguage === "en" ? "en" : "de"
      )
    : t("settingEffect.notAvailable");

  return (
    <Stack spacing={1.5} data-testid="general-settings-operations-matrix">
      <Stack data-theme-surface="panel"
        direction={{ xs: "column", lg: "row" }}
        spacing={1}
        alignItems={{ lg: "center" }}
        sx={{
          px: 1.75,
          py: 1.25,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          borderRadius: 0,
        }}
      >
        <Typography variant="body2" fontWeight={800} sx={{ mr: "auto" }}>
          {actionContext.serverName || t("dashboard.unknownServer")}
          {actionContext.serverNumber != null
            ? ` · ${t("sidebar.serverNumber", {
                number: actionContext.serverNumber,
              })}`
            : ""}
        </Typography>
        <Chip
          size="small"
          variant="outlined"
          label={`CRCON · ${t(
            `connectionStates.${actionContext.crcon.state}`
          )}`}
          color={
            actionContext.crcon.state === CONNECTION_STATE.ONLINE
              ? "success"
              : "warning"
          }
          sx={{ borderRadius: 0 }}
        />
        <Chip
          size="small"
          variant="outlined"
          label={`${t("sidebar.gameServer")} · ${t(
            `connectionStates.${actionContext.gameServer.state}`
          )}`}
          color={
            actionContext.gameServer.state === CONNECTION_STATE.ONLINE
              ? "success"
              : "warning"
          }
          sx={{ borderRadius: 0 }}
        />
        <Typography variant="caption" color="text.secondary">
          {copy.lastRead} {lastRead}
        </Typography>
        <Stack
          direction="row"
          spacing={0.5}
          alignItems="center"
          color="warning.main"
        >
          <WarningAmberRoundedIcon fontSize="small" />
          <Typography variant="caption" fontWeight={800} color="inherit">
            {copy.unverified}
          </Typography>
        </Stack>
      </Stack>

      {!actionContext.canExecute && (
        <Alert severity="warning">{copy.blocked}</Alert>
      )}

      <Box data-theme-surface="panel"
        className="wardogs-control-layout"
        sx={{
          display: { xs: "block", md: "grid" },
          gridTemplateColumns: "176px minmax(0, 1fr)",
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        {compact ? (
          <FormControl fullWidth size="small" sx={{ p: 1 }}>
            <InputLabel id="general-settings-section-label" sx={{ ml: 1 }}>
              {copy.columnSetting}
            </InputLabel>
            <Select
              labelId="general-settings-section-label"
              value={activeSection}
              label={copy.columnSetting}
              onChange={(event) => {
                setActiveSection(event.target.value);
                setExpandedKey(null);
              }}
              sx={{ borderRadius: 0 }}
            >
              {copy.sections.map((label, index) => (
                <MenuItem
                  key={copy.sectionKeys[index]}
                  value={copy.sectionKeys[index]}
                >
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        ) : (
          <Stack
            className="wardogs-control-navigation"
            sx={{ borderRight: "1px solid", borderColor: "divider" }}
          >
            {copy.sections.map((label, index) => {
              const key = copy.sectionKeys[index];
              const active = activeSection === key;
              return (
                <Button
                  key={key}
                  onClick={() => {
                    setActiveSection(key);
                    setExpandedKey(null);
                  }}
                  sx={{
                    justifyContent: "flex-start",
                    minHeight: 58,
                    px: 2,
                    borderRadius: 0,
                    borderBottom: "1px solid",
                    borderColor: "divider",
                    borderLeft: "2px solid",
                    borderLeftColor: active ? "primary.main" : "transparent",
                    bgcolor: active ? "action.selected" : "transparent",
                    color: active ? "primary.main" : "text.secondary",
                  }}
                >
                  {label}
                </Button>
              );
            })}
          </Stack>
        )}

        <Box sx={{ minWidth: 0 }}>
          <Box
            sx={{
              display: { xs: "none", lg: "grid" },
              gridTemplateColumns:
                "minmax(220px, 1.2fr) minmax(260px, 1.5fr) 130px 150px 130px",
              minHeight: 48,
              alignItems: "center",
              borderBottom: "1px solid",
              borderColor: "divider",
              color: "text.secondary",
              "& > *": { px: 1.5 },
            }}
          >
            <Typography variant="overline">{copy.columnSetting}</Typography>
            <Typography variant="overline">{copy.columnValue}</Typography>
            <Typography variant="overline">{copy.columnCurrent}</Typography>
            <Typography variant="overline">
              {copy.columnRecommendation}
            </Typography>
            <Typography variant="overline">{copy.columnStatus}</Typography>
          </Box>

          {visibleRows.map((row) => {
            const metadata = getGeneralSettingMetadata(row.key);
            const dirty = !valuesEqual(baseline[row.key], draft[row.key]);
            const disabled =
              isSaving ||
              !canChange(row.key) ||
              (row.dependentOn && !draft[row.dependentOn]);
            const rowState = pendingKeys.includes(row.key)
              ? "pending"
              : rowErrors[row.key]
              ? "error"
              : dirty
              ? "dirty"
              : "saved";
            const recommendation =
              row.key === GENERAL_KEY.vip_slots_num
                ? copy.recommendationRange
                : metadata?.recommendedValue == null
                ? copy.notDocumented
                : formatValue(metadata.recommendedValue, metadata.unit, copy);
            const expandable =
              row.kind === "thresholds" || row.kind === "autoVotekick";
            const expanded = expandedKey === row.key;

            return (
              <Box
                key={row.key}
                data-testid={`general-setting-${row.key}`}
                sx={{
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  bgcolor: dirty ? "action.hover" : "transparent",
                }}
              >
                <Box
                  sx={{
                    display: { xs: "flex", lg: "grid" },
                    flexDirection: "column",
                    gridTemplateColumns:
                      "minmax(220px, 1.2fr) minmax(260px, 1.5fr) 130px 150px 130px",
                    minHeight: { xs: "auto", lg: 80 },
                    alignItems: { lg: "center" },
                    gap: { xs: 1.25, lg: 0 },
                    p: { xs: 1.5, lg: 0 },
                    opacity:
                      row.dependentOn && !draft[row.dependentOn] ? 0.55 : 1,
                    "& > *": { px: { lg: 1.5 } },
                  }}
                >
                  <Box>
                    <Typography variant="body2" fontWeight={800}>
                      {row.title}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {row.subtitle}
                    </Typography>
                  </Box>

                  <Box sx={{ minWidth: 0 }}>
                    {row.kind === "slider" && (
                      <CompactSlider
                        settingKey={row.key}
                        value={draft[row.key]}
                        disabled={disabled}
                        onChange={(value) => setValue(row.key, value)}
                        ariaLabel={row.title}
                      />
                    )}
                    {row.kind === "toggle" && (
                      <CompactToggle
                        value={Boolean(draft[row.key])}
                        disabled={disabled}
                        onChange={(value) => setValue(row.key, value)}
                        copy={copy}
                        ariaLabel={row.title}
                      />
                    )}
                    {expandable && (
                      <Stack direction="row" spacing={1} alignItems="center">
                        <Typography variant="body2" sx={{ flex: 1 }}>
                          {row.kind === "thresholds"
                            ? formatValue(draft[row.key], "thresholds", copy)
                            : draft[row.key]?.enabled
                            ? `${copy.active} · ${
                                draft[row.key].minimum_ingame_mods
                              } ${copy.ingameShort} ${
                                draft[row.key].condition
                              } ${draft[row.key].minimum_online_mods} ${
                                copy.onlineShort
                              }`
                            : copy.inactive}
                        </Typography>
                        <Button
                          variant="outlined"
                          size="small"
                          startIcon={<TuneRoundedIcon />}
                          disabled={disabled}
                          onClick={() =>
                            setExpandedKey(expanded ? null : row.key)
                          }
                          sx={{ borderRadius: 0 }}
                        >
                          {expanded ? copy.close : copy.edit}
                        </Button>
                      </Stack>
                    )}
                  </Box>

                  <Box sx={{ display: { xs: "flex", lg: "block" }, gap: 1 }}>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: { lg: "none" } }}
                    >
                      {copy.columnCurrent}:
                    </Typography>
                    <Typography variant="body2">
                      {row.key === AUTO_VOTEKICK_KEY
                        ? baseline[row.key]?.enabled
                          ? copy.active
                          : copy.inactive
                        : formatValue(baseline[row.key], metadata?.unit, copy)}
                    </Typography>
                  </Box>

                  <Box>
                    <Typography
                      variant="caption"
                      color="text.secondary"
                      sx={{ display: { lg: "none" } }}
                    >
                      {copy.columnRecommendation}:
                    </Typography>
                    <Tooltip
                      title={
                        metadata?.recommendedValue != null
                          ? copy.useRecommendation
                          : ""
                      }
                    >
                      <span>
                        <Button
                          variant="text"
                          size="small"
                          disabled={
                            disabled || metadata?.recommendedValue == null
                          }
                          onClick={() =>
                            setValue(
                              row.key,
                              deepClone(metadata.recommendedValue)
                            )
                          }
                          sx={{
                            minWidth: 0,
                            p: 0,
                            justifyContent: "flex-start",
                            color:
                              metadata?.recommendedValue == null
                                ? "text.secondary"
                                : "text.primary",
                          }}
                        >
                          {recommendation}
                        </Button>
                      </span>
                    </Tooltip>
                  </Box>

                  <Box>
                    <StatusCell state={rowState} copy={copy} />
                    {rowErrors[row.key] && (
                      <Typography variant="caption" color="error.main">
                        {rowErrors[row.key]}
                      </Typography>
                    )}
                  </Box>
                </Box>

                <Collapse in={expanded} unmountOnExit>
                  <Box
                    sx={{
                      px: 1.5,
                      pb: 1.5,
                      ml: { lg: "calc(220px + 1.5rem)" },
                      maxWidth: 720,
                    }}
                  >
                    {row.kind === "thresholds" ? (
                      <ThresholdEditor
                        value={draft[row.key]}
                        disabled={disabled}
                        onChange={(value) => setValue(row.key, value)}
                        copy={copy}
                      />
                    ) : (
                      <AutoVotekickEditor
                        value={draft[row.key]}
                        disabled={disabled}
                        onChange={(value) => setValue(row.key, value)}
                        copy={copy}
                      />
                    )}
                  </Box>
                </Collapse>
              </Box>
            );
          })}
        </Box>
      </Box>

      <Stack data-theme-surface="panel"
        className="wardogs-action-bar"
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        alignItems={{ sm: "center" }}
        sx={{
          position: "sticky",
          bottom: 0,
          zIndex: 5,
          p: 1.5,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          boxShadow: 3,
        }}
      >
        <Stack
          direction="row"
          spacing={0.75}
          alignItems="center"
          sx={{ mr: "auto" }}
          className="wardogs-control-action-status"
        >
          {dirtyKeys.length ? (
            <WarningAmberRoundedIcon color="warning" />
          ) : (
            <CheckCircleOutlineRoundedIcon color="success" />
          )}
          <Typography variant="body2" fontWeight={800}>
            {dirtyKeys.length
              ? copy.unsavedCount.replace("{{count}}", dirtyKeys.length)
              : copy.noChanges}
          </Typography>
          {dirtyKeys.length > editableDirtyKeys.length && (
            <Tooltip title={t("settingEffect.permissionMissing")}>
              <InfoOutlinedIcon color="disabled" fontSize="small" />
            </Tooltip>
          )}
        </Stack>
        <Button
          variant="outlined"
          startIcon={<RestartAltRoundedIcon />}
          disabled={!dirtyKeys.length || isSaving}
          onClick={resetAll}
          sx={{ borderRadius: 0 }}
        >
          {copy.reset}
        </Button>
        <Button
          variant="contained"
          startIcon={
            isSaving ? (
              <CircularProgress size={16} color="inherit" />
            ) : (
              <SaveRoundedIcon />
            )
          }
          disabled={
            !editableDirtyKeys.length || isSaving || !actionContext.canExecute
          }
          onClick={saveAll}
          sx={{ borderRadius: 0, minWidth: 210 }}
        >
          {isSaving ? copy.saving : copy.save}
        </Button>
      </Stack>
    </Stack>
  );
}
