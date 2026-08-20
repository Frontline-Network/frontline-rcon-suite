export const CONNECTION_STATE = Object.freeze({
  LOADING: "loading",
  ONLINE: "online",
  OFFLINE: "offline",
  STALE: "stale",
  UNKNOWN: "unknown",
});

export const EMPTY_CONNECTION_HEALTH = Object.freeze({
  state: CONNECTION_STATE.LOADING,
  lastSuccessAt: null,
  lastAttemptAt: null,
  isRefreshing: false,
});

/**
 * Convert React Query transport state into the explicit operational states
 * shown to administrators. Cached data is marked stale after a failed refresh
 * instead of being presented as current.
 */
export function createConnectionHealth(query, { enabled = true } = {}) {
  const hasData = query?.data !== undefined && query?.data !== null;
  const lastSuccessAt = query?.dataUpdatedAt || null;
  const lastAttemptAt =
    Math.max(query?.dataUpdatedAt || 0, query?.errorUpdatedAt || 0) || null;

  let state = CONNECTION_STATE.UNKNOWN;

  if (!enabled) {
    state = hasData ? CONNECTION_STATE.STALE : CONNECTION_STATE.UNKNOWN;
  } else if (query?.isPending && !hasData) {
    state = CONNECTION_STATE.LOADING;
  } else if (query?.isError) {
    state = hasData ? CONNECTION_STATE.STALE : CONNECTION_STATE.OFFLINE;
  } else if (hasData) {
    state = CONNECTION_STATE.ONLINE;
  }

  return {
    state,
    lastSuccessAt,
    lastAttemptAt,
    isRefreshing: Boolean(query?.isFetching && hasData),
  };
}

export function isUsableConnectionState(state) {
  return state === CONNECTION_STATE.ONLINE || state === CONNECTION_STATE.STALE;
}
