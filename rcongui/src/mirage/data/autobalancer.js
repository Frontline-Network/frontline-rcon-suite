export const autobalancerConfig = {
  mode: "shadow",
  minimum_players: 40,
  target_difference: 2,
  skill_strategy: "balanced-v2",
  manual_proposal_timeout_seconds: 180,
};

export const autobalancerStatus = {
  mode: "shadow",
  phase: "observing",
  updated_at: new Date().toISOString(),
  team_counts: { allies: 41, axis: 39 },
  required_switches: 1,
  data_confidence: 1,
  team_ratings: { allies: 53.4, axis: 50.0 },
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
  type: "object",
  properties: {
    mode: {
      type: "string",
      enum: ["disabled", "shadow", "manual", "auto"],
    },
    minimum_players: { type: "integer", minimum: 0 },
    target_difference: { type: "integer", minimum: 0 },
    skill_strategy: {
      type: "string",
      enum: ["squad-first", "balanced-v2", "skill-first"],
    },
  },
};
