import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { simulateLevelRule } from "../src/pages/settings/config-form/simulateLevelRule.mjs";
import { simulateEscalationRule } from "../src/pages/settings/config-form/simulateEscalationRule.mjs";
import { simulateTrustRule } from "../src/pages/settings/config-form/simulateTrustRule.mjs";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(root, relativePath), "utf8");

const config = {
  enabled: true,
  dry_run: false,
  dont_do_anything_below_this_number_of_players: 20,
  min_level: 10,
  max_level: 200,
  levelbug_enabled: true,
  whitelist_flags: ["VIP"],
  level_thresholds: {
    officer: { min_players: 30, min_level: 50, label: "Squad leader" },
  },
  number_of_warnings: 2,
  number_of_punishments: 1,
  kick_after_max_punish: true,
};

const cases = [
  [
    "off",
    { ...config, enabled: false },
    { playerLevel: 20, serverPlayers: 60 },
  ],
  ["waiting", config, { playerLevel: 20, serverPlayers: 10 }],
  ["exempt", config, { playerLevel: 20, serverPlayers: 60, playerFlag: "VIP" }],
  ["exempt", config, { playerLevel: 1, serverPlayers: 60 }],
  ["immediate", config, { playerLevel: 5, serverPlayers: 60 }],
  [
    "escalation",
    config,
    { playerLevel: 20, serverPlayers: 60, role: "officer" },
  ],
  [
    "detected",
    {
      ...config,
      number_of_warnings: 0,
      number_of_punishments: 0,
      kick_after_max_punish: false,
    },
    { playerLevel: 20, serverPlayers: 60, role: "officer" },
  ],
  ["allowed", config, { playerLevel: 80, serverPlayers: 60, role: "officer" }],
];

for (const [expected, rule, sample] of cases) {
  const actual = simulateLevelRule(rule, sample).outcome;
  if (actual !== expected) {
    throw new Error(`Expected ${expected}, received ${actual}`);
  }
}

const escalationConfig = {
  enabled: true,
  dry_run: false,
  dont_do_anything_below_this_number_of_players: 20,
  whitelist_flags: ["VIP"],
  immune_roles: ["medic"],
  immune_player_level: 10,
  number_of_notes: 1,
  notes_interval_seconds: 10,
  number_of_warnings: 2,
  warning_interval_seconds: 60,
  number_of_punishments: 1,
  min_squad_players_for_punish: 2,
  min_server_players_for_punish: 40,
  punish_interval_seconds: 60,
  kick_after_max_punish: true,
  min_squad_players_for_kick: 2,
  min_server_players_for_kick: 50,
  kick_grace_period_seconds: 120,
};

const escalationCases = [
  ["off", "noLeader", { ...escalationConfig, enabled: false }, {}],
  ["waiting", "noLeader", escalationConfig, { serverPlayers: 10 }],
  [
    "noViolation",
    "noLeader",
    escalationConfig,
    { serverPlayers: 60, squadState: "led" },
  ],
  [
    "exempt",
    "noLeader",
    escalationConfig,
    { serverPlayers: 60, squadState: "leaderless", playerFlag: "VIP" },
  ],
  [
    "exempt",
    "noLeader",
    escalationConfig,
    { serverPlayers: 60, squadState: "leaderless", playerLevel: 10 },
  ],
  [
    "exempt",
    "noLeader",
    escalationConfig,
    {
      serverPlayers: 60,
      squadPlayers: 3,
      squadState: "leaderless",
      playerLevel: 100,
      role: "medic",
    },
  ],
  [
    "escalation",
    "noLeader",
    escalationConfig,
    {
      serverPlayers: 60,
      squadPlayers: 3,
      squadState: "leaderless",
      playerLevel: 100,
      role: "rifleman",
    },
  ],
  [
    "paused",
    "noLeader",
    escalationConfig,
    {
      serverPlayers: 45,
      squadPlayers: 1,
      squadState: "leaderless",
      playerLevel: 100,
    },
  ],
  [
    "detected",
    "noLeader",
    {
      ...escalationConfig,
      number_of_notes: 0,
      number_of_warnings: 0,
      number_of_punishments: 0,
    },
    {
      serverPlayers: 60,
      squadPlayers: 3,
      squadState: "leaderless",
      playerLevel: 100,
    },
  ],
  [
    "noViolation",
    "noSoloTank",
    escalationConfig,
    { serverPlayers: 60, squadType: "infantry", squadPlayers: 1 },
  ],
  [
    "noViolation",
    "noSoloTank",
    escalationConfig,
    { serverPlayers: 60, squadType: "armor", squadPlayers: 2 },
  ],
  [
    "escalation",
    "noSoloTank",
    escalationConfig,
    {
      serverPlayers: 60,
      squadType: "armor",
      squadPlayers: 1,
      playerLevel: 100,
    },
  ],
];

for (const [expected, kind, rule, sample] of escalationCases) {
  const actual = simulateEscalationRule(kind, rule, sample).outcome;
  if (actual !== expected) {
    throw new Error(`Expected ${expected} for ${kind}, received ${actual}`);
  }
}

const vacConfig = {
  vac_history_days: 365,
  game_ban_threshhold: 2,
  blacklist_id: 1,
  ban_on_vac_history_reason:
    "VAC history ({DAYS_SINCE_LAST_BAN}/{MAX_DAYS_SINCE_BAN})",
  auto_expire: true,
  whitelist_flags: ["trusted"],
};

