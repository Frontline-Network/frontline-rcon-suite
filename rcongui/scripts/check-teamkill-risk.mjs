import assert from "node:assert/strict";

import {
  getTeamkillCount,
  getTeamkillRisk,
  TEAMKILL_RISK_THRESHOLDS,
} from "../src/utils/teamkill-risk.mjs";

assert.equal(getTeamkillCount({ team_kills: 2 }), 2, "HLL field is supported");
assert.equal(getTeamkillCount({ teamkills: 3 }), 3, "HLLV/legacy field is supported");
assert.equal(getTeamkillCount({ team_kills: "2.9" }), 2);
assert.equal(getTeamkillCount({ team_kills: -1 }), 0);
assert.equal(getTeamkillCount({ team_kills: "unknown" }), 0);

assert.deepEqual(getTeamkillRisk({ team_kills: 0 }), {
  count: 0,
  level: "none",
});
assert.deepEqual(getTeamkillRisk({ teamkills: 1 }), {
  count: 1,
  level: "caution",
});
assert.deepEqual(getTeamkillRisk({ team_kills: 3 }), {
  count: 3,
  level: "high",
});
assert.deepEqual(
  getTeamkillRisk({ team_kills: 2 }, { caution: 2, high: 5 }),
  { count: 2, level: "caution" },
  "thresholds remain explicit and configurable"
);
assert.deepEqual(TEAMKILL_RISK_THRESHOLDS, { caution: 1, high: 3 });

console.log("Teamkill risk contract passed for HLL and HLL Vietnam payloads.");
