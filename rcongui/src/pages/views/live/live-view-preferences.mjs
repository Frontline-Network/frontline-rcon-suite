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
    cards: Object.fromEntries(
      Object.entries(DEFAULT_LIVE_CARDS).map(([key, fallback]) => [
        key,
        typeof value?.cards?.[key] === "boolean" ? value.cards[key] : fallback,
      ])
    ),
  };
}

export const liveViewPreferencesKey = (userName) => [
  "user",
  "live-view",
  userName,
];
