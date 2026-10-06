export const copy = {
  de: {
    title: "Report-Admin – Kommunikation & Teamkills",
    info: "Serverbezogen. Verarbeitet neue !admin-Reports nach festen Regeln, ohne KI-Zugang. Andere Beschwerden bleiben manuell. Bei Aktivierung ersetzt dies die automatische Führungsvote-Zuordnung auf diesem Server.",
    warning:
      "Aktivmodus: Eine eindeutige Kommunikationsmeldung kann ohne Abstimmung oder Vorwarnung zum Kick führen. Ob jemand tatsächlich spricht, ist technisch nicht überprüfbar. Falschmeldungen können deshalb zum Missbrauch führen.",
    teamkills:
      "Teamkills: Kick ab 5 protokollierten Teamkills in den 5 Minuten vor dem Report, nur im laufenden Match. Die Anzahl beweist keine Absicht.",
    names:
      "Namen: nur ein eindeutiger Online-Treffer. Bis zu drei Tippfehler bei längeren Namen; kurze oder ähnlich gute Treffer werden manuell geprüft.",
    enabled: "Report-Admin aktivieren",
    communication: "Kommunikationsmeldungen bearbeiten",
    tk: "Teamkill-Meldungen bearbeiten",
    selfReports: "Selbstmeldungen für Tests zulassen",
    selfReportsWarning:
      "Testausnahme aktiv: Neue Selbstmeldungen werden ebenfalls geprüft. Im Aktivmodus kann dies dich tatsächlich vom Server kicken. Die übrigen Regeln gelten weiterhin; beim Führungsvote bleiben Selbstmeldungen gesperrt. Nach dem Test wieder ausschalten und speichern.",
    mode: "Betriebsart",
    dry: "Probelauf – keine Kicks",
    active: "Aktiv – automatische Kicks",
    commTemplate: "Kick-Grund für Kommunikation",
    tkTemplate: "Kick-Grund für Teamkills",
    fallback: "Integrierter DE/EN-Standardtext",
    placeholders:
      "Vorlagen aus der Kategorie Gründe. Platzhalter: {player_name}, {teamkills}, {minutes}. Ohne passende Vorlage gilt der Standardtext.",
    save: "Speichern",
    saved: "Gespeichert",
    loading: "Laden …",
    permission: "Keine Berechtigung zur Konfiguration.",
  },
  en: {
    title: "Report admin – communication & teamkills",
    info: "Server-specific. Processes new !admin reports using fixed rules, without an AI account. Other complaints remain manual. Enabling this replaces automatic leadership-vote routing on this server.",
    warning:
      "Active mode: An unambiguous communication report can trigger a kick without a vote or warning. Voice activity cannot be verified. False reports can therefore be abused.",
    teamkills:
      "Teamkills: kick at 5 recorded teamkills in the 5 minutes before the report, in the current match only. The count does not prove intent.",
    names:
      "Names: one unambiguous online match only. Up to three typos in longer names; short or similarly plausible matches require manual review.",
    enabled: "Enable report admin",
    communication: "Process communication reports",
    tk: "Process teamkill reports",
    selfReports: "Allow self-reports for testing",
    selfReportsWarning:
      "Test exception enabled: New self-reports are also checked. In active mode this can actually kick you from the server. All other rules still apply; leadership votes still reject self-reports. Disable and save this option after testing.",
    mode: "Mode",
    dry: "Dry run – no kicks",
    active: "Active – automatic kicks",
    commTemplate: "Communication kick reason",
    tkTemplate: "Teamkill kick reason",
    fallback: "Built-in DE/EN default",
    placeholders:
      "Templates from the Reasons category. Placeholders: {player_name}, {teamkills}, {minutes}. Missing templates use the default text.",
    save: "Save",
    saved: "Saved",
    loading: "Loading …",
    permission: "You cannot manage this configuration.",
  },
};
