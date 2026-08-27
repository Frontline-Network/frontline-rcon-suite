import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import {
  ADMIN_ACTION_CONFIRMATION,
  ADMIN_ACTION_CONTRACTS,
  getAdminActionContract,
  normalizeAdminActionGame,
  requiresSecondConfirmation,
  supportsAdminActionGame,
  validateAdminActionContracts,
} from "../src/features/player-action/action-contracts.mjs";

const actionSource = await readFile(
  new URL("../src/features/player-action/actions.js", import.meta.url),
  "utf8"
);
const livePageSource = await readFile(
  new URL("../src/pages/views/live/index.jsx", import.meta.url),
  "utf8"
);
const livePlayerColumnsSource = await readFile(
  new URL("../src/pages/views/live/players-columns.jsx", import.meta.url),
  "utf8"
);
const teamPageSource = await readFile(
  new URL("../src/pages/views/team/index.jsx", import.meta.url),
  "utf8"
);
const teamSectionSource = await readFile(
  new URL("../src/pages/views/team/team-section.jsx", import.meta.url),
  "utf8"
);
const liveSessionsPageSource = await readFile(
  new URL("../src/pages/stats/live-sessions/index.jsx", import.meta.url),
  "utf8"
);
const liveSessionsColumnsSource = await readFile(
  new URL("../src/pages/stats/live-sessions/columns.jsx", import.meta.url),
  "utf8"
);
const completedGamePageSource = await readFile(
  new URL("../src/pages/stats/games/[gameId]/index.jsx", import.meta.url),
  "utf8"
);
const completedGameTableSource = await readFile(
  new URL("../src/pages/stats/games/[gameId]/game-table.jsx", import.meta.url),
  "utf8"
);
const completedGameColumnsSource = await readFile(
  new URL(
    "../src/pages/stats/games/[gameId]/game-columns.jsx",
    import.meta.url
  ),
  "utf8"
);

const matches = (pattern) =>
  [...actionSource.matchAll(pattern)].map((match) => match[1]);

const executionCommands = matches(/execute:\s*executeAction\("([^"]+)"\)/g);
const safetyCommands = matches(
  /safety:\s*getAdminActionContract\("([^"]+)"\)/g
);

const actionDefinitions = [
  ...actionSource.matchAll(/export const (\w+Action)\s*=\s*\{([\s\S]*?)\n\};/g),
];

assert.equal(
  actionDefinitions.length,
  executionCommands.length,
  "Every executed generic action must be parsed and checked individually"
);

for (const [, actionName, body] of actionDefinitions) {
  const safetyCommand = body.match(
    /safety:\s*getAdminActionContract\("([^"]+)"\)/
  )?.[1];
  const executionCommand = body.match(
    /execute:\s*executeAction\("([^"]+)"\)/
  )?.[1];
  assert.ok(safetyCommand, `${actionName} must attach a safety contract`);
  assert.ok(executionCommand, `${actionName} must execute an explicit command`);
  assert.equal(
    safetyCommand,
    executionCommand,
    `${actionName} must review the same command that it executes`
  );
}

assert.deepEqual(
  [...safetyCommands].sort(),
  [...executionCommands].sort(),
  "Every generic player action must attach the contract for the command it executes"
);

assert.deepEqual(
  validateAdminActionContracts(),
  [],
  "Admin action contracts must be complete and internally consistent"
);

for (const command of new Set(executionCommands)) {
  const actionContract = getAdminActionContract(command);
  assert.equal(
    actionContract.auditCommand,
    command,
    `${command} must link to its exact audit command`
  );
  assert.equal(
    supportsAdminActionGame(actionContract, "hll"),
    true,
    `${command} needs an explicit HLL compatibility decision`
  );
  assert.equal(
    supportsAdminActionGame(actionContract, "hll_vietnam"),
    true,
    `${command} needs an explicit HLL Vietnam compatibility decision`
  );
}

assert.equal(normalizeAdminActionGame("vietnam"), "hllv");
assert.equal(normalizeAdminActionGame("unknown"), null);

