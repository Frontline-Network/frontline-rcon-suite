export const ADMIN_ACTION_RISK = Object.freeze({
  LOW: "low",
  MEDIUM: "medium",
  HIGH: "high",
  CRITICAL: "critical",
});

export const ADMIN_ACTION_REVERSIBILITY = Object.freeze({
  REVERSIBLE: "reversible",
  LIMITED: "limited",
  IRREVERSIBLE: "irreversible",
});

export const ADMIN_ACTION_CONFIRMATION = Object.freeze({
  REVIEW: "review",
  SECOND: "second_confirmation",
});

export const ADMIN_ACTION_SCOPE = Object.freeze({
  CURRENT_SERVER: "current_server",
  OPTIONAL_ALL_SERVERS: "optional_all_servers",
  CRCON_PROFILE: "crcon_profile",
  BLACKLIST: "blacklist",
});

export const SUPPORTED_ADMIN_ACTION_GAMES = Object.freeze(["hll", "hllv"]);

const shared = Object.freeze({
  supportedGames: SUPPORTED_ADMIN_ACTION_GAMES,
  resultPerTarget: true,
  retryFailedOnly: true,
});

const contract = (definition) =>
  Object.freeze({
    ...shared,
    auditCommand: definition.command,
    confirmation: ADMIN_ACTION_CONFIRMATION.REVIEW,
    ...definition,
    reviewFields: Object.freeze([...(definition.reviewFields ?? [])]),
    supportedGames: Object.freeze([
      ...(definition.supportedGames ?? shared.supportedGames),
    ]),
  });

/**
 * Safety and compatibility metadata for every generic player action.
 *
 * This is deliberately independent from React components. The review dialog,
 * API contract tests and future non-web clients can therefore use the same
 * action semantics instead of inferring risk from a translated button label.
 */
export const ADMIN_ACTION_CONTRACTS = Object.freeze({
  message_player: contract({
    command: "message_player",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.IRREVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["message", "scope"],
  }),
  watch_player: contract({
    command: "watch_player",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CRCON_PROFILE,
    reviewFields: ["reason"],
  }),
  unwatch_player: contract({
    command: "unwatch_player",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CRCON_PROFILE,
    reviewFields: [],
  }),
  add_vip: contract({
    command: "add_vip",
    risk: ADMIN_ACTION_RISK.MEDIUM,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.OPTIONAL_ALL_SERVERS,
    reviewFields: ["description", "expiration", "scope"],
  }),
  remove_vip: contract({
    command: "remove_vip",
    risk: ADMIN_ACTION_RISK.MEDIUM,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.OPTIONAL_ALL_SERVERS,
    reviewFields: ["scope"],
  }),
  switch_player_now: contract({
    command: "switch_player_now",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.LIMITED,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["scope"],
  }),
  switch_player_on_death: contract({
    command: "switch_player_on_death",
    risk: ADMIN_ACTION_RISK.MEDIUM,
    reversibility: ADMIN_ACTION_REVERSIBILITY.LIMITED,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["scope"],
  }),
  punish: contract({
    command: "punish",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.IRREVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["reason", "scope"],
  }),
  kick: contract({
    command: "kick",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.IRREVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["reason", "scope"],
  }),
  temp_ban: contract({
    command: "temp_ban",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.OPTIONAL_ALL_SERVERS,
    reviewFields: ["reason", "duration", "scope"],
  }),
  unban: contract({
    command: "unban",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.LIMITED,
    // The RCON API removes the matching temporary/permanent bans on the
    // current game server. It intentionally does not remove blacklist state.
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["scope"],
  }),
  perma_ban: contract({
    command: "perma_ban",
    risk: ADMIN_ACTION_RISK.CRITICAL,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.OPTIONAL_ALL_SERVERS,
    confirmation: ADMIN_ACTION_CONFIRMATION.SECOND,
    reviewFields: ["reason", "scope"],
  }),
  add_blacklist_record: contract({
    command: "add_blacklist_record",
    risk: ADMIN_ACTION_RISK.CRITICAL,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.BLACKLIST,
    confirmation: ADMIN_ACTION_CONFIRMATION.SECOND,
    reviewFields: ["blacklist", "reason", "expiration", "scope"],
  }),
  flag_player: contract({
    command: "flag_player",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CRCON_PROFILE,
    reviewFields: ["flag"],
  }),
  unflag_player: contract({
    command: "unflag_player",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CRCON_PROFILE,
    reviewFields: ["flag"],
  }),
  post_player_comment: contract({
    command: "post_player_comment",
    risk: ADMIN_ACTION_RISK.LOW,
    reversibility: ADMIN_ACTION_REVERSIBILITY.LIMITED,
    scope: ADMIN_ACTION_SCOPE.CRCON_PROFILE,
    reviewFields: ["comment"],
  }),
  add_admin: contract({
    command: "add_admin",
    risk: ADMIN_ACTION_RISK.CRITICAL,
    reversibility: ADMIN_ACTION_REVERSIBILITY.REVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    confirmation: ADMIN_ACTION_CONFIRMATION.SECOND,
    reviewFields: ["role", "description", "scope"],
  }),
  remove_player_from_squad: contract({
    command: "remove_player_from_squad",
    risk: ADMIN_ACTION_RISK.HIGH,
    reversibility: ADMIN_ACTION_REVERSIBILITY.IRREVERSIBLE,
    scope: ADMIN_ACTION_SCOPE.CURRENT_SERVER,
    reviewFields: ["reason", "scope"],
  }),
});

