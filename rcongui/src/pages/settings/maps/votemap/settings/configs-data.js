export const padlockConfigs = [
    { name: "allow_opt_out", labelKey: "allowOptOut" },
    { name: "consider_offensive_same_map", labelKey: "considerOffensiveSameMap" },
    { name: "consider_skirmishes_as_same_map", labelKey: "considerSkirmishesSameMap" },
    { name: "allow_consecutive_offensives", labelKey: "allowConsecutiveOffensives" },
    { name: "allow_consecutive_offensives_opposite_sides", labelKey: "allowConsecutiveOffensivesOppositeSides" },
    { name: "allow_consecutive_skirmishes", labelKey: "allowConsecutiveSkirmishes" },
    { name: "allow_default_to_offensive", labelKey: "allowDefaultToOffensive" },
    { name: "allow_default_to_skirmish", labelKey: "allowDefaultToSkirmish" },
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
];

export const textFieldConfigs = [
    {
        name: "reminder_frequency_minutes",
        labelKey: "reminderFrequency",
        helperKey: "reminderFrequencyHelp",
        inputProps: { min: 0, max: 90 },
    },
    {
        name: "num_warfare_options",
        labelKey: "warfareOptions",
        helperKey: "warfareOptionsHelp",
    },
    {
        name: "num_offensive_options",
        labelKey: "offensiveOptions",
        helperKey: "offensiveOptionsHelp",
    },
    {
        name: "num_skirmish_control_options",
        labelKey: "skirmishOptions",
        helperKey: "skirmishOptionsHelp",
    },
    {
        name: "number_last_played_to_exclude",
        labelKey: "recentMapsExcluded",
        helperKey: "recentMapsExcludedHelp",
        inputProps: { min: 0, max: 6, step: 1 },
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
]
