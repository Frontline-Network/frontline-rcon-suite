# Frontline RCON Suite

Die **Frontline RCON Suite** ist der private Frontline-Fork von Hell Let Loose Community RCON (CRCON). Das Repository enthält die klassische CRCON-Serververwaltung und erweitert sie um Frontline-spezifische Funktionen für Hell Let Loose und Hell Let Loose: Vietnam, Moderation, Reports/Incidents, Mobile Admin, Discord-Integration, AI-gestützte Moderationsanalyse, Player-Message-Campaigns, Frontline-VIP-Integration und gehärteten Produktionsbetrieb.

Das Projekt basiert auf dem ursprünglichen CRCON von Julien Marechal und behält dessen MIT-Lizenz und Provenienz. Die Frontline-Erweiterungen ersetzen diese Herkunft nicht; sie bauen darauf auf.

---

# Teil 1 – Was macht die Frontline RCON Suite?

## Serververwaltung für HLL und HLL Vietnam

Die Plattform verbindet RCON, Spieler-/Rundeninformationen, Moderation und Verwaltungsoberflächen. Frontline betreibt damit mehrere CRCON-Instanzen beziehungsweise Serverprofile.

Für externe Belegungs- und Seeding-Analysen gibt es eine geschützte
[Spielerzahl-Historie mit API und Einrichtungsanleitung](docs/population-history-api.md).

## Moderation und Spielerakten

Administratoren können Spielerinformationen, Livekontext, historische Daten, VIP-/Adminzustände und Moderationsaktionen über die CRCON-Funktionen verwalten.

## Reports und Incidents

Spieler können über definierte Chat-Trigger Reports erzeugen. Daraus entstehen Incidents mit Reporter-, Ziel- und Kontextinformationen.

Die Incident-Schicht kann mehrere betroffene Spieler beziehungsweise Squads enthalten und bewahrt Snapshots des Zustands zum Reportzeitpunkt.

## Mobile Admin

Eine separate Mobile-Admin-Integration erlaubt Administratoren, ihre eigene CRCON-Identität sicher mit einem mobilen Client zu koppeln.

Die App verwendet keine gemeinsamen QR-Codes oder geteilten Adminaccounts. Jeder Administrator koppelt sein eigenes Gerät.

## Discord-Integration

Incidents und Moderationsinformationen können über einen zentralen Frontline-Discord-Service an Discord ausgeliefert werden.

Der zentrale Dienst ermöglicht, dass einzelne CRCON-Installationen nicht selbst Discord-Bot-Tokens oder OpenAI-Keys verwalten müssen.

## AI-Moderationsanalyse

Die Frontline-Erweiterung kann Report-/Chat-/Namenskandidaten über einen verwalteten Analysepfad klassifizieren.

Wichtig: Das AI-System **führt keine Moderationsaktion selbst aus**. Es liefert strukturierte Analyse für menschliche beziehungsweise nachgelagerte Policy-Entscheidung.

## Kampagnen und Player Messages

Neben klassischen Broadcasts existiert eine persistente Campaign-Delivery-Schicht für gestaffelte Direktnachrichten an Spieler.

Diese kann Empfängergruppen, Mindest-Sessionzeit und Abstände berücksichtigen und speichert Zustellversuche dauerhaft.

## HLLV-spezifische Workarounds

Hell Let Loose: Vietnam besitzt andere Identitäten und teilweise anderes Serververhalten. Der Frontline-Fork enthält deshalb gezielte HLLV-Anpassungen, beispielsweise für EOS-IDs und das erneute Aktivieren bestätigter Spectatorrechte nach Reconnect.

## Was dieses Repo nicht ist

Nicht zuständig für:

- Discord-Level-/Communitysystem → `frontline-level`
- globale Server-/Sessionerfassung → `frontline-game-tracker`
- Positions-/Heatmaptelemetrie → `hll-telemetry`
- HLL-Seeding-/VIP-Lifecycle → `seeding-suite`
- Host-/Dockerorchestrierung → `frontline-gamehost`

---

# Teil 2 – Technische Dokumentation

## 1. Upstream und Lizenz

Das Repository basiert auf Hell Let Loose Community RCON.

Die vorhandene `LICENSE` ist MIT und nennt Julien Marechal als ursprünglichen Copyrightinhaber.

Frontline-spezifische Erweiterungen müssen diese Provenienz bei Weitergabe des Codes erhalten.

## 2. Default Branch

Der aktuelle Default Branch des Repositories ist:

```text
master
```

