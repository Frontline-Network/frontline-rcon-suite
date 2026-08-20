import assert from "node:assert/strict";

import { resolveTimerSettings } from "../src/pages/settings/general-group/game/timer-capabilities.mjs";

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
assert.deepEqual(Object.keys(hll.match), ["warfare", "offensive", "skirmish"]);
assert.deepEqual(Object.keys(hll.warmup), ["warfare", "skirmish"]);

const hllv = resolveTimerSettings({
  game: "hllv",
  supported_game_modes: ["warfare", "offensive", "conquest", "domination"],
  game_capabilities: {
    match_timer_modes: ["warfare", "offensive"],
    warmup_timer_modes: ["warfare"],
  },
});
assert.deepEqual(Object.keys(hllv.match), ["warfare", "offensive"]);
assert.deepEqual(Object.keys(hllv.warmup), ["warfare"]);
assert.equal(hllv.match.skirmish, undefined);
assert.equal(hllv.match.domination, undefined);

const legacyHllv = resolveTimerSettings({ game: "hll_vietnam" });
assert.deepEqual(Object.keys(legacyHllv.match), ["warfare", "offensive"]);
assert.deepEqual(Object.keys(legacyHllv.warmup), ["warfare"]);

const defensive = resolveTimerSettings({
  game: "hllv",
  supported_game_modes: ["warfare"],
  game_capabilities: {
    match_timer_modes: ["warfare", "skirmish", "future_mode"],
    warmup_timer_modes: ["future_mode"],
  },
});
assert.deepEqual(Object.keys(defensive.match), ["warfare"]);
assert.deepEqual(defensive.warmup, {});

console.log("Game timer capability contract passed for HLL and HLL Vietnam.");