const tkConfig = {
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
  blacklist_id: 1,
  ban_duration: { minutes: 0, hours: 24, days: 0, weeks: 0, years: 0 },
  discord_webhook_url: "https://discord.example/frontline",
  discord_webhook_message: "Teamkill ban for {player}",
};

const tkSample = {
  profileStatus: "available",
  vipLookupStatus: "available",
  isVip: false,
  sessions: 0,
  playerFlag: "",
  hasConnectEvent: true,
  weapon: "Rifle",
  minutesAfterConnect: 2,
  ownKillsBeforeEvent: 0,
  deathsBeforeEvent: 0,
  teamkillsIncludingCurrent: 3,
};

const trustCases = [
  ["off", "vacBans", { ...vacConfig, vac_history_days: 0 }, {}],
  ["unavailable", "vacBans", vacConfig, { dataStatus: "missing" }],
  [
    "exempt",
    "vacBans",
    vacConfig,
    {
      dataStatus: "current",
      vacBanned: true,
      daysSinceLastBan: 30,
      playerFlag: "trusted",
    },
  ],
  [
    "noAction",
    "vacBans",
    vacConfig,
    { dataStatus: "current", vacBanned: true, daysSinceLastBan: 0 },
  ],
  [
    "noAction",
    "vacBans",
    vacConfig,
    { dataStatus: "current", vacBanned: true, daysSinceLastBan: 500 },
  ],
  [
    "noAction",
    "vacBans",
    vacConfig,
    {
      dataStatus: "current",
      vacBanned: false,
      gameBans: 1,
      daysSinceLastBan: 30,
    },
  ],
  [
    "configError",
    "vacBans",
    { ...vacConfig, ban_on_vac_history_reason: "Ban {UNKNOWN}" },
    { dataStatus: "current", vacBanned: true, daysSinceLastBan: 30 },
  ],
  [
    "action",
    "vacBans",
    vacConfig,
    { dataStatus: "current", vacBanned: true, daysSinceLastBan: 30 },
  ],
  [
    "action",
    "vacBans",
    vacConfig,
    {
      dataStatus: "stale",
      vacBanned: false,
      gameBans: 2,
      daysSinceLastBan: 30,
    },
    "staleData",
  ],
  ["off", "tkBans", { ...tkConfig, enabled: false }, tkSample],
  ["exempt", "tkBans", tkConfig, { ...tkSample, isVip: true }],
  ["exempt", "tkBans", tkConfig, { ...tkSample, sessions: 10 }],
  ["exempt", "tkBans", tkConfig, { ...tkSample, playerFlag: "admin" }],
  ["noAction", "tkBans", tkConfig, { ...tkSample, hasConnectEvent: false }],
  ["exempt", "tkBans", tkConfig, { ...tkSample, weapon: "Roadkill" }],
  ["noAction", "tkBans", tkConfig, { ...tkSample, minutesAfterConnect: 16 }],
  ["noAction", "tkBans", tkConfig, { ...tkSample, ownKillsBeforeEvent: 8 }],
  ["noAction", "tkBans", tkConfig, { ...tkSample, deathsBeforeEvent: 8 }],
  [
    "noAction",
    "tkBans",
    tkConfig,
    { ...tkSample, teamkillsIncludingCurrent: 2 },
  ],
  ["action", "tkBans", tkConfig, tkSample],
  [
    "action",
    "tkBans",
    tkConfig,
    { ...tkSample, profileStatus: "missing" },
    "profileUnavailable",
  ],
  [
    "action",
    "tkBans",
    { ...tkConfig, discord_webhook_message: "Ban for {player_name}" },
    tkSample,
    "notificationTemplate",
  ],
  [
    "action",
    "tkBans",
    {
      ...tkConfig,
      ban_duration: {
        minutes: 0,
        hours: 0,
        days: 0,
        weeks: 0,
        years: 1,
      },
    },
    tkSample,
    "yearsIgnored",
  ],
];

for (const [expected, kind, rule, sample, expectedRisk] of trustCases) {
  const result = simulateTrustRule(kind, rule, sample);
  if (result.outcome !== expected) {
    throw new Error(
      `Expected ${expected} for ${kind}, received ${result.outcome}`
    );
  }
  if (expectedRisk && !result.risks.includes(expectedRisk)) {
    throw new Error(`Expected ${expectedRisk} risk for ${kind}`);
  }
}

const actionBar = read("src/pages/settings/config-form/ConfigActionBar.jsx");
const detail = read("src/pages/settings/[configs]/detail.jsx");
const modeControl = read(
  "src/pages/settings/config-form/ConfigOperationModeControl.jsx"
);

for (const [label, source, fragments] of [
  ["change footer", actionBar, ["metaItems", "config-save-button"]],
  [
    "level workbench",
    detail,
    ["changeMetaItems", "LevelRuleTestDrawer", "config-test-impact-button"],
  ],
  [
    "escalation workbench",
    detail,
    ["EscalationRuleTestDrawer", "supportsImpactTest", "testKind"],
  ],
  ["trust workbench", detail, ["TrustRuleTestDrawer", '"vacBans"', '"tkBans"']],
  ["operation mode", modeControl, ['"off"', '"observe"', '"active"']],
]) {
  for (const fragment of fragments) {
    if (!source.includes(fragment)) {
      throw new Error(`${label} is missing ${fragment}`);
    }
  }
}

console.log(
  `Configuration Workbench contract passed: ${cases.length} level simulations, ${escalationCases.length} escalation simulations, ${trustCases.length} trust simulations, shared mode control, scope, validation and impact tests stay connected.`
);
