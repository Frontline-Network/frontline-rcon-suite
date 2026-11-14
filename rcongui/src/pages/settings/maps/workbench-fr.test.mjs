import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";
import { frenchMapWorkbench } from "./workbench-fr.js";

test("French map workbench includes all English strings and variables", async () => {
  const source = (await readFile(new URL("./workbench-translations.js", import.meta.url), "utf8")).replace(/\r\n/g, "\n");
  const object = source.split("const resources = ")[1].split("\n\nfor (const")[0].trim().replace(/;$/, "");
  const english = vm.runInNewContext(`(${object})`, { frenchMapWorkbench: {} }).en;
  assert.deepEqual(Object.keys(frenchMapWorkbench).sort(), Object.keys(english).sort());
  for (const section of Object.keys(english)) {
    assert.deepEqual(Object.keys(frenchMapWorkbench[section]).sort(), Object.keys(english[section]).sort(), section);
    for (const [key, value] of Object.entries(english[section])) {
      const translated = frenchMapWorkbench[section][key];
      assert.ok(translated?.trim(), `${section}.${key}`);
      const markers = (s) => [...s.matchAll(/\{\{\w+\}\}/g)].map((m) => m[0]).sort();
      assert.deepEqual(markers(translated), markers(value), `${section}.${key}`);
    }
  }
});
