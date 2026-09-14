# Teaminterne Führungsabstimmung

## Status und Freigabe

Die Funktion ist **standardmäßig deaktiviert**, auch nach einem Update. Der
voreingestellte Modus ist **Probelauf**: private Nachrichten und Abstimmungen,
aber niemals ein automatischer Kick. Es gibt keine KI-Abhängigkeit und keine
Auswertung von Sprachdaten.

Die Implementierung ist kein Ausrollungsauftrag. Vor einer Pilot-Ausrollung sind
Datenbank und Konfiguration zu sichern; zuerst ausschließlich RCON4 im Probelauf.
Aktivmodus und weitere Server benötigen eine separate Freigabe.

## Spielerablauf

1. Eine berechtigte Führungskraft meldet im **Team- oder Squadchat**:
   `!admin able redet nicht`, `!admin baker is not talking` oder
   `!admin commander redet nicht`. Auch `kommandant` und `kommandeur` sind Ziele.
2. Die normale Admin-Meldung wird sofort gespeichert und über die bestehenden
   Admin-Kanäle zugestellt. Eindeutige Kommunikationsbeschwerden können zusätzlich
   eine private Rückfrage mit Zielrolle, Squad und Spielernamen auslösen.
3. Der Melder bestätigt innerhalb von **60 Sekunden** mit `!yes`.
   `!no` oder Ablauf beendet das Angebot, nicht den Admin-Fall.
   Bestätigung ist **keine Ja-Stimme**. Bevor die Warnung beginnt, muss die
   ursprüngliche Meldung nachweislich beim Discord-Bot zugestellt worden sein.
4. Das Ziel wird privat aufgefordert, innerhalb von **60 Sekunden** im
   Führungskanal zu sprechen oder seine Rolle abzugeben. In dieser Phase kann
   der weiterhin berechtigte Melder mit `!no` zurückziehen.
   Eine Antwort des Ziels alleine beendet das Verfahren nicht.
5. Die berechtigten Führungskräfte erhalten direkte private Einladungen:
   `!yes` / `!no`, **120 Sekunden**. Groß-/Kleinschreibung und äußere
   Leerzeichen sind erlaubt, zusätzliche Argumente nicht. Die letzte gültige
   Antwort gilt. Keine vorzeitige Auswertung.
6. Nach Ablauf wird nochmals geprüft. Im Probelauf bleibt es bei einem Ergebnis;
   im Aktivmodus kann eine erfolgreiche Abstimmung einen **Server-Kick, keinen
   Bann**, auslösen. Nur ein eindeutig bestätigter echter Kick schließt den
   Admin-Fall automatisch.

Alle Workflow-Nachrichten sind Deutsch und Englisch. Es gibt keine globale
Einladung oder Ergebnisnachricht. Nicht zuordenbare Ziele, andere Beschwerden,
fehlende Berechtigungen oder unbekannter/globaler Chat bleiben normale
Admin-Meldungen.

### Formulierung der Meldung

Für das Abstimmungsangebot muss `!admin` am Anfang stehen. Der Squadname oder
`commander` / `kommandant` / `kommandeur` darf dagegen an beliebiger Stelle
danach vorkommen. Ein fester Satzbau ist nicht erforderlich. Zum Beispiel:

- `!admin der commander redet nicht`
- `!admin bitte mal prüfen able redet nicht`
- `!admin redet nicht: able`
- `!admin please check, the squadleader of Able is not talking`

Zusätzlich zum eindeutig erkannten Ziel im eigenen Team muss eine eindeutige,
unterstützte Kommunikationsbeschwerde enthalten sein, etwa `redet nicht`,
`spricht nicht` oder `is not talking`. `!admin able` allein oder andere Gründe
bleiben normale Admin-Reports. Die Erkennung verwendet feste Sprachmuster,
keine KI; sie versteht nicht jede beliebige Umschreibung. Die üblichen
Berechtigungen gelten weiterhin, und zuerst erhält der Melder die private
Rückfrage, noch keine sofortige Abstimmung.

## Wer darf teilnehmen?

- Ausschließlich Commander und Squadleader des betroffenen Teams.
- Dieselbe Führungsposition muss **mindestens fünf Minuten** durchgehend
  beobachtet worden sein. Ohne Verlauf beginnt die Beobachtung bei null.
- Gegen einen Squadleader sind **er und sein gesamter Squad ausgeschlossen**.
  Andere Squadleader und der Commander haben je eine Stimme.
- Gegen einen Commander dürfen nur die anderen berechtigten Squadleader starten
  und abstimmen. Der Commander selbst ist ausgeschlossen.