export function getAdminActionContract(command) {
  const actionContract = ADMIN_ACTION_CONTRACTS[command];
  if (!actionContract) {
    throw new Error(`Missing admin action contract for ${command}`);
  }
  return actionContract;
}

export function normalizeAdminActionGame(game) {
  const value = String(game ?? "")
    .trim()
    .toLowerCase();
  if (value === "hll") return "hll";
  if (["hllv", "hll_vietnam", "vietnam"].includes(value)) return "hllv";
  return null;
}

export function supportsAdminActionGame(actionContract, game) {
  const normalized = normalizeAdminActionGame(game);
  return Boolean(
    normalized && actionContract?.supportedGames?.includes(normalized)
  );
}

export function requiresSecondConfirmation(actionContract, targetCount = 1) {
  return (
    actionContract?.confirmation === ADMIN_ACTION_CONFIRMATION.SECOND ||
    Number(targetCount) > 1
  );
}

export function validateAdminActionContracts(
  contracts = ADMIN_ACTION_CONTRACTS
) {
  const errors = [];
  const commands = new Set();
  const allowedRisks = new Set(Object.values(ADMIN_ACTION_RISK));
  const allowedReversibility = new Set(
    Object.values(ADMIN_ACTION_REVERSIBILITY)
  );
  const allowedConfirmations = new Set(
    Object.values(ADMIN_ACTION_CONFIRMATION)
  );
  const allowedScopes = new Set(Object.values(ADMIN_ACTION_SCOPE));

  for (const [key, value] of Object.entries(contracts)) {
    if (key !== value.command)
      errors.push(`${key}: command must match its key`);
    if (commands.has(value.command)) errors.push(`${key}: duplicate command`);
    commands.add(value.command);
    if (!allowedRisks.has(value.risk)) errors.push(`${key}: invalid risk`);
    if (!allowedReversibility.has(value.reversibility)) {
      errors.push(`${key}: invalid reversibility`);
    }
    if (!allowedConfirmations.has(value.confirmation)) {
      errors.push(`${key}: invalid confirmation`);
    }
    if (!allowedScopes.has(value.scope)) errors.push(`${key}: invalid scope`);
    if (!Array.isArray(value.reviewFields)) {
      errors.push(`${key}: reviewFields must be an array`);
    }
    if (!value.auditCommand) errors.push(`${key}: auditCommand is required`);
    if (!value.resultPerTarget)
      errors.push(`${key}: per-target results required`);
    if (!value.retryFailedOnly)
      errors.push(`${key}: retry-failed-only required`);
    for (const game of SUPPORTED_ADMIN_ACTION_GAMES) {
      if (!value.supportedGames?.includes(game)) {
        errors.push(`${key}: missing ${game} compatibility decision`);
      }
    }
  }

  return errors;
}
