# RCON3/4: alte Versionen unter /root – Prüfung vom 2. November 2026

**Nachtrag:** Die anschließend ausdrücklich freigegebenen 52 Ordner und 34 Archive wurden am selben Tag entfernt. Durchführung und Nachkontrolle stehen im [Bereinigungsprotokoll](rcon34-root-version-cleanup-20261102.md). Die folgende Bestandsaufnahme beschreibt den Zustand vor der Löschung.

Host: `87.106.112.21`. Inventur ab **01:16 Uhr Europe/Berlin**. Ausschließlich lesende Prüfung; keine Serverdateien gelöscht oder geändert, keine Dienste neu gestartet.

## Ergebnis

**52 Versions-/Build-Ordner und 34 RCON-Paketarchive** sind Kandidaten für eine weitere Bereinigung. Für diese Pfade wurde in den unten beschriebenen Prüfungen keine aktive Nutzung gefunden. Die Ordner enthalten historische Builds mit jüngsten Dateizeitstempeln zwischen dem 13. August und dem 5. September 2026.

| Kategorie | Anzahl | Zugeordneter Speicher |
| --- | ---: | ---: |
| Versions-/Build-Ordner | 52 | 3,483,820,032 Bytes (3.24 GiB) |
| RCON-Paketarchive | 34 | 1,189,888,000 Bytes (1.11 GiB) |

Die Summe beträgt **4,673,708,032 Bytes**. Nach Berücksichtigung von Hardlinks zu beibehaltenen Dateien sind voraussichtlich **4,570,099,712 Bytes (4,57 GB / 4.26 GiB)** freigebbar. Das ist eine Schätzung anhand der zugeordneten Dateisystemblöcke, kein gemessener Löschgewinn.

Diese Liste ist eine Bestandsaufnahme und keine ausgeführte oder pauschal freigegebene Löschung. Vor einer späteren Bereinigung müssen Nutzung und Dateistand erneut geprüft werden. Neueste Backups, aktive Konfigurationen, unklare Sicherungen und alte Testdatenbanken bleiben erhalten.

## Unbedingt beibehalten

- `/root/hll_rcon_tool`: aktive Installation, einschließlich aktueller Rollback-/Sicherungsdaten.
- `/root/hll_rcon_tool-data`: aktiv eingebundene Daten.
- `/root/frontline-rcon-perf-00a57098`: Trotz altem Build-Namen verweist der laufende Container `hll_rcon_tool-redis-1` in seinen Compose-Metadaten auf `rcon1-performance-canary.override.yaml` in diesem Ordner. Der Pfad muss für die Wiederherstellung der Compose-Konfiguration erhalten bleiben. Vorsorglich ist auch das zugehörige `/root/frontline-rcon-perf-00a57098.tar` aus der Kandidatenliste ausgeschlossen.

## Alte Versionsordner mit noch ungeklärten Codebeständen

Bei zwölf direkten Git-Arbeitskopien konnte die Redundanz nicht belegt werden: fehlende/ungültige Git-Metadaten, lokale Änderungen oder ein Commit, der im Git-Objektbestand der aktiven Installation nicht vorhanden ist. Nicht vorhanden bedeutet hier nicht automatisch unveröffentlicht; es wurde kein Remote-Abgleich vorgenommen.

Zusätzlich bleiben die beiden Sammelordner `/root/hll_rcon_tool-builds` und `/root/releases` vollständig außerhalb der Kandidatenliste. Die tiefere Prüfung fand unter anderem:

- `hll_rcon_tool-builds/simplify-preview`: 17 Änderungen an versionierten Dateien und zwei unversionierte Dateien.
- `releases/hll_rcon_tool-player-records-5264e51d`: 28 Änderungen an versionierten Dateien und drei unversionierte Dateien.
- Weitere verschachtelte Arbeitskopien mit unversionierten Dateien oder nicht im aktiven Git-Objektbestand nachweisbaren Commits.

