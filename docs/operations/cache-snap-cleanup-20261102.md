# RCON3/4: alter Build-Cache und deaktivierte Snap-Revisionen bereinigt

Host `87.106.112.21`, abgeschlossen am **02.11.2026 um 03:11 Uhr Europe/Berlin**. Der Benutzer hat ausdrücklich die Bereinigung von seit über 30 Tagen ungenutztem Build-Cache und deaktivierten Snap-Versionen freigegeben; aktuelle Versionen, Backups und Datenbanken sollten erhalten bleiben.

## Ergebnis

- Docker: 2,064 der 2,119 vorab erfassten alten Cache-Einträge entfernt.
- Native Docker-Zusammenfassung: `Total:	129.7GB`.
- Snap: 12 deaktivierte Revisionen einschließlich ihrer eindeutig identifizierten Download-Kopien (2.61 GB) entfernt; alle vorher aktiven Revisionen erhalten.
- Beobachtete Zunahme des freien Speichers zwischen Beginn der Cache-Bereinigung und abschließender Prüfung: **182.32 GB (182,321,487,872 Bytes)**.
- Verfügbarer Speicher nach abschließender Prüfung: **624.52 GB**.

| Messpunkt | Freier Speicher in Bytes |
| --- | ---: |
| Vor der Cache-Bereinigung | 442,203,004,928 |
| Nach der Cache-Bereinigung | 621,980,569,600 |
| Vor der Snap-Bereinigung | 621,980,491,776 |
| Nach der Snap-Bereinigung | 621,987,356,672 |
| Nach Entfernung der zwölf alten Snap-Download-Kopien | 624,445,038,592 |
| Nach abschließender Verifikation | 624,524,492,800 |

Der Dateisystemgewinn und Dockers Summe der Cache-Dateigrößen sind unterschiedliche Messgrößen. Blockbelegung, Metadaten und parallele Schreibvorgänge des laufenden Hosts können zu Abweichungen führen. Es wird keine größere Docker-Löschmenge aus dem Dateisystemwert abgeleitet.

## Begrenzung der Cache-Bereinigung

Die Vorprüfung erfasste 2,119 unbenutzte und nicht mit Images geteilte Einträge mit zusammen 130,790,226,319 Bytes. Die letzte Nutzung lag jeweils mehr als 720 Stunden zurück; bei fehlendem Nutzungszeitpunkt wurde der Erstellungszeitpunkt geprüft. Junge, nie verwendete Einträge wurden vor der Ausführung gesondert ausgeschlossen.

Verwendet wurde der lokale Docker-Builder `default` mit Docker 29.0.0 und Buildx 0.29.1. Der ausgeführte Befehl entsprach:

```sh
docker buildx prune --builder default --filter until=720h --filter 'private=""' --force
```

Es wurden weder `docker system prune` noch Image-, Container- oder Volume-Prune verwendet. Die eigentliche Entfernung erfolgte über BuildKit, nicht durch Löschen unter `/var/lib/docker`.

Die Filter wurden zuerst lesend geprüft und mit den exakten Zeitstempeln der Docker-Engine abgeglichen. Buildx 0.29.1 berücksichtigt die Zeitgrenze bei `prune`, während dessen `du`-Vorschau sie in der hier beobachteten Kombination nicht anwandte. Ein zusätzlicher lesender Abgleich mit den konkreten Cache-IDs bestätigte deshalb die Auswahl. Die privaten Cache-Einträge werden in dieser Version mit einem leeren Vergleichswert gefiltert; `private=false` oder `shared=false` wären hier keine geeignete Auswahl.

