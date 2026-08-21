/**
 * Central, explicit moderation thresholds for the live player list.
 * Consumers can pass another threshold set for a future server policy without
 * changing rendering code.
 */
export const TEAMKILL_RISK_THRESHOLDS = Object.freeze({
  caution: 1,
  high: 3,
});

export const getTeamkillCount = (value) => {
  const rawValue =
    value && typeof value === "object"
      ? value.team_kills ?? value.teamkills ?? 0
      : value;
  const parsed = Number(rawValue);

  return Number.isFinite(parsed) ? Math.max(0, Math.trunc(parsed)) : 0;
};

export const getTeamkillRisk = (
  value,
  thresholds = TEAMKILL_RISK_THRESHOLDS
) => {
  const count = getTeamkillCount(value);

  if (count >= thresholds.high) {
    return { count, level: "high" };
  }
  if (count >= thresholds.caution) {
    return { count, level: "caution" };
  }
  return { count, level: "none" };
};