| Vorläufig beibehaltene Arbeitskopie / Sammlung | Belegter Speicher (MiB) |
| --- | ---: |
| `/root/frontline-rcon-build-v0.4.9-ec6d4d1c` | 41.1 |
| `/root/frontline-rcon-build-v0.4.9.2-474c994e` | 41.1 |
| `/root/frontline-rcon-perf-6fa6e3c4` | 38.7 |
| `/root/frontline-rcon-perf-bb2a00d4` | 38.7 |
| `/root/frontline-rcon-perf-f2ed6c8a` | 40.7 |
| `/root/frontline-rcon-release-v0.3.2` | 38.4 |
| `/root/frontline-rcon-release-v0.3.7` | 104.8 |
| `/root/frontline-rcon-release-v0.3.8` | 38.5 |
| `/root/frontline-rcon-release-v0.3.9` | 38.5 |
| `/root/frontline-rcon-release-v0.4.7` | 40.7 |
| `/root/frontline-rcon-release-v0.4.7.1` | 40.7 |
| `/root/hll_rcon_tool-builds` | 1575.4 |
| `/root/hll_rcon_tool.pre-v0.4.10-20260824T192239Z` | 336.8 |
| `/root/releases` | 254.0 |

## Große Verzeichnisse, die keine reinen Versionskopien sind

Diese Verzeichnisse enthalten Datenbanken, Sicherungen oder Bestände anderer Dienste. Ihr Alter allein ist kein ausreichender Löschgrund.

| Pfad | Belegter Speicher (GiB) | Befund |
| --- | ---: | --- |
| `/root/test` | 22.92 | Alte Testinstallationen und Datenbanken; entsprechend bisheriger Vorgabe erhalten. |
| `/root/backups` | 21.72 | Gemischte Sicherungen, darunter WordPress und Datenbanksicherungen. |
| `/root/hll_rcon_tool_backup` | 11.99 | Alte Installations-/Datenbankkopie. |
| `/root/crcon-backups` | 8.33 | Überwiegend VIP-Wiederherstellungsdaten. |
| `/root/hll_rcon_tool-backup-c9a2d8fc-20260808` | 8.32 | Alte Installation samt Daten und lokalen Änderungen. |
| `/root/crcon-deploy-backups` | 1.90 | Datenbank-Dumps vor und nach früheren Reparaturen. |
| `/root/frontline-rcon-vip-a27010d` | 1.57 | Enthält eine PostgreSQL-Sicherung von ca. 1,69 GB; keine bloße Versionskopie. |
| `/root/frontline-backups` | 1.37 | Gemischte ältere Sicherungsbestände. |
| `/root/service11-upgrade-v085-20260917` | 0.10 | Upgrade-Sicherung einer anderen Instanz samt Datenbank. |
| `/root/service11-upgrade-v087-20260920` | 0.06 | Upgrade-Sicherung einer anderen Instanz samt Datenbank. |
| `/root/service11-upgrade-v086-20260917` | 0.05 | Upgrade-Sicherung einer anderen Instanz samt Datenbank. |

Außerdem bleiben `/root/hll_rcon_tool.tar.gz` (2,42 GiB; Inhalt in dieser Prüfung nicht untersucht), zwei Git-Bundles sowie die bisher geschützten Sicherungsordner erhalten. Bei den großen Altbeständen ist eine spätere gesonderte Bewertung möglich; diese Größen werden nicht als bereits freigebbarer Speicher ausgegeben.

Im Root liegen auch **103 `frontline-network-*`-Pakete**, **46 `frontline-content-core-*`-Pakete** und **3 `frontline-gamehost-control-*`-Pakete** (zusammen rund 185 MiB). Diese gehören nicht zur hier geprüften RCON-Paketliste; ein Abgleich mit den zugehörigen Installationen wurde nicht vorgenommen.

## Prüfung und Grenzen

