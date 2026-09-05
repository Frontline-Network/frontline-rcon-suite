import test from "node:test";
import assert from "node:assert/strict";
import { tacticalPollInterval, sampleAge, sampleIsStale } from "./polling.mjs";

test("age uses server age and local monotonic elapsed time, never wall-clock skew", () => {
  const snapshot = {
    captured_at: 1000,
    age_seconds: 2,
    received_at_monotonic: 20,
    transport_seconds: 0.25,
  };
  assert.equal(sampleAge(snapshot, 23), 5.25);
  assert.equal(sampleAge({ ...snapshot, captured_at: 100000000 }, 23), 5.25);
  assert.equal(sampleAge({ ...snapshot, received_at_monotonic: 24 }, 23), 2.25);
  assert.equal(sampleAge({}, 23), Infinity);
});

test("warning tolerates normal cadence, detects outages and has recovery hysteresis", () => {
  assert.equal(sampleIsStale(7, 2), false);
  assert.equal(sampleIsStale(13, 2), true);
  assert.equal(sampleIsStale(7, 2, true), true);
  assert.equal(sampleIsStale(4, 2, true), false);
  assert.equal(sampleIsStale(31, 10), false);
  assert.equal(sampleIsStale(33, 10), true);
  assert.equal(sampleIsStale(Infinity), true);
});

test("temporary network failures back off and recover, revocation stops polling", () => {
  assert.equal(
    tacticalPollInterval({ state: { error: new TypeError("offline") } }, 2000),
    10000
  );
  assert.equal(
    tacticalPollInterval({ state: { error: { status: 503 } } }, 2000),
    10000
  );
  assert.equal(tacticalPollInterval({ state: { error: null } }, 2000), 2000);
  for (const status of [401, 403])
    assert.equal(
      tacticalPollInterval({ state: { error: { status } } }, 2000),
      false
    );
});
