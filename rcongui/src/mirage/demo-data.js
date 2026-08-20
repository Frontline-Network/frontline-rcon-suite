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
    map: { name: "foy", pretty_name: "Foy", orientation: "vertical", allies: { name: "us", team: "Alliierte" }, axis: { name: "ger", team: "Achsenmächte" } },
  },
  {
    id: "carentan_warfare",
    name: "carentan_warfare",
    pretty_name: "Carentan · Warfare",
    game_mode: "warfare",
    environment: "day",
    image_name: "carentan-day.webp",
    attackers: null,
    map: { name: "carentan", pretty_name: "Carentan", orientation: "horizontal", allies: { name: "us", team: "Alliierte" }, axis: { name: "ger", team: "Achsenmächte" } },
  },
  {
    id: "kursk_offensive_ger",
    name: "kursk_offensive_ger",
    pretty_name: "Kursk · Offensive · Deutschland",
    game_mode: "offensive",
    environment: "day",
    image_name: "kursk-day.webp",
    attackers: "ger",
    map: { name: "kursk", pretty_name: "Kursk", orientation: "horizontal", allies: { name: "rus", team: "Alliierte" }, axis: { name: "ger", team: "Achsenmächte" } },
  },
];

const demoNames = ["FLN_Raven", "FLN_Wolf", "FLN_Valkyrie", "FLN_Hawkeye", "FLN_Falcon", "FLN_Bravo"];

export const demoPlayerRecords = demoNames.map((name, index) => ({
  id: index + 1,
  player_id: `7656119800000000${index + 1}`,
  names: [{ name, created: new Date(now - (index + 20) * 86400000).toISOString(), last_seen: new Date(now - index * 1800000).toISOString() }],
  soldier: { name, level: 80 + index * 17, clan_tag: "FLN", platform: "steam" },
  account: { name, country: index % 2 ? "AT" : "DE" },
  country: index % 2 ? "AT" : "DE",
  first_seen_timestamp_ms: now - (index + 20) * 86400000,
  last_seen_timestamp_ms: now - index * 1800000,
  created: new Date(now - (index + 20) * 86400000).toISOString(),
  total_playtime_seconds: 28800 + index * 3600,
  current_playtime_seconds: index < 3 ? 3600 : 0,
  penalty_count: { PUNISH: index, KICK: index % 2, TEMPBAN: 0, PERMABAN: 0 },
  flags: index === 2 ? [{ id: 1, flag: "Teamplay", comment: "Verlässlich", modified: new Date(now - 7200000).toISOString() }] : [],
  received_actions: index % 2
    ? [{ action_type: "KICK", reason: "Regelhinweis", by: "Frontline Admin", time: new Date(now - index * 86400000).toISOString() }]
    : [{ action_type: "PUNISH", reason: "Teamkill", by: "Leitstelle", time: new Date(now - (index + 1) * 7200000).toISOString() }],
  sessions: [
    { start: new Date(now - (index + 2) * 7200000).toISOString(), end: new Date(now - (index + 2) * 7200000 + 5400000).toISOString() },
    { start: new Date(now - (index + 5) * 86400000).toISOString(), end: null },
  ],
  comments: [{ content: "Demo-Notiz für die Moderation.", by: "Frontline Admin", creation_time: new Date(now - (index + 1) * 3600000).toISOString() }],
  sessions_count: 4 + index,
  watchlist: index === 2 ? { is_watched: true, reason: "Beobachtung", count: 1 } : null,
  vips: index === 0 ? [{ server_number: 2, expiration: new Date(now + 86400000 * 30).toISOString() }] : [],
  blacklist: null, steaminfo: null,
}));

export const demoHistoricalLogs = demoNames.map((name, index) => ({
  id: index + 1,
  type: index % 3 === 0 ? "CHAT[Team]" : index % 3 === 1 ? "KILL" : "CONNECTED",
  event_time: new Date(now - index * 90000).toISOString(),
  creation_time: new Date(now - index * 90000).toISOString(),
  content: index % 3 === 0 ? `${name}: Bereit für den Einsatz.` : name,
  player1_id: `7656119800000000${index + 1}`,
  player1_name: name,
  player2_id: null, player2_name: null, server: "2", raw: `[FLN] ${name}`,
}));

export const demoAuditData = {
  audit_logs: [
    { creation_time: new Date(now).toISOString(), username: "Frontline Admin", command: "message_player", command_arguments: JSON.stringify({ player_name: "FLN_Raven", player_id: "76561198000000001", message: "Bitte beachte die Serverregeln." }) },
    { creation_time: new Date(now - 3600000).toISOString(), username: "Leitstelle", command: "set_map", command_arguments: JSON.stringify({ map_name: "foy_warfare_night" }) },
  ],
  total_pages: 1, page: 1, page_size: 10, total_entries: 2,
};

export const demoScorePlayers = demoNames.map((name, index) => ({
  player_id: `7656119800000000${index + 1}`, player: name,
  team: index % 2 ? "axis" : "allies", role: index === 0 ? "officer" : "rifleman", unit: index % 2 ? "Baker" : "Able",
  level: 80 + index * 17, kills: 28 - index, deaths: 4 + index,
  combat: 540 - index * 8, offense: 310 - index * 4, defense: 280 - index * 3, support: 420 - index * 5,
  kills_streak: Math.max(1, 9 - index),
  time_seconds: 4200 - index * 40,
  kill_death_ratio: Number(((28 - index) / (4 + index)).toFixed(2)),
  kills_per_minute: Number(((28 - index) / ((4200 - index * 40) / 60)).toFixed(2)),
  teamkills: index % 3,
  teamkills_streak: index % 2,
  deaths_by_tk: index % 2,
  deaths_by_tk_streak: index % 2,
  steaminfo: { country: index % 2 ? "AT" : "DE" },
}));

