import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { simulateLevelRule } from "../src/pages/settings/config-form/simulateLevelRule.mjs";
import { simulateEscalationRule } from "../src/pages/settings/config-form/simulateEscalationRule.mjs";

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
  ["off", { ...config, enabled: false }, { playerLevel: 20, serverPlayers: 60 }],
  ["waiting", config, { playerLevel: 20, serverPlayers: 10 }],
  ["exempt", config, { playerLevel: 20, serverPlayers: 60, playerFlag: "VIP" }],
  ["exempt", config, { playerLevel: 1, serverPlayers: 60 }],
  ["immediate", config, { playerLevel: 5, serverPlayers: 60 }],
  ["escalation", config, { playerLevel: 20, serverPlayers: 60, role: "officer" }],
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
    throw new Error(
      `Expected ${expected} for ${kind}, received ${actual}`
    );
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
  ["operation mode", modeControl, ['"off"', '"observe"', '"active"']],
]) {
  for (const fragment of fragments) {
    if (!source.includes(fragment)) {
      throw new Error(`${label} is missing ${fragment}`);
    }
  }
}

console.log(
  `Configuration Workbench contract passed: ${cases.length} level simulations, ${escalationCases.length} escalation simulations, shared mode control, scope, validation and impact tests stay connected.`
);
