import {
  balanceRecommendations,
  preferRecommendation,
  recommendationKey,
} from "./balance-recommendations.mjs";

const TEAM_NAMES = ["allies", "axis"];

const LEADER_ROLES = new Set([
  "armycommander",
  "commander",
  "officer",
  "squadleader",
  "tankcommander",
  "spotter",
  "artilleryobserver",
  "mortarobserver",
  "helicopterlogisticsofficer",
]);

const SPECIAL_SQUAD_TYPES = new Set([
  "armor",
  "armour",
  "recon",
  "artillery",
  "mortar",
  "helicopter",
]);

const finiteNumber = (value) => {
  if (value === null || value === undefined || value === "") return null;
  const number = Number(value);
  return Number.isFinite(number) ? number : null;
};

const normalizeKey = (value) =>
  String(value ?? "")
    .trim()
    .toLowerCase()
    .replace(/[\s_-]+/g, "");

const currentPlaytime = (player) =>
  finiteNumber(
    player?.current_playtime_seconds ??
      player?.profile?.current_playtime_seconds ??
      player?.map_playtime_seconds
  ) ?? 0;

const percentileMap = (entries) => {
  const valid = entries
    .filter(([, value]) => Number.isFinite(value))
    .sort((left, right) => left[1] - right[1]);
  const result = new Map(entries.map(([key]) => [key, 50]));
  if (valid.length < 2) return result;

  valid.forEach(([key, value]) => {
    const lower = valid.findIndex((entry) => entry[1] === value);
    const upper =
      valid.length -
      1 -
      [...valid].reverse().findIndex((entry) => entry[1] === value);
    const rank = (lower + upper) / 2;
    result.set(key, (rank / (valid.length - 1)) * 100);
  });
  return result;
};

const flattenLivePlayers = (teams) => {
  const players = [];
  TEAM_NAMES.forEach((teamName) => {
    const team = teams?.[teamName];
    if (!team) return;
    if (team.commander) {
      players.push({
        ...team.commander,
        team: teamName,
        is_leader: true,
        unit_type: "commander",
      });
    }
    Object.entries(team.squads ?? {}).forEach(([unitName, squad]) => {
      const squadPlayers = squad?.players ?? [];
      squadPlayers.forEach((player) => {
        const role = normalizeKey(player.role);
        players.push({
          ...player,
          team: teamName,
          unit_name: player.unit_name ?? unitName,
          unit_type: player.unit_type ?? squad?.type ?? "",
          unit_size: player.unit_size ?? squadPlayers.length,
          is_leader: Boolean(player.is_leader) || LEADER_ROLES.has(role),
        });
      });
    });
  });
  return players.filter((player) => player?.player_id);
};

const addLiveRatings = (players) => {
  const levelScores = percentileMap(
    players.map((player) => [player.player_id, finiteNumber(player.level)])
  );
  const performanceEntries = players.map((player) => {
    const seconds = currentPlaytime(player);
    const minutes = seconds > 0 ? seconds / 60 : null;
    if (!minutes) return [player.player_id, null];
    const kills = (finiteNumber(player.kills) ?? 0) / minutes;
    const combat = (finiteNumber(player.combat) ?? 0) / minutes;
    const teamwork =
      ((finiteNumber(player.offense) ?? 0) +
        (finiteNumber(player.defense) ?? 0) +
        (finiteNumber(player.support) ?? 0)) /
      minutes;
    return [player.player_id, kills * 8 + combat * 0.3 + teamwork * 0.14];
  });
  const performanceScores = percentileMap(performanceEntries);
  const performanceAvailable = new Set(
    performanceEntries
      .filter(([, value]) => Number.isFinite(value))
      .map(([playerId]) => playerId)
  );

  return players.map((player) => {
    const levelAvailable = Number.isFinite(finiteNumber(player.level));
    const liveAvailable = performanceAvailable.has(player.player_id);
    const level = levelScores.get(player.player_id) ?? 50;
    const performance = performanceScores.get(player.player_id) ?? 50;
    const rating =
      levelAvailable && liveAvailable
        ? level * 0.45 + performance * 0.55
        : levelAvailable
        ? level
        : liveAvailable
        ? performance
        : 50;
    const liveCoverage = Math.min(1, currentPlaytime(player) / (15 * 60));
    const confidence = Math.min(
      1,
      (levelAvailable ? 0.65 : 0) + (liveAvailable ? 0.35 * liveCoverage : 0)
    );
    return {
      ...player,
      live_rating: rating,
      live_confidence: confidence,
    };
  });
};

