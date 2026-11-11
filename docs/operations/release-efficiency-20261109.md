# Kleineres Backend-Paket und geprüfter Update-Pfad

Prüfstand: 9. November 2026. Ausgangsversion: **v0.9.3**. Es wurde kein Release
veröffentlicht und kein produktiver Dienst aktualisiert.

Das Backend-Image ist im vergleichbaren Build **41,65 % kleiner**. Der Wechsel
vom tatsächlich veröffentlichten v0.9.3-Image zum Kandidaten, ein zweiter
Update-Durchlauf und der anschließende Code-Rollback wurden mit einer
wiederhergestellten Bestandsdatenbank erfolgreich geprüft. Zusätzlich wurden
eine synthetische HLL-Installation und eine frische HLLV-Installation geprüft.

## Ausgangsmessung unter laufender Nutzung

Zeitraum: **21:21–21:51 Uhr Europe/Berlin**, 91 Messpunkte im Abstand von
20 Sekunden. Prozessspeicher wurde zusätzlich jede Minute aus Linux-PSS
ermittelt; gemeinsam genutzte Speicherseiten werden dabei anteilig gezählt.
Erfasst wurden die RCON3/4-Container und ihre gemeinsamen Datenbank-, Redis-,
Webhook-, Hintergrund- und Discord-Dienste. Das ist keine Messung des gesamten
Hosts und kein künstlicher Lasttest. Builds und Wiederherstellung begannen erst
nach Abschluss dieser Messung.

- RCON3: 60 Spielerzahlmessungen, **93–98 Spieler**, Mittelwert 97,65; keine
  fehlgeschlagenen Spielerzahlmessungen.
- RCON4: ebenfalls 60 erfolgreiche Messungen, durchgehend **0 Spieler**.
- Gesamt-PSS der erfassten Prozesse: durchschnittlich **3,23 GiB**.
- Gesamt-CPU: durchschnittlich **0,928 CPU-Kerne**. Das entspricht ungefähr
  93 % eines einzelnen Kerns, nicht 93 % des gesamten Hosts.
- PostgreSQL: 32 bzw. 31 Verbindungen an den beiden Messgrenzen, jeweils keine
  offene inaktive Transaktion; keine hinzugekommenen Deadlocks.
- Alle Container-IDs und Neustartzähler blieben während der Messung gleich.

| Prozessgruppe | Mittlerer PSS |
| --- | ---: |
| Web-Backend RCON3 | 319,8 MiB |
| Web-Backend RCON4 | 311,9 MiB |
| Supervisor-Prozesse RCON3 | 876,9 MiB |
| Supervisor-Prozesse RCON4 | 628,5 MiB |
| Gemeinsames Redis | 541,4 MiB |
| RCON-PostgreSQL | 206,4 MiB |
| Gemeinsamer Hintergrundarbeiter | 164,8 MiB |
| Discord-Dienst | 136,5 MiB |

PostgreSQL verarbeitete im Intervall 89.373 Transaktionen. Der kumulierte Zähler
für temporäre Abfragedateien nahm um **273,25 MiB** zu. Das ist kein entsprechend
dauerhaft belegter zusätzlicher Speicherplatz und allein kein Nachweis eines
Engpasses. Für spätere Laufzeitoptimierung sollten die dafür verantwortlichen
Abfragen und die Hintergrundprozesse gezielt gemessen werden. Diese Änderung
nimmt keine Datenbankbereinigung oder neue Aufbewahrungsregel beim Kunden vor.

## Vergleich des Backend-Pakets

Beide Builds verwendeten denselben endgültigen Quellstand, dieselben unveränderten
Dependency-Locks und dasselbe Python-Basisimage. Die bisherige Dockerfile wurde
nur für die gemeinsame Basisimage-Auswahl parametrisiert. Gemessen wurde die
unkomprimierte Docker-Image-Größe auf Linux/amd64:

| Messwert | Bisherige Paketstruktur | Schlanke Paketstruktur |
| --- | ---: | ---: |
| Image-Größe | 510.404.641 Byte | 297.833.892 Byte |
| Image-Größe in MiB | 486,76 MiB | 284,04 MiB |
| Installierte Python-Pakete | 95 | 95, identische Versionen |
| `pip check` | bestanden | bestanden |

Ersparnis: **212.570.749 Byte bzw. 41,65 %**. Das ist keine Messung der
komprimierten Registry-Downloadgröße. Buildzeiten und der von BuildKit gemeldete
Kontexttransfer werden wegen geteilter Caches nicht als Leistungsgewinn gewertet.

Die wesentlichen Änderungen:

- Git wird nur in einer separaten Build-Stufe für die unveränderlich referenzierte
  VCS-Abhängigkeit installiert. Das Laufzeitimage enthält es nicht mehr.
- Das Laufzeitimage behält Cron, Logrotate, Procps und alle bisherigen
  Python-Abhängigkeiten. Nicht erforderliche APT-Empfehlungen und Paketlisten
  werden nicht mitgeliefert.
- Eine eigene `Dockerfile.dockerignore` und ausdrückliche `COPY`-Anweisungen
  begrenzen das Backend auf seine Laufzeitdateien. Frontend-Quellen, große
  Grafikbestände, separate Anwendungen und Entwicklungsdateien entfallen dort.
- Django-Templates, statische Admin-Dateien, Migrationen, Gesundheitsprüfung,
  Release-Prüfscripte und gebündelte Release-Hinweise bleiben enthalten.
- Die gemeinsame `.dockerignore` und die separate Frontend-Dockerfile bleiben
  unverändert. Kundenkonfigurationen werden weiterhin außerhalb des Images
  bereitgestellt.

Basisimage für diesen Vergleich:
`python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b`.

| Image | Lokale Prüf-ID |
| --- | --- |
| Echtes v0.9.3-Ausgangsimage | `7a81b13da66f8be2cc27b34cc1ebec8f6b5a34b30be31dbad3060cd6b515d1bd` |
| Vergleich mit bisheriger Verpackung | `a7f36bbdf38895b554e3d22a36667bababaa884994ac25ceb6b49eb2f1cc1df3` |
| Endgültiger Kandidat | `c25a4d8ded8cb30e0a9ed048b063d355705ad65a5866837b97b176ce9a9a33d1` |

## Erfolgreiche Update- und Neuinstallationsprüfungen

Die [wiederholbare Testumgebung](isolated-upgrade-rehearsal.md) verwendet eigene
PostgreSQL-/Redis-Container ohne externes Netzwerk oder veröffentlichte Ports.
Die Bestandskopie stammt aus dem zusammengehörigen PostgreSQL-/Redis-Backup
`hotfix-live-ui-20261109`; beide SHA-256-Prüfsummen wurden vor der Wiederherstellung
bestätigt. Die Originaldateien waren ausschließlich lesend eingebunden.

| Fall | Ergebnis |
| --- | --- |
| Wiederhergestellter Bestand, HLLV, getrennte HTTP-/WebSocket-Prozesse | v0.9.3 → Kandidat → Kandidat erneut → v0.9.3: bestanden |
| Synthetischer Bestand, HLL, gemeinsamer API-Prozess | v0.9.3 → Kandidat → Kandidat erneut → v0.9.3: bestanden |
| Leere Datenbanken, HLLV, gemeinsamer API-Prozess | Kandidat direkt installiert, Migrationen und API-Prüfungen bestanden |
| Maintenance-/Start- und Testumgebungs-Schutztests | 8 bestanden |
| Django-Migrationsregressionen | 2 bestanden |
| Struktur des neuen GitHub-Testworkflows | erfolgreich geprüft |
| Laufzeitbefehle, native Python-Importe, 17 erforderliche Dateien | in beiden Vergleichsimages vorhanden und geprüft |
| Gebündelte v0.9.3-Hinweise und v0.9.0-Featureankündigung | in beiden Vergleichsimages geprüft |

