# Speicheranalyse des RCON3/4-Hosts – 2. November 2026

Host: `87.106.112.21`. Lesende Bestandsaufnahme ab **02:28 Uhr Europe/Berlin**. Die Dateisysteminventur erfasste die gesamte Root-Partition ohne Fehler. Es wurde in dieser Untersuchung nichts gelöscht, keine Konfiguration geändert und kein Dienst neu gestartet.

## Ergebnis und empfohlene Reihenfolge

Größter kurzfristiger Ansatzpunkt: **130.79 GB** seit mindestens 30 Tagen ungenutzter Docker-Build-Cache, der laut Engine nicht mit Images geteilt wird (2,119 Einträge). Aktuelle Builds und die Nutzdaten laufender Anwendungen sind davon getrennt. Gelöschter Cache muss bei einem späteren Build gegebenenfalls neu aufgebaut werden.

Danach lohnt sich die Auswahl alter, nicht mehr benötigter Docker-Images. Docker meldet dafür rund **56,97 GB** grundsätzlich freigebbaren Speicher. Vor einer Löschung müssen die gewünschten Rückfallversionen und Konfigurationsverweise festgelegt werden. „Kein Container verwendet das Image“ bedeutet allein noch nicht „als Rückfallversion unnötig“.

Weitere Ansatzpunkte sind die Logs der gestoppten Hosting-Instanz 11, alte Releasekopien anderer Anwendungen und ältere Sicherungen. Aktuelle Backups, ungeklärte Datenbankkopien, Testdatenbanken und aktive Konfigurationen bleiben entsprechend der bisherigen Vorgabe erhalten.

| Priorität | Bestand | Größe / Potenzial | Bewertung |
| --- | --- | ---: | --- |
| 1 | Nicht verwendeter, nicht geteilter Build-Cache, zuletzt vor über 30 Tagen genutzt | **130.79 GB** | Sinnvollster erster Bereinigungsschritt; Alter und Nutzung direkt vor Ausführung erneut prüfen. |
| 2 | Docker-Images ohne Containerreferenz | Docker meldet **56,97 GB freigebbar** | Explizite Image-Liste mit Schutz aktueller und gewünschter Rückfallversionen erstellen. Kein pauschales Prune aller Ressourcen. |
| 3 | Logs der gestoppten Instanz 11 (`hll-2464-88`) | **10.27 GB** | Keine laufende Instanz; Altprotokolle nach Aufbewahrungsentscheidung archivieren oder entfernen. Datenbank und Konfiguration behalten. |
| 4 | Naval-Webmap-Releaseordner | **9.94 GB** | 204 Ordner inklusive aktuell verwendeter Version; aktuelle Version und Rückfallstände schützen. |
| 4 | Naval-Webmap-Paketarchive direkt im Anwendungsordner | **8.47 GB** | 230 Archive; junge Bestände, nicht alle veraltet. Abgleich mit benötigten Client-/Serverversionen erforderlich. |
| 5 | Systemjournal | 3,28 GB belegt | Bei einer gewählten Obergrenze von z. B. 1 GB wären grob 2 GB gewinnbar; genaue Freigabe hängt von aktiven Journaldateien ab. |
| 5 | Deaktivierte Snap-Paketrevisionen | **2,61 GB** | 12 als `disabled` markierte alte Revisionen. Über die Paketverwaltung entfernen, aktuelle Revisionen erhalten. |
| 6 | Alte SQLite-Sicherungen des deaktivierten Statistik-Bots | **2.92 GB** | Vier große Sicherungen vom 6. Juli; aktuelle Datenbank und gewünschte Rückfallkopie vorerst behalten. |
| 6 | WordPress-Sicherungen unter `/tmp/fln-wp-direct-backup` | **4.37 GB** | Drei Sicherungszeitpunkte Juli, August und September; kein gewöhnlicher temporärer Cache. Vor Entfernung aktuelle geprüfte WordPress-Sicherung zuordnen. |

Die Tabellenwerte sind keine garantierte Gesamtsumme eines einzelnen Löschvorgangs. Docker-Schichten werden geteilt; gespeicherte Größe und tatsächlich freigebbarer Platz unterscheiden sich. Der Cache-Gesamtwert von 230,5 GB darf insbesondere nicht zusätzlich zu allen Imagegrößen addiert werden.

## Gesamte Speicherverteilung

`df` meldete eine Root-Partition von **1.040,4 GB**, davon **599,4 GB belegt** und **441,0 GB verfügbar** (58 % belegt). `du -x` ermittelte 599,3 GB zugeordnete Blöcke. Die kleine Differenz ist auf dem laufenden Host zu erwarten. Größen in diesem Bericht sind dezimale GB; Unterverzeichnisse sind in ihren Eltern bereits enthalten.

