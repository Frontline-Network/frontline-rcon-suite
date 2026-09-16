import assert from "node:assert/strict";
import test from "node:test";
import { liveViewsEn, liveViewsDe } from "../../../i18n/locales/live-views.js";
import { copy } from "../live-map/copy.js";
import { recommendationNotice } from "./balance-recommendations.mjs";
import { balanceActionPreflight } from "./balance-action-guard.mjs";

const translate = (language) => (key) =>
  key
    .split(".")
    .slice(1)
    .reduce((value, part) => value?.[part], language);

test("live views and tactical map have complete English and German key parity", () => {
  for (const [en, de] of [
    [liveViewsEn.balance, liveViewsDe.balance],
    [copy.en, copy.de],
  ]) {
    assert.deepEqual(Object.keys(en).sort(), Object.keys(de).sort());
    for (const [key, value] of Object.entries(en)) {
      assert.equal(typeof value, "string", key);
      assert.ok(value.trim(), key);
      assert.deepEqual(
        value.match(/\{\{?\w+\}?\}/g)?.sort() ?? [],
        de[key].match(/\{\{?\w+\}?\}/g)?.sort() ?? [],
        `Placeholders: ${key}`
      );
    }
  }
});

test("all held-proposal states use the selected language and preserve safety guidance", () => {
  const en = translate(liveViewsEn);
  for (const context of [
    { valid: true },
    { valid: true, reviewing: true },
    { blocked: true },
    { balanced: true },
    {},
    { reviewing: true },
  ]) {
    const english = recommendationNotice(context, en);
    const german = recommendationNotice(context, translate(liveViewsDe));
    assert.notEqual(english.title, german.title);
    assert.ok(english.description);
    assert.doesNotMatch(
      english.description,
      /Prüfung|Vorschlag|Wechsel|Sekunden|wähle/
    );
    assert.equal(english.severity, german.severity);
  }
  assert.match(
    recommendationNotice({ valid: true }, en).description,
    /60 seconds/
  );
  assert.match(
    recommendationNotice({ reviewing: true }, en).description,
    /Close the review/
  );
});

test("preflight rejects changed selections with localized errors before reading live data", async () => {
  let reads = 0;
  const guard = balanceActionPreflight({
    recommendation: { kind: "move" },
    recipientIds: ["reviewed"],
    readTeams: () => {
      reads += 1;
    },
    readSettings: () => {
      reads += 1;
    },
    t: translate(liveViewsEn),
  });
  await assert.rejects(
    guard([{ player_id: "different" }]),
    /The player selection changed/
  );
  assert.equal(reads, 0);
});

test("stale proposal rejection is localized and never executes a switch", async () => {
  const guard = balanceActionPreflight({
    recommendation: { kind: "move", player: { player_id: "gone" } },
    recipientIds: ["gone"],
    readTeams: async () => ({
      allies: { squads: {} },
      axis: { squads: {} },
      fail_count: 1,
    }),
    readSettings: async () => ({}),
    t: translate(liveViewsEn),
  });
  await assert.rejects(
    guard([{ player_id: "gone" }]),
    /No switch was executed/
  );
});
