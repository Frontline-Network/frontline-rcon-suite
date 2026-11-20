import i18n from "@/i18n";
import french from "./copy-fr.json";

// Keep the form's catalog in its lazy chunk. User names and configured text are
// never passed through this dictionary.
export const vipCopy = {
  "Nachricht vorgemerkt": "Message queued",
  "Nachricht wird gesendet": "Sending message",
  "Nachricht vom Server angenommen": "Message accepted by server",
  "Nachrichtenergebnis unklar": "Message outcome uncertain",
  "Nachricht wiederholt abgelehnt": "Message repeatedly rejected",
  "Nachricht abgelaufen": "Message expired",
  "Sprache der Spielernachrichten": "Player message language",
  "Gilt für automatische VIP-Benachrichtigungen und die private Statusantwort.": "Applies to automatic VIP notifications and private status replies.",
  Deutsch: "German",
  Englisch: "English",
  Französisch: "French",
  Nahkampf: "Melee",
  Rundentreue: "Round loyalty",
  Wochenaktivität: "Weekly activity",
  "Wöchentliche Team-Unterstützung": "Weekly team support",
  "Spielzeit-Meilensteine": "Playtime milestones",
  "Freiwilliger Teamausgleich": "Voluntary team balancing",
  "Sammle Unterstützungspunkte über mehrere Runden: Montag bis Sonntag in der eingestellten Server-Zeitzone. Einmal pro Woche gibt es VIP beim Erreichen des Ziels. Nur neu erspielte Punkte zählen; die Seeding-Pause und das gemeinsame VIP-Limit gelten auch hier. Zielwerte gelten nur für diesen Server und können für HLL und HLLV unterschiedlich eingestellt werden.":
    "Collect support points across rounds, Monday to Sunday in the configured server time zone. Reaching the goal earns VIP once per week. Only newly earned points count; the seeding pause and shared VIP limit also apply. Goals apply only to this server and can differ between HLL and HLLV.",
  "Nur Gegnerkills mit Messer oder Spaten. Wiederholte Gegner werden gemeinsam mit Challenges begrenzt.":
    "Only enemy kills with a knife or shovel count. Repeat kills of the same opponent share a cooldown with challenges.",
  "Belohne Spieler, die bis zum Rundenende bleiben. Sowohl die Mindestspielzeit als auch der Mindestanteil an der Runde müssen erreicht sein.":
    "Reward players who stay until the round ends. Both the minimum playtime and minimum share of the round must be reached.",
  "Belohne regelmäßiges Spielen: An der gewählten Anzahl von Tagen muss jeweils die Mindestspielzeit erreicht werden. Die Woche läuft von Montag bis Sonntag.":
    "Reward regular play: reach the minimum playtime on each of the required days. The week runs from Monday to Sunday.",
  "Belohne insgesamt gesammelte Spielzeit ab Aktivierung. Jede Stufe kann ein Spieler einmal erreichen; frühere Spielzeit wird nicht nachgetragen.":
    "Reward total playtime recorded after activation. Each milestone can be earned once per player; earlier playtime is not imported.",
  "Der bestehende Autobalancer-Befehl !balance meldet Spieler auch für diese Belohnung an. VIP gibt es erst nach dem freiwilligen Wechsel und der Mindestspielzeit im kleineren Team. Erzwungene Wechsel zählen nicht.":
    "The existing autobalancer command !balance also registers players for this reward. VIP requires a voluntary switch and the minimum playtime on the smaller team. Forced switches do not count.",
  Vorgemerkt: "Queued",
  "Abgleich ausstehend": "Reconciliation pending",
  Gutgeschrieben: "Awarded",
  Vorschau: "Preview",
  "Nicht vergeben": "Not awarded",
  "Prüfung erforderlich": "Review required",
  "Manuell geprüft": "Manually reviewed",
  "24-Stunden-Budget erreicht": "24-hour budget reached",
  "Regellimit erreicht": "Rule limit reached",
  "Dauerhaftes VIP": "Permanent VIP",
  "Deaktiviert oder pausiert": "Disabled or paused",
  "Frühere Vergabe prüfen": "Review earlier award",
  "Teilbetrag: Restbudget": "Partial award: remaining budget",
  "Nach Neustart bestätigt": "Confirmed after restart",
  "Schreibergebnis unklar": "Write outcome uncertain",
  "VIP-Ablauf nicht bestätigt": "VIP expiry not confirmed",
  "Letzte 24 Stunden": "Last 24 hours",
  Täglich: "Daily",
  Wöchentlich: "Weekly",
  Monatlich: "Monthly",
  Events: "Events",
  "Waffen-Challenges": "Weapon challenges",
  Stunde: "hour",
  Stunden: "hours",
  Tag: "day",
  Tage: "days",
  Minuten: "minutes",
  Vergabe: "award",
  Vergaben: "awards",
  "Maximale Vergaben": "Maximum awards",
  "Pro Spieler. Das gemeinsame VIP-Zeitbudget gilt zusätzlich.":
    "Per player. The shared VIP time budget also applies.",
  "Zeitraum für maximale Vergaben": "Award limit period",
  "Rollend: die jeweils letzten 24 Stunden.":
    "Rolling window: the preceding 24 hours.",
  "Kalenderzeitraum in der gewählten Zeitzone. Wochen beginnen montags, Monate am 1.":
    "Calendar period in the selected time zone. Weeks start on Monday, months on the 1st.",
  "VIP-Dauer (Tage)": "VIP duration (days)",
  "Wähle die VIP-Dauer. Ein Tag entspricht 24 Stunden; kürzere Belohnungen sind ebenfalls möglich.":
    "Choose the VIP duration. One day is 24 hours; shorter rewards are also available.",
  "Die Waffenliste konnte nicht geladen werden. Vorhandene Auswahlen bleiben erhalten. Bitte lade die Seite erneut.":
    "Could not load weapons. Existing selections are preserved. Please reload the page.",
  "Bitte wähle für jede aktive Waffen-Challenge mindestens eine Waffe aus.":
    "Select at least one weapon for every enabled weapon challenge.",
  "Speichern fehlgeschlagen": "Could not save",
  "Einstellungen gespeichert. Der Dienst übernimmt sie bei der nächsten Prüfung.":
    "Settings saved. The service will apply them on its next check.",
  "VIP-Ablauf und zwischenzeitliche Änderungen geprüft? Die Bestätigung erlaubt zukünftige Belohnungen, zahlt diesen Eintrag aber nicht erneut aus.":
    "Have you checked the VIP expiry and any intervening changes? Confirming allows future rewards but does not pay this entry again.",
  "Eintrag konnte nicht bestätigt werden": "Could not acknowledge this entry",
  "Manuell geprüft; keine erneute Auszahlung":
    "Manually reviewed; no repeat payment",
  "VIP-Belohnungen werden geladen …": "Loading VIP rewards …",
  "Status wird geladen": "Loading status",
  Aktiv: "Active",
  Deaktiviert: "Disabled",
  "Pausiert: kein bestätigter Serverstatus":
    "Paused: server status not confirmed",
  "Pausiert: Seeding / Freigabeprüfung": "Paused: seeding / population check",
  "Wartet auf Mindestbesetzung": "Waiting for minimum team sizes",
  "Freigabe in {{time}}": "Rewards unlock in {{time}}",
  "Freigabe wird bestätigt": "Confirming eligibility",
  "Lokaler Formulartest · Nur simulierte Daten. Keine VIP-Vergaben oder Spielernachrichten.":
    "Local form preview · Simulated data only. No VIP awards or player messages.",
  "VIP-Belohnungen": "VIP rewards",
  Livebetrieb: "Live operation",
  "Zusätzliche Belohnungen für Spielzeit, Teamhilfe und Herausforderungen.":
    "Additional rewards for playtime, teamwork and challenges.",
  "VIP-Bereiche": "VIP sections",
  Belohnungen: "Rewards",
  Grundeinstellungen: "General settings",
  Vergabejournal: "Award journal",
  "Nur Lesezugriff. Änderungen erfordern die Berechtigung für Seed-VIP-Einstellungen.":
    "Read-only access. Changes require permission to edit Seed-VIP settings.",
  "Betrieb und Grenzen": "Operation and limits",
  "Diese Einstellungen gelten für alle zusätzlichen VIP-Belohnungen.":
    "These settings apply to all additional VIP rewards.",
  "Seed-VIP separat einstellen": "Configure Seed-VIP separately",
  "Neue VIP-Belohnungen aktivieren": "Enable new VIP rewards",
  "Vorschau: keine VIP-Vergabe und keine Spielernachrichten":
    "Preview: no VIP awards or player messages",
  "Während des Seedens pausieren": "Pause during seeding",
  "Spieler nach erfolgreicher Vergabe benachrichtigen":
    "Notify players after a successful award",
  "Seed-VIP-Zielzahlen müssen fünf Minuten gehalten werden. Prüfung alle 30 Sekunden. Vorschau und Livebetrieb haben getrennte Fortschritte und Budgets.":
    "Seed-VIP population targets must hold for five minutes. Checked every 30 seconds. Preview and live operation have separate progress and budgets.",
  "Maximale VIP-Tage pro Spieler je 24 Stunden":
    "Maximum VIP days per player in 24 hours",
  "Obergrenze für alle Regeln zusammen innerhalb der letzten 24 Stunden. Überschüsse werden nicht später nachgezahlt.":
    "Combined limit for all rules over the last 24 hours. Excess rewards are not paid later.",
  "Abstand beim selben Gegner (Minuten)": "Same opponent cooldown (minutes)",
  "Weitere Kills desselben Gegners zählen erst nach diesem Abstand erneut für Nahkampf und Challenges.":
    "Further kills of the same opponent count for melee and challenges only after this cooldown.",
  Zeitzone: "Time zone",
  "Bestimmt Tages-, Wochen- und Monatsgrenzen. Sommerzeit wird automatisch berücksichtigt.":
    "Sets daily, weekly and monthly boundaries. Daylight saving time is handled automatically.",
  "Chatbefehl für den Wochenfortschritt": "Weekly progress chat command",
  "Zum Beispiel !rewards oder !teamvip. Leer lassen zum Abschalten. Antwort nur privat, höchstens alle 30 Sekunden pro Spieler. Im Probelauf keine Nachrichten.":
    "For example !rewards or !teamvip. Leave empty to disable. Private reply, at most once every 30 seconds per player. No messages in preview mode.",
  Belohnungsregeln: "Reward rules",
  Belohnungsregel: "Reward rule",
  Aus: "Off",
  "Regel auswählen": "Select a rule",
  "Belohnungen gezielt konfigurieren.": "Configure individual rewards.",
  "Unterstützungspunkte über mehrere Runden sammeln. Ein Wochenziel für hilfreiches Teamplay.":
    "Collect support points across rounds. A weekly goal for helpful teamwork.",
  "Aktiviere diese Regel, um Voraussetzungen und Belohnung einzustellen. Gespeicherte Werte bleiben beim Ausschalten erhalten.":
    "Enable this rule to configure its requirements and reward. Disabling it preserves your settings.",
  Voraussetzungen: "Requirements",
  "Ein gültiger Nahkampfkill gegen einen Gegner. Der eingestellte Abstand beim selben Gegner gilt zusätzlich.":
    "A valid melee kill against an enemy. The configured same-opponent cooldown also applies.",
  "Erreichte Spielstunden und die zugehörige Belohnung legst du unten je Stufe fest.":
    "Set the playtime threshold and reward for each milestone below.",
  "Mindestspielzeit (Minuten)": "Minimum playtime (minutes)",
  "Mindestanteil der Runde (%)": "Minimum share of the round (%)",
  "Unterstützungspunkte pro Woche": "Support points per week",
  "Beispielwert: 5.000 Punkte. Passe das Ziel an die Spielweise auf deinem Server an.":
    "Example: 5,000 points. Adjust the goal to suit play on your server.",
  "Unterschiedliche Tage": "Distinct days",
  "Mindest-Teamdifferenz": "Minimum team size difference",
  "Anmeldung gültig (Minuten)": "Registration valid for (minutes)",
  Belohnung: "Reward",
  "Regel aktivieren": "Enable {{rule}}",
  "Wochenziel-Zusammenfassung":
    "Earn {{duration}} VIP by reaching {{points}} support points. Once per week, Monday to Sunday · {{zone}}.",
  Spielstunden: "Hours played",
  Entfernen: "Remove",
  "Meilenstein hinzufügen": "Add milestone",
  "Belohne die Teilnahme in einem festgelegten Zeitraum, zum Beispiel an einem Community-Abend.":
    "Reward participation during a set time window, such as a community evening.",
  "Wähle Waffen aus der Liste und lege fest, wie viele Gegnerkills damit nötig sind. Teamkills zählen nicht.":
    "Choose weapons and set the required number of enemy kills. Teamkills do not count.",
  Name: "Name",
  Aktiviert: "Enabled",
  "Keine passende Waffe gefunden": "No matching weapons found",
  "Waffen auswählen": "Select weapons",
  "Suchen und mehrere Waffen auswählen. Kills mit diesen Waffen werden gemeinsam gezählt.":
    "Search and select multiple weapons. Kills with these weapons count together.",
  Gegnerkills: "Enemy kills",
  Zeitraum: "Period",
  "Fester Zeitraum": "Fixed period",
  Beginn: "Start",
  Ende: "End",
  "Neues Event": "New event",
  "Neue Challenge": "New challenge",
  "Event hinzufügen": "Add event",
  "Challenge hinzufügen": "Add challenge",
  "Ungespeicherte Änderungen": "Unsaved changes",
  "Alle Änderungen gespeichert": "All changes saved",
  "Änderungen verwerfen": "Discard changes",
  Verwerfen: "Discard",
  "Einstellungen speichern": "Save settings",
  "Speichert …": "Saving …",
  Speichern: "Save",
  "Vergabejournal und Spielerfortschritt": "Award journal and player progress",
  "Spieler-ID filtern": "Filter player ID",
  Journal: "Journal",
  Live: "Live",
  "Aktuellen Fortschritt anzeigen": "Show current progress",
  "Aktueller Betriebsmodus:": "Current mode:",
  ". Spielzeit-Meilensteine:": ". Playtime milestones:",
  "h; Rundentreue:": "h; round loyalty:",
  "min; erfasste Spieltage:": "min; recorded play days:",
  "Wochenziel Unterstützung (Woche ab": "Weekly support goal (week starting",
  "Punkte.": "points.",
  "VIP-Vergabejournal": "VIP award journal",
  Zeit: "Time",
  Spieler: "Player",
  Regel: "Rule",
  "VIP-Gutschrift": "VIP credit",
  Ergebnis: "Result",
  von: "of",
  "h beantragt": "h requested",
  "Budget reserviert; Gutschrift unbestätigt":
    "Budget reserved; credit not confirmed",
  "Zielablauf:": "Target expiry:",
  unbekannt: "unknown",
  "Als geprüft markieren": "Mark as reviewed",
  "Noch keine Vergaben für diese Auswahl.": "No awards for this selection yet.",
  Zurück: "Previous",
  Einträge: "entries",
  Weiter: "Next",
  "Unbekannter Spieler": "Unknown player",
  "Spielersuche nicht verfügbar": "Player search unavailable",
  "Spielersuche fehlgeschlagen. Bitte erneut versuchen.":
    "Player search failed. Please try again.",
  "Spieler werden gesucht …": "Searching players …",
  "Mindestens zwei Zeichen eingeben": "Enter at least two characters",
  "Keine Spieler gefunden": "No players found",
  "Ausgeschlossene Spieler": "Excluded players",
  "Nach Spielernamen oder ID suchen und auswählen. Ausgewählte Spieler erhalten keine dieser VIP-Belohnungen. Die Spielerakte bleibt unverändert.":
    "Search by name or ID and select players. Selected players receive none of these VIP rewards. Their player record is unchanged.",
};

const german = Object.fromEntries(
  Object.keys(vipCopy).map((key) => [key, key])
);
german["Wochenziel-Zusammenfassung"] =
  "Wer {{points}} Unterstützungspunkte erreicht, erhält {{duration}} VIP. Einmal pro Woche, Montag bis Sonntag · {{zone}}.";
german["Regel aktivieren"] = "{{rule}} aktivieren";
for (const [language, entries] of Object.entries({ de: german, en: vipCopy, fr: french })) {
  i18n.addResourceBundle(language, "vipRewards", entries, true, true);
}
export const tr = (text, values = {}) =>
  i18n.t(text, { ns: "vipRewards", keySeparator: false, ...values });
export const vipLocale = () =>
  ({ en: "en-GB", fr: "fr-FR", de: "de-DE" })[(i18n.resolvedLanguage || "de").split("-")[0]] || "de-DE";
