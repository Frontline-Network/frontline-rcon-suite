// Loaded only by the existing fake-build flag. Never used as a live fallback.
const now = () => Date.now() / 1000;
const roundId = "demo-hllv-round";
const config = {
  enabled: true,
  monitor_enabled: true,
  archive_enabled: true,
  detection_enabled: true,
  detection_profile: {
    min_kills: 25,
    killrate_infantry: 1.25,
    killrate_mg: 1.5,
    killrate_armor: 2,
    killrate_artillery: 3,
    burst_kills: 6,
    burst_unique_victims: 4,
    burst_seconds: 60,
    movement_mps: 50,
    movement_consecutive: 2,
  },
};
let monitors = [
  {
    player_id: "demo-0",
    name: "Demo Spieler 01",
    scope: "permanent",
    aliases: ["demo-0"],
  },
];
const reviews = {};
let archives = [];
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
    events: [
      {
        id: "demo-live-kill",
        time: time - 1,
        attacker: "demo-1",
        victim: "demo-0",
        attacker_name: "Demo Spieler 02",
        victim_name: "Demo Spieler 01",
        attacker_position_sample_at: time - 2,
        attacker_map_position: players[1].map_position,
        position_sample_at: time - 2,
        map_position: players[0].map_position,
        weapon: "Demo-Waffe",
        teamkill: false,
      },
    ],
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
  events: [700, 500, 200, 5].map((offset, i) => ({
    id: `demo-event-${i}`,
    time: time - offset,
    position_sample_at: time - offset - 1,
    map_position: { x: 0.3 + i * 0.1, y: 0.4 },
    attacker_position_sample_at: time - offset - 1,
    attacker_map_position: { x: 0.15 + i * 0.1, y: 0.25 },
    weapon: "Demo-Waffe",
  })),
});
const detection = (time) => ({
  id: "demo-detection",
  round_id: roundId,
  player_id: "demo-2",
  player_name: "Demo Spieler 03",
  kind: "gameplay_pattern",
  severity: "review",
  first_at: time - 900,
  last_at: time - 30,
  rule_version: "2",
  status: "open",
  review: reviews["demo-detection"],
  evidence: {
    signals: [
      {
        kind: "kill_rate",
        category: "infantry",
        kills: 27,
        kpm: 1.42,
        threshold: 1.25,
      },
      {
        kind: "kill_burst",
        kills: 6,
        unique_victims: 5,
        seconds: 48,
      },
    ],
  },
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
      permissions: { manage: true, cases: true, archives: true },
      archive_retention_days: [30, 90],
      archive_limits: { rounds: 50, bytes: 1073741824 },
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
    f.detections = config.detection_enabled ? [detection(time)] : [];
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
    return [
      {
        round_id: roundId,
        start: time - 3600,
        end: time,
        archive: archives.find((item) => item.round_id === roundId),
      },
    ];
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
  if (url.pathname === "/events")
    return {
      events: signal(time).events.map((item) => ({
        ...item,
        attacker: "demo-1",
        victim: "demo-0",
        attacker_name: "Demo Spieler 02",
        victim_name: "Demo Spieler 01",
        teamkill: item.id === "demo-event-3",
      })),
      markers: [
        {
          id: "demo-detection",
          time: time - 30,
          kind: "detection",
          severity: "review",
          player_id: "demo-2",
          player_name: "Demo Spieler 03",
        },
      ],
    };
  if (url.pathname === "/detections")
    return { detections: config.detection_enabled ? [detection(time)] : [] };
  if (url.pathname === "/detections/demo-detection")
    return {
      ...detection(time),
      previous_24h: [
        {
          ...detection(time - 7200),
          id: "demo-detection-previous",
          round_id: "demo-hllv-previous-round",
          severity: "observation",
        },
      ],
      profile_context: {
        source: "Steam Web API",
        has_bans: false,
        steam_bans: {},
        note: "Profilkontext; fließt nicht in Auslösung oder Priorität ein.",
      },
    };
  if (url.pathname === "/archives") {
    if (method === "POST") {
      const item = {
        id: `demo-archive-${Date.now()}`,
        round_id: data.round_id,
        start: time - 3600,
        end: time,
        expires_at: time + data.retention_days * 86400,
        retention_days: data.retention_days,
        reason: data.reason,
        status: "collecting",
        bytes: 12582912,
        expires_soon: false,
      };
      archives = [item];
      return item;
    }
    return { archives };
  }
  if (url.pathname.startsWith("/archives/")) {
    const id = url.pathname.split("/").at(-1);
    if (method === "DELETE") {
      const result = archives.find((item) => item.id === id);
      archives = archives.filter((item) => item.id !== id);
      return result;
    }
    archives = archives.map((item) =>
      item.id === id
        ? {
            ...item,
            retention_days: data.retention_days,
            expires_at: time + data.retention_days * 86400,
          }
        : item
    );
    return archives.find((item) => item.id === id);
  }
  if (url.pathname === "/reviews") return reviews;
  if (url.pathname.startsWith("/reviews/")) {
    if (method === "GET")
      return {
        signal: url.pathname.endsWith("demo-detection")
          ? detection(time)
          : signal(time),
        frames: Array.from({ length: 120 }, (_, i) =>
          frame(time - 240 + i * 2)
        ),
      };
    const id = url.pathname.split("/").at(-1);
    reviews[id] = {
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
    return reviews[id];
  }
  throw new Error("Unknown demo route");
}
