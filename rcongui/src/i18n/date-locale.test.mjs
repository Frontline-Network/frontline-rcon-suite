import { test } from "node:test";
import assert from "node:assert/strict";
import { dateLocale } from "./date-locale.js";

test("date pickers use the chosen language including regional variants", () => {
  for (const [input, expected] of [["fr", "fr"], ["fr-FR", "fr"], ["FR_ca", "fr"], ["en-US", "en"], ["de-DE", "de"], [undefined, "de"], ["es", "de"]]) {
    assert.equal(dateLocale(input), expected);
  }
});
