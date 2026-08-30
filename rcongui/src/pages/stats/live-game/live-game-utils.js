import dayjs from "dayjs";

const numberOrZero = (value) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : 0;
};

export const normalizeLiveGameTeam = (team) => {
  const raw = typeof team === "object" ? team?.side : team;
  const normalized = String(raw ?? "").toLowerCase();
  if (normalized === "allies" || normalized === "axis") return normalized;
  return "unknown";
};

export const normalizeLiveGamePlayer = (player = {}, index = 0) => {
  const kills = numberOrZero(player.kills);
  const deaths = numberOrZero(player.deaths);
  const seconds = numberOrZero(player.time_seconds ?? player.time);

  return {
    ...player,
    player_id: String(player.player_id ?? `unknown-${index}`),
    player: player.player ?? player.name ?? player.names?.[0] ?? "–",
    team: normalizeLiveGameTeam(player.team),
    faction: player.faction ?? normalizeLiveGameTeam(player.team),
    status: player.status ?? "unknown",
    kills,
    deaths,
    teamkills: numberOrZero(player.teamkills),
    teamkills_streak: numberOrZero(player.teamkills_streak),
    deaths_by_tk: numberOrZero(player.deaths_by_tk),
    deaths_by_tk_streak: numberOrZero(player.deaths_by_tk_streak),
    kills_streak: numberOrZero(player.kills_streak),
    kills_per_minute: numberOrZero(player.kills_per_minute),
    kill_death_ratio: Number.isFinite(Number(player.kill_death_ratio))
      ? Number(player.kill_death_ratio)
      : deaths > 0
        ? kills / deaths
        : kills,
    time_seconds: seconds,
    combat: numberOrZero(player.combat),
    offense: numberOrZero(player.offense),
    defense: numberOrZero(player.defense),
    support: numberOrZero(player.support),
    level: numberOrZero(player.level),
    most_killed: player.most_killed ?? {},
    death_by: player.death_by ?? {},
    weapons: player.weapons ?? {},
    death_by_weapons: player.death_by_weapons ?? {},
    steaminfo: player.steaminfo ?? null,
  };
};

export const unwrapPublicLayer = (value) => {
  if (!value) return null;
  if (value.game_mode || value.pretty_name) return value;
  return value.map ?? null;
};

export const getLayerLabel = (value) => {
  const layer = unwrapPublicLayer(value);
  return layer?.pretty_name ?? layer?.map?.pretty_name ?? layer?.name ?? "–";
};

export const getLayerMode = (value) => {
  const layer = unwrapPublicLayer(value);
  return layer?.game_mode ? String(layer.game_mode).toUpperCase() : "–";
};

export const formatMatchDuration = (seconds, withSeconds = true) =>
  dayjs
    .duration(Math.max(0, numberOrZero(seconds)), "seconds")
    .format(withSeconds ? "H:mm:ss" : "H:mm");

export const getSnapshotAge = (timestamp) => {
  const raw = Number(timestamp);
  if (!Number.isFinite(raw) || raw <= 0) return null;
  const milliseconds = raw < 1e12 ? raw * 1000 : raw;
  return Math.max(0, Date.now() - milliseconds);
};

export const isSnapshotStale = (payload) => {
  const age = getSnapshotAge(payload?.snapshot_timestamp);
  if (age === null) return false;
  const interval = Math.max(15, numberOrZero(payload?.refresh_interval_sec));
  return age > Math.max(30000, interval * 2000);
};

export const getTeamSummary = (players) => {
  const totals = players.reduce(
    (accumulator, player) => {
      accumulator.kills += player.kills;
      accumulator.deaths += player.deaths;
      accumulator.teamkills += player.teamkills;
      accumulator.online += player.status === "online" ? 1 : 0;
      return accumulator;
    },
    { kills: 0, deaths: 0, teamkills: 0, online: 0 }
  );

  return {
    ...totals,
    kdr: totals.deaths > 0 ? totals.kills / totals.deaths : totals.kills,
  };
};

export const getPlayerSearchText = (player) =>
  [
    player.player,
    player.player_id,
    player.steaminfo?.country,
    player.status,
    player.faction,
  ]
    .filter(Boolean)
    .join(" ")
    .toLowerCase();

export const sortLiveGamePlayers = (players, sortKey, descending = true) => {
  const sorted = [...players].sort((left, right) => {
    if (sortKey === "player") {
      return String(left.player).localeCompare(String(right.player));
    }
    return numberOrZero(left[sortKey]) - numberOrZero(right[sortKey]);
  });
  return descending ? sorted.reverse() : sorted;
};

export const getTopEntries = (value, playerNames, limit = 3) =>
  Object.entries(value ?? {})
    .map(([key, count]) => ({
      key,
      label: playerNames?.get(key) ?? key,
      count: numberOrZero(count),
    }))
    .filter((entry) => entry.count > 0)
    .sort((left, right) => right.count - left.count)
    .slice(0, limit);
