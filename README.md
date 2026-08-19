# Frontline RCON Suite

Die Frontline RCON Suite ist der stark erweiterte Frontline-Fork von **Hell Let Loose Community RCON (CRCON / hll_rcon_tool)**. Die ursprüngliche CRCON-Basis bleibt erhalten, wurde aber um zahlreiche Frontline-spezifische Funktionen für Hell Let Loose und Hell Let Loose: Vietnam erweitert.

Das Repository ist inzwischen deutlich mehr als ein klassisches RCON-Webpanel. Es umfasst unter anderem:

- Multi-Server-RCON und Serveradministration
- HLL- und HLL-Vietnam-Unterstützung
- Player-/Session-/Admin-Daten
- Reports und Incident-Workflows
- Mobile-Admin-Anbindung
- Discord-Report-/Incident-Integration
- verwaltete AI-Moderationsanalyse
- Broadcast- und Player-Message-Kampagnen
- VoteMap und HLL-spezifische Automationen
- VIP-/Admin-/Spectator-Workarounds
- Produktions-Deployment, Migrationen, Backups und Rollback

Diese README ersetzt bewusst die bisherige fast unveränderte Upstream-README als Einstieg in den **Frontline-Fork**. Upstream-Provenienz und Lizenz bleiben dabei ausdrücklich erhalten.

Diese README ist zweigeteilt:

- **Teil 1 – Für Menschen:** Was die Suite für Spieler, Moderation und Serverbetrieb macht – ohne Endpointlisten, Ports oder Frameworkdetails.
- **Teil 2 – Technische Dokumentation:** Architektur, Datenmodell, Worker, Incidents, Mobile Admin, Discord-Service, AI-Moderation, HLLV-Besonderheiten, Campaign Delivery, Deployment, Migrationen und Sicherheitsgrenzen.

---

# Teil 1 – Was macht die Frontline RCON Suite?

## Serververwaltung für Hell Let Loose

Die Suite stellt die zentrale RCON-basierte Verwaltungsoberfläche für Hell-Let-Loose-Server bereit.

Administratoren können damit – abhängig von Rolle und Serverprofil – typische Aufgaben erledigen wie:

- Serverstatus prüfen
- Spieler sehen
- Admin-/VIP-Listen verwalten
- Spieler moderieren
- Karten und Rotation verwalten
- VoteMap verwenden
- Chat-/Serverereignisse auswerten
- Statistiken und historische Informationen ansehen

Die Frontline-Erweiterungen bauen auf dieser bestehenden CRCON-Basis auf.

## Hell Let Loose und Hell Let Loose: Vietnam

Der Fork unterstützt nicht nur klassisches Hell Let Loose, sondern enthält inzwischen auch HLL-Vietnam-spezifische Anpassungen.

Dabei wird nicht vorausgesetzt, dass beide Spiele technisch identisch reagieren. Wo sich Identitäten, Adminlisten oder Serververhalten unterscheiden, existieren explizite Kompatibilitäts- und Sicherheitslogiken.

Ein Beispiel ist die HLLV-Spectator-Berechtigung: Der Gameserver kann nach einem Reconnect eine weiterhin vorhandene Adminzuordnung nicht korrekt aktivieren. Der Frontline-Fork prüft deshalb bei einem passenden HLLV-Reconnect erneut die aktuelle Adminliste und kann eine bestätigte Spectator-Zuordnung additiv neu anwenden.

## Spielerreports und Incidents

Spieler können Moderationsprobleme melden. Aus solchen Reports entstehen strukturierte Incidents.

Ein Incident kann Kontext enthalten wie:

- meldender Spieler
- betroffener Spieler
- mehrere mögliche Spieler-/Squadbezüge
- Reportgrund
- Serverkontext
- aktuelle und historische Zustände
- Adminnotizen
- Status und Bearbeiter

Mehrdeutige Namenszuordnungen werden nicht automatisch als sichere Zielidentität behandelt.

## Mobile Admin

Die Suite besitzt eine optionale Mobile-Admin-Integration.

Ein Administrator koppelt sein eigenes Gerät mit seinem eigenen CRCON-Konto. Es gibt keinen gemeinsamen universellen QR-Code für alle Admins.

Die Mobile-App kann – abhängig von den CRCON-Berechtigungen des jeweiligen Administrators – unter anderem:

