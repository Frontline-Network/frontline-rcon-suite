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
   `!admin able`, `!admin bitte mal prüfen able redet nicht` oder
   `!admin commander`. Auch `kommandant` und `kommandeur` sind Ziele.
2. Die normale Admin-Meldung wird sofort gespeichert und über die bestehenden
   Admin-Kanäle zugestellt. Ein eindeutig erkanntes Führungsziel kann zusätzlich
   direkt eine Führungsabstimmung mit Zielrolle, Squad und Spielernamen auslösen.
   Der ausgeschriebene Grund ist dafür keine Voraussetzung.
3. **Keine zusätzliche Startbestätigung:** Der eindeutige Report einer berechtigten
   Führungskraft friert den Teilnehmerkreis ein und reiht die Einladungen ein.
   Der Report ist **keine Ja-Stimme**. Vor dem Versand muss die ursprüngliche
   Meldung nachweislich beim Discord-Bot zugestellt worden sein. Fehlt diese
   Zustellung bis zum Ablauf der Versandfrist, wird ohne Kick abgebrochen.
4. Ohne weitere Antwort des Melders werden die privaten Einladungen an die berechtigten
   Führungskräfte eingereiht: Deutsch zuerst, danach Englisch als eigene Nachricht.
   Der Versand erfolgt im nächsten regulären Verarbeitungsschritt. Es gibt keine
   Warnung oder zusätzliche Wartefrist; das Ziel erhält keine privaten Hinweise
   oder Ergebnisse. Alte gespeicherte Zielnachrichten werden ebenfalls blockiert.
5. Die berechtigten Führungskräfte stimmen ab:
   `!yes` / `!no`, **120 Sekunden**. Groß-/Kleinschreibung und äußere
   Leerzeichen sind erlaubt, zusätzliche Argumente nicht. Die letzte gültige
   Antwort gilt. Keine vorzeitige Auswertung. Auch `!no`
   des Melders eine Gegenstimme, kein Rückzug des gesamten Votes.
6. Nach Ablauf wird nochmals geprüft. Im Probelauf bleibt es bei einem Ergebnis;
   im Aktivmodus kann eine erfolgreiche Abstimmung einen **Server-Kick, keinen
   Bann**, auslösen. Nur ein eindeutig bestätigter echter Kick schließt den
   Admin-Fall automatisch.

Alle Workflow-Nachrichten sind Deutsch und Englisch. Es gibt keine globale
Einladung oder Ergebnisnachricht. Nicht zuordenbare Ziele,
fehlende Berechtigungen oder unbekannter/globaler Chat bleiben normale
Admin-Meldungen.

Die alten Konfigurationsfelder `confirmation_seconds` und `warning_seconds`
werden für ältere Clients weiterhin akzeptiert, aber für neue Verfahren nicht
mehr verwendet. Der Backend-Hotfix ändert bestehende Frontend-Dateien nicht;
alte Oberflächen können die Bestätigung deshalb noch beschreiben. Neue Verfahren
beginnen direkt in `inviting`, nicht `confirming`. Spielseitige Kick-Anzeigen
bleiben davon unberührt.

### Formulierung der Meldung

Für das Abstimmungsangebot muss `!admin` am Anfang stehen. Der Squadname oder
`commander` / `kommandant` / `kommandeur` darf dagegen an beliebiger Stelle
danach vorkommen. Ein fester Satzbau ist nicht erforderlich. Zum Beispiel:

- `!admin der commander redet nicht`
- `!admin bitte mal prüfen able redet nicht`
- `!admin able`
- `!admin commander`
- `!admin redet nicht: able`
- `!admin please check, the squadleader of Able is not talking`

Es reicht ein eindeutig erkanntes Ziel im eigenen Team; der Grund darf fehlen
oder frei formuliert sein. Die Automatik beurteilt den Grund nicht und benötigt
keine KI. Die Einladungen zeigen den gemeldeten Grund als Spielerangabe, ohne
pauschal fehlende Kommunikation zu behaupten. Die ursprüngliche Meldung bleibt
unverändert erhalten. Bei erfüllten Berechtigungs- und Schutzregeln startet die
Meldung allein die Abstimmung, ohne eine Stimme automatisch abzugeben.