const average = (values) =>
  values.length
    ? values.reduce((total, value) => total + value, 0) / values.length
    : 50;

const teamRating = (players, team) =>
  average(
    players
      .filter((player) => player.team === team)
      .map((player) => player.live_rating)
  );

const eligiblePlayer = (player, allowIndividualSquadFallback = true) =>
  !player.is_leader &&
  !LEADER_ROLES.has(normalizeKey(player.role)) &&
  !SPECIAL_SQUAD_TYPES.has(normalizeKey(player.unit_type)) &&
  (allowIndividualSquadFallback || Number(player.unit_size || 0) <= 1);

const publicPlayer = (player) => ({
  player_id: player.player_id,
  player_name: player.name,
  team: player.team,
  unit_name: player.unit_name,
  unit_type: player.unit_type,
  role: player.role,
  rating: Number(player.live_rating.toFixed(2)),
  rating_confidence: Number(player.live_confidence.toFixed(3)),
  protection_tier: 2,
  protection_reason: "Live-Kandidat ohne Führungsrolle oder Spezialtrupp",
});

const publicSquad = (squad) => ({
  team: squad.team,
  squad_name: squad.squad_name,
  squad_type: squad.squad_type,
  member_count: squad.members.length,
  members: squad.members.map((player) => ({
    player_id: player.player_id,
    player_name: player.name,
    role: player.role,
    rating: Number(player.live_rating.toFixed(2)),
    rating_confidence: Number(player.live_confidence.toFixed(3)),
  })),
});

const regularSquads = (players) => {
  const groups = new Map();
  players.forEach((player) => {
    const squadName = String(player.unit_name ?? "").trim();
    const squadType = normalizeKey(player.unit_type);
    if (!squadName || SPECIAL_SQUAD_TYPES.has(squadType)) return;
    const key = `${player.team}:${squadName.toLocaleLowerCase()}`;
    if (!groups.has(key)) {
      groups.set(key, {
        team: player.team,
        squad_name: squadName,
        squad_type: player.unit_type || "infantry",
        members: [],
      });
    }
    groups.get(key).members.push(player);
  });
  return [...groups.values()].filter((squad) => squad.members.length >= 2);
};

const projectedGroupRatings = (players, moves) => {
  const targetByPlayer = new Map();
  moves.forEach((move) =>
    move.squad.members.forEach((player) =>
      targetByPlayer.set(player.player_id, move.target_team)
    )
  );
  const projected = players.map((player) => ({
    ...player,
    team: targetByPlayer.get(player.player_id) ?? player.team,
  }));
  return Object.fromEntries(
    TEAM_NAMES.map((team) => [
      team,
      Number(teamRating(projected, team).toFixed(2)),
    ])
  );
};

const ratingGap = (ratings) => Math.abs(ratings.allies - ratings.axis);

const squadMovePayload = (squad, targetTeam) => ({
  source_team: squad.team,
  target_team: targetTeam,
  squad_name: squad.squad_name,
  player_ids: squad.members.map((player) => player.player_id),
});

const buildSquadMoveRecommendations = (
  players,
  squads,
  counts,
  teamRatings,
  sourceTeam,
  targetTeam,
  preferred
) => {
  if (!sourceTeam || !targetTeam) return [];
  const beforeCountDifference = Math.abs(counts.allies - counts.axis);
  const ratingGapBefore = Math.abs(teamRatings.allies - teamRatings.axis);

  const recommendations = squads
    .filter((squad) => squad.team === sourceTeam)
    .map((squad) => {
      const projectedCounts = { ...counts };
      projectedCounts[sourceTeam] -= squad.members.length;
      projectedCounts[targetTeam] += squad.members.length;
      const projectedCountDifference = Math.abs(
        projectedCounts.allies - projectedCounts.axis
      );
      if (projectedCountDifference >= beforeCountDifference) return null;
      const projectedRatings = projectedGroupRatings(players, [
        { squad, target_team: targetTeam },
      ]);
      const projectedRatingGap = ratingGap(projectedRatings);
      return {
        kind: "squad_move",
        advisory_only: true,
        source: "current_server_snapshot",
        source_team: sourceTeam,
        target_team: targetTeam,
        squads: [publicSquad(squad)],
        moves: [squadMovePayload(squad, targetTeam)],
        member_count: squad.members.length,
        count_difference_before: beforeCountDifference,
        projected_count_difference: projectedCountDifference,
        rating_gap_before: Number(ratingGapBefore.toFixed(2)),
        projected_rating_gap: Number(projectedRatingGap.toFixed(2)),
        projected_team_ratings: projectedRatings,
        rating_improvement: Number(
          (ratingGapBefore - projectedRatingGap).toFixed(2)
        ),
        rating_confidence: Number(
          average(
            squad.members.map((player) => player.live_confidence)
          ).toFixed(3)
        ),
      };
    })
    .filter(Boolean)
    .sort(
      (left, right) =>
        left.projected_count_difference - right.projected_count_difference ||
        left.projected_rating_gap - right.projected_rating_gap ||
        left.member_count - right.member_count
    );
  return preferRecommendation(recommendations, preferred).slice(0, 3);
};