Das unterscheidet dieses Repo von vielen anderen Frontline-Repositories auf `main`.

Deployskripte und Dokumentation müssen deshalb nicht automatisch `main` annehmen.

## 3. Technologiestack

Die Plattform besteht aus mehreren Technologien:

- Python Backend / RCON-Logik
- Django-Web-/API-Schicht
- SQLAlchemy-/Alembic-Migrationen
- PostgreSQL
- Frontend/Web-UI
- Supervisor-Prozesse für Hintergrundloops
- Docker / Compose
- optionaler Flutter-Mobile-Client
- separater Discord-/AI-Service

`pyproject.toml` konfiguriert unter anderem Black und isort für Python 3.11.

## 4. Wichtige Sourcebereiche

```text
rcon/                 Kern-RCON, Models, Loops, Policies, Campaigns
rconweb/              Django/Web/API
alembic/              Schema-Migrationen
frontend/             Weboberfläche
callback_service/     Integrations-/Callbackkomponente
push_relay/           Mobile Push Relay
discord_service/      zentraler Discord-/AI-Service
scripts/              Deployment, E2E, Diagnose
supervisor/           Hintergrundprozesskonfiguration
tests/                umfangreiche Regressionen
docs/                 Mobile Admin, Production Deploy usw.
```

Die genaue Verzeichnisstruktur kann sich weiterentwickeln; diese Bereiche sind aus dem geprüften Source-/Doku-Stand belegt.

Der private, revisionsgebundene Eventador-Vertrag ist in
[`docs/eventador-control-api-v1.md`](docs/eventador-control-api-v1.md) beschrieben.

## 5. CRCON-Core bleibt Grundlage

Frontline ersetzt nicht die grundlegende CRCON-Architektur.

Weiterhin zentral sind:

- RCON-Verbindung
- Spielerlisten
- Serverzustand
- Moderationsaktionen
- User/Permissions
- Scoreboards/History
- Serverkonfiguration
- Hintergrundloops

Frontline-Erweiterungen bauen auf diesen bestehenden Contracts auf.

## 6. Mehrere Serverinstanzen

CRCON wird serverbezogen betrieben. Viele Tabellen und Abläufe besitzen eine `server_number`-Beziehung.

Dadurch kann dieselbe Codebasis mehrere getrennte HLL-/HLLV-Server verwalten, ohne deren Zustände zu vermischen.

## 7. HLL und HLL Vietnam

Der Fork unterstützt sowohl klassisches Hell Let Loose als auch Hell Let Loose: Vietnam.

Dabei dürfen Identitäts-/Protocolldetails nicht blind gleichgesetzt werden.

Beispiel:

- klassisches HLL verwendet typischerweise SteamID64 im entsprechenden Pfad;
- HLLV-Adminoperationen können EOS Product User IDs verwenden.

## 8. EOS-ID-Schutz

Der HLLV-Spectator-Workaround prüft explizit die erwartete 32-Zeichen-EOS-ID und lehnt eine klassische 17-stellige SteamID in diesem Pfad ab.

Damit soll keine falsche Identitätsform an HLLV-Admincommands gesendet werden.

## 9. HLLV Spectator Reconnect Fix

HLLV kann einen Spectator-Eintrag in `GetAdminUsers` behalten, obwohl die tatsächlichen Spectatorrechte nach Reconnect nicht wirksam sind.

Der Frontline-Fix arbeitet deshalb additiv:

1. nur HLLV;
2. nur definierte Rolle `spectator`;
3. zunächst vorhandenen Adminzustand prüfen;
4. Cache löschen beziehungsweise Fresh Read erzwingen;
5. Rolle erneut live bestätigen;
6. erst dann `AddAdmin` erneut ausführen.

## 10. Warum Fresh Read vor AddAdmin?

Ohne frischen Read könnte ein veralteter Cache eine Rolle wiederherstellen, die ein Administrator inzwischen bewusst direkt am Server entfernt hat.

Der Fix soll deshalb **keine gelöschte Berechtigung auferstehen lassen**.

## 11. Additiv statt destruktiv

Der Reconnect-Fix ruft kein `remove_admin` auf.

Wenn Reapply fehlschlägt, bleibt der Fehler isoliert und unterbricht nicht die normale CONNECTED-Logverarbeitung.

## 12. Incident-System

Reports werden nicht nur als Discord-Nachricht behandelt, sondern als persistenter Incidentzustand.

Ein Incident kann enthalten:

- Quelle
- Reporter
- Grund / Snapshotkontext
- bestätigte oder vorgeschlagene Subjects
- Squads
- Status / Claim / Resolution
- Events/Notes
- Discord Delivery State

## 13. Incident Sources

Der aktuelle Schema-Stand unterstützt unter anderem Quellen wie:

```text
chat
manual
ai_chat
ai_player_name
```

Damit wird zwischen klassischem Spielerreport und automatisch erzeugtem Analyse-/Moderationskandidaten unterschieden.

## 14. Report-Trigger

Mit aktivierter Incident-Integration können Chatnachrichten wie:

```text
!admin Player Name reason
```

Incidents erzeugen.

Mehrere Triggerwörter können konfiguriert werden.

## 15. Deduplizierung von Reports

Identische Reports desselben Spielers und Servers werden für ein kurzes Zeitfenster dedupliziert.

Das schützt den Incidentbereich vor versehentlichen oder absichtlichen Wiederholungsfluten.

## 16. Incident Context V2

Der Mobile-/Incident-Pfad besitzt einen konfigurierbaren Context-Modus:

```text
disabled
shadow
enabled
```

### disabled

ursprünglicher beziehungsweise begrenzter Resolver.

### shadow

reichere Kandidaten werden gespeichert, aber nicht automatisch bestätigt.

### enabled

nur eindeutig exakte Matches können automatisch bestätigt werden; fuzzy Matches bleiben Vorschläge.

## 17. Multi-Subject-Incidents

Ein Incident kann mehrere Spieler- und Squad-Subjects enthalten.

Das ist wichtig für Reports, die sich auf mehrere Personen oder eine Squad-Situation beziehen.

## 18. Keine implizite Squad-Aktion

Squadmitglieder müssen einzeln ausgewählt werden.

Es existiert keine implizite „Aktion gegen das gesamte Squad“, und der Squadleader wird nicht automatisch als Ziel einer Moderationsaktion interpretiert.

## 19. Immutable Snapshots

Incidents bewahren Reporter-/Subject-Snapshots vom Reportzeitpunkt.

Die UI kann zusätzlich aktuellen Serverzustand anzeigen.

Damit werden zwei unterschiedliche Wahrheiten getrennt:

```text
Was war beim Report bekannt?
Was ist jetzt live?
```

## 20. Kürzlich disconnectete Targets

Der aktuelle Fork enthält eine Reparatur, um kürzlich getrennte Reporttargets wieder aufzulösen.

Das adressiert die Race Condition, dass ein Spieler zwischen Report und Contextauflösung den Server verlässt.

## 21. Mobile Admin Pairing

Die Mobile-Admin-Integration ist opt-in und standardmäßig deaktiviert.

Pairing wird aus einer bereits authentifizierten CRCON-Websession gestartet.

Ein Administrator erzeugt einen kurzlebigen One-Time-QR-Code und bestätigt einen auf beiden Geräten sichtbaren Code.

## 22. Kein Shared Mobile Account

Jedes Gerät wird an das individuelle CRCON-Konto gekoppelt.

Es gibt keinen gemeinsamen Team-QR-Code oder einen universellen Mobile-Adminaccount.

Dadurch bleiben CRCON-User, Rollen und Permissions maßgeblich.

## 23. Mobile Token Lifecycle

Die Dokumentation beschreibt:

- opaque Access Tokens
- gehashte Speicherung in CRCON
- kurze Access-Token-Laufzeit
- Refresh-Token-Rotation
- Idle-Lifetime
- absolute Lifetime

Damit ist Mobile Auth nicht nur ein langlebiger statischer API-Key.

## 24. Permission Changes wirken weiter

Gerätebindung friert Berechtigungen nicht für Monate ein.

User-Deaktivierung, Device Revocation und Permissionänderungen werden bei nachfolgenden Requests berücksichtigt.

## 25. Mobile Secrets auf dem Gerät

Mobile Secrets werden in Keychain beziehungsweise Android Secure Storage gespeichert.

Der lokale Drift-Cache verwendet einen getrennten Schlüssel aus dem OS-Keystore.

## 26. Keine Offline-Moderationswrites

Schreibende Mobile-Aktionen werden nicht offline gequeued oder später blind wiederholt.

Das verhindert, dass ein alter Kick/Ban nach Wiederverbindung unerwartet ausgeführt wird.

## 27. Action Confirmation

Kick und temporärer Ban verlangen laut Doku Grund und explizite Bestätigung.

Der Mobile-E2E-Runner führt standardmäßig keine Spieleraktion aus.

