import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useLoaderData } from "react-router-dom";
import {
  mapsManagerMutationOptions,
  mapsManagerQueryKeys,
  mapsManagerQueryOptions,
} from "../../queries";
import { useEffect, useMemo, useRef, useState } from "react";
import cloneDeep from "lodash/cloneDeep";
import isEqual from "lodash/isEqual";
import { toast } from "react-toastify";
import { VotemapChangeNotification } from "./VotemapChangeNotification";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Switch,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import {
  advancedRuleConfigs,
  defaultMapOptions,
  findPadlockConfig,
  gameModeOptionConfigs,
  messageFieldConfigs,
  primaryRuleGroups,
  recentMapsConfig,
  reminderFrequencyConfig,
  vipVoteCountConfig,
} from "./configs-data";
import SaveIcon from "@mui/icons-material/Save";
import ReplayIcon from "@mui/icons-material/Replay";
import { useTranslation } from "react-i18next";
import { lazy, Suspense } from "react";
const EmojiPicker = lazy(() => import("@emoji-mart/react"));
import emojiData from "@emoji-mart/data/sets/15/twitter.json";
import Emoji from "@/components/shared/Emoji";
import AddCircleIcon from "@mui/icons-material/AddCircle";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import AddIcon from "@mui/icons-material/Add";
import BallotOutlinedIcon from "@mui/icons-material/BallotOutlined";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import RemoveIcon from "@mui/icons-material/Remove";
import StarBorderOutlinedIcon from "@mui/icons-material/StarBorderOutlined";
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import StableNumberField from "@/pages/settings/config-form/StableNumberField";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";

const workbenchCardSx = {
  height: "100%",
  borderRadius: 0,
  borderColor: "divider",
  bgcolor: "background.paper",
  boxShadow: "none",
};

function SectionHeading({ number, title, description, summary }) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "flex-start", sm: "center" }}
      gap={1}
    >
      <Stack direction="row" spacing={1.25} alignItems="flex-start">
        <Box
          aria-hidden="true"
          sx={{
            display: "grid",
            placeItems: "center",
            width: 24,
            height: 24,
            flex: "0 0 auto",
            border: "1px solid",
            borderColor: "primary.main",
            color: "primary.main",
            fontSize: 13,
            fontWeight: 850,
          }}
        >
          {number}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography
            component="h3"
            variant="subtitle1"
            color="primary.main"
            fontWeight={850}
            sx={{ textTransform: "uppercase", letterSpacing: 0.35 }}
          >
            {title}
          </Typography>
          {description && (
            <Typography variant="caption" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      </Stack>
      {summary && (
        <Typography variant="caption" color="text.secondary" sx={{ pl: 4.5 }}>
          {summary}
        </Typography>
      )}
    </Stack>
  );
}

function SummaryMetric({ icon, label, value }) {
  return (
    <Stack
      direction="row"
      alignItems="center"
      spacing={1.25}
      sx={{ minWidth: 0, px: { xs: 1.25, sm: 2 }, py: 1.25 }}
    >
      <Box
        sx={{ display: "grid", placeItems: "center", color: "text.secondary" }}
      >
        {icon}
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", lineHeight: 1.15 }}
        >
          {label}
        </Typography>
        <Typography variant="body2" fontWeight={850} noWrap>
          {value}
        </Typography>
      </Box>
    </Stack>
  );
}

function RuleToggle({ label, checked, onChange, disabled = false }) {
  return (
    <FormControlLabel
      label={label}
      labelPlacement="start"
      disabled={disabled}
      control={
        <Switch
          size="small"
          checked={Boolean(checked)}
          onChange={(event) => onChange(event.target.checked)}
        />
      }
      sx={{
        width: "100%",
        minHeight: 27,
        m: 0,
        gap: 2,
        justifyContent: "space-between",
        "& .MuiFormControlLabel-label": {
          flex: "1 1 auto",
          fontSize: "0.75rem",
          lineHeight: 1.35,
        },
      }}
    />
  );
}

