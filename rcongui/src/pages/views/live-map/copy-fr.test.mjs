import test from "node:test";
import assert from "node:assert/strict";
import { copy } from "./copy.js";

test("French live-map text covers English controls, warnings and variables", () => {
  assert.deepEqual(Object.keys(copy.fr).sort(), Object.keys(copy.en).sort());
  for (const [key, english] of Object.entries(copy.en)) {
    assert.ok(copy.fr[key]?.trim(), key);
    const markers = (s) => [...s.matchAll(/\{\w+\}/g)].map((item) => item[0]).sort();
    assert.deepEqual(markers(copy.fr[key]), markers(english), key);
  }
});
