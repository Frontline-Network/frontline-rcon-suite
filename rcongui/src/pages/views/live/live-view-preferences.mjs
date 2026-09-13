import { normalizePlayerTablePreferences } from "./player-table-preferences.mjs";

export const DEFAULT_LIVE_CARDS = Object.freeze({
  commander: false,
  squad_leaders: false,
  vips: false,
  watched: false,
  score: true,
  next_map: true,
});

export function normalizeLiveViewPreferences(value) {
  return {
    version: 1,
    players_table: normalizePlayerTablePreferences(value?.players_table),
    balance_expanded:
      typeof value?.balance_expanded === "boolean"
        ? value.balance_expanded
        : true,
    cards: Object.fromEntries(
      Object.entries(DEFAULT_LIVE_CARDS).map(([key, fallback]) => [
        key,
        typeof value?.cards?.[key] === "boolean" ? value.cards[key] : fallback,
      ])
    ),
  };
}

export function resetLiveStatusCards(value) {
  return {
    ...normalizeLiveViewPreferences(value),
    cards: { ...DEFAULT_LIVE_CARDS },
  };
}

export const liveViewPreferencesKey = (userName) => [
  "user",
  "live-view",
  userName,
];
