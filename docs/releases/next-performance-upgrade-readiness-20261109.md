# Schlankeres RCON und sichere Kundenupdates: Prüfstand 9. November 2026

Ziel: Die nächste Version soll auch bei bestehenden Kunden weniger unnötige
Arbeit verursachen und sich ohne Verlust von Daten, Einstellungen oder
Integrationen aktualisieren lassen. Ausgangspunkt ist `v0.9.3`. Diese Datei
ist ein Prüfstand, keine Freigabe oder Ankündigung einer neuen Version.

## Portable Änderungen seit v0.9.3

| Änderung | Nutzen | Kompatibilität und bisheriger Nachweis |
| --- | --- | --- |
| Inkrementelle Live-Logs (`6c0c0d25`, `2a263a33`) | Nach dem ersten Laden nur neue Ereignisse; pro Anfrage höchstens 500 Rohereignisse; frühere Freigabe inaktiver Browser-Caches | Cursor optional, bisherige API und Berechtigung erhalten. 20 Backend-, 67 Frontend- und sieben Browserprüfungen beim Hotfix bestanden. Filter, ältere Seiten und Pause/Fortsetzen auf RCON3/4 abgenommen. |
| Theme-Fehlerbehandlung und gültiges `gcTime` (`6c0c0d25`) | Bedienbare Fehleranzeige statt leerer Seite, begrenzter Wiederholungsversuch; ungenutzte Live-Logdaten nach einer Minute freigegeben | Produktionsbuild, Übersetzungen, CSRF, Polling und Paketgröße beim Hotfix geprüft; alte Assets für bereits geöffnete Tabs erhalten. |
| TCP-Verarbeitung und Verbindungsbereinigung (`26af1623`) | Vollständige fragmentierte Antworten lesen, Verbindungen bei EOF/Fehlern schließen, Laufzeit und Antwortgröße begrenzen | 113 isolierte Tests einschließlich HLL/HLLV und Schutz vor doppelten Kick-Versuchen bestanden. RCON3/4 produktiv geprüft. |
| Gemeinsame Logrotation (`26af1623`) | Rotation funktioniert auch bei stillgelegtem Server 1; gemeinsame Sperre und Zustand verhindern konkurrierende Rotation | Tatsächliche Rotation und Neustart-/Sperrverhalten getestet; RCON3/4 mit archivierten Ausgangslogs geprüft. |
| Abgesicherter Maintenance-Start (dieser Änderungsstand) | Keine beim Kunden erzeugten Django-Migrationsdateien; veralteter Gesund-Marker entfernt; keine Shell-Ausgabe expandierter Zugangsdaten | Sechs gezielte Tests und Modell-/Migrationsabgleich im isolierten Linux-Container bestanden. Noch nicht produktiv ausgerollt. |

Messbeispiel Live-Protokoll: RCON3 lieferte beim alten 500er-Abruf 412.597 Byte,
unmittelbar danach im neuen Delta-Modus ohne neue Ereignisse 713 Byte. RCON4:
247.406 bzw. 713 Byte. Das belegt kleinere Antworten in dieser Probe, keinen
pauschalen CPU-/RAM-Gewinn für jeden Kunden oder Lastzustand. Die komplette
frühere Abnahme steht in [Live-UI-Hotfix](v0.9.3-live-ui-hotfix-20261109.md) und
[Runtime-Hotfix](v0.9.3-runtime-hotfix-20261109.md).

## Update-Start und neue Regressionstests

Der Maintenance-Container prüft Django-Modelle mit
`makemigrations --check --dry-run --no-input` und wendet anschließend die
mitgelieferten Migrationen an. Modelländerungen ohne mitgelieferte Migration
führen zum Fehler statt zu einer installationsspezifischen Migrationshistorie.
Ein alter Health-Marker wird schon am Beginn entfernt und erst nach erfolgreichem
Abschluss neu geschrieben. Globales Shell-Tracing wurde entfernt, damit die
Passwortprüfung im Web-Start keine expandierten Zugangsdaten ausgibt.

Die Reihenfolge der bestehenden Alembic-, ID- und Redis-Schritte bleibt erhalten.
Ein späterer Django-Fehler rollt zuvor abgeschlossene Schritte **nicht** automatisch
zurück. Sicherung und ein getesteter Rückweg bleiben deshalb erforderlich.

Neue/erweiterte Tests prüfen:

- Tatsächliches Shell-Verhalten bei Erfolg, fehlender Modellmigration,
  Alembic-Fehler und Django-Migrationsfehler, auch mit altem Health-Marker.
- Web-Start bei unerreichbarem Gameserver ohne Ausgabe des Datenbankpassworts.
- Bestehenden v0.9.3-Migrationsstand mit Benutzer und Passwort, direktem Recht,
  Gruppenrecht und Mitgliedschaft, API-Key-Hash, individuellen Anzeige- und
  Live-Einstellungen sowie Discord-Anbindung, Aktionen, Rollen, Richtlinie und
  gespeicherten verschlüsselten Werten. Zweimaliges `migrate` darf diese Werte
  nicht verändern oder den Benutzer zum Superuser machen.
- Den bereits vorhandenen Upgrade-Test von API-Migration 0039 auf 0041.

Endgültige Testfassung am 9. November 2026, 20:12:51–20:13:02 UTC geprüft:
3 Maintenance-Tests, 1 Web-Start-Test, 2 Django-Migrationstests und
`makemigrations --check --dry-run` erfolgreich. Der Wegwerfcontainer hatte
kein Netzwerk, keine produktiven Datenvolumes und wurde danach entfernt.
Private Belege: `upgrade-final-tests.json` und `upgrade-final-tests.log` im
Wartungsverzeichnis `rcon34-log-compaction-20261109`.