export const demoGames = demoMapLayers.map((map, index) => ({
  id: `fln-demo-${index + 1}`, map,
  server_number: 2,
  result: { allied: index % 2 ? 2 : 3, axis: index % 2 ? 3 : 2 },
  start: new Date(now - (index + 1) * 7200000).toISOString(),
  end: new Date(now - (index + 1) * 7200000 + 5400000).toISOString(),
}));

export const demoServices = [
  { name: "rcon", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "RCON-Verbindung zum Gameserver" },
  { name: "worker", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "CRCON-Auftragsverarbeitung" },
  { name: "scheduler", statename: "RUNNING", start: 1775205000, stop: 0, now: 1775210400, info: "Zeitgesteuerte Automatisierungen" },
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
  kills: 14 - index,
  deaths: 3 + index,
  combat: 320 - index * 12,
  offense: 180 - index * 8,
  defense: 140 - index * 5,
  support: 220 - index * 7,
  level: record.soldier.level,
});

const alliesPlayers = demoPlayerRecords.slice(0, 3).map((record, index) =>
  livePlayer(record, index, "allies", "able", index === 0 ? "officer" : "rifleman")
);
const axisPlayers = demoPlayerRecords.slice(3, 6).map((record, index) =>
  livePlayer(record, index, "axis", "baker", index === 0 ? "officer" : "rifleman")
);

export const demoTeamView = {
  fail_count: 0,
  allies: { commander: null, squads: { able: { type: "infantry", has_leader: true, players: alliesPlayers } }, combat: 0, offense: 0, defense: 0, support: 0, kills: 0, deaths: 0, count: alliesPlayers.length },
  axis: { commander: null, squads: { baker: { type: "infantry", has_leader: true, players: axisPlayers } }, combat: 0, offense: 0, defense: 0, support: 0, kills: 0, deaths: 0, count: axisPlayers.length },
  unassigned: { squads: { unassigned: { type: "infantry", has_leader: false, players: [] } }, combat: 0, offense: 0, defense: 0, support: 0, kills: 0, deaths: 0, count: 0 },
};

export const demoGameState = {
  current_map: demoMapLayers[0],
  next_map: demoMapLayers[1],
  raw_time_remaining: "00:57:07",
  time_remaining: 3427,
  allied_score: 3,
  axis_score: 2,
  num_allied_players: 43,
  num_axis_players: 43,
};

export const demoServerConnection = {
  name: "[GER] Frontline Network | #2",
  short_name: "Frontline #2",
  server_number: 2,
  game: "hll",
  current_players: 86,
  max_players: 100,
  port: 4174,
};

const readDemoParameter = (name) => {
  if (typeof window === "undefined") return null;
  return new URLSearchParams(window.location.search).get(name);
};

export const getDemoConnectionMode = () =>
  readDemoParameter("demo_connection") || "online";

export const getDemoRole = () => readDemoParameter("demo_role") || "admin";

export const shouldFailDemoServerSettings = () =>
  readDemoParameter("demo_settings_error") === "1";

const normalizeDemoGame = (value, fallback = "hll") => {
  const game = String(value ?? "").trim().toLowerCase();
  if (!game) return fallback;
  if (game === "hll") return "hll";
  if (["hllv", "hll_vietnam", "vietnam"].includes(game)) return "hll_vietnam";
  return null;
};

export const getDemoServerConnection = () => ({
  ...demoServerConnection,
  game: normalizeDemoGame(readDemoParameter("demo_game")),
});

export const getDemoServerList = () => {
  if (readDemoParameter("demo_multiserver") !== "1") return [];

  return [
    {
      name: "[GER] Frontline Network | Vietnam #3",
      short_name: "Frontline Vietnam #3",
      server_number: 3,
      game: normalizeDemoGame(readDemoParameter("demo_other_game"), "hll_vietnam"),
      current_players: 72,
      max_players: 100,
      port: 4175,
      link: typeof window === "undefined" ? "http://localhost:4175" : window.location.origin,
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
});

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
  history: [],
  range: {
    from: new Date(now).toISOString(),
    to: new Date(now).toISOString(),
    seconds: 0,
    sample_interval_seconds: 15,
    max_samples: 61,
  },
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
    id: 101,
    blacklist: demoBlacklists[0],
    player: { player_id: "76561198000000021", names: [{ name: "FLN_Rulebreaker" }], steaminfo: null },
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
    player: { player_id: "76561198000000022", names: [{ name: "FLN_EventBan" }, { name: "Old_EventBan" }], steaminfo: null },
    reason: "Event-Ausschluss nach wiederholtem Teamkilling",
    formatted_reason: "Event-Ausschluss nach wiederholtem Teamkilling",
    created_at: new Date(Date.now() - 86400000 * 3).toISOString(),
    expires_at: new Date(Date.now() + 86400000 * 4).toISOString(),
    is_active: true,
    admin_name: "Leitstelle",
  },
];

export const isFakeMode = () => import.meta.env.MODE === "fake";