function NumberStepper({
  label,
  value,
  inputProps,
  helperText,
  invalidHelperText,
  onValidityChange,
  onChange,
  compact = false,
}) {
  const [invalid, setInvalid] = useState(false);
  const min =
    inputProps?.min === undefined ? undefined : Number(inputProps.min);
  const max =
    inputProps?.max === undefined ? undefined : Number(inputProps.max);
  const numericValue = Number(value);
  const canDecrease =
    Number.isFinite(numericValue) && (min === undefined || numericValue > min);
  const canIncrease =
    Number.isFinite(numericValue) && (max === undefined || numericValue < max);
  const stepValue = (direction) => {
    const base = Number.isFinite(numericValue) ? numericValue : min ?? 0;
    const next = base + direction;
    onChange(Math.max(min ?? next, Math.min(max ?? next, next)));
  };

  return (
    <Box sx={{ minWidth: 0 }}>
      {!compact && (
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", mb: 0.5 }}
        >
          {label}
        </Typography>
      )}
      <Stack direction="row" alignItems="stretch" spacing={0}>
        <IconButton
          aria-label={`${label}: weniger`}
          onClick={() => stepValue(-1)}
          disabled={!canDecrease}
          size="small"
          sx={{
            width: 36,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 0,
          }}
        >
          <RemoveIcon fontSize="small" />
        </IconButton>
        <StableNumberField
          variant="outlined"
          value={value}
          requiredValue
          invalidHelperText={invalidHelperText}
          onValidityChange={(valid) => {
            setInvalid(!valid);
            onValidityChange?.(valid);
          }}
          onChange={onChange}
          slotProps={{
            htmlInput: { ...inputProps, "aria-label": label },
          }}
          sx={{
            width: compact ? 72 : 84,
            mx: "-1px",
            "& .MuiOutlinedInput-root": { height: 36, borderRadius: 0 },
            "& input": {
              textAlign: "center",
              px: 0.75,
              py: 0.75,
              fontWeight: 800,
            },
            "& .MuiFormHelperText-root": { display: "none" },
          }}
        />
        <IconButton
          aria-label={`${label}: mehr`}
          onClick={() => stepValue(1)}
          disabled={!canIncrease}
          size="small"
          sx={{
            width: 36,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 0,
          }}
        >
          <AddIcon fontSize="small" />
        </IconButton>
      </Stack>
      {invalid ? (
        <Typography
          role="alert"
          variant="caption"
          color="error.main"
          sx={{ display: "block", mt: 0.5 }}
        >
          {invalidHelperText}
        </Typography>
      ) : (
        !compact &&
        helperText && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 0.5 }}
          >
            {helperText}
          </Typography>
        )
      )}
    </Box>
  );
}

function WorkbenchAccordion({ number, title, summary, testId, children }) {
  return (
    <Accordion
      data-testid={testId}
      disableGutters
      elevation={0}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: "0 !important",
        bgcolor: "background.paper",
        "&::before": { display: "none" },
        "& + &": { mt: 1 },
      }}
    >
      <AccordionSummary
        expandIcon={<ExpandMoreIcon />}
        sx={{
          minHeight: 52,
          px: { xs: 1.5, sm: 2 },
          "& .MuiAccordionSummary-content": { my: 1 },
        }}
      >
        <Box sx={{ width: "100%", pr: 1 }}>
          <SectionHeading number={number} title={title} summary={summary} />
        </Box>
      </AccordionSummary>
      <AccordionDetails sx={{ px: { xs: 1.5, sm: 2 }, pt: 0, pb: 2 }}>
        <Divider sx={{ mb: 2 }} />
        {children}
      </AccordionDetails>
    </Accordion>
  );
}

function FlagChooserGroup({ title, help, items, addLabel, onEdit, onAdd }) {
  return (
    <Box>
      <Typography variant="subtitle2" fontWeight={850}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {help}
      </Typography>
      <Stack
        direction="row"
        flexWrap="wrap"
        gap={1}
        alignItems="center"
        sx={{ mt: 1 }}
      >
        {items.map((item, index) => (
          <Button
            key={`${item}-${index}`}
            variant="outlined"
            aria-label={`${title}: ${item || "?"}`}
            onClick={() => onEdit(index)}
            sx={{ minWidth: 44, minHeight: 40, borderRadius: 0, fontSize: 22 }}
          >
            <Emoji emoji={item ?? "❓"} />
          </Button>
        ))}
        <IconButton
          aria-label={addLabel}
          sx={{
            width: 40,
            height: 40,
            border: "1px solid",
            borderColor: "divider",
            borderRadius: 0,
          }}
          onClick={onAdd}
        >
          <AddCircleIcon />
        </IconButton>
      </Stack>
    </Box>
  );
}

