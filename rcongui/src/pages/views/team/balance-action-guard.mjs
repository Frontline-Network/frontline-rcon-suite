import { validateLiveRecommendation } from "./live-balance.mjs";
import { liveViewsDe } from "../../../i18n/locales/live-views.js";

export function balanceActionPreflight({
  recommendation,
  recipientIds,
  readTeams,
  readSettings,
  t,
}) {
  const text = (key) =>
    t ? t(`liveViews.balance.${key}`) : liveViewsDe.balance[key];
  return async (payloads) => {
    const actual = payloads.map((payload) => payload.player_id).sort();
    if (JSON.stringify(actual) !== JSON.stringify([...recipientIds].sort())) {
      throw new Error(text("selectionChanged"));
    }
    const [teams, settings] = await Promise.all([readTeams(), readSettings()]);
    const valid = validateLiveRecommendation(teams, settings, recommendation);
    const disabledSquad =
      recommendation.kind.startsWith("squad_") &&
      !settings.coordinatedSquadSwitchesEnabled;
    if (!valid || disabledSquad) {
      throw new Error(text("suggestionInvalid"));
    }
  };
}
