export const CONNECTION_STATE = Object.freeze({
  LOADING: "loading",
  ONLINE: "online",
  PARTIAL: "partial",
  OFFLINE: "offline",
  STALE: "stale",
  UNKNOWN: "unknown",
  DISABLED: "disabled",
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
export function createConnectionHealth(
  query,
  { enabled = true, disabled = false } = {}
) {
  const hasData = query?.data !== undefined && query?.data !== null;
  const lastSuccessAt = query?.dataUpdatedAt || null;
  const lastAttemptAt =
    Math.max(query?.dataUpdatedAt || 0, query?.errorUpdatedAt || 0) || null;
  const hasFailedRefresh = Boolean(
    hasData &&
      (query?.isRefetchError ||
        (query?.errorUpdatedAt || 0) > (query?.dataUpdatedAt || 0))
  );

  let state = CONNECTION_STATE.UNKNOWN;

  if (disabled) {
    state = CONNECTION_STATE.DISABLED;
  } else if (!enabled) {
    state = hasData ? CONNECTION_STATE.STALE : CONNECTION_STATE.UNKNOWN;
  } else if (query?.isPending && !hasData) {
    state = CONNECTION_STATE.LOADING;
  } else if (query?.isError || hasFailedRefresh) {
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

/**
 * Summarise multiple independently refreshed data sources without hiding a
 * partial outage behind the first successful request. This is a display-level
 * health contract; individual source states remain available for precise
 * action gating and diagnostics.
 */
export function createAggregateConnectionHealth(...healthSources) {
  const sources = healthSources.flat().filter(Boolean);
  if (sources.length === 0) {
    return { ...EMPTY_CONNECTION_HEALTH, state: CONNECTION_STATE.UNKNOWN };
  }

  const states = sources.map((source) => source.state);
  const availableStates = new Set([
    CONNECTION_STATE.ONLINE,
    CONNECTION_STATE.STALE,
  ]);
  const availableCount = states.filter((state) =>
    availableStates.has(state)
  ).length;
  let state = CONNECTION_STATE.UNKNOWN;

  if (states.every((value) => value === CONNECTION_STATE.DISABLED)) {
    state = CONNECTION_STATE.DISABLED;
  } else if (states.every((value) => value === CONNECTION_STATE.ONLINE)) {
    state = CONNECTION_STATE.ONLINE;
  } else if (states.every((value) => value === CONNECTION_STATE.STALE)) {
    state = CONNECTION_STATE.STALE;
  } else if (availableCount > 0) {
    state = CONNECTION_STATE.PARTIAL;
  } else if (states.some((value) => value === CONNECTION_STATE.LOADING)) {
    state = CONNECTION_STATE.LOADING;
  } else if (states.some((value) => value === CONNECTION_STATE.OFFLINE)) {
    state = CONNECTION_STATE.OFFLINE;
  }

  const newestTimestamp = (key) =>
    Math.max(...sources.map((source) => Number(source[key]) || 0)) || null;

  return {
    state,
    lastSuccessAt: newestTimestamp("lastSuccessAt"),
    lastAttemptAt: newestTimestamp("lastAttemptAt"),
    isRefreshing: sources.some((source) => source.isRefreshing),
  };
}

export function isUsableConnectionState(state) {
  return [
    CONNECTION_STATE.ONLINE,
    CONNECTION_STATE.PARTIAL,
    CONNECTION_STATE.STALE,
  ].includes(state);
}
