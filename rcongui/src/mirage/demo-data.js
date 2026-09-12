const now = Date.now();

export const demoMapLayers = [
  {
    id: "foy_warfare_night",
    name: "foy_warfare_night",
    pretty_name: "Foy · Warfare · Nacht",
    game_mode: "warfare",
    environment: "night",
    image_name: "foy-night.webp",
    attackers: null,
    map: {
      name: "foy",
      pretty_name: "Foy",
      orientation: "vertical",
      allies: { name: "us", team: "Alliierte" },
      axis: { name: "ger", team: "Achsenmächte" },
    },
  },
  {
    id: "carentan_warfare",
    name: "carentan_warfare",
    pretty_name: "Carentan · Warfare",
    game_mode: "warfare",
    environment: "day",
    image_name: "carentan-day.webp",
    attackers: null,
    map: {
      name: "carentan",
      pretty_name: "Carentan",
      orientation: "horizontal",
      allies: { name: "us", team: "Alliierte" },
      axis: { name: "ger", team: "Achsenmächte" },
    },
  },
  {
    id: "kursk_offensive_ger",
    name: "kursk_offensive_ger",
    pretty_name: "Kursk · Offensive · Deutschland",
    game_mode: "offensive",
    environment: "day",
    image_name: "kursk-day.webp",
    attackers: "ger",
    map: {
      name: "kursk",
      pretty_name: "Kursk",
      orientation: "horizontal",
      allies: { name: "rus", team: "Alliierte" },
      axis: { name: "ger", team: "Achsenmächte" },
    },
  },
];

const demoVietnamMapDefinitions = [
  ["a", "WDEV_A", "Vạn Tường", "horizontal"],
  ["b", "WDEV_B", "Quảng Ngãi", "horizontal"],
  ["c", "WDEV_C", "Huế Outskirts", "vertical"],
  ["d", "WDEV_D", "Đăk Tô Airfield", "horizontal"],
  ["e", "WDEV_E", "Cam Ranh Port", "horizontal"],
  ["f", "WDEV_F", "Thanh Hòa Bridge", "vertical"],
];

export const demoVietnamMapLayers = demoVietnamMapDefinitions.map(
  ([suffix, mapId, prettyName, orientation]) => ({
    id: `wdev${suffix}_warfare_day`,
    name: `wdev${suffix}_warfare_day`,
    pretty_name: `${prettyName} · Warfare`,
    game_mode: "warfare",
    environment: "day",
    attackers: null,
    image_name: `wdev_${suffix}-day.webp`,
    map: {
      id: mapId,
      name: prettyName.toUpperCase(),
      pretty_name: prettyName,
      shortname: prettyName,
      attackers: null,
      allies: { name: "us", team: "Alliierte" },
      axis: { name: "nva", team: "Achsenmächte" },
      orientation,
    },
  })
);

const baseDemoNames = [
  "FLN_Raven",
  "FLN_Wolf",
  "FLN_Valkyrie",
  "FLN_Hawkeye",
  "FLN_Falcon",
  "FLN_Bravo",
];
const simulatedAlliesNames = Array.from(
  { length: 46 },
  (_, index) => `Demo_Allies_${String(index + 1).padStart(2, "0")}`
);
const simulatedAxisNames = Array.from(
  { length: 46 },
  (_, index) => `Demo_Axis_${String(index + 1).padStart(2, "0")}`
);
const demoNames = [
  ...baseDemoNames,
  ...simulatedAlliesNames,
  ...simulatedAxisNames,
  "FLN_Raven_VN",
];
const demoClassicPlayerId = "76561198000000001";
const demoVietnamPlayerId = "f0a11e0d000000000000000000000001";
const demoVietnamPlayerIndex = demoNames.length - 1;
const demoPlayerId = (index) => `76561198${String(index + 1).padStart(9, "0")}`;