## 28. Mobile E2E Gate

`scripts/mobile_admin_beta_e2e.py` kann einen sicheren Workflow prüfen:

- Incident lesen
- claimen
- optional Note
- resolve

Eine tatsächliche Spieleraktion benötigt einen expliziten `--allow-action`-Gate und ein bestätigtes Ziel.

## 29. Mobile Push Relay

Push ist als separate Komponente implementiert.

CRCON übermittelt keine vollständigen Moderationsinhalte an den Relay.

Der dokumentierte Payload enthält nur minimale IDs/Ereignisinformationen und keine Playernamen, IDs, Reportgründe oder Adminnotes.

## 30. Push Permission Check

Der Mobile Push Worker prüft aktive CRCON-Permissions für Deliveries.

Ein früher einmal berechtigtes Gerät soll nicht dauerhaft Push-/Adminmacht behalten, wenn der User später Rechte verliert.

## 31. Push Registration Limits

Der Relay besitzt Rate-/Capacity-Grenzen für Device Registration.

Retry desselben Push Tokens ist idempotent.

## 32. Zentraler Discord Service

Frontline betreibt einen separaten Discord-Integrationsservice.

Zweck:

- ein zentral verwalteter Bot Token
- zentrale Discord App
- zentral verwalteter OpenAI-Key
- CRCON-Installationen pairen sich mit diesem Dienst

Kunden-/Einzelinstanzen müssen dadurch nicht eigene Bot-/AI-Secrets verwalten.

## 33. Separate Deploymentgrenze

Der Discord Service ist **nicht** einfach ein weiterer Thread im CRCON-Prozess.

Er besitzt einen eigenen Deployment-/DB-/Secretkontext.

Das reduziert den Blast Radius eines CRCON-Instanzfehlers.

## 34. Discord Service Datenhaltung

Der Service speichert Integrations-/Capability-/Mapping-/Idempotenzdaten.

Die eigene Doku betont, dass er keine DB-Spalten für vollständige Report-/Chat-/Namensinhalte, Aktionsgründe, Nachrichten oder Previews benötigt.

## 35. Capability-Modell

Beim Pairing werden getrennte zufällige Capabilities für:

- CRCON -> Service Events
- Service -> CRCON Actions

erzeugt.

Empfänger speichern nur Digest; Sender kann die benötigte rohe Capability verschlüsselt halten.

## 36. Capabilities nicht in URLs

Die Service-Doku verbietet, Capabilities in URLs oder Logs zu platzieren.

Dadurch sollen Reverse-Proxy-/Accesslogs keine langlebigen Aktionsberechtigungen enthalten.

## 37. Callback-Zielschutz

Pairing kann Callbackhosts allowlisten und lehnt private/link-local Ziele sowie falsche Callbackpfade ab.

Damit wird der zentrale Service nicht als SSRF-Proxy zu beliebigen internen Zielen verwendet.

## 38. Discord Interaction Verification

Der zentrale Service verwendet den Discord Public Key zur Verifikation eingehender Interactions.

Discord-Requests werden damit nicht allein aufgrund der URL als vertrauenswürdig behandelt.

## 39. AI-Moderation: zwei Stufen

Der verwaltete Analyzer verwendet:

1. Moderation Model / Safety Gate
2. strukturierten generativen Analysecall

Das hard-hit-Sicherheitsbit wird aus dem Moderation Gate gesetzt und nicht aus untrusted Text oder generativem Output übernommen.

## 40. Prompt-Injection-Grenze

Der Systemprompt behandelt Report-/Chat-/Namensinhalte ausdrücklich als **untrusted evidence**.

Anweisungen innerhalb dieses Textes sollen nicht ausgeführt werden.

## 41. Structured Output

Die AI-Antwort wird gegen ein definiertes `ModerationAnalysis`-Schema geparst.

Dadurch soll ein freier Prosatext nicht direkt als Maschinencommand interpretiert werden.

## 42. AI führt keine Aktion aus

Der Analyzer besitzt keine Tools für direkte Serveradministration.

Er klassifiziert und empfiehlt für Review.

Moderationsausführung bleibt in den CRCON-/Adminpfaden.

## 43. Moderation Analysis Records

Die CRCON-Datenbank speichert Analysemetadaten, darunter abhängig vom Schema:

- Source
- Incident
- Player
- Candidate Fingerprint
- Analysis JSON
- Visibility
- Model Version
- Prompt Version
- Policy Profile/Version
- Dedupe-Zeit

