import { expect, test } from "@playwright/test";
import { getGameLabel, normalizeGame } from "../src/utils/game-context.js";

test.describe("game context API contract", () => {
  const hllVietnamAliases = ["hllv", "hll_vietnam", "vietnam", " HLL_VIETNAM "];

  test("keeps the HLL identifier stable", () => {
    expect(normalizeGame("hll")).toBe("hll");
    expect(getGameLabel("hll")).toBe("HLL");
  });

  for (const alias of hllVietnamAliases) {
    test(`normalizes ${JSON.stringify(alias)} as HLL Vietnam`, () => {
      expect(normalizeGame(alias)).toBe("hllv");
      expect(getGameLabel(alias)).toBe("HLL: Vietnam");
    });
  }

  test("does not invent a label for missing or future identifiers", () => {
    for (const value of [null, undefined, "", "future_game"]) {
      expect(normalizeGame(value)).toBeNull();
      expect(getGameLabel(value)).toBeNull();
    }
  });
});
