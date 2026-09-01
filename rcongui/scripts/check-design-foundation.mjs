import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

import {
  FRONTLINE_GEOMETRY,
  frontlineFocusRing,
} from "../src/themes/foundation.mjs";

const ROOT = path.resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

assert.deepEqual(FRONTLINE_GEOMETRY.radius, {
  structure: 0,
  control: 2,
  overlay: 4,
  round: 999,
});
assert.equal(FRONTLINE_GEOMETRY.focusRing.width, 2);
assert.equal(FRONTLINE_GEOMETRY.focusRing.offset, 2);
assert.equal(frontlineFocusRing("#fff"), "2px solid #fff");

const themeSource = read("src/themes/default/getDefaultTheme.js");
const primitiveSource = read("src/themes/default/primitives/frontline.js");
const appearanceSource = read("src/themes/appearance.js");
const dataDisplaySource = read(
  "src/themes/default/customizations/dataDisplay.js"
);

assert.match(themeSource, /foundationCustomizations/);
assert.match(
  themeSource,
  /frontline: \{ geometry: geometry \?\? FRONTLINE_GEOMETRY \}/
);
assert.match(
  primitiveSource,
  /shape = \{ borderRadius: geometry\.radius\.control \}/
);
assert.match(appearanceSource, /\.\.\.baseOptions\.frontline/);
assert.doesNotMatch(dataDisplaySource, /borderRadius:\s*["']999px["']/);

console.log(
  "Design foundation contract passed: geometry, focus and appearance tokens stay connected."
);