Damit ist AI-Ausgabe versionierbar und auditierbar.

## 44. Candidate Outbox

AI-Kandidaten werden über eine Outbox transportiert.

Felder umfassen unter anderem:

- Source
- Server
- Player
- Fingerprint
- gematchte Rule IDs
- Policy
- Shadow Flag
- Attempts
- Next Attempt
- Delivery/Analysis Status

## 45. AI Shadow Mode

Kandidaten können `shadow_only` sein.

Damit kann neue Analyse zunächst beobachtet werden, ohne sofort sichtbare Incidents oder operative Folgen zu erzeugen.

## 46. Discord Incident Delivery

Incident-Events besitzen einen eigenen Delivery-State mit:

- Attempts
- Next Attempt
- Delivered At
- Last Error

Damit ist Discord-Zustellung retrybar und nicht an die Transaktion gekoppelt, die den Incident erzeugt hat.

## 47. Campaign Delivery

Der Fork besitzt persistente Direct-Player-Campaigns.

Die Migration erzeugt `campaign_deliveries` mit server-, campaign-, player- und sessionbezogenen Daten.

## 48. Warum Delivery pro Session?

Die Unique Constraint bindet Delivery an:

```text
server_number
campaign_id
player_session_id
```

Damit kann dieselbe Kampagne in einer späteren echten neuen Session wieder relevant sein, ohne innerhalb derselben Session doppelt gesendet zu werden.

## 49. Campaign States

Der Code verwendet Zustände wie:

```text
queued
sending
sent
failed
expired
```

und speichert Attempt-/Retryinformationen.

## 50. Stale Sending Recovery

Es existiert eine Schwelle für zu lange `sending`-Zustände.

Damit kann ein Workerabbruch nach Claim einer Delivery später erkannt werden, statt den Datensatz für immer im Zwischenzustand zu lassen.

## 51. Campaign Retry

Direktnachrichten besitzen begrenzte Retryanzahl und definierte Retrydelays.

Damit wird ein temporärer Fehler nicht sofort endgültig, aber auch nicht unendlich oft wiederholt.

## 52. Recipient Groups

Campaigns können Zielgruppen unterscheiden, beispielsweise:

```text
vip
non_vip
all
```

Dafür liest der Worker Onlineplayer und VIPzustand.

## 53. Minimum Session Time

Eine Campaign kann eine Mindest-Sessiondauer verlangen.

Damit wird ein Spieler nicht zwangsläufig direkt beim Connect mit Kampagnenmeldungen überschüttet.

## 54. Player Gap / Global Interval

Der Campaign-Code besitzt sowohl globale Sendeintervalle als auch Abstände pro Spieler.

Dadurch können Serverlast und Nutzerfrequenz getrennt begrenzt werden.

## 55. Sessionbezug

Campaign Delivery verwendet aktive PlayerSessions aus der CRCON-Datenbank.

Das verbindet Direct Messaging mit dem tatsächlichen aktuellen Spielaufenthalt.

## 56. Broadcast vs. Direct Campaign

Klassische Autobroadcasts und direkte Player Messages verwenden dieselbe Konfigurationsfamilie, aber unterschiedliche Delivery Modes.

Der klassische Broadcastloop filtert auf `broadcast`; der Campaign Worker verarbeitet `player_message`.

Damit werden beide Versandarten nicht doppelt ausgeführt.

## 57. Supervisor Worker

Die kombinierte Standardkonfiguration startet drei Supervisor-Programme:
`frontline_runtime`, RQ-`workers` und `cron`.

Der gemeinsame Python-Prozess betreibt die kompatiblen CRCON-Hintergrunddienste
als einzeln überwachte, kooperativ stoppbare Threads. Dazu gehören auch
Campaign Messages, Logs, Scoreboard, Automod, Seed-VIP und VIP Rewards. Die
Service-API behält ihre bisherigen Namen sowie Start-/Stopp-Steuerung bei.

Die getrennte Supervisor-Konfiguration bleibt als unterstützter Rollback
erhalten. RQ und Cron werden wegen ihres abweichenden Ausführungsmodells nicht
in den Thread-Runtime-Prozess integriert.

## 58. Consolidated Loops / Scaling

Aktuelle Commits dokumentieren die zweistufige Konsolidierung der kompatiblen
Hintergrundloops und die zugehörigen Performance-/Scalingoptimierungen.

Das Ziel ist, bei mehreren RCON-Instanzen unnötige Poller, DB-Verbindungen und Dashboardlast zu reduzieren.

