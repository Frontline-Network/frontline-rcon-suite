export const autobalancerConfig = {
  mode: "shadow",
  poll_interval_seconds: 5,
  minimum_players: 40,
  target_difference: 2,
  stable_difference_seconds: 45,
  volunteer_phase_seconds: 30,
  map_start_grace_minutes: 5,
  map_end_guard_minutes: 10,
  candidate_timeout_seconds: 180,
  manual_proposal_timeout_seconds: 120,
  connection_grace_seconds: 120,
  cooldown_maps: 3,
  max_switches_per_incident: 3,
  coordinated_squad_switches_enabled: true,
  allow_individual_squad_fallback: false,
  death_event_max_age_seconds: 5,
  switch_confirmation_timeout_seconds: 15,
  history_server_numbers: [1, 2],
  skill_strategy: "balanced-v2",
  skill_gap_soft_limit: 8,
  skill_gap_hard_warning: 12,
  skill_gap_min_improvement: 2.5,
  history_half_life_days: 30,
  volunteer_command: "!balance",
  message_language: "de+en",
  messages_en: {
    volunteer_request:
      "The teams are uneven. Volunteer to join {target_team}: type !balance within {seconds} seconds.",
    volunteer_registered:
      "Thank you! You have volunteered for this balance call.",
    candidate_selected:
      "You have been selected to join {target_team}. You will switch after your next death, then be protected for {cooldown_maps} maps.",
    switch_completed:
      "Thank you for helping! You have joined {target_team} and are protected from another automatic switch for {cooldown_maps} maps.",
    squad_switch_selected:
      "Your squad {squad_name} will now move together to {target_team}. Please recreate the squad there afterwards.",
    squad_switch_completed:
      "The move to {target_team} is complete. Please recreate squad {squad_name} on that team.",
    squad_switch_aborted:
      "Squad {squad_name} could not be moved completely. Please wait for instructions from an admin.",
  },
  messages: {
    volunteer_request:
      "Die Teams sind unausgeglichen. Freiwilliger Wechsel zu {target_team}: Schreibe innerhalb von {seconds} Sekunden !balance.",
    volunteer_registered:
      "Danke! Deine freiwillige Meldung gilt für diesen Balance-Vorfall.",
    candidate_selected:
      "Du wurdest für den Teamausgleich zu {target_team} ausgewählt.",
    switch_completed: "Danke für deine Mithilfe beim Teamausgleich.",
    squad_switch_selected:
      "Euer Squad {squad_name} wird jetzt gemeinsam zu {target_team} verschoben. Bitte bildet den Squad dort anschließend neu.",
    squad_switch_completed:
      "Der gemeinsame Wechsel zu {target_team} ist abgeschlossen. Bitte bildet Squad {squad_name} in diesem Team neu.",
    squad_switch_aborted:
      "Der gemeinsame Wechsel von Squad {squad_name} konnte nicht vollständig ausgeführt werden. Bitte wartet auf eine Anweisung der Moderation.",
  },
};

export const autobalancerStatus = {
  mode: "shadow",
  phase: "observing",
  updated_at: new Date().toISOString(),
  team_counts: { allies: 49, axis: 49 },
  target_difference: 2,
  required_switches: 0,
  data_confidence: 0.91,
  team_ratings: { allies: 46.0, axis: 63.0 },
  team_rating_confidence: { allies: 0.88, axis: 0.92 },
  strength_thresholds: {
    soft_limit: 8,
    hard_warning: 12,
    minimum_improvement: 2.5,
  },
  strength_swap: {
    kind: "strength_swap",
    advisory_only: true,
    stronger_team: "axis",
    weaker_team: "allies",
    stronger_player: {
      player_id: "76561198000000005",
      player_name: "FLN_Falcon",
      team: "axis",
      unit_name: "Baker",
      role: "rifleman",
      rating: 72,
      rating_confidence: 0.86,
      protection_tier: 2,
      protection_reason: "Mitglied eines unvollständigen Infantry-Squads",
    },
    weaker_player: {
      player_id: "76561198000000002",
      player_name: "FLN_Wolf",
      team: "allies",
      unit_name: "Able",
      role: "rifleman",
      rating: 38,
      rating_confidence: 0.84,
      protection_tier: 2,
      protection_reason: "Mitglied eines unvollständigen Infantry-Squads",
    },
    rating_gap_before: 17,
    projected_rating_gap: 1.4,
    rating_improvement: 15.6,
    rating_confidence: 0.84,
  },
  strength_swap_alternatives: [
    {
      kind: "strength_swap",
      advisory_only: true,
      stronger_team: "axis",
      weaker_team: "allies",
      stronger_player: {
        player_id: "76561198000000006",
        player_name: "FLN_Bravo",
        team: "axis",
        rating: 69,
        rating_confidence: 0.81,
      },
      weaker_player: {
        player_id: "76561198000000003",
        player_name: "FLN_Valkyrie",
        team: "allies",
        rating: 41,
        rating_confidence: 0.8,
      },
      rating_gap_before: 17,
      projected_rating_gap: 3.2,
      rating_improvement: 13.8,
      rating_confidence: 0.8,
    },
  ],
  strategy: "balanced-v2",
  rating_model_version: "rating-v3",
  warnings: [],
  block_reasons: [],
};

