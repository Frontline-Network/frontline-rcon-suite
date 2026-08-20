export const GAME_STATE_POLLING = Object.freeze({
  defaultIntervalMs: 30_000,
  liveOperationsIntervalMs: 10_000,
});

const LIVE_GAME_STATE_ROUTES = new Set(["/views/live", "/views/team"]);

export const getGameStatePollingInterval = (pathname = "") =>
  LIVE_GAME_STATE_ROUTES.has(pathname)
    ? GAME_STATE_POLLING.liveOperationsIntervalMs
    : GAME_STATE_POLLING.defaultIntervalMs;
