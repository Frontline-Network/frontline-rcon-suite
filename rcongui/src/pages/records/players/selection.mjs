/** Batch forms fetch their own context and only need the chosen account ID/name. */
export function recordRecipient(player) {
  const playerId = player.player_id;
  const name = player.name ?? player.account?.name ?? player.names?.[0]?.name ??
    player.soldier?.name ?? playerId;
  return { player_id: playerId, name, player_name: name, names: [{ name }] };
}

export function toggleRecordSelection(previous, player) {
  const selected = new Map(previous);
  if (selected.has(player.player_id)) selected.delete(player.player_id);
  else selected.set(player.player_id, recordRecipient(player));
  return selected;
}

export function selectRecordPage(previous, players) {
  const selected = new Map(previous);
  for (const player of players) {
    selected.set(player.player_id, recordRecipient(player));
  }
  return selected;
}