export const demoPlayerRecords = demoNames.map((name, index) => ({
  id: index + 1,
  player_id:
    index === demoVietnamPlayerIndex
      ? demoVietnamPlayerId
      : `7656119800000000${index + 1}`,
  steam_id: index === demoVietnamPlayerIndex ? demoClassicPlayerId : undefined,
  game: index === demoVietnamPlayerIndex ? "hll_vietnam" : "hll",
  names: [
    {
      name,
      created: new Date(now - (index + 20) * 86400000).toISOString(),
      last_seen: new Date(now - index * 1800000).toISOString(),
    },
  ],
  soldier: { name, level: 80 + index * 17, clan_tag: "FLN", platform: "steam" },
  account: { name, country: index % 2 ? "AT" : "DE" },
  country: index % 2 ? "AT" : "DE",
  first_seen_timestamp_ms: now - (index + 20) * 86400000,
  last_seen_timestamp_ms: now - index * 1800000,
  created: new Date(now - (index + 20) * 86400000).toISOString(),
  total_playtime_seconds: 28800 + index * 3600,
  current_playtime_seconds: 300 + (index % 18) * 240,
  penalty_count: { PUNISH: index, KICK: index % 2, TEMPBAN: 0, PERMABAN: 0 },
  flags:
    index === 2
      ? [
          {
            id: 1,
            flag: "Teamplay",
            comment: "Verlässlich",
            modified: new Date(now - 7200000).toISOString(),
          },
        ]
      : [],
  received_actions:
    index % 2
      ? [
          {
            action_type: "KICK",
            reason: "Regelhinweis",
            by: "Frontline Admin",
            time: new Date(now - index * 86400000).toISOString(),
          },
        ]
      : [
          {
            action_type: "PUNISH",
            reason: "Teamkill",
            by: "Leitstelle",
            time: new Date(now - (index + 1) * 7200000).toISOString(),
          },
        ],
  sessions: [
    {
      start: new Date(now - (index + 2) * 7200000).toISOString(),
      end: new Date(now - (index + 2) * 7200000 + 5400000).toISOString(),
    },
    { start: new Date(now - (index + 5) * 86400000).toISOString(), end: null },
  ],
  comments: [
    {
      content: "Demo-Notiz für die Moderation.",
      by: "Frontline Admin",
      creation_time: new Date(now - (index + 1) * 3600000).toISOString(),
    },
  ],
  identity: {
    linked_accounts:
      index === 0
        ? [
            {
              player_id: demoVietnamPlayerId,
              steam_id: demoClassicPlayerId,
              name: "FLN_Raven_VN",
              game: "hll_vietnam",
              active_blacklists: [],
              existing_blacklists: [],
            },
          ]
        : index === demoVietnamPlayerIndex
        ? [
            {
              player_id: demoClassicPlayerId,
              steam_id: null,
              name: "FLN_Raven",
              game: "hll",
              active_blacklists: [],
              existing_blacklists: [],
            },
          ]
        : [],
  },
  sessions_count: 4 + index,
  watchlist:
    index === 2 ? { is_watched: true, reason: "Beobachtung", count: 1 } : null,
  vips:
    index === 0
      ? [
          {
            server_number: 2,
            expiration: new Date(now + 86400000 * 30).toISOString(),
          },
        ]
      : [],
  blacklist: null,
  steaminfo: null,
}));

const demoLogTypes = [
  "MATCH START",
  "CONNECTED",
  "CHAT[Team]",
  "KILL",
  "TEAM KILL",
  "ADMIN KICKED",
  "CHAT[Unit]",
  "DISCONNECTED",
];
const demoWeapons = ["Karabiner 98k", "M1 Garand", "MP40", "StG 44"];
const demoChatMessages = [
  "Bereit für den Einsatz.",
  "Rechte Flanke sichern.",
  "Brauche Munition am Punkt.",
  "Feindlicher Panzer bei F6.",
];