- Mindestens **drei Stimmberechtigte**. Erforderlich sind
  `floor(ursprünglich Stimmberechtigte / 2) + 1` Ja-Stimmen.
  Bei drei also zwei, bei sechs vier. Enthaltung ist keine Zustimmung.
- Der Teilnehmerkreis wird bei Bestätigung eingefroren. Neue Führungskräfte
  werden nicht nachträglich aufgenommen.
- Rollen-, Squad-, Team- oder Sitzungswechsel entfernen die Berechtigung und
  bereits abgegebene Stimmen dauerhaft. Die Mehrheitsschwelle sinkt nicht.
  Unter drei verbleibenden Berechtigten wird abgebrochen.
- Zielwechsel, Rollenabgabe, Disconnect oder ein neuer Amtsinhaber beenden den
  Vorgang. Niemand erbt die Abstimmung seines Vorgängers.

## Admins und Discord

Unter **Apps → Discord-Report-Bot → Führungsabstimmung** werden ausdrücklich
**serverbezogen** Aktivierung, Modus, Zeitwerte und Schutzzeiten eingestellt.
Die gemeinsame Discord-Anbindung wird dadurch nicht geändert.

Voraussetzungen: aktivierte Discord-Report-Zustellung (`DISCORD_REPORTS_ENABLED`),
verbundener/aktivierter Bot, Report-Kanal und hinterlegte Moderatorrollen.
Konfiguration benötigt `api.can_manage_leadership_votes`; Aktivieren zusätzlich
`api.can_kick_players`. Einzelstimmen und Status sind nur mit
`api.can_view_admin_incidents` verfügbar. Abbrechen benötigt zusätzlich
`api.can_claim_admin_incidents`. Es werden keine neuen Rechte automatisch
an bestehende Benutzer oder Gruppen vergeben.

Das optionale Incident-Feld `leadership_vote` enthält Modus, Phase, Zielrolle,
Zielspieler, Squad, Frist, feste Mehrheit, Teilnehmer und Stimmenstand.
Bestehende Incident-Statuswerte bleiben unverändert.

Discord aktualisiert dieselbe Report-Karte. Einzelne Stimmen erzeugen nur eine
Kartenänderung, keine zusätzlichen Benachrichtigungen. Bei Abbruch, fehlender
Mehrheit, unklarem Ausgang oder erfolgreichem Probelauf bleibt der Fall offen
und erhält eine Admin-Benachrichtigung als Antwort auf dieselbe Karte.
Spieler sehen keine Einzelstimmen; berechtigte Admins können den Verlauf prüfen.

Übernahme, manuelle Report-Aktion oder Änderung der Ziele stoppt das Verfahren.
Direkte Moderationsaktionen (u.a. Kick/Bann/Bestrafen, gespeicherte Verwarnung,
Teamwechsel, Squadentfernung) gegen das Ziel werden ebenfalls abgesichert.
Eine native Squad-Auflösung über numerische Indizes beendet vorsorglich alle
offenen Führungsverfahren dieses Servers, da diese Indizes keine stabilen
Spieleridentitäten sind.
Ein **bereits begonnener** Kick-Versand kann nicht zurückgerufen werden;
konkurrierende Maßnahmen erhalten dann einen Konflikt bis zum Ergebnis.

## Sicherheit und Laufzeit

- Ein offener Vorgang je Server und Team, einschließlich Bestätigung und Warnung.
  Kein globaler spielinterner Votekick, keine Warteschlange.
- Nach Beginn der Warnphase gelten ab Abschluss mindestens **zehn Minuten
  Team-Pause** und **30 Minuten Zielspieler-Schutz**. Admin-Reports bleiben möglich.
- Abgeschaltete Funktion oder geänderte Regeln beenden offene Verfahren.
  Ein bereits begonnener Kick muss zuerst sein Ergebnis erhalten.
- PostgreSQL-Transaktionssperre pro Server und eindeutiger Team-Slot schützen
  parallele Reports, Antworten und manuelle Aktionen.
- Eine getrennte Sitzungssperre erlaubt nur einen Fristverarbeiter je Server.
  Er läuft als isolierter Fünf-Sekunden-Schritt in der vorhandenen
  Routines-Laufzeit, sowohl im gemeinsamen als auch im getrennten Supervisor.
- Kompakte Bulk-Spielerdaten, bestätigte Rundenidentität und frische
  Positions-/Rollenbeobachtungen sind Voraussetzung. Beobachtungslücken über
  15 Sekunden setzen die Führungsdauer zurück. Veraltete/unvollständige Daten
  führen zum Abbruch, nicht zu einer vermuteten Berechtigung.
