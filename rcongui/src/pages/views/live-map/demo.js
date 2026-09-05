// Loaded only by the existing fake-build flag. Never used as a live fallback.
const now = () => Date.now() / 1000;
const roundId = "demo-hllv-round";
const config = { enabled: true, monitor_enabled: true };
let monitors = [
  {
    player_id: "demo-0",
    name: "Demo Spieler 01",
    scope: "permanent",
    aliases: ["demo-0"],
  },
];
const reviews = {};
let snapshotCount = 0;
function frame(time) {
  const params = new URLSearchParams(window.location.search);
  const hllMap = params.get("tacticalHllMap");
  const estimated = hllMap || params.get("tacticalScenario") === "estimated";
  const uncalibrated = params.get("tacticalScenario") === "uncalibrated";
  const players = Array.from({ length: 100 }, (_, i) => {
    const x = 0.1 + (i % 10) * 0.08 + Math.sin(time / 50 + i) * 0.015;
    const y = 0.1 + Math.floor(i / 10) * 0.08;
    return {
      player_id: `demo-${i}`,
      name: `Demo Spieler ${String(i + 1).padStart(2, "0")}`,
      team: i % 2 ? "axis" : "allies",
      unit_name: ["ABLE", "BAKER", "CHARLIE"][i % 3],
      role: i % 6 ? "rifleman" : "officer",
      position: {
        x: (x - (estimated ? 0.5 : 0)) * 200000,
        y: (y - (estimated ? 0.5 : 0)) * 200000,
        z: 0,
      },
      position_valid: true,
      position_m:
        estimated || uncalibrated ? null : { x: x * 2000, y: y * 2000, z: 0 },
      map_position: uncalibrated ? null : { x, y },
      deaths: i % 7,
      session_id: `session-${i}`,
      segment_id: `segment-${i}`,
    };
  });
  return {
    schema_version: 1,
    server_number: hllMap ? 1 : 3,
    game: hllMap ? "hll" : "hllv",
    round_id: roundId,
    captured_at: time,
    age_seconds: 0,
    map: hllMap
      ? {
          id: `${hllMap}_warfare`,
          pretty_name: `${hllMap} · Warfare`,
          map: { id: hllMap },
        }
      : {
          id: "wdeve_warfare_day",
          pretty_name: "Cam Ranh Port · Warfare",
          map: { id: "WDEV_E" },
        },
    calibration: uncalibrated
      ? null
      : estimated
      ? {
          verified: false,
          display_ready: true,
          quality: "estimated",
          units_per_meter: null,
        }
      : { verified: true, units_per_meter: 100 },
    players,
    objects: [],
    events: [],
    signals: [],
    collector_interval: 2,
    quality: {
      valid_positions: 100,
      total_players: 100,
      round_confirmed: true,
    },
  };
}
const signal = (time) => ({
  id: "demo-signal",
  kind: "review",
  round_id: roundId,
  attacker: "demo-1",
  victim: "demo-0",
  attacker_name: "Demo Spieler 02",
  victim_name: "Demo Spieler 01",
  count: 4,
  total_deaths: 5,
  share: 0.8,
  counterkills: 1,
  located_events: 4,
  first_at: time - 700,
  last_at: time - 20,
  review: reviews["demo-signal"],
  events: [700, 500, 200, 20].map((offset, i) => ({
    id: `demo-event-${i}`,
    time: time - offset,
    position_sample_at: time - offset - 1,
    map_position: { x: 0.3 + i * 0.1, y: 0.4 },
    weapon: "Demo-Waffe",
  })),
});

export async function demoRequest(path, data, method) {
  const url = new URL(path, "https://demo.invalid/");
  const time = now();
  if (url.pathname === "/capabilities")
    return {
      ...config,
      server_number: new URLSearchParams(window.location.search).has(
        "tacticalHllMap"
      )
        ? 1
        : 3,
      positions: "observed",
      permissions: { manage: true, cases: true },
    };
  if (url.pathname === "/settings") return Object.assign(config, data);
  if (url.pathname === "/snapshot") {
    const scenario = new URLSearchParams(window.location.search).get(
      "tacticalScenario"
    );
    const ages = [1, 1, 1, 8, 20, 20, 8, 1];
    const age =
      scenario === "stale-recovery"
        ? ages[Math.min(snapshotCount++, ages.length - 1)]
        : 0;
    const f = frame(time - age);
    f.age_seconds = age;
    f.signals = config.monitor_enabled && monitors.length ? [signal(time)] : [];
    return { enabled: config.enabled, snapshot: config.enabled ? f : null };
  }
  if (url.pathname === "/monitors") {
    if (method === "DELETE")
      monitors = monitors.filter((m) => m.player_id !== data.player_id);
    else if (method === "POST") {
      const p = frame(time).players.find((p) => p.player_id === data.player_id);
      monitors = [
        ...monitors.filter((m) => m.player_id !== p.player_id),
        { ...data, name: p.name, aliases: [p.player_id] },
      ];
    }
    return monitors;
  }
  if (url.pathname === "/rounds")
    return [{ round_id: roundId, start: time - 3600, end: time }];
  if (url.pathname === "/history") {
    const start = Number(url.searchParams.get("start")),
      end = Number(url.searchParams.get("end"));
    return {
      frames: Array.from(
        { length: Math.floor((end - start) / 2) + 1 },
        (_, i) => frame(start + i * 2)
      ),
    };
  }
  if (url.pathname === "/reviews") return reviews;
  if (url.pathname.startsWith("/reviews/")) {
    if (method === "GET")
      return {
        signal: signal(time),
        frames: Array.from({ length: 120 }, (_, i) =>
          frame(time - 240 + i * 2)
        ),
      };
    reviews["demo-signal"] = {
      incident_id: "demo-case",
      status:
        data.action === "claim"
          ? "claimed"
          : data.action === "dismiss"
          ? "dismissed"
          : "new",
      saved: data.action === "save",
      revision: 1,
    };
    return reviews["demo-signal"];
  }
  throw new Error("Unknown demo route");
}