- Incident-Inbox anzeigen
- Incidents claimen und bearbeiten
- Kontext und Dossiers ansehen
- Spieler-/Squadbezüge prüfen
- Notizen hinzufügen
- erlaubte Moderationsaktionen ausführen

Fehlende CRCON-Rechte werden nicht durch die Mobile-App erweitert.

## Sichere Geräte-Paarung

Die Kopplung ist kurzlebig und muss im bereits authentifizierten CRCON-Webinterface bestätigt werden.

Der Administrator vergleicht einen Code auf beiden Geräten und bestätigt die Kopplung bewusst.

Mobile-Token sind kurzlebig beziehungsweise rotierend und können entzogen werden.

## Discord-Integration

Der Frontline-Fork kann Incidents und Moderationsereignisse an einen getrennten Frontline-Discord-Service übergeben.

Dadurch müssen einzelne CRCON-Installationen nicht jeweils ihren eigenen Discord-Bot-Token verwalten.

Der zentrale Dienst kann Reports in Discord darstellen und kontrollierte Rückaktionen an die gebundene CRCON-Instanz vermitteln.

## Verwaltete AI-Moderation

Die Suite enthält zusätzlich eine optional aktivierbare Moderationsanalyse.

Dabei können beispielsweise Chattexte oder Spielernamen als Moderationskandidaten analysiert werden.

Wichtig: Die AI trifft nicht automatisch die Moderationsentscheidung und behauptet nicht, eine Aktion ausgeführt zu haben.

Die Architektur behandelt den analysierten Text ausdrücklich als **untrusted input**. Darin enthaltene Anweisungen oder Prompt-Injection-Versuche sollen nicht befolgt werden.

Die Analyse liefert strukturierte Empfehlungen beziehungsweise Einordnungen für Review-Workflows.

## Schutz vor Incident-Fluten

Reports und automatisierte Moderationskandidaten können schnell sehr viele Ereignisse erzeugen.

Der Fork enthält deshalb Deduplizierung, Delivery-State und Retrylogik, damit wiederholte oder identische Ereignisse nicht unkontrolliert Discord oder Adminoberflächen fluten.

## Broadcasts und Player-Kampagnen

Neben klassischen Serverbroadcasts unterstützt der Fork auch gezielte Player-Message-Kampagnen.

Eine Kampagne kann Regeln besitzen wie:

- erst nach bestimmter Sessiondauer
- nur VIP oder Nicht-VIP
- nur in bestimmten Serverzuständen
- Mindestabstand zwischen Nachrichten
- globaler Versandabstand

Die Zustellung wird persistent pro Spielersession erfasst. Dadurch kann ein Prozessneustart nicht einfach vergessen, wem eine Kampagnennachricht bereits zugestellt wurde.

## VoteMap und Layoutgrenzen

CRCON bleibt der Eigentümer von VoteMap und Kartenwahl.

Andere Frontline-Dienste wie HLL Telemetry beobachten und analysieren Layouts, sollen aber nicht heimlich CRCONs Mapsteuerung ersetzen.

Diese Ownership-Grenze ist wichtig, weil mehrere Systeme dieselbe HLL-Runde beobachten, aber nicht alle davon Control-Rechte besitzen sollen.

## Performance und Skalierung

Der Fork wurde in mehreren Bereichen auf dauerhaften Multi-Server-Betrieb optimiert.

Dazu gehören unter anderem:

- Worker-/Supervisor-Konsolidierung
- begrenzte Log-/Payloadgrößen
- Runtime-Retention
- kontrollierte Datenbankverbindungen
- Hintergrundjobs
- Health-/Readiness-Prüfungen
- dedizierte Delivery-Tabellen für neue Automationen

Die Root-README beschreibt diese Prinzipien; konkrete Messwerte und einzelne Canary-Ergebnisse bleiben in Commits und Detaildokumentation.

---

# Teil 2 – Technische Dokumentation

## 1. Upstream und Lizenz

Die Frontline RCON Suite basiert auf dem Open-Source-Projekt **Hell Let Loose Community RCON / hll_rcon_tool** von Julien Marechal und weiteren Contributors.

Die vorhandene `LICENSE` ist eine MIT-Lizenz mit Copyright-Hinweis auf Julien Marechal (2020).

Diese Upstream-Provenienz muss erhalten bleiben.

