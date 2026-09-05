import assert from "node:assert/strict";
import test from "node:test";
import {
  filterPlayers,
  frameAt,
  trailSegments,
  projectionReady,
} from "./geometry.mjs";

test("provisional rendering is explicit and distinct from verified calibration", () => {
  assert.equal(projectionReady(null), false);
  assert.equal(projectionReady({ verified: false }), false);
  assert.equal(projectionReady({ display_ready: true }), false);
  assert.equal(projectionReady({ verified: true }), true);
  assert.equal(
    projectionReady({
      verified: false,
      display_ready: true,
      quality: "estimated",
    }),
    true
  );
});

const f = (time, segment, point = { x: 0.1, y: 0.2 }, round = "r") => ({
  captured_at: time,
  round_id: round,
  players: [{ player_id: "p", segment_id: segment, map_position: point }],
});
test("history never displays a future sample", () => {
  assert.equal(frameAt([f(10, "a"), f(20, "a")], 9), null);
  assert.equal(frameAt([f(10, "a"), f(20, "a")], 19).captured_at, 10);
});
test("trails do not bridge deaths, missing samples, or rounds", () => {
  const frames = [
    f(1, "a"),
    f(2, "a"),
    f(3, "a", null),
    f(4, "b"),
    f(5, "b"),
    f(6, "b", undefined, "next"),
  ];
  assert.deepEqual(
    trailSegments(frames, "p", "r", 10).map((line) => line.length),
    [2, 2]
  );
  assert.equal(trailSegments(frames, "p", "r", 1).length, 0);
});
test("search supports player ID and combines team/squad filters", () => {
  const players = [
    { player_id: "123", name: "Alpha", team: "allies", unit_name: "ABLE" },
    { player_id: "456", name: "Beta", team: "axis", unit_name: "BAKER" },
  ];
  assert.deepEqual(filterPlayers(players, "123", "allies", "ABLE"), [
    players[0],
  ]);
  assert.equal(filterPlayers(players, "beta", "allies", "all").length, 0);
});
