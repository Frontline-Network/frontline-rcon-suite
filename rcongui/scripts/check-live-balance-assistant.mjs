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

const squadStatus = buildLiveBalanceStatus(
  {
    allies: {
      commander: null,
      squads: {
        Able: {
          type: "infantry",
          players: [player("able-1", 90), player("able-2", 85)],
        },
        Baker: {
          type: "infantry",
          players: [player("baker-1", 80), player("baker-2", 75)],
        },
        Charlie: {
          type: "infantry",
          players: [player("charlie-1", 70), player("charlie-2", 65)],
        },
      },
    },
    axis: team("infantry", [player("axis-1", 60), player("axis-2", 55)]),
  },
  {
    targetDifference: 2,
    coordinatedSquadSwitchesEnabled: true,
    allowIndividualSquadFallback: false,
  }
);

assert.equal(squadStatus.required_switches, 1);
assert.equal(squadStatus.coordinated_squad_switches_enabled, true);
assert.equal(squadStatus.proposal, null, "individual fallback stays disabled");
assert.equal(squadStatus.squad_recommendation.kind, "squad_move");
assert.equal(squadStatus.squad_recommendation.member_count, 2);
assert.equal(squadStatus.squad_recommendation.projected_count_difference, 0);
assert.equal(squadStatus.squad_recommendation.moves[0].player_ids.length, 2);

console.log("Live balance assistant contract passed.");
