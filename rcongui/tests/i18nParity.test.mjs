import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import test from "node:test";

async function importSource(relativePath) {
  const source = await readFile(new URL(relativePath, import.meta.url), "utf8");
  return import(
    `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
  );
}

function collectKeys(value, prefix = "") {
  return Object.entries(value).flatMap(([key, child]) => {
    const path = prefix ? `${prefix}.${key}` : key;
    return child && typeof child === "object" && !Array.isArray(child)
      ? collectKeys(child, path)
      : [path];
  });
}

const [{ default: de }, { default: en }] = await Promise.all([
  importSource("../src/i18n/locales/de.js"),
  importSource("../src/i18n/locales/en.js"),
]);

test("German and English expose the same translation keys", () => {
  assert.deepEqual(collectKeys(de).sort(), collectKeys(en).sort());
});

test("operational states have complete translations", () => {
  for (const locale of [de, en]) {
    for (const state of ["loading", "online", "offline", "stale", "unknown"]) {
      assert.equal(typeof locale.connectionStates[state], "string");
      assert.equal(typeof locale.sidebar.gameServerState[state], "string");
      assert.equal(typeof locale.sidebar.crconState[state], "string");
    }
  }
});