const buildSquadSwapRecommendations = (
  players,
  squads,
  teamRatings,
  options
) => {
  const ratingGapBefore = Math.abs(teamRatings.allies - teamRatings.axis);
  if (ratingGapBefore <= options.skillGapSoftLimit) return [];
  const strongerTeam =
    teamRatings.allies >= teamRatings.axis ? "allies" : "axis";
  const weakerTeam = strongerTeam === "allies" ? "axis" : "allies";
  const strongerSquads = squads.filter((squad) => squad.team === strongerTeam);
  const weakerSquads = squads.filter((squad) => squad.team === weakerTeam);
  const recommendations = [];

  strongerSquads.forEach((strongerSquad) => {
    weakerSquads.forEach((weakerSquad) => {
      if (strongerSquad.members.length !== weakerSquad.members.length) return;
      const projectedRatings = projectedGroupRatings(players, [
        { squad: strongerSquad, target_team: weakerTeam },
        { squad: weakerSquad, target_team: strongerTeam },
      ]);
      const projectedRatingGap = ratingGap(projectedRatings);
      const improvement = ratingGapBefore - projectedRatingGap;
      if (improvement < options.minimumImprovement) return;
      recommendations.push({
        kind: "squad_swap",
        advisory_only: true,
        source: "current_server_snapshot",
        stronger_team: strongerTeam,
        weaker_team: weakerTeam,
        squads: [publicSquad(strongerSquad), publicSquad(weakerSquad)],
        moves: [
          squadMovePayload(strongerSquad, weakerTeam),
          squadMovePayload(weakerSquad, strongerTeam),
        ],
        member_count: strongerSquad.members.length + weakerSquad.members.length,
        count_difference_before: 0,
        projected_count_difference: 0,
        rating_gap_before: Number(ratingGapBefore.toFixed(2)),
        projected_rating_gap: Number(projectedRatingGap.toFixed(2)),
        projected_team_ratings: projectedRatings,
        rating_improvement: Number(improvement.toFixed(2)),
        rating_confidence: Number(
          Math.min(
            average(
              strongerSquad.members.map((player) => player.live_confidence)
            ),
            average(weakerSquad.members.map((player) => player.live_confidence))
          ).toFixed(3)
        ),
      });
    });
  });

  recommendations.sort(
    (left, right) =>
      left.projected_rating_gap - right.projected_rating_gap ||
      right.rating_confidence - left.rating_confidence ||
      left.member_count - right.member_count
  );
  return preferRecommendation(recommendations, options.preferred).slice(0, 3);
};

const projectedSwapRatings = (players, first, second) => {
  const projected = players.map((player) => {
    if (player.player_id === first.player_id)
      return { ...player, team: second.team };
    if (player.player_id === second.player_id)
      return { ...player, team: first.team };
    return player;
  });
  return Object.fromEntries(
    TEAM_NAMES.map((team) => [
      team,
      Number(teamRating(projected, team).toFixed(2)),
    ])
  );
};