### Erweiterte Zielerkennung

Die Führungsabstimmung verwendet eine eigene deterministische Zielauflösung.
Die normale Report-Suche mit ihren unscharfen Spielervorschlägen bleibt erhalten;
ein bloß ähnlicher Spielername wird nicht automatisch zum Abstimmungsziel.

- Aktuelle Squadnamen des eigenen Teams werden unabhängig von ihrer Position
  nach `!admin` erkannt, auch mit Satzzeichen und wechselnder Großschreibung.
- NATO-Bezeichnungen werden über denselben Buchstaben zugeordnet, beispielsweise
  `Bravo` zu `Baker`, `Echo` zu `Easy`, `Kilo` zu `King`. Die Zuordnung erfolgt
  ausschließlich gegen vorhandene Squadnamen, niemals über numerische RCON-IDs.
  Gibt es etwa gleichzeitig Baker und Bravo im selben Team, wird nicht geraten.
- Einzelbuchstaben brauchen einen eindeutigen Rollenbezug: `SL B`, `B SL`,
  `Squad B` oder `B squad`. Ein alleinstehendes `a`, `I` oder `B` genügt nicht.
  Zusammenschreibungen wie `echosquad` und `SquadBravo` sind ebenfalls möglich.
- Die in echten Reports gefundenen Squad-Tippfehler `Eays`, `Gorge` und `Geoge`
  sind ausdrücklich hinterlegt. Es gibt keine beliebige Ähnlichkeitssuche für
  automatische Ziele. Neue Schreibfehler benötigen eine geprüfte Ergänzung.
- Commander-Aliasse umfassen `commander`, `kommandant`, `kommandeur`, `cmd`,
  `cmdr`, `cdr`, `kommi`, `kommander`, `komander`, `comander`, `kommandar` und
  `kommandat`. **Nicht** `com`: In vielen Meldungen heißt das Kommunikation.
- Squad und vollständiger aktueller Spielername werden über dieselbe Spieler-ID
  zusammengeführt. `SL` plus vollständiger, eindeutiger Name eines aktuellen
  Squadleaders ist ebenfalls möglich. Ein Spielername ohne Führungsbezug bleibt
  ein normaler Admin-Report. Namensbestandteile sind kein zweites Squad-Ziel.
- Verschiedene Ziele, doppelte Namen, fehlende oder doppelte Amtsinhaber und
  Hinweise auf bereits ausgeschiedene Spieler führen zu keinem Angebot.
  Ein gemeldeter Amtsvorgänger wird nicht durch seinen Nachfolger ersetzt.

Jede Einladung nennt den tatsächlich erkannten Squad und Spielernamen bzw.
Commander. Bei falschem Ziel können die Führungskräfte mit `!no` gegen den Kick
stimmen; Admins können den Vorgang übernehmen/abbrechen. Worterkennung ist kein
Beweis für die Bedeutung eines Satzes: Ein Wort wie „love“ kann auch beiläufig
vorkommen. Deshalb bleiben Ziel-, Berechtigungs- und Mehrheitsprüfungen notwendig.

Nur wenn sämtliche Angebotsvoraussetzungen erfüllt sind, wird der kanonische
Zielspieler als primäres Ziel mit dem bestehenden Admin-Fall verknüpft. Text,
Grund und weitere Vorschläge bleiben erhalten. Ohne Angebot wird der normale
Fall nicht umgeschrieben. `leadership_vote.target_resolution` dokumentiert die
verwendeten Textstellen und Erkennungsregeln für berechtigte Admins. Diese
Erweiterung nutzt bestehende JSON-Felder und benötigt keine neue Migration.

### Datengrundlage der Erweiterung (14. September 2026)

Read-only-Suche auf RCON1–4: 640 Chat-Logzeilen mit `!admin` im abgefragten
Zeitraum 1. Juni bis 14. September 2026 (UTC). Davon stammen 166 aus Juni/Juli
(RCON1: 143, RCON2: 23; keine Treffer auf RCON3/4) und 474 aus August/September
(37, 48, 291 und 98 auf RCON1 bis RCON4). Zusätzlich wurden 443 gespeicherte
Admin-Fälle aus August/September auf die bisherige Zielerkennung geprüft.
Diese Fälle überlappen mit den Chat-Logs und werden **nicht hinzuaddiert**.

