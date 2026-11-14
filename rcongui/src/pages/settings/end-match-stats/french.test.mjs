import { readFile } from "node:fs/promises";
import { test } from "node:test";
import assert from "node:assert/strict";
import vm from "node:vm";
import { french } from "./french.js";

test("French covers every existing translated match-statistics setting", async () => {
  const source = await readFile(new URL("./index.jsx", import.meta.url), "utf8");
  const dictionary = source.match(/const english = (\{[\s\S]*?\});\s*const languages =/);
  assert.ok(dictionary, "English settings dictionary must be discoverable");
  const english = vm.runInNewContext(`(${dictionary[1]})`);
  assert.deepEqual(Object.keys(english).filter((key) => !french[key]), []);
});