Der Frontline-Fork ergänzt die bestehende CRCON-Architektur, ersetzt aber nicht die Lizenz- und Attribution-Pflichten der Upstream-Basis.

## 2. Repository-Grundstruktur

Der Python-Code ist laut `pyproject.toml` insbesondere in folgenden Bereichen organisiert:

```text
rcon/        RCON-, Domain-, Worker- und Serverlogik
rconweb/     Django-Webanwendung / Adminoberfläche
server/      Server-/Runtime-bezogene Komponenten
tests/       Regressionen
```

Zusätzlich existieren unter anderem:

```text
alembic/ bzw. Migrationen
mobile_app/              Flutter Mobile Admin
push_relay/              selbst hostbarer Push Relay
callback_service/        Callback-/Integrationskomponente
discord_service/         zentrale Discord-/Moderationsintegration
docs/                    Frontline-spezifische Betriebsdokumentation
scripts/                 Deployment-, Test- und Betriebshelfer
Dockerfile
Frontend-/Builddateien
Compose-Definitionen
```

## 3. Technologie

Die Upstream-/Fork-Architektur kombiniert mehrere Technologien:

- Python 3
- Django für Web-/Adminlogik
- SQLAlchemy/Alembic für Teile des Datenmodells und Migrationen
- PostgreSQL
- RCON-/Gameserverkommunikation
- Supervisor-/Workerprozesse
- Frontend/Weboberfläche
- optional Flutter für Mobile Admin
- separater Python-Webservice für Discord-/AI-Integration

`pyproject.toml` konfiguriert unter anderem Black und isort mit Python-3.11-Ziel.

## 4. CRCON bleibt Source of Truth für Serveradministration

Mobile Admin, Discord-Service und andere Frontline-Komponenten dürfen CRCON-Berechtigungen nicht umgehen.

CRCON bleibt maßgeblich für:

- Nutzer
- Rollen
- Permissions
- Serverprofile
- Playerdaten
- Admin-/VIP-Daten
- eigentliche RCON-/Moderationsaktionen

Externe Oberflächen erhalten nur die Fähigkeiten, die der zugrunde liegende CRCON-Nutzer tatsächlich besitzt.

## 5. Multi-Server-Modell

CRCON wird pro konfigurierter Serverinstanz beziehungsweise Servernummer betrieben.

Viele Frontline-Erweiterungen speichern `server_number`, damit Ereignisse, Incidents, Kampagnen und Aktionen eindeutig der richtigen Serverinstanz zugeordnet bleiben.

Serverübergreifende Oberflächen müssen diese Trennung respektieren.

## 6. Datenbank und Migrationen

Der Fork verwendet Datenbankmigrationen für neue Features.

Neue Frontline-Funktionen wie Mobile Incidents, AI-Moderationsanalyse und Kampagnenzustellung besitzen eigene Tabellen beziehungsweise Migrationen.

Produktionsdeployments müssen sowohl die bestehende Django-Migrationshistorie als auch die Alembic-Migrationskette berücksichtigen.

Migrationen werden nicht als beiläufige Dateikopie behandelt.

## 7. Player Sessions

CRCON führt Spielersessions und Playeridentitäten, die auch von Frontline-Erweiterungen verwendet werden können.

Player-Message-Kampagnen referenzieren beispielsweise konkrete `player_session`-Datensätze, damit Zustellung an eine reale aktuelle Session gebunden ist.

Eine neue Session ist damit ein neuer möglicher Kampagnenkontext; die alte Zustellung wird nicht einfach global auf unbestimmte Zeit mitgeschleppt.

## 8. Campaign Delivery

Die jüngste Frontline-Erweiterung führt persistente Campaign-Delivery-Daten ein.

Eine Delivery speichert unter anderem:

- Server
- Campaign-ID
- Player-ID
- konkrete Player-Session
- Spielername
- Nachricht
- Status
- Attempt Count
- Eligible-Zeitpunkt
- Next Attempt
- letzte Ausführung
- Versandzeit
- letzten Fehler

Eine Unique Constraint auf Server + Campaign + Player Session verhindert doppelte Zustellung derselben Kampagne innerhalb derselben Session.

## 9. Campaign Delivery States

Der Code unterscheidet Zustände wie:

```text
queued
sending
sent
failed
expired
```

Zusätzlich existieren:

