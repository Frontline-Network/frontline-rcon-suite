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

// These pages already own a faster roster observer. GlobalState must remain
// subscribed so its shared online-player state stays current, but a second
// interval on the same query can create an extra request whenever the timers
// are slightly offset.
const PAGE_OWNED_LIVE_ROSTER_ROUTES = new Set([
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

export const shouldUseGlobalLiveRosterPolling = (pathname = "") => {
  const normalized = normalizePathname(pathname);
  return (
    shouldPollLiveRoster(normalized) &&
    !PAGE_OWNED_LIVE_ROSTER_ROUTES.has(normalized)
  );
};

export const getGlobalLiveRosterPollingInterval = (
  pathname = "",
  intervalMs = GAME_STATE_POLLING.defaultIntervalMs
) => (shouldUseGlobalLiveRosterPolling(pathname) ? intervalMs : false);

export const shouldPollModeratorPresence = (pathname = "") =>
  normalizePathname(pathname) === "/";

export const getGameStatePollingInterval = (pathname = "") =>
  LIVE_GAME_STATE_ROUTES.has(normalizePathname(pathname))
    ? GAME_STATE_POLLING.liveOperationsIntervalMs
    : GAME_STATE_POLLING.defaultIntervalMs;
