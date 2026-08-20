export const GENERAL_SETTING_METADATA = {
  team_switch_cooldown: {
    recommendedValue: null,
    unit: "minutes",
    changePermission: "can_change_team_switch_cooldown",
    conflictKey: "autoSettings",
  },
  max_ping_autokick: {
    recommendedValue: null,
    unit: "milliseconds",
    changePermission: "can_change_max_ping_autokick",
    conflictKey: "autoSettings",
  },
  queue_length: {
    recommendedValue: 6,
    unit: "players",
    changePermission: "can_change_queue_length",
    conflictKey: "autoSettings",
  },
  vip_slots_num: {
    recommendedValue: 2,
    unit: "slots",
    changePermission: "can_change_vip_slots",
    conflictKey: "vipAutomation",
  },
  autobalance_enabled: {
    recommendedValue: null,
    unit: "boolean",
    changePermission: "can_change_autobalance_enabled",
    conflictKey: "autobalancer",
  },
  autobalance_threshold: {
    recommendedValue: null,
    unit: "players",
    changePermission: "can_change_autobalance_threshold",
    conflictKey: "autobalancer",
  },
  idle_autokick_time: {
    recommendedValue: null,
    unit: "minutes",
    changePermission: "can_change_idle_autokick_time",
    conflictKey: "autoSettings",
  },
  votekick_enabled: {
    recommendedValue: null,
    unit: "boolean",
    changePermission: "can_change_votekick_enabled",
    conflictKey: "autoVotekick",
  },
  votekick_thresholds: {
    recommendedValue: [
      [0, 1],
      [10, 5],
      [25, 12],
      [50, 20],
    ],
    unit: "thresholds",
    changePermission: "can_change_votekick_threshold",
    conflictKey: "autoVotekick",
  },
};

export const getGeneralSettingMetadata = (settingKey) =>
  GENERAL_SETTING_METADATA[settingKey] || null;
