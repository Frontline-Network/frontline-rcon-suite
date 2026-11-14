export const copy = {
  fr: {
    receiptLanguage: "Langue de l’accusé de réception", receiptLanguageHelp: "Concerne les confirmations envoyées au joueur ayant effectué le signalement. Les motifs d’expulsion personnalisés ne sont pas modifiés.",
    title: "Administration des signalements – communication, teamkills et triche",
    info: "Automatisation des signalements propre au serveur, avec interprétation facultative du motif complet par IA. Enregistrez ici séparément ; configurez le fournisseur d’IA ci-dessous. Les autres plaintes restent manuelles. Les votes de commandement ont été supprimés.",
    reasonMode: "Interprétation du motif du signalement", aiReason: "IA – interpréter le signalement complet", rulesReason: "Règles de mots-clés existantes (sans IA)",
    aiReasonHelp: "Utilise le fournisseur d’IA et le modèle de signalement configurés ci-dessous. Le signalement complet et les noms et rôles actuels des joueurs sont transmis à l’IA ; des frais API ou limites de compte peuvent s’appliquer. Le sens, les négations et le contexte sont analysés, pas seulement les mots-clés. L’identification des joueurs et les protections restent vérifiées séparément. Les réponses incertaines, l’absence de connexion et les erreurs restent traitées manuellement, sans recours aux mots-clés. Le signalement ne prouve pas qu’une personne ne parle pas.",
    rulesReasonHelp: "Mode de compatibilité : reconnaît uniquement les formulations prises en charge. Pas de compréhension générale du langage ni d’appel à l’IA.",
    warning: "Mode actif : un signalement de communication sans ambiguïté peut déclencher une expulsion sans vote ni avertissement. L’activité vocale ne peut pas être vérifiée. De faux signalements peuvent donc être utilisés abusivement.",
    teamkills: "Teamkills : examen individuel avec jusqu’à 15 minutes de contexte et une attente silencieuse de 60 secondes à partir du teamkill. Le signaleur et l’accusé sont examinés. Une expulsion automatique exige un teamkill enregistré et un aveu explicite et rapide de l’intention à la première personne. L’absence d’excuses, un nombre élevé ou de nouveaux teamkills après des excuses ne prouvent pas à eux seuls l’intention. Les excuses, teamkills réciproques et cas incertains sont transmis aux administrateurs. Aucune sollicitation n’est envoyée à l’accusé.",
    cheating: "Examen de la triche : chronologie des éliminations par arme sur 1, 5 et 15 minutes et historique des rôles si disponible. Les taux d’élimination sont des indices à examiner, pas une preuve de triche. Aucune expulsion ou aucun bannissement automatique pour triche. Un bannissement temporaire de 24 heures exige des preuves supplémentaires et une décision manuelle d’un administrateur dans Discord. Seul le signaleur reçoit un accusé de réception.",
    cheatToggle: "Analyser les signalements de triche pour les administrateurs (sans sanction automatique)",
    names: "Noms : une seule correspondance en ligne sans ambiguïté. Jusqu’à trois fautes pour les noms longs ; les noms courts ou correspondances aussi plausibles nécessitent un examen manuel.",
    enabled: "Activer l’administration des signalements", communication: "Traiter les signalements de communication", members: "Inclure les membres d’escouade explicitement nommés dans les signalements de communication",
    memberHelp: "Par défaut, les signalements de communication concernent uniquement les chefs d’escouade et les commandants. Avec cette extension, un membre de la même équipe nommé sans ambiguïté peut aussi être expulsé. Le nom d’une escouade signale toujours uniquement son chef, jamais toute l’escouade. Les noms incertains restent traités manuellement. S’applique à ce serveur uniquement.",
    tk: "Traiter les signalements de teamkill", selfReports: "Autoriser les autosignalements pour les tests", selfReportsWarning: "Exception de test activée : les nouveaux autosignalements sont également vérifiés. En mode actif, vous pouvez réellement être expulsé du serveur. Les autres règles restent applicables. Désactivez cette option et enregistrez après le test.",
    mode: "Mode", dry: "Simulation – aucune expulsion", active: "Actif – expulsions automatiques", commTemplate: "Motif d’expulsion pour communication", tkTemplate: "Motif d’expulsion pour teamkill", fallback: "Texte par défaut intégré DE/EN",
    placeholders: "Modèles de la catégorie Motifs. Variables : {player_name}, {teamkills}, {minutes} (période réelle de contexte). Vérifiez les modèles de teamkill existants qui indiquent systématiquement 5 en 5 minutes. Sans modèle adapté, le texte par défaut est utilisé.",
    save: "Enregistrer les règles de signalement", saved: "Enregistré", loading: "Chargement…", permission: "Vous n’avez pas l’autorisation de modifier cette configuration."
  },
  de: {
    receiptLanguage: "Sprache der Eingangsbestätigung", receiptLanguageHelp: "Gilt für Bestätigungen an den meldenden Spieler. Individuelle Kick-Gründe bleiben unverändert.",
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
    receiptLanguage: "Acknowledgement language", receiptLanguageHelp: "Applies to confirmations sent to the reporting player. Custom kick reasons are unchanged.",
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
