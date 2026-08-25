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

console.log(
  `Validated ${executionCommands.length} action definitions across ${referencedCommands.size} commands.`
);
