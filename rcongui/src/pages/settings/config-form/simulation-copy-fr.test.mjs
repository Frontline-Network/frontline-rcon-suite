import test from "node:test";
import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import vm from "node:vm";

for (const [sourceFile, translatedFile] of [
  ["LevelRuleTestDrawer.jsx", "level-copy-fr.json"],
  ["EscalationRuleTestDrawer.jsx", "escalation-copy-fr.json"],
  ["TrustRuleTestDrawer.jsx", "trust-copy-fr.json"],
]) {
  test(`${sourceFile}: French simulation copy matches English structure and variables`, async () => {
    const source = (await readFile(new URL(sourceFile, import.meta.url), "utf8")).replace(/\r\n/g, "\n");
    const expression = source.split("const copyByLanguage = ")[1].split("\n\nconst fill")[0].trim().replace(/;$/, "");
    const english = vm.runInNewContext(`(${expression})`).en;
    const french = JSON.parse(await readFile(new URL(translatedFile, import.meta.url), "utf8"));
    const compare = (left, right, path = "") => {
      if (typeof left === "string") {
        assert.equal(typeof right, "string", path);
        assert.ok(right.trim(), path);
        const variables = (s) => [...s.matchAll(/\{\{\w+\}\}/g)].map((x) => x[0]).sort();
        assert.deepEqual(variables(right), variables(left), path);
      } else {
        assert.equal(Array.isArray(right), Array.isArray(left), path);
        assert.deepEqual(Object.keys(right).sort(), Object.keys(left).sort(), path);
        for (const key of Object.keys(left)) compare(left[key], right[key], `${path}.${key}`);
      }
    };
    compare(english, french);
  });
}
