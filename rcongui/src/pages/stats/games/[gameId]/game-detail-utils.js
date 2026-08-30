export const normalizeHistoricalTeam = (team) => {
  if (typeof team === "string") {
    const normalized = team.trim().toLowerCase();
    return normalized === "allies" || normalized === "axis"
      ? normalized
      : "unknown";
  }

  if (team && typeof team === "object") {
    const side = String(team.side ?? "")
      .trim()
      .toLowerCase();
    if (side !== "allies" && side !== "axis") return "unknown";

    const confidence = String(team.confidence ?? "")
      .trim()
      .toLowerCase();
    return confidence && confidence !== "strong" ? "mixed" : side;
  }

  return "unknown";
};

export const getHistoricalRole = (player) => {
  const role = typeof player?.role === "string" ? player.role.trim() : "";
  return role || null;
};

export const getHistoricalSquad = (player) => {
  const squad = typeof player?.unit === "string" ? player.unit.trim() : "";
  return squad || null;
};

export const getHistoricalPlayerLabel = (player) =>
  player?.player || player?.player_id || "–";