- Retrydelays
- maximales Attempt-Limit
- Recovery für stale `sending`-Zustände
- Retention älterer Deliverydaten

Damit ist die Kampagnenzustellung restart- und retryfähig.

## 10. Campaign Targeting

Player-Kampagnen können nach dokumentiertem Code unter anderem filtern nach:

- VIP
- Nicht-VIP
- alle
- Mindestdauer der aktuellen Session
- Kampagnenintervall
- Player-spezifischem Mindestabstand
- Server-/Seedingzustand

Die tatsächliche Eligibility wird unmittelbar aus aktuellem Spieler-/Sessionzustand berechnet.

## 11. Broadcast vs. Player Message

Der bisherige Auto-Broadcast-Mechanismus und neue Player-Messages werden getrennt behandelt.

Broadcast-Kampagnen gehen über den klassischen Serverbroadcast-Weg.

`player_message`-Kampagnen erzeugen dagegen persistente individuelle Delivery-Einträge.

Diese Trennung verhindert, dass ein individueller Delivery-Workflow die bestehende Broadcastschleife unkontrolliert verändert.

## 12. Incidents

Die Incident-Architektur kann unterschiedliche Quellen unterscheiden, darunter:

- Chatreport
- manuell erzeugt
- AI-basierter Chatkandidat
- AI-basierter Spielernamenkandidat

Incidents besitzen Eventhistorie und können mehrere Subjekte beziehungsweise Kontextkandidaten enthalten.

## 13. Incident Context

Der Mobile-/Incident-Resolver unterstützt mehrere Kontextmodi.

Sinngemäß:

```text
disabled
  alte/einfache Resolverlogik

shadow
  Kandidaten werden gespeichert, aber nicht automatisch bestätigt

enabled
  nur eindeutige exakte Matches können automatisch bestätigt werden
```

Fuzzy Matches bleiben Vorschläge und dürfen nicht als Action Target verwendet werden, bis ein Administrator sie bestätigt.

## 14. Multi-Subject Incidents

Ein Incident kann mehrere Spieler- und Squadsubjekte enthalten.

Squad-Mitglieder müssen einzeln ausgewählt werden.

Es existieren keine impliziten Squad-weiten Actions und ein Squadleader wird nicht automatisch als Stellvertreter für den gesamten Squad als Ziel gewählt.

Das reduziert das Risiko, dass ein mehrdeutiger Report zu einer Aktion gegen die falsche Person führt.

## 15. Immutable Snapshots vs. Live State

Incidents behalten immutable Reporter-/Subject-Snapshots aus dem Zeitpunkt des Ereignisses.

Die Oberfläche kann parallel den aktuellen Serverzustand anzeigen.

Damit wird unterschieden zwischen:

```text
Was wurde zum Reportzeitpunkt gemeldet?

und

Wie sieht der Spieler/Server jetzt aus?
```

Aktuelle Änderungen überschreiben nicht die historische Incident-Evidenz.

## 16. Incident Deduplizierung

Identische Reports desselben Spielers und Servers können für ein kurzes Fenster dedupliziert werden.

Zusätzliche Discord-Delivery- und Candidate-Outbox-Tabellen verhindern, dass Events bei Retries mehrfach zugestellt werden.

## 17. Discord Incident Delivery

CRCON besitzt eine Delivery-Tabelle für Discord-Reportevents.

Sie speichert unter anderem:

- Eventbezug
- Attempts
- Next Attempt
- Delivered-Zeitpunkt
- Fehler

Damit wird die Zustellung asynchron und retrybar, ohne den RCON-/Logprozess direkt von Discord abhängig zu machen.

## 18. Zentraler Discord Service

Der Frontline-Fork enthält einen separaten `discord_service`.

Seine Aufgabe ist zentrale Discord-Zustellung und verwaltete Moderationsanalyse für gebundene CRCON-Installationen.

Das ermöglicht ein Modell, in dem Kunden-/Serverinstanzen nicht jeweils eigene Bot- und AI-Credentials verwalten müssen.

## 19. Discord-Service-Datensparsamkeit

Die dokumentierte Servicearchitektur speichert technische Bindungs- und Capabilitydaten, aber soll keine dauerhafte Datenbankspalte für eigentliche Report-/Chat-/Namens-Texte, Action-Gründe oder Previewtexte besitzen.

Persistiert werden stattdessen unter anderem:

