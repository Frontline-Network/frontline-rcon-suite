import assert from "node:assert/strict";
import test from "node:test";
import {
  DEFAULT_LIVE_CARDS,
  liveViewPreferencesKey,
  normalizeLiveViewPreferences,
  resetLiveStatusCards,
} from "./live-view-preferences.mjs";

test("only score and next map are enabled by default", () => {
  assert.deepEqual(
    Object.entries(normalizeLiveViewPreferences().cards)
      .filter(([, enabled]) => enabled)
      .map(([key]) => key),
    ["score", "next_map"]
  );
});
test("keeps explicit false settings and all-off preferences", () => {
  const cards = Object.fromEntries(
    Object.keys(DEFAULT_LIVE_CARDS).map((key) => [key, false])
  );
  assert.deepEqual(normalizeLiveViewPreferences({ cards }).cards, cards);
});
test("merges missing settings with defaults and ignores invalid values", () => {
  assert.deepEqual(
    normalizeLiveViewPreferences({
      cards: { vips: true, score: "false", watched: 1, unknown: true },
    }).cards,
    { ...DEFAULT_LIVE_CARDS, vips: true }
  );
});
test("normalizing creates independent objects without mutating defaults", () => {
  const value = normalizeLiveViewPreferences();
  value.cards.score = false;
  assert.equal(normalizeLiveViewPreferences().cards.score, true);
});
test("query caches are isolated by user account", () => {
  assert.notDeepEqual(
    liveViewPreferencesKey("Alice"),
    liveViewPreferencesKey("Bob")
  );
});

test("older preferences keep balance details expanded by default", () => {
  assert.equal(
    normalizeLiveViewPreferences({ cards: { vips: true } }).balance_expanded,
    true
  );
  assert.equal(
    normalizeLiveViewPreferences({ balance_expanded: "false" })
      .balance_expanded,
    true
  );
});

test("keeps compact balance and status-card preferences independently", () => {
  const value = normalizeLiveViewPreferences({
    balance_expanded: false,
    cards: { vips: true },
  });
  assert.equal(value.balance_expanded, false);
  assert.equal(value.cards.vips, true);
  const reset = resetLiveStatusCards(value);
  assert.equal(reset.balance_expanded, false);
  assert.deepEqual(reset.cards, DEFAULT_LIVE_CARDS);
  assert.equal(value.cards.vips, true);
});
