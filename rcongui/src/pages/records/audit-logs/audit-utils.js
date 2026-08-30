import dayjs from "dayjs";

export const AUDIT_CATEGORIES = [
  { id: "all", labelKey: "all" },
  { id: "moderation", labelKey: "moderation" },
  { id: "maps", labelKey: "maps" },
  { id: "access", labelKey: "access" },
  { id: "settings", labelKey: "settings" },
  { id: "system", labelKey: "system" },
];

const ACTION_META = {
  message_player: { labelKey: "messagePlayer", category: "moderation" },
  punish: { labelKey: "punishPlayer", category: "moderation" },
  punish_player: { labelKey: "punishPlayer", category: "moderation" },
  kick: { labelKey: "kickPlayer", category: "moderation" },
  kick_player: { labelKey: "kickPlayer", category: "moderation" },
  temp_ban: { labelKey: "tempBanPlayer", category: "moderation" },
  temp_ban_player: { labelKey: "tempBanPlayer", category: "moderation" },
  perma_ban: { labelKey: "permaBanPlayer", category: "moderation" },
  perma_ban_player: { labelKey: "permaBanPlayer", category: "moderation" },
  disband_squad: { labelKey: "disbandSquad", category: "moderation" },
  disband_squad_by_name: { labelKey: "disbandSquad", category: "moderation" },
  switch_player_now: { labelKey: "switchPlayer", category: "moderation" },
  set_map: { labelKey: "changeMap", category: "maps" },
  change_map: { labelKey: "changeMap", category: "maps" },
  set_next_map: { labelKey: "setNextMap", category: "maps" },
  set_map_rotation: { labelKey: "changeRotation", category: "maps" },
  add_map_to_rotation: { labelKey: "changeRotation", category: "maps" },
  remove_map_from_rotation: { labelKey: "changeRotation", category: "maps" },
  add_vip: { labelKey: "addVip", category: "access" },
  remove_vip: { labelKey: "removeVip", category: "access" },
  add_admin: { labelKey: "addAdmin", category: "access" },
  add_admin_roles: { labelKey: "addAdmin", category: "access" },
  remove_admin: { labelKey: "removeAdmin", category: "access" },
  remove_admin_roles: { labelKey: "removeAdmin", category: "access" },
  set_autobalance_threshold: {
    labelKey: "changeAutobalance",
    category: "settings",
  },
  set_welcome_message: { labelKey: "changeWelcome", category: "settings" },
  clear_cache: { labelKey: "clearCache", category: "system" },
  clear_crcon_cache: { labelKey: "clearCache", category: "system" },
  restart_webserver: { labelKey: "restartService", category: "system" },
  toggle_service: { labelKey: "toggleService", category: "system" },
};

const SENSITIVE_KEY =
  /password|passwd|passphrase|secret|token|api[_-]?key|authorization|cookie|session|credential|webhook.*url|rcon[_-]?password/i;

export const safeParse = (value, fallback = null) => {
  if (value === null || value === undefined || value === "") return fallback;
  if (typeof value === "object") return value;
  try {
    return JSON.parse(value);
  } catch (error) {
    return fallback;
  }
};

export const maskSensitiveValues = (value) => {
  if (Array.isArray(value)) return value.map(maskSensitiveValues);
  if (!value || typeof value !== "object") return value;

  return Object.entries(value).reduce((masked, [key, child]) => {
    masked[key] = SENSITIVE_KEY.test(key)
      ? "••••••"
      : maskSensitiveValues(child);
    return masked;
  }, {});
};

const normalizeCommand = (command) =>
  String(command || "unknown").toLowerCase();

export const getAuditCategory = (command) => {
  const normalized = normalizeCommand(command);
  if (ACTION_META[normalized]) return ACTION_META[normalized].category;
  if (/map|rotation|votemap|objective/.test(normalized)) return "maps";
  if (/vip|admin|role|permission/.test(normalized)) return "access";
  if (
    /message|punish|kick|ban|blacklist|disband|switch_player/.test(normalized)
  ) {
    return "moderation";
  }
  if (/cache|restart|service|worker|raw_command/.test(normalized))
    return "system";
  if (/config|setting|threshold|welcome|broadcast|set_/.test(normalized)) {
    return "settings";
  }
  return "system";
};