const buildStrengthSwaps = (players, teamRatings, options) => {
  const ratingGapBefore = Math.abs(teamRatings.allies - teamRatings.axis);
  if (ratingGapBefore <= options.skillGapSoftLimit) return [];
  const strongerTeam =
    teamRatings.allies >= teamRatings.axis ? "allies" : "axis";
  const weakerTeam = strongerTeam === "allies" ? "axis" : "allies";
  const strongerPlayers = players.filter(
    (player) =>
      player.team === strongerTeam &&
      eligiblePlayer(player, options.allowIndividualSquadFallback)
  );
  const weakerPlayers = players.filter(
    (player) =>
      player.team === weakerTeam &&
      eligiblePlayer(player, options.allowIndividualSquadFallback)
  );
  const recommendations = [];

  strongerPlayers.forEach((strongerPlayer) => {
    weakerPlayers.forEach((weakerPlayer) => {
      const projectedRatings = projectedSwapRatings(
        players,
        strongerPlayer,
        weakerPlayer
      );
      const projectedRatingGap = ratingGap(projectedRatings);
      const improvement = ratingGapBefore - projectedRatingGap;
      if (improvement < options.minimumImprovement) return;
      recommendations.push({
        kind: "strength_swap",
        advisory_only: true,
        source: "current_server_snapshot",
        stronger_team: strongerTeam,
        weaker_team: weakerTeam,
        stronger_player: publicPlayer(strongerPlayer),
        weaker_player: publicPlayer(weakerPlayer),
        rating_gap_before: Number(ratingGapBefore.toFixed(2)),
        projected_rating_gap: Number(projectedRatingGap.toFixed(2)),
        projected_team_ratings: projectedRatings,
        rating_improvement: Number(improvement.toFixed(2)),
        rating_confidence: Number(
          Math.min(
            strongerPlayer.live_confidence,
            weakerPlayer.live_confidence
          ).toFixed(3)
        ),
      });
    });
  });

  recommendations.sort(
    (left, right) =>
      left.projected_rating_gap - right.projected_rating_gap ||
      right.rating_confidence - left.rating_confidence
  );
  return preferRecommendation(recommendations, options.preferred).slice(0, 3);
};

const projectedMoveRatings = (players, player, targetTeam) => {
  const projected = players.map((item) =>
    item.player_id === player.player_id ? { ...item, team: targetTeam } : item
  );
  return Object.fromEntries(
    TEAM_NAMES.map((team) => [
      team,
      Number(teamRating(projected, team).toFixed(2)),
    ])
  );
};

const buildMoveProposal = (
  players,
  sourceTeam,
  targetTeam,
  allowIndividualSquadFallback,
  preferred
) => {
  if (!sourceTeam || !targetTeam) return null;
  const candidates = players
    .filter(
      (player) =>
        player.team === sourceTeam &&
        eligiblePlayer(player, allowIndividualSquadFallback)
    )
    .map((player) => ({
      player,
      projectedRatings: projectedMoveRatings(players, player, targetTeam),
    }))
    .sort(
      (left, right) =>
        ratingGap(left.projectedRatings) - ratingGap(right.projectedRatings) ||
        right.player.live_confidence - left.player.live_confidence
    );
  if (!candidates.length) return null;
  const candidate =
    candidates.find(
      ({ player }) =>
        preferred?.kind === "move" &&
        preferred.source_team === sourceTeam &&
        preferred.target_team === targetTeam &&
        preferred.player.player_id === player.player_id
    ) ?? candidates[0];
  return {
    ...publicPlayer(candidate.player),
    projected_rating_gap: Number(
      ratingGap(candidate.projectedRatings).toFixed(2)
    ),
    projected_team_ratings: candidate.projectedRatings,
    reason: "Live-Vorschlag aus dem aktuell größeren Team",
  };
};

