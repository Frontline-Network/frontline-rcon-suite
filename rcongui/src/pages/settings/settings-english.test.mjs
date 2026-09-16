import assert from "node:assert/strict";
import { readFileSync, readdirSync } from "node:fs";
import test from "node:test";

async function importSource(relative) {
  const content = readFileSync(new URL(relative, import.meta.url), "utf8");
  return import(
    `data:text/javascript;base64,${Buffer.from(content).toString("base64")}`
  );
}

const { settingsPanelsDe: de, settingsPanelsEn: en } = await importSource(
  "../../i18n/locales/settings-panels.js"
);
const { leadershipResults, translateLeadershipResult } = await importSource(
  "./leadership-votes/result-copy.js"
);

const leaves = (object, prefix = "") =>
  Object.entries(object).flatMap(([key, value]) =>
    typeof value === "string"
      ? [[`${prefix}${key}`, value]]
      : leaves(value, `${prefix}${key}.`)
  );

test("settings catalogs cover every key and preserve interpolation arguments", () => {
  const german = Object.fromEntries(leaves(de));
  const english = Object.fromEntries(leaves(en));
  assert.deepEqual(Object.keys(english).sort(), Object.keys(german).sort());
  assert.ok(Object.keys(english).length > 350);
  for (const [key, value] of Object.entries(german)) {
    assert.ok(english[key].trim(), key);
    assert.deepEqual(
      [...english[key].matchAll(/{{([^}]+)}}/g)].map((m) => m[1]).sort(),
      [...value.matchAll(/{{([^}]+)}}/g)].map((m) => m[1]).sort(),
      key
    );
  }
});

test("all extracted autobalancer references have English translations", () => {
  const folder = new URL("./[configs]/", import.meta.url);
  for (const name of readdirSync(folder).filter((name) =>
    /^autobalancer-.*\.jsx$/.test(name)
  )) {
    const source = readFileSync(new URL(name, folder), "utf8");
    for (const match of source.matchAll(
      /settingsPanels\.autobalancer\.([a-zA-Z]+)["']/g
    )) {
      assert.equal(
        typeof en.autobalancer[match[1]],
        "string",
        `${name}: ${match[1]}`
      );
    }
    assert.match(
      source,
      /useTranslation\(\)/,
      `${name} reacts to language changes`
    );
    assert.doesNotMatch(
      source,
      /(?:DateTimeFormat|NumberFormat|toLocale\w+)\("de-DE"/,
      name
    );
  }
});

test("known leadership outcomes are localized without rewriting arbitrary reports", () => {
  for (const [key, [german, english]] of Object.entries(leadershipResults)) {
    const raw = `${german} / ${english}`;
    assert.equal(translateLeadershipResult(raw, "en"), english, key);
    assert.equal(translateLeadershipResult(raw, "de"), german, key);
    assert.equal(translateLeadershipResult(raw, "en-GB"), english, key);
  }
  for (const raw of [
    undefined,
    null,
    "Unknown result",
    "Name / changed",
    "Squad gemeldet – Kommunikation prüfen",
  ])
    assert.equal(translateLeadershipResult(raw, "en"), raw);
});
