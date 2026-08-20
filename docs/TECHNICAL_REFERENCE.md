# Frontline RCON Suite – Technische Referenz

Stand: 20. August 2026  
Repository: `Frontline-Network/frontline-rcon-suite`  
Default Branch: `master`

Die Frontline RCON Suite ist ein privater Fork von Hell Let Loose Community RCON. Diese Referenz dokumentiert die Frontline-Erweiterungen und ihre Einbettung in CRCON auf Datei-, Funktions-, Datenmodell-, Default-, Sicherheits- und Datenflussebene. Die MIT-Provenienz des Upstreamprojekts bleibt maßgeblich.

---

## 1. Plattformgrenze

| Domäne | Eigentümer |
| --- | --- |
| RCON-Verbindung, Serverbefehle, Live-Spieler, Logs | CRCON-Core in diesem Repo |
| HLL-/HLLV-Moderation, Bans, VIP/Adminlisten | dieses Repo |
| Reports/Incidents und Mobile Admin | dieses Repo |
| gestaffelte CRCON-Spielerkampagnen | dieses Repo |
| zentraler CRCON-Discord-/AI-Service | `discord_service/` in diesem Repo, separater Deploymentkontext |
| HLL-Tiefentelemetrie/Heatmaps/Routen | `hll-telemetry` |
| Seeding/Switch/Geofence/Monthly VIP | `seeding-suite` |
| spielübergreifender Tracker/CRM | `frontline-game-tracker` |
| Discord-Community | `frontline-level` |
| Docker-/Hostorchestrierung | `frontline-gamehost` |

---

## 2. Hauptverzeichnisse

| Pfad | Aufgabe |
| --- | --- |
| `rcon/` | Controller, Parser, Models, Hooks, Worker, Policies und Frontline-Erweiterungen |
| `rconweb/` | Django-API, Permissions, Mobile API, Web-/Integrationsmodelle |
| `alembic/versions/` | SQLAlchemy/Alembic-Schemaänderungen |
| `rcongui/` beziehungsweise Frontendpfad | Weboberfläche |
| `mobile_app/` | Flutter Mobile Admin |
| `discord_service/` | zentraler FastAPI-/Discord-/AI-Service |
| `push_relay/` | minimales Mobile Push Relay |
| `callback_service/` | Callback-/Integrationskomponente |
| `supervisor/` und Compose-Dateien | getrennte Hintergrundprozesse |
| `scripts/` | E2E, Diagnose, guarded Production Deploy |
| `tests/` | Unit-, API-, Incident-, Mobile-, HLLV- und Campaignregressionen |
| `docs/` | Mobile, Discordbot, Production Deploy und technische Spezialdoku |

`pyproject.toml` richtet Black und isort auf Python 3.11 aus. Einzelne neue Services verwenden eigene `pyproject.toml`-Dateien und Images.

---

## 3. RCON-Core

### 3.1 `rcon/rcon.py`

| Symbol | Logik |
| --- | --- |
| `create_rcon(credentials)` | `GameEnum.HLL_WW2 -> HLLRcon`, `GameEnum.HLL_VIETNAM -> HLLVRcon` |
| `get_rcon(credentials=None)` | lazily initialisiertes Interpreter-Singleton `CTL` |
| `do_run_commands(rcon,commands)` | Konfigänderungen sequenziell anwenden, Userconfig partiell mergen, nach jedem Command 5 Sekunden Pause |
| `is_user_config_func(name)` | Regex `set_.*_config` |
| `Rcon` | gemeinsame High-Level-Funktionen über dem konkreten Servercontroller |
| `HLLRcon` / `HLLVRcon` | spielspezifische Controllerkombinationen |

### 3.2 Basiskonstanten und Parser