- Integrationsbindungen
- Capability-Material
- Incident-/Message-Mappings
- kurzlebige Bestätigungsrelays
- Idempotenzreceipts
- content-free Usage Metrics

Dadurch wird die zentrale Infrastruktur nicht automatisch zur dauerhaften Kopie aller Moderationstexte.

## 20. Discord-Service-Pairing

Die Servicebindung erzeugt getrennte zufällige Capabilities für:

```text
CRCON -> Service Events
Service -> CRCON Actions
```

Der Empfänger speichert nur einen keyed Digest; der Sender hält den Raw-Wert verschlüsselt.

Capabilities sollen nicht in URLs oder Logs landen.

Callback-Ziele werden eingeschränkt; private/link-local Ziele und unzulässige Pfade werden abgewiesen.

## 21. AI Moderation Candidate Outbox

CRCON kann potenzielle Chat-/Namensfälle in eine eigene Moderation-Outbox schreiben.

Ein Candidate enthält unter anderem:

- Quelle
- Server
- Playerbezug
- Candidate-Fingerprint
- Text
- gematchte Policy-Regeln
- Policy
- Shadow-Flag
- Retry-/Deliveryzustand

Analyseergebnis und Incident-Erzeugung werden davon getrennt verarbeitet.

## 22. AI-Analyse

Der zentrale Analyzer verwendet einen fest definierten Systemprompt und ein strukturiertes Output-Schema.

Wichtige Sicherheitsregeln im Code:

- Inputtext wird als untrusted evidence behandelt.
- Anweisungen im Text werden nicht befolgt.
- das Modell hat keine Tools in diesem Analysepfad.
- Ausgabe muss dem erwarteten Schema entsprechen.
- Action wird nur empfohlen, nicht als ausgeführt behauptet.
- Rule IDs müssen aus der mitgegebenen Policy stammen.

## 23. Separate Moderation Gate

Vor beziehungsweise neben generativer Analyse wird eine Moderationprüfung verwendet.

Ein `hard_hit`-Signal wird aus diesem separaten Moderationsgate übernommen und **nicht** vom untrusted Text oder generativen Modell selbst gesetzt.

Dadurch kann der analysierte Text nicht einfach behaupten „ich bin ein Hard Hit“ und diese interne Sicherheitsflagge manipulieren.

## 24. AI Privacy / Store-Verhalten

Der Analyzer verwendet den Responses-Aufruf mit deaktivierter Speicherung (`store=False`).

Die lokale Servicearchitektur speichert Analysemetadaten und strukturierte Ergebnisse entsprechend ihrem eigenen Datenmodell; der externe Modellrequest soll nicht als allgemeiner Konversationsspeicher verwendet werden.

## 25. AI Visibility

Analyseergebnisse unterscheiden Sichtbarkeits-/Verarbeitungszustände wie:

```text
incident
shadow
ignore
```

Damit kann Moderationslogik zunächst im Shadow-Modus evaluiert werden, ohne jeden Treffer als echten Incident zu behandeln.

## 26. Mobile Admin Pairing

Mobile Admin ist opt-in und standardmäßig deaktiviert.

Der Pairingflow:

1. Administrator ist bereits in CRCON authentifiziert.
2. CRCON erzeugt kurzlebigen One-Time-QR.
3. Mobile Gerät liest Pairingdaten.
4. sechsstelliger Code wird auf beiden Seiten verglichen.
5. Admin bestätigt im Browser.
6. Gerät erhält eigene Credentials.

Shared Pairing-Codes für mehrere Admins sind nicht vorgesehen.

## 27. Mobile Token Lifecycle

`docs/mobile-admin.md` dokumentiert:

- opaque Access Tokens
- gehashte Speicherung in CRCON
- kurze Access-Token-Laufzeit
- rotierende Refresh Tokens
- Idle- und absolute Refresh-Lifetime
- Revocation bei Geräteentzug
- unmittelbare Berücksichtigung von User-Deaktivierung/Permissionänderungen beim nächsten Request

## 28. Mobile Secret Storage

Mobile Secrets werden im OS-Secure-Storage gehalten.

Der lokale verschlüsselte Cache verwendet einen getrennten Schlüssel aus dem OS-KeyStore.

Damit soll ein Appdaten-Backup nicht automatisch alle Authentifizierungssecrets im Klartext enthalten.

