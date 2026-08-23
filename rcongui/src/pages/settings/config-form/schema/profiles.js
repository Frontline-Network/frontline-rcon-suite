const ROOT = "settings.configForms";

const pageKeys = (page) => ({
  eyebrowKey: `${ROOT}.${page}.eyebrow`,
  titleKey: `${ROOT}.${page}.title`,
  introKey: `${ROOT}.${page}.intro`,
});

const section = (id, fields) => ({
  id,
  titleKey: `${ROOT}.noLeader.sections.${id}.title`,
  descriptionKey: `${ROOT}.noLeader.sections.${id}.description`,
  fields,
});

const field = (name, metadata = {}) => ({
  labelKey: `${ROOT}.noLeader.fields.${name}.label`,
  helpKey: `${ROOT}.noLeader.fields.${name}.help`,
  ...metadata,
});

const noLeaderProfile = {
  ...pageKeys("noLeader"),
  summary: {
    titleKey: `${ROOT}.noLeader.summary.title`,
    descriptionKey: `${ROOT}.noLeader.summary.description`,
  },
  sections: [
    section("operation", ["enabled", "dry_run"]),
    section("exemptions", [
      "whitelist_flags",
      "immune_roles",
      "immune_player_level",
      "dont_do_anything_below_this_number_of_players",
    ]),
    section("observation", ["number_of_notes", "notes_interval_seconds"]),
    section("warnings", [
      "number_of_warnings",
      "warning_interval_seconds",
      "warning_message",
    ]),
    section("punishments", [
      "number_of_punishments",
      "min_squad_players_for_punish",
      "min_server_players_for_punish",
      "punish_interval_seconds",
      "punish_message",
    ]),
    section("kick", [
      "kick_after_max_punish",
      "min_squad_players_for_kick",
      "min_server_players_for_kick",
      "kick_grace_period_seconds",
      "kick_message",
    ]),
    section("notifications", ["discord_webhook_url"]),
  ],
  fields: {
    enabled: field("enabled", { kind: "toggle" }),
    dry_run: field("dry_run", { kind: "toggle" }),
    discord_webhook_url: field("discord_webhook_url", {
      kind: "url",
      placeholderKey: `${ROOT}.noLeader.fields.discord_webhook_url.placeholder`,
    }),
    whitelist_flags: field("whitelist_flags", { kind: "tags" }),
    immune_roles: field("immune_roles", { kind: "roles" }),
    immune_player_level: field("immune_player_level", {
      kind: "number",
      unitKey: `${ROOT}.units.level`,
      specialValues: { 0: "disabled" },
    }),
    dont_do_anything_below_this_number_of_players: field(
      "dont_do_anything_below_this_number_of_players",
      {
        kind: "number",
        unitKey: `${ROOT}.units.players`,
        specialValues: { 0: "noMinimum" },
      }
    ),
    number_of_notes: field("number_of_notes", {
      kind: "number",
      unitKey: `${ROOT}.units.checks`,
      specialValues: { 0: "skip" },
    }),
    notes_interval_seconds: field("notes_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
    }),
    number_of_warnings: field("number_of_warnings", {
      kind: "number",
      unitKey: `${ROOT}.units.messages`,
      specialValues: { 0: "skip", "-1": "unlimited" },
    }),
    warning_interval_seconds: field("warning_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    warning_message: field("warning_message", {
      kind: "textarea",
      placeholders: [
        "{player_name}",
        "{squad_name}",
        "{max_warnings}",
        "{received_warnings}",
        "{next_check_seconds}",
      ],
    }),
    number_of_punishments: field("number_of_punishments", {
      kind: "number",
      unitKey: `${ROOT}.units.actions`,
      specialValues: { 0: "skip", "-1": "unlimited" },
    }),
    min_squad_players_for_punish: field("min_squad_players_for_punish", {
      kind: "number",
      unitKey: `${ROOT}.units.squadPlayers`,
      specialValues: { 0: "anySquadSize" },
    }),
    min_server_players_for_punish: field("min_server_players_for_punish", {
      kind: "number",
      unitKey: `${ROOT}.units.players`,
      specialValues: { 0: "noMinimum" },
    }),
    punish_interval_seconds: field("punish_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    punish_message: field("punish_message", {
      kind: "textarea",
      placeholders: [
        "{player_name}",
        "{squad_name}",
        "{max_punishes}",
        "{received_punishes}",
        "{next_check_seconds}",
      ],
    }),
    kick_after_max_punish: field("kick_after_max_punish", { kind: "toggle" }),
    min_squad_players_for_kick: field("min_squad_players_for_kick", {
      kind: "number",
      unitKey: `${ROOT}.units.squadPlayers`,
      specialValues: { 0: "anySquadSize" },
    }),
    min_server_players_for_kick: field("min_server_players_for_kick", {
      kind: "number",
      unitKey: `${ROOT}.units.players`,
      specialValues: { 0: "noMinimum" },
    }),
    kick_grace_period_seconds: field("kick_grace_period_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    kick_message: field("kick_message", {
      kind: "textarea",
      placeholders: ["{player_name}", "{squad_name}", "{kick_grace_period}"],
    }),
  },
};

const configFormProfiles = {
  auto_mod_no_leader_config: noLeaderProfile,
  auto_mod_level_config: {
    ...pageKeys("level"),
    sections: [],
    fields: {},
  },
  auto_mod_seeding_config: {
    ...pageKeys("seeding"),
    sections: [],
    fields: {},
  },
  auto_mod_solo_tank_config: {
    ...pageKeys("noSoloTank"),
    sections: [],
    fields: {},
  },
};

export const getConfigFormProfile = (command) =>
  configFormProfiles[command] || null;

export const getProfileFieldOrder = (profile, fieldNames = []) => {
  if (!profile) return [...fieldNames];

  const ordered = profile.sections.flatMap(({ fields }) => fields);
  const available = new Set(fieldNames);
  const known = ordered.filter((name) => available.has(name));
  const knownSet = new Set(known);

  return [...known, ...fieldNames.filter((name) => !knownSet.has(name))];
};
