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
    isPlayerMessage(action) &&
    typeof action.by === "string" &&
    INFORMATIONAL_SENDERS.some((prefix) => action.by.startsWith(prefix))
  );
}

export function isPlayerMessage(action) {
  return action?.action_type === "MESSAGE";
}

export function isModerationAction(action) {
  return Boolean(action?.action_type) && !isInformationalPlayerMessage(action);
}

export function countRecentWarnings(receivedActions, now = Date.now()) {
  if (receivedActions && !Array.isArray(receivedActions)) {
    const count = receivedActions.recent_warning_count;
    if (Number.isInteger(count) && count >= 0) return count;
    receivedActions = receivedActions.received_actions;
  }
  if (!Array.isArray(receivedActions)) return 0;
  const earliest = now - RECENT_WARNING_WINDOW_MS;
  return receivedActions.filter((action) => {
    if (!isModerationAction(action)) return false;
    const timestamp = Date.parse(action?.time);
    return Number.isFinite(timestamp) && timestamp > earliest;
  }).length;
}

export function hasRecentWarnings(receivedActions, now = Date.now()) {
  return countRecentWarnings(receivedActions, now) > 0;
}