## 59. DB Connection Pool in Workerprozessen

Bestimmte Supervisorprozesse setzen `HLL_DB_DISABLE_CONNECTION_POOL=1`.

Damit können kurz-/loopbasierte Worker vermeiden, jeweils einen großen Pool zu halten.

## 60. Dashboard Performance

Der Fork enthält gezielte Änderungen zur Reduktion von Dashboardlog-/Background-Polling-Last.

Performance wurde über Canary-/Stability-Samples dokumentiert.

## 61. Shared Runtime Compatibility

Commits und Tests decken gemeinsam genutzte Runtime-/Supervisor-Konfigurationen ab.

Damit soll Optimierung nicht versehentlich einzelne Serverprofile funktional brechen.

## 62. Reports: Reporterbenachrichtigung

Ein aktueller Fix begrenzt bestimmte Reportbenachrichtigungen auf den tatsächlichen Reporting Player.

Das verhindert, dass Kontext-/Bestätigungsnachrichten unnötig andere Spieler erreichen.

## 63. Recently Disconnected Target Recovery

Bei Reportauflösung kann ein Ziel kurz zuvor disconnected sein.

Der aktuelle Fork versucht solche Targets aus jüngster Session-/Kontexthistorie zu rekonstruieren, statt den Report sofort kontextlos zu machen.

## 64. Frontline VIP Verification

Der Source enthält `frontline_vip_verification`-Integration im Hookpfad.

Damit kann CRCON mit dem Frontline-VIP-/Identity-Ökosystem zusammenarbeiten, ohne die Seeding-Suite-Domain vollständig zu übernehmen.

## 65. VoteMap Ownership

VoteMap und Mapwahl bleiben in CRCON.

HLL Telemetry kann Layouts analysieren, soll aber nicht VoteMap umgehen.

Diese Grenze ist für die Zusammenarbeit mit `hll-telemetry` und `seeding-suite` wichtig.

## 66. Django API Keys / Permissions

CRCONs API ist an Nutzer-/Permissionmodelle gebunden.

Integrationen sollen dedizierte API-Keys beziehungsweise Serviceaccounts mit minimal erforderlichen Permissions verwenden.

## 67. Mobile API Permission Awareness

Player Search, Dossiers und Incidentactions berücksichtigen aktive CRCON-Permissions.

Fehlende Rechte führen dazu, dass Abschnitte fehlen oder gesperrt sind, nicht dass die Mobile API großzügigere Rechte erfindet.

## 68. Production Deployment

`docs/production-deploy.md` beschreibt einen guarded GitHub-Deploymentweg.

Produktiv soll aus einem sauberen Checkout des privaten Frontline-Repositories deployt werden.

Tracked Files sollen nicht direkt auf dem Server editiert werden.

## 69. Deploy Key

Die Doku empfiehlt einen dedizierten read-only Deploy Key für die Produktionsmaschine.

Der Server benötigt damit keine allgemeinen Org-Schreibrechte.

## 70. Preflight-Deploy-Gates

Der Deployhelper verweigert unter anderem:

- dirty checkout
- falschen Branch
- non-fast-forward Update
- ungültiges Compose-Modell

## 71. Pre-Deploy DB Backup

Vor dem Rollout wird ein PostgreSQL Custom-Format-Backup erzeugt.

Damit existiert eine Recoverybasis, falls eine Migration oder Releaseänderung Daten beschädigt.

## 72. Commit-addressed Images

Der Deployprozess baut Images mit Commitbezug und taggt vorhandene Images für Rollback.

Dadurch ist später nachvollziehbar, welcher Source-Commit tatsächlich im Container lief.

## 73. Migration State

Nach dem Start wird der Migrationszustand ausgegeben beziehungsweise geprüft.

Ein gesunder Container mit falschem DB-Schema ist kein erfolgreicher Rollout.

## 74. Rollback

Die Doku rät ausdrücklich davon ab, DB-Migrationen automatisch herunterzustufen.

Vorgehen:

1. vorheriges App/Image wiederherstellen;
2. DB nur dann zurücksetzen, wenn Daten inkompatibel verändert wurden;
3. Restore vorher separat prüfen.

## 75. Release-Version im Produktionsimage

Ein aktueller Fix sorgt dafür, dass die Releaseversion tatsächlich in Production Images exponiert wird.

Damit kann Runtime-/UI-Version mit Buildzustand abgeglichen werden.

## 76. Datenbankmigrationen

Frontline-Erweiterungen verwenden Alembic für Schemaänderungen.

