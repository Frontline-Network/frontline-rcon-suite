export const padlockConfigs = [
  { name: "allow_opt_out", labelKey: "allowOptOut" },
  { name: "consider_offensive_same_map", labelKey: "considerOffensiveSameMap" },
  {
    name: "consider_skirmishes_as_same_map",
    labelKey: "considerSkirmishesSameMap",
  },
  {
    name: "consider_environment_as_same_map",
    translationKey: "maps.votemapAdvanced.considerEnvironmentSameMap",
  },
  {
    name: "allow_consecutive_offensives",
    labelKey: "allowConsecutiveOffensives",
  },
  {
    name: "allow_consecutive_offensives_opposite_sides",
    labelKey: "allowConsecutiveOffensivesOppositeSides",
  },
  {
    name: "allow_consecutive_skirmishes",
    labelKey: "allowConsecutiveSkirmishes",
  },
  { name: "allow_default_to_offensive", labelKey: "allowDefaultToOffensive" },
  { name: "allow_default_to_skirmish", labelKey: "allowDefaultToSkirmish" },
  {
    name: "allow_multiple_maps_with_same_environment",
    translationKey: "maps.votemapAdvanced.allowMultipleMapsSameEnvironment",
  },
  {
    name: "remind_on_match_start",
    translationKey: "maps.votemapAdvanced.remindOnMatchStart",
  },
  {
    name: "remind_on_match_end",
    translationKey: "maps.votemapAdvanced.remindOnMatchEnd",
  },
  {
    name: "allow_vip_only",
    translationKey: "maps.votemapAdvanced.allowVipOnly",
  },
];

export const messageFieldConfigs = [
  {
    name: "instruction_text",
    labelKey: "instructionText",
    helperKey: "instructionTextHelp",
    rows: 10,
  },
  {
    name: "thank_you_text",
    labelKey: "thankYouText",
    helperKey: "thankYouTextHelp",
    rows: 10,
  },
  {
    name: "help_text",
    labelKey: "helpText",
    helperKey: "helpTextHelp",
    rows: 10,
  },
  {
    name: "player_choice_help_text",
    translationKey: "maps.votemapAdvanced.playerChoiceHelpText",
    helperTranslationKey: "maps.votemapAdvanced.playerChoiceHelpTextHelp",
    rows: 10,
  },
  {
    name: "no_vote_text",
    translationKey: "maps.votemapAdvanced.noVoteText",
    helperTranslationKey: "maps.votemapAdvanced.noVoteTextHelp",
    rows: 1,
  },
];

export const textFieldConfigs = [
  {
    name: "reminder_frequency_minutes",
    labelKey: "reminderFrequency",
    helperKey: "reminderFrequencyHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "num_warfare_options",
    labelKey: "warfareOptions",
    helperKey: "warfareOptionsHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "num_offensive_options",
    labelKey: "offensiveOptions",
    helperKey: "offensiveOptionsHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "num_conquest_options",
    labelKey: "conquestOptions",
    helperKey: "conquestOptionsHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "num_domination_options",
    labelKey: "dominationOptions",
    helperKey: "dominationOptionsHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "num_skirmish_control_options",
    labelKey: "skirmishOptions",
    helperKey: "skirmishOptionsHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "number_last_played_to_exclude",
    labelKey: "recentMapsExcluded",
    helperKey: "recentMapsExcludedHelp",
    inputProps: { min: 0, step: 1 },
  },
  {
    name: "vip_vote_count",
    translationKey: "maps.votemapAdvanced.vipVoteCount",
    helperTranslationKey: "maps.votemapAdvanced.vipVoteCountHelp",
    inputProps: { min: 1, max: 100, step: 1 },
  },
];

export const defaultMapOptions = [
  {
    name: "least_played_from_suggestions",
    labelKey: "leastPlayedSuggestions",
  },
  {
    name: "least_played_from_all_map",
    labelKey: "leastPlayedAll",
  },
  {
    name: "random_from_suggestions",
    labelKey: "randomSuggestions",
  },
  {
    name: "random_from_all_maps",
    labelKey: "randomAll",
  },
];
