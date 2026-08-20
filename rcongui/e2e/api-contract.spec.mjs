import { expect, test } from "@playwright/test";
import { getGameLabel, normalizeGame } from "../src/utils/game-context.js";
import {
  CONNECTION_STATE,
  createAggregateConnectionHealth,
  createConnectionHealth,
} from "../src/utils/connectionHealth.js";

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

test.describe("connection-health API contract", () => {
  test("distinguishes loading, online, offline, stale and dependent unknown data", () => {
    expect(createConnectionHealth({ isPending: true }).state).toBe(
      CONNECTION_STATE.LOADING
    );
    expect(
      createConnectionHealth({ data: { current_players: 20 } }).state
    ).toBe(CONNECTION_STATE.ONLINE);
    expect(createConnectionHealth({ isError: true }).state).toBe(
      CONNECTION_STATE.OFFLINE
    );
    expect(
      createConnectionHealth({
        data: { current_players: 20 },
        dataUpdatedAt: 1000,
        errorUpdatedAt: 2000,
        isError: true,
      })
    ).toMatchObject({
      state: CONNECTION_STATE.STALE,
      lastSuccessAt: 1000,
      lastAttemptAt: 2000,
    });
    expect(
      createConnectionHealth({
        data: { current_players: 20 },
        dataUpdatedAt: 1000,
        errorUpdatedAt: 2000,
        isError: false,
        isRefetchError: true,
      })
    ).toMatchObject({
      state: CONNECTION_STATE.STALE,
      lastSuccessAt: 1000,
      lastAttemptAt: 2000,
    });
    expect(createConnectionHealth(undefined, { enabled: false }).state).toBe(
      CONNECTION_STATE.UNKNOWN
    );
    expect(createConnectionHealth(undefined, { disabled: true }).state).toBe(
      CONNECTION_STATE.DISABLED
    );
  });

  test("summarizes independently refreshed sources as partially available", () => {
    expect(
      createAggregateConnectionHealth(
        {
          state: CONNECTION_STATE.ONLINE,
          lastSuccessAt: 2000,
          lastAttemptAt: 2000,
          isRefreshing: false,
        },
        {
          state: CONNECTION_STATE.STALE,
          lastSuccessAt: 1000,
          lastAttemptAt: 3000,
          isRefreshing: true,
        }
      )
    ).toEqual({
      state: CONNECTION_STATE.PARTIAL,
      lastSuccessAt: 2000,
      lastAttemptAt: 3000,
      isRefreshing: true,
    });

    expect(
      createAggregateConnectionHealth(
        { state: CONNECTION_STATE.DISABLED },
        { state: CONNECTION_STATE.DISABLED }
      ).state
    ).toBe(CONNECTION_STATE.DISABLED);
  });
});
