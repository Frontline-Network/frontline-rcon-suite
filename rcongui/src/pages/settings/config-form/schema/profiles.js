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

const noSoloTankSection = (id, fields) => ({
  id,
  titleKey: `${ROOT}.noSoloTank.sections.${id}.title`,
  descriptionKey: `${ROOT}.noSoloTank.sections.${id}.description`,
  fields,
});

const nameKickSection = (id, fields) => ({
  id,
  titleKey: `${ROOT}.nameKicks.sections.${id}.title`,
  descriptionKey: `${ROOT}.nameKicks.sections.${id}.description`,
  fields,
});

const genericSection = (page, id, fields) => ({
  id,
  titleKey: page
    ? `${ROOT}.${page}.sections.${id}.title`
    : `${ROOT}.workbench.sectionTitles.${id}`,
  descriptionKey: page
    ? `${ROOT}.${page}.sections.${id}.description`
    : `${ROOT}.workbench.sectionDescriptions.${id}`,
  fields,
});

const seedingSection = (id, fields) => ({
  id,
  titleKey: `${ROOT}.seedingWorkbench.sections.${id}.title`,
  descriptionKey: `${ROOT}.seedingWorkbench.sections.${id}.description`,
  fields,
});

const field = (name, metadata = {}) => ({
  labelKey: `${ROOT}.noLeader.fields.${name}.label`,
  helpKey: `${ROOT}.noLeader.fields.${name}.help`,
  ...metadata,
});

const soloTankField = (name, metadata = {}) => ({
  labelKey: `${ROOT}.noSoloTank.fields.${name}.label`,
  helpKey: `${ROOT}.noSoloTank.fields.${name}.help`,
  ...metadata,
});

const schemaProfile = (
  page,
  sections,
  summarySectionIds,
  { operationMode = null, testKind = null } = {}
) => ({
  ...pageKeys(page),
  page,
  renderer: "schema",
  layout: "workbench",
  translationRoot: `${ROOT}.${page}`,
  operationMode,
  testKind,
  sections: sections.map(([id, fields]) => genericSection(page, id, fields)),
  fields: {},
  summarySectionIds,
});

