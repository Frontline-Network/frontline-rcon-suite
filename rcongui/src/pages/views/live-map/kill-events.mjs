const pointIsUsable = (point) =>
  point &&
  Number.isFinite(Number(point.x)) &&
  Number.isFinite(Number(point.y)) &&
  Number(point.x) >= 0 &&
  Number(point.x) <= 1 &&
  Number(point.y) >= 0 &&
  Number(point.y) <= 1;

const sampleIsFreshForEvent = (sampleAt, eventAt, maximumAge) => {
  const sample = Number(sampleAt);
  const event = Number(eventAt);
  const age = event - sample;
  return (
    Number.isFinite(sample) &&
    Number.isFinite(event) &&
    age >= 0 &&
    age <= maximumAge
  );
};

export function killConnection(event, maximumSampleAge = 3) {
  if (
    !pointIsUsable(event?.attacker_map_position) ||
    !pointIsUsable(event?.map_position) ||
    !sampleIsFreshForEvent(
      event.attacker_position_sample_at,
      event.time,
      maximumSampleAge
    ) ||
    !sampleIsFreshForEvent(
      event.position_sample_at,
      event.time,
      maximumSampleAge
    )
  )
    return null;

  return {
    from: {
      x: Number(event.attacker_map_position.x),
      y: Number(event.attacker_map_position.y),
    },
    to: {
      x: Number(event.map_position.x),
      y: Number(event.map_position.y),
    },
  };
}

export function visibleKillConnections({
  events,
  at,
  selected = null,
  showAll = false,
  windowSeconds = 8,
  limit = 12,
  maximumSampleAge = 3,
}) {
  const end = Number(at);
  if (!Number.isFinite(end)) return [];

  const unique = new Map();
  for (const event of events || []) {
    const eventAt = Number(event?.time);
    if (
      !event?.id ||
      !Number.isFinite(eventAt) ||
      eventAt > end ||
      eventAt < end - windowSeconds
    )
      continue;
    if (
      selected &&
      !showAll &&
      event.attacker !== selected &&
      event.victim !== selected
    )
      continue;
    const connection = killConnection(event, maximumSampleAge);
    if (connection) unique.set(event.id, { ...event, connection });
  }

  return [...unique.values()]
    .sort((left, right) => Number(right.time) - Number(left.time))
    .slice(0, limit)
    .reverse();
}