Die Quelle enthält auch Tests und andere Admin-Anliegen, nicht nur Beschwerden
gegen Führungskräfte. Daraus folgt weder eine 95-%-Quote für Kommunikation noch
eine garantierte Vollständigkeit aller zukünftigen Schreibweisen. Historische
Nachrichten beweisen auch keine damalige Stimmberechtigung oder fehlende Sprache.

Beispiele aus den geprüften Meldungen:

| Tatsächliche Formulierung (ohne Spielernamen) | Verarbeitung bei passendem aktuellem Team |
| --- | --- |
| `!admin bitte How SL kicken, redet nicht` | How, unabhängig vom Satzbau |
| `!admin Bravo SL kicken aufgrund fehlender komms` | Baker über NATO-Alias |
| `!admin Bitte KILO SL kicken, redet nicht` | King über NATO-Alias |
| `!Admin Eays SL kicken, der redet nicht` | Easy über geprüften Tippfehler |
| `!admin SL Gorge keine Com plz ban` | George; „Com“ ist kein Commander-Ziel |
| `!admin sl B hat kein mic` | Baker über Squad-Buchstaben |
| `!admin echosquad not communicating` | Easy trotz Zusammenschreibung |
| `!admin Kommander spricht nicht` | Aktueller eigener Commander |
| `!admin item` | Führungsabstimmung auch ohne ausgeschriebenen Grund |
| `!admin how fox redet nicht` | Kein Angebot: zwei Squad-Ziele |
| `!ADMIN BEIDE AUFKLÄRER sprechen nicht` | Normaler Admin-Fall: kein einzelnes Ziel |

Auch Kombinationen aus „SL + Squad + Spielername“ kamen wiederholt vor.
In den Tests sind alle Spieleridentitäten synthetisch. Rohdaten, Spielernamen,
IDs und Zugänge aus Produktion werden nicht ins Repository übernommen.
Die NATO-Schreibweisen wurden anhand der
[offiziellen NATO-Liste](https://www.nato.int/en/about-us/nato-history/history-by-theme/symbols-of-nato/nato-phonetic-alphabet)
abgeglichen; die Zuordnung zu den aktuellen Spiel-Squads ist unsere eigene
Implementierungsregel, keine Aussage dieser Quelle über HLL oder HLLV.

Regressionen: `tests/test_leadership_targets.py` prüft Buchstaben, NATO-Aliasse,
beobachtete Formulierungen und bewusste Ablehnungen. Die Integrationssuite
spielt zusätzliche echte Formulierungen mit synthetischen Spielern durch den
vollständigen Probelauf und prüft Admin-Übernahme, Nachfolge, Abschalten und
unveränderte gewöhnliche Reports. Das ersetzt keine spielseitige Live-Abnahme.
Prüfstand dieser Erweiterung: 477 ausgewählte Backend-/Regressionstests und
vier Browser-Tests bestanden; keine Produktionsaktionen. Die Browser-Prüfung
umfasst die neuen Hinweise auf Deutsch/Englisch und auf Desktop/Mobilgeräten.

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
- Der Teilnehmerkreis wird beim Report-Start eingefroren. Neue Führungskräfte
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

- Ein offener Vorgang je Server und Team, einschließlich Einladungsversand.
  Kein globaler spielinterner Votekick, keine Warteschlange.
- Nach dem Report-Start gelten ab Abschluss mindestens **zehn Minuten
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
- Mit `!admin` beginnende Meldungen und exakte Antworten werden bei
  eingeschalteter Funktion aus allgemeinen Chat-/Log-Webhooks herausgefiltert.
  Dies gilt vorsorglich für alle solchen Admin-Rufe, weil die Spiegelung vor
  der Zielauflösung erfolgt und auch Meldungen ohne Grund ein Angebot auslösen
  können. Bei ausgeschalteter Funktion bleibt die bisherige Spiegelung erhalten.
  Der Admin-Report und private Admin-Protokolle bleiben immer erhalten.

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