Die Django-Tests verwenden synthetische Daten und SQLite. Beim initialen Import
des leeren Testschemas protokolliert das bestehende App-Ready-Verhalten eine
noch fehlende `api_steamplayer`-Tabelle; Modellprüfung und alle Tests enden
erfolgreich. Es wurde kein Produktionsschema beschädigt. Diese Tests belegen
keinen vollständigen PostgreSQL-Upgrade-/Restore-Durchlauf. Die bestehenden
CI-Schritte `pytest tests/` und `api.test_release_migrations` führen die neuen
Tests künftig mit aus.

Gegenüber `v0.9.3` werden mit diesen Hotfixes keine neuen Alembic- oder
Django-Migrationsdateien eingeführt. Die aktuelle CI-Versionsmatrix baut
verschiedene Versionsbeschriftungen aus demselben Quellstand; sie ersetzt
keinen Upgrade-Test von tatsächlichen alten Release-Images.

## Was beim Kundenupdate erhalten bleiben muss

Benutzer, Passwörter, Rechte und Gruppen, API-Schlüssel, SMTP, Discord-/KI-
Anbindung, serverbezogene Automatikregeln, Darstellungspräferenzen, Spiel- und
Reportdaten sowie aktive Compose-/Proxy-Einstellungen müssen erhalten bleiben.
Optionale Dienste oder automatische Maßnahmen dürfen durch ein Update nicht
ungefragt aktiviert werden. Die bisherige API muss für externe Clients und
noch geöffnete Browser-Tabs weiter funktionieren.

Die lokale Entfernung eines ungültigen RCON3-Webhooks ist keine globale
Kundeneinstellung. Ebenso sind die genehmigten RCON1/2-Löschungen und die
[Indexverkleinerung](../operations/rcon34-log-index-compaction-20261109.md)
keine automatischen Release-Schritte. Bestehende Retention bleibt in ihrer
bisherigen Einstellung; dieses Update schaltet sie nicht ein. Komprimierung
und Aufbewahrung vorhandener Kundenlogs müssen deren Einstellungen beachten.

## Noch erforderliche Release-Abnahme

1. **Echtes Bestandsupgrade:** Datenbank und Konfiguration einer repräsentativen
   v0.9.3-Installation in einer isolierten Umgebung wiederherstellen. SMTP,
   Discord, Push und Gameserver-Aktionen dort technisch von externen Empfängern
   trennen. Mit dem tatsächlichen alten Image starten, Kandidatenimage anwenden,
   Schema sowie alle oben genannten Bestandsdaten vergleichen und Update erneut
   ausführen. Zusätzlich Neuinstallation prüfen. Weitere ältere Ausgangsversionen
   nur als unterstützt nennen, wenn ihr tatsächlicher Upgrade-Pfad geprüft ist.
2. **Funktionsabnahme:** Login, CSRF, Rechte einschließlich abgelehnter Zugriffe,
   API-Key-Authentifizierung, Live-Filter/Nachladen, Rundenende/Statistiken,
   Discord-Interaktionen, WebSockets und Automod-Status. HLL und HLLV sowie
   gemeinsame/getrennte Runtime-Modi abdecken. RCON3/4 decken live derzeit nur
   HLLV ab; die stillgelegten RCON1/2 dürfen dafür nicht wieder gestartet werden.
3. **Reproduzierbare Leistungsmessung:** Gleiche Datenmenge und nachvollziehbare
   Last vor/nach Änderung vergleichen: Antwortgrößen, p50/p95-Latenz, CPU-Zeit,
   Prozess-RAM, DB-Verbindungen und Datenwachstum. RCON4 ist derzeit leer und
   allein kein Beleg für Verhalten auf einem vollen Server.
4. **Rückweg prüfen:** Unveränderliche alte Images und Konfiguration sichern,
   Wiederherstellung prüfen. Bei den schemaunveränderten Code-Hotfixes zuerst
   Image-Rollback testen, damit neue Live-Daten erhalten bleiben. Falls der
   endgültige Kandidat zusätzliche Migrationen erhält, deren Rückweg gesondert
   testen; keine pauschale Wiederherstellung über zwischenzeitliche Live-Daten.
5. **Pilot und Freigabe:** Zuerst RCON4, dann RCON3 mit Backup und HTTP-/WebSocket-
   Readiness, statischen Dateirechten und Beobachtung über normale Nutzung und
   einen Rundenwechsel. Danach Entscheidung über Veröffentlichung und weitere
   Kunden. Kein ungeprüfter Flottenwechsel auf einen beweglichen Image-Tag.

Fortschreibung vom selben Abend: Eine 30-minütige Ausgangsmessung, ein echtes
Bestandsupgrade von v0.9.3 mit wiederhergestelltem PostgreSQL/Redis, Wiederholung,
Code-Rollback und Neuinstallation sind inzwischen geprüft. Das Backend-Paket
wurde bei identischen Python-Abhängigkeiten um 41,65 % verkleinert. Die Ergebnisse,
Prüfgrenzen und verbleibende Release-Abnahme stehen im
[Paket- und Update-Prüfbericht](../operations/release-efficiency-20261109.md).
Ein Laufzeitgewinn der API oder des RAM-Verbrauchs wurde dadurch nicht belegt.
Es fand noch kein Rollout dieses Kandidaten statt.