- 653 direkte Einträge unter `/root` inventarisiert; Verzeichnisgrößen über `du -x` erfasst.
- Laufende und gestoppte Docker-Container auf Bind-Mounts, Compose-Dateien und Compose-Arbeitsverzeichnisse geprüft.
- Dienst-/Cron-/Proxy-Konfigurationen sowie aktuelle Prozess-Arbeitsverzeichnisse, Programme und offene Dateien auf Verweise geprüft; keine Konfigurationsinhalte oder Zugangsdaten ausgegeben.
- Kandidaten rekursiv auf Datenbankdateien und Git-Arbeitskopien geprüft. Bei den beibehaltenen 52 Kandidaten wurden in vorhandenen Git-Arbeitskopien keine lokalen Änderungen gefunden; ihre HEAD-Commits sind im Git-Objektbestand der aktiven Installation vorhanden. Reine Quellcodeexporte ohne Git-Metadaten wurden als solche eingeordnet.
- Inhaltsverzeichnisse der ausgewählten RCON-Archive und Archive innerhalb der Kandidaten gelesen, ohne Extraktion. Keine Datenbank-Dumps oder Redis-Snapshots anhand der geprüften Dateimarker gefunden. Das ist keine vollständige Wiederherstellungs- oder Integritätsprüfung.
- Hardlinks über Geräte-/Inode-Kennungen gezählt. Dateien mit verbleibenden Links außerhalb der Kandidaten sind vom erwarteten Speichergewinn abgezogen.
- Kein Git-Fetch, kein Docker-Prune, keine Datenbankänderung und kein Löschvorgang. Historische manuelle Skripte oder dynamisch zusammengesetzte Pfade können zusätzliche Verweise enthalten; die Aussage lautet daher „keine Nutzung in den geprüften Quellen gefunden“.

Private Rohinventuren, Detailprüfungen und Metadaten liegen lokal unter `outputs/rcon34-root-audit-20261102/`. Die aktuelle geprüfte Sicherung vom Vortag ist im [Bereinigungsprotokoll vom 1. November](rcon34-backup-cleanup-20261101.md) dokumentiert.

## Vollständige Kandidatenliste

### Versions-/Build-Ordner

| Pfad | Belegter Speicher (MiB) |
| --- | ---: |
| `/root/crcon-release-dbddbca7828a` | 131.8 |
| `/root/frontline-builds` | 140.0 |
| `/root/frontline-rcon-build-v0.4.1-69593e73` | 40.9 |
| `/root/frontline-rcon-build-v0.4.1-beba9ebd` | 40.9 |
| `/root/frontline-rcon-build-v0.4.1-e2155b99` | 40.9 |
| `/root/frontline-rcon-build-v0.4.2-6d0ac7bc` | 40.9 |
| `/root/frontline-rcon-build-v0.4.2-fd41ba94` | 40.9 |
| `/root/frontline-rcon-build-v0.4.3-e7cb8c26` | 40.9 |
| `/root/frontline-rcon-canary-505101e0` | 41.2 |
| `/root/frontline-rcon-canary-builds` | 120.2 |
| `/root/frontline-rcon-canary-pr237-4425244da872` | 59.7 |
| `/root/frontline-rcon-canary-pr237-4772602850ce` | 58.0 |
| `/root/frontline-rcon-canary-pr237-619a4a369562` | 59.8 |
| `/root/frontline-rcon-canary-pr237-d5bd0afd3716` | 59.7 |
| `/root/frontline-rcon-canary-pr237-ef7c1301ad7a` | 58.0 |
| `/root/frontline-rcon-deploy-28a3ec9c` | 134.5 |
| `/root/frontline-rcon-deploy-472f85a6` | 134.5 |
| `/root/frontline-rcon-deploy-ab67c302` | 134.5 |
| `/root/frontline-rcon-frontend-build-v0.3.8` | 38.8 |
| `/root/frontline-rcon-frontend-full-v0.3.8-v2` | 131.3 |
| `/root/frontline-rcon-hll-pr238-1a6342d98f8e` | 58.1 |
| `/root/frontline-rcon-hll-pr238-1c411a5ea717` | 58.1 |
| `/root/frontline-rcon-perf-0029fdee` | 38.6 |
| `/root/frontline-rcon-perf-0ceee66a` | 38.5 |
| `/root/frontline-rcon-perf-0e95d12f` | 38.5 |
| `/root/frontline-rcon-perf-1cab0660` | 38.6 |
| `/root/frontline-rcon-perf-23d581d9` | 38.5 |
| `/root/frontline-rcon-perf-41475e4d` | 38.6 |
| `/root/frontline-rcon-perf-585609e9` | 38.6 |
| `/root/frontline-rcon-perf-662dea46` | 38.6 |
| `/root/frontline-rcon-perf-663fa55f` | 38.6 |
| `/root/frontline-rcon-perf-898563b7` | 38.5 |
| `/root/frontline-rcon-perf-94b43f5c` | 41.2 |
| `/root/frontline-rcon-perf-a79487f6` | 38.6 |
| `/root/frontline-rcon-perf-ad8a9895` | 38.6 |
| `/root/frontline-rcon-perf-c23d2ae0` | 38.5 |
| `/root/frontline-rcon-perf-c9203568` | 38.6 |
| `/root/frontline-rcon-perf-d4d19aa5` | 38.6 |
| `/root/frontline-rcon-perf-d761ffa4` | 38.6 |
| `/root/frontline-rcon-perf-de8d3ee0` | 38.6 |
| `/root/frontline-rcon-perf-efd93034` | 38.6 |
| `/root/frontline-rcon-perf-f702ac0d` | 38.6 |
| `/root/frontline-rcon-perf-ff33e7a8` | 38.6 |
| `/root/frontline-rcon-release-build-v0.3.2` | 139.1 |
| `/root/frontline-rcon-release-v0.6.4-e15229728ee0` | 58.2 |
| `/root/frontline-rcon-v0.4.1-eaa9787b` | 40.9 |
| `/root/frontline-rcon-v0.4.5-build.mFOcWQ` | 65.8 |
| `/root/frontline-rcon-version-fix-7e026671` | 62.9 |
| `/root/hll_rcon_releases` | 176.8 |
| `/root/hll_rcon_tool-build-a232d756` | 37.9 |
| `/root/hll_rcon_tool-build-cc699744` | 130.8 |
| `/root/hll_rcon_tool-build-e4a6ade3` | 133.4 |