export const demoHistoricalLogs = Array.from({ length: 36 }, (_, index) => {
  const type = demoLogTypes[index % demoLogTypes.length];
  // Historical demo activity intentionally cycles through the named players.
  // Otherwise the first player only receives the system-only match-start row
  // and their profile appears to have no logs at all.
  const playerIndex = index % baseDemoNames.length;
  const targetIndex = (index + 2) % baseDemoNames.length;
  const player1Name = demoNames[playerIndex];
  const player2Name = ["KILL", "TEAM KILL", "ADMIN KICKED"].includes(type)
    ? demoNames[targetIndex]
    : null;
  const weapon = ["KILL", "TEAM KILL"].includes(type)
    ? demoWeapons[index % demoWeapons.length]
    : null;
  const eventTime = new Date(now - index * 45000).toISOString();
  const chatMessage = demoChatMessages[index % demoChatMessages.length];
  const content = type.startsWith("CHAT")
    ? `${player1Name}: ${chatMessage}`
    : type === "CONNECTED"
    ? `${player1Name} ist dem Server beigetreten.`
    : type === "DISCONNECTED"
    ? `${player1Name} hat den Server verlassen.`
    : type === "MATCH START"
    ? "Runde gestartet · Foy · Warfare · Nacht"
    : type.startsWith("ADMIN")
    ? `Frontline Admin kickte ${player2Name}. Grund: Teamkill`
    : `${player1Name} hat ${player2Name} getötet (${weapon}, ${
        42 + index * 3
      } m)`;

  return {
    id: index + 1,
    type,
    event_time: eventTime,
    creation_time: eventTime,
    content,
    player1_id: type === "MATCH START" ? null : demoPlayerId(playerIndex),
    player1_name: type === "MATCH START" ? "SYSTEM" : player1Name,
    player2_id: player2Name ? demoPlayerId(targetIndex) : null,
    player2_name: player2Name,
    server: "2",
    weapon,
    raw: `[DEMO ${index + 1}] ${type} ${content}`,
  };
});