const decision = ({
  id,
  playerName,
  ageMinutes,
  tier,
  gapAfter,
  confidence,
  role,
  roleFamily,
  unitName,
  selectionReason,
}) => ({
  decision_id: id,
  incident_id: `incident-${id}`,
  round_id: "1786220040:omaha-beach-warfare",
  created_at: new Date(Date.now() - ageMinutes * 60_000).toISOString(),
  map_name: "Omaha Beach Warfare",
  allies_count: 41,
  axis_count: 39,
  difference: 2,
  simulated_difference_after: 0,
  size_overshoot: false,
  source_team: "allies",
  target_team: "axis",
  player_id: `player-${id}`,
  player_name: playerName,
  volunteer: false,
  protection_tier: tier,
  rating: 51,
  rating_confidence: confidence,
  rating_raw: 54,
  rating_role_family: roleFamily,
  rating_history_source: "shared-pool",
  rating_model_version: "rating-v3",
  strategy_version: "balanced-v2",
  selection_reason: selectionReason,
  required_switches: 1,
  projected_rating_gap: gapAfter,
  rating_gap_before: 3.4,
  strategy_plans: {
    "squad-first": {
      player_id: `player-${id}`,
      player_name: playerName,
      base_tier: tier,
      effective_tier: tier,
      projected_rating_gap: gapAfter,
      rating_gap_before: 3.4,
      warnings: [],
    },
    "balanced-v2": {
      player_id: `player-${id}`,
      player_name: playerName,
      base_tier: tier,
      effective_tier: tier,
      projected_rating_gap: gapAfter,
      rating_gap_before: 3.4,
      warnings: [],
    },
    "skill-first": {
      player_id: "player-maverik",
      player_name: "MaverikScab8",
      base_tier: 3,
      effective_tier: 3,
      projected_rating_gap: 2.6,
      rating_gap_before: 3.4,
      warnings: ["Stärkerer Eingriff in einen stabilen Squad"],
    },
  },
  strategies_agree: false,
  unit_name: unitName,
  unit_type: "Infantry",
  unit_size: tier >= 3 ? 6 : 3,
  role,
  is_leader: role === "Officer",
  connected_seconds: 4920,
  squad_seconds: tier >= 3 ? 4100 : 620,
  review_verdict: null,
  review_category: null,
  review_comment: null,
  reviewed_by: null,
  reviewed_at: null,
  review_preferred_strategy: null,
  review_preferred_player_id: null,
  audit_warnings: [],
});

export const autobalancerShadowOverview = {
  live_status: autobalancerStatus,
  timeline: [],
  summary: {
    proposals: 20,
    rounds_observed: 12,
    reviewed: 8,
    pending_review: 12,
    accepted: 7,
    rejected: 1,
    acceptance_rate: 0.875,
    reviewed_rounds: 5,
    median_rating_confidence: 0.34,
    gap_guardrail_rate: 0.96,
    rule_warning_proposals: 0,
    protection_tiers: { 0: 4, 1: 8, 2: 5, 3: 3 },
    rejection_categories: { squad_should_stay: 1 },
  },
  pilot_goals: {
    ready_for_manual: false,
    reviewed_rounds_target: 10,
    reviewed_rounds_met: false,
    reviewed_proposals_target: 20,
    reviewed_proposals_met: false,
    acceptance_rate_target: 0.9,
    acceptance_rate_met: false,
    rating_confidence_target: 0.6,
    rating_confidence_met: false,
    gap_guardrail_target: 0.95,
    gap_guardrail_met: true,
  },
  decisions: [
    decision({
      id: "rehjaeger",
      playerName: "Rehjäger Stoffel",
      ageMinutes: 2,
      tier: 1,
      gapAfter: 3.9,
      confidence: 0.34,
      role: "Rifleman",
      roleFamily: "combat_infantry",
      unitName: "Able",
      selectionReason:
        "Geringster Eingriff in einen Squad bei vollständigem Live-Snapshot.",
    }),
    decision({
      id: "maverik",
      playerName: "MaverikScab8",
      ageMinutes: 4,
      tier: 3,
      gapAfter: 2.6,
      confidence: 0.68,
      role: "Automatic Rifleman",
      roleFamily: "combat_infantry",
      unitName: "Baker",
      selectionReason:
        "Verbessert die geschätzte Teamstärke, greift aber in einen stabilen Squad ein.",
    }),
    decision({
      id: "bismarck",
      playerName: "Otto von Bismarck",
      ageMinutes: 7,
      tier: 4,
      gapAfter: 2.9,
      confidence: 0.72,
      role: "Officer",
      roleFamily: "leader",
      unitName: "Charlie",
      selectionReason:
        "Guter Stärkeausgleich, jedoch durch die Squad-Lead-Rolle geschützt.",
    }),
  ],
};

