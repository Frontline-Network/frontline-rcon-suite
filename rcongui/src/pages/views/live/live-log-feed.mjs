export const LIVE_LOG_GC_TIME = 60_000;
export const LIVE_LOG_PAGE_SIZE = 500;

export function mergeLogPage(current, page, direction, limit) {
  if (!page || !Array.isArray(page.logs) || !("newest" in page)) {
    throw new Error("Invalid live-log page");
  }
  const reset = !current || Boolean(page.reset);
  const combined = reset
    ? page.logs
    : direction === "older"
    ? [...current.logs, ...page.logs]
    : [...page.logs, ...current.logs];
  const seen = new Set();
  const logs = combined
    .filter((line) => {
      if (!line.cursor_id || seen.has(line.cursor_id)) return false;
      seen.add(line.cursor_id);
      return true;
    })
    .slice(0, limit);
  return {
    logs,
    actions: [
      ...new Set([...(current?.actions ?? []), ...page.actions]),
    ].sort(),
    players: [...new Set([...(current?.players ?? []), ...page.players])].slice(
      -2000
    ),
    newest: reset || direction === "newer" ? page.newest : current.newest,
    oldest: reset || direction === "older" ? page.oldest : current.oldest,
    has_older:
      reset || direction === "older" ? page.has_older : current.has_older,
    reset: page.reset || current?.reset || null,
  };
}
