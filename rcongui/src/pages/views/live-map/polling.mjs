export function tacticalPollInterval(query, normalInterval) {
  const error = query.state.error;
  if ([401, 403].includes(error?.status)) return false;
  return error ? 10000 : normalInterval;
}

export function sampleAge(snapshot, monotonicNow) {
  if (
    !snapshot ||
    !Number.isFinite(snapshot.age_seconds) ||
    !Number.isFinite(snapshot.received_at_monotonic)
  )
    return Infinity;
  // Never compare the browser's wall clock with the server's wall clock.
  return (
    Math.max(0, snapshot.age_seconds) +
    Math.max(0, snapshot.transport_seconds || 0) +
    Math.max(0, monotonicNow - snapshot.received_at_monotonic)
  );
}

export function sampleIsStale(age, interval = 2, wasStale = false) {
  const cadence = Number.isFinite(interval) ? Math.max(2, interval) : 2;
  // Allow the shared sample cache + collector + browser poll to complete.
  // Once stale, require a genuinely fresh sample instead of flickering at 6 s.
  const limit = wasStale
    ? Math.max(4, cadence * 2)
    : Math.max(12, cadence * 3 + 2);
  return age > limit;
}