export const reviewAutobalancerShadowDecision = (payload) => {
  const decision = autobalancerShadowOverview.decisions.find(
    (item) => item.decision_id === payload.decision_id
  );
  if (!decision) return null;

  const summary = autobalancerShadowOverview.summary;
  const goals = autobalancerShadowOverview.pilot_goals;
  const previousVerdict = decision.review_verdict;
  const previousCategory = decision.review_category;

  if (!previousVerdict) {
    summary.reviewed += 1;
    summary.pending_review = Math.max(0, summary.pending_review - 1);
  } else if (previousVerdict === "accepted") {
    summary.accepted = Math.max(0, summary.accepted - 1);
  } else if (previousVerdict === "rejected") {
    summary.rejected = Math.max(0, summary.rejected - 1);
    if (previousCategory && summary.rejection_categories?.[previousCategory]) {
      summary.rejection_categories[previousCategory] -= 1;
    }
  }

  decision.review_verdict = payload.verdict;
  decision.review_category =
    payload.verdict === "rejected" ? payload.category : null;
  decision.review_comment = payload.comment || null;
  decision.reviewed_by = "Frontline Admin";
  decision.reviewed_at = new Date().toISOString();
  decision.review_preferred_strategy = payload.preferred_strategy || null;
  decision.review_preferred_player_id = payload.preferred_player_id || null;

  if (payload.verdict === "accepted") {
    summary.accepted += 1;
  } else {
    summary.rejected += 1;
    const category = payload.category || "other";
    summary.rejection_categories ||= {};
    summary.rejection_categories[category] =
      (summary.rejection_categories[category] || 0) + 1;
  }

  summary.acceptance_rate = summary.reviewed
    ? summary.accepted / summary.reviewed
    : null;
  goals.reviewed_proposals_met =
    summary.reviewed >= goals.reviewed_proposals_target;
  goals.acceptance_rate_met =
    summary.acceptance_rate >= goals.acceptance_rate_target;
  goals.rating_confidence_met =
    summary.median_rating_confidence >= goals.rating_confidence_target;
  goals.ready_for_manual = Boolean(
    goals.reviewed_rounds_met &&
      goals.reviewed_proposals_met &&
      goals.acceptance_rate_met &&
      goals.rating_confidence_met &&
      goals.gap_guardrail_met
  );

  return decision;
};

export const autobalancerHistoryDashboard = {
  generated_at: new Date().toISOString(),
  source_counts: {
    live_snapshots: 9,
    historical_logs: 3,
  },
  rating_quality: {
    fully_captured_rounds: 9,
    snapshot_coverage: 0.91,
    median_rating_confidence: 0.58,
    gap_guardrail_rate: 0.96,
    confidence_distribution: {
      low: 2,
      medium: 5,
      high: 5,
    },
  },
  backfill: {
    complete: true,
    analyzed_rounds: 12,
    requested_rounds: 12,
  },
  summary: {
    rounds_analyzed: 12,
    measurable_rounds: 11,
    coverage_ratio: 0.91,
    balanced_time_ratio: 0.73,
    incidents_per_10_rounds: 3.3,
    switches_per_round: 0.7,
    weekly: [
      { week: "KW 29", balanced_ratio: 0.64 },
      { week: "KW 30", balanced_ratio: 0.69 },
      { week: "KW 31", balanced_ratio: 0.73 },
      { week: "KW 32", balanced_ratio: 0.78 },
    ],
    quality_levels: { hoch: 9, mittel: 2, niedrig: 1 },
    difference_distribution: [
      { difference: 0, seconds: 3810 },
      { difference: 1, seconds: 2840 },
      { difference: 2, seconds: 1960 },
      { difference: 3, seconds: 610 },
      { difference: 4, seconds: 220 },
    ],
    maps: [
      { map_name: "Omaha Beach Warfare", balanced_ratio: 0.76 },
      { map_name: "Carentan Warfare", balanced_ratio: 0.71 },
      { map_name: "Sainte-Marie-du-Mont Warfare", balanced_ratio: 0.69 },
    ],
  },
  what_if: [
    {
      strategy: "squad-first",
      label: "Squad zuerst",
      balanced_time_ratio: 0.7,
      switches_per_round: 0.5,
    },
    {
      strategy: "balanced-v2",
      label: "Ausgewogen V2",
      balanced_time_ratio: 0.78,
      switches_per_round: 0.7,
    },
    {
      strategy: "skill-first",
      label: "Stärke zuerst",
      balanced_time_ratio: 0.75,
      switches_per_round: 0.9,
    },
  ],
};

