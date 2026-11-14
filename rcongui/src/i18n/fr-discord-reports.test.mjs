import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { discordReportsFr } from "./locales/fr-discord-reports.js";

test("French Discord integration interface covers all fields and placeholders", () => {
  const english = en.settings.discordReports;
  assert.deepEqual(Object.keys(discordReportsFr).sort(), Object.keys(english).sort());
  for (const [key, value] of Object.entries(english)) {
    assert.ok(discordReportsFr[key]?.trim(), key);
    const markers = (s) => [...s.matchAll(/\{\{\w+\}\}/g)].map((m) => m[0]).sort();
    assert.deepEqual(markers(discordReportsFr[key]), markers(value), key);
  }
});
