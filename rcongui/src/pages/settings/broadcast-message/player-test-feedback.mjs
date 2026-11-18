export function playerTestErrorKey(message) {
  if (message === "RCON rejected the player message") return "settings.campaigns.playerTestRejected";
  if (message === "Message delivery could not be confirmed; it may have been delivered") return "settings.campaigns.playerTestUnconfirmed";
  return null;
}
