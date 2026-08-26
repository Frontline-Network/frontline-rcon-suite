import { expect, test } from "@playwright/test";
import { getGameLabel, normalizeGame } from "../src/utils/game-context.js";
import {
  CONNECTION_STATE,
  createAggregateConnectionHealth,
  createConnectionHealth,
} from "../src/utils/connectionHealth.js";
import {
  GAME_STATE_POLLING,
  getGameStatePollingInterval,
  shouldPollLiveRoster,
  shouldPollModeratorPresence,
} from "../src/queries/polling-policy.js";
import {
  HTTP_ERROR_TOAST_WINDOW_MS,
  createHttpErrorToastBudget,
} from "../src/utils/httpErrorToastBudget.js";

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

test.describe("HTTP error toast budget", () => {
  test("updates repeated errors and collapses a burst of distinct errors", () => {
    const budget = createHttpErrorToastBudget();
    const now = 1_000;

    expect(budget.record("api-unreachable", now)).toEqual({
      kind: "new",
      count: 1,
    });
    expect(budget.record("api-unreachable", now + 1)).toEqual({
      kind: "repeat",
      count: 2,
    });
    expect(budget.record("permission:map", now + 2).kind).toBe("new");
    expect(budget.record("auth", now + 3).kind).toBe("new");
    expect(budget.record("api:500:command", now + 4)).toEqual({
      kind: "suppressed",
      suppressed: 1,
    });
    expect(budget.diagnostics()).toEqual([
      expect.objectContaining({ signature: "api-unreachable", count: 2 }),
      expect.objectContaining({ signature: "permission:map", count: 1 }),
      expect.objectContaining({ signature: "auth", count: 1 }),
      expect.objectContaining({ signature: "api:500:command", count: 1 }),
    ]);
  });

  test("reopens the toast budget after the bounded error window", () => {
    const budget = createHttpErrorToastBudget();
    const now = 1_000;

    for (const signature of ["one", "two", "three", "four"]) {
      budget.record(signature, now);
    }

    expect(
      budget.record("fresh", now + HTTP_ERROR_TOAST_WINDOW_MS + 1)
    ).toEqual({ kind: "new", count: 1 });
  });
});

test.describe("game-state polling policy", () => {
  test("uses one faster stream only on live operation routes", () => {
    expect(getGameStatePollingInterval("/views/live")).toBe(
      GAME_STATE_POLLING.liveOperationsIntervalMs
    );
    expect(getGameStatePollingInterval("/views/team")).toBe(
      GAME_STATE_POLLING.liveOperationsIntervalMs
    );
    expect(getGameStatePollingInterval("/")).toBe(
      GAME_STATE_POLLING.defaultIntervalMs
    );
    expect(getGameStatePollingInterval("/settings/general")).toBe(
      GAME_STATE_POLLING.defaultIntervalMs
    );
  });

  test("loads expensive roster and moderator presence only where visible", () => {
    for (const route of [
      "/",
      "/views/live",
      "/views/team/",
      "/records/players",
      "/records/players/7656119",
      "/stats/live-sessions",
    ]) {
      expect(shouldPollLiveRoster(route)).toBe(true);
    }

    for (const route of [
      "/settings/general",
      "/settings/automods/no-leader",
      "/records/game-logs",
      "/apps/discord-report-bot",
    ]) {
      expect(shouldPollLiveRoster(route)).toBe(false);
    }

    expect(shouldPollModeratorPresence("/")).toBe(true);
    expect(shouldPollModeratorPresence("/views/live")).toBe(false);
    expect(shouldPollModeratorPresence("/settings/general")).toBe(false);
  });
});
