import assert from "node:assert/strict";

import { resolveTimerSettings } from "../src/pages/settings/general-group/game/timer-capabilities.mjs";
import { resolveSectorLayoutCapabilities } from "../src/pages/settings/maps/objectives/layout-capabilities.mjs";

const check = (capability, actual, expected) => {
  try {
    assert.deepEqual(actual, expected);
  } catch (error) {
    error.message = `[${capability}] ${error.message}`;
    throw error;
  }
};

const hll = resolveTimerSettings({
  game: "hll",
  supported_game_modes: [
    "warfare",
    "offensive",
    "conquest",
    "skirmish",
    "phased",
    "majority",
  ],
  game_capabilities: {
    match_timer_modes: ["warfare", "offensive", "skirmish"],
    warmup_timer_modes: ["warfare", "skirmish"],
  },
});
check("HLL match timers", Object.keys(hll.match), ["warfare", "offensive", "skirmish"]);
check("HLL warmup timers", Object.keys(hll.warmup), ["warfare", "skirmish"]);

const hllv = resolveTimerSettings({
  game: "hllv",
  supported_game_modes: ["warfare", "offensive", "conquest", "domination"],
  game_capabilities: {
    match_timer_modes: ["warfare", "offensive"],
    warmup_timer_modes: ["warfare"],
  },
});
check("HLLV match timers", Object.keys(hllv.match), ["warfare", "offensive"]);
check("HLLV warmup timers", Object.keys(hllv.warmup), ["warfare"]);
assert.equal(hllv.match.skirmish, undefined);
assert.equal(hllv.match.domination, undefined);

const legacyHllv = resolveTimerSettings({ game: "hll_vietnam" });
check("legacy HLLV match timers", Object.keys(legacyHllv.match), ["warfare", "offensive"]);
check("legacy HLLV warmup timers", Object.keys(legacyHllv.warmup), ["warfare"]);

const defensive = resolveTimerSettings({
  game: "hllv",
  supported_game_modes: ["warfare"],
  game_capabilities: {
    match_timer_modes: ["warfare", "skirmish", "future_mode"],
    warmup_timer_modes: ["future_mode"],
  },
});
check("unsupported HLLV match modes", Object.keys(defensive.match), ["warfare"]);
check("unsupported HLLV warmup modes", defensive.warmup, {});

check(
  "sector layout is supported by HLLV",
  resolveSectorLayoutCapabilities({
    game_capabilities: {
      sector_layout: { read: true, set: true, remove: false },
    },
  }),
  { read: true, set: true, remove: false }
);
check(
  "explicitly unsupported sector layout stays unavailable",
  resolveSectorLayoutCapabilities({
    game_capabilities: {
      sector_layout: { read: false, set: false, remove: false },
    },
  }),
  { read: false, set: false, remove: false }
);
check(
  "legacy sector layout fallback",
  resolveSectorLayoutCapabilities({}),
  { read: true, set: true, remove: false }
);

console.log("Game capability contract passed for HLL and HLL Vietnam.");
