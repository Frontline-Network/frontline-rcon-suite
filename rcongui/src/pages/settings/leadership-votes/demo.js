// Synthetic demo only. No messages or commands ever reach a gameserver.
let config = {
  enabled: false,
  mode: "dry_run",
  confirmation_seconds: 60,
  warning_seconds: 60,
  duration_seconds: 120,
  minimum_participants: 3,
  leadership_seconds: 300,
  team_gap_seconds: 600,
  target_cooldown_seconds: 1800,
};
let vote = {
  id: "demo-leadership-vote",
  team: "allies",
  squad: "Able",
  target_id: "demo-leader",
  target_name: "Demo Squadleader",
  reason: "Squad gemeldet – Kommunikation prüfen",
  status: "rejected",
  yes: 2,
  no: 3,
  required: 5,
  participant_count: 8,
  target_role: "squadleader",
  mode: "dry_run",
  electorate: Object.fromEntries(
    Array.from({ length: 8 }, (_, n) => [
      `demo-${n}`,
      { name: `Demo Führung ${n + 1}` },
    ])
  ),
  ballots: {
    "demo-0": { yes: true },
    "demo-1": { yes: true },
    "demo-2": { yes: false },
    "demo-3": { yes: false },
    "demo-4": { yes: false },
  },
  result: "Demo: Zustimmung nicht erreicht – kein Kick",
};

if (
  new URLSearchParams(window.location.search).get("demo_vote_target") ===
  "commander"
) {
  vote.target_role = "commander";
  vote.target_name = "Demo Commander";
  vote.squad = "";
}

export function demoRequest(path, data, method) {
  if (path === "config") {
    if (method === "PUT") {
      const started = data.enabled && !config.enabled;
      config = { ...data };
      if (started)
        vote = {
          ...vote,
          status: "active",
          ends_at: Date.now() / 1000 + config.duration_seconds,
          result: null,
        };
      if (!config.enabled)
        vote = {
          ...vote,
          status: "cancelled",
          result: "Demo: Funktion ausgeschaltet",
        };
    }
    return structuredClone({ config, can_enable: true, conflicts: [] });
  }
  if (path === `votes/${vote.id}/cancel`)
    vote = {
      ...vote,
      status: "cancelled",
      result: "Demo: Von Moderator beendet",
    };
  if (path === "status")
    return structuredClone({ enabled: config.enabled, votes: [vote] });
  return structuredClone(vote);
}
