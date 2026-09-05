import test from "node:test";
import assert from "node:assert/strict";
import { tacticalPollInterval } from "./polling.mjs";

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