- `MAX_SERV_NAME_LEN = 1024`; Kommentar kennzeichnet den Wert selbst als nicht getestet.
- Mapregex `^(\w+_?)+$`.
- feste Logactions für Liveansicht, unter anderem Connect, Disconnect, Chat, Kill, Teamswitch, Admin, Match und Message.
- Klassisches HLL und HLLV werden über `GameEnum` getrennt; Player-ID-Verträge dürfen nicht blind vermischt werden.

### 3.3 Configwrites

`do_run_commands()`:

1. prüft, ob Command eine Userconfig-Setterfunktion ist;
2. lädt bei Userconfig den vorhandenen Stand;
3. merged nur übergebene Felder;
4. setzt `by=AutoSettings`, wenn nicht vorhanden;
5. ruft den konkreten RCON-Command auf;
6. isoliert Attribute-/Commandfehler pro Eintrag;
7. wartet fünf Sekunden vor der nächsten Änderung.

---

## 4. Hooks und HLLV-Reconnect-Fix

### Dateien

- `rcon/hooks.py` registriert Logeventhandler.
- `rcon/hllv_admin_refresh.py` enthält den isolierten HLLV-Workaround.
- `tests/test_hllv_admin_refresh.py` deckt die Sicherheitsfälle ab.

### `refresh_hllv_admin_role_on_connect()`

1. nur `GameEnum.HLL_VIETNAM`.
2. Player-ID muss vorhanden und exakt 32 Zeichen lang sein; 17-stellige Steam-ID wird abgelehnt.
3. nur Rollen in `RECONNECT_REFRESH_ROLES`, aktuell ausschließlich `spectator`.
4. erste Adminliste darf den gecachten Eintrag enthalten.
5. Cache wird, falls möglich, explizit gelöscht.
6. zweite Adminliste muss den Eintrag weiterhin live enthalten.
7. erst dann `add_admin()` mit vorhandener Rolle/Beschreibung.
8. niemals `remove_admin()`.
9. Hook fängt jede Exception ab, damit CONNECTED-Verarbeitung nicht scheitert.

Damit ist die Funktion additiv und schützt vor dem Wiederauferstehen einer zwischenzeitlich direkt am Gameserver entfernten Rolle.

---

## 5. Incident-System

### 5.1 Dateien

| Datei | Funktionen/Modelle |
| --- | --- |
| `rcon/admin_incidents.py` | Parsing, Contextresolver, CRUD, Revisionen, Subjects, Events, Dedupe |
| `rcon/incident_settings.py` | generische/Legacy-Environmentwerte |
| `rcon/models.py` | `AdminIncident`, `AdminIncidentEvent`, `AdminIncidentSubject` und Delivery-/Analysismodelle |
| `rcon/hooks.py` / `rcon/discord_chat.py` | Chat-/Logeingang |
| `rcon/incident_notifications.py` | Discord-Delivery-Outbox anlegen |
| `rconweb/api/mobile_incidents.py` | Mobile Incident API |
| `rconweb/api/mobile_context.py` | aktueller mobiler Kontext |
| `alembic/versions/*incident*` | Schemaentwicklung |

### 5.2 Konstante Werte

| Wert | Default/Grenze |
| --- | --- |
| Status | `new`, `claimed`, `resolved`, `dismissed` |
| Finalstatus | `resolved`, `dismissed` |
| Subject Kind | `player`, `squad` |
| Subject State | `suggested`, `confirmed`, `rejected` |
| Parser Version | `2.1.0` |
| Defaulttrigger | `!admin` |
| Fuzzy Threshold | 0.74, Clamp 0..1 |
| Recent Player Lookback | 300 s |
| Recent Log Limit | 2500 |
| Retention | 90 d, Clamp 1..3650 |
| Reason/Raw Message | maximal 4000 Zeichen |
| Incident Listenlimit | 1..250 |
| Idempotency-Key | maximal 64 Zeichen |
| Defaultdedupe | 60 s |

### 5.3 Settings

`incident_capture_enabled()` wird wahr, wenn mindestens eines gilt:

