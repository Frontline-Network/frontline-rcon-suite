import dayjs from "dayjs";
import { isLeader, normalizePlayerProfile } from "@/utils/lib";

export const normalizeLiveTeam = (team) => {
  const value = String(team ?? "").toLowerCase();
  if (value === "axis" || value === "allies") return value;
  return "unassigned";
};

const normalizePlayer = (player, context) => ({
  ...player,
  profile: normalizePlayerProfile(player?.profile),
  team: normalizeLiveTeam(player?.team ?? context.team),
  faction: player?.faction ?? player?.team ?? context.team,
  unit_name: player?.unit_name ?? context.unitName,
  squad_type: player?.type ?? context.squadType,
  has_leader: context.hasLeader,
  is_leaderless_squad: context.isLeaderlessSquad,
  squad_key: `${context.team}:${context.unitName}`,
});

export const flattenLiveSessionPlayers = (data) => {
  if (!data) return [];

  return ["allies", "axis", "unassigned"].flatMap((team) => {
    const teamData = data?.[team];
    if (!teamData) return [];

    const squadPlayers = Object.entries(teamData.squads ?? {}).flatMap(
      ([unitName, squad]) => {
        const players = squad?.players ?? [];
        const hasLeader =
          typeof squad?.has_leader === "boolean"
            ? squad.has_leader
            : players.some((player) => isLeader(player.role));
        const isLeaderlessSquad =
          team !== "unassigned" &&
          unitName !== "unassigned" &&
          players.length > 0 &&
          !hasLeader;

        return players.map((player) =>
          normalizePlayer(player, {
            team,
            unitName,
            squadType: squad?.type,
            hasLeader,
            isLeaderlessSquad,
          })
        );
      }
    );

    const commander = teamData.commander
      ? [
          normalizePlayer(teamData.commander, {
            team,
            unitName: "command",
            squadType: "armycommander",
            hasLeader: true,
            isLeaderlessSquad: false,
          }),
        ]
      : [];

    return [...commander, ...squadPlayers];
  });
};

export const getPlayerSessionSeconds = (player) =>
  Number(
    player?.map_playtime_seconds ??
      player?.current_playtime_seconds ??
      player?.profile?.current_playtime_seconds ??
      0
  ) || 0;

export const formatSessionDuration = (seconds) =>
  dayjs
    .duration(Math.max(0, Number(seconds) || 0), "seconds")
    .format("H:mm:ss");

export const getPlayerKdr = (player) => {
  const kills = Number(player?.kills) || 0;
  const deaths = Number(player?.deaths) || 0;
  return deaths > 0 ? kills / deaths : kills;
};

export const getLiveSessionRowId = (player) =>
  String(
    player?.player_id ||
      `${player?.team ?? "unknown"}:${player?.unit_name ?? "unknown"}:${
        player?.name ?? "player"
      }`
  );

export const getRoleLabel = (t, role) =>
  t(`stats.liveSessions.roles.${role || "unknown"}`, {
    defaultValue: role || t("stats.liveSessions.unknown"),
  });

export const getTeamLabel = (t, team) =>
  t(`stats.liveSessions.teams.${normalizeLiveTeam(team)}`);

export const liveSessionGlobalFilter = (row, _columnId, value) => {
  const search = String(value ?? "")
    .trim()
    .toLowerCase();
  if (!search) return true;
  const player = row.original;
  return [
    player?.name,
    player?.player_id,
    player?.unit_name,
    player?.role,
    player?.team,
  ].some((field) =>
    String(field ?? "")
      .toLowerCase()
      .includes(search)
  );
};
