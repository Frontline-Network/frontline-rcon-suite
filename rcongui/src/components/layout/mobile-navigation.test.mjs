import assert from "node:assert/strict";
import test from "node:test";

import { getMobileNavigationValue } from "./mobile-navigation.mjs";

test("mobile navigation separates the operations hub from the live workspace", () => {
  assert.equal(getMobileNavigationValue("/"), "server-operations");
  assert.equal(
    getMobileNavigationValue("/mobile/operations"),
    "server-operations"
  );
  assert.equal(getMobileNavigationValue("/views/live"), "operations");
  assert.equal(getMobileNavigationValue("/incidents"), "incidents");
  assert.equal(getMobileNavigationValue("/records/players"), "players");
});

test("mobile navigation groups related server operations", () => {
  assert.equal(
    getMobileNavigationValue("/settings/maps/votemap"),
    "server-operations"
  );
  assert.equal(getMobileNavigationValue("/records/vips"), "more");
});
