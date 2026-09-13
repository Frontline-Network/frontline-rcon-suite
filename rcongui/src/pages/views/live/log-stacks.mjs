export const LOG_STACK_WINDOW_MS = 60_000;

// MESSAGE records contain a recipient prefix in `message`; sub_content is the
// unmodified message body from the RCON parser. Never remove names inside it.
export function getMessageBody(event) {
  if (typeof event.sub_content === "string") return event.sub_content;
  const message = String(event.message ?? "");
  const name = String(event.player_name_1 ?? "");
  const id = String(event.player_id_1 ?? "");
  if (!name) return message;
  const prefixes = [
    `${name}(${id}): `,
    `${name}(Allies/${id}): `,
    `${name}(Axis/${id}): `,
    `${name}: `,
  ];
  const prefix = prefixes.find((candidate) => message.startsWith(candidate));
  return prefix ? message.slice(prefix.length) : message;
}

const timestamp = (event) =>
  typeof event.timestamp_ms === "number" &&
  Number.isFinite(event.timestamp_ms) &&
  Math.abs(event.timestamp_ms) <= 8.64e15
    ? event.timestamp_ms
    : null;

const eventKey = (event) =>
  JSON.stringify([
    event.id ?? null,
    event.timestamp_ms,
    event.action,
    event.player_id_1,
    event.player_id_2,
    event.message,
    event.sub_content,
  ]);

// Operate on the visible, filtered page only. Kills, chat and moderation actions
// are deliberately not collapsed: each of those is a distinct event to review.
export function groupLogRows(rows) {
  const descending =
    (timestamp(rows[0]?.original ?? {}) ?? 0) >=
    (timestamp(rows.at(-1)?.original ?? {}) ?? 0);
  // Anchor bursts at the oldest entry so new live messages can grow a stack
  // without replacing its React key (and closing its expanded details).
  const ordered = descending ? [...rows].reverse() : rows;
  const groups = [];
  const keyCounts = new Map();
  for (const row of ordered) {
    const event = row.original;
    const time = timestamp(event);
    const body = event.action === "MESSAGE" ? getMessageBody(event) : null;
    const stackable = body !== null && body.trim() !== "" && time !== null;
    const previous = groups.at(-1);
    const start = Math.min(previous?.start ?? time, time);
    const end = Math.max(previous?.end ?? time, time);
    if (
      stackable &&
      previous?.stackable &&
      previous.body === body &&
      end - start <= LOG_STACK_WINDOW_MS
    ) {
      previous.rows.push(row);
      previous.start = start;
      previous.end = end;
    } else {
      const key = eventKey(event);
      const occurrence = keyCounts.get(key) ?? 0;
      keyCounts.set(key, occurrence + 1);
      groups.push({
        key: `${key}:${occurrence}`,
        rows: [row],
        body,
        stackable,
        start: time,
        end: time,
      });
    }
  }
  if (descending) {
    groups.reverse();
    groups.forEach((group) => group.rows.reverse());
  }
  return groups;
}
