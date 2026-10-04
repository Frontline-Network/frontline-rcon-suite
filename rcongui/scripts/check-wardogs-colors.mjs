import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { createRequire } from "node:module";
import { WARDOGS_COLOR_STYLES, normalizeWardogsStyle } from "../src/themes/wardogs/colorStyles.js";

const { getContrastRatio } = createRequire(import.meta.url)("@mui/material/styles");
const backend = readFileSync(new URL("../../rconweb/api/wardogs_styles.py", import.meta.url), "utf8");
const adminStyles = Object.fromEntries([...backend.matchAll(/"(\w+)": (\{"accent": "#[a-f0-9]+", "lightAccent": "#[a-f0-9]+"\})/g)]
  .map(([, id, colors]) => [id, JSON.parse(colors)]));
assert.deepEqual(Object.keys(adminStyles), Object.keys(WARDOGS_COLOR_STYLES));
for (const [id, style] of Object.entries(WARDOGS_COLOR_STYLES)) {
  assert.deepEqual(adminStyles[id], { accent: style.accent, lightAccent: style.lightAccent }, `${id}: admin and RCON must match`);
  for (const background of ["#0d0d0f", "#141416", "#1a1a1e"]) {
    assert.ok(getContrastRatio(style.accent, background) >= 4.5, `${id}: dark text contrast`);
  }
  for (const background of ["#f5f5f7", "#ffffff", "#f0f0f4"]) {
    assert.ok(getContrastRatio(style.lightAccent, background) >= 4.5, `${id}: light text contrast`);
  }
  assert.ok(getContrastRatio(style.accent, "#080b08") >= 4.5, `${id}: dark button label`);
  assert.ok(getContrastRatio(style.lightAccent, "#ffffff") >= 4.5, `${id}: light button label`);
  assert.equal(normalizeWardogsStyle(id), id);
}
for (const value of [undefined, null, "invalid", "__proto__", [], ["blue"], {}]) {
  assert.equal(normalizeWardogsStyle(value), "rose");
}
console.log("Wardogs colors: 6 styles, dark/light contrast and admin parity passed.");
