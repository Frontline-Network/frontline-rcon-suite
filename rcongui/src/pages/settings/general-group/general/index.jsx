import React from "react";
import { Alert, Grid2 as Grid, Stack } from "@mui/material";
import BalanceIcon from "@mui/icons-material/Balance";
import GavelIcon from "@mui/icons-material/Gavel";
import TimerIcon from "@mui/icons-material/Timer";
import NetworkPingIcon from "@mui/icons-material/NetworkPing";
import QueueIcon from "@mui/icons-material/Queue";
import StarIcon from "@mui/icons-material/Star";
import AccessTimeIcon from "@mui/icons-material/AccessTime";
import HowToVoteIcon from "@mui/icons-material/HowToVote";
import RuleIcon from "@mui/icons-material/Rule";
import { cmd } from "@/utils/fetchUtils";
import { useLoaderData } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  AutoVotekickSetting,
  GENERAL_KEY,
  SliderSetting,
  ThresholdsSetting,
  ToggleSetting,
} from "../components";
import AdminActionContext from "@/components/shared/AdminActionContext";

function GeneralSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();

  return (
    <Stack spacing={2}>
      <AdminActionContext />
      <Alert severity="warning">{t("settingEffect.unverified")}</Alert>
      <Grid container spacing={1}>
        <SliderSetting
          settingKey={GENERAL_KEY.team_switch_cooldown}
          payloadKey={"minutes"}
          title={t("settings.general.cards.teamSwitchCooldown.title")}
          subheader={t("settings.general.cards.teamSwitchCooldown.subtitle")}
          icon={TimerIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_TEAM_SWITCH_COOLDOWN}
          initialData={loaderData.settings}
        />

        <SliderSetting
          settingKey={GENERAL_KEY.max_ping_autokick}
          payloadKey={"max_ms"}
          title={t("settings.general.cards.maxPingAutokick.title")}
          subheader={t("settings.general.cards.maxPingAutokick.subtitle")}
          icon={NetworkPingIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_MAX_PING_AUTOKICK}
          initialData={loaderData.settings}
        />

        <SliderSetting
          settingKey={GENERAL_KEY.queue_length}
          payloadKey={"value"}
          title={t("settings.general.cards.queueLength.title")}
          subheader={t("settings.general.cards.queueLength.subtitle")}
          icon={QueueIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.APPLY_QUEUE_LENGTH}
          initialData={loaderData.settings}
        />

        <SliderSetting
          settingKey={GENERAL_KEY.vip_slots_num}
          payloadKey={"value"}
          title={t("settings.general.cards.vipSlots.title")}
          subheader={t("settings.general.cards.vipSlots.subtitle")}
          icon={StarIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.APPLY_VIP_SLOTS_NUM}
          initialData={loaderData.settings}
        />

        <ToggleSetting
          settingKey={GENERAL_KEY.autobalance_enabled}
          payloadKey={"value"}
          title={t("settings.general.cards.autobalance.title")}
          subheader={t("settings.general.cards.autobalance.subtitle")}
          icon={BalanceIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_AUTOBALANCE_ENABLED}
          initialData={loaderData.settings}
        />

        <SliderSetting
          settingKey={GENERAL_KEY.autobalance_threshold}
          payloadKey={"max_diff"}
          title={t("settings.general.cards.autobalanceThreshold.title")}
          subheader={t("settings.general.cards.autobalanceThreshold.subtitle")}
          icon={BalanceIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_AUTOBALANCE_THRESHOLD}
          initialData={loaderData.settings}
        />

        <SliderSetting
          settingKey={GENERAL_KEY.idle_autokick_time}
          payloadKey={"minutes"}
          title={t("settings.general.cards.idleAutokick.title")}
          subheader={t("settings.general.cards.idleAutokick.subtitle")}
          icon={AccessTimeIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_IDLE_AUTOKICK_TIME}
          initialData={loaderData.settings}
        />

        <ToggleSetting
          settingKey={GENERAL_KEY.votekick_enabled}
          payloadKey={"value"}
          title={t("settings.general.cards.votekick.title")}
          subheader={t("settings.general.cards.votekick.subtitle")}
          icon={HowToVoteIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_VOTEKICK_ENABLED}
          initialData={loaderData.settings}
        />

        <ThresholdsSetting
          settingKey={GENERAL_KEY.votekick_thresholds}
          payloadKey={"threshold_pairs"}
          title={t("settings.general.cards.votekickThresholds.title")}
          subheader={t("settings.general.cards.votekickThresholds.subtitle")}
          icon={RuleIcon}
          queryKey={{ queryIdentifier: "get_server_settings" }}
          mutationFn={cmd.SET_VOTEKICK_THRESHOLDS}
          initialData={loaderData.settings}
        />

        <AutoVotekickSetting
          title={t("settings.general.cards.autoVotekick.title")}
          subheader={t("settings.general.cards.autoVotekick.subtitle")}
          icon={GavelIcon}
          queryKey={{ queryIdentifier: "get_votekick_autotoggle_config" }}
          mutationFn={cmd.SET_VOTEKICK_AUTOTOGGLE_CONFIG}
          initialData={loaderData.autokickSettings}
        />
      </Grid>
    </Stack>
  );
}

export default GeneralSettings;
