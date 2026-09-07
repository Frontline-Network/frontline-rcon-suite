import assert from "node:assert/strict";
import test from "node:test";
import { killConnection, visibleKillConnections } from "./kill-events.mjs";

const event = (overrides = {}) => ({
  id: "kill-1",
  time: 100,
  attacker: "attacker",
  victim: "victim",
  attacker_map_position: { x: 0.2, y: 0.3 },
  attacker_position_sample_at: 98,
  map_position: { x: 0.7, y: 0.8 },
  position_sample_at: 99,
  ...overrides,
});

test("connects fresh measured attacker and victim positions", () => {
  assert.deepEqual(killConnection(event()), {
    from: { x: 0.2, y: 0.3 },
    to: { x: 0.7, y: 0.8 },
  });
});

test("does not invent a connection for missing or stale positions", () => {
  assert.equal(killConnection(event({ attacker_map_position: null })), null);
  assert.equal(killConnection(event({ position_sample_at: 96 })), null);
  assert.equal(
    killConnection(event({ attacker_position_sample_at: 101 })),
    null
  );
});

test("selection limits connections unless all kills are requested", () => {
  const values = [
    event(),
    event({ id: "kill-2", attacker: "other", victim: "another" }),
  ];
  assert.deepEqual(
    visibleKillConnections({ events: values, at: 101, selected: "victim" }).map(
      (item) => item.id
    ),
    ["kill-1"]
  );
  assert.equal(
    visibleKillConnections({
      events: values,
      at: 101,
      selected: "victim",
      showAll: true,
    }).length,
    2
  );
});

test("deduplicates events and caps the visible effect count", () => {
  const values = Array.from({ length: 20 }, (_, index) =>
    event({
      id: `kill-${index}`,
      time: 80 + index,
      attacker_position_sample_at: 79 + index,
      position_sample_at: 79 + index,
    })
  );
  values.push(values.at(-1));
  const result = visibleKillConnections({
    events: values,
    at: 100,
    windowSeconds: 30,
    limit: 12,
  });
  assert.equal(result.length, 12);
  assert.equal(result.at(-1).id, "kill-19");
});
