const finiteNumber = (value) => {
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const positive = (value) => Math.max(0, finiteNumber(value) ?? 0);

const stringList = (value) =>
  Array.isArray(value) ? value.map((item) => String(item).trim()) : [];

const placeholderNames = (template) => {
  const names = [];
  const source = String(template || "")
    .replaceAll("{{", "")
    .replaceAll("}}", "");
  for (const match of source.matchAll(/\{([^{}]+)\}/g)) {
    names.push(match[1].split(/[!:]/, 1)[0]);
  }
  return names;
};

const invalidPlaceholders = (template, allowed) =>
  placeholderNames(template).filter((name) => !allowed.includes(name));

const banTarget = (config) =>
  config.blacklist_id === null || config.blacklist_id === undefined
    ? { kind: "server" }
    : { kind: "blacklist", id: config.blacklist_id };

const durationMinutes = (duration = {}) =>
  positive(duration.minutes) +
  positive(duration.hours) * 60 +
  positive(duration.days) * 24 * 60 +
  positive(duration.weeks) * 7 * 24 * 60;

const normalizedDuration = (duration = {}) => ({
  weeks: positive(duration.weeks),
  days: positive(duration.days),
  hours: positive(duration.hours),
  minutes: positive(duration.minutes),
});

const simulateVac = (config, sample) => {
  const historyDays = positive(config.vac_history_days);
  if (historyDays <= 0) {
    return { outcome: "off", kind: "vacBans", stages: [], risks: [] };
  }

  const dataStatus = sample.dataStatus || "current";
  const stages = [{ kind: "storedData", status: dataStatus }];
  const risks = [];
  if (["missing", "invalid"].includes(dataStatus)) {
    stages.push({ kind: "refresh", status: "queued" });
    stages.push({ kind: "freshRecheck", status: "conditional" });
    return {
      outcome: "unavailable",
      reason: dataStatus,
      kind: "vacBans",
      stages,
      risks: [dataStatus],
    };
  }

  if (dataStatus === "stale") risks.push("staleData");
  if (dataStatus === "unknownAge") risks.push("unknownAge");

  const flag = String(sample.playerFlag || "").trim();
  if (flag && stringList(config.whitelist_flags).includes(flag)) {
    stages.push({ kind: "exemption", status: "flag", value: flag });
    return {
      outcome: "exempt",
      reason: "flag",
      kind: "vacBans",
      stages,
      risks,
    };
  }

  const daysSinceLastBan = finiteNumber(sample.daysSinceLastBan);
  if (daysSinceLastBan === null) {
    stages.push({ kind: "decision", status: "invalid" });
    return {
      outcome: "unavailable",
      reason: "invalid",
      kind: "vacBans",
      stages,
      risks: [...risks, "invalid"],
    };
  }

  const gameBanThreshold = positive(config.game_ban_threshhold);
  const numberOfGameBans = positive(sample.gameBans);
  const vacBanned = Boolean(sample.vacBanned);
  const gameBanHit =
    gameBanThreshold > 0 && numberOfGameBans >= gameBanThreshold;
  const qualifyingHistory = vacBanned || gameBanHit;

  stages.push({
    kind: "history",
    days: daysSinceLastBan,
    vacBanned,
    gameBans: numberOfGameBans,
    threshold: gameBanThreshold,
  });

  if (
    daysSinceLastBan <= 0 ||
    daysSinceLastBan > historyDays ||
    !qualifyingHistory
  ) {
    stages.push({ kind: "decision", status: "allow" });
    return {
      outcome: "noAction",
      reason:
        daysSinceLastBan <= 0
          ? "zeroDays"
          : daysSinceLastBan > historyDays
          ? "outsideHistory"
          : "belowThreshold",
      kind: "vacBans",
      stages,
      risks,
    };
  }

  const invalidReasonTokens = invalidPlaceholders(
    config.ban_on_vac_history_reason,
    ["DAYS_SINCE_LAST_BAN", "MAX_DAYS_SINCE_BAN"]
  );
  if (invalidReasonTokens.length) {
    stages.push({
      kind: "decision",
      status: "templateError",
      tokens: invalidReasonTokens,
    });
    return {
      outcome: "configError",
      reason: "reasonTemplate",
      kind: "vacBans",
      stages,
      risks: [...risks, "reasonTemplate"],
      invalidTokens: invalidReasonTokens,
    };
  }

  const expiresInDays = config.auto_expire
    ? Math.max(0, historyDays - daysSinceLastBan)
    : null;
  stages.push({
    kind: "action",
    status: "ban",
    target: banTarget(config),
    expiresInDays,
  });
  stages.push({ kind: "refresh", status: "queued" });
  stages.push({ kind: "freshRecheck", status: "conditional" });

  return {
    outcome: "action",
    reason: vacBanned ? "vac" : "gameBans",
    kind: "vacBans",
    stages,
    risks,
    target: banTarget(config),
    expiresInDays,
  };
};

const simulateTk = (config, sample) => {
  if (!config.enabled) {
    return { outcome: "off", kind: "tkBans", stages: [], risks: [] };
  }

  const stages = [];
  const risks = [];
  const whitelist = config.whitelist_players || {};
  const profileStatus = sample.profileStatus || "available";
  const vipLookupStatus = sample.vipLookupStatus || "available";

  stages.push({ kind: "profile", status: profileStatus });
  if (profileStatus === "available") {
    if (whitelist.is_vip && vipLookupStatus === "unavailable") {
      risks.push("vipLookupUnavailable");
    }
    if (whitelist.is_vip && vipLookupStatus === "available" && sample.isVip) {
      stages.push({ kind: "exemption", status: "vip" });
      return {
        outcome: "exempt",
        reason: "vip",
        kind: "tkBans",
        stages,
        risks,
      };
    }

    const sessionThreshold = positive(whitelist.has_at_least_n_sessions);
    if (sessionThreshold > 0 && positive(sample.sessions) >= sessionThreshold) {
      stages.push({
        kind: "exemption",
        status: "sessions",
        threshold: sessionThreshold,
      });
      return {
        outcome: "exempt",
        reason: "sessions",
        kind: "tkBans",
        stages,
        risks,
      };
    }

    const flag = String(sample.playerFlag || "").trim();
    if (flag && stringList(whitelist.has_flag).includes(flag)) {
      stages.push({ kind: "exemption", status: "flag", value: flag });
      return {
        outcome: "exempt",
        reason: "flag",
        kind: "tkBans",
        stages,
        risks,
      };
    }
  } else {
    risks.push("profileUnavailable");
  }

  if (!sample.hasConnectEvent) {
    stages.push({ kind: "logWindow", status: "missingConnect" });
    return {
      outcome: "noAction",
      reason: "missingConnect",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  stages.push({ kind: "logWindow", status: "connected" });
  const weapon = String(sample.weapon || "")
    .trim()
    .toLowerCase();
  if (
    weapon &&
    stringList(config.excluded_weapons)
      .map((item) => item.toLowerCase())
      .includes(weapon)
  ) {
    stages.push({ kind: "exemption", status: "weapon" });
    return {
      outcome: "exempt",
      reason: "weapon",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  if (
    positive(sample.minutesAfterConnect) >
    positive(config.max_time_after_connect_minutes)
  ) {
    stages.push({ kind: "window", status: "expired" });
    return {
      outcome: "noAction",
      reason: "outsideWindow",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  if (
    positive(sample.ownKillsBeforeEvent) >=
    positive(config.ignore_tk_after_n_kills)
  ) {
    stages.push({ kind: "window", status: "stoppedByKills" });
    return {
      outcome: "noAction",
      reason: "kills",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  if (
    positive(sample.deathsBeforeEvent) >=
    positive(config.ignore_tk_after_n_deaths)
  ) {
    stages.push({ kind: "window", status: "stoppedByDeaths" });
    return {
      outcome: "noAction",
      reason: "deaths",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  const teamkills = positive(sample.teamkillsIncludingCurrent);
  const tolerance = positive(config.teamkill_tolerance_count);
  stages.push({ kind: "counter", teamkills, tolerance });
  if (teamkills <= tolerance) {
    return {
      outcome: "noAction",
      reason: "tolerated",
      kind: "tkBans",
      stages,
      risks,
    };
  }

  const minutes = durationMinutes(config.ban_duration);
  const duration = normalizedDuration(config.ban_duration);
  if (positive(config.ban_duration?.years) > 0) risks.push("yearsIgnored");
  const invalidAuditTokens = config.discord_webhook_url
    ? invalidPlaceholders(config.discord_webhook_message, ["player"])
    : [];
  if (invalidAuditTokens.length) risks.push("notificationTemplate");

  const target = banTarget(config);
  stages.push({
    kind: "action",
    status: "ban",
    target,
    durationMinutes: minutes,
    duration,
  });
  if (config.discord_webhook_url) {
    stages.push({
      kind: "audit",
      status: invalidAuditTokens.length ? "templateError" : "send",
      tokens: invalidAuditTokens,
    });
  }

  return {
    outcome: "action",
    reason: "teamkills",
    kind: "tkBans",
    stages,
    risks,
    target,
    durationMinutes: minutes,
    duration,
    invalidTokens: invalidAuditTokens,
  };
};

export const simulateTrustRule = (kind, config = {}, sample = {}) =>
  kind === "vacBans" ? simulateVac(config, sample) : simulateTk(config, sample);
