import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

test("French VIP rewards catalog covers every English entry and preserves variables and commands", async () => {
  const source = await readFile(new URL("./copy.js", import.meta.url), "utf8");
  const objectSource = source.split("export const vipCopy = ")[1].split("const german =")[0].trim().replace(/;$/, "");
  const english = vm.runInNewContext(`(${objectSource})`);
  const french = JSON.parse(await readFile(new URL("./copy-fr.json", import.meta.url), "utf8"));
  assert.deepEqual(Object.keys(french).sort(), Object.keys(english).sort());
  for (const [key, text] of Object.entries(english)) {
    assert.ok(french[key]?.trim(), key);
    const markers = (value) => [...value.matchAll(/\{\{\w+\}\}|![a-z]+/g)].map((item) => item[0]).sort();
    assert.deepEqual(markers(french[key]), markers(text), key);
  }
});