## 29. Mobile Actions

Schreibende Mobile-Aktionen werden nicht offline gequeued oder blind retried.

Kick und temporärer Ban verlangen Reason und explizite Bestätigung.

Ein Beta-E2E-Runner ist standardmäßig safe und führt keine Playeraktion aus, solange kein expliziter Action-Gate und ein bestätigtes Ziel angegeben wurden.

## 30. Push Relay

Push ist eine optionale getrennte Komponente.

Pushpayloads sind bewusst minimal und enthalten keine normalen Playernamen, IDs, Reportgründe oder Adminnotizen.

Der Worker prüft aktive CRCON-Permissions bei Delivery.

Device Registration ist rate-limited und besitzt eine konfigurierbare Obergrenze.

## 31. HLL Vietnam Identity

HLL Vietnam kann EOS-basierte Identitäten verwenden, die sich von klassischen 17-stelligen SteamIDs unterscheiden.

Der HLLV-Spectator-Refresh prüft ausdrücklich auf den erwarteten EOS-Identifier-Typ und verweigert die Aktion bei einem klassischen SteamID-Format.

Damit wird verhindert, dass HLL- und HLLV-Identitäten unkontrolliert vermischt werden.

## 32. HLLV Spectator Reconnect Workaround

Der Workaround ist bewusst additiv:

1. nur HLL Vietnam
2. nur definierte Rolle(n), aktuell Spectator
3. bestehende Adminzuordnung muss zunächst vorhanden sein
4. Cache wird verworfen
5. frische Live-Adminliste wird erneut gelesen
6. nur wenn Rolle weiterhin existiert, wird `AddAdmin` erneut gesendet
7. es wird nie automatisch eine Rolle entfernt

Damit kann eine in CRCON oder auf dem Gameserver bewusst entfernte Rolle nicht aus einem alten Cache wiederauferstehen.

## 33. Supervisor-/Worker-Modell

CRCON verwendet mehrere Hintergrundprozesse für dauerhafte Aufgaben.

Frontline-Erweiterungen fügen eigene Worker hinzu, beispielsweise:

- Campaign Messages
- Discord Report Delivery
- Mobile Push
- bestehende CRCON-Log-/Automation-Worker

Mehrere Performance-Commits haben gemeinsame Runtime-/Supervisorlogik konsolidiert und unnötige Parallelität reduziert.

## 34. Datenbankverbindungen in Workern

Einige dauerhafte Worker laufen explizit mit deaktiviertem DB-Connection-Pool.

Das reduziert bei vielen Supervisorprozessen die Anzahl langlebiger paralleler Datenbankverbindungen.

Diese Optimierung darf nicht pauschal auf jeden Prozess übertragen werden, ohne dessen Zugriffsmuster zu prüfen.

## 35. Runtime Retention

Der Fork enthält begrenzte Aufbewahrung für bestimmte Runtime-Daten.

Ziel ist, dass Log-/Event-/Delivery-/Zwischenzustände bei dauerhaftem Betrieb nicht unbegrenzt wachsen.

Fachlich benötigte historische Daten und kurzfristige Operational-State-Daten müssen dabei getrennt behandelt werden.

## 36. Backend Readiness

Der Produktionspfad prüft nicht nur, ob ein Container existiert.

Neuere Änderungen härten Backend-Health gegen den tatsächlich laufenden Prozess und Proxy-/Service-Discovery-Zustand.

Damit soll ein Supervisor-/Proxy-Container nicht „gesund“ erscheinen, wenn der eigentliche Backendprozess nicht funktionsfähig ist.

## 37. Produktions-Deployment

`docs/production-deploy.md` definiert einen guarded Deploymentflow.

Wesentliche Regeln:

- Produktion läuft aus einem sauberen Checkout.
- Tracked Files werden nicht direkt auf dem Server editiert.
- Runtimekonfiguration bleibt in ignorierten `.env`-/generated Dateien.
- Deploy verweigert dirty checkout.
- erwarteter Branch muss aktiv sein.
- kein nicht-fast-forward Update.
- Composemodell wird vor Start validiert.
- vor Rollout wird ein PostgreSQL-Backup erzeugt.
- laufende Images werden für Rollback getaggt.
- neue Images sind commitadressiert.
- Healthchecks werden nach Start abgewartet.
- Migrationszustand wird ausgegeben.

