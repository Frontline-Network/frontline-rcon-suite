export const noLeaderConfig = {
  enabled: true,
  dry_run: true,
  discord_webhook_url: null,
  whitelist_flags: [],
  immune_roles: [],
  immune_player_level: 1,
  dont_do_anything_below_this_number_of_players: 40,
  number_of_notes: 1,
  notes_interval_seconds: 10,
  number_of_warnings: 2,
  warning_interval_seconds: 60,
  warning_message:
    "{player_name}, euer Trupp „{squad_name}“ hat keinen Truppführer.\nBitte bestimmt einen Truppführer, sonst folgt eine Bestrafung.",
  number_of_punishments: 5,
  min_squad_players_for_punish: 1,
  min_server_players_for_punish: 40,
  punish_interval_seconds: 60,
  punish_message:
    "Dein Trupp {squad_name} benötigt weiterhin einen Truppführer. Bestrafung {received_punishes}/{max_punishes}.",
  kick_after_max_punish: true,
  min_squad_players_for_kick: 1,
  min_server_players_for_kick: 60,
  kick_grace_period_seconds: 120,
  kick_message:
    "Dein Trupp {squad_name} hatte weiterhin keinen Truppführer. Die letzte Frist von {kick_grace_period} Sekunden ist abgelaufen.",
};

const integer = (title, minimum = 0, maximum) => ({
  type: "integer",
  title,
  minimum,
  ...(maximum === undefined ? {} : { maximum }),
});

export const noLeaderSchema = {
  type: "object",
  properties: {
    enabled: { type: "boolean", title: "Enable" },
    dry_run: { type: "boolean", title: "Dry-Run" },
    discord_webhook_url: {
      anyOf: [{ type: "string", format: "uri" }, { type: "null" }],
      title: "Discord Webhook URL",
    },
    whitelist_flags: {
      type: "array",
      title: "Whitelist Flags",
      items: { type: "string" },
    },
    immune_roles: {
      type: "array",
      title: "Immune Roles",
      items: {
        type: "string",
        enum: [
          "armycommander",
          "officer",
          "rifleman",
          "assault",
          "automaticrifleman",
          "medic",
          "support",
          "heavymachinegunner",
          "antitank",
          "engineer",
          "tankcommander",
          "crewman",
          "spotter",
          "sniper",
          "artilleryobserver",
          "operator",
          "gunner",
        ],
      },
    },
    immune_player_level: integer("Minimum Level", 0, 500),
    dont_do_anything_below_this_number_of_players: integer(
      "Minimum Players",
      0,
      100
    ),
    number_of_notes: integer("Number of notes"),
    notes_interval_seconds: integer("Notes interval", 1),
    number_of_warnings: integer("Number of warnings", -1),
    warning_interval_seconds: integer("Warning interval"),
    warning_message: { type: "string", title: "Warning message" },
    number_of_punishments: integer("Number of punishes", -1),
    min_squad_players_for_punish: integer(
      "Punishment minimum squad players",
      0,
      6
    ),
    min_server_players_for_punish: integer(
      "Punishment minimum server players",
      0,
      100
    ),
    punish_interval_seconds: integer("Punish interval"),
    punish_message: { type: "string", title: "Punish message" },
    kick_after_max_punish: { type: "boolean", title: "Enable Kick" },
    min_squad_players_for_kick: integer("Kick minimum squad players", 0, 6),
    min_server_players_for_kick: integer("Kick minimum server players", 0, 100),
    kick_grace_period_seconds: integer("Kick Grace Period"),
    kick_message: { type: "string", title: "Kick message" },
  },
  required: Object.keys(noLeaderConfig).filter(
    (field) => field !== "discord_webhook_url"
  ),
};
