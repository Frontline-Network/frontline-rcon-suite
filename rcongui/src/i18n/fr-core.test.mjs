import assert from "node:assert/strict";
import { test } from "node:test";
import en from "./locales/en.js";
import { frenchCore } from "./locales/fr-core.js";
import { incidentsFr } from "./locales/fr-incidents.js";
import { commonFr } from "./locales/fr-common.js";

function check(source, translated, path) {
  assert.deepEqual(Object.keys(translated).sort(), Object.keys(source).sort(), path);
  for (const key of Object.keys(source)) {
    const value = source[key];
    const target = translated[key];
    if (value && typeof value === "object") {
      check(value, target, `${path}.${key}`);
    } else {
      assert.equal(typeof target, "string", `${path}.${key}`);
      assert.ok(target.trim(), `${path}.${key}`);
      const tokens = (text) => [...text.matchAll(/\{\{[^{}]+\}\}/g)].map((x) => x[0]).sort();
      assert.deepEqual(tokens(target), tokens(value), `${path}.${key}`);
    }
  }
}

test("reviewed French core copy covers the source and preserves placeholders", () => {
  for (const key of Object.keys(frenchCore)) check(en[key], frenchCore[key], key);
  check(en.incidents, incidentsFr, "incidents");
  check(en.common, commonFr, "common");
  assert.equal(frenchCore.connectionStates.disabled, "Désactivé");
  assert.equal(frenchCore.errors.back, "Retour");
});