### RCON-Paketarchive

| Pfad | Belegter Speicher (MiB) |
| --- | ---: |
| `/root/frontline-rcon-94b43f5c.tar.gz` | 27.4 |
| `/root/frontline-rcon-f2ed6c8a.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-0ceee66a.tar` | 35.1 |
| `/root/frontline-rcon-perf-0e95d12f.tar` | 35.1 |
| `/root/frontline-rcon-perf-1cab0660.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-23d581d9.tar` | 35.1 |
| `/root/frontline-rcon-perf-662dea46.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-6fa6e3c4.tar` | 35.1 |
| `/root/frontline-rcon-perf-898563b7.tar` | 35.1 |
| `/root/frontline-rcon-perf-a79487f6.tar` | 35.1 |
| `/root/frontline-rcon-perf-ad8a9895.tar` | 35.1 |
| `/root/frontline-rcon-perf-bb2a00d4.tar` | 35.1 |
| `/root/frontline-rcon-perf-c23d2ae0.tar` | 35.1 |
| `/root/frontline-rcon-perf-c9203568.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-d4d19aa5.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-d761ffa4.tar.gz` | 27.4 |
| `/root/frontline-rcon-perf-ff33e7a8.tar.gz` | 27.4 |
| `/root/frontline-rcon-suite-v0.4.1-69593e73.tar` | 37.3 |
| `/root/frontline-rcon-suite-v0.4.1-e2155b99.tar` | 37.3 |
| `/root/frontline-rcon-v0.4.1-beba9ebd.tar.gz` | 28.7 |
| `/root/frontline-rcon-v0.4.1-eaa9787b.tar.gz` | 28.7 |
| `/root/frontline-rcon-v0.4.2-6d0ac7bc.tar` | 37.3 |
| `/root/frontline-rcon-v0.4.2-fd41ba94.tar` | 37.3 |
| `/root/frontline-rcon-v0.4.3-e7cb8c26.tar` | 37.3 |
| `/root/map-navigation-c0136be0.tar` | 36.5 |
| `/root/payload-c61a2102.tar` | 36.6 |
| `/root/perf-0029fdee.tar` | 35.1 |
| `/root/perf-41475e4d.tar` | 35.1 |
| `/root/perf-585609e9.tar` | 35.1 |
| `/root/perf-663fa55f.tar` | 35.1 |
| `/root/perf-de8d3ee0.tar` | 35.1 |
| `/root/perf-efd93034.tar` | 35.1 |
| `/root/perf-f702ac0d.tar` | 35.1 |
| `/root/polling-679c1051.tar` | 36.5 |