- Incident Capture/Mobile Integration;
- Discord Reports;
- AI Moderation.

`_value()` behandelt auch leere Composewerte als „nicht gesetzt“ und fällt auf Legacy-Mobile-Variablen zurück.

Contextmodi:

- `disabled`: Legacy-Targetresolver, keine Subjectliste.
- `shadow`: reichere Kandidaten bleiben vorgeschlagen.
- `enabled`: eindeutige exakte Kandidaten können bestätigt werden; Fuzzy bleibt Vorschlag.

### 5.4 Parsing

Wichtige Funktionen in `rcon/admin_incidents.py`:

| Funktion | Aufgabe |
| --- | --- |
| `_normalize_message()` | NFKD, Casefold, Diakritika entfernen, nichtwortzeichen normalisieren |
| `_normalize_team()` | Allies/Axis normalisieren |
| `_strip_clan_tag()` | führende `[Tag]`, `<Tag>` oder `(Tag)` entfernen |
| `player_snapshot()` | stabiles Snapshotfeldset, `team_kills`/`teamkills` vereinheitlichen |
| `recent_report_players()` | explizit erwähnte kürzlich disconnectete Spieler aus Logs rekonstruieren |
| `flatten_team_view()` | Team-/Squadbaum in flache Squadobjekte mit Leader/Snapshots umwandeln |
| `_best_fuzzy_window()` | bestes Textfenster via `SequenceMatcher` |
| `_resolve_subjects()` | Player-, Squad- und Commander-Kandidaten erzeugen |
| `parse_chat_report()` | Trigger, Reason, Subjects und Primary Target ableiten |

### 5.5 Recently disconnected recovery

`recent_report_players()`:

- durchsucht nur das Lookbackfenster;
- stoppt bei älteren newest-first Logs;
- verwendet keine Fuzzymatches für historische Kandidaten;
- schließt Reporter und noch live vorhandene IDs/Namen aus;
- bewahrt direkten Teamkill gegen Reporter als Evidence;
- kann Commander aus gecachtem Squad `-1` erkennen, wenn kein Livecommander vorhanden ist.

### 5.6 Subjects

`_subject_from_payload()`:

- Kind und State allowlisten;
- Player benötigt Name und ID;
- `is_primary` nur bei confirmed;
- Name maximal 255;
- Player-/Team-/Squad-/Role-IDs meist 100;
- Squaddtyp 32;
- Matchmethod 64;
- Matched Text 255;
- Parserversion 32;
- Confidence Clamp 0..1.

Es gibt keine implizite Aktion gegen ein gesamtes Squad. Einzelne Spieler müssen ausgewählt werden.

### 5.7 Create und Dedupe

`create_incident()`:

1. Source allowlisten: chat/manual/ai_chat/ai_player_name.
2. Reason nicht leer.
3. Idempotency-Key prüfen.
4. optionaler Dedupehash aus Server, Reporter, Rawmessage, Subjects/Target.
5. bestehenden Event mit Idempotency-Key zurückgeben.
6. gleichen Incident im Dedupefenster zurückgeben.
7. Incident mit Revision 1 erstellen.
8. Created Event anlegen.
9. Subjects validieren oder Legacy-Target in Confirmed Subject überführen.
10. genau ein Primary Target synchronisieren.

### 5.8 Mutation und Concurrency

`mutate_incident()` verwendet:

- DB-Rowlock `FOR UPDATE`;
- `expected_revision`;
- Idempotency-Key;
- spezielle idempotente Wiederholung für denselben Claimactor;
- Conflict bei fremdem Claim oder geänderter Revision;
- erlaubte State Transitions statt freier Statusstrings.

Damit ist Mobile-/Discord-Optimistic Concurrency serverseitig, nicht nur UI-seitig.

---

## 6. Mobile Admin

### 6.1 Dateien

