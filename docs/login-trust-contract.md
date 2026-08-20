# Login-Vertrauensvertrag

## Problem und Nutzerwirkung

Der anonyme Aufruf von `https://rcon3.fln.gg/` leitete zwar korrekt zur
Anmeldung weiter, zeigte im Browser-Tab aber den irreführenden Zustand
`🔴 Dieser Bereich kann derzeit nicht angezeigt werden.`. Während derselben
Messung wurden außerdem fünf geschützte Live-Abfragen mit HTTP 401 beantwortet:

- `GET /api/get_status`: 1 Anfrage
- `GET /api/get_gamestate`: 4 Anfragen

Damit wirkte die funktionsfähige Anmeldung wie eine Störung. Gleichzeitig
verursachte der anonyme Einstieg unnötige Requests, Fehlerausgaben und
potenzielle Wiederholungen.

Messzeitpunkt: 20. August 2026, Desktop-Viewport 1440 × 1000. Die Prüfung lief
in einem frischen, nicht angemeldeten Browserkontext gegen RCON3.

## Technische Ursache

Der globale `TitleManager` war außerhalb des authentifizierten Routenbaums
montiert. Er interpretierte den absichtlich noch nicht geladenen Serverzustand
der Anmeldeseite als Systemfehler und überschrieb ihren Dokumenttitel. Für die
anonyme Route fehlte außerdem ein eigener automatisierter Vertrag, der
geschützte Status-, Spiel-, Mehrserver-, Moderator- und Teamabfragen verbietet.

## Lösung

- Die Anmeldeseite besitzt einen eigenen lokalisierten Dokumenttitel:
  `Frontline Network · Anmelden` beziehungsweise
  `Frontline Network · Sign in`.
- Der dynamische Servertitel wird ausschließlich innerhalb des
  authentifizierten Administrationsbereichs montiert.
- Der Fake-Server kann einen ausdrücklich anonymen Zustand reproduzieren.
- Die visuellen Tests erfassen intern auch von Mirage abgefangene Requests.
  Dadurch ist die Prüfung nicht von Browser-Netzwerkereignissen abhängig.
- Der Test verbietet auf der anonymen Anmeldung Aufrufe von
  `get_connection_info`, `get_status`, `get_gamestate`, `get_server_list`,
  `get_ingame_mods`, `get_online_mods` und `get_team_view`.
- Die lokale Asset-Vorbereitung funktioniert plattformunabhängig über Node und
  wird vor visuellen Fake-Mode-Tests ausgeführt.

## Vorher-/Nachher-Evidenz

Die sichtbare Frontline-Anmeldung bleibt bewusst unverändert; der Meilenstein
korrigiert Vertrauen, Titel und Hintergrundverhalten ohne ein neues
Designsystem einzuführen.

| Viewport | Live vorher | Verifizierter Stand danach |
| --- | --- | --- |
| Desktop · 1440 px | [Screenshot](evidence/login-trust/before-live-desktop.png) | [Regressionstest](../rcongui/e2e/login-trust.spec.mjs-snapshots/login-desktop.png) |
| Tablet · 768 px | [Screenshot](evidence/login-trust/before-live-tablet.png) | [Regressionstest](../rcongui/e2e/login-trust.spec.mjs-snapshots/login-tablet.png) |
| Mobil · 390 px | [Screenshot](evidence/login-trust/before-live-mobile.png) | [Regressionstest](../rcongui/e2e/login-trust.spec.mjs-snapshots/login-mobile.png) |

| Vertrag | Vorher auf RCON3 | Danach |
| --- | --- | --- |
| Dokumenttitel | roter, falscher Fehlerzustand | lokalisierter Anmeldetitel |
| geschützte Live-Abfragen | 5 fehlgeschlagene Requests | 0 Requests |
| schwere/kritische axe-Verstöße | nicht automatisiert belegt | 0 bei 390, 768 und 1440 px |
| horizontales Überlaufen | visuell geprüft | automatisiert ausgeschlossen |
| Tastaturbedienung | nicht automatisiert belegt | Benutzername → Passwort → Anmelden; Fehler sichtbar |

Der geprüfte Produktions-Build bleibt innerhalb des bestehenden Budgets:
375,73 kB Rohdaten beziehungsweise 114,85 kB gzip für den Entry-Chunk und
1.190,15 kB beziehungsweise 398,57 kB gzip für alle initial referenzierten
JavaScript-Dateien. Das Budget liegt bei 500/150 kB für den Entry-Chunk und
1.500/500 kB für den gesamten initialen JavaScript-Satz.

## Kompatibilität und Berechtigungen

Die Anmeldung ist spielneutral. Der Vertrag gilt unverändert für HLL, HLL
Vietnam und Mehrserverinstallationen. Vor erfolgreicher Authentifizierung wird
nur der Authentifizierungsstatus abgefragt; Server-, Spiel-, Rollen- und
Teamdaten bleiben geschützt. Nach erfolgreicher Anmeldung bleibt der bisherige
`AuthProvider` mit der bestehenden Berechtigungsprüfung maßgeblich.

## Tests

`e2e/login-trust.spec.mjs` prüft:

- 390, 768 und 1440 Pixel Breite
- anonymen Einstieg über `/` mit Weiterleitung zur Anmeldung
- deutschen Dokumenttitel und sichtbare Anmeldung
- geladene reale Frontline-Assets
- keine geschützten Requests auf Anwendungs- oder Netzwerkebene
- keine schweren oder kritischen axe-Verstöße
- kein horizontales Überlaufen
- Tastaturreihenfolge und Validierungsfehler
- visuelle Regressionen für alle drei Viewports

## Risiko und Rollback

Risiko: gering. Der Serverstatus-Titel beginnt nun erst nach erfolgreicher
Authentifizierung. Die Login-Route erhält stattdessen immer ihren statischen,
lokalisierten Titel. Ein Rollback besteht aus dem Zurücksetzen dieses
Meilenstein-Commits; Datenbank-, API- oder Konfigurationsmigrationen sind nicht
erforderlich.

## Changelog

- Irreführenden roten Browser-Titel auf der Anmeldung behoben.
- Anonyme Anmeldung gegen geschützte Hintergrundabfragen abgesichert.
- Login-Verhalten bei 390, 768 und 1440 Pixel inklusive axe, Tastatur und
  visueller Regression automatisiert.
- Plattformunabhängige Frontline-Asset-Vorbereitung für lokale UI-Tests
  ergänzt.