| Hauptverzeichnis | Zugeordneter Speicher (GB) |
| --- | ---: |
| `/var` | 362.27 |
| `/root` | 158.25 |
| `/opt` | 42.22 |
| `/home` | 23.30 |
| `/tmp` | 7.44 |
| `/usr` | 5.58 |
| `/boot` | 0.18 |
| `/etc` | 0.06 |

Wichtigste Unterbereiche von `/var/lib`:

| Pfad | Zugeordneter Speicher (GB) |
| --- | ---: |
| `/var/lib/docker` | 337.22 |
| `/var/lib/snapd` | 5.58 |
| `/var/lib/mysql` | 5.31 |
| `/var/lib/apt` | 0.40 |
| `/var/lib/dpkg` | 0.07 |
| `/var/lib/postgresql` | 0.05 |
| `/var/lib/letsencrypt` | 0.01 |
| `/var/lib/ubuntu-advantage` | 0.01 |

Die Overlay-Mounts laufender Container wurden nicht als eigene zusätzliche Festplatten addiert. Die Prüfung verwendete `du -x`; Docker-Images, Build-Cache, beschreibbare Container-Layer und Volumes wurden ergänzend über die Docker-Engine aufgeschlüsselt.

## Docker im Detail

Offizielle Zusammenfassung von `docker system df`:

| Kategorie | Anzahl | Gesamtgröße laut Docker | Von Docker als freigebbar gemeldet |
| --- | ---: | ---: | ---: |
| Images | 1.457, davon 28 von Containern referenziert | 129,7 GB | 56,97 GB |
| Container | 51, davon 31 laufend | 6,851 GB beschreibbare Layer | 1,259 GB |
| Lokale Volumes | 165, davon 19 referenziert | 8,077 GB | 47,69 MB |
| Build-Cache | 9.947 Einträge | 230,5 GB | 140,3 GB |

Die Engine meldete bei der Momentaufnahme keinen Cache-Eintrag als `InUse`. Von den 230,5 GB Cache sind 90,24 GB mit Images geteilt und 140,26 GB nicht geteilt. Nach dem letzten Nutzungsdatum verbleiben folgende konservativere Altersgruppen:

| Mindestalter seit letzter Nutzung | Einträge, ungenutzt und nicht geteilt | Größe (GB) |
| --- | ---: | ---: |
| 7 Tage | 2,618 | 137.65 |
| 14 Tage | 2,324 | 132.53 |
| 30 Tage | 2,119 | 130.79 |
| 60 Tage | 1,929 | 115.97 |

Die Altersgruppen überlappen und dürfen nicht addiert werden. Kurz vor der Bestandsaufnahme liefen neue Builds; deshalb ist der Schutz junger und dann erneut aktiv benutzter Einträge erforderlich.

**Volumes sind kein nennenswerter Aufräumhebel:** Das große Modell-Volume (4,68 GB) ist aktiv referenziert. Nextcloud-Daten (2,82 GB), WordPress-Daten und eine Testdatenbank gehören zu gestoppten, aber vorhandenen Containern. Sie werden nicht als Datenmüll eingestuft. Das unreferenzierte `hll-geofences_dbdata` enthält nur rund 48 MB und bleibt als ungeklärte Datenbank erhalten.

**Container-Logs:** rund 0,38 GB. In den geprüften Container-Metadaten fehlen explizite `max-size`/`max-file`-Angaben. Eine Größenbegrenzung wäre für zukünftiges Wachstum sinnvoll; hier liegt aktuell kein großer Speichergewinn.

## Anwendungslogs und Historie

| Bestand | Größe (GB) | Einordnung |
| --- | ---: | --- |
| `/root/hll_rcon_tool/logs` | 6.08 | Laufende RCON3/4-Protokolle; nicht pauschal löschen. |
| `/opt/frontline-hosting/instances/11/logs` | 10.27 | Gestoppte Instanz, letzte große Logänderungen am 18. Oktober. |
| `/opt/frontline-hosting/instances/12/logs` | 3.19 | Aktive Atomaresecho-Instanz; Logrotation vorsehen. |
| `/var/log` | 3.86 | System- und Dienstlogs inklusive Journal. |

Besonders groß sind `live_stats_loop_1.log` der Instanz 11 (6,84 GB), ihr `log_event_loop_1.log` (2,85 GB) sowie die RCON3/4-Dateien `log_event_loop_3.log` (2,69 GB) und `log_event_loop_4.log` (1,60 GB).

