# Live-Karte und Spielerschutz-Monitor

## Stand und Freigabegrenzen

Implementierung auf `codex/live-map-player-protection`, Basis v0.6.3. Noch **kein Release und keine Aktivierung auf den Gameservern**. Beide Schalter sind für jede Instanz standardmäßig aus. Die Browser-Demo ist ausdrücklich synthetisch und wird niemals als Live-Fallback verwendet.

Die Seite `/views/live-map` liegt unter **Live-Betrieb → Live-Karte**. Sie verwendet die vorhandenen taktischen Kartenbilder, einschließlich der sechs HLLV-Karten, und die Theme-/Farbenblindheitsfarben. Eine existierende Bilddatei ist keine bestätigte Weltkoordinaten-Abbildung: Ohne geprüfte Referenzen bleiben Marker und Laufwege verborgen.

### Lesende Datenprüfung vom 5. September 2026

Auf RCON1–4 wurden nur Spieler-Sammelantwort, Kartenstatus und die vom Gameserver gemeldete Befehlsliste gelesen. Keine Nachrichten, Kartenwechsel oder Moderationsaktionen wurden ausgeführt.

| Instanz | Spiel | Spieler bei Prüfung | Karte | Dauer der Probe* |
|---|---|---:|---|---:|
| RCON1 | HLL | 0 | Juno Beach | 0,145 s |
| RCON2 | HLL | 0 | St. Marie Du Mont | 0,086 s |
| RCON3 | HLLV | 0 | Cam Ranh Port | 0,198 s |
| RCON4 | HLLV | 0 | Đăk Tô Airfield | 0,217 s |

\* Enthält mehrere lesende Aufrufe; **kein Lastnachweis für 100 Spieler**. `scripts/probe_live_map.py` gibt Anzahl, Feldnamen und höchstens drei anonymisierte Vektoren aus, keine Spieler-IDs oder Namen. Alle Antworten waren leer, daher sind reale Positionsqualität und Kartenabweichung weiterhin ungeprüft.

HLLV meldete 63, HLL 61 Befehle. Kein Treffer für Garnisonen, Outposts oder Spawn-/Objektpositionsabfragen in diesen Listen. Die bereitgestellte HLLV-RCON-PDF dokumentiert `WorldPosition` auf Seite 20, aber keine personenbezogenen Spawnpunkt-Abbauereignisse. Das ist **keine Behauptung**, dass eine solche Quelle grundsätzlich unmöglich wäre. Bis zu deren Bestätigung bleiben die drei Fähigkeiten Objektposition, Verlust und Verursacher separat auf „Vom Gameserver nicht verfügbar“.

## Bedienung

- Karte: Zoom, Verschieben, Namensanzeige ab ausreichendem Zoom, Suche nach Name/ID, Team und Trupp. Kreise und Rauten ergänzen die Teamfarben.
- Auswahl: Verfolgen, Profil und bestehende berechtigungsgeprüfte Spieleraktionen. Aktionen sind im Rückblick und bei veralteten Live-Daten ausgeblendet.
- Beobachtung: Sitzung oder dauerhaft. Sitzungseinträge gelten nur für die aufgezeichnete Sitzungs-ID; dauerhafte Einträge werden mit bestätigten Kontoverbindungen aufgelöst. Namen allein sind kein Verknüpfungskriterium.
- Rückblick: Die letzten 24 Stunden in Abfragen von höchstens 15 Minuten. Sichtbarer Zeitstempel, Wiedergabe/Pause, Schieberegler, „Zurück zu Live“. Datenlücken werden nicht interpoliert. Aktuelle Live-Hinweise werden nicht mit historischen Karten vermischt.
- Hinweise: Ausgewählte Spieler zeigen auch einzelne Begegnungen. Ab drei Kills desselben Gegners in 15 Minuten erscheint eine zusammengefasste Wiederholungsübersicht. Gegenkills, Waffen, Abstände zwischen Ereignissen, Rollen/Trupps und letzte bekannte Positionsmessungen bleiben prüfbar.
- Hervorgehobene Empfehlung: mindestens vier Kills, mindestens fünf erfasste Tode, mindestens 60 % Anteil und zwei anhand geprüfter Positionsdaten mindestens 200 m entfernte Begegnungsbereiche. Zusätzlich wird der Todesnenner mit einem lückenlosen 15-Minuten-Fenster des Sitzungszählers abgesichert. Fehlt diese Abdeckung, bleibt es ausdrücklich bei der Begegnungsübersicht. Teamkills sind keine verdächtigen Gegnerkills, zählen aber zum Todesnenner; weitere vom Zähler erfasste Tode reduzieren den Anteil ebenfalls. Der Randmesspunkt liegt vor dem Zeitfenster und kann den Nenner leicht erhöhen, nicht den Anteil künstlich steigern.
- Moderation: übernehmen, unauffällig schließen oder einen privaten Ausschnitt sichern. **Keine automatischen Nachrichten, Strafen, Sperren oder Cheating-Wahrscheinlichkeiten.**