Neue Features wie Incidents, AI-Analyse und Campaign Delivery werden über additive beziehungsweise kontrollierte Migrationen eingeführt.

## 77. Django-/Alembic-Koordination

Die Mobile-Doku verlangt, sowohl Django- als auch Alembic-Migrationen im normalen Wartungsstart auszuführen.

Damit dürfen die beiden Schemaverantwortlichkeiten nicht gegeneinander vergessen werden.

## 78. Tests

Das Repository besitzt eine umfangreiche Testbasis für:

- RCON-Core
- API
- Incidents
- Mobile Admin
- HLLV
- Campaign Delivery
- Permissions
- Migrations
- Performance-/Compatibilityänderungen

Aktuelle Commits ergänzen gezielt Regressionen für Incident Subjects und HLLV Spectator Refresh.

## 79. Failure Modes

### RCON offline

Web/API kann teilweise verfügbar sein, Live-/Writeaktionen aber nicht.

### Incident Context mehrdeutig

Nicht automatisch fuzzy Ziel bestätigen.

### Discord Service offline

Incident bleibt in CRCON; Delivery State retryt beziehungsweise zeigt Fehler.

### AI Provider offline

Incident-/Moderationsworkflow darf nicht komplett verschwinden. Analyzer kann `unavailable_reason` liefern.

### Mobile Push offline

Admin kann weiterhin über Web/API arbeiten; Push ist Zusatzkanal.

### Campaign Worker crash

Persistente Deliveryrows und stale-sending-Recovery ermöglichen Wiederaufnahme.

### HLLV Reconnect Refresh fehlschlägt

CONNECT-Logverarbeitung darf nicht abbrechen.

## 80. Security Summary

- Upstream CRCON Permissionmodell bleibt maßgeblich
- Mobile Tokens rotieren und sind revokierbar
- Pushpayload minimal
- Discord Service separat
- Capabilities gehasht/verschlüsselt
- Callbackziele eingeschränkt
- Discord Interactions verifiziert
- AI Input untrusted
- Structured Output
- AI ohne direkte Admin-Tools
- idempotente Mobile-/Campaignwrites
- guarded Production Deploy
- read-only Deploy Key

## 81. Ownership gegenüber Frontline-Systemen

| Bereich | Owner |
| --- | --- |
| HLL RCON/Admin/Moderation | `frontline-rcon-suite` |
| Reports/Incidents | `frontline-rcon-suite` |
| Mobile Admin | `frontline-rcon-suite` |
| CRCON Campaign Delivery | `frontline-rcon-suite` |
| HLL Movement/Layouts | `hll-telemetry` |
| HLL VIP/Seeding/Switch | `seeding-suite` |
| globale Server-/Sessiondaten | `frontline-game-tracker` |
| Discord Community | `frontline-level` |
| Host/Gateway | `frontline-gamehost` |

## 82. Weiterführende Dokumentation

- `docs/mobile-admin.md`
- `docs/production-deploy.md`
- `LICENSE`
- `rcon/`
- `rconweb/`
- `alembic/`
- `discord_service/`
- `push_relay/`
- `scripts/`
- `tests/`

## 83. Dokumentationsregel

Die Root-README dokumentiert den Frontline-Fork als Gesamtplattform. Upstream-Anleitungen, einzelne API-Endpunkte und Release-Details können in Spezialdokumenten bleiben. Neue Moderationsmodelle, Mobile-Auth-Änderungen, HLLV-Workarounds, Campaign-Zustände oder neue externe Dienste müssen hier als Architekturänderung aufgenommen werden.

## Ergänzter Quellstand: Releases und Operator-Verträge

Dokumentationsabgleich vom **20. September 2026** gegen `master`-Commit
`9621633eda3b178911b827230dd57fd6a6656f22`.
Die bisherigen Abschnitte bleiben vollständig erhalten. Sie sind eine
Architekturübersicht und kein Nachweis für den heute aktiven Stand einzelner
Produktionsserver.

### Tatsächliche Web-Verzeichnisse

Die Weboberflächen liegen im aktuellen Dateibaum unter
[`rcongui/`](rcongui/) und [`rcongui_public/`](rcongui_public/), nicht unter dem
oben historisch genannten `frontend/`. Der optionale Mobile-Client liegt unter
[`mobile_app/`](mobile_app/). Python-Abhängigkeiten besitzen eigene Lockdateien;
das Verfahren ist in [dependency-locking.md](docs/dependency-locking.md)
beschrieben. Komponenten müssen mit ihren eigenen Build-/Testverträgen
bearbeitet werden, nicht über einen erfundenen gemeinsamen Root-npm-Befehl.

