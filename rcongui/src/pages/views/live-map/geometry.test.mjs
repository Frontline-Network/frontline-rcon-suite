import assert from "node:assert/strict";
import test from "node:test";
import {
  mapArtworkBounds,
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

test("Vietnam artwork places Cam Ranh US HQ 1 at its recorded world position", () => {
  const matrix = [0.000005, 0, 0.5, 0, 0.000005, 0.5];
  for (const revision of ["hllv-field-grid-20260905-v1", "hllv-display-preview-20260905-v2"]) {
    const calibration = { verified: false, revision, matrix };
    const b = mapArtworkBounds("hq.svg", calibration);
    const x = b.x + b.width * 96.33091187259843 / 2280;
    const y = b.y + b.height * 643.2531686445668 / 2280;
    assert.ok(Math.abs(x - 1000 * (0.5 - 90863.29561109176 * matrix[0])) < 1e-9);
    assert.ok(Math.abs(y - 1000 * (0.5 - 43247.476326339245 * matrix[4])) < 1e-9);
    const full = { x: 0, y: 0, width: 1000, height: 1000 };
    assert.deepEqual(mapArtworkBounds(null, calibration), full);
    assert.deepEqual(mapArtworkBounds("hq.svg", null), full);
    assert.deepEqual(mapArtworkBounds("hq.svg", { ...calibration, verified: true }), full);
    assert.deepEqual(mapArtworkBounds("hq.svg", { ...calibration, revision: "custom" }), full);
    assert.deepEqual(mapArtworkBounds("hq.svg", { ...calibration, matrix: [1,0,0,0,1,0] }), full);
  }
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