## Kartenkalibrierung

Nur berechtigte Einrichter sehen den aufklappbaren Bereich „Kartenabbildung prüfen“. Für jede Karte getrennt:

1. Bestätigten Maßstab in Welteinheiten pro Meter beschaffen. Nicht aus Pixelzahl oder Sektorausrichtung erraten.
2. Drei weit verteilte, nicht kollineare Referenzpunkte im Spiel messen. X/Y werden beim ausgewählten Spieler angezeigt; Koordinaten und Bildpunkt müssen dieselbe tatsächliche Position beschreiben.
3. Zwei weitere unabhängige Prüfpunkte aufnehmen. Referenzpunkte nicht als Prüfpunkte wiederverwenden.
4. Bildpositionen in Prozent des **gesamten** taktischen Bildes angeben: links/oben 0 %, rechts/unten 100 %. Bildränder/Legenden zählen zur Bildfläche. Die affine Abbildung erfasst Achsenrichtung, Maßstab, Rotation und Versatz.
5. Herkunft/Datum dokumentieren, Eingaben bestätigen und speichern. Die API lehnt mehr als zehn Meter Fehler an einem Prüfpunkt ab. Unbekannte Karten und ungültige Werte werden abgelehnt.
6. Die Abnahme anschließend mit zusätzlichen Punkten wiederholen, die nicht zur Einrichtung dienten. Ein bestandener synthetischer Test oder eine selbst deklarierte Herkunft ersetzt diese Abnahme nicht. Nach Austausch/Beschnitt eines Kartenbildes ist eine erneute Kalibrierung erforderlich.

Es sind absichtlich **keine erfundenen Standardkalibrierungen** vorinstalliert. Entsprechend kann die Karte noch nicht auf allen realen Karten als exakt freigegeben werden.

## Technik und Zugriffsschutz

`rcon/live_map/service.py` läuft als `live_map` im vorhandenen gemeinsamen Laufzeitdienst oder als eigener Supervisor-Prozess. Eine erneuerbare Redis-Sperre verhindert mehrere Sammler pro Instanz. `get_raw_player_snapshot` verwendet den gemeinsamen Bulk-Cache; Browser-Endpunkte lesen ausschließlich Cache/Verlauf und führen keine Gameserver-Abfragen aus. Das Zielintervall beträgt 2 s, bei langsamen Zyklen 5/10 s. Messzeit und tatsächliches Datenalter bleiben sichtbar. Persistenzfehler werden vor weiterer Erfassung erneut versucht, damit kein unbeschränkter Puffer anwächst.

PostgreSQL: additive Tabellen `tactical_settings`, `tactical_block`, `tactical_review`; komprimierte Zeitblöcke statt einer Positionszeile pro Spieler. Indizes nach Server/Zeit und Server/Runde/Zeit. Wiederholtes Speichern desselben Blocks ist idempotent. Redis enthält aktuellen Snapshot und den noch nicht persistierten Block (maximal ungefähr 30 s, TTL 120 s). Neustarts übernehmen den Puffer, solange er noch vorhanden ist; längere Ausfälle können eine ausdrücklich sichtbare Datenlücke hinterlassen.

Bereinigung erfolgt pro Instanz jede Minute, auch bei deaktivierter Erfassung: normaler Verlauf 24 h, private gesicherte Ausschnitte 30 Tage. HTTP filtert abgelaufene Daten sofort. Allgemeine Fallakten bleiben beim Löschen der privaten Ausschnitte erhalten. Bei komplett gestopptem Laufzeitdienst kann die physische Bereinigung erst nach dessen Neustart nachgeholt werden; Backups brauchen eine eigene, passende Aufbewahrung.

Eigene Django-Rechte ohne automatische Zuweisung an bestehende Gruppen:

| Recht | Wirkung |
|---|---|
| `api.can_view_live_map` | taktische Karte, aktuelle Positionen und 24-h-Verlauf |
| `api.can_manage_live_map` | zusätzlich Schalter, Kalibrierung und geschützte Spieler verwalten |
| `api.can_view_live_map_cases` | zusätzlich private Fallausschnitte lesen/bearbeiten |

Verwaltung und Fälle erfordern außerdem das Kartenrecht. Fallaktionen benötigen zusätzlich die bestehenden Rechte zum Anlegen/Übernehmen/Schließen. Django-Superuser behalten ihre systemweite Vollberechtigung; gewöhnliche Moderationsgruppen erhalten diese neuen Rechte nicht.

Die API unter `/api/live-map/v1/` prüft jede Anfrage. Session-Schreibzugriffe durchlaufen den bestehenden CSRF-Schutz. Taktische JSON-Felder werden ohne Kartenrecht auch aus alten Spieler-/Team-/Rohdaten-/Mobile-Antworten sowie verschachtelten Weiterleitungsantworten entfernt, einschließlich `world_position`, `WorldPosition` und `p_coord`. Interne Berechnungen behalten Zugriff. Der freie Rohbefehl-Endpunkt erfordert jetzt sowohl Rohbefehl- als auch Kartenrecht, da beliebige Textantworten nicht zuverlässig gefiltert werden können.

Bestehende CSV-Logexporte besitzen feste Logfelder, keine Positionsvektoren. WebSocket-Verträge sind strukturierte Spiel-Logs, allgemeine Vorfälle und Barricade-Scans; die neue Telemetrie wird in keinen dieser Kanäle eingespeist. Private Fallausschnitte liegen ausschließlich in `tactical_review`, niemals im allgemeinen Incident-/Discord-Payload. Öffentliche Builds bekommen weder neue Navigation noch autorisierte taktische Antworten.

Kartenaufrufe, Rückblicke, private Fallzugriffe, Kalibrierungen und Monitoränderungen verwenden das bestehende Auditlog; protokolliert werden Metadaten, keine Koordinaten. Ein Entzug wird an der nächsten API-Anfrage wirksam. Bereits an einen berechtigten Benutzer übertragene Daten können selbstverständlich nicht aus Screenshots oder externen Kopien zurückgerufen werden.

## Prüfungen und Rollout

Automatisiert: reine Domänenregeln, sichere Herkunfts-/Kalibrierungsprüfung, echte Nullkoordinate versus fehlend, Tod/Team-/Sitzungswechsel/Sprünge, doppelte Logs, fehlende Messungen, konservativer Todesnenner, servergetrennter Verlauf, Aufbewahrung, private Fälle, Rechte/CSRF und alte JSON-Ausgaben. Browser: 100 synthetische Spieler, Suche/Zoom, Rückblick, Fall sichern/öffnen, unkalibrierte Karten, normaler Viewer, Mobilansicht ohne horizontalen Überlauf. Die existierende Fall-Engine und Laufzeitdienst-Tests werden mitgeprüft.

Noch offene Abnahmen vor einem Release:

- Reale belegte HLL-/HLLV-Instanz: Positionsfelder, Aktualität, Rundenidentität, Sitzungszähler und Bulk-Kosten bei bis zu 100 Spielern.
- Alle sechs HLLV-Karten und unterstützten HLL-Karten: unabhängige Referenzmessungen, maximal 10 m Abweichung. Keine Freigabe allein durch Tests mit synthetischen Punkten.
- Mehrere echte Betrachter, tatsächlicher Speicher-/Netzwerkverbrauch, Verbindungsabbrüche, Karten-/Serverwechsel, Rechteentzug und Incident-Zugriffe gegen PostgreSQL/Redis.
- Gegenproben mit normalen Duellen, Spawnkämpfen und Aufklärung; die Regeln sind erklärbare Startheuristiken, kein Beweis für Streamsniping.

Sicheres Vorgehen: PostgreSQL-Backup und Konfigurationssicherung; additive Alembic-/Django-Migrationen; zuerst je eine HLL- und HLLV-Testinstanz bei ausgeschalteten Schaltern; ausdrücklich taktische Rechte an Tester vergeben; Erfassung einzeln einschalten und kalibrieren; Monitor erst danach prüfen. Nach menschlicher Abnahme schrittweise RCON1–4. Bei Problemen beide Schalter aus bzw. `live_map` stoppen, ohne übrige RCON-Dienste zu stoppen. Beim Rückrollen bestehende additive Tabellen behalten, keine produktive Downgrade-Löschung ausführen.