## 38. Produktions-Remote-Historie

Die vorhandene Deploymentdokumentation enthält noch einen älteren Repositorynamen (`hll_rcon_tool-mobile-admin`) für den privaten Deploy-Key-/Remote-Setup.

Der aktuelle Repositoryname ist `Frontline-Network/frontline-rcon-suite`.

Dieser Migrationsrest sollte bei einer späteren Detaildoku-Bereinigung korrigiert werden; die Root-README verwendet deshalb den aktuellen Namen.

## 39. Rollback

Ein normaler Applikationsrollback soll nicht automatisch Datenbankmigrationen downgraden.

Der dokumentierte Ansatz:

- vorherigen Commit / Rollback-Images verwenden
- DB-Backup nur dann zurückspielen, wenn tatsächlich inkompatible Datenänderungen vorliegen
- Restore zuerst separat verifizieren

Das schützt aktuelle Betriebsdaten vor unnötigem Datenbankrollback.

## 40. Tests

Der Fork besitzt Tests für Upstream- und Frontline-Funktionen.

Neue Frontline-Komponenten werden mit Regressionen abgesichert, unter anderem für:

- HLLV Admin/Spectator Refresh
- Incident Context
- Mobile Admin
- Campaign Delivery
- Runtime-/Supervisorverhalten
- Discord-/Moderationsintegration

Schreibende Features müssen insbesondere Idempotenz, Berechtigungsgrenzen und falsche Zielidentitäten testen.

## 41. Failure Modes

### Reportname ist mehrdeutig

Schutz: nur Vorschlag; keine Action bis Admin bestätigt.

### Incident wird mehrfach geliefert

Schutz: persistente Delivery-/Outboxzustände und Deduplizierung.

### Discord ist temporär nicht erreichbar

Schutz: asynchrone Delivery mit Attempt-/Retryzustand.

### AI-Input enthält Prompt Injection

Schutz: Text als untrusted evidence, kein Toolzugriff, strukturiertes Schema.

### AI behauptet selbst einen Hard Hit

Schutz: Hard-Hit-Bit stammt nur aus separatem Moderation Gate.

### HLLV Spectatorrolle wurde bewusst entfernt

Schutz: frische Adminliste vor Reapply; alte Cachezuordnung reicht nicht.

### Kampagnenworker startet neu

Schutz: persistente Deliverytabelle pro Campaign/Session.

### gleiche Kampagne wird innerhalb einer Session doppelt eingequeued

Schutz: Unique Constraint auf Server + Campaign + Player Session.

### fehlende CRCON-Berechtigung im Mobile Client

Schutz: Funktion wird verborgen/gesperrt, Rechte werden nicht erweitert.

### Produktionsdeploy hat dirty files

Schutz: Deploy helper bricht ab.

## 42. Ownership im Frontline-System

- **CRCON / frontline-rcon-suite:** HLL-/HLLV-RCON, Serveradministration, VoteMap, Player-/Admin-/VIP-nahe HLL-Daten, Incidents und RCON-Aktionen.
- **HLL Telemetry:** hochfrequente Positionen, Bewegung, Heatmaps und Layoutanalyse.
- **Seeding Suite:** VIP-Automation, `!switch`, Geofence, Broadcast und separater Layoutcontroller.
- **Game Tracker:** globale/operative Server-/Session-Sicht und Identity-Matching-Projektionen.
- **Player CRM:** kanonische plattformübergreifende Identität.
- **Levelbot:** Discord-Community-UI außerhalb des CRCON-spezifischen Discord-Services.

## 43. Relevante Dokumentation

```text
docs/mobile-admin.md
docs/production-deploy.md
LICENSE
pyproject.toml
rcon/
rconweb/
mobile_app/
push_relay/
discord_service/
scripts/
tests/
```

## 44. Pflege dieser README

Diese README beschreibt den Frontline-Fork. Upstream-Dokumentation kann weiterhin für allgemeine CRCON-Bedienung relevant sein, darf aber nicht mehr die einzige Root-Erklärung darstellen.

Neue Frontline-Funktionen sollen hier nur dann aufgenommen werden, wenn ihr Zweck und ihre Verantwortungsgrenze dauerhaft relevant sind. Einzelne Hotfixes, Canary-Messungen und Releasechroniken gehören in Commits und Spezialdokumentation.