export const getAuditActionLabel = (command, t) => {
  const normalized = normalizeCommand(command);
  const meta = ACTION_META[normalized];
  if (!meta) return t("records.auditLogs.actions.administrativeAction");
  return t(`records.auditLogs.actions.${meta.labelKey}`);
};

export const getAuditStatus = (log) => {
  const raw = String(log?.command_result || "").trim();
  const parsed = safeParse(raw);
  const forwardResults = Array.isArray(parsed?.forward_results)
    ? parsed.forward_results
    : [];
  const forwardFailures = forwardResults.filter(
    (result) =>
      result?.failed === true ||
      result?.success === false ||
      result?.result === false ||
      Boolean(result?.error)
  );

  if (
    forwardFailures.length > 0 &&
    forwardFailures.length < forwardResults.length
  ) {
    return "partial";
  }

  const errorValue = parsed?.error;
  const explicitFailure =
    parsed?.failed === true ||
    parsed?.result === false ||
    (forwardFailures.length === forwardResults.length &&
      forwardResults.length > 0) ||
    (errorValue !== null && errorValue !== undefined && errorValue !== "");

  if (
    explicitFailure ||
    (parsed === null && /traceback|exception|\berror\b|failed/i.test(raw))
  ) {
    return "failed";
  }

  if (parsed?.failed === false || /^ok$/i.test(raw)) {
    return "success";
  }

  return "unknown";
};

const firstValue = (object, keys) => {
  for (const key of keys) {
    const value = object?.[key];
    if (value !== null && value !== undefined && value !== "") return value;
  }
  return null;
};

export const getAuditTarget = (argumentsValue, t) => {
  const args = argumentsValue || {};
  const label = firstValue(args, [
    "player_name",
    "target_name",
    "squad_name",
    "unit_name",
    "map_name",
    "map",
    "server_name",
    "service_name",
    "blacklist_name",
    "config_name",
    "name",
  ]);
  const id = firstValue(args, [
    "player_id",
    "steam_id_64",
    "target_id",
    "player_steam_id",
  ]);

  if (label) return { label: String(label), id: id ? String(id) : null };
  if (id) return { label: t("records.auditLogs.playerTarget"), id: String(id) };
  return { label: t("records.auditLogs.serverWide"), id: null };
};

export const getAuditEntryView = (log, t) => {
  const parsedArguments = maskSensitiveValues(
    safeParse(log?.command_arguments, { value: log?.command_arguments || "" })
  );
  const parsedResult = maskSensitiveValues(
    safeParse(log?.command_result, { value: log?.command_result || "" })
  );

  return {
    ...log,
    key: String(
      log?.id || `${log?.creation_time}-${log?.username}-${log?.command}`
    ),
    category: getAuditCategory(log?.command),
    actionLabel: getAuditActionLabel(log?.command, t),
    status: getAuditStatus(log),
    target: getAuditTarget(parsedArguments, t),
    arguments: parsedArguments,
    result: parsedResult,
  };
};

export const getAuditCategoryCounts = (entries) =>
  entries.reduce(
    (counts, entry) => {
      counts.all += 1;
      counts[entry.category] = (counts[entry.category] || 0) + 1;
      return counts;
    },
    { all: 0, moderation: 0, maps: 0, access: 0, settings: 0, system: 0 }
  );

export const groupAuditEntriesByDate = (entries) => {
  const groups = new Map();
  entries.forEach((entry) => {
    const date = dayjs(entry.creation_time);
    const key = date.isValid() ? date.format("YYYY-MM-DD") : "unknown";
    if (!groups.has(key)) groups.set(key, []);
    groups.get(key).push(entry);
  });
  return [...groups.entries()].map(([date, items]) => ({ date, items }));
};

export const formatTechnicalData = (value) =>
  JSON.stringify(value ?? {}, null, 2);