const demoAuditEntries = [
  {
    id: 1042,
    creation_time: new Date(now).toISOString(),
    username: "Frontline Admin",
    command: "message_player",
    command_arguments: JSON.stringify({
      player_name: "FLN_Raven",
      player_id: "76561198000000001",
      message: "Bitte beachte die Serverregeln.",
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1041,
    creation_time: new Date(now - 420000).toISOString(),
    username: "Leitstelle",
    command: "kick_player",
    command_arguments: JSON.stringify({
      player_name: "Гук в Шльопках",
      player_id: "76561198000000002",
      reason: "Namensfilter",
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1040,
    creation_time: new Date(now - 840000).toISOString(),
    username: "Frontline Admin",
    command: "temp_ban_player",
    command_arguments: JSON.stringify({
      player_name: "Wotan",
      player_id: "76561198000000003",
      duration: "2 hours",
      reason: "Wiederholter Regelverstoß",
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1039,
    creation_time: new Date(now - 1260000).toISOString(),
    username: "Leitstelle",
    command: "disband_squad_by_name",
    command_arguments: JSON.stringify({
      squad_name: "Able",
      team_name: "allies",
    }),
    command_result: JSON.stringify({ failed: true, error: "Squad not found" }),
  },
  {
    id: 1038,
    creation_time: new Date(now - 1680000).toISOString(),
    username: "Map Manager",
    command: "set_map",
    command_arguments: JSON.stringify({ map_name: "foy_warfare_night" }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1037,
    creation_time: new Date(now - 2100000).toISOString(),
    username: "Frontline Admin",
    command: "set_autobalance_threshold",
    command_arguments: JSON.stringify({ threshold: 2 }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1036,
    creation_time: new Date(now - 2520000).toISOString(),
    username: "Frontline Admin",
    command: "add_vip",
    command_arguments: JSON.stringify({
      player_name: "FLN_Valkyrie",
      player_id: "76561198000000004",
      duration: "30 days",
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1035,
    creation_time: new Date(now - 2940000).toISOString(),
    username: "Leitstelle",
    command: "set_welcome_message",
    command_arguments: JSON.stringify({
      message: "Willkommen auf Frontline #2",
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1034,
    creation_time: new Date(now - 3360000).toISOString(),
    username: "System Admin",
    command: "clear_cache",
    command_arguments: JSON.stringify({ scope: "players" }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1033,
    creation_time: new Date(now - 3780000).toISOString(),
    username: "Frontline Admin",
    command: "add_admin_roles",
    command_arguments: JSON.stringify({
      player_name: "FLN_Wolf",
      player_id: "76561198000000005",
      roles: ["moderator", "camera"],
    }),
    command_result: JSON.stringify({ failed: false }),
  },
  {
    id: 1032,
    creation_time: new Date(now - 4200000).toISOString(),
    username: "System Admin",
    command: "set_steam_config",
    command_arguments: JSON.stringify({ api_key: "demo-sensitive-token" }),
    command_result: JSON.stringify({
      failed: true,
      error: "Steam API unavailable",
    }),
  },
  {
    id: 1031,
    creation_time: new Date(now - 4620000).toISOString(),
    username: "Leitstelle",
    command: "restart_webserver",
    command_arguments: "",
    command_result: "",
  },
];

const demoAuditCommands = [
  "message_player",
  "punish_player",
  "kick_player",
  "set_next_map",
  "add_vip",
  "remove_vip",
  "set_autobalance_threshold",
  "toggle_service",
];

Array.from({ length: 24 }, (_, index) => {
  const command = demoAuditCommands[index % demoAuditCommands.length];
  const player = demoNames[index % demoNames.length];
  const failed = index % 9 === 7;
  demoAuditEntries.push({
    id: 1030 - index,
    creation_time: new Date(now - (index + 3) * 5400000).toISOString(),
    username: index % 3 === 0 ? "Leitstelle" : "Frontline Admin",
    command,
    command_arguments: JSON.stringify({
      player_name: player,
      player_id: `7656119800000000${(index % demoNames.length) + 1}`,
      reason: command.includes("kick") ? "Regelverstoß" : undefined,
      map_name: command.includes("map") ? "carentan_warfare" : undefined,
      service_name: command.includes("service") ? "worker" : undefined,
    }),
    command_result: JSON.stringify(
      failed ? { failed: true, error: "Demo action failed" } : { failed: false }
    ),
  });
});

export const demoAuditData = {
  audit_logs: demoAuditEntries,
  total_pages: 1,
  page: 1,
  page_size: 50,
  total_entries: demoAuditEntries.length,
};

export const demoScorePlayers = demoNames.map((name, index) => ({
  player_id: `7656119800000000${index + 1}`,
  player: name,
  team: index % 2 ? "axis" : "allies",
  role: index === 0 ? "officer" : "rifleman",
  unit: index % 2 ? "Baker" : "Able",
  level: 80 + index * 17,
  kills: 28 - index,
  deaths: 4 + index,
  combat: 540 - index * 8,
  offense: 310 - index * 4,
  defense: 280 - index * 3,
  support: 420 - index * 5,
  kills_streak: Math.max(1, 9 - index),
  time_seconds: 4200 - index * 40,
  kill_death_ratio: Number(((28 - index) / (4 + index)).toFixed(2)),
  kills_per_minute: Number(
    ((28 - index) / ((4200 - index * 40) / 60)).toFixed(2)
  ),
  teamkills: index % 3,
  teamkills_streak: index % 2,
  deaths_by_tk: index % 2,
  deaths_by_tk_streak: index % 2,
  steaminfo: { country: index % 2 ? "AT" : "DE" },
}));

export const demoGames = demoMapLayers.map((map, index) => ({
  id: `fln-demo-${index + 1}`,
  map,
  server_number: 2,
  result: { allied: index % 2 ? 2 : 3, axis: index % 2 ? 3 : 2 },
  start: new Date(now - (index + 1) * 7200000).toISOString(),
  end: new Date(now - (index + 1) * 7200000 + 5400000).toISOString(),
}));

export const demoServices = [
  {
    name: "rcon",
    statename: "RUNNING",
    start: 1775205000,
    stop: 0,
    now: 1775210400,
    info: "RCON-Verbindung zum Gameserver",
  },
  {
    name: "worker",
    statename: "RUNNING",
    start: 1775205000,
    stop: 0,
    now: 1775210400,
    info: "CRCON-Auftragsverarbeitung",
  },
  {
    name: "scheduler",
    statename: "RUNNING",
    start: 1775205000,
    stop: 0,
    now: 1775210400,
    info: "Zeitgesteuerte Automatisierungen",
  },
];

const livePlayer = (record, index, team, unitName, role = "rifleman") => ({
  name: record.names[0].name,
  player_id: record.player_id,
  country: record.country,
  profile: record,
  is_vip: record.vips.length > 0,
  unit_id: index + 1,
  unit_name: unitName,
  loadout: "standard issue",
  team,
  role,
  kills: Math.max(0, 14 - (index % 15)),
  deaths: 3 + (index % 12),
  team_kills: index % 11 === 0 ? 3 : index % 7 === 0 ? 1 : 0,
  combat: 160 + (index % 18) * 12,
  offense: 90 + (index % 16) * 8,
  defense: 80 + (index % 14) * 7,
  support: 100 + (index % 20) * 6,
  level: record.soldier.level,
});

const alliesPlayers = demoPlayerRecords
  .slice(0, 3)
  .map((record, index) =>
    livePlayer(
      record,
      index,
      "allies",
      "able",
      index === 0 ? "officer" : "rifleman"
    )
  );
const axisPlayers = demoPlayerRecords
  .slice(3, 6)
  .map((record, index) =>
    livePlayer(
      record,
      index,
      "axis",
      "baker",
      index === 0 ? "officer" : "rifleman"
    )
  );

export const demoTeamView = {
  fail_count: 0,
  allies: {
    commander: null,
    squads: {
      able: { type: "infantry", has_leader: true, players: alliesPlayers },
    },
    combat: 0,
    offense: 0,
    defense: 0,
    support: 0,
    kills: 0,
    deaths: 0,
    count: alliesPlayers.length,
  },
  axis: {
    commander: null,
    squads: {
      baker: { type: "infantry", has_leader: true, players: axisPlayers },
    },
    combat: 0,
    offense: 0,
    defense: 0,
    support: 0,
    kills: 0,
    deaths: 0,
    count: axisPlayers.length,
  },
  unassigned: {
    squads: {
      unassigned: { type: "infantry", has_leader: false, players: [] },
    },
    combat: 0,
    offense: 0,
    defense: 0,
    support: 0,
    kills: 0,
    deaths: 0,
    count: 0,
  },
};

export const demoGameState = {
  current_map: demoMapLayers[0],
  next_map: demoMapLayers[1],
  raw_time_remaining: "00:57:07",
  time_remaining: 3427,
  allied_score: 3,
  axis_score: 2,
  num_allied_players: 49,
  num_axis_players: 49,
};

export const demoServerConnection = {
  name: "[GER] Frontline Network | #2",
  short_name: "Frontline #2",
  server_number: 2,
  game: "hll",
  current_players: 98,
  max_players: 100,
  port: 4174,
};

const readDemoParameter = (name) => {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(name);
};

// Deterministic imbalance for checking compact-mode intervention controls.
const demoUnbalancedTeamView = {
  ...demoTeamView,
  allies: {
    ...demoTeamView.allies,
    count: 5,
    squads: {
      able: demoTeamView.allies.squads.able,
      charlie: {
        type: "infantry", has_leader: false,
        players: axisPlayers.slice(1).map((player) => ({
          ...player, team: "allies", unit_name: "charlie",
        })),
      },
    },
  },
  axis: {
    ...demoTeamView.axis,
    count: 1,
    squads: { baker: { ...demoTeamView.axis.squads.baker, players: axisPlayers.slice(0, 1) } },
  },
};

export const getDemoTeamView = () =>
  readDemoParameter("demo_balance") === "unbalanced" ? demoUnbalancedTeamView : demoTeamView;

export const getDemoConnectionMode = () =>
  readDemoParameter("demo_connection") || "online";

export const getDemoRole = () => readDemoParameter("demo_role") || "admin";

export const isDemoAuthenticated = () => {
  if (readDemoParameter("session_expired") === "1") return false;
  if (readDemoParameter("demo_auth") === "anonymous") return false;

  const returnTarget = readDemoParameter("from");
  if (!returnTarget || typeof window === "undefined") return true;

  try {
    const returnUrl = new URL(returnTarget, window.location.origin);
    return returnUrl.searchParams.get("demo_auth") !== "anonymous";
  } catch {
    return true;
  }
};

export const isDemoSessionExpired = () =>
  readDemoParameter("demo_auth") === "expired" &&
  readDemoParameter("session_expired") !== "1";

export const shouldFailDemoServerSettings = () =>
  readDemoParameter("demo_settings_error") === "1";

const normalizeDemoGame = (value, fallback = "hll") => {
  const game = String(value ?? "")
    .trim()
    .toLowerCase();
  if (!game) return fallback;
  if (game === "hll") return "hll";
  if (["hllv", "hll_vietnam", "vietnam"].includes(game)) return "hll_vietnam";
  return null;
};

export const getDemoServerConnection = () => ({
  ...demoServerConnection,
  game: normalizeDemoGame(readDemoParameter("demo_game")),
});

export const getDemoMapLayers = () =>
  getDemoServerConnection().game === "hll_vietnam"
    ? demoVietnamMapLayers
    : demoMapLayers;

export const getDemoGameState = () => {
  if (getDemoServerConnection().game !== "hll_vietnam") return demoGameState;

  return {
    ...demoGameState,
    current_map: demoVietnamMapLayers[4],
    next_map: demoVietnamMapLayers[3],
  };
};

export const getDemoServerList = () => {
  if (readDemoParameter("demo_multiserver") !== "1") return [];

  return [
    {
      name: "[GER] Frontline Network | Vietnam #3",
      short_name: "Frontline Vietnam #3",
      server_number: 3,
      game: normalizeDemoGame(
        readDemoParameter("demo_other_game"),
        "hll_vietnam"
      ),
      current_players: 72,
      max_players: 100,
      port: 4175,
      link:
        typeof window === "undefined"
          ? "http://localhost:4175"
          : window.location.origin,
    },
  ];
};

export const demoServerStatus = {
  ...demoServerConnection,
  queue_players: 4,
  version: "11.2.0",
};

export const getDemoServerStatus = () => ({
  ...demoServerStatus,
  game: getDemoServerConnection().game,
  supported_game_modes:
    getDemoServerConnection().game === "hll_vietnam"
      ? ["warfare", "offensive", "conquest", "domination"]
      : ["warfare", "offensive", "conquest", "skirmish", "phased", "majority"],
  game_capabilities:
    getDemoServerConnection().game === "hll_vietnam"
      ? {
          match_timer_modes: ["warfare", "offensive"],
          warmup_timer_modes: ["warfare"],
          sector_layout: { read: true, set: true, remove: false },
        }
      : {
          match_timer_modes: ["warfare", "offensive", "skirmish"],
          warmup_timer_modes: ["warfare", "skirmish"],
          sector_layout: { read: true, set: true, remove: false },
        },
});

const demoSystemUsageHistory = Array.from({ length: 12 }, (_, index) => ({
  sampled_at: new Date(now - (11 - index) * 15_000).toISOString(),
  cpu_percent: [11, 15, 17, 14, 19, 23, 21, 18, 16, 20, 17, 18][index],
  ram_percent: [42, 42, 43, 43, 44, 44, 45, 45, 45, 46, 46, 46][index],
  disk_percent: 62,
  status: "ok",
}));

export const demoSystemUsage = {
  schema_version: 2,
  sampled_at: new Date(now).toISOString(),
  generated_at: new Date(now).toISOString(),
  data_age_seconds: 0,
  cache_hit: false,
  poll_after_seconds: 15,
  status: "ok",
  warnings: [],
  cpu_usage: {
    available: true,
    percent: 18,
    used: 0.72,
    total: 4,
    unit: "cores",
    source: "cgroup_v2",
    severity: "ok",
  },
  ram_usage: {
    available: true,
    percent: 46,
    used: 3.68,
    total: 8,
    unit: "GiB",
    source: "cgroup_v2",
    severity: "ok",
  },
  disk_usage: {
    available: true,
    percent: 62,
    used: 62,
    total: 100,
    unit: "GiB",
    source: "filesystem",
    severity: "ok",
  },
  history: demoSystemUsageHistory,
  range: {
    from: demoSystemUsageHistory[0].sampled_at,
    to: new Date(now).toISOString(),
    seconds: 165,
    sample_interval_seconds: 15,
    max_samples: 61,
  },
};

export const getDemoSystemUsage = () => {
  const result = JSON.parse(JSON.stringify(demoSystemUsage));
  const mode = readDemoParameter("demo_resources") || "ok";

  if (mode === "warning") {
    result.status = "warning";
    result.ram_usage.percent = 86;
    result.ram_usage.used = 6.88;
    result.ram_usage.severity = "warning";
    result.warnings = [
      {
        metric: "ram",
        severity: "warning",
        code: "ram_warning",
        threshold_percent: 80,
      },
    ];
  }

  if (mode === "critical") {
    result.status = "critical";
    result.cpu_usage.percent = 92;
    result.cpu_usage.used = 3.68;
    result.cpu_usage.severity = "critical";
    result.warnings = [
      {
        metric: "cpu",
        severity: "critical",
        code: "cpu_critical",
        threshold_percent: 90,
      },
    ];
  }

  if (mode === "partial") {
    result.status = "partial";
    result.disk_usage = {
      available: false,
      percent: null,
      used: null,
      total: null,
      unit: "GiB",
      source: "unavailable",
      severity: "unknown",
    };
  }

  if (mode === "unavailable") {
    result.status = "unavailable";
    result.warnings = [];
    result.history = [];
    for (const key of ["cpu_usage", "ram_usage", "disk_usage"]) {
      result[key] = {
        available: false,
        percent: null,
        used: null,
        total: null,
        unit: key === "cpu_usage" ? "cores" : "GiB",
        source: "unavailable",
        severity: "unknown",
      };
    }
  }

  if (mode === "stale") {
    const sampledAt = new Date(now - 5 * 60_000).toISOString();
    result.sampled_at = sampledAt;
    result.data_age_seconds = 300;
    result.range.to = sampledAt;
  }

  return result;
};

export const demoServerSettings = {
  autobalance_enabled: true,
  votekick_enabled: true,
  team_switch_cooldown: 15,
  autobalance_threshold: 3,
  idle_autokick_time: 15,
  max_ping_autokick: 250,
  queue_length: 6,
  vip_slots_num: 2,
};

export const demoBlacklists = [
  { id: 1, name: "FLN Hauptsperrliste", servers: null, sync: "ban_on_connect" },
  { id: 2, name: "Event-Ausschlüsse", servers: [2], sync: "kick_only" },
];

export const demoBlacklistRecords = [
  {
    id: 106,
    blacklist: demoBlacklists[1],
    player: {
      player_id: "76561198000000026",
      names: [{ name: "Wotan" }, { name: "Odin32" }],
      steaminfo: null,
    },
    reason: "Mehrfaches Teamkilling und absichtliches Stören des Events",
    formatted_reason:
      "Mehrfaches Teamkilling und absichtliches Stören des Events",
    created_at: new Date(Date.now() - 35 * 60_000).toISOString(),
    expires_at: null,
    is_active: true,
    admin_name: "Frontline Admin",
  },
  {
    id: 105,
    blacklist: demoBlacklists[0],
    player: {
      player_id: "76561198000000025",
      names: [{ name: "Shadow" }],
      steaminfo: null,
    },
    reason: "Beleidigungen im Textchat",
    formatted_reason: "Beleidigungen im Textchat",
    created_at: new Date(Date.now() - 2 * 60 * 60_000).toISOString(),
    expires_at: new Date(Date.now() + 4 * 86400000).toISOString(),
    is_active: true,
    admin_name: "Frontline Admin",
  },
  {
    id: 104,
    blacklist: demoBlacklists[1],
    player: {
      player_id: "76561198000000024",
      names: [{ name: "DerJoker254" }],
      steaminfo: null,
    },
    reason: "Event-Ausschluss wegen wiederholter Regelverstöße",
    formatted_reason: "Event-Ausschluss wegen wiederholter Regelverstöße",
    created_at: new Date(Date.now() - 4 * 60 * 60_000).toISOString(),
    expires_at: new Date(Date.now() + 4 * 86400000).toISOString(),
    is_active: true,
    admin_name: "Leitstelle",
  },
  {
    id: 103,
    blacklist: demoBlacklists[0],
    player: {
      player_id: "76561198000000023",
      names: [{ name: "TommyGun" }],
      steaminfo: null,
    },
    reason: "Rassistische Äußerungen im Chat",
    formatted_reason: "Rassistische Äußerungen im Chat",
    created_at: new Date(Date.now() - 86400000 * 18).toISOString(),
    expires_at: new Date(Date.now() - 86400000 * 2).toISOString(),
    is_active: false,
    admin_name: "Frontline Admin",
  },
  {
    id: 101,
    blacklist: demoBlacklists[0],
    player: {
      player_id: "76561198000000021",
      names: [{ name: "FLN_Rulebreaker" }],
      steaminfo: null,
    },
    reason: "Wiederholte schwere Regelverstöße",
    formatted_reason: "Wiederholte schwere Regelverstöße",
    created_at: new Date(Date.now() - 86400000 * 12).toISOString(),
    expires_at: null,
    is_active: true,
    admin_name: "Frontline Admin",
  },
  {
    id: 102,
    blacklist: demoBlacklists[1],
    player: {
      player_id: "76561198000000022",
      names: [{ name: "FLN_EventBan" }, { name: "Old_EventBan" }],
      steaminfo: null,
    },
    reason: "Event-Ausschluss nach wiederholtem Teamkilling",
    formatted_reason: "Event-Ausschluss nach wiederholtem Teamkilling",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    expires_at: new Date(Date.now() + 86400000 * 4).toISOString(),
    is_active: true,
    admin_name: "Leitstelle",
  },
];

export const isFakeMode = () => import.meta.env.MODE === "fake";
