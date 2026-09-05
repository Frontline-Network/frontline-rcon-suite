export function projectionReady(calibration) {
  return Boolean(
    calibration &&
      (calibration.verified === true ||
        (calibration.display_ready === true &&
          calibration.quality === "estimated"))
  );
}

export function filterPlayers(players, search, team, squad) {
  const needle = search.toLocaleLowerCase();
  return players.filter(
    (p) =>
      (!needle ||
        `${p.name} ${p.player_id}`.toLocaleLowerCase().includes(needle)) &&
      (team === "all" || p.team === team) &&
      (squad === "all" || p.unit_name === squad)
  );
}

export function trailSegments(frames, playerId, roundId, until) {
  const lines = [];
  let lastSegment, current;
  for (const frame of frames) {
    if (frame.round_id !== roundId || frame.captured_at > until) continue;
    const player = frame.players.find((p) => p.player_id === playerId);
    if (!player?.map_position) {
      lastSegment = null;
      continue;
    }
    if (lastSegment !== player.segment_id) {
      current = [];
      lines.push(current);
    }
    current.push(player.map_position);
    lastSegment = player.segment_id;
  }
  return lines.filter((line) => line.length > 1);
}

export function frameAt(frames, cursor) {
  return [...frames].reverse().find((f) => f.captured_at <= cursor) ?? null;
}
