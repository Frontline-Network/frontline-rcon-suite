# RCON3/4: Bereinigung alter Versionskopien am 2. November 2026

Auf ausdrückliche Freigabe des Benutzers wurden auf dem gemeinsamen Host
`87.106.112.21` genau die **52 Versions-/Build-Ordner und 34 RCON-Paketarchive**
aus dem [vorherigen Prüfprotokoll](rcon34-root-version-audit-20261102.md) entfernt.
Die abschließende Verifikation war um **01:28 Uhr Europe/Berlin** erfolgreich.

## Speichergewinn

| Messwert | Bytes |
| --- | ---: |
| Erwarteter Gewinn nach Berücksichtigung erhaltener Hardlinks | 4,570,099,712 |
| Freier Speicher unmittelbar vor der Löschung | 436,855,574,528 |
| Freier Speicher unmittelbar nach der Löschung | 441,425,625,088 |
| Beobachteter Gewinn während der Löschung | **4,570,050,560** |

Damit wurden rund **4,57 GB (4,26 GiB)** frei. Der beobachtete Gewinn stimmt
bis auf 48 KiB mit der vorab ermittelten Größe überein; auf dem laufenden Host
finden parallel normale Schreibvorgänge statt. Nach der abschließenden Prüfung
waren rund **441,4 GB** frei.

## Vorhandene Sicherung wiederverwendet

Entsprechend der Benutzerangabe wurde keine weitere vollständige Sicherung
angelegt. Verwendet wurde der bereits wiederherstellungsgeprüfte Bestand unter
`/root/hll_rcon_tool/.deploy-state/backup-cleanup-20261101`.

Vor und nach der Löschung wurden Größe und vollständige SHA-256-Prüfsumme aller
sechs Sicherungsdateien erneut mit dem
[gespeicherten Sicherungsprotokoll](rcon34-backup-cleanup-20261101.md) abgeglichen:

- `configuration.tar.gz`
- `postgres-globals.sql`
- `rcon.dump`
- `postgres.dump`
- `redis.rdb`
- `current-images.tar`

Alle sechs Dateien waren unverändert. Der vollständige Restore-Test vom Vortag
wurde nicht wiederholt. Die aktuelle Betriebs-/Datensicherung ist keine neue
Archivkopie der jetzt gelöschten historischen Build-Verzeichnisse.

## Durchführung

- Ausschließlich die 86 einzeln aufgeführten und freigegebenen Pfade wurden
  bearbeitet; keine Löschung über Namensmuster und kein Docker-Prune.
- Aufgelöste Pfade mussten direkte Kinder von `/root` sein. Symlinks als Ziel,
  verschachtelte Dateisystem-Mounts und Verweise aus Docker, Systemdiensten,
  Cron-/Proxy-Konfigurationen oder offenen Prozessen waren ausgeschlossen.
- Geräte-/Inode-Kennungen, Zeitstempel, Dateianzahl und jüngster Dateistand
  wurden mit der Inventur verglichen. Vor der Löschung wurden zusätzlich
  Fingerprints der vollständigen Verzeichnis-Metadaten erneut geprüft.
- Git-Arbeitskopien innerhalb der freigegebenen Ordner waren unverändert;
  ihre HEAD-Commits waren im Git-Objektbestand der aktiven Installation vorhanden.
- Ordner wurden mit symlink-sicherem `shutil.rmtree` entfernt; Paketarchive
  einzeln mit `unlink`. Jeder erfolgreiche Schritt wurde sofort protokolliert.

Die erste lesende Vorprüfung stoppte wegen einer automatischen
PowerShell-Zeitzonenkonvertierung im JSON-Transport. Nach Umstellung auf
unveränderte Datumsstrings stimmten die Zeitstempel überein. Dabei wurden keine
Serverdaten verändert; die Löschung begann erst nach vollständig bestandener
Vorprüfung.

## Erhalten und abschließend geprüft

- Alle 86 freigegebenen Ziele sind entfernt. Die Menge der übrigen direkten
  Root-Einträge entspricht exakt dem vorherigen Bestand.
- Aktive Installation und Daten, aktuelle Backups, unklare Sicherungen,
  Testdatenbanken, Arbeitskopien mit ungeklärten Änderungen sowie Pakete anderer
  Anwendungen blieben erhalten.
- `/root/frontline-rcon-perf-00a57098` und das zugehörige Archiv bleiben erhalten,
  da die laufende Redis-Compose-Konfiguration auf den Ordner verweist.
- Fingerprints der ausdrücklich geschützten Pfade und Hashes vorhandener
  Compose-/Umgebungskonfigurationen stimmen mit dem Zustand vor der Löschung überein.
- Container-IDs, Image-IDs, Laufzustände und Startzeitpunkte sämtlicher zuvor
  inventarisierter Container sind unverändert. Es wurde kein Dienst neu gestartet.
- Kein laufender Container meldete bei der Nachkontrolle `unhealthy`.
- RCON3 und RCON4: `/api/get_version` jeweils HTTP 200, `failed: false`,
  Version `v0.9.3-rc.1`; beide Backends weiterhin `healthy`.

Das private Ausführungsprotokoll liegt unter
`/root/hll_rcon_tool/.deploy-state/backup-cleanup-20261101/root-version-cleanup-20261102`:
`approved-targets.json`, `preflight.json`, `removed.jsonl`, `result.json` und
`verification.json`. Lokale Prüfausgaben und Ausführungsskripte liegen unter
`outputs/rcon34-root-cleanup-20261102/`.
