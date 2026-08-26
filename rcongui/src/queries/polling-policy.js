export const GAME_STATE_POLLING = Object.freeze({
  defaultIntervalMs: 30_000,
  liveOperationsIntervalMs: 10_000,
});

const LIVE_GAME_STATE_ROUTES = new Set(["/views/live", "/views/team"]);

const normalizePathname = (pathname = "") => {
  if (!pathname || pathname === "/") return "/";
  return pathname.replace(/\/+$/, "");
};

const LIVE_ROSTER_ROUTES = new Set([
  "/",
  "/views/live",
  "/views/team",
  "/stats/live-sessions",
]);

export const shouldPollLiveRoster = (pathname = "") => {
  const normalized = normalizePathname(pathname);
  return (
    LIVE_ROSTER_ROUTES.has(normalized) ||
    normalized.startsWith("/records/players/") ||
    normalized === "/records/players"
  );
};

export const shouldPollModeratorPresence = (pathname = "") =>
  normalizePathname(pathname) === "/";

export const getGameStatePollingInterval = (pathname = "") =>
  LIVE_GAME_STATE_ROUTES.has(normalizePathname(pathname))
    ? GAME_STATE_POLLING.liveOperationsIntervalMs
    : GAME_STATE_POLLING.defaultIntervalMs;
