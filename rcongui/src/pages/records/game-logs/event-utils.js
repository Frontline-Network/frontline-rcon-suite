import dayjs from "dayjs";
import utcPlugin from "dayjs/plugin/utc";
import timezonePlugin from "dayjs/plugin/timezone";

dayjs.extend(utcPlugin);
dayjs.extend(timezonePlugin);

export const EVENT_CATEGORIES = [
  { id: "all", labelKey: "all" },
  { id: "admin", labelKey: "admin" },
  { id: "chat", labelKey: "chat" },
  { id: "kills", labelKey: "kills" },
  { id: "teamkills", labelKey: "teamkills" },
  { id: "connections", labelKey: "connections" },
  { id: "round", labelKey: "round" },
];

export const getEventCategory = (type = "") => {
  const normalized = String(type).toUpperCase();

  if (normalized.includes("TEAM KILL") || normalized.includes("TEAMKILL")) {
    return "teamkills";
  }
  if (normalized === "KILL") return "kills";
  if (normalized.startsWith("CHAT") || normalized === "MESSAGE") return "chat";
  if (normalized.startsWith("ADMIN") || normalized.startsWith("TK AUTO")) {
    return "admin";
  }
  if (["CONNECTED", "DISCONNECTED", "TEAMSWITCH"].includes(normalized)) {
    return "connections";
  }
  if (normalized.startsWith("MATCH") || normalized === "ROUND") return "round";

  return "other";
};

export const getEventLabel = (type = "", t) => {
  const normalized = String(type).toUpperCase();
  const category = getEventCategory(normalized);

  if (category === "teamkills")
    return t("records.gameLogs.timeline.eventLabels.teamkill");
  if (category === "kills")
    return t("records.gameLogs.timeline.eventLabels.kill");
  if (category === "connections") {
    return normalized === "DISCONNECTED"
      ? t("records.gameLogs.timeline.eventLabels.disconnected")
      : t("records.gameLogs.timeline.eventLabels.connected");
  }
  if (category === "chat") {
    if (normalized.includes("TEAM"))
      return t("records.gameLogs.timeline.eventLabels.teamChat");
    if (normalized.includes("UNIT"))
      return t("records.gameLogs.timeline.eventLabels.unitChat");
    return t("records.gameLogs.timeline.eventLabels.chat");
  }
  if (category === "admin")
    return t("records.gameLogs.timeline.eventLabels.admin");
  if (category === "round")
    return t("records.gameLogs.timeline.eventLabels.round");

  return normalized || t("records.gameLogs.timeline.eventLabels.other");
};

export const removePlayerIds = (message = "") =>
  String(message)
    .replace(/\((?:(?:Axis|Allies)\/)?(?:[0-9]{17}|[A-Z0-9]{16})\)/gi, "")
    .replace(/\s{2,}/g, " ")
    .trim();

export const formatEventTime = (value, format = "HH:mm:ss.SSS") => {
  if (!value) return "–";
  return dayjs
    .utc(value)
    .tz(Intl.DateTimeFormat().resolvedOptions().timeZone)
    .format(format);
};

export const buildEventSummary = (log, t) => {
  const category = getEventCategory(log.type);
  const cleanContent = removePlayerIds(log.content);
  const actor = log.player1_name || t("records.gameLogs.timeline.system");
  const target = log.player2_name;

  if ((category === "kills" || category === "teamkills") && target) {
    return [actor, "→", target, log.weapon].filter(Boolean).join(" · ");
  }

  if (category === "connections") {
    return log.type === "DISCONNECTED"
      ? t("records.gameLogs.timeline.playerLeft", { player: actor })
      : t("records.gameLogs.timeline.playerJoined", { player: actor });
  }

  if (category === "chat") {
    const message = cleanContent.replace(
      new RegExp(`^${actor.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")}\\s*:\\s*`),
      ""
    );
    return `${actor} · ${message || cleanContent}`;
  }

  return cleanContent || [actor, target].filter(Boolean).join(" → ");
};

export const filterLogsByCategory = (logs, category) => {
  if (!category || category === "all") return logs;
  return logs.filter((log) => getEventCategory(log.type) === category);
};

export const getCategoryCounts = (logs) =>
  logs.reduce(
    (counts, log) => {
      const category = getEventCategory(log.type);
      counts[category] = (counts[category] || 0) + 1;
      counts.all += 1;
      return counts;
    },
    {
      all: 0,
      admin: 0,
      chat: 0,
      kills: 0,
      teamkills: 0,
      connections: 0,
      round: 0,
      other: 0,
    }
  );

export const getTopPlayers = (logs, limit = 5) => {
  const counts = new Map();
  logs.forEach((log) => {
    [log.player1_name, log.player2_name].filter(Boolean).forEach((name) => {
      counts.set(name, (counts.get(name) || 0) + 1);
    });
  });

  return [...counts.entries()]
    .sort((a, b) => b[1] - a[1])
    .slice(0, limit)
    .map(([name, count]) => ({ name, count }));
};

export const getRoundWindow = (logs) => {
  const validTimes = logs
    .map((log) => dayjs(log.event_time))
    .filter((value) => value.isValid())
    .sort((a, b) => a.valueOf() - b.valueOf());

  if (!validTimes.length) return { start: null, end: null, duration: "–" };

  const start = validTimes[0];
  const end = validTimes[validTimes.length - 1];
  const durationSeconds = Math.max(0, end.diff(start, "second"));
  const hours = Math.floor(durationSeconds / 3600);
  const minutes = Math.floor((durationSeconds % 3600) / 60);
  const seconds = durationSeconds % 60;

  return {
    start,
    end,
    duration: [hours, minutes, seconds]
      .map((part) => String(part).padStart(2, "0"))
      .join(":"),
  };
};