In den geprüften `/etc/logrotate.d`-Dateien wurde keine Zuordnung zu den beiden RCON-Logpfaden gefunden. Der lokale Anwendungsquellcode konfiguriert `logging.FileHandler`. Das spricht für eine gesonderte Größen-/Aufbewahrungsregel; vor einer Umsetzung muss die tatsächlich eingesetzte Logging-Konfiguration berücksichtigt werden. Alte Reparatur- und Moderationsbelege sollen erhalten bleiben.

Die aktive RCON-Datenbank umfasst rund **25,26 GB**. Die größten Tabellen, jeweils einschließlich Indizes und TOAST-Daten:

| Tabelle | Größe (GB) |
| --- | ---: |
| `log_lines` | 16.51 |
| `autobalance_snapshots` | 2.55 |
| `autobalance_player_role_stats` | 1.73 |
| `audit_log` | 1.59 |
| `player_stats` | 1.32 |
| `steam_info` | 0.27 |
| `tactical_block` | 0.22 |

Das sind aktive Log-, Audit- und Statistikdaten, keine entbehrlichen Sicherungen. Rund 20,8 Millionen geschätzte Logzeilen erklären einen erheblichen Teil der Datenbankgröße. Ein möglicher späterer Abbau benötigt eine eigene Aufbewahrungsentscheidung und einen Datenbank-Wartungsplan. Ein sofort freigebbarer Betrag wird dafür nicht zugesichert.

## Große Sicherungs- und Altbestände

Diese Bestände bleiben in dieser Analyse geschützt. Bei einer späteren Einzelprüfung muss geklärt werden, welche historischen Daten oder Wiederherstellungsmöglichkeiten benötigt werden.

| Pfad | Größe (GB) | Hinweis |
| --- | ---: | --- |
| `/root/test` | 24.61 | Alte Testinstallationen und Datenbanken; bisher ausdrücklich behalten. |
| `/root/hll_rcon_tool_backup` | 12.88 | Alte vollständige Installations-/Datenbankkopie. |
| `/root/hll_rcon_tool-backup-c9a2d8fc-20260808` | 8.94 | Alte Installation samt Daten und lokalen Änderungen. |
| `/root/backups` | 23.33 | Gemischte Sicherungen, darunter WordPress und RCON. |
| `/root/crcon-backups` | 8.94 | Überwiegend ältere VIP-Wiederherstellungsdaten. |
| `/root/hll_rcon_tool-backups` | 2.57 | Bei der vorherigen Bereinigung bewusst zurückgestellte Sicherungen. |
| `/root/crcon-deploy-backups` | 2.04 | Alte Datenbank-Dumps vor/nach Reparaturen. |
| `/root/frontline-backups` | 1.48 | Gemischte Sicherungen. |
| `/root/frontline-rcon-vip-a27010d` | 1.69 | Enthält eine Datenbanksicherung, keine reine Build-Kopie. |
| `/var/backups` | 5.16 | Vorwiegend frühere Website-/Hosting-Änderungssicherungen. |
| `/tmp/fln-wp-direct-backup` | 4.37 | WordPress-Dumps und Archive unter einem temporären Pfad. |
| `/root/hll_rcon_tool/.deploy-state` | 32.88 | Aktuelle und bewusst behaltene Wiederherstellungspunkte; bestehende Vorgaben beachten. |

Die drei alten Installations-/Testdatenbankbestände (`/root/test`, `/root/hll_rcon_tool_backup`, `/root/hll_rcon_tool-backup-c9a2d8fc-20260808`) belegen zusammen **46,43 GB**. Für diese Pfade wurden bei den geprüften Dienst-, Container- und Prozessreferenzen keine aktuellen Verwendungen gefunden. Sie bleiben dennoch ungeklärte Datensicherungen und sind nicht zur Löschung freigegeben.

Die frische, bereits geprüfte Sicherung vom 1. November liegt weiterhin unter `/root/hll_rcon_tool/.deploy-state/backup-cleanup-20261101`. Die vorangegangenen Bereinigungen sind in den [Backup-](rcon34-backup-cleanup-20261101.md) und [Versionsbereinigungsprotokollen](rcon34-root-version-cleanup-20261102.md) dokumentiert. Deren bereits gelöschte Dateien sind in den jetzigen Größen nicht mehr enthalten.

## Weitere Anwendungen und temporäre Dateien

