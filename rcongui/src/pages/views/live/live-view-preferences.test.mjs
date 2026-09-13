import assert from "node:assert/strict";
import test from "node:test";
import { readFileSync } from "node:fs";
import {
  FIXED_PLAYER_COLUMNS,
  PLAYER_COLUMN_IDS,
  getPlayerColumnVisibility,
  getPlayerTablePresentation,
  normalizePlayerTablePreferences,
  setPlayerColumnVisible,
} from "./player-table-preferences.mjs";
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

test("table presets survive serialization instead of reverting to operations", () => {
  for (const preset of ["operations", "all", "custom"]) {
    const settings = normalizeLiveViewPreferences({
      players_table: {
        preset,
        fontSize: "large",
        density: "comfortable",
        columnVisibility: { role: true, kills: false },
      },
    });
    assert.deepEqual(
      normalizeLiveViewPreferences(JSON.parse(JSON.stringify(settings))),
      settings
    );
    assert.equal(settings.players_table.preset, preset);
  }
});

test("customizing snapshots the active preset and keeps essential columns", () => {
  for (const preset of ["operations", "all"]) {
    const initial = normalizePlayerTablePreferences({ preset });
    const expected = { ...getPlayerColumnVisibility(initial), kills: false };
    const custom = setPlayerColumnVisible(initial, "kills", false);
    assert.equal(custom.preset, "custom");
    assert.deepEqual(getPlayerColumnVisibility(custom), expected);
    assert.equal(getPlayerColumnVisibility(initial).kills, true);
    for (const id of FIXED_PLAYER_COLUMNS) {
      assert.equal(
        getPlayerColumnVisibility(setPlayerColumnVisible(custom, id, false))[
          id
        ],
        true
      );
    }
    assert.deepEqual(setPlayerColumnVisible(custom, "unknown", true), custom);
  }
});

test("invalid or older table preferences use independent safe defaults", () => {
  const defaults = normalizePlayerTablePreferences();
  assert.deepEqual(
    normalizeLiveViewPreferences({ cards: { vips: true } }).players_table,
    defaults
  );
  assert.deepEqual(
    normalizePlayerTablePreferences({
      preset: "invalid",
      fontSize: 1,
      density: null,
      columnVisibility: {
        kills: "false",
        player_summary: false,
        unknown: true,
      },
    }),
    defaults
  );
  defaults.columnVisibility.kills = false;
  assert.equal(normalizePlayerTablePreferences().columnVisibility.kills, true);
});

test("resetting status cards preserves table settings and compact balance", () => {
  const preferences = normalizeLiveViewPreferences({
    cards: { vips: true },
    balance_expanded: false,
    players_table: { preset: "all", density: "comfortable", fontSize: "large" },
  });
  const reset = resetLiveStatusCards(preferences);
  assert.deepEqual(reset.players_table, preferences.players_table);
  assert.equal(reset.balance_expanded, false);
  assert.deepEqual(reset.cards, DEFAULT_LIVE_CARDS);
});

test("row spacing and font choices have distinct layout sizes", () => {
  assert.deepEqual(getPlayerTablePresentation(), {
    fontSize: "0.85rem",
    rowHeight: 38,
  });
  assert.deepEqual(
    getPlayerTablePresentation({ fontSize: "normal", density: "normal" }),
    { fontSize: "1rem", rowHeight: 46 }
  );
  assert.deepEqual(
    getPlayerTablePresentation({ fontSize: "large", density: "comfortable" }),
    { fontSize: "1.15rem", rowHeight: 56 }
  );
  assert.equal(getPlayerTablePresentation({ fontSize: "large" }).rowHeight, 44);
});

test("preference whitelist covers the actual player columns", () => {
  const source = readFileSync(
    new URL("./players-columns.jsx", import.meta.url),
    "utf8"
  );
  const ids = [...source.matchAll(/\bid: "([\w-]+)"/g)].map(
    (match) => match[1]
  );
  assert.deepEqual([...ids, "details"].sort(), [...PLAYER_COLUMN_IDS].sort());
});
