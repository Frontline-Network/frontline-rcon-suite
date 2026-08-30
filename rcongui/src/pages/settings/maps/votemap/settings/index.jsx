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
import transform from "lodash/transform";
import { toast } from "react-toastify";
import { VotemapChangeNotification } from "./VotemapChangeNotification";
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import {
  defaultMapOptions,
  messageFieldConfigs,
  padlockConfigs,
  textFieldConfigs,
} from "./configs-data";
import Padlock from "@/components/shared/Padlock";
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
import ConfigActionBar from "@/pages/settings/config-form/ConfigActionBar";
import ConfigFormSection from "@/pages/settings/config-form/ConfigFormSection";
import StableNumberField from "@/pages/settings/config-form/StableNumberField";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";

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
    onSuccess: (response) => {
      // Update this reference so the user does not get change
      // notification about his own changes
      prevConfig.current = cloneDeep(workingConfig);
      if (fakeMode) {
        queryClient.setQueryData(
          mapsManagerQueryKeys.voteMapConfig,
          response.arguments
        );
      } else {
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
  const [workingConfig, setWorkingConfig] = useState(config);
  const [emojiPickerOpen, setEmojiPickerOpen] = useState(false);
  const [emojiPickerIndex, setEmojiPickerIndex] = useState(null);
  const [emojiPickerMode, setEmojiPickerMode] = useState(null);
  const [invalidNumberFields, setInvalidNumberFields] = useState(
    () => new Set()
  );
  const isConfigDirty = useMemo(
    () => !isEqual(workingConfig, config),
    [workingConfig, config]
  );

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
    const diff = transform(
      prevConfig.current,
      (result, value, key) => {
        if (!isEqual(value, config[key])) {
          result.push(key);
        }
      },
      []
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
            actionableDiff.forEach((key) => {
              combined[key] = cloneDeep(config[key]);
            });
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
    setWorkingConfig(cloneDeep(prevConfig.current));
  };

  const handleConfigSave = () => {
    changeConfig(workingConfig);
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

  useEffect(handleIncomingConfigChange, [config, workingConfig]);

  return (
    <>
      <Box sx={{ p: { xs: 1.5, md: 2.5 }, pb: 0 }}>
        <Box sx={{ mb: 2 }}>
          <Typography variant="overline" color="primary.main">
            {t("maps.votemapWorkbench.settingsEyebrow")}
          </Typography>
          <Typography component="h2" variant="h5" fontWeight={850}>
            {t("maps.votemapWorkbench.settingsTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>
            {t("maps.votemapWorkbench.settingsDescription")}
          </Typography>
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              lg: "minmax(0, 0.9fr) minmax(0, 1.1fr)",
            },
            gap: 2,
            alignItems: "start",
          }}
        >
          <ConfigFormSection
            id="votemap-messages"
            eyebrow={t("maps.votemapWorkbench.messagesEyebrow")}
            title={t("maps.messages")}
            description={t("maps.votemapWorkbench.messagesDescription")}
          >
            <Stack spacing={1.5}>
              {messageFieldConfigs.map((configItem) => (
                <TextField
                  key={configItem.name}
                  fullWidth
                  variant="filled"
                  multiline
                  rows={configItem.rows}
                  label={getLabel(configItem)}
                  helperText={getHelperText(configItem)}
                  value={workingConfig[configItem.name] ?? ""}
                  onChange={handleWorkingChanges(configItem.name)}
                />
              ))}
            </Stack>
          </ConfigFormSection>

          <ConfigFormSection
            id="votemap-rules"
            eyebrow={t("maps.votemapWorkbench.rulesEyebrow")}
            title={t("maps.configuration")}
            description={t("maps.votemapWorkbench.rulesDescription")}
          >
            <Stack spacing={1.25}>
              <FormControl>
                <InputLabel id="default_method">
                  {t("maps.votemapSettings.defaultMapMethod")}
                </InputLabel>
                <Select
                  value={workingConfig.default_method ?? ""}
                  onChange={handleWorkingChanges("default_method")}
                  label={t("maps.votemapSettings.defaultMapMethod")}
                  labelId="default_method"
                >
                  {defaultMapOptions.map((option) => (
                    <MenuItem key={option.name} value={option.name}>
                      {t(`maps.votemapSettings.${option.labelKey}`)}
                    </MenuItem>
                  ))}
                </Select>
              </FormControl>

              <Divider flexItem orientation={"horizontal"} />

              {padlockConfigs.map((configItem) => (
                <Padlock
                  key={configItem.name}
                  label={getLabel(configItem)}
                  checked={workingConfig[configItem.name] ?? false}
                  handleChange={handleWorkingChanges(configItem.name)}
                />
              ))}

              <Divider flexItem orientation={"horizontal"} />

              {textFieldConfigs.map((configItem) => (
                <StableNumberField
                  key={configItem.name}
                  variant="filled"
                  fullWidth
                  slotProps={{
                    htmlInput: configItem.inputProps,
                  }}
                  label={getLabel(configItem)}
                  helperText={getHelperText(configItem)}
                  value={workingConfig[configItem.name]}
                  requiredValue
                  invalidHelperText={t("maps.votemapWorkbench.invalidNumber")}
                  onValidityChange={handleNumberValidity(configItem.name)}
                  onChange={(value) => {
                    if (value !== undefined) {
                      handleWorkingChanges(configItem.name)(value);
                    }
                  }}
                />
              ))}

              <Divider flexItem orientation={"horizontal"} />

              {/* Vote Flags Section */}
              <Typography variant="subtitle1">
                {t("maps.votemapAdvanced.voteCountFlags")}
              </Typography>
              <Typography variant="caption">
                {t("maps.votemapAdvanced.voteCountFlagsHelp")}
              </Typography>
              <Stack
                direction="row"
                gap={1}
                flexWrap={"wrap"}
                alignItems={"center"}
              >
                {(workingConfig.vote_flags || []).map((item, idx) => (
                  <Stack
                    key={idx}
                    direction="row"
                    gap={0.25}
                    alignItems="center"
                  >
                    <Button
                      variant="outlined"
                      aria-label={`${t(
                        "maps.votemapAdvanced.voteCountFlags"
                      )}: ${item.flag || "?"}`}
                      onClick={() =>
                        handleOpenEmojiPicker(idx, "update_vote_flag")
                      }
                      sx={{ minWidth: 48, minHeight: 44, fontSize: 24 }}
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
                      sx={{ width: 112 }}
                    />
                  </Stack>
                ))}
                <IconButton
                  variant="outlined"
                  aria-label={t("maps.votemapWorkbench.addVoteWeightFlag")}
                  sx={{ width: 44, height: 44 }}
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

              <Divider flexItem orientation={"horizontal"} />

              {/* Vote Whitelist Flags Section */}
              <Typography variant="subtitle1">
                {t("maps.votemapAdvanced.voteWhitelistFlags")}
              </Typography>
              <Typography variant="caption">
                {t("maps.votemapAdvanced.voteWhitelistFlagsHelp")}
              </Typography>
              <Stack
                direction="row"
                flexWrap={"wrap"}
                gap={1}
                alignItems="center"
              >
                {(workingConfig.allow_flag_only || []).map((item, idx) => (
                  <Button
                    key={idx}
                    variant="outlined"
                    aria-label={`${t(
                      "maps.votemapAdvanced.voteWhitelistFlags"
                    )}: ${item || "?"}`}
                    onClick={() =>
                      handleOpenEmojiPicker(idx, "update_allow_flag_only")
                    }
                    sx={{ minWidth: 48, minHeight: 44, fontSize: 24 }}
                  >
                    <Emoji emoji={item ?? "❓"} />
                  </Button>
                ))}
                <IconButton
                  variant="outlined"
                  aria-label={t("maps.votemapWorkbench.addAllowedFlag")}
                  sx={{ width: 44, height: 44 }}
                  onClick={() =>
                    handleOpenEmojiPicker(
                      (workingConfig.allow_flag_only || []).length,
                      "add_allow_flag_only"
                    )
                  }
                >
                  <AddCircleIcon />
                </IconButton>
              </Stack>

              {/* Vote Ban Flags Section */}
              <Typography variant="subtitle1">
                {t("maps.votemapAdvanced.voteBanFlags")}
              </Typography>
              <Typography variant="caption">
                {t("maps.votemapAdvanced.voteBanFlagsHelp")}
              </Typography>
              <Stack
                direction="row"
                flexWrap={"wrap"}
                gap={1}
                alignItems="center"
              >
                {(workingConfig.vote_ban_flags || []).map((item, idx) => (
                  <Button
                    key={idx}
                    variant="outlined"
                    aria-label={`${t("maps.votemapAdvanced.voteBanFlags")}: ${
                      item || "?"
                    }`}
                    onClick={() =>
                      handleOpenEmojiPicker(idx, "update_vote_ban_flag")
                    }
                    sx={{ minWidth: 48, minHeight: 44, fontSize: 24 }}
                  >
                    <Emoji emoji={item ?? "❓"} />
                  </Button>
                ))}
                <IconButton
                  variant="outlined"
                  aria-label={t("maps.votemapWorkbench.addBlockedFlag")}
                  sx={{ width: 44, height: 44 }}
                  onClick={() =>
                    handleOpenEmojiPicker(
                      (workingConfig.vote_ban_flags || []).length,
                      "add_vote_ban_flag"
                    )
                  }
                >
                  <AddCircleIcon />
                </IconButton>
              </Stack>

              <Divider flexItem orientation={"horizontal"} />

              {/* Player Choice Flags Section */}
              <Typography variant="subtitle1">
                {t("maps.votemapAdvanced.playerChoiceWhitelistFlags")}
              </Typography>
              <Typography variant="caption">
                {t("maps.votemapAdvanced.playerChoiceWhitelistFlagsHelp")}
              </Typography>
              <Stack
                direction="row"
                flexWrap={"wrap"}
                gap={1}
                alignItems="center"
              >
                {(workingConfig.player_choice_flags || []).map((item, idx) => (
                  <Button
                    key={idx}
                    variant="outlined"
                    aria-label={`${t(
                      "maps.votemapAdvanced.playerChoiceWhitelistFlags"
                    )}: ${item || "?"}`}
                    onClick={() =>
                      handleOpenEmojiPicker(idx, "update_player_choice_flag")
                    }
                    sx={{ minWidth: 48, minHeight: 44, fontSize: 24 }}
                  >
                    <Emoji emoji={item ?? "❓"} />
                  </Button>
                ))}
                <IconButton
                  variant="outlined"
                  aria-label={t("maps.votemapWorkbench.addPlayerChoiceFlag")}
                  sx={{ width: 44, height: 44 }}
                  onClick={() =>
                    handleOpenEmojiPicker(
                      (workingConfig.player_choice_flags || []).length,
                      "add_player_choice_flag"
                    )
                  }
                >
                  <AddCircleIcon />
                </IconButton>
              </Stack>
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
                        sx={{ minHeight: 44 }}
                      >
                        {t("settings.general.remove")}
                      </Button>
                    )}
                  </Suspense>
                </DialogContent>
              </Dialog>
            </Stack>
          </ConfigFormSection>
        </Box>
      </Box>

      <ConfigActionBar
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
            !canChangeConfig,
          loading: isConfigSaving,
          onClick: handleConfigSave,
        }}
      />
    </>
  );
}

export default VotemapSettingsPage;
