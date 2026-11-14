import test from "node:test";
import assert from "node:assert/strict";
import { copy } from "./copy.js";

test("French report-admin safety copy covers all English fields and variables", () => {
  assert.deepEqual(Object.keys(copy.fr).sort(), Object.keys(copy.en).sort());
  for (const [key, value] of Object.entries(copy.en)) {
    assert.ok(copy.fr[key]?.trim(), key);
    const variables = (s) => [...s.matchAll(/\{\w+\}/g)].map((match) => match[0]).sort();
    assert.deepEqual(variables(copy.fr[key]), variables(value), key);
  }
});
