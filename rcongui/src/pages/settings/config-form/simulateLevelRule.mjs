const positive = (value) => Math.max(0, Number(value) || 0);

const activeStages = (config = {}) => {
  const stages = [];
  if (Number(config.number_of_warnings) !== 0) stages.push("warn");
  if (Number(config.number_of_punishments) !== 0) stages.push("punish");
  if (config.kick_after_max_punish) stages.push("kick");
  return stages;
};

export const simulateLevelRule = (config = {}, sample = {}) => {
  const playerLevel = positive(sample.playerLevel);
  const serverPlayers = positive(sample.serverPlayers);
  const role = sample.role || "";
  const playerFlag = String(sample.playerFlag || "").trim();
  const startAt = positive(
    config.dont_do_anything_below_this_number_of_players
  );
  const mode = !config.enabled
    ? "off"
    : config.dry_run
    ? "observe"
    : "active";

  if (mode === "off") return { outcome: "off", mode, stages: [] };
  if (serverPlayers < startAt) {
    return { outcome: "waiting", mode, stages: [], startAt };
  }

  const exemptFlags = Array.isArray(config.whitelist_flags)
    ? config.whitelist_flags.map((flag) => String(flag).trim())
    : [];
  if (playerFlag && exemptFlags.includes(playerFlag)) {
    return { outcome: "exempt", reason: "flag", mode, stages: [] };
  }
  if (config.levelbug_enabled && playerLevel === 1) {
    return { outcome: "exempt", reason: "levelBug", mode, stages: [] };
  }

  const minLevel = positive(config.min_level);
  const maxLevel = positive(config.max_level);
  if (minLevel > 0 && playerLevel < minLevel) {
    return {
      outcome: "immediate",
      reason: "minimum",
      mode,
      requiredLevel: minLevel,
      stages: ["kick"],
    };
  }
  if (maxLevel > 0 && playerLevel > maxLevel) {
    return {
      outcome: "immediate",
      reason: "maximum",
      mode,
      requiredLevel: maxLevel,
      stages: ["kick"],
    };
  }

  const roleRule = role ? config.level_thresholds?.[role] : null;
  const roleStartsAt = positive(roleRule?.min_players);
  const roleMinimum = positive(roleRule?.min_level);
  if (
    roleRule &&
    roleMinimum > 0 &&
    serverPlayers >= roleStartsAt &&
    playerLevel < roleMinimum
  ) {
    const stages = activeStages(config);
    return {
      outcome: stages.length ? "escalation" : "detected",
      reason: "role",
      mode,
      role,
      requiredLevel: roleMinimum,
      stages,
    };
  }

  return { outcome: "allowed", mode, stages: [] };
};