| Datei | Verantwortung |
| --- | --- |
| `rconweb/api/mobile.py` | Discovery, Pairing, Desktop Device Code, Devices und Integrationsstatus |
| `rconweb/api/mobile_tokens.py` | Access-/Refresh-Token-Lifecycle |
| `rconweb/api/mobile_incidents.py` | Incidentlisten und Mutationen |
| `rconweb/api/mobile_stream.py` | Event-/Live-Stream |
| `rconweb/api/mobile_audit.py` | Mobile Audit |
| `rconweb/api/models.py` | MobileDevice, Pairing, AccessToken und Integrationsmodelle |
| `mobile_app/` | Flutterclient |
| `scripts/mobile_admin_beta_e2e.py` | gated E2E |
| `docs/mobile-admin.md` | Betriebsvertrag |

### 6.2 Pairingdefaults und Grenzen

| Wert | Default/Grenze |
| --- | --- |
| Pairing Lifetime | 120 s |
| Recent Password Confirmation | 300 s |
| Protocol Version | 1 |
| Minimum App Version | 0.1.0 |
| Device Name | maximal 128 Zeichen |
| App Version | maximal 32 Zeichen |
| Device-Code-Pollintervall | 2 s |
| User Code | `FLN-XXXX-XXXX`, ambiguitätsarmes Alphabet |
| Public Base URL | HTTPS; HTTP nur Debug oder explizit insecure |

`create_pairing()` verweigert alte offene Pairings desselben Users, erzeugt ein purpose-bound Token-Digest und liefert das rohe Secret nur im QR-Payload.

Desktopflow:

```text
Client erzeugt Device Code
  -> Browser öffnet Verification URI
  -> CRCON-Login + frische Passwortbestätigung
  -> approve/deny unter DB-Rowlock
  -> Client pollt Exchange
  -> Device + Tokenpaar
  -> Pairing wird consumed und Secretdigest ersetzt
```

### 6.3 Token-Lifecycle

Datei `mobile_tokens.py`:

| Wert | Default |
| --- | ---: |
| Access Token | 15 min |
| Refresh Idle | 30 d |
| Absolute Device Lifetime | 180 d |
| Last-Seen-DB-Update | höchstens alle 5 min |
| Randomtoken | Prefix + 32 URL-safe Randombytes |

- Tokens werden HMAC-SHA256 mit Django `SECRET_KEY` und Purpose gebunden.
- Refresh rotiert, löscht alle alten Access Tokens und gibt ein neues Paar aus.
- Device Revocation löscht Refreshdigest und alle Access Tokens.
- User muss aktiv bleiben; Permissions werden bei APIrequests erneut geprüft.

### 6.4 Featureflags

`mobile_feature_enabled(name)` ist opt-in; risikoreiche Oberflächen liefern 404, wenn ihr Flag nicht aktiv ist.

### 6.5 Actiongate

- Kick/temp Ban brauchen Reason und Confirmation im Client/API-Vertrag.
- E2E führt ohne `--allow-action` keine echte Spieleraktion aus.
- Schreibende Mobile-Aktionen werden nicht offline gequeued.

---

## 7. Campaign Delivery

### 7.1 Dateien

- `rcon/campaign_delivery.py`.
- `rcon/broadcast.py`.
- `rcon/user_config/auto_broadcast.py`.
- `rcon/models.py::CampaignDelivery`.
- Alembic `8d0f4a2c9b71`.
- Supervisor-Command `campaign_message_loop`.

### 7.2 Campaignconfig

`AutoBroadcastMessage`:

| Feld | Default/Grenze |
| --- | --- |
| ID | automatisch UUID, maximal 64 |
| Title | leer, maximal 80 |
| Enabled | true, strict bool |
| `time_sec` | Pflicht, >=1 |
| min Players | 0, 0..100 |
| max Players | 100, 0..100 und >= min |
| Pause During Seeding | false |
| Delivery Mode | broadcast/player_message |
| min Session | 5 min, 1..1440 |
| Recipient | all/vip/non_vip |
| global Direct Interval | 10 s, 5..300 |
| per Player Gap | 300 s, 60..3600 |