- Verbindungs- und Teamwechsel sowie Rundenwechsel invalidieren zusätzlich
  über die vorhandenen Log-Hooks. Ein Neustart beendet offene Verfahren und
  löscht den Führungsdauer-Verlauf.
- Private Nachrichten haben eine dauerhafte Outbox und werden bei unklarem
  Versand nicht automatisch wiederholt. Fehlende Zustellung senkt niemals
  die Mehrheit. Empfänger werden vor dem Versand nochmals dem Team zugeordnet.
- Vor einem Kick werden Reservierung und Sendebeginn dauerhaft festgehalten.
  Der Netzwerkaufruf läuft ohne Transport-Wiederholungen. Nur exakt bestätigter
  Erfolg zählt; Timeout, Fehler, Prozessabbruch oder ein Offline-Spieler sind
  kein Erfolgsbeweis. Keine automatische Wiederholung eines unklaren Kicks.
- `!yes` und `!no` werden bei Aktivierung auf Konflikte geprüft.
  Konfigurierte Chatbefehle werden nicht still überschrieben.
- Abstimmungsbezogene `!admin`-Kommunikationsmeldungen und exakte Antworten
  werden bei eingeschalteter Funktion aus allgemeinen Chat-/Log-Webhooks
  herausgefiltert. Der Admin-Report und private Admin-Protokolle bleiben erhalten.

**Grenzen:** RCON kann weder Sprache beurteilen noch bereits global geschriebene
Spielernachrichten verstecken. Rollen werden regelmäßig beobachtet, nicht als
lückenloser Sprach-/Rollen-Stream geliefert. Spielseitige Kick-Anzeigen und
Nachrichtenlängen müssen vor Aktivmodus getrennt in HLL und HLLV geprüft werden.
Vollständige Unsichtbarkeit gegenüber der Gegenseite wird nicht zugesichert.

## Migrationen und Tests

- Alembic `e3a8b1c5d209` nach `d2f7a4c9b8e1`: neue Tabellen
  `leadership_vote`, `leadership_message`, `leadership_presence` und optionale
  Incident-Felder. Additiv; bestehende Meldungen werden nicht ersetzt.
- Django `0038_leadership_vote_permission` folgt auf den bestehenden Merge
  `0037_merge_eventador_live_view`.
- Rollback der Migration löscht die neuen Workflow-Daten. Deshalb erst
  deaktivieren, offene Sendungen klären und ein Backup anlegen.

Lokale Tests verwenden ausschließlich synthetische Spieler, Stub-Transport,
SQLite und die Frontend-Demo. Die beiden echten PostgreSQL-Paralleltests sind
über `LEADERSHIP_VOTE_TEST_DB_URL` an eine ausdrücklich freigegebene,
wegwerfbare Testdatenbank gebunden. Sie erstellen und entfernen ausschließlich
ein eigenes zufällig benanntes Test-Schema. Die bestehende CI führt sie gegen
ihre lokale PostgreSQL-Instanz aus.

Lokaler Prüfstand der Implementierung: 222 ausgewählte Backend-/Regressionstests,
78 Discord-Service-Tests, zwei Django-Migrations-/Berechtigungstests und vier
Browser-Tests bestanden. Produktions-Build sowie CSRF-, Aktions-, Text- und
Polling-Prüfungen bestanden. Die zwei PostgreSQL-Paralleltests wurden mangels
lokaler PostgreSQL-Instanz übersprungen, nicht als erfolgreich gewertet.
Die breitere bestehende Django-Integrationssuite ließ sich ohne Redis und
SQL-Testverbindung nicht erfolgreich abschließen. Diese Integrationsabnahme
und eine wiederhergestellte Testdatenbank bleiben vor Ausrollung erforderlich.

Vor Ausrollung bleiben erforderlich:

1. PostgreSQL-Paralleltests und Migration gegen eine wiederhergestellte,
   isolierte Testdatenbank; kein Test gegen Produktion.
2. Backup und separate Ausrollungsfreigabe für RCON4 im Probelauf.
3. Vollständige Votes gegen Squadleader und Commander, gescheiterter Vote,
   Admin-Übernahme, Rollen-/Teamwechsel und Neustart mit abgestimmten Teilnehmern.
4. Nachrichten- und Kick-Anzeigen für HLL **und** HLLV prüfen.
5. Erst danach explizite Freigabe für echte Kicks und weitere Server.