export const autobalancerRoundArchive = {
  total: 3,
  page: 1,
  page_size: 12,
  analysis: null,
  rounds: [
    {
      map_id: "round-omaha-1",
      start: new Date(Date.now() - 2 * 60 * 60_000).toISOString(),
      duration_seconds: 4110,
      map_name: "Omaha Beach Warfare",
      result: { allies: 5, axis: 3 },
      shadow_proposals: 3,
    },
    {
      map_id: "round-carentan-1",
      start: new Date(Date.now() - 26 * 60 * 60_000).toISOString(),
      duration_seconds: 3570,
      map_name: "Carentan Warfare",
      result: { allies: 2, axis: 5 },
      shadow_proposals: 2,
    },
    {
      map_id: "round-smdm-1",
      start: new Date(Date.now() - 50 * 60 * 60_000).toISOString(),
      duration_seconds: 3890,
      map_name: "Sainte-Marie-du-Mont Warfare",
      result: { allies: 5, axis: 4 },
      shadow_proposals: 1,
    },
  ],
};

export const autobalancerSchema = {
  $defs: {
    AutobalancerMessages: {
      type: "object",
      properties: {
        volunteer_request: { type: "string" },
        volunteer_registered: { type: "string" },
        candidate_selected: { type: "string" },
        switch_completed: { type: "string" },
        squad_switch_selected: { type: "string" },
        squad_switch_completed: { type: "string" },
        squad_switch_aborted: { type: "string" },
      },
    },
  },
  type: "object",
  properties: {
    mode: {
      type: "string",
      enum: ["disabled", "shadow", "manual", "auto"],
    },
    poll_interval_seconds: { type: "integer", minimum: 2, maximum: 60 },
    minimum_players: { type: "integer", minimum: 0, maximum: 100 },
    target_difference: { type: "integer", minimum: 0, maximum: 10 },
    stable_difference_seconds: { type: "integer", minimum: 5, maximum: 600 },
    volunteer_phase_seconds: { type: "integer", minimum: 0, maximum: 300 },
    map_start_grace_minutes: { type: "integer", minimum: 0, maximum: 60 },
    map_end_guard_minutes: { type: "integer", minimum: 0, maximum: 60 },
    candidate_timeout_seconds: { type: "integer", minimum: 15, maximum: 900 },
    manual_proposal_timeout_seconds: {
      type: "integer",
      minimum: 15,
      maximum: 900,
    },
    connection_grace_seconds: { type: "integer", minimum: 0, maximum: 1800 },
    cooldown_maps: { type: "integer", minimum: 0, maximum: 20 },
    max_switches_per_incident: { type: "integer", minimum: 1, maximum: 10 },
    coordinated_squad_switches_enabled: { type: "boolean" },
    allow_individual_squad_fallback: { type: "boolean" },
    death_event_max_age_seconds: { type: "integer", minimum: 1, maximum: 30 },
    switch_confirmation_timeout_seconds: {
      type: "integer",
      minimum: 5,
      maximum: 60,
    },
    history_server_numbers: { type: "array", items: { type: "integer" } },
    skill_strategy: {
      type: "string",
      enum: ["squad-first", "balanced-v2"],
    },
    skill_gap_soft_limit: { type: "number", minimum: 0, maximum: 100 },
    skill_gap_hard_warning: { type: "number", minimum: 0, maximum: 100 },
    skill_gap_min_improvement: { type: "number", minimum: 0, maximum: 100 },
    history_half_life_days: { type: "integer", minimum: 1, maximum: 365 },
    volunteer_command: { type: "string", minLength: 2, maxLength: 32 },
    message_language: {
      type: "string",
      enum: ["de", "en", "de+en"],
      default: "de",
    },
    messages_en: { $ref: "#/$defs/AutobalancerMessages" },
    messages: { $ref: "#/$defs/AutobalancerMessages" },
  },
};