Legacyformat `<seconds> <message>` wird weiter akzeptiert.

### 7.3 Workerdefaults

| Konstante | Wert |
| --- | ---: |
| Check Interval | 5 s |
| Retention | 30 d |
| Max Attempts | 3 |
| Retry Delays | 30 s, 60 s |
| stale `sending` | 120 s |
| Claim Advisory Lock Namespace | 824000 + Servernummer |
| Claimscan | maximal 500 Rows |
| Status Recent Limit | Clamp 1..100, Default 20 |

### 7.4 Zustandsmaschine

```text
eligible Onlineplayer + aktive Session
  -> queued
  -> advisory transaction lock
  -> global interval + player gap
  -> sending
  -> sent
     oder queued für Retry
     oder failed nach 3 Versuchen
  -> expired bei Sessionende/Configänderung
```

Stale Sending wird absichtlich auf `failed` gesetzt und nicht automatisch wiederholt, weil der Worker nicht beweisen kann, ob die Nachricht bereits zugestellt wurde. Das verhindert Duplicate Messages auf Kosten eines möglichen verlorenen Sends.

Unique Constraint:

```text
server_number + campaign_id + player_session_id
```

---

## 8. Discord-/AI-Service

### 8.1 Deploymentgrenze

- eigenes `discord_service/Dockerfile`.
- Python 3.13 Slim.
- FastAPI/Uvicorn.
- eigene DB und Secrets.
- öffentlich nur hinter HTTPS-Reverse-Proxy.

### 8.2 Settings

Datei `discord_service/app/config.py`:

| Feld | Default/Grenze |
| --- | --- |
| DB | SQLite Developmentdefault |
| Service Secret | min 32, Developmentplaceholder |
| Discord Permissions | 84992 |
| AI Model | `gpt-5.6-luna` |
| Player Name Model | `gpt-5.4-nano` |
| Moderation Model | `omni-moderation-latest` |
| Prompt Version | `moderation-v1` |
| Codex Enabled | true |
| Codex Timeout | 90 s, 10..300 |
| Rate Limit | 120/min, 1..10000 |
| Dry Run | false |

Developmentdefaults sind nicht produktionssicher; echte Secrets sind Pflicht.

### 8.3 Managed AI

Datei `discord_service/app/ai.py`.

#### Allgemein

- Input ist ausdrücklich untrusted evidence.
- Structured Output via Pydantic.
- generatives Modell hat keine Tools.
- `hard_hit` kommt ausschließlich aus dem Moderation Gate.
- Text wird für Hauptanalyse auf 4000 Zeichen begrenzt.
- Reports werden nicht automatisch durch denselben AI-Pfad gejagt; AI-Kandidaten sind getrennt.

#### Player Names

- Batch maximal 50.
- Index 0..49.
- Risk Score 0..1.
- Evidence excerpts maximal 80.
- Rationale 1..300.
- Playerresponse maximal 200.
- Batch Output Tokens Clamp 1200..12000 abhängig von Itemzahl.
- nur exakte, normalisierte Evidenzsubstrate akzeptiert.
- targeted hate benötigt sowohl Protected-Target- als auch Hostile-Excerpt.
- klare Verletzung hebt Risk auf mindestens .9; nicht belegte wird höchstens .89.

#### Cost Gate

Chatkandidaten ohne Omni-Flag und ohne Force Structured Analysis erhalten eine strukturierte `none`-Analyse, ohne zweiten teureren Modellcall. Playernamen verwenden den spezialisierten günstigen Nameclassifier.

### 8.4 Tabellen/Outbox

Alembic ergänzt:

- `admin_incident_discord_delivery`, unique Event, Attempts/Next/Delivered/Error.
- `moderation_analysis`, Source/Incident/Player/Fingerprint/Analysis/Visibility/Model/Prompt/Policy/Dedupe.
- `moderation_candidate_outbox`, Source/Server/Player/Text/Fingerprint/Rules/Policy/Shadow/Attempts/Delivery/Analysis.

Source-/Visibility-Constraints verhindern freie Zustände.

### 8.5 Capabilities

Pairing erzeugt getrennte Event- und Actioncapabilities. Empfänger speichern Digests; Sender kann Rohwerte verschlüsselt halten. Callbackhosts können allowlistet werden; private/link-local Targets und falsche Pfade werden abgelehnt.

---

## 9. Mobile Push

- separater Relay und Worker.
- Payload enthält minimale Event-/Delivery-IDs, keine Reporttexte, Playernamen/-IDs oder Adminnotes.
- Permission wird vor Delivery erneut geprüft.
- Tokenregistration retryt idempotent.
- Pushausfall blockiert Web-/API-Moderation nicht.

---

## 10. Datenmodell nach Domäne

### CRCON-Core

- Spieler-IDs, PlayerSessions, PlayerActions.
- Server/Map/Score/History.
- VIP/Admin/Bans.
- Userconfig.

### Incidents

- `admin_incident`.
- `admin_incident_event`.
- `admin_incident_subject`.
- Delivery/Analysis/Outboxtabellen.

### Mobile

- `MobileDevice`.
- `MobilePairing`.
- `MobileAccessToken`.
- Integrations-/Pushzustände.

### Campaign

- `campaign_deliveries` mit Foreign Keys auf PlayerID und PlayerSession.

Neue Frontlinefeatures werden über Alembic additiv eingeführt. Mobile/Django-Modeländerungen müssen zusätzlich mit Django-Migrationszustand koordiniert werden.

---

## 11. Supervisor-/Prozessmodell

Getrennte Prozesse umfassen je nach Composeprofil unter anderem:

- Web/API.
- Log Event Loop.
- Broadcasts.
- Campaign Messages.
- Expiring VIPs.
- Mobile Push Worker.
- Discord Report Worker.
- weitere CRCON-Automods.

Bestimmte Worker setzen `HLL_DB_DISABLE_CONNECTION_POOL=1`, um pro Loop keinen großen DB-Pool zu halten. Supervisor isoliert Restarts einzelner Prozesse.

---

## 12. Datenwege

### Report

```text
HLL Chatlog
  -> Hooks/Discord Chat
  -> Trigger + Live/Recent Context
  -> parse_chat_report
  -> Incident + Immutable Subjects/Snapshots + Event
  -> Discord Delivery Outbox
  -> zentraler Discord Service
  -> Discord Incident Message
  -> Mobile/Web Claim/Resolve/Action
  -> Revision + Event + Audit
```

### AI

```text
Chat-/Name-Regelcandidate
  -> Candidate Outbox
  -> Discord Service
  -> Omni Gate / Name Classifier / Structured Analysis
  -> Moderation Analysis Record
  -> shadow/ignore/incident policy
  -> Menschlicher Review; keine direkte AI-Serveraktion
```

### Campaign

```text
AutoBroadcast Config
  -> Onlineplayer + VIP + aktive PlayerSession
  -> CampaignDelivery pro Session
  -> Campaign Worker
  -> message_player
  -> persistent Status/Retry
```

### Mobile

```text
CRCON Websession + Passwortbestätigung
  -> One-Time Pairing/Device Code
  -> Access/Refresh Tokens
  -> Permission-aware Mobile API
  -> Incident/Player/Server Read
  -> bestätigte Action
  -> CRCON Permission + Idempotency + Audit
```

---

## 13. Production Deployment

`docs/production-deploy.md` beschreibt:

- sauberen Checkout;
- richtigen Branch `master`;
- read-only Deploy Key;
- Dirty-/Non-Fast-Forward-/Compose-Gates;
- PostgreSQL Custom-Format-Backup;
- commitadressierte Images;
- Migrationcheck;
- Rollback auf vorheriges Image;
- keine automatische Alembic-Downgradeannahme.

Ein laufender Container mit falschem Alembic-/Django-Migrationsstand ist kein erfolgreicher Deploy.

---

## 14. Failure Modes und Sicherheitsgrenzen

- RCON kann offline sein, während Web/API erreichbar bleibt.
- Fuzzy Incidentkandidaten dürfen nicht automatisch bestätigt werden.
- Recently-disconnected Recovery nutzt explizite Namen/Evidence, keine historische Fuzzysuche.
- Mobile Featureflags sind opt-in; Integrationsdefault deaktiviert.
- Pairingsecret und Tokens werden nur gehasht gespeichert; Rohwerte nur einmal ausgegeben.
- keine Offlinequeue für Kick/Ban.
- Discordserviceoffline: Incident bleibt persistent, Delivery retryt.
- AI offline: `unavailable_reason`; Incidentworkflow muss fortbestehen.
- Stale Campaign Sending wird nicht wiederholt, um Duplikate zu vermeiden.
- Workerlocks können pro DB/Server wirken; Supervisor allein ersetzt keine Idempotency.
- HLLV-Reconnect-Fix darf CONNECTED nicht abbrechen.
- Developmentdefaults im Discord Service sind nicht produktionsgeeignet.
- Capabilities dürfen nicht in URLs/Logs.
- CORS/Reverse-Proxy-Konfiguration ersetzt keine Token-/Interaction-Signaturprüfung.

---

## 15. Tests

Belegte Testbereiche:

- Admin Incidents und Subject Contract.
- Recently Disconnected Targets.
- HLLV Spectator Refresh.
- Campaign Delivery und Configvalidierung.
- Mobile Pairing/Permissions/E2E.
- Discord-/AI-Service Structured Output und Security.
- API/CRCON-Core.
- Migrationsheads.
- Supervisor-/Scalingcompatibility.

Formatierung:

- Black Python 3.11.
- isort `black`-Profil.

---

## 16. Die zehn jüngsten Commits

| Datum | Commit | Änderung |
| --- | --- | --- |
| 2026-08-20 | `97968b4` | `docs: expand Frontline CRCON platform README` |
| 2026-08-19 | `16d6a04` | Production Images exponieren Releaseversion |
| 2026-08-19 | `0073389` | Frontline CRCON README neu aufgebaut |
| 2026-08-19 | `6196004` | kürzlich disconnectete Reporttargets rekonstruieren |
| 2026-08-19 | `81535aa` | Merge gestaffelte Player-Message-Campaigns |
| 2026-08-19 | `79bff78` | persistente gestaffelte Player Messages |
| 2026-08-18 | `48c13a0` | HLLV Spectatorrechte nach Reconnect sicher reapplyen |
| 2026-08-17 | `52ab9e0` | Reportbenachrichtigung nur an Reporter |
| 2026-08-17 | `29cb67d` | offizielle North-Africa-Factionicons |
| 2026-08-17 | `48a6860` | Incident-Subject-Vertrag testen |

Der direkt folgende Commit `d8b0095` stellt den reichen HLL-/HLLV-Reportkontext wieder her. Die Tabelle bleibt bei genau zehn Git-Commits und filtert Doku-/Mergecommits nicht künstlich heraus.

---

## 17. Pflegevorgabe

Jede neue Frontline-Funktion muss dokumentieren:

1. Sourcefile und Symbol;
2. Prozess/Supervisorprogramm;
3. Permission-/Featureflag;
4. Defaults und echte Clamps;
5. Tabelle, Status und Unique-/Idempotency-Key;
6. Datenweg;
7. Retry/Retention;
8. Mobile-/Discord-/HLLV-Spezifika;
9. Tests und Migration;
10. letzte relevante Commits.