export const buildLiveBalanceStatus = (
  teams,
  settings = {},
  preferred = null
) => {
  const players = addLiveRatings(flattenLivePlayers(teams));
  if (!players.length) return null;
  const counts = Object.fromEntries(
    TEAM_NAMES.map((team) => [
      team,
      players.filter((player) => player.team === team).length,
    ])
  );
  const expectedCounts = settings.authoritativeTeamCounts;
  const reportedAllies = finiteNumber(expectedCounts?.allies);
  const reportedAxis = finiteNumber(expectedCounts?.axis);
  const countsUnverified = settings.requireCountVerification === true && (
    reportedAllies === null || reportedAxis === null ||
    reportedAllies !== counts.allies || reportedAxis !== counts.axis
  );
  const incomplete = Boolean(teams?.fail_count) || countsUnverified;
  const difference = counts.allies - counts.axis;
  const targetDifference = Number.isFinite(Number(settings.targetDifference))
    ? Math.max(0, Number(settings.targetDifference))
    : 2;
  const skillGapSoftLimit = Number.isFinite(Number(settings.skillGapSoftLimit))
    ? Math.max(0, Number(settings.skillGapSoftLimit))
    : 5;
  const minimumImprovement = Number.isFinite(
    Number(settings.minimumImprovement)
  )
    ? Math.max(0, Number(settings.minimumImprovement))
    : 1.5;
  const allowIndividualSquadFallback =
    settings.allowIndividualSquadFallback !== false;
  const coordinatedSquadSwitchesEnabled =
    settings.coordinatedSquadSwitchesEnabled === true;
  const requiredSwitches = Math.max(
    0,
    Math.floor((Math.abs(difference) - targetDifference + 1) / 2)
  );
  const teamRatings = {
    allies: Number(teamRating(players, "allies").toFixed(2)),
    axis: Number(teamRating(players, "axis").toFixed(2)),
  };
  const squads = regularSquads(players);
  const sourceTeam = requiredSwitches
    ? difference > 0
      ? "allies"
      : "axis"
    : null;
  const targetTeam = sourceTeam
    ? sourceTeam === "allies"
      ? "axis"
      : "allies"
    : null;
  const squadRecommendations = requiredSwitches
    ? buildSquadMoveRecommendations(
        players,
        squads,
        counts,
        teamRatings,
        sourceTeam,
        targetTeam,
        preferred
      )
    : difference === 0
    ? buildSquadSwapRecommendations(players, squads, teamRatings, {
        skillGapSoftLimit,
        minimumImprovement,
        preferred,
      })
    : [];
  const strengthSwaps =
    allowIndividualSquadFallback && requiredSwitches === 0 && difference === 0
      ? buildStrengthSwaps(players, teamRatings, {
          skillGapSoftLimit,
          minimumImprovement,
          allowIndividualSquadFallback,
          preferred,
        })
      : [];
  const proposal = allowIndividualSquadFallback
    ? buildMoveProposal(
        players,
        sourceTeam,
        targetTeam,
        allowIndividualSquadFallback,
        preferred
      )
    : null;
  const confidences = players
    .filter((player) => !player.is_leader)
    .map((player) => player.live_confidence);

  return {
    source: "current_server_snapshot",
    updated_at: new Date().toISOString(),
    team_counts: counts,
    team_ratings: teamRatings,
    target_difference: targetDifference,
    required_switches: requiredSwitches,
    data_confidence: Number(average(confidences).toFixed(3)),
    strength_thresholds: {
      soft_limit: skillGapSoftLimit,
      minimum_improvement: minimumImprovement,
    },
    coordinated_squad_switches_enabled: coordinatedSquadSwitchesEnabled,
    allow_individual_squad_fallback: allowIndividualSquadFallback,
    squad_recommendation: squadRecommendations[0] ?? null,
    squad_recommendation_alternatives: squadRecommendations.slice(1),
    strength_swap: strengthSwaps[0] ?? null,
    strength_swap_alternatives: strengthSwaps.slice(1),
    proposal,
    plan: proposal
      ? {
          source_team: sourceTeam,
          target_team: targetTeam,
          projected_rating_gap: proposal.projected_rating_gap,
          projected_team_ratings: proposal.projected_team_ratings,
          rating_gap_before: Number(
            Math.abs(teamRatings.allies - teamRatings.axis).toFixed(2)
          ),
        }
      : null,
    warnings: incomplete
      ? ["Der aktuelle Spielersnapshot ist unvollständig"]
      : [],
    block_reasons: incomplete
      ? ["Live-Daten sind derzeit unvollständig"]
      : [],
  };
};

// Re-evaluate the exact held choice even when it has dropped out of the top 3.
// Never silently substitute another player, squad, or direction.
export function validateLiveRecommendation(teams, settings, recommendation) {
  const status = buildLiveBalanceStatus(teams, settings, recommendation);
  if (!status || status.block_reasons.length) return null;
  const groups = [
    ...balanceRecommendations(status),
    ...balanceRecommendations({ ...status, squad_recommendation: null }),
    ...balanceRecommendations({
      ...status,
      squad_recommendation: null,
      strength_swap: null,
    }),
  ];
  return (
    groups.find(
      (value) => recommendationKey(value) === recommendationKey(recommendation)
    ) ?? null
  );
}
