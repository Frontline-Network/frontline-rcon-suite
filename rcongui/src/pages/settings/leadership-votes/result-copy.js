// Only known system outcomes are localized; unknown results and player reports
// remain verbatim. Never split arbitrary player/server content on a slash.
export const leadershipResults = {
  declined: ["Melder lehnt ab", "Reporter declined"],
  eligibility: ["Berechtigung geändert", "Eligibility changed"],
  withdrawn: ["Vom Melder zurückgezogen", "Withdrawn by reporter"],
  admin: ["Von Admin übernommen", "Taken over by admin"],
  manualAction: ["Manuelle Maßnahme", "Manual action"],
  configuration: ["Konfiguration geändert", "Configuration changed"],
  round: ["Runde/Verbindung geändert", "Round or connection changed"],
  auditConfirmed: ["Kick-Audit bestätigt", "Kick audit confirmed"],
  restart: [
    "Neustart: manuell prüfen, keine Wiederholung",
    "Restart: manual review, no retry",
  ],
  target: [
    "Ziel oder Live-Daten nicht mehr gültig",
    "Target or live data no longer valid",
  ],
  confirmation: ["Bestätigung abgelaufen", "Confirmation expired"],
  voters: ["Zu wenige Berechtigte", "Too few eligible leaders"],
  adminHandling: [
    "Admin-Bearbeitung oder Zieländerung",
    "Admin handling or target changed",
  ],
  warning: ["Warnung nicht zugestellt", "Warning not delivered"],
  invitations: [
    "Einladungen nicht ausreichend zugestellt",
    "Insufficient invitation delivery",
  ],
  delivery: ["Zustellung unvollständig", "Delivery incomplete"],
  majority: [
    "Mehrheit fehlt – Admins übernehmen",
    "No majority – admins take over",
  ],
  dryRun: [
    "Probelauf: Mehrheit erreicht, kein Kick",
    "Dry run: majority reached, no kick",
  ],
  finalCheck: [
    "Letzte Prüfung fehlgeschlagen – kein Kick",
    "Final check failed – no kick",
  ],
  kicked: ["Kick bestätigt", "Kick confirmed"],
  unknown: [
    "Kick unbestätigt – manuell prüfen, keine Wiederholung",
    "Kick unconfirmed – manual review, no retry",
  ],
  demoMajority: [
    "Demo: Zustimmung nicht erreicht – kein Kick",
    "Demo: no majority – no kick",
  ],
  demoDisabled: ["Demo: Funktion ausgeschaltet", "Demo: feature disabled"],
  demoAdmin: ["Demo: Von Moderator beendet", "Demo: ended by a moderator"],
};

const knownResults = new Map(
  Object.entries(leadershipResults).flatMap(([key, [de, en]]) => [
    [`${de} / ${en}`, key],
    ...(key.startsWith("demo") ? [[de, key]] : []),
  ])
);

export function translateLeadershipResult(result, language) {
  const key = knownResults.get(result);
  if (!key) return result;
  return leadershipResults[key][language?.startsWith("de") ? 0 : 1];
}