for (const command of ["perma_ban", "add_admin"]) {
  assert.equal(
    getAdminActionContract(command).confirmation,
    ADMIN_ACTION_CONFIRMATION.SECOND,
    `${command} must require a second confirmation`
  );
}

assert.equal(
  getAdminActionContract("add_blacklist_record").confirmation,
  ADMIN_ACTION_CONFIRMATION.REVIEW,
  "A reversible single-player blacklist entry should execute from its reviewed form"
);
assert.equal(
  requiresSecondConfirmation(getAdminActionContract("add_blacklist_record"), 1),
  false,
  "A single blacklist target must not require a redundant second confirmation"
);
assert.equal(
  requiresSecondConfirmation(getAdminActionContract("add_blacklist_record"), 2),
  true,
  "Bulk blacklist actions retain the stronger confirmation path"
);

assert.equal(
  requiresSecondConfirmation(getAdminActionContract("kick"), 1),
  false
);
assert.equal(
  requiresSecondConfirmation(getAdminActionContract("kick"), 2),
  true,
  "Bulk actions must require the stronger confirmation path"
);

const referencedCommands = new Set(safetyCommands);
const unusedContracts = Object.keys(ADMIN_ACTION_CONTRACTS).filter(
  (command) => !referencedCommands.has(command)
);
assert.deepEqual(
  unusedContracts,
  [],
  "Contracts must not drift away from the generic action catalogue"
);

assert.doesNotMatch(
  livePlayerColumnsSource,
  /ActionMenuButton/,
  "Live player rows must not mount a complete action menu per player"
);
assert.match(
  livePlayerColumnsSource,
  /table\.options\.meta\?\.openPlayerActionMenu/,
  "Live player row triggers must delegate to the shared action menu"
);
assert.equal(
  [...livePageSource.matchAll(/<ActionMenu\b/g)].length,
  1,
  "The live desktop roster must mount exactly one shared row action menu"
);

assert.doesNotMatch(
  teamSectionSource,
  /ActionMenuButton/,
  "Team player rows must not mount a complete action menu per player"
);
assert.match(
  teamSectionSource,
  /onOpenPlayerActionMenu/,
  "Team player row triggers must delegate to the shared action menu"
);
assert.equal(
  [...teamPageSource.matchAll(/<ActionMenu\b/g)].length,
  1,
  "The team roster must mount exactly one shared row action menu"
);

assert.doesNotMatch(
  liveSessionsColumnsSource,
  /ActionMenuButton/,
  "Live-session desktop rows must not mount a complete action menu per player"
);
assert.match(
  liveSessionsColumnsSource,
  /table\.options\.meta\?\.openPlayerActionMenu/,
  "Live-session desktop row triggers must delegate to the shared action menu"
);
assert.equal(
  [...liveSessionsPageSource.matchAll(/<ActionMenu\b/g)].length,
  1,
  "Live Sessions must mount exactly one shared row action menu"
);

assert.doesNotMatch(
  completedGameColumnsSource,
  /ActionMenuButton/,
  "Completed-game desktop rows must not mount a complete action menu per player"
);
assert.match(
  completedGameColumnsSource,
  /table\.options\.meta\?\.openPlayerActionMenu/,
  "Completed-game desktop row triggers must delegate to the shared action menu"
);
assert.match(
  completedGameTableSource,
  /table\.options\.meta\?\.openPlayerActionMenu/,
  "Completed-game mobile row triggers must delegate to the shared action menu"
);
assert.equal(
  [...completedGameTableSource.matchAll(/<ActionMenuButton\b/g)].length,
  1,
  "Completed-game tables may retain only the single multi-player toolbar menu"
);
assert.equal(
  [...completedGamePageSource.matchAll(/<ActionMenu\b/g)].length,
  1,
  "Completed games must mount exactly one shared row action menu"
);

console.log(
  `Validated ${executionCommands.length} action definitions across ${referencedCommands.size} commands and one shared row action menu on Live, Teams, Live Sessions and completed games.`
);
