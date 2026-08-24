const boolean = (title) => ({ type: "boolean", title });
const integer = (title, minimum = 0) => ({ type: "integer", title, minimum });
const text = (title, format) => ({
  type: "string",
  title,
  ...(format ? { format } : {}),
});
const strings = (title) => ({
  type: "array",
  title,
  items: { type: "string" },
});
const schema = (properties) => ({ type: "object", properties });

const commonAutomodData = {
  enabled: true,
  dry_run: false,
  whitelist_flags: ["admin"],
  dont_do_anything_below_this_number_of_players: 20,
  number_of_warnings: 2,
  warning_interval_seconds: 60,
  warning_message: "{player_name}, bitte beachte die Serverregeln.",
  number_of_punishments: 1,
  punish_interval_seconds: 60,
  punish_message: "Regelverstoß nach vorheriger Warnung.",
  kick_after_max_punish: true,
  kick_grace_period_seconds: 120,
  kick_message: "Wiederholter Regelverstoß.",
  discord_webhook_url: "https://discord.example/frontline",
};

const commonAutomodProperties = {
  enabled: boolean("Aktiviert"),
  dry_run: boolean("Testbetrieb"),
  whitelist_flags: strings("Ausgenommene Markierungen"),
  dont_do_anything_below_this_number_of_players: integer(
    "Mindestanzahl Spieler"
  ),
  number_of_warnings: integer("Warnungen vor der Bestrafung", -1),
  warning_interval_seconds: integer("Abstand zwischen Warnungen"),
  warning_message: text("Warnnachricht"),
  number_of_punishments: integer("Anzahl Bestrafungen", -1),
  punish_interval_seconds: integer("Abstand zwischen Bestrafungen"),
  punish_message: text("Bestrafungsnachricht"),
  kick_after_max_punish: boolean("Nach den Bestrafungen kicken"),
  kick_grace_period_seconds: integer("Letzte Frist vor dem Kick"),
  kick_message: text("Kick-Nachricht"),
  discord_webhook_url: text("Discord-Webhook-URL", "uri"),
};

