const positive = (value) => Math.max(0, Number(value) || 0);

const configuredCount = (value) => {
  const numeric = Number(value);
  return numeric === -1 ? -1 : positive(numeric);
};

const getMode = (config = {}) =>
  !config.enabled ? "off" : config.dry_run ? "observe" : "active";

const getViolation = (kind, sample) => {
  if (kind === "noLeader") {
    const squadState = sample.squadState || "leaderless";
    return squadState === "leaderless"
      ? { violation: true }
      : { violation: false, reason: squadState };
  }

  const squadType = sample.squadType || "armor";
  const squadPlayers = Math.max(1, positive(sample.squadPlayers));
  if (squadType !== "armor") {
    return { violation: false, reason: "nonArmor" };
  }
  return squadPlayers <= 1
    ? { violation: true }
    : { violation: false, reason: "crewed" };
};

const getExemption = (kind, config, sample) => {
  const playerFlag = String(sample.playerFlag || "").trim();
  const whitelistFlags = Array.isArray(config.whitelist_flags)
    ? config.whitelist_flags.map((flag) => String(flag).trim())
    : [];
  if (playerFlag && whitelistFlags.includes(playerFlag)) return "flag";

  const protectedLevel = positive(config.immune_player_level);
  if (
    protectedLevel > 0 &&
    positive(sample.playerLevel) <= protectedLevel
  ) {
    return "level";
  }

  if (
    kind === "noLeader" &&
    sample.role &&
    Array.isArray(config.immune_roles) &&
    config.immune_roles.includes(sample.role)
  ) {
    return "role";
  }

  return null;
};

const thresholdBlock = (kind, config, sample, stage) => {
  const serverPlayers = positive(sample.serverPlayers);
  const serverMinimum = positive(config[`min_server_players_for_${stage}`]);
  if (serverPlayers < serverMinimum) {
    return { reason: "serverPlayers", minimum: serverMinimum };
  }

  if (kind === "noLeader") {
    const squadPlayers = Math.max(1, positive(sample.squadPlayers));
    const squadMinimum = positive(config[`min_squad_players_for_${stage}`]);
    if (squadPlayers < squadMinimum) {
      return { reason: "squadPlayers", minimum: squadMinimum };
    }
  }

  return null;
};

export const simulateEscalationRule = (
  kind,
  config = {},
  sample = {}
) => {
  const mode = getMode(config);
  if (mode === "off") return { outcome: "off", mode, stages: [] };

  const serverPlayers = positive(sample.serverPlayers);
  const startAt = positive(
    config.dont_do_anything_below_this_number_of_players
  );
  if (serverPlayers < startAt) {
    return { outcome: "waiting", mode, startAt, stages: [] };
  }

  const violation = getViolation(kind, sample);
  if (!violation.violation) {
    return {
      outcome: "noViolation",
      mode,
      reason: violation.reason,
      stages: [],
    };
  }

  const exemption = getExemption(kind, config, sample);
  if (exemption) {
    return { outcome: "exempt", mode, reason: exemption, stages: [] };
  }

  const stages = [];
  const noteCount = configuredCount(config.number_of_notes);
  if (noteCount > 0) {
    stages.push({
      kind: "note",
      count: noteCount,
      interval: positive(config.notes_interval_seconds),
    });
  }

  const warningCount = configuredCount(config.number_of_warnings);
  if (warningCount !== 0) {
    stages.push({
      kind: "warn",
      count: warningCount,
      interval: positive(config.warning_interval_seconds),
      terminal: warningCount === -1,
    });
    if (warningCount === -1) {
      return { outcome: "escalation", mode, terminal: "warn", stages };
    }
  }

  const punishmentCount = configuredCount(config.number_of_punishments);
  if (punishmentCount === 0) {
    return {
      outcome: warningCount > 0 ? "escalation" : "detected",
      mode,
      terminal: warningCount > 0 ? "warn" : "note",
      stages,
    };
  }

  const punishBlock = thresholdBlock(kind, config, sample, "punish");
  if (punishBlock) {
    stages.push({
      kind: "punish",
      count: punishmentCount,
      interval: positive(config.punish_interval_seconds),
      blocked: punishBlock,
    });
    return { outcome: "paused", mode, terminal: "punish", stages };
  }

  stages.push({
    kind: "punish",
    count: punishmentCount,
    interval: positive(config.punish_interval_seconds),
    terminal: punishmentCount === -1,
  });
  if (punishmentCount === -1) {
    return { outcome: "escalation", mode, terminal: "punish", stages };
  }

  if (!config.kick_after_max_punish) {
    return { outcome: "escalation", mode, terminal: "punish", stages };
  }

  const kickBlock = thresholdBlock(kind, config, sample, "kick");
  if (kickBlock) {
    stages.push({ kind: "kick", blocked: kickBlock });
    return { outcome: "paused", mode, terminal: "kick", stages };
  }

  stages.push({
    kind: "kick",
    delay: positive(config.kick_grace_period_seconds),
  });
  return { outcome: "escalation", mode, terminal: "kick", stages };
};