function VotemapSettingsPage() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();
  const theme = useTheme();
  const { permissions } = useAuth();
  const fakeMode = isFakeMode();
  const canChangeConfig =
    fakeMode ||
    permissions?.is_superuser ||
    (permissions?.permissions ?? []).some(
      (entry) =>
        (typeof entry === "string" ? entry : entry.permission) ===
        "can_change_votemap_config"
    );

  const { data: config } = useQuery({
    ...mapsManagerQueryOptions.voteMapConfig(),
    initialData: loaderData.config,
    refetchInterval: fakeMode ? false : 5_000,
    staleTime: 5_000,
    refetchOnMount: false,
  });

  const { mutate: changeConfig, isPending: isConfigSaving } = useMutation({
    mutationFn: fakeMode
      ? async (nextConfig) => ({ arguments: nextConfig })
      : mapsManagerMutationOptions.setVotemapConfig.mutationFn,
    onSuccess: (response, submittedConfig) => {
      // Update this reference so the user does not get change
      // notification about his own changes
      prevConfig.current = cloneDeep(submittedConfig);
      editBaseline.current = cloneDeep(submittedConfig);
      setWorkingConfig(cloneDeep(submittedConfig));
      queryClient.setQueryData(
        mapsManagerQueryKeys.voteMapConfig,
        fakeMode ? response.arguments : submittedConfig
      );
      if (!fakeMode) {
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.voteMapConfig,
        });
        queryClient.invalidateQueries({
          queryKey: mapsManagerQueryKeys.votemapStatus,
        });
      }
      toast.success(t("maps.votemapSettings.updated"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <span>{error.name}</span>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  const prevConfig = useRef(config);
  const editBaseline = useRef(config);
  const [workingConfig, setWorkingConfig] = useState(config);
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
  const [emojiPickerIndex, setEmojiPickerIndex] = useState(null);
  const [emojiPickerMode, setEmojiPickerMode] = useState(null);
  const [invalidNumberFields, setInvalidNumberFields] = useState(
    () => new Set()
  );
  const isConfigDirty = useMemo(
    () => !isEqual(workingConfig, editBaseline.current),
    [workingConfig]
  );
  const instructionTextIsValid = String(
    workingConfig.instruction_text ?? ""
  ).includes("{map_selection}");

  const getLabel = (configItem) =>
    t(
      configItem.translationKey ?? `maps.votemapSettings.${configItem.labelKey}`
    );
  const getHelperText = (configItem) =>
    t(
      configItem.helperTranslationKey ??
        `maps.votemapSettings.${configItem.helperKey}`
    );

  // Compare incoming config changes
  const handleIncomingConfigChange = () => {
    // check how the configs differ (deep comparison)
    const diff = [
      ...new Set([
        ...Object.keys(prevConfig.current ?? {}),
        ...Object.keys(config ?? {}),
      ]),
    ].filter(
      (key) => !isEqual(prevConfig.current?.[key], config?.[key])
    );

    // no changes do nothing
    if (diff.length === 0) return;

    // update reference
    // this will also prevent infinite toasting for the same changes
    prevConfig.current = cloneDeep(config);

    // Keep the hidden runtime flag in sync even when other settings changed at
    // the same time. Saving this full config must never overwrite an
    // enable/disable action performed from the live tab.
    if (diff.includes("enabled")) {
      editBaseline.current = {
        ...editBaseline.current,
        enabled: config.enabled,
      };
      setWorkingConfig((prev) => ({ ...prev, enabled: config.enabled }));
    }

    const actionableDiff = diff.filter((key) => key !== "enabled");
    if (actionableDiff.length === 0) return;

    // announce there have been some changes made
    toast(VotemapChangeNotification, {
      onClose(reason) {
        // No-op: all logic is handled in the onAccept callback below
      },
      data: {
        changes: actionableDiff,
        onAccept: () => {
          setWorkingConfig((prev) => {
            const combined = { ...prev };
            const nextBaseline = { ...editBaseline.current };
            actionableDiff.forEach((key) => {
              if (Object.prototype.hasOwnProperty.call(config, key)) {
                combined[key] = cloneDeep(config[key]);
                nextBaseline[key] = cloneDeep(config[key]);
              } else {
                delete combined[key];
                delete nextBaseline[key];
              }
            });
            editBaseline.current = nextBaseline;
            return combined;
          });
        },
      },
      autoClose: false,
      closeOnClick: false,
    });
  };

  const handleConfigReset = () => {
    setInvalidNumberFields(new Set());
    editBaseline.current = cloneDeep(config);
    setWorkingConfig(cloneDeep(config));
  };

  const handleConfigSave = () => {
    // Start from the freshest server object and overlay only fields that the
    // operator changed relative to the accepted baseline. This preserves
    // future backend fields even if they change while this form is open.
    const baseline = editBaseline.current ?? {};
    const changedKeys = [
      ...new Set([
        ...Object.keys(baseline),
        ...Object.keys(workingConfig ?? {}),
      ]),
    ].filter(
      (key) =>
        key !== "enabled" &&
        !isEqual(baseline[key], workingConfig?.[key])
    );
    const submittedConfig = cloneDeep(config ?? {});
    changedKeys.forEach((key) => {
      if (Object.prototype.hasOwnProperty.call(workingConfig, key)) {
        submittedConfig[key] = cloneDeep(workingConfig[key]);
      } else {
        delete submittedConfig[key];
      }
    });
    submittedConfig.enabled = config?.enabled ?? workingConfig.enabled;
    changeConfig(submittedConfig);
  };

  const handleNumberValidity = (field) => (valid) => {
    setInvalidNumberFields((current) => {
      const currentlyInvalid = current.has(field);
      if (currentlyInvalid === !valid) return current;
      const next = new Set(current);
      if (valid) next.delete(field);
      else next.add(field);
      return next;
    });
  };

  const handleWorkingChanges = (propName) => (value) => {
    // When Event object is being passed in as a value
    if (typeof value === "object" && "target" in value) {
      const isNumber = value.target.type === "number";
      value = isNumber ? Number(value.target.value) : value.target.value;
    }
    setWorkingConfig((prevConfig) => ({
      ...prevConfig,
      [propName]: value,
    }));
  };

  const handleRemoveVoteFlag = (index) => {
    setInvalidNumberFields(
      (current) =>
        new Set([...current].filter((key) => !key.startsWith("vote_flags.")))
    );
    setWorkingConfig((prev) => ({
      ...prev,
      vote_flags: prev.vote_flags.filter((_, i) => i !== index),
    }));
  };

  const handleRemovePlayerChoiceFlag = (index) => {
    setWorkingConfig((prev) => ({
      ...prev,
      player_choice_flags: prev.player_choice_flags.filter(
        (_, i) => i !== index
      ),
    }));
  };

  const handleRemoveVoteBanFlag = (index) => {
    setWorkingConfig((prev) => ({
      ...prev,
      vote_ban_flags: prev.vote_ban_flags.filter((_, i) => i !== index),
    }));
  };

  const handleRemoveAllowOnlyFlag = (index) => {
    setWorkingConfig((prev) => ({
      ...prev,
      allow_flag_only: (prev.allow_flag_only || []).filter(
        (_, i) => i !== index
      ),
    }));
  };

  const handleRemoveFlag = (index) => {
    switch (emojiPickerMode) {
      case "update_vote_flag":
        handleRemoveVoteFlag(index);
        break;
      case "update_player_choice_flag":
        handleRemovePlayerChoiceFlag(index);
        break;
      case "update_vote_ban_flag":
        handleRemoveVoteBanFlag(index);
        break;
      case "update_allow_flag_only":
        handleRemoveAllowOnlyFlag(index);
        break;
      default:
        break;
    }
  };

  const handlePlayerChoiceFlagChange = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = [...(prev.player_choice_flags || [])];
      updated[index] = value;
      return { ...prev, player_choice_flags: updated };
    });
  };

  const handleAddPlayerChoiceFlag = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = (prev.player_choice_flags || []).concat(value);
      return { ...prev, player_choice_flags: updated };
    });
  };

  const handleVoteBanFlagChange = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = [...(prev.vote_ban_flags || [])];
      updated[index] = value;
      return { ...prev, vote_ban_flags: updated };
    });
  };

  const handleAllowOnlyFlagChange = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = [...(prev.allow_flag_only || [])];
      updated[index] = value;
      return { ...prev, allow_flag_only: updated };
    });
  };

  const handleAddVoteBanFlag = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = (prev.vote_ban_flags || []).concat(value);
      return { ...prev, vote_ban_flags: updated };
    });
  };

  const handleAddVoteFlag = (index, value) => {
    setWorkingConfig((prev) => {
      const another = { flag: value, vote_count: 1 };
      const updated = (prev.vote_flags || []).concat(another);
      return { ...prev, vote_flags: updated };
    });
  };

  const handleAddAllowOnlyFlag = (index, value) => {
    setWorkingConfig((prev) => {
      const updated = (prev.allow_flag_only || []).concat(value);
      return { ...prev, allow_flag_only: updated };
    });
  };

  const handleVoteFlagChange = (index, key, value) => {
    if (key === "vote_count" && (value === undefined || value === null)) {
      return;
    }
    setWorkingConfig((prev) => {
      const updated = [...(prev.vote_flags || [])];
      if (key === "vote_count") {
        value = Math.max(0, Math.min(100, Number(value)));
      }
      updated[index] = { ...updated[index], [key]: value };
      return { ...prev, vote_flags: updated };
    });
  };

  const handleOpenEmojiPicker = (index, mode) => {
    setEmojiPickerIndex(index);
    setEmojiPickerOpen(true);
    setEmojiPickerMode(mode);
  };

  const handleCloseEmojiPicker = () => {
    setEmojiPickerIndex(null);
    setEmojiPickerOpen(false);
    setEmojiPickerMode(null);
  };

  const handleEmojiSelected = (emoji) => {
    if (emojiPickerIndex !== null && emojiPickerMode !== null) {
      switch (emojiPickerMode) {
        case "update_vote_flag":
          handleVoteFlagChange(emojiPickerIndex, "flag", emoji.native);
          break;
        case "update_player_choice_flag":
          handlePlayerChoiceFlagChange(emojiPickerIndex, emoji.native);
          break;
        case "update_vote_ban_flag":
          handleVoteBanFlagChange(emojiPickerIndex, emoji.native);
          break;
        case "update_allow_flag_only":
          handleAllowOnlyFlagChange(emojiPickerIndex, emoji.native);
          break;
        case "add_player_choice_flag":
          handleAddPlayerChoiceFlag(emojiPickerIndex, emoji.native);
          break;
        case "add_vote_ban_flag":
          handleAddVoteBanFlag(emojiPickerIndex, emoji.native);
          break;
        case "add_vote_flag":
          handleAddVoteFlag(emojiPickerIndex, emoji.native);
          break;
        case "add_allow_flag_only":
          handleAddAllowOnlyFlag(emojiPickerIndex, emoji.native);
          break;
        default:
          break;
      }
    }
    handleCloseEmojiPicker();
  };

  const totalMapOptions = gameModeOptionConfigs.reduce(
    (sum, configItem) => sum + (Number(workingConfig[configItem.name]) || 0),
    0
  );
  const hasMapOptions = totalMapOptions > 0;
  const configuredMessageCount = messageFieldConfigs.filter((configItem) =>
    String(workingConfig[configItem.name] ?? "").trim()
  ).length;
  const permissionSummary = workingConfig.allow_vip_only
    ? t("maps.votemapWorkbench.vipOnly")
    : (workingConfig.allow_flag_only || []).length > 0
    ? t("maps.votemapWorkbench.markerRestricted", {
        count: workingConfig.allow_flag_only.length,
      })
    : t("maps.votemapWorkbench.allPlayers");
  const reminderSummary =
    Number(workingConfig.reminder_frequency_minutes) === 0
      ? t("maps.votemapWorkbench.disabled")
      : t("maps.votemapWorkbench.everyMinutes", {
          count: workingConfig.reminder_frequency_minutes,
        });
  const selectedDefaultMethod = defaultMapOptions.find(
    (option) => option.name === workingConfig.default_method
  );
  const defaultMethodSummary = selectedDefaultMethod
    ? t(`maps.votemapSettings.${selectedDefaultMethod.labelKey}`)
    : t("common.unknown");

  const renderRuleToggle = (configItem, { disabled = false } = {}) => (
    <RuleToggle
      key={configItem.name}
      label={getLabel(configItem)}
      checked={workingConfig[configItem.name]}
      disabled={disabled}
      onChange={handleWorkingChanges(configItem.name)}
    />
  );

  useEffect(handleIncomingConfigChange, [config, workingConfig]);

  return (
    <>
      <Box
        sx={{
          width: { xs: "calc(100vw - 12px)", md: "100%" },
          maxWidth: { xs: "calc(100vw - 12px)", md: "100%" },
          boxSizing: "border-box",
          minWidth: 0,
          overflowX: "hidden",
          p: { xs: 1.5, md: 2.5 },
          pb: 1.5,
        }}
      >
        <Box
          component="section"
          aria-labelledby="votemap-effect-summary-title"
          sx={{
            mb: 1.25,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          <Typography
            id="votemap-effect-summary-title"
            variant="overline"
            color="primary.main"
            sx={{ display: "block", px: 2, pt: 1.25 }}
          >
            {t("maps.votemapWorkbench.effectSummary")}
          </Typography>
          <Box
            data-testid="votemap-effect-summary"
            sx={{
              display: "grid",
              width: "100%",
              minWidth: 0,
              gridTemplateColumns: {
                xs: "minmax(0, 1fr)",
                sm: "repeat(2, minmax(0, 1fr))",
                lg: "repeat(4, minmax(0, 1fr))",
              },
              "& > *": {
                borderRight: { xs: 0, sm: "1px solid" },
                borderBottom: { xs: "1px solid", sm: 0 },
                borderColor: "divider",
              },
              "& > *:nth-of-type(2n)": {
                borderRight: { sm: 0, lg: "1px solid" },
              },
              "& > *:nth-of-type(n+3)": {
                borderTop: { sm: "1px solid", lg: 0 },
                borderColor: "divider",
              },
              "& > *:last-of-type": { borderRight: 0, borderBottom: 0 },
            }}
          >
            <SummaryMetric
              icon={<BallotOutlinedIcon />}
              label={t("maps.votemapWorkbench.optionMix")}
              value={t("maps.votemapWorkbench.mapsTotal", {
                count: totalMapOptions,
              })}
            />
            <SummaryMetric
              icon={<NotificationsNoneOutlinedIcon />}
              label={t("maps.votemapWorkbench.reminders")}
              value={reminderSummary}
            />
            <SummaryMetric
              icon={<GroupsOutlinedIcon />}
              label={t("maps.votemapWorkbench.eligibility")}
              value={permissionSummary}
            />
            <SummaryMetric
              icon={<StarBorderOutlinedIcon />}
              label={t("maps.votemapWorkbench.vip")}
              value={t("maps.votemapWorkbench.voteWeight", {
                count: workingConfig.vip_vote_count,
              })}
            />
          </Box>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "minmax(0, 1fr)",
              lg: "minmax(360px, 0.82fr) minmax(480px, 1.18fr)",
            },
            gap: 1.25,
            alignItems: "stretch",
          }}
        >
          <Card
            data-testid="votemap-mode-matrix"
            component="section"
            aria-labelledby="votemap-modes-heading"
            variant="outlined"
          sx={workbenchCardSx}
          >
            <CardContent
              sx={{
                p: 1.5,
                "&:last-child": { pb: 1.5 },
              }}
            >
              <SectionHeading
                number="1"
                title={t("maps.votemapWorkbench.modeSectionTitle")}
                description={t("maps.votemapWorkbench.modeSectionDescription")}
              />
              <Divider sx={{ my: 1.25 }} />
              <Stack spacing={0} divider={<Divider flexItem />}>
                {gameModeOptionConfigs.map((configItem) => (
                  <Stack
                    key={configItem.name}
                    data-testid={`votemap-mode-row-${configItem.name}`}
                    direction="row"
                    justifyContent="space-between"
                    alignItems="center"
                    gap={2}
                    sx={{ minHeight: 45, py: 0.35 }}
                  >
                    <Stack
                      direction="row"
                      spacing={1}
                      alignItems="center"
                      sx={{ minWidth: 0 }}
                    >
                      <MapOutlinedIcon
                        fontSize="small"
                        sx={{ color: "text.secondary", flex: "0 0 auto" }}
                      />
                      <Typography variant="body2" fontWeight={750}>
                        {getLabel(configItem)}
                      </Typography>
                    </Stack>
                    <NumberStepper
                      compact
                      label={getLabel(configItem)}
                      value={workingConfig[configItem.name]}
                      inputProps={configItem.inputProps}
                      invalidHelperText={t(
                        "maps.votemapWorkbench.invalidNumber"
                      )}
                      onValidityChange={handleNumberValidity(configItem.name)}
                      onChange={(value) => {
                        if (value !== undefined)
                          handleWorkingChanges(configItem.name)(value);
                      }}
                    />
                  </Stack>
                ))}
              </Stack>
              {!hasMapOptions && (
                <Typography
                  role="alert"
                  variant="caption"
                  color="error.main"
                  sx={{ display: "block", mt: 1 }}
                >
                  {t("maps.votemapWorkbench.requireMapOption")}
                </Typography>
              )}
              <Divider sx={{ my: 1.25 }} />
              <FormControl fullWidth size="small">
                <InputLabel id="default_method">
                  {t("maps.votemapWorkbench.fallbackSelection")}
                </InputLabel>
                <Select
                  value={workingConfig.default_method ?? ""}
                  onChange={handleWorkingChanges("default_method")}
                  label={t("maps.votemapWorkbench.fallbackSelection")}
                  labelId="default_method"
                >
                  {defaultMapOptions.map((option) => (
                    <MenuItem key={option.name} value={option.name}>
                      {t(`maps.votemapSettings.${option.labelKey}`)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>
            </CardContent>
          </Card>

          <Card
            component="section"
            aria-labelledby="votemap-rules-heading"
            variant="outlined"
            sx={workbenchCardSx}
          >
            <CardContent
              sx={{
                p: 1.5,
                "&:last-child": { pb: 1.5 },
              }}
            >
              <SectionHeading
                number="2"
                title={t("maps.votemapWorkbench.selectionRulesTitle")}
                description={t(
                  "maps.votemapWorkbench.selectionRulesDescription"
                )}
              />
              <Divider sx={{ my: 1.25 }} />
              {primaryRuleGroups.map((group, groupIndex) => (
                <Box key={group.id} sx={{ mt: groupIndex ? 0.75 : 0 }}>
                  <Typography
                    variant="overline"
                    color="primary.main"
                    sx={{ display: "block", mb: 0.25 }}
                  >
                    {t(`maps.votemapWorkbench.ruleGroups.${group.id}`)}
                  </Typography>
                  <Stack spacing={0.1}>
                    {group.configNames.map((name) =>
                      renderRuleToggle(findPadlockConfig(name))
                    )}
                  </Stack>
                  <Divider sx={{ mt: 0.75 }} />
                </Box>
              ))}
              <Box sx={{ mt: 0.75 }}>
                <Typography
                  variant="overline"
                  color="primary.main"
                  sx={{ display: "block", mb: 0.5 }}
                >
                  {t("maps.votemapWorkbench.ruleGroups.reminders")}
                </Typography>
                <Stack spacing={0.25}>
                  {renderRuleToggle(findPadlockConfig("allow_opt_out"))}
                  <Stack
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                    alignItems={{ xs: "flex-start", sm: "center" }}
                    gap={1}
                    sx={{ minHeight: 32 }}
                  >
                    <Typography variant="body2">
                      {getLabel(reminderFrequencyConfig)}
                    </Typography>
                    <NumberStepper
                      compact
                      label={getLabel(reminderFrequencyConfig)}
                      value={workingConfig[reminderFrequencyConfig.name]}
                      inputProps={reminderFrequencyConfig.inputProps}
                      invalidHelperText={t(
                        "maps.votemapWorkbench.invalidNumber"
                      )}
                      onValidityChange={handleNumberValidity(
                        reminderFrequencyConfig.name
                      )}
                      onChange={(value) => {
                        if (value !== undefined)
                          handleWorkingChanges(reminderFrequencyConfig.name)(
                            value
                          );
                      }}
                    />
                  </Stack>
                  {renderRuleToggle(findPadlockConfig("remind_on_match_start"))}
                  {renderRuleToggle(findPadlockConfig("remind_on_match_end"))}
                </Stack>
              </Box>
              <Divider sx={{ my: 0.75 }} />
              <Typography
                variant="overline"
                color="primary.main"
                sx={{ display: "block", mb: 0.25 }}
              >
                {t("maps.votemapWorkbench.ruleGroups.vipAccess")}
              </Typography>
              {renderRuleToggle(findPadlockConfig("allow_vip_only"))}
            </CardContent>
          </Card>
        </Box>

        <Box sx={{ mt: 1.25 }}>
          <WorkbenchAccordion
            number="3"
            testId="votemap-accordion-messages"
            title={t("maps.messages")}
            summary={t("maps.votemapWorkbench.messagesConfigured", {
              count: configuredMessageCount,
            })}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  lg: "repeat(2, minmax(0, 1fr))",
                },
                gap: 1.5,
              }}
            >
              {messageFieldConfigs.map((configItem) => (
                <TextField
                  key={configItem.name}
                  fullWidth
                  variant="filled"
                  multiline
                  minRows={configItem.name === "no_vote_text" ? 2 : 4}
                  maxRows={8}
                  label={getLabel(configItem)}
                  helperText={getHelperText(configItem)}
                  error={
                    configItem.name === "instruction_text" &&
                    !instructionTextIsValid
                  }
                  FormHelperTextProps={{
                    component: "div",
                  }}
                  value={workingConfig[configItem.name] ?? ""}
                  onChange={handleWorkingChanges(configItem.name)}
                  sx={{
                    gridColumn:
                      configItem.name === "instruction_text"
                        ? { lg: "1 / -1" }
                        : undefined,
                    "& .MuiFilledInput-root": { borderRadius: 0 },
                  }}
                />
              ))}
              {!instructionTextIsValid && (
                <Typography
                  role="alert"
                  variant="caption"
                  color="error.main"
                  sx={{ gridColumn: { lg: "1 / -1" } }}
                >
                  {t("maps.votemapWorkbench.requireMapSelectionPlaceholder")}
                </Typography>
              )}
            </Box>
          </WorkbenchAccordion>

          <WorkbenchAccordion
            number="4"
            testId="votemap-accordion-permissions"
            title={t("maps.votemapWorkbench.markersAndPermissions")}
            summary={t("maps.votemapWorkbench.permissionsSummary", {
              access: permissionSummary,
              count: workingConfig.vip_vote_count,
            })}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  lg: "repeat(2, minmax(0, 1fr))",
                },
                gap: 2,
              }}
            >
              <Box>
                <Typography
                  variant="subtitle2"
                  fontWeight={850}
                  sx={{ mb: 0.5 }}
                >
                  {t("maps.votemapWorkbench.vipWeightTitle")}
                </Typography>
                <NumberStepper
                  label={getLabel(vipVoteCountConfig)}
                  value={workingConfig[vipVoteCountConfig.name]}
                  inputProps={vipVoteCountConfig.inputProps}
                  helperText={getHelperText(vipVoteCountConfig)}
                  invalidHelperText={t("maps.votemapWorkbench.invalidNumber")}
                  onValidityChange={handleNumberValidity(
                    vipVoteCountConfig.name
                  )}
                  onChange={(value) => {
                    if (value !== undefined)
                      handleWorkingChanges(vipVoteCountConfig.name)(value);
                  }}
                />
              </Box>
              <Box>
                <Typography variant="subtitle2" fontWeight={850}>
                  {t("maps.votemapAdvanced.voteCountFlags")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("maps.votemapAdvanced.voteCountFlagsHelp")}
                </Typography>
                <Stack
                  direction="row"
                  gap={1}
                  flexWrap="wrap"
                  alignItems="flex-start"
                  sx={{ mt: 1 }}
                >
                  {(workingConfig.vote_flags || []).map((item, idx) => (
                    <Stack
                      key={`${item.flag}-${idx}`}
                      direction="row"
                      spacing={0.5}
                      alignItems="flex-start"
                    >
                      <Button
                        variant="outlined"
                        aria-label={`${t(
                          "maps.votemapAdvanced.voteCountFlags"
                        )}: ${item.flag || "?"}`}
                        onClick={() =>
                          handleOpenEmojiPicker(idx, "update_vote_flag")
                        }
                        sx={{
                          minWidth: 44,
                          minHeight: 40,
                          borderRadius: 0,
                          fontSize: 22,
                        }}
                      >
                        <Emoji emoji={item.flag || "❓"} />
                      </Button>
                      <StableNumberField
                        label={t("maps.votemapAdvanced.voteCount")}
                        slotProps={{ htmlInput: { min: 1, max: 100 } }}
                        value={item.vote_count}
                        requiredValue
                        invalidHelperText={t(
                          "maps.votemapWorkbench.invalidNumber"
                        )}
                        onValidityChange={handleNumberValidity(
                          `vote_flags.${idx}`
                        )}
                        onChange={(value) =>
                          handleVoteFlagChange(idx, "vote_count", value)
                        }
                        sx={{
                          width: 112,
                          "& .MuiOutlinedInput-root": { borderRadius: 0 },
                        }}
                      />
                    </Stack>
                  ))}
                  <IconButton
                    aria-label={t("maps.votemapWorkbench.addVoteWeightFlag")}
                    sx={{
                      width: 40,
                      height: 40,
                      border: "1px solid",
                      borderColor: "divider",
                      borderRadius: 0,
                    }}
                    onClick={() =>
                      handleOpenEmojiPicker(
                        (workingConfig.vote_flags || []).length,
                        "add_vote_flag"
                      )
                    }
                  >
                    <AddCircleIcon />
                  </IconButton>
                </Stack>
              </Box>
              <FlagChooserGroup
                title={t("maps.votemapAdvanced.voteWhitelistFlags")}
                help={t("maps.votemapAdvanced.voteWhitelistFlagsHelp")}
                items={workingConfig.allow_flag_only || []}
                addLabel={t("maps.votemapWorkbench.addAllowedFlag")}
                onEdit={(index) =>
                  handleOpenEmojiPicker(index, "update_allow_flag_only")
                }
                onAdd={() =>
                  handleOpenEmojiPicker(
                    (workingConfig.allow_flag_only || []).length,
                    "add_allow_flag_only"
                  )
                }
              />
              <FlagChooserGroup
                title={t("maps.votemapAdvanced.voteBanFlags")}
                help={t("maps.votemapAdvanced.voteBanFlagsHelp")}
                items={workingConfig.vote_ban_flags || []}
                addLabel={t("maps.votemapWorkbench.addBlockedFlag")}
                onEdit={(index) =>
                  handleOpenEmojiPicker(index, "update_vote_ban_flag")
                }
                onAdd={() =>
                  handleOpenEmojiPicker(
                    (workingConfig.vote_ban_flags || []).length,
                    "add_vote_ban_flag"
                  )
                }
              />
              <FlagChooserGroup
                title={t("maps.votemapAdvanced.playerChoiceWhitelistFlags")}
                help={t("maps.votemapAdvanced.playerChoiceWhitelistFlagsHelp")}
                items={workingConfig.player_choice_flags || []}
                addLabel={t("maps.votemapWorkbench.addPlayerChoiceFlag")}
                onEdit={(index) =>
                  handleOpenEmojiPicker(index, "update_player_choice_flag")
                }
                onAdd={() =>
                  handleOpenEmojiPicker(
                    (workingConfig.player_choice_flags || []).length,
                    "add_player_choice_flag"
                  )
                }
              />
            </Box>
          </WorkbenchAccordion>

          <WorkbenchAccordion
            number="5"
            testId="votemap-accordion-advanced"
            title={t("maps.votemapWorkbench.advancedSelectionRules")}
            summary={t("maps.votemapWorkbench.advancedSummary", {
              method: defaultMethodSummary,
              count: workingConfig.number_last_played_to_exclude,
            })}
          >
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  lg: "minmax(260px, 0.75fr) minmax(0, 1.25fr)",
                },
                gap: 2,
              }}
            >
              <NumberStepper
                label={getLabel(recentMapsConfig)}
                value={workingConfig[recentMapsConfig.name]}
                inputProps={recentMapsConfig.inputProps}
                helperText={getHelperText(recentMapsConfig)}
                invalidHelperText={t("maps.votemapWorkbench.invalidNumber")}
                onValidityChange={handleNumberValidity(recentMapsConfig.name)}
                onChange={(value) => {
                  if (value !== undefined)
                    handleWorkingChanges(recentMapsConfig.name)(value);
                }}
              />
              <Stack spacing={0.25}>
                {advancedRuleConfigs.map((configItem) =>
                  renderRuleToggle(configItem)
                )}
              </Stack>
            </Box>
          </WorkbenchAccordion>
        </Box>

        <Dialog
          open={emojiPickerOpen}
          onClose={handleCloseEmojiPicker}
          aria-labelledby="votemap-emoji-picker-title"
          maxWidth="xs"
          fullWidth
        >
          <DialogTitle id="votemap-emoji-picker-title">
            {t("maps.votemapWorkbench.chooseMarker")}
          </DialogTitle>
          <DialogContent dividers sx={{ p: 0, overflow: "hidden" }}>
            <Suspense
              fallback={
                <Typography sx={{ p: 3 }}>
                  {t("maps.votemapAdvanced.loadingEmojiPicker")}
                </Typography>
              }
            >
              <EmojiPicker
                set="twitter"
                theme={theme.palette.mode}
                data={emojiData}
                onEmojiSelect={handleEmojiSelected}
              />
              {!emojiPickerMode?.startsWith("add_") && (
                <Button
                  onClick={() => {
                    handleRemoveFlag(emojiPickerIndex);
                    handleCloseEmojiPicker();
                  }}
                  variant="contained"
                  color="error"
                  fullWidth
                  sx={{ minHeight: 44, borderRadius: 0 }}
                >
                  {t("settings.general.remove")}
                </Button>
              )}
            </Suspense>
          </DialogContent>
        </Dialog>
      </Box>

      <ConfigActionBar
        mobileSticky={false}
        dirty={isConfigDirty}
        dirtyLabel={t("maps.votemapWorkbench.unsavedChanges")}
        stateIcon={
          isConfigDirty ? (
            <WarningAmberOutlinedIcon color="warning" fontSize="small" />
          ) : (
            <CheckCircleOutlineIcon color="success" fontSize="small" />
          )
        }
        stateLabel={
          isConfigDirty
            ? t("maps.votemapWorkbench.settingsChangesPending")
            : t("maps.votemapWorkbench.settingsSaved")
        }
        stateDescription={t("maps.votemapWorkbench.settingsStateDescription")}
        secondaryActions={[
          {
            id: "reset-votemap-settings",
            label: t("maps.votemapSettings.reset"),
            startIcon: <ReplayIcon />,
            disabled: !isConfigDirty || isConfigSaving,
            onClick: handleConfigReset,
          },
        ]}
        primaryAction={{
          label: t("common.save"),
          loadingLabel: t("common.loading"),
          startIcon: isConfigSaving ? (
            <CircularProgress size={18} />
          ) : (
            <SaveIcon />
          ),
          disabled:
            !isConfigDirty ||
            isConfigSaving ||
            invalidNumberFields.size > 0 ||
            !hasMapOptions ||
            !instructionTextIsValid ||
            !canChangeConfig,
          loading: isConfigSaving,
          onClick: handleConfigSave,
        }}
      />
    </>
  );
}

export default VotemapSettingsPage;
