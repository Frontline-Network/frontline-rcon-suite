export const copy = {
  de: {
    title: "Report-Admin – Kommunikation, Teamkills & Cheatprüfung",
    info: "Serverbezogene Report-Automatik mit wählbarer KI-Einordnung des vollständigen Meldegrunds. Hier separat speichern; die KI-Anbindung wird darunter eingerichtet. Andere Beschwerden bleiben manuell. Führungsabstimmungen wurden eingestellt.",
    reasonMode: "Einordnung des Meldegrunds",
    aiReason: "KI – vollständigen Inhalt einordnen",
    rulesReason: "Bisherige Suchregeln (ohne KI)",
    aiReasonHelp:
      "Nutzt den unten konfigurierten KI-Anbieter und das Report-Modell. Der vollständige Report und aktuelle Spielernamen/Rollen werden zur KI übertragen; API-Kosten bzw. Kontolimits können anfallen. Prüft Bedeutung, Verneinungen und Zusätze statt nur Suchwörter. Spielerzuordnung und Schutzregeln bleiben technisch geprüft. Unklare Antworten, fehlende Anbindung und Fehler bleiben manuell; kein Suchwort-Fallback. Der Report ist kein Beweis für tatsächliches Schweigen.",
    rulesReasonHelp:
      "Kompatibilitätsmodus: erkennt nur unterstützte Formulierungen. Kein allgemeines Sprachverständnis und keine KI-Abfrage.",
    warning:
      "Aktivmodus: Eine eindeutige Kommunikationsmeldung kann ohne Abstimmung oder Vorwarnung zum Kick führen. Ob jemand tatsächlich spricht, ist technisch nicht überprüfbar. Falschmeldungen können deshalb zum Missbrauch führen.",
    teamkills:
      "Teamkills: Einzelfallprüfung mit bis zu 15 Minuten Kontext und 60 Sekunden stiller Wartezeit ab dem Teamkill. Melder und Beschuldigter werden geprüft. Automatischer Kick nur bei protokolliertem Teamkill mit zeitnaher, ausdrücklicher eigener Absichtserklärung. Keine Entschuldigung, hohe Anzahl oder weitere Teamkills nach einer Entschuldigung beweisen allein keine Absicht. Entschuldigungen, gegenseitige Teamkills und unklare Fälle gehen an Admins. Keine Aufforderung an den Beschuldigten.",
    cheating:
      "Cheatprüfung: Waffenbezogene Killverläufe über 1, 5 und 15 Minuten; Rollenverlauf, sofern verfügbar. Killraten sind nur Hinweise für die Admin-Prüfung, kein Cheatnachweis. Keine automatischen Cheat-Kicks oder Banns. Ein 24-Stunden-Tempbann erfordert zusätzliche Belege und eine manuelle Admin-Entscheidung in Discord. Nur der Melder erhält eine Eingangsbestätigung.",
    cheatToggle:
      "Cheatmeldungen für Admins auswerten (keine automatische Sanktion)",
    names:
      "Namen: nur ein eindeutiger Online-Treffer. Bis zu drei Tippfehler bei längeren Namen; kurze oder ähnlich gute Treffer werden manuell geprüft.",
    enabled: "Report-Admin aktivieren",
    communication: "Kommunikationsmeldungen bearbeiten",
    members: "Kommunikationsmeldungen auch gegen namentlich gemeldete Squadmitglieder",
    memberHelp: "Standardmäßig gelten Kommunikationsmeldungen nur für Squadleader und Commander. Mit der Erweiterung kann auch ein eindeutig benanntes Squadmitglied im selben Team gekickt werden. Ein Squadname meldet weiterhin nur den Squadleader, niemals den ganzen Squad. Unklare Namen bleiben manuell. Gilt nur für diesen Server.",
    tk: "Teamkill-Meldungen bearbeiten",
    selfReports: "Selbstmeldungen für Tests zulassen",
    selfReportsWarning:
      "Testausnahme aktiv: Neue Selbstmeldungen werden ebenfalls geprüft. Im Aktivmodus kann dies dich tatsächlich vom Server kicken. Die übrigen Regeln gelten weiterhin. Nach dem Test wieder ausschalten und speichern.",
    mode: "Betriebsart",
    dry: "Probelauf – keine Kicks",
    active: "Aktiv – automatische Kicks",
    commTemplate: "Kick-Grund für Kommunikation",
    tkTemplate: "Kick-Grund für Teamkills",
    fallback: "Integrierter DE/EN-Standardtext",
    placeholders:
      "Vorlagen aus der Kategorie Gründe. Platzhalter: {player_name}, {teamkills}, {minutes} (tatsächlicher Kontextzeitraum). Bestehende Teamkill-Vorlagen mit festen 5-in-5-Aussagen bitte überarbeiten. Ohne passende Vorlage gilt der Standardtext.",
    save: "Report-Regeln speichern",
    saved: "Gespeichert",
    loading: "Laden …",
    permission: "Keine Berechtigung zur Konfiguration.",
  },
  en: {
    title: "Report admin – communication, teamkills & cheat review",
    info: "Server-specific report automation with optional AI interpretation of the entire complaint. Save separately here; configure the AI provider below. Other complaints remain manual. Leadership voting has been retired.",
    reasonMode: "Report reason interpretation",
    aiReason: "AI – interpret the entire report",
    rulesReason: "Existing keyword rules (no AI)",
    aiReasonHelp:
      "Uses the configured provider and report model below. The complete report and current player names/roles are sent to AI; API charges or account limits may apply. Evaluates meaning, negations and context rather than keywords alone. Player matching and safety checks remain independently enforced. Uncertain output, missing credentials and failures stay manual, with no keyword fallback. The report does not prove actual voice silence.",
    rulesReasonHelp:
      "Compatibility mode: recognizes supported wording only. No general language understanding or AI request.",
    warning:
      "Active mode: An unambiguous communication report can trigger a kick without a vote or warning. Voice activity cannot be verified. False reports can therefore be abused.",
    teamkills:
      "Teamkills: individual assessment with up to 15 minutes of context and a silent 60-second window starting at the teamkill. Both reporter and accused are reviewed. Automatic kick only for a recorded teamkill with a timely, explicit first-person admission of intent. No apology, high counts or further kills after an apology alone do not prove intent. Apologies, reciprocal teamkills and unclear cases go to admins. No prompt to the accused.",
    cheating:
      "Cheat review: weapon-based kill timelines over 1, 5 and 15 minutes, with role history where available. Kill rates are review hints, not cheating evidence. No automatic cheat kicks or bans. A 24-hour temporary ban requires additional evidence and a manual admin decision in Discord. Only the reporter receives an acknowledgement.",
    cheatToggle: "Assess cheat reports for admins (no automatic sanction)",
    names:
      "Names: one unambiguous online match only. Up to three typos in longer names; short or similarly plausible matches require manual review.",
    enabled: "Enable report admin",
    communication: "Process communication reports",
    members: "Include explicitly named squad members in communication reports",
    memberHelp: "By default, communication reports cover squadleaders and commanders only. With this extension, a uniquely named squad member on the same team can also be kicked. A squad name still reports only its leader, never the entire squad. Unclear names stay manual. Applies only to this server.",
    tk: "Process teamkill reports",
    selfReports: "Allow self-reports for testing",
    selfReportsWarning:
      "Test exception enabled: New self-reports are also checked. In active mode this can actually kick you from the server. All other rules still apply. Disable and save this option after testing.",
    mode: "Mode",
    dry: "Dry run – no kicks",
    active: "Active – automatic kicks",
    commTemplate: "Communication kick reason",
    tkTemplate: "Teamkill kick reason",
    fallback: "Built-in DE/EN default",
    placeholders:
      "Templates from the Reasons category. Placeholders: {player_name}, {teamkills}, {minutes} (actual context period). Review existing teamkill templates containing fixed 5-in-5 claims. Missing templates use the default text.",
    save: "Save report rules",
    saved: "Saved",
    loading: "Loading …",
    permission: "You cannot manage this configuration.",
  },
};
