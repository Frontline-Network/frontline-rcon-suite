const GAME_LABELS = {
  hll: "HLL",
  hllv: "HLL: Vietnam",
};

export const normalizeGame = (game) => {
  const value = String(game ?? "").trim().toLowerCase();
  if (value === "hll") return "hll";
  if (["hllv", "hll_vietnam", "vietnam"].includes(value)) return "hllv";
  return null;
};

export const getGameLabel = (game) => GAME_LABELS[normalizeGame(game)] ?? null;