Die Altersgrenze wird im [Quellcode von Buildx 0.29.1](https://github.com/docker/buildx/blob/v0.29.1/commands/prune.go) als `KeepDuration` an BuildKit übergeben. Die verwendeten Filterkategorien sind in der [Docker-Dokumentation zu Buildx Prune](https://docs.docker.com/reference/cli/docker/buildx/prune/) beschrieben.

## Snap-Versionen und erhaltene Revisionsdaten

Jede Revision wurde unmittelbar vor der Entfernung nochmals auf `disabled` geprüft. Die Auswahl der aktiven Snap-Revisionen musste unverändert sein. Prozesse, offene Dateien und Prozess-Mappings wurden auf Verweise auf die jeweilige alte Revision geprüft. Entfernt wurde ausschließlich mit `snap remove <name> --revision=<revision>`; weder `--terminate` noch `--purge` wurden verwendet.

| Snap | Entfernte Revision |
| --- | ---: |
| `chromium` | 3548 |
| `core20` | 2866 |
| `core22` | 2955 |
| `core24` | 1643 |
| `core26` | 462 |
| `cups` | 1272 |
| `firefox` | 9113 |
| `gnome-42-2204` | 247 |
| `gnome-46-2404` | 168 |
| `lxd` | 40911 |
| `mesa-2404` | 1165 |
| `snapd` | 27738 |

Snap hatte die entfernten Pakete über weitere Hardlinks im Download-Cache erhalten. Ausschließlich die zwölf zugehörigen Dateien wurden anschließend entfernt: Paketname und Revision wurden über lokal signierte Snap-Assertions zugeordnet, SHA3-384, Dateigröße, Inode und Linkzahl überprüft. Keine der Dateien war noch installiert oder durch einen Prozess geöffnet; die Linkzahl war jeweils 1. Andere Download-Dateien und alle aktiven Pakete blieben erhalten.

Die alten Revisionen enthielten insgesamt **6,730,192 Bytes** kleiner Datenbestände. Darunter waren eine Chromium-Zertifikats-/Schlüsseldatenbank und CUPS-Revisionsdaten. Sämtliche vorhandenen alten Revisionsdatenverzeichnisse wurden vor der Paketentfernung separat erhalten; Dateien wurden mit SHA-256, Eigentümern, Berechtigungen und Symlink-Zielen geprüft. Die erhaltenen Kopien wurden nachher nochmals mit dem Manifest verglichen.

Private Ablage:
`/root/hll_rcon_tool/.deploy-state/cache-snap-cleanup-20261102/preserved-snap-data`.

## Abschlussprüfung

- Alle ursprünglichen Container-IDs, Image-IDs, Laufzustände und Startzeitpunkte sind unverändert.
- Sämtliche vorher vorhandenen Docker-Images und Tags sind weiterhin vorhanden.
- Sämtliche ursprünglichen Daten-Mounts und alle Docker-Volumes mit der unten dokumentierten Ausnahme sind erhalten.
- Hashes der erfassten Compose-/Umgebungskonfigurationen stimmen überein.
- Alle vorher aktiven Snap-Revisionen sind unverändert ausgewählt.
- Die kleinen alten Snap-Datenbestände sind unverändert in der geschützten Ablage erhalten.
- Sämtliche nicht zur Cache-Auswahl gehörenden ursprünglichen Cache-IDs sind weiterhin vorhanden.
- Die sechs Dateien der geprüften Sicherung vom 1. November wurden vor und nach der Bereinigung anhand ihrer vollständigen SHA-256-Prüfsummen bestätigt.
- RCON3 und RCON4 liefern weiterhin HTTP 200, `failed: false` und Version `v0.9.3-rc.1`. Die Backends sind gesund.

Die aktuellen Backups unter `/root/hll_rcon_tool/.deploy-state/backup-cleanup-20261101` wurden nicht ersetzt oder entfernt. Es erfolgte kein Eingriff in Datenbanktabellen oder Datenbankdateien. Laufende Anwendungen wurden für diese Bereinigung nicht neu gestartet.

### Separate Änderung durch den Benutzer

Der erste Volume-Vergleich meldete das fehlende, nicht eingebundene Volume `fngh-hll-2464-88_scoreboard_db` der stillgelegten Hosting-Instanz. Der Benutzer bestätigte während der Abschlussprüfung ausdrücklich: „Das war ich. Den hab ich gelöscht“. Diese separate Löschung ist deshalb als erwartete Ausnahme protokolliert und wird nicht als unveränderter Bestand ausgegeben. Kein Volume wurde durch die hier ausgeführten Bereinigungsbefehle gelöscht. Die Bestandsaufnahme hatte dafür zuvor 12.288 Bytes gemeldet; RCON3/4 und ihre Daten-Mounts sind davon nicht betroffen.

Die native Bereinigung hat **55** Einträge der ursprünglichen Auswahl behalten (zusammen 1,11 GB laut vorheriger Engine-Inventur). Sie wurden nicht anschließend manuell entfernt. Die genaue Liste steht in `remaining-cache.json`; die Vorher-/Nachher-Prüfung bestätigt, dass sämtliche außerhalb der ursprünglichen Auswahl liegenden Cache-IDs weiterhin vorhanden sind.

## Nachweise

Privates Serverprotokoll unter `/root/hll_rcon_tool/.deploy-state/cache-snap-cleanup-20261102`: `preflight.json`, `cache-prune-output.txt`, `cache-result.json`, `snap-progress.json`, `snap-result.json`, `snap-cache-review.json`, `snap-cache-result.json`, `verification.json`, die Volume-Diagnose sowie die erhaltenen Snap-Revisionsdaten.

Lokale Ausgaben und Ausführungsskripte: `outputs/cache-snap-cleanup-20261102/`.

Die ursprüngliche Bestandsaufnahme steht in der [Speicheranalyse](server-storage-audit-20261102.md). Andere darin genannte Kandidaten wurden nicht bereinigt.
