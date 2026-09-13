import { validateLiveRecommendation } from "./live-balance.mjs";

export function balanceActionPreflight({
  recommendation,
  recipientIds,
  readTeams,
  readSettings,
}) {
  return async (payloads) => {
    const actual = payloads.map((payload) => payload.player_id).sort();
    if (JSON.stringify(actual) !== JSON.stringify([...recipientIds].sort())) {
      throw new Error(
        "Die Spielerauswahl wurde geändert. Bitte den Balance-Vorschlag erneut prüfen."
      );
    }
    const [teams, settings] = await Promise.all([readTeams(), readSettings()]);
    const valid = validateLiveRecommendation(teams, settings, recommendation);
    const disabledSquad =
      recommendation.kind.startsWith("squad_") &&
      !settings.coordinatedSquadSwitchesEnabled;
    if (!valid || disabledSquad) {
      throw new Error(
        "Der Balance-Vorschlag ist nicht mehr gültig. Es wurde kein Wechsel ausgeführt. Bitte einen neuen Vorschlag prüfen."
      );
    }
  };
}
