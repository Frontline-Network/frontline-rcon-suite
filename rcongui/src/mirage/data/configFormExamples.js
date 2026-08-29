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
  min_squad_players_for_punish: 0,
  min_server_players_for_punish: 0,
  punish_interval_seconds: 60,
  punish_message: "Regelverstoß nach vorheriger Warnung.",
  kick_after_max_punish: true,
  min_squad_players_for_kick: 0,
  min_server_players_for_kick: 0,
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
  min_squad_players_for_punish: integer("Mindestgröße des Trupps"),
  min_server_players_for_punish: integer(
    "Mindestanzahl Spieler für Bestrafungen"
  ),
  punish_interval_seconds: integer("Abstand zwischen Bestrafungen"),
  punish_message: text("Bestrafungsnachricht"),
  kick_after_max_punish: boolean("Nach den Bestrafungen kicken"),
  min_squad_players_for_kick: integer("Mindestgröße des Trupps für Kicks"),
  min_server_players_for_kick: integer("Mindestanzahl Spieler für Kicks"),
  kick_grace_period_seconds: integer("Letzte Frist vor dem Kick"),
  kick_message: text("Kick-Nachricht"),
  discord_webhook_url: text("Discord-Webhook-URL", "uri"),
};

const examples = {
  audit_discord_webhooks_config: {
    data: {
      hooks: [{ url: "https://discord.com/api/webhooks/123456/demo-token" }],
    },
    schema: schema({
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({ url: text("Webhook-URL", "uri") }),
      },
    }),
  },
  admin_pings_discord_webhooks_config: {
    data: {
      trigger_words: ["!admin", "admin bitte"],
      hooks: [
        {
          url: "https://discord.com/api/webhooks/123456/demo-token",
          user_mentions: ["<@123456789>"],
          role_mentions: ["<@&987654321>"],
        },
      ],
    },
    schema: schema({
      trigger_words: strings("Auslösewörter"),
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({
          url: text("Webhook-URL", "uri"),
          user_mentions: strings("Benutzer erwähnen"),
          role_mentions: strings("Rollen erwähnen"),
        }),
      },
    }),
  },
  watchlist_discord_webhooks_config: {
    data: {
      hooks: [
        {
          url: "https://discord.com/api/webhooks/123456/demo-token",
          user_mentions: [],
          role_mentions: ["<@&987654321>"],
        },
      ],
    },
    schema: schema({
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({
          url: text("Webhook-URL", "uri"),
          user_mentions: strings("Benutzer erwähnen"),
          role_mentions: strings("Rollen erwähnen"),
        }),
      },
    }),
  },
  camera_discord_webhooks_config: {
    data: {
      hooks: [
        {
          url: "https://discord.com/api/webhooks/123456/demo-token",
          user_mentions: [],
          role_mentions: ["<@&987654321>"],
        },
      ],
    },
    schema: schema({
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({
          url: text("Webhook-URL", "uri"),
          user_mentions: strings("Benutzer erwähnen"),
          role_mentions: strings("Rollen erwähnen"),
        }),
      },
    }),
  },
  chat_discord_webhooks_config: {
    data: {
      allow_mentions: false,
      hooks: [{ url: "https://discord.com/api/webhooks/123456/demo-token" }],
    },
    schema: schema({
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({ url: text("Webhook-URL", "uri") }),
      },
      allow_mentions: boolean("Erwähnungen aus dem Chat erlauben"),
    }),
  },
  kills_discord_webhooks_config: {
    data: {
      send_kills: true,
      send_team_kills: true,
      hooks: [{ url: "https://discord.com/api/webhooks/123456/demo-token" }],
    },
    schema: schema({
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({ url: text("Webhook-URL", "uri") }),
      },
      send_kills: boolean("Kills senden"),
      send_team_kills: boolean("Teamkills senden"),
    }),
  },
  log_line_webhook_config: {
    data: {
      webhooks: [
        {
          log_types: ["CHAT", "KILL", "TEAM KILL"],
          webhook: {
            url: "https://discord.com/api/webhooks/123456/demo-token",
            user_mentions: [],
            role_mentions: ["<@&987654321>"],
          },
        },
      ],
    },
    schema: schema({
      webhooks: {
        type: "array",
        title: "Log-Webhooks",
        items: schema({
          log_types: {
            type: "array",
            title: "Ereignistypen",
            items: {
              type: "string",
              enum: ["CHAT", "KILL", "TEAM KILL", "CONNECTED", "DISCONNECTED"],
            },
          },
          webhook: schema({
            url: text("Webhook-URL", "uri"),
            user_mentions: strings("Benutzer erwähnen"),
            role_mentions: strings("Rollen erwähnen"),
          }),
        }),
      },
    }),
  },
  scoreboard_config: {
    data: {
      public_scoreboard_url: "https://stats.example/frontline",
      hooks: [{ url: "https://discord.com/api/webhooks/123456/demo-token" }],
      header_gamestate_enabled: true,
      map_rotation_enabled: true,
      player_stats_enabled: true,
      footer_last_refreshed_text: "Zuletzt aktualisiert",
      header_gamestate_include_server_name: true,
      header_gamestate_time_between_refreshes: 5,
      quick_connect_url: "steam://connect/127.0.0.1:7777",
      battlemetrics_url: "https://www.battlemetrics.com/servers/hll/123456",
      show_map_image: true,
      map_rotation_include_server_name: true,
      map_rotation_time_between_refreshes: 30,
      current_map_format: "🟩 {1}. **{0}**",
      next_map_format: "🟨 {1}. {0}",
      other_map_format: "⬛ {1}. {0}",
      show_map_legend: true,
      map_rotation_title_text: "Kartenrotation",
      player_stats_include_server_name: true,
      player_stats_title_text: "Spielerstatistiken",
      player_stats_time_between_refreshes: 5,
      player_stats_num_to_display: 5,
    },
    schema: schema({
      public_scoreboard_url: text("Öffentliche Scoreboard-URL", "uri"),
      hooks: {
        type: "array",
        title: "Discord-Webhooks",
        items: schema({ url: text("Webhook-URL", "uri") }),
      },
      header_gamestate_enabled: boolean("Kopfbereich aktiv"),
      map_rotation_enabled: boolean("Kartenrotation aktiv"),
      player_stats_enabled: boolean("Spielerstatistiken aktiv"),
      footer_last_refreshed_text: text("Fußzeile"),
      header_gamestate_include_server_name: boolean("Servername anzeigen"),
      header_gamestate_time_between_refreshes: integer("Aktualisierung"),
      quick_connect_url: text("Direktverbindungs-URL", "uri"),
      battlemetrics_url: text("BattleMetrics-URL", "uri"),
      show_map_image: boolean("Kartenbild anzeigen"),
      map_rotation_include_server_name: boolean("Servername anzeigen"),
      map_rotation_time_between_refreshes: integer("Aktualisierung"),
      current_map_format: text("Aktuelle Karte"),
      next_map_format: text("Nächste Karte"),
      other_map_format: text("Weitere Karten"),
      show_map_legend: boolean("Kartenlegende anzeigen"),
      map_rotation_title_text: text("Titel"),
      player_stats_include_server_name: boolean("Servername anzeigen"),
      player_stats_title_text: text("Titel"),
      player_stats_time_between_refreshes: integer("Aktualisierung"),
      player_stats_num_to_display: integer("Spieler je Statistik", 1),
    }),
  },
  chat_commands_config: {
    data: {
      enabled: true,
      describe_words: ["!help", "@help"],
      command_words: [
        {
          words: ["!rules"],
          description: "Zeigt die wichtigsten Serverregeln.",
          message: "Bitte beachte unsere Serverregeln unter fln.gg/rules.",
        },
      ],
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      describe_words: strings("Hilfe-Befehle"),
      command_words: {
        type: "array",
        title: "Konfigurierte Befehle",
        items: schema({
          words: strings("Befehlswörter"),
          description: text("Beschreibung"),
          message: text("Antwortnachricht"),
        }),
      },
    }),
  },
  rcon_chat_commands_config: {
    data: {
      enabled: true,
      describe_words: ["!help"],
      command_words: [
        {
          words: ["!redeploy"],
          enabled: true,
          description: "Löst einen schnelleren Redeploy aus.",
          commands: {
            punish: {
              player_name: "{player_name}",
              reason: "Redeploy per Chatbefehl",
            },
          },
          conditions: { player_count: { min: 0, max: 49 } },
        },
      ],
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      describe_words: strings("Hilfe-Befehle"),
      command_words: {
        type: "array",
        title: "RCON-Chatbefehle",
        items: schema({
          words: strings("Befehlswörter"),
          enabled: boolean("Befehl aktiv"),
          description: text("Beschreibung"),
          commands: {
            type: "object",
            title: "RCON-Befehle",
            additionalProperties: true,
          },
          conditions: {
            type: "object",
            title: "Bedingungen",
            additionalProperties: true,
          },
        }),
      },
    }),
  },
  server_name_change_config: {
    data: { ip: "127.0.0.1", port: 10011 },
    schema: schema({
      ip: text("Server-IP"),
      port: integer("Query-Port", 1),
    }),
  },
  auto_mod_level_config: {
    data: {
      ...commonAutomodData,
      enabled: false,
      min_level: 25,
      max_level: 500,
      level_thresholds: {
        armycommander: {
          label: "Commander",
          min_players: 40,
          min_level: 100,
        },
      },
      levelbug_enabled: true,
      announcement_enabled: true,
      only_announce_impacted_players: true,
      announcement_message:
        "Auf diesem Server gelten rollenabhängige Mindestlevel.",
      min_level_message: "Zugang erst ab Level {level}.",
      max_level_message: "Zugang nur bis Level {level}.",
      violation_message: "{role} ist erst ab Level {level} erlaubt.",
      force_kick_message: "Du erfüllst die Levelanforderung nicht.",
    },
    schema: schema({
      ...commonAutomodProperties,
      levelbug_enabled: boolean("Level-Fehler berücksichtigen"),
      min_level: integer("Mindestlevel"),
      max_level: integer("Höchstlevel"),
      level_thresholds: {
        type: "object",
        title: "Levelgrenzen je Rolle",
        additionalProperties: schema({
          label: text("Anzeigename"),
          min_players: integer("Gilt ab Spielerzahl"),
          min_level: integer("Mindestlevel"),
        }),
      },
      min_level_message: text("Nachricht bei zu niedrigem Level"),
      max_level_message: text("Nachricht bei zu hohem Level"),
      violation_message: text("Nachricht bei Rollenverstoß"),
      force_kick_message: text("Kick-Nachricht für Serverlevel"),
      announcement_enabled: boolean("Ankündigung aktivieren"),
      only_announce_impacted_players: boolean(
        "Nur betroffene Spieler informieren"
      ),
      announcement_message: text("Ankündigung"),
    }),
  },
  auto_mod_seeding_config: {
    data: {
      ...commonAutomodData,
      immune_roles: ["armycommander"],
      immune_player_level: 25,
      min_squad_players_for_punish: 0,
      min_server_players_for_punish: 0,
      min_squad_players_for_kick: 0,
      min_server_players_for_kick: 0,
      disallowed_roles: {
        min_players: 1,
        max_players: 40,
        roles: {
          tankcommander: "Panzerkommandant",
          crewman: "Panzerbesatzung",
        },
        violation_message: "{role} ist während des Seedings nicht erlaubt.",
      },
      disallowed_weapons: {
        min_players: 1,
        max_players: 40,
        weapons: { "155MM HOWITZER [M114]": "Artillerie" },
        violation_message: "{weapon} ist während des Seedings nicht erlaubt.",
      },
      enforce_cap_fight: {
        min_players: 1,
        max_players: 50,
        max_caps: 3,
        skip_warning: true,
        violation_message:
          "Während des Seedings darf nur um den mittleren Punkt gekämpft werden.",
      },
      announcement_enabled: true,
      announcement_message:
        "Bis 20 gegen 20 wird nur um den mittleren Punkt gekämpft.",
    },
    schema: schema({
      ...commonAutomodProperties,
      immune_roles: strings("Ausgenommene Rollen"),
      immune_player_level: integer("Ausnahme bis Spielerlevel"),
      min_squad_players_for_punish: integer(
        "Mindestgröße des Trupps für Bestrafungen"
      ),
      min_server_players_for_punish: integer(
        "Mindestanzahl Spieler für Bestrafungen"
      ),
      min_squad_players_for_kick: integer("Mindestgröße des Trupps für Kicks"),
      min_server_players_for_kick: integer("Mindestanzahl Spieler für Kicks"),
      disallowed_roles: schema({
        min_players: integer("Mindestanzahl Spieler"),
        max_players: integer("Höchstanzahl Spieler"),
        roles: {
          type: "object",
          title: "Gesperrte Rollen",
          additionalProperties: { type: "string" },
        },
        violation_message: text("Hinweis bei Rollenverstoß"),
      }),
      disallowed_weapons: schema({
        min_players: integer("Mindestanzahl Spieler"),
        max_players: integer("Höchstanzahl Spieler"),
        weapons: {
          type: "object",
          title: "Gesperrte Waffen",
          additionalProperties: { type: "string" },
        },
        violation_message: text("Hinweis bei Waffenverstoß"),
      }),
      enforce_cap_fight: schema({
        min_players: integer("Mindestanzahl Spieler"),
        max_players: integer("Höchstanzahl Spieler"),
        max_caps: integer("Maximal gehaltene Sektoren", 2),
        skip_warning: boolean("Warnung überspringen"),
        violation_message: text("Hinweis bei Sektorverstoß"),
      }),
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
      whitelist_players: {
        has_flag: ["admin"],
        is_vip: true,
        has_at_least_n_sessions: 10,
      },
      message: "Frühe Teamkills nach dem Beitritt führen zu einer Sperre.",
      author_name: "Frontline Moderation",
      blacklist_id: 1,
      ban_duration: { minutes: 0, hours: 24, days: 0, weeks: 0, years: 0 },
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
        has_flag: strings("Ausgenommene Markierungen"),
        is_vip: boolean("VIPs ausnehmen"),
        has_at_least_n_sessions: integer("Ab dieser Sitzungszahl ausnehmen"),
      }),
      message: text("Spielernachricht"),
      author_name: text("Autor"),
      blacklist_id: integer("Sperrlisten-ID"),
      ban_duration: schema({
        minutes: integer("Minuten"),
        hours: integer("Stunden"),
        days: integer("Tage"),
        weeks: integer("Wochen"),
        years: integer("Jahre"),
      }),
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
      requirements: {
        buffer: { seconds: 0, minutes: 10, hours: 0 },
        min_allies: 10,
        min_axis: 10,
        max_allies: 25,
        max_axis: 25,
        online_when_seeded: true,
        minimum_play_time: { seconds: 0, minutes: 45, hours: 0 },
      },
      player_announce_thresholds: [10, 15, 20],
      reward: {
        forward: false,
        player_name_format_not_current_vip: "{player_name} - CRCON Seed VIP",
        cumulative: true,
        timeframe: { minutes: 0, hours: 0, days: 7, weeks: 0 },
      },
      nice_time_delta: true,
      nice_expiration_date: true,
      player_messages: {
        seeding_in_progress_message:
          "Server has reached {player_count} players",
        seeding_complete_message: "Server is live!",
        player_count_message: "{num_allied_players} - {num_axis_players}",
        reward_player_message:
          "Danke fürs Seeden. Du erhältst {vip_reward} VIP bis {vip_expiration}.",
        reward_player_message_no_vip:
          "Danke fürs Seeden. Der Server ist jetzt live.",
      },
      hooks: [{ url: "https://discord.example/frontline" }],
    },
    schema: schema({
      enabled: boolean("Aktiviert"),
      dry_run: boolean("Testbetrieb"),
      language: text("Sprache"),
      poll_time_seeding: integer("Prüfintervall beim Seeding"),
      poll_time_seeded: integer("Prüfintervall nach Seeding"),
      requirements: schema({
        buffer: schema({
          seconds: integer("Sekunden"),
          minutes: integer("Minuten"),
          hours: integer("Stunden"),
        }),
        min_allies: integer("Mindestens Alliierte"),
        min_axis: integer("Mindestens Achsenmächte"),
        max_allies: integer("Höchstens Alliierte"),
        max_axis: integer("Höchstens Achsenmächte"),
        online_when_seeded: boolean("Spieler muss beim Abschluss online sein"),
        minimum_play_time: schema({
          seconds: integer("Sekunden"),
          minutes: integer("Minuten"),
          hours: integer("Stunden"),
        }),
      }),
      player_announce_thresholds: {
        type: "array",
        title: "Spieler-Schwellen für Ankündigungen",
        items: { type: "integer" },
      },
      reward: schema({
        forward: boolean("Laufzeit ab heute berechnen"),
        player_name_format_not_current_vip: text(
          "Name für einen neuen VIP-Eintrag"
        ),
        cumulative: boolean("Belohnungen addieren"),
        timeframe: schema({
          minutes: integer("Minuten"),
          hours: integer("Stunden"),
          days: integer("Tage"),
          weeks: integer("Wochen"),
        }),
      }),
      nice_time_delta: boolean("Laufzeit lesbar formatieren"),
      nice_expiration_date: boolean("Ablaufdatum lesbar formatieren"),
      player_messages: schema({
        seeding_in_progress_message: text("Seeding läuft"),
        seeding_complete_message: text("Seeding abgeschlossen"),
        player_count_message: text("Spielerzahl"),
        reward_player_message: text("Belohnungsnachricht"),
        reward_player_message_no_vip: text("Nachricht ohne Belohnung"),
      }),
      hooks: {
        type: "array",
        title: "Benachrichtigungs-Webhooks",
        items: schema({ url: text("Webhook-URL", "uri") }),
      },
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
