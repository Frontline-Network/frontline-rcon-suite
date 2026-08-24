const ROOT = "settings.configForms";

const pageKeys = (page) => ({
  eyebrowKey: `${ROOT}.${page}.eyebrow`,
  titleKey: `${ROOT}.${page}.title`,
  introKey: `${ROOT}.${page}.intro`,
});

const noLeaderSection = (id, fields) => ({
  id,
  titleKey: `${ROOT}.noLeader.sections.${id}.title`,
  descriptionKey: `${ROOT}.noLeader.sections.${id}.description`,
  fields,
});

const genericSection = (id, fields) => ({
  id,
  titleKey: `${ROOT}.workbench.sectionTitles.${id}`,
  descriptionKey: `${ROOT}.workbench.sectionDescriptions.${id}`,
  fields,
});

const field = (name, metadata = {}) => ({
  labelKey: `${ROOT}.noLeader.fields.${name}.label`,
  helpKey: `${ROOT}.noLeader.fields.${name}.help`,
  ...metadata,
});

const schemaProfile = (page, sections, summarySectionIds) => ({
  ...pageKeys(page),
  renderer: "schema",
  sections: sections.map(([id, fields]) => genericSection(id, fields)),
  fields: {},
  summarySectionIds,
});

const noLeaderProfile = {
  ...pageKeys("noLeader"),
  renderer: "guided",
  summary: {
    titleKey: `${ROOT}.noLeader.summary.title`,
    descriptionKey: `${ROOT}.noLeader.summary.description`,
  },
  sections: [
    noLeaderSection("operation", ["enabled", "dry_run"]),
    noLeaderSection("exemptions", [
      "whitelist_flags",
      "immune_roles",
      "immune_player_level",
      "dont_do_anything_below_this_number_of_players",
    ]),
    noLeaderSection("observation", [
      "number_of_notes",
      "notes_interval_seconds",
    ]),
    noLeaderSection("warnings", [
      "number_of_warnings",
      "warning_interval_seconds",
      "warning_message",
    ]),
    noLeaderSection("punishments", [
      "number_of_punishments",
      "min_squad_players_for_punish",
      "min_server_players_for_punish",
      "punish_interval_seconds",
      "punish_message",
    ]),
    noLeaderSection("kick", [
      "kick_after_max_punish",
      "min_squad_players_for_kick",
      "min_server_players_for_kick",
      "kick_grace_period_seconds",
      "kick_message",
    ]),
    noLeaderSection("notifications", ["discord_webhook_url"]),
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
  auto_mod_level_config: schemaProfile(
    "level",
    [
      ["operation", ["enabled", "dry_run"]],
      [
        "exemptions",
        [
          "whitelist_flags",
          "dont_do_anything_below_this_number_of_players",
          "levelbug_enabled",
        ],
      ],
      [
        "rules",
        [
          "min_level",
          "max_level",
          "level_thresholds",
          "min_level_message",
          "max_level_message",
          "violation_message",
          "force_kick_message",
        ],
      ],
      [
        "announcements",
        [
          "announcement_enabled",
          "only_announce_impacted_players",
          "announcement_message",
        ],
      ],
      [
        "warnings",
        ["number_of_warnings", "warning_interval_seconds", "warning_message"],
      ],
      [
        "punishments",
        [
          "number_of_punishments",
          "min_squad_players_for_punish",
          "min_server_players_for_punish",
          "punish_interval_seconds",
          "punish_message",
        ],
      ],
      [
        "kick",
        [
          "kick_after_max_punish",
          "min_squad_players_for_kick",
          "min_server_players_for_kick",
          "kick_grace_period_seconds",
          "kick_message",
        ],
      ],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["rules", "warnings", "punishments", "kick"]
  ),
  auto_mod_seeding_config: schemaProfile(
    "seeding",
    [
      ["operation", ["enabled", "dry_run"]],
      [
        "exemptions",
        [
          "whitelist_flags",
          "immune_roles",
          "immune_player_level",
          "dont_do_anything_below_this_number_of_players",
        ],
      ],
      [
        "rules",
        ["disallowed_roles", "disallowed_weapons", "enforce_cap_fight"],
      ],
      ["announcements", ["announcement_enabled", "announcement_message"]],
      [
        "warnings",
        ["number_of_warnings", "warning_interval_seconds", "warning_message"],
      ],
      [
        "punishments",
        [
          "number_of_punishments",
          "min_squad_players_for_punish",
          "min_server_players_for_punish",
          "punish_interval_seconds",
          "punish_message",
        ],
      ],
      [
        "kick",
        [
          "kick_after_max_punish",
          "min_squad_players_for_kick",
          "min_server_players_for_kick",
          "kick_grace_period_seconds",
          "kick_message",
        ],
      ],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["rules", "warnings", "punishments", "kick"]
  ),
  auto_mod_solo_tank_config: schemaProfile(
    "noSoloTank",
    [
      ["operation", ["enabled", "dry_run"]],
      [
        "exemptions",
        [
          "whitelist_flags",
          "immune_player_level",
          "dont_do_anything_below_this_number_of_players",
        ],
      ],
      ["observation", ["number_of_notes", "notes_interval_seconds"]],
      [
        "warnings",
        ["number_of_warnings", "warning_interval_seconds", "warning_message"],
      ],
      [
        "punishments",
        [
          "number_of_punishments",
          "min_server_players_for_punish",
          "punish_interval_seconds",
          "punish_message",
        ],
      ],
      [
        "kick",
        [
          "kick_after_max_punish",
          "min_server_players_for_kick",
          "kick_grace_period_seconds",
          "kick_message",
        ],
      ],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["observation", "warnings", "punishments", "kick"]
  ),
  vac_game_bans_config: schemaProfile(
    "vacBans",
    [
      ["rules", ["vac_history_days", "game_ban_threshhold"]],
      ["actions", ["blacklist_id", "ban_on_vac_history_reason", "auto_expire"]],
      ["exemptions", ["whitelist_flags"]],
    ],
    ["rules", "actions", "exemptions"]
  ),
  tk_ban_on_connect_config: schemaProfile(
    "tkBans",
    [
      ["operation", ["enabled"]],
      [
        "detection",
        [
          "max_time_after_connect_minutes",
          "ignore_tk_after_n_kills",
          "ignore_tk_after_n_deaths",
          "teamkill_tolerance_count",
        ],
      ],
      ["exemptions", ["excluded_weapons", "whitelist_players"]],
      ["actions", ["message", "author_name", "blacklist_id", "ban_duration"]],
      ["notifications", ["discord_webhook_url", "discord_webhook_message"]],
    ],
    ["detection", "actions", "exemptions", "notifications"]
  ),
  name_kick_config: schemaProfile(
    "nameKicks",
    [
      ["rules", ["regular_expressions"]],
      ["exemptions", ["whitelist_flags"]],
      ["actions", ["kick_reason"]],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["rules", "actions", "exemptions", "notifications"]
  ),
  seed_vip_config: schemaProfile(
    "seedVip",
    [
      [
        "operation",
        [
          "enabled",
          "dry_run",
          "language",
          "poll_time_seeding",
          "poll_time_seeded",
        ],
      ],
      ["requirements", ["requirements", "player_announce_thresholds"]],
      ["reward", ["reward", "nice_time_delta", "nice_expiration_date"]],
      ["messages", ["player_messages"]],
      ["notifications", ["hooks"]],
    ],
    ["requirements", "reward", "messages", "notifications"]
  ),
  expired_vip_config: schemaProfile(
    "expiredVip",
    [
      ["operation", ["enabled"]],
      ["schedule", ["interval_minutes"]],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["operation", "schedule", "notifications"]
  ),
};

const sectionOrder = [
  "operation",
  "scope",
  "requirements",
  "detection",
  "rules",
  "exemptions",
  "schedule",
  "announcements",
  "warnings",
  "punishments",
  "kick",
  "actions",
  "reward",
  "messages",
  "notifications",
  "advanced",
];

const classifyField = (name) => {
  if (["enabled", "dry_run", "language", "mode"].includes(name))
    return "operation";
  if (/webhook|hooks|discord/i.test(name)) return "notifications";
  if (/whitelist|immune|excluded|ignore_/i.test(name)) return "exemptions";
  if (/message|reason|author/i.test(name)) return "messages";
  if (/reward|vip/i.test(name)) return "reward";
  if (/kick/i.test(name)) return "kick";
  if (/punish/i.test(name)) return "punishments";
  if (/ban|blacklist|action|expire/i.test(name)) return "actions";
  if (/interval|poll|schedule|frequency/i.test(name)) return "schedule";
  if (/threshold|requirement|condition|min_|max_/i.test(name))
    return "requirements";
  if (/detect|tolerance|watch|history/i.test(name)) return "detection";
  if (/rule|weapon|role|expression|filter|word/i.test(name)) return "rules";
  return "advanced";
};

const buildGenericProfile = (schema) => {
  const groups = new Map(sectionOrder.map((id) => [id, []]));
  Object.keys(schema?.properties || {}).forEach((name) => {
    groups.get(classifyField(name)).push(name);
  });
  const sections = sectionOrder
    .filter((id) => groups.get(id).length)
    .map((id) => genericSection(id, groups.get(id)));
  return {
    renderer: "schema",
    sections,
    fields: {},
    summarySectionIds: sections.slice(0, 4).map(({ id }) => id),
  };
};

const finalizeProfile = (profile, schema) => {
  if (!profile || !schema?.properties) return profile;
  const available = new Set(Object.keys(schema.properties));
  const known = new Set();
  const sections = profile.sections
    .map((entry) => ({
      ...entry,
      fields: entry.fields.filter((name) => available.has(name)),
    }))
    .filter((entry) => entry.fields.length)
    .map((entry) => {
      entry.fields.forEach((name) => known.add(name));
      return entry;
    });
  const remaining = [...available].filter((name) => !known.has(name));
  if (remaining.length) sections.push(genericSection("advanced", remaining));
  return { ...profile, sections };
};

export const getConfigFormProfile = (command, schema) =>
  finalizeProfile(
    configFormProfiles[command] || buildGenericProfile(schema),
    schema
  );

export const getProfileFieldOrder = (profile, fieldNames = []) => {
  if (!profile) return [...fieldNames];

  const ordered = profile.sections.flatMap(({ fields }) => fields);
  const available = new Set(fieldNames);
  const known = ordered.filter((name) => available.has(name));
  const knownSet = new Set(known);

  return [...known, ...fieldNames.filter((name) => !knownSet.has(name))];
};
