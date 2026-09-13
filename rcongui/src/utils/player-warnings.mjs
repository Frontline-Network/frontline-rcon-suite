const RECENT_WARNING_WINDOW_MS = 24 * 60 * 60 * 1000;

// These senders are written by campaign_delivery.py and vip_lifecycle.py.
// Keep their MESSAGE entries in the history, but not in moderation indicators.
const INFORMATIONAL_SENDERS = [
  "Campaign:",
  "VIP lifecycle:",
  "VIP lifecycle test:",
];

export function isInformationalPlayerMessage(action) {
  return (
    action?.action_type === "MESSAGE" &&
    typeof action.by === "string" &&
    INFORMATIONAL_SENDERS.some((prefix) => action.by.startsWith(prefix))
  );
}

export function countRecentWarnings(receivedActions, now = Date.now()) {
  if (!Array.isArray(receivedActions)) return 0;
  const earliest = now - RECENT_WARNING_WINDOW_MS;
  return receivedActions.filter((action) => {
    if (isInformationalPlayerMessage(action)) return false;
    const timestamp = Date.parse(action?.time);
    return Number.isFinite(timestamp) && timestamp > earliest;
  }).length;
}

export function hasRecentWarnings(receivedActions, now = Date.now()) {
  return countRecentWarnings(receivedActions, now) > 0;
}