const noLeaderProfile = {
  ...pageKeys("noLeader"),
  renderer: "guided",
  testKind: "noLeader",
  translationRoot: `${ROOT}.noLeader`,
  summary: {
    titleKey: `${ROOT}.noLeader.summary.title`,
    descriptionKey: `${ROOT}.noLeader.summary.description`,
  },
  sections: [
    noLeaderSection("operation", [
      "enabled",
      "dry_run",
      "dont_do_anything_below_this_number_of_players",
    ]),
    noLeaderSection("detection", ["number_of_notes", "notes_interval_seconds"]),
    noLeaderSection("exemptions", [
      "whitelist_flags",
      "immune_roles",
      "immune_player_level",
    ]),
    noLeaderSection("actions", [
      "number_of_warnings",
      "warning_interval_seconds",
      "warning_message",
      "number_of_punishments",
      "min_squad_players_for_punish",
      "min_server_players_for_punish",
      "punish_interval_seconds",
      "punish_message",
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

const noSoloTankProfile = {
  ...pageKeys("noSoloTank"),
  renderer: "guided",
  testKind: "noSoloTank",
  translationRoot: `${ROOT}.noSoloTank`,
  summary: {
    titleKey: `${ROOT}.noSoloTank.summary.title`,
    descriptionKey: `${ROOT}.noSoloTank.summary.description`,
  },
  sections: [
    noSoloTankSection("operation", [
      "enabled",
      "dry_run",
      "dont_do_anything_below_this_number_of_players",
    ]),
    noSoloTankSection("detection", [
      "number_of_notes",
      "notes_interval_seconds",
    ]),
    noSoloTankSection("exemptions", ["whitelist_flags", "immune_player_level"]),
    noSoloTankSection("actions", [
      "number_of_warnings",
      "warning_interval_seconds",
      "warning_message",
      "number_of_punishments",
      "min_server_players_for_punish",
      "punish_interval_seconds",
      "punish_message",
      "kick_after_max_punish",
      "min_server_players_for_kick",
      "kick_grace_period_seconds",
      "kick_message",
    ]),
    noSoloTankSection("notifications", ["discord_webhook_url"]),
  ],
  fields: {
    enabled: soloTankField("enabled", { kind: "toggle" }),
    dry_run: soloTankField("dry_run", { kind: "toggle" }),
    discord_webhook_url: soloTankField("discord_webhook_url", {
      kind: "url",
      placeholderKey: `${ROOT}.noSoloTank.fields.discord_webhook_url.placeholder`,
    }),
    whitelist_flags: soloTankField("whitelist_flags", { kind: "tags" }),
    immune_player_level: soloTankField("immune_player_level", {
      kind: "number",
      unitKey: `${ROOT}.units.level`,
      specialValues: { 0: "disabled" },
    }),
    dont_do_anything_below_this_number_of_players: soloTankField(
      "dont_do_anything_below_this_number_of_players",
      {
        kind: "number",
        unitKey: `${ROOT}.units.players`,
        specialValues: { 0: "noMinimum" },
      }
    ),
    number_of_notes: soloTankField("number_of_notes", {
      kind: "number",
      unitKey: `${ROOT}.units.checks`,
      specialValues: { 0: "skip" },
    }),
    notes_interval_seconds: soloTankField("notes_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
    }),
    number_of_warnings: soloTankField("number_of_warnings", {
      kind: "number",
      unitKey: `${ROOT}.units.messages`,
      specialValues: { 0: "skip", "-1": "unlimited" },
    }),
    warning_interval_seconds: soloTankField("warning_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    warning_message: soloTankField("warning_message", {
      kind: "textarea",
      placeholders: [
        "{player_name}",
        "{squad_name}",
        "{max_warnings}",
        "{received_warnings}",
        "{next_check_seconds}",
      ],
    }),
    number_of_punishments: soloTankField("number_of_punishments", {
      kind: "number",
      unitKey: `${ROOT}.units.actions`,
      specialValues: { 0: "skip", "-1": "unlimited" },
    }),
    min_server_players_for_punish: soloTankField(
      "min_server_players_for_punish",
      {
        kind: "number",
        unitKey: `${ROOT}.units.players`,
        specialValues: { 0: "noMinimum" },
      }
    ),
    punish_interval_seconds: soloTankField("punish_interval_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    punish_message: soloTankField("punish_message", {
      kind: "textarea",
      placeholders: [
        "{player_name}",
        "{squad_name}",
        "{max_punishes}",
        "{received_punishes}",
        "{next_check_seconds}",
      ],
    }),
    kick_after_max_punish: soloTankField("kick_after_max_punish", {
      kind: "toggle",
    }),
    min_server_players_for_kick: soloTankField("min_server_players_for_kick", {
      kind: "number",
      unitKey: `${ROOT}.units.players`,
      specialValues: { 0: "noMinimum" },
    }),
    kick_grace_period_seconds: soloTankField("kick_grace_period_seconds", {
      kind: "number",
      unitKey: `${ROOT}.units.seconds`,
      specialValues: { 0: "noDelay" },
    }),
    kick_message: soloTankField("kick_message", {
      kind: "textarea",
      placeholders: ["{player_name}", "{squad_name}", "{kick_grace_period}"],
    }),
  },
};

const nameKickProfile = {
  ...pageKeys("nameKicks"),
  renderer: "nameKick",
  translationRoot: `${ROOT}.nameKicks`,
  sections: [
    nameKickSection("rules", ["regular_expressions"]),
    nameKickSection("exemptions", ["whitelist_flags"]),
    nameKickSection("actions", ["kick_reason"]),
    nameKickSection("notifications", ["discord_webhook_url"]),
  ],
  fields: {},
  summarySectionIds: ["rules", "actions", "exemptions", "notifications"],
};

const configFormProfiles = {
  autobalancer_config: schemaProfile(
    "autobalancer",
    [
      ["operation", ["mode"]],
      [
        "intervention",
        ["target_difference", "minimum_players", "stable_difference_seconds"],
      ],
      [
        "squads",
        [
          "coordinated_squad_switches_enabled",
          "allow_individual_squad_fallback",
        ],
      ],
      [
        "safety",
        [
          "volunteer_phase_seconds",
          "map_start_grace_minutes",
          "map_end_guard_minutes",
          "connection_grace_seconds",
          "cooldown_maps",
          "max_switches_per_incident",
        ],
      ],
      ["messages", ["volunteer_command", "messages"]],
      [
        "advanced",
        [
          "poll_interval_seconds",
          "candidate_timeout_seconds",
          "manual_proposal_timeout_seconds",
          "death_event_max_age_seconds",
          "switch_confirmation_timeout_seconds",
          "skill_strategy",
          "skill_gap_soft_limit",
          "skill_gap_hard_warning",
          "skill_gap_min_improvement",
          "history_server_numbers",
          "history_half_life_days",
        ],
      ],
    ],
    ["operation", "intervention", "squads", "safety"]
  ),
  rcon_connection_settings_config: schemaProfile(
    "rconConnection",
    [
      ["connections", ["thread_pool_size"]],
      [
        "telemetry",
        [
          "performance_statistics_enabled",
          "performance_statistics_interval_seconds",
        ],
      ],
    ],
    ["connections", "telemetry"]
  ),
  rcon_server_settings_config: schemaProfile(
    "crconRuntime",
    [
      ["identity", ["short_name", "server_url", "discord_invite_url"]],
      ["access", ["lock_stats_api", "broadcast_unbans"]],
      [
        "refresh",
        [
          "live_stats_refresh_seconds",
          "live_stats_refresh_current_game_seconds",
        ],
      ],
      ["windowsStore", ["windows_store_players"]],
      ["messages", ["message_enhancements"]],
    ],
    ["identity", "access", "refresh", "windowsStore"]
  ),
  steam_config: schemaProfile(
    "steamApi",
    [["credentials", ["api_key"]]],
    ["credentials"]
  ),
  log_stream_config: schemaProfile(
    "logStream",
    [
      ["capacity", ["stream_size", "startup_since_mins"]],
      ["refresh", ["refresh_frequency_sec", "refresh_since_mins"]],
    ],
    ["capacity", "refresh"],
    { operationMode: "toggle" }
  ),
  watch_killrate_config: schemaProfile(
    "watchKillrate",
    [
      [
        "timing",
        [
          "match_start_cooldown_secs",
          "watch_interval_secs",
          "report_cooldown_mins",
        ],
      ],
      [
        "thresholds",
        [
          "min_kills",
          "killrate_threshold",
          "killrate_threshold_armor",
          "killrate_threshold_artillery",
          "killrate_threshold_mg",
        ],
      ],
      [
        "exceptions",
        [
          "only_report_once_per_match",
          "whitelist_flags",
          "ignore_armor",
          "ignore_artillery",
          "ignore_mg",
        ],
      ],
      ["notifications", ["author", "webhooks"]],
    ],
    ["timing", "thresholds", "exceptions", "notifications"],
    { operationMode: "toggle" }
  ),
  auto_mod_no_leader_config: noLeaderProfile,
  auto_mod_level_config: schemaProfile(
    "level",
    [
      ["operation", ["dont_do_anything_below_this_number_of_players"]],
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
      ["exemptions", ["whitelist_flags", "levelbug_enabled"]],
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
    ["rules", "warnings", "punishments", "kick"],
    { operationMode: "threeState", testKind: "level" }
  ),
  auto_mod_seeding_config: {
    ...pageKeys("seeding"),
    renderer: "seeding",
    sections: [
      seedingSection("operation", [
        "enabled",
        "dry_run",
        "dont_do_anything_below_this_number_of_players",
      ]),
      seedingSection("rules", [
        "disallowed_roles",
        "disallowed_weapons",
        "enforce_cap_fight",
      ]),
      seedingSection("exemptions", [
        "whitelist_flags",
        "immune_roles",
        "immune_player_level",
      ]),
      seedingSection("actions", [
        "announcement_enabled",
        "announcement_message",
        "number_of_warnings",
        "warning_interval_seconds",
        "warning_message",
        "number_of_punishments",
        "min_squad_players_for_punish",
        "min_server_players_for_punish",
        "punish_interval_seconds",
        "punish_message",
        "kick_after_max_punish",
        "min_squad_players_for_kick",
        "min_server_players_for_kick",
        "kick_grace_period_seconds",
        "kick_message",
      ]),
      seedingSection("notifications", ["discord_webhook_url"]),
    ],
    fields: {},
    summarySectionIds: ["rules", "actions"],
  },
  auto_mod_solo_tank_config: noSoloTankProfile,
  vac_game_bans_config: schemaProfile(
    "vacBans",
    [
      ["rules", ["vac_history_days", "game_ban_threshhold"]],
      ["actions", ["blacklist_id", "ban_on_vac_history_reason", "auto_expire"]],
      ["exemptions", ["whitelist_flags"]],
    ],
    ["rules", "actions", "exemptions"],
    { testKind: "vacBans" }
  ),
  tk_ban_on_connect_config: schemaProfile(
    "tkBans",
    [
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
    ["detection", "actions", "exemptions", "notifications"],
    { operationMode: "toggle", testKind: "tkBans" }
  ),
  name_kick_config: nameKickProfile,
  seed_vip_config: {
    ...schemaProfile(
      "seedVip",
      [
        ["operation", ["language", "poll_time_seeding", "poll_time_seeded"]],
        ["requirements", ["requirements", "player_announce_thresholds"]],
        ["reward", ["reward", "nice_time_delta", "nice_expiration_date"]],
        ["messages", ["player_messages"]],
        ["notifications", ["hooks"]],
      ],
      ["requirements", "reward", "messages", "notifications"],
      { operationMode: "threeState" }
    ),
    renderer: "seedVip",
  },
  expired_vip_config: schemaProfile(
    "expiredVip",
    [
      ["schedule", ["interval_minutes"]],
      ["notifications", ["discord_webhook_url"]],
    ],
    ["schedule", "notifications"],
    { operationMode: "toggle" }
  ),
};

const sectionOrder = [
  "operation",
  "intervention",
  "squads",
  "safety",
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
    .map((id) => genericSection(null, id, groups.get(id)));
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
  const shellFields = new Set(
    profile.operationMode === "threeState"
      ? ["enabled", "dry_run"]
      : profile.operationMode === "toggle"
      ? ["enabled"]
      : []
  );
  const remaining = [...available].filter(
    (name) => !known.has(name) && !shellFields.has(name)
  );
  if (remaining.length)
    sections.push(genericSection(profile.page || null, "advanced", remaining));
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
