const TIMER_LIMITS = Object.freeze({
  match: Object.freeze({
    warfare: Object.freeze({ min: 30, max: 180, default: 90 }),
    offensive: Object.freeze({ min: 10, max: 60, default: 30 }),
    skirmish: Object.freeze({ min: 10, max: 60, default: 30 }),
  }),
  warmup: Object.freeze({
    warfare: Object.freeze({ min: 1, max: 10, default: 3 }),
    skirmish: Object.freeze({ min: 1, max: 10, default: 3 }),
  }),
});

const normalizeGame = (game) => {
  const value = String(game ?? "")
    .trim()
    .toLowerCase();
  if (["hllv", "hll_vietnam", "vietnam"].includes(value)) return "hllv";
  if (value === "hll") return "hll";
  return null;
};

const legacyModes = (status, timerType) => {
  if (normalizeGame(status?.game) === "hllv") {
    return timerType === "match" ? ["warfare", "offensive"] : ["warfare"];
  }
  return Object.keys(TIMER_LIMITS[timerType]);
};

export const resolveTimerSettings = (status = {}) => {
  const supportedModes = new Set(
    Array.isArray(status.supported_game_modes)
      ? status.supported_game_modes
      : []
  );
  const capabilities = status.game_capabilities || {};

  const resolve = (timerType, capabilityKey) => {
    const declared = Array.isArray(capabilities[capabilityKey])
      ? capabilities[capabilityKey]
      : legacyModes(status, timerType);

    return Object.fromEntries(
      declared
        .filter((mode) => TIMER_LIMITS[timerType][mode])
        .filter((mode) => !supportedModes.size || supportedModes.has(mode))
        .map((mode) => [mode, { ...TIMER_LIMITS[timerType][mode] }])
    );
  };

  return {
    match: resolve("match", "match_timer_modes"),
    warmup: resolve("warmup", "warmup_timer_modes"),
  };
};

export { TIMER_LIMITS };