const examples = {
  auto_mod_level_config: {
    data: {
      ...commonAutomodData,
      enabled: false,
      min_level: 25,
      max_level: 500,
      levelbug_enabled: true,
      announcement_enabled: true,
      announcement_message:
        "Auf diesem Server gelten rollenabhängige Mindestlevel.",
    },
    schema: schema({
      ...commonAutomodProperties,
      levelbug_enabled: boolean("Level-Fehler berücksichtigen"),
      min_level: integer("Mindestlevel"),
      max_level: integer("Höchstlevel"),
      announcement_enabled: boolean("Ankündigung aktivieren"),
      announcement_message: text("Ankündigung"),
    }),
  },
  auto_mod_seeding_config: {
    data: {
      ...commonAutomodData,
      immune_roles: ["commander"],
      immune_player_level: 25,
      disallowed_roles: ["armor", "artillery"],
      disallowed_weapons: ["Artillery"],
      enforce_cap_fight: true,
      announcement_enabled: true,
      announcement_message:
        "Bis 20 gegen 20 wird nur um den mittleren Punkt gekämpft.",
    },
    schema: schema({
      ...commonAutomodProperties,
      immune_roles: strings("Ausgenommene Rollen"),
      immune_player_level: integer("Ausnahme bis Spielerlevel"),
      disallowed_roles: strings("Während des Seedings gesperrte Rollen"),
      disallowed_weapons: strings("Während des Seedings gesperrte Waffen"),
      enforce_cap_fight: boolean("Kampf um den mittleren Punkt erzwingen"),
      announcement_enabled: boolean("Ankündigung aktivieren"),
      announcement_message: text("Seeding-Ankündigung"),
    }),
  },
  auto_mod_solo_tank_config: {
    data: {
      ...commonAutomodData,
      immune_player_level: 30,
      number_of_notes: 2,
      notes_interval_seconds: 45,
    },
    schema: schema({
      ...commonAutomodProperties,
      immune_player_level: integer("Ausnahme bis Spielerlevel"),
      number_of_notes: integer("Interne Bestätigungen"),
      notes_interval_seconds: integer("Abstand zwischen Bestätigungen"),
    }),
  },
  vac_game_bans_config: {
    data: {
      vac_history_days: 365,
      game_ban_threshhold: 2,
      blacklist_id: 1,
      ban_on_vac_history_reason: "Aktive oder junge VAC-/Spielsperre",
      auto_expire: true,
      whitelist_flags: ["trusted"],
    },
    schema: schema({
      vac_history_days: integer("VAC-Sperren innerhalb der letzten Tage"),
      game_ban_threshhold: integer("Schwellenwert für Spielsperren"),
      blacklist_id: integer("Sperrlisten-ID"),
      ban_on_vac_history_reason: text("Sperrgrund"),
      auto_expire: boolean("Sperre automatisch ablaufen lassen"),
      whitelist_flags: strings("Ausgenommene Markierungen"),
    }),
  },
  tk_ban_on_connect_config: {
    data: {
      enabled: true,
      max_time_after_connect_minutes: 15,
      ignore_tk_after_n_kills: 8,
      ignore_tk_after_n_deaths: 8,
      teamkill_tolerance_count: 2,
      excluded_weapons: ["Roadkill"],
      whitelist_players: { flags: ["admin"] },
      message: "Frühe Teamkills nach dem Beitritt führen zu einer Sperre.",
      author_name: "Frontline Moderation",
      blacklist_id: 1,
      ban_duration: { hours: 24 },
      discord_webhook_url: "https://discord.example/frontline",
      discord_webhook_message: "Teamkill-Sperre für {player_name}",
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      max_time_after_connect_minutes: integer("Zeitfenster nach Beitritt"),
      ignore_tk_after_n_kills: integer(
        "Nach dieser Anzahl Kills nicht mehr prüfen"
      ),
      ignore_tk_after_n_deaths: integer(
        "Nach dieser Anzahl Tode nicht mehr prüfen"
      ),
      teamkill_tolerance_count: integer("Tolerierte Teamkills"),
      excluded_weapons: strings("Ausgenommene Waffen"),
      whitelist_players: schema({
        flags: strings("Ausgenommene Markierungen"),
      }),
      message: text("Spielernachricht"),
      author_name: text("Autor"),
      blacklist_id: integer("Sperrlisten-ID"),
      ban_duration: schema({ hours: integer("Sperrdauer in Stunden") }),
      discord_webhook_url: text("Discord-Webhook-URL", "uri"),
      discord_webhook_message: text("Discord-Nachricht"),
    }),
  },
  name_kick_config: {
    data: {
      regular_expressions: ["(?i)admin", "(?i)offensive-name"],
      whitelist_flags: ["admin"],
      kick_reason: "Dieser Spielername ist auf dem Server nicht erlaubt.",
      discord_webhook_url: "https://discord.example/frontline",
    },
    schema: schema({
      regular_expressions: strings("Reguläre Ausdrücke"),
      whitelist_flags: strings("Ausgenommene Markierungen"),
      kick_reason: text("Kick-Grund"),
      discord_webhook_url: text("Discord-Webhook-URL", "uri"),
    }),
  },
  seed_vip_config: {
    data: {
      enabled: true,
      dry_run: false,
      language: "de",
      poll_time_seeding: 60,
      poll_time_seeded: 300,
      requirements: { minimum_players: 20, minimum_minutes: 45 },
      player_announce_thresholds: [10, 15, 20],
      reward: { vip_days: 7, extend_existing: true },
      nice_time_delta: "7 Tage",
      nice_expiration_date: "Automatisch berechnet",
      player_messages: {
        progress: "Danke fürs Seeden – noch {minutes} Minuten.",
        rewarded: "Du hast 7 Tage VIP erhalten.",
      },
      hooks: { discord_webhook_url: "https://discord.example/frontline" },
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      dry_run: boolean("Testbetrieb"),
      language: text("Sprache"),
      poll_time_seeding: integer("Prüfintervall beim Seeding"),
      poll_time_seeded: integer("Prüfintervall nach Seeding"),
      requirements: schema({
        minimum_players: integer("Mindestanzahl Spieler"),
        minimum_minutes: integer("Erforderliche Spielzeit in Minuten"),
      }),
      player_announce_thresholds: {
        type: "array",
        title: "Spieler-Schwellen für Ankündigungen",
        items: { type: "integer" },
      },
      reward: schema({
        vip_days: integer("VIP-Dauer in Tagen"),
        extend_existing: boolean("Bestehendes VIP verlängern"),
      }),
      nice_time_delta: text("Angezeigte VIP-Dauer"),
      nice_expiration_date: text("Angezeigtes Ablaufdatum"),
      player_messages: schema({
        progress: text("Fortschrittsnachricht"),
        rewarded: text("Belohnungsnachricht"),
      }),
      hooks: schema({
        discord_webhook_url: text("Discord-Webhook-URL", "uri"),
      }),
    }),
  },
  expired_vip_config: {
    data: {
      enabled: true,
      interval_minutes: 15,
      discord_webhook_url: "https://discord.example/frontline",
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      interval_minutes: integer("Prüfintervall in Minuten", 1),
      discord_webhook_url: text("Discord-Webhook-URL", "uri"),
    }),
  },
};

export const getConfigFormExample = (command) => examples[command] || null;
