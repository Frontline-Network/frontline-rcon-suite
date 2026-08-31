import assert from "node:assert/strict";
import { buildLiveBalanceStatus } from "../src/pages/views/team/live-balance.mjs";

const player = (id, level, role = "rifleman") => ({
  player_id: id,
  name: id,
  level,
  role,
  kills: 0,
  combat: 0,
  offense: 0,
  defense: 0,
  support: 0,
});

const team = (type, players) => ({
  commander: null,
  squads: {
    squad: { type, players },
  },
});

const status = buildLiveBalanceStatus({
  fail_count: 0,
  allies: team("infantry", [
    player("allies-leader", 20, "officer"),
    player("allies-low", 30),
    player("allies-mid", 40),
  ]),
  axis: team("infantry", [
    player("axis-leader", 400, "officer"),
    player("axis-high", 350),
    player("axis-mid", 300),
  ]),
});

assert.equal(status.source, "current_server_snapshot");
assert.deepEqual(status.team_counts, { allies: 3, axis: 3 });
assert.ok(status.data_confidence >= 0.65);
assert.ok(status.strength_swap, "an immediate level-based swap is expected");
assert.notEqual(status.strength_swap.stronger_player.player_id, "axis-leader");
assert.notEqual(status.strength_swap.weaker_player.player_id, "allies-leader");

const countStatus = buildLiveBalanceStatus({
  allies: team("infantry", [
    player("a1", 100),
    player("a2", 90),
    player("a3", 80),
    player("a4", 70),
  ]),
  axis: team("infantry", [player("b1", 100)]),
});

assert.equal(countStatus.required_switches, 1);
assert.equal(countStatus.plan.target_team, "axis");
assert.ok(countStatus.proposal, "a live move candidate is expected");

console.log("Live balance assistant contract passed.");
