export function tacticalPollInterval(query, normalInterval) {
  const error = query.state.error;
  if ([401, 403].includes(error?.status)) return false;
  return error ? 10000 : normalInterval;
}