Jede vollständig gestartete Prüfphase durchlief zwölf HTTP-Prüfungen sowie die
Ablehnung eines nicht authentifizierten Barricade-WebSockets. Abgedeckt wurden
u. a. Anmeldung, Sitzung, API-Key, ungültiger API-Key, Admin-Startseite,
Anzeigepräferenzen, Live-Protokoll, fehlendes CSRF-Token und fehlende Kick-Rechte.
Es wurde kein echter Spieler gekickt oder benachrichtigt.

Für den Bestand blieben die Inhaltsprüfsummen von **21 Tabellen** identisch,
darunter Kundenbenutzer einschließlich Passwort-Hashes, Gruppen, Rechte,
API-Schlüssel, Anzeigeeinstellungen, Update-Bestätigungen, Discord-Anbindung,
Serverkonfiguration, VIPs, Sperrlisten, Markierungen und Nachrichtenvorlagen.
Auch die Django-/Alembic-Migrationshistorie blieb unverändert.

Zusätzlich wurden unveränderte Zeilenzahlen in zwölf Tabellen bestätigt, u. a.:

- 21.024.359 Protokolleinträge;
- 1.738.883 Rundenstatistikeinträge;
- 1.099.005 Spielersitzungen;
- 495.586 Spielermaßnahmen in `players_actions`;
- 1.236 Reports und 5.221 Report-Ereignisse.

Die Benutzerzeile des künstlichen Testbenutzers und ausschließlich seine neu
erzeugten Audit-Einträge sind vom Bestandsvergleich ausgenommen. Diese Test-Audits
wurden nicht gelöscht.
Für große Spiel-/Protokolltabellen sind Zeilenzahlen kein vollständiger
Inhaltsvergleich. Gespeicherte Integrationswerte wurden unverändert verglichen;
ihre Entschlüsselung mit dem Kundenschlüssel und externe Zustellungen wurden
nicht getestet, da die Testumgebung einen eigenen Schlüssel und kein externes
Netzwerk verwendet.

Beim wiederhergestellten Bestand wurde die Web-Bereitschaft mit dem alten Image
nach 28,21 Sekunden und mit dem Kandidaten nach 28,43 Sekunden erreicht. Die
zweite Aktualisierung benötigte 30,84 Sekunden, der Rückweg 28,19 Sekunden.
Diese einzelnen, ressourcenbegrenzten Beobachtungen belegen **keine Beschleunigung
der laufenden API**. Nachgewiesen sind das kleinere Paket und der geprüfte
Update-Pfad.

## Abschluss und verbleibende Release-Abnahme

Alle drei eigenen Testumgebungen, ihre Wegwerfvolumes, vier Vergleichsimages und
der Build-Arbeitsordner wurden anschließend entfernt. Originalbackups und
Prüfbelege bleiben erhalten. Die produktiven Container-IDs, Images und
Neustartzähler waren unverändert; die öffentlichen Authentifizierungs-Endpunkte
von RCON3 und RCON4 antworteten abschließend jeweils erfolgreich mit HTTP 200.

Private Belege liegen unter
`/root/hll_rcon_tool/.deploy-state/release-efficiency-20261109/`:
`baseline-enriched.json`, `build-results.json`, die beiden `verified.json`,
`fresh-candidate-proof.json`, `regression-checks.json` und `cleanup-verified.json`.
Credentials und private Startprotokolle sind keine Veröffentlichungsartefakte.

Vor Veröffentlichung bleiben die GitHub-/ARM64-Prüfung und der vereinbarte
Pilot auf RCON3/4 einschließlich normaler Nutzung, Rundenwechsel und tatsächlicher
Integrationen erforderlich. Ältere Ausgangsreleases wurden hier nicht geprüft.
Der Code-Rollback ist für diesen schemaunveränderten Kandidaten belegt; spätere
Schemaänderungen benötigen einen eigenen Rückweg. Der neue GitHub-Workflow ist
manuell auslösbar, in diesem Auftrag aber weder gepusht noch auf GitHub ausgeführt.