- **Naval-Webmap:** insgesamt rund 20,98 GB. Davon 9,94 GB in 204 Releaseordnern und 8,47 GB in 230 direkt abgelegten Paketarchiven. `current` zeigt auf `releases/0.3.192`; der laufende Container referenziert den Releasebaum. Daten und Downloads sind aktiv eingebunden. Die Paketarchive sind sämtlich jünger als 30 Tage; 85 Archive mit 2,22 GB sind älter als 14 Tage. Es ist eine Versionsauswahl nötig, keine Löschung des gesamten Ordners.
- **Statistik-Discord-Bot:** rund 4,07 GB, darunter 2,92 GB Sicherungen und eine aktuelle SQLite-Datei mit 1,11 GB. `fln-stats.service` ist deaktiviert/inaktiv, verweist aber weiterhin auf diese Installation. Die eigentliche Statistikdatenbank bleibt erhalten.
- **`/tmp`:** rund 7,44 GB. Davon 4,37 GB WordPress-Sicherungen; daneben alte Theme-Staging-Verzeichnisse und RCON-OCI-Archive. Ein laufender Nginx-Container bindet außerdem eine Konfigurationsdatei unter `/tmp` ein. Pauschales Leeren wäre daher falsch.
- **`/home`:** rund 23,30 GB. Ein großer Teil gehört zur aktiven Steam-/Collector-Umgebung; außerdem liegen dort weitere Projekt-, Cache- und Website-Sicherungen. Eine weitere Bereinigung ist nur je Anwendung sinnvoll.
- **`/var/www`:** rund 4,05 GB, überwiegend Webseitenbestand. Keine pauschale Bereinigung empfohlen.
- **System-Caches:** `/var/cache` nur rund 0,23 GB. Kein wesentlicher Hebel.
- **Snap-Pakete:** `/var/lib/snapd` belegt 5,58 GB. Davon entfallen 2,61 GB auf zwölf deaktivierte Paketrevisionen; die Paketverwaltung kann diese gezielt entfernen. Aktuelle Revisionen und deren Daten bleiben erhalten.
- **MariaDB/MySQL:** `/var/lib/mysql` belegt 5,31 GB, überwiegend aktive Website-Datenbanken. Binärlogging ist abgeschaltet; es gibt keinen alten Binärlog-Bestand zum Aufräumen. Die Dateisystemgrößen liegen deutlich über den vom Tabellenkatalog gemeldeten Größen. Ob und wie viel davon eine Datenbankwartung zurückgewinnen könnte, wurde nicht festgestellt; keine direkte Dateilöschung empfohlen.
- **Bereits gelöschte, noch offene Dateien:** nur ungefähr 0,10 GB über verschiedene Prozesse/Dateisysteme. Kein Anlass, laufende Dienste allein dafür neu zu starten.

## Vorgehen für die nächste Bereinigung

1. Nach Freigabe zuerst den alten, unbenutzten Build-Cache über Docker bereinigen; mindestens die letzten 30 Tage und inzwischen wieder benutzte Einträge schützen.
2. Danach eine konkrete Image-Liste aus den nicht referenzierten Images erstellen; aktuelle und benötigte Rückfallstände schützen.
3. Für die alte Instanz 11 eine Aufbewahrungsentscheidung für die Logs treffen. Datenbank und Konfiguration davon getrennt behandeln.
4. Für Naval-Webmap eine begrenzte Anzahl getesteter Releases/Pakete behalten; andere Dienste und Nutzer nicht mit pauschalen Löschregeln erfassen.
5. Logrotation sowie feste Cache-/Release-Aufbewahrung einführen. Datenbank- und historische Backup-Bereinigung erst danach gesondert planen.

## Nachweise und Grenzen

Lesend geprüft wurden: Dateisystembelegung und Inodes, `du -x` auf der gesamten Root-Partition, Docker-Engine-Speicherstatistik und `docker system df`, Container-Mounts und Compose-Pfade, Dienst-/Cron-/Logrotate-Verweise, Prozesslinks, Snap-Revisionsstatus, MariaDB-Metadaten und PostgreSQL-Datenbank-/Tabellengrößen in `READ ONLY`-Transaktionen. Es wurden keine Spieler- oder Chatdatensätze ausgelesen.

Rohinventuren, Größenlisten und Kandidaten-IDs liegen lokal unter `outputs/server-storage-audit-20261102/`. Die Größen wurden während des laufenden Betriebs erfasst und sind Momentaufnahmen. Nicht jeder alte Bestand ist entbehrlich; insbesondere ältere Sicherungen anderer Anwendungen wurden hier nicht wiederhergestellt oder vollständig inhaltlich verglichen. Die Analyse selbst enthält keine Ausrollung oder Löschung.
