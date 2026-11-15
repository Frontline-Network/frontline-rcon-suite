import { validateLiveRecommendation } from "./live-balance.mjs";
import { liveViewsDe } from "../../../i18n/locales/live-views.js";

export function balanceActionPreflight({
  recommendation,
  recipientIds,
  readTeams,
  readSettings,
  readGameState,
  t,
}) {
  const text = (key) =>
    t ? t(`liveViews.balance.${key}`) : liveViewsDe.balance[key];
  return async (payloads) => {
    const actual = payloads.map((payload) => payload.player_id).sort();
    if (JSON.stringify(actual) !== JSON.stringify([...recipientIds].sort())) {
      throw new Error(text("selectionChanged"));
    }
    const [teams, settings, gameState] = await Promise.all([
      readTeams(), readSettings(), readGameState?.(),
    ]);
    const verifiedSettings = {
      ...settings,
      requireCountVerification: true,
      authoritativeTeamCounts: {
        allies: gameState?.num_allied_players,
        axis: gameState?.num_axis_players,
      },
    };
    const valid = validateLiveRecommendation(teams, verifiedSettings, recommendation);
    const disabledSquad =
      recommendation.kind.startsWith("squad_") &&
      !settings.coordinatedSquadSwitchesEnabled;
    if (!valid || disabledSquad) {
      throw new Error(text("suggestionInvalid"));
    }
  };
}
