export const DEFAULT_WARDOGS_SHORTCUTS = Object.freeze([
  "/settings/broadcast-message",
  "/records/players",
]);

export const MAX_WARDOGS_SHORTCUTS = 64;
const INTERNAL_ROUTE = /^\/[a-z0-9_-]+(?:\/[a-z0-9_-]+)*$/;

export function normalizeWardogsShortcuts(value) {
  if (!Array.isArray(value)) return [...DEFAULT_WARDOGS_SHORTCUTS];
  return [
    ...new Set(
      value.filter(
        (route) =>
          typeof route === "string" &&
          route.length <= 200 &&
          INTERNAL_ROUTE.test(route)
      )
    ),
  ].slice(0, MAX_WARDOGS_SHORTCUTS);
}

// Saved destinations may become unavailable after a permission change or an
// upgrade. Keep the preference, but never turn those entries into working links.
export function resolveWardogsShortcuts(routes, links) {
  const available = new Map(
    links
      .filter((link) => !link.locked && link.isAccessible !== false)
      .map((link) => [link.to, link])
  );
  return normalizeWardogsShortcuts(routes).flatMap((route) =>
    available.has(route) ? [available.get(route)] : []
  );
}

export function moveWardogsShortcut(routes, route, offset) {
  const next = [...routes];
  const from = next.indexOf(route);
  const to = from + offset;
  if (from < 0 || to < 0 || to >= next.length) return next;
  [next[from], next[to]] = [next[to], next[from]];
  return next;
}
