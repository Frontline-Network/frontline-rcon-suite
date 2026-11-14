import { test } from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { autobalancerFr } from "./locales/fr-autobalancer.js";

test("reviewed French autobalancer settings cover the English configuration copy", () => {
  const missing = [];
  function compare(reference, translated, path = "") {
    for (const [key, value] of Object.entries(reference)) {
      const current = path ? `${path}.${key}` : key;
      if (typeof value === "object") compare(value, translated?.[key] || {}, current);
      else if (typeof translated?.[key] !== "string" || !translated[key].trim()) missing.push(current);
    }
  }
  compare(en.settings.configForms.autobalancer, autobalancerFr);
  assert.deepEqual(missing, []);
});
