export const RECOMMENDATION_HOLD_MS = 60_000;

// Identity describes the reviewed move, never its changing rank or score.
export function recommendationKey(value) {
  if (!value) return null;
  if (value.moves) {
    return JSON.stringify([
      value.kind,
      value.moves
        .map((move) => [
          move.source_team,
          move.target_team,
          move.squad_name,
          [...move.player_ids].sort(),
        ])
        .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b))),
    ]);
  }
  if (value.kind === "strength_swap") {
    return JSON.stringify([
      value.kind,
      value.stronger_team,
      value.weaker_team,
      value.stronger_player.player_id,
      value.weaker_player.player_id,
    ]);
  }
  return JSON.stringify([
    "move",
    value.source_team,
    value.target_team,
    value.player.player_id,
  ]);
}

export function preferRecommendation(values, preferred) {
  const key = recommendationKey(preferred);
  const selected =
    key && values.find((value) => recommendationKey(value) === key);
  return selected
    ? [selected, ...values.filter((value) => value !== selected)]
    : values;
}

export function balanceRecommendations(status) {
  if (!status) return [];
  if (status.squad_recommendation)
    return [
      status.squad_recommendation,
      ...status.squad_recommendation_alternatives,
    ];
  if (status.strength_swap)
    return [status.strength_swap, ...status.strength_swap_alternatives];
  return status.proposal
    ? [
        {
          kind: "move",
          source_team: status.plan.source_team,
          target_team: status.plan.target_team,
          player: status.proposal,
          rating_gap_before: status.plan.rating_gap_before,
          projected_rating_gap: status.plan.projected_rating_gap,
          projected_team_ratings: status.plan.projected_team_ratings,
          rating_confidence: status.proposal.rating_confidence,
        },
      ]
    : [];
}

export function holdRecommendations(previous, current, now, reviewing = false) {
  if (previous?.items.length && (reviewing || now < previous.expiresAt))
    return previous;
  if (!previous?.items.length && !current.length) return previous;
  return { items: current, expiresAt: now + RECOMMENDATION_HOLD_MS };
}

export function recommendationStatus(status, recommendations) {
  if (!status) return null;
  const [first, ...alternatives] = recommendations;
  const squad = first?.kind?.startsWith("squad_");
  const swap = first?.kind === "strength_swap";
  const move = first?.kind === "move";
  return {
    ...status,
    squad_recommendation: squad ? first : null,
    squad_recommendation_alternatives: squad ? alternatives : [],
    strength_swap: swap ? first : null,
    strength_swap_alternatives: swap ? alternatives : [],
    proposal: move ? first.player : null,
    plan: move
      ? {
          source_team: first.source_team,
          target_team: first.target_team,
          rating_gap_before: first.rating_gap_before,
          projected_rating_gap: first.projected_rating_gap,
          projected_team_ratings: first.projected_team_ratings,
        }
      : null,
  };
}