### Führungsabstimmung, Seeding und Autobalancer

Die [Releasebeschreibung v0.8.5](docs/releases/v0.8.5.md) ergänzt die bestehende
Incident-/Moderationsarchitektur um teaminterne Führungsabstimmungen über den
`!admin`-Pfad und `!yes`/`!no`. Der Ablauf besitzt Probelauf und gesonderten
Aktivmodus; unkonfigurierte Server bleiben deaktiviert. Unklare Ziele bleiben
normale Admin-Meldungen. Eine KI- oder Spracherkennung ist dafür keine
Voraussetzung und wird nicht als RCON-Nachweis behauptet.

Dasselbe Release dokumentiert korrigierte Seeding-Seitenzuordnung,
Beitritts-/Nullpositionsschutz und verlässlichere freiwillige Balance-Einladungen.
Unsichere Daten berechtigen weiterhin nicht zum Teamwechsel. Vorhandene
Konfigurationen werden nicht durch den Releasehinweis automatisch aktiviert.
Gegenüber v0.8.4 gehören die Alembic-Migration `e3a8b1c5d209` und Django `0038`
zum beschriebenen Schemaumfang; daraus folgt kein Auftrag, sie auszuführen.

### Englische Operator-Oberfläche

[v0.8.6](docs/releases/v0.8.6.md) schließt Lücken in der englischen Admin- und
öffentlichen Stats-Oberfläche: unter anderem Balance-Prüfung, Live-Kartenhinweise,
Einstellungen, Discord-Anbindung, Datums-/Zahlenformatierung und Sprachwechsel.
Bekannte Systemtexte werden an der Darstellungsgrenze übersetzt, während
Spielernamen, Chat, individuelle Nachrichten, Fallnotizen und unbekannte
technische Details unverändert bleiben. Moderationsregeln und gespeicherte
Servereinstellungen werden dadurch nicht geändert; gegenüber v0.8.5 ist keine
zusätzliche Datenbankmigration beschrieben.

Der Release-Commit enthält `npm run check:i18n` im Admin-UI-Paket sowie
Struktur- und Browserregressionen. Diese Prüfungen wurden bei diesem
Dokumentationsreview nicht ausgeführt. Historische Testzahlen sind keine neue
Vollständigkeits- oder Produktionsabnahme.

### Themenbezogener Dokumentationseinstieg

| Thema | Vorhandene Detaildokumentation |
| --- | --- |
| Führungsabstimmungen und Diagnose | [leadership-votes.md](docs/leadership-votes.md), [Troubleshooting](docs/leadership-vote-troubleshooting.md) |
| Freiwillige Balance-Wechsel | [autobalancer-volunteer-reliability.md](docs/autobalancer-volunteer-reliability.md) |
| Seeding-Geofences | [seeding-geofence-map-sides.md](docs/seeding-geofence-map-sides.md) |
| Lokalisierung | [frontline-localization.md](docs/frontline-localization.md) |
| Vorbereitete Adminaktionen | [prepared-admin-action-contract.md](docs/prepared-admin-action-contract.md) |
| Einstellungswirkung und Vorschau | [general-setting-effect-contract.md](docs/general-setting-effect-contract.md), [auto-settings-preview-contract.md](docs/auto-settings-preview-contract.md) |
| Integrationsfähigkeiten und Spielprofile | [integration-capabilities-v1.md](docs/integration-capabilities-v1.md), [game-profile-status-contract.md](docs/game-profile-status-contract.md) |
| Live-Karte und Spielerschutz | [live-map-player-protection.md](docs/live-map-player-protection.md) |
| Login-/Proxy-Grenzen | [login-trust-contract.md](docs/login-trust-contract.md), [proxy-security-baseline.md](docs/proxy-security-baseline.md) |
| Stilllegung und Releasehistorie | [retiring-a-server.md](docs/retiring-a-server.md), [releases/](docs/releases/) |

Dieser Index macht vorhandene Verträge auffindbar, ersetzt aber nicht deren
konkrete Freigabe- und Sicherheitsbedingungen. Es wurden keine GitHub Actions,
Tests, Migrationen, Builds, Spieleraktionen oder Deployments gestartet und
keine lokale Homelab-Arbeitskopie verändert. Nachverfolgung:
[frontline-github-ops#3](https://github.com/Frontline-Network/frontline-github-ops/issues/3).
