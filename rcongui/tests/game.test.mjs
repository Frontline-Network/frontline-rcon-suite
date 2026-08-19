import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

const source = await readFile(
  new URL("../src/utils/game.js", import.meta.url),
  "utf8"
);
const { getGameLabel } = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);

test("labels HLL and HLL Vietnam explicitly", () => {
  assert.equal(getGameLabel("hll"), "Hell Let Loose");
  assert.equal(getGameLabel("hllv"), "HLL Vietnam");
  assert.equal(getGameLabel("unsupported"), null);
});
