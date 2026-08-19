const GAME_LABELS = Object.freeze({
  hll: "Hell Let Loose",
  hllv: "HLL Vietnam",
});

export const getGameLabel = (game) => GAME_LABELS[game] ?? null;
