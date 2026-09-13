import assert from "node:assert/strict";
import test from "node:test";
import {
  buildLiveBalanceStatus,
  validateLiveRecommendation,
} from "./live-balance.mjs";
import {
  balanceRecommendations,
  holdRecommendations,
  preferRecommendation,
  recommendationKey,
  recommendationStatus,
} from "./balance-recommendations.mjs";
import { balanceActionPreflight } from "./balance-action-guard.mjs";

const player = (id, level) => ({
  player_id: id,
  name: id,
  level,
  role: "rifleman",
});
const team = (players) => ({
  squads: Object.fromEntries(
    players.map((p) => [p.player_id, { type: "infantry", players: [p] }])
  ),
});
const teams = () => ({
  allies: team([
    player("a1", 300),
    player("a2", 200),
    player("a3", 100),
    player("a4", 50),
    player("a5", 30),
  ]),
  axis: team([player("b1", 20)]),
});
const choice = (snapshot, settings = {}) =>
  balanceRecommendations(buildLiveBalanceStatus(snapshot, settings))[0];

test("keeps the exact choice for 60 seconds, then adopts the latest proposal", () => {
  const first = choice(teams());
  const second = {
    ...first,
    player: { ...first.player, player_id: "another" },
  };
  const held = holdRecommendations(null, [first], 1000);
  assert.equal(holdRecommendations(held, [second], 60_999), held);
  assert.equal(holdRecommendations(held, [], 20_000), held);
  assert.deepEqual(holdRecommendations(held, [second], 61_000).items, [second]);
  assert.deepEqual(holdRecommendations(held, [], 61_000).items, []);
});

test("an open review never changes players when the hold expires", () => {
  const held = holdRecommendations(null, [choice(teams())], 1000);
  assert.equal(holdRecommendations(held, [], 180_000, true), held);
  assert.deepEqual(holdRecommendations(held, [], 180_000, false).items, []);
});

test("a valid player remains selectable after their ranking changes", () => {
  const snapshot = teams();
  const selected = choice(snapshot);
  snapshot.allies.squads[selected.player.player_id].players[0].level = 0;
  assert.notEqual(
    recommendationKey(choice(snapshot)),
    recommendationKey(selected)
  );
  const refreshed = validateLiveRecommendation(snapshot, {}, selected);
  assert.equal(recommendationKey(refreshed), recommendationKey(selected));
  assert.notDeepEqual(
    refreshed.projected_team_ratings,
    selected.projected_team_ratings
  );
});

test("preferred choices are recovered before limiting alternatives to the top 3", () => {
  const base = choice(teams());
  const values = Array.from({ length: 6 }, (_, i) => ({
    ...base,
    player: { ...base.player, player_id: String(i) },
  }));
  assert.equal(preferRecommendation(values, values[5])[0], values[5]);
  assert.equal(values[0].player.player_id, "0");
});

test("leaving, switching, protected roles, incomplete data and disabled fallback invalidate a held player", () => {
  for (const change of [
    (snapshot, id) => {
      delete snapshot.allies.squads[id];
    },
    (snapshot, id) => {
      snapshot.axis.squads[id] = snapshot.allies.squads[id];
      delete snapshot.allies.squads[id];
    },
    (snapshot, id) => {
      snapshot.allies.squads[id].players[0].role = "officer";
    },
    (snapshot, id) => {
      snapshot.allies.squads[id].type = "armor";
    },
    (snapshot) => {
      snapshot.fail_count = 1;
    },
  ]) {
    const snapshot = teams();
    const selected = choice(snapshot);
    change(snapshot, selected.player.player_id);
    assert.equal(validateLiveRecommendation(snapshot, {}, selected), null);
  }
  const snapshot = teams();
  assert.equal(
    validateLiveRecommendation(
      snapshot,
      { allowIndividualSquadFallback: false },
      choice(snapshot)
    ),
    null
  );
});

test("squad membership changes cannot silently change the reviewed recipients", () => {
  const snapshot = teams();
  snapshot.allies = {
    squads: {
      able: {
        type: "infantry",
        players: [player("a1", 300), player("a2", 200)],
      },
      baker: {
        type: "infantry",
        players: [player("a3", 100), player("a4", 50), player("a5", 30)],
      },
    },
  };
  const selected = choice(snapshot);
  assert.equal(selected.kind, "squad_move");
  assert.ok(validateLiveRecommendation(snapshot, {}, selected));
  snapshot.allies.squads[selected.moves[0].squad_name].players.push(
    player("new", 99)
  );
  assert.equal(validateLiveRecommendation(snapshot, {}, selected), null);
});

test("projections retain the real direction after an overcorrecting swap", () => {
  const snapshot = {
    allies: team([player("high", 400), player("mid", 300)]),
    axis: team([player("low", 30), player("lowest", 20)]),
  };
  const selected = {
    kind: "strength_swap",
    stronger_team: "allies",
    weaker_team: "axis",
    stronger_player: { player_id: "high" },
    weaker_player: { player_id: "lowest" },
  };
  const validated = validateLiveRecommendation(snapshot, {}, selected);
  assert.ok(validated);
  assert.ok(
    validated.projected_team_ratings.allies <
      validated.projected_team_ratings.axis
  );
  assert.ok(validated.projected_rating_gap < validated.rating_gap_before);
});

test("no recommendation means no forecast, never a duplicate of the live ratings", () => {
  const status = recommendationStatus(buildLiveBalanceStatus(teams()), []);
  assert.equal(status.plan, null);
  assert.equal(status.strength_swap, null);
  assert.equal(status.squad_recommendation, null);
  assert.ok(status.team_ratings);
});

test("final confirmation reads fresh teams/settings and rejects invalid or edited selections", async () => {
  const snapshot = teams();
  const selected = choice(snapshot);
  const id = selected.player.player_id;
  let reads = 0;
  const preflight = balanceActionPreflight({
    recommendation: selected,
    recipientIds: [id],
    readTeams: async () => {
      reads++;
      return snapshot;
    },
    readSettings: async () => ({}),
  });
  await preflight([{ player_id: id }]);
  assert.equal(reads, 1);
  await assert.rejects(
    preflight([{ player_id: "different" }]),
    /Spielerauswahl/
  );
  snapshot.allies.squads[id].players[0].role = "commander";
  await assert.rejects(preflight([{ player_id: id }]), /nicht mehr gültig/);
  assert.equal(reads, 2);
});

test("final confirmation fails closed when fresh data cannot be loaded", async () => {
  const selected = choice(teams());
  const preflight = balanceActionPreflight({
    recommendation: selected,
    recipientIds: [selected.player.player_id],
    readTeams: async () => {
      throw new Error("Offline");
    },
    readSettings: async () => ({}),
  });
  await assert.rejects(
    preflight([{ player_id: selected.player.player_id }]),
    /Offline/
  );
});
