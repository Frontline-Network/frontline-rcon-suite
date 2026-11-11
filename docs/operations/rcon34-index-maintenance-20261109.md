# RCON3/4: Autobalancer-Indizes neu aufgebaut

Am 9. November 2026 wurden nach ausdrücklicher Freigabe die acht bestehenden
Indizes von `autobalance_player_role_stats` in der gemeinsamen RCON-Datenbank
einzeln mit `REINDEX INDEX CONCURRENTLY` neu aufgebaut. Alle acht sind gültig
und haben unveränderte Definitionen. Es wurden keine Anwendungsdaten gelöscht,
keine Dienste neu gestartet und keine Konfigurationen oder Spielregeln geändert.

Die Wartung folgt auf den
[Aufbewahrungs- und Indexvergleich](rcon34-retention-audit-20261109.md).
RCON1/2 bleiben stillgelegt; deren historische Daten wurden nicht bereinigt.
Andere Kundeninstanzen wurden nicht bearbeitet.

## Ergebnis

| Messung | Vorher | Nach Abschlussprüfung |
| --- | ---: | ---: |
| Acht Rollenstatistik-Indizes | 1.790.328.832 Byte | 110.239.744 Byte |
| Gemeinsame Datenbank | 25.747.923.823 Byte | 24.067.392.367 Byte |

Die Indizes belegen damit **1.680.089.088 Byte weniger**, etwa **1,68 GB**
beziehungsweise 94 % weniger. Die
[Einzelmessungen](rcon34-index-maintenance-20261109.csv) sind beigefügt.
Die Werte nach der Prüfung enthalten bereits neue reguläre Schreibvorgänge;
unmittelbar nach dem Neuaufbau waren die Indizes noch rund 74 KB kleiner.

Die acht Schritte einschließlich Zwischenprüfungen liefen von
17:48:51 bis 17:49:01 UTC, also 18:48:51 bis 18:49:01 Uhr Berlin.
Jeder Schritt dauerte mit Index- und Containerprüfung etwa 0,8 bis 1,5 Sekunden.
Nach jedem Schritt wurden öffentliche HTTPS-Endpunkte beider Instanzen geprüft.
Es gab keine ungültigen Restindizes und keine zurückgebliebene Wartungssitzung.

Die freie Hostkapazität lag vor der gesamten Sicherung und Wartung bei
577,64 GB und bei der Abschlussprüfung bei 575,44 GB. **Die Gesamtbelegung des
Hosts ist diesmal trotz der kleineren Datenbank gestiegen**, weil die neue
geprüfte Sicherung zusätzlich 3,71 GB belegt und erhalten bleibt. Auch normale
Live-Schreibvorgänge und WAL-Dateien beeinflussen diese Momentaufnahmen.
Frühere Sicherungen wurden nicht gelöscht.

## Sicherung und Wiederherstellungsprüfung

Privater Sicherungsordner auf dem RCON-Host:

```text
/root/hll_rcon_tool/.deploy-state/index-maintenance-20261109/
```

- PostgreSQL-Sicherung: `postgres.dump`, 3.711.470.922 Byte. Inhaltsverzeichnis
  geprüft und das gesamte Archiv mit `pg_restore` gelesen.
- PostgreSQL-Rollen: `postgres-globals.sql`, gesondert gesichert.
- Konfiguration: `configuration-before.tar.gz`, 35.105 Byte; alle 19 enthaltenen
  regulären Dateien per SHA-256 gegen die Quelldateien geprüft. Zusätzlich
  liegen die tatsächlichen Container-Einstellungen privat im Sicherungsordner.
- Acht nicht mehr vorhandene historische Compose-Dateien aus alten
  Container-Labels wurden dokumentiert. Aktuelle Konfigurationsdateien und
  die tatsächlich laufenden Container-Einstellungen sind gesichert.

SHA-256 der Datenbanksicherung:

```text
89f2150fb89287cebffd2c2c4c69ea18f5cda5182cd47b102e4fc324546073bb
```

Die vollständige Datenbank wurde anschließend mit PostgreSQL 12.22 aus demselben
Image in eine isolierte Kopie wiederhergestellt. Diese hatte kein Netzwerk,
keine veröffentlichten Ports und keine Produktivvolumes; Ressourcenlimit:
zwei CPUs und 3 GB RAM. Eigentümer und ACLs wurden für die isolierte
Wiederherstellung nicht übernommen; sie bleiben im Originalarchiv beziehungsweise
im Rollenexport erhalten.

Der vollständige Restore endete erfolgreich um 17:48:21 UTC. Stichproben aus
der wiederhergestellten Datenbank:

| Tabelle | Wiederhergestellte Zeilen |
| --- | ---: |
| Spielprotokolle | 21.028.058 |
| Spieler-Rundenstatistiken | 1.739.065 |
| Autobalancer-Rollenstatistiken | 309.968 |
| Admin-Reports | 1.237 |
| Rundenhistorie | 22.530 |

Alle wiederhergestellten Indizes waren gültig. Die acht Rollenindexdefinitionen
stimmten mit der Quelle überein; die geschützten negativen Spielzeiten wurden
zusätzlich per Anzahl und Inhaltsdigest verglichen. Erst danach begann die
Produktivwartung. Der eigens angelegte Testcontainer und sein Datenverzeichnis
wurden entfernt. Bereits vorhandene Testdatenbanken blieben unangetastet.

## Prüfung nach der Wartung

Abnahme ab 17:49:31 UTC, zusätzliche Erreichbarkeitsprüfung um 17:52 UTC:

- Container-IDs, Images, Laufzustände, Neustartzähler und Supervisor-Zustände
  stimmen mit der Vorprüfung überein. Beide Backends sind gesund. Bereits zuvor
  beendete Einzelprozesse wurden nicht gestartet; die vorhandene gemeinsame
  Laufzeit läuft weiter.
- `get_recent_logs` liefert auf beiden Instanzen 100 Ereignisse. Die Abfragen
  der Live-Statistik und des Scoreboards liefern HTTP 200; ihre Daten sind
  etwa zwei bis acht Sekunden alt und enthalten keine negativen Spielzeiten.
- RCON3 hat bei der Prüfung 98 Spieler online und 138 bisherige Teilnehmer der
  laufenden Runde. RCON4 ist leer; seine Live-Daten werden trotzdem aktualisiert.
- Die letzten drei abgeschlossenen RCON3-Runden sind mit 182, 243 und 177
  Teilnehmerdatensätzen gespeichert. Die kleinste Spielzeit beträgt jeweils
  null Sekunden. Die entsprechenden RCON4-Runden haben beim leeren Server
  keine Teilnehmerdatensätze. Während dieser Wartung wurde kein weiterer
  Rundenabschluss abgewartet oder künstlich ausgelöst.
- RCON3: 53 von 53 Discord-Report-Zustellungen im vorangehenden 24-Stunden-Fenster
  bestätigt, keine offenen Zustellungen. RCON4 hat in diesem Fenster keine
  Zustellungen. Während der Wartung traf kein neuer Report ein; daher wurde
  kein neuer automatischer Eingriff vollständig durchlaufen. Es wurden keine
  Testmeldungen oder Test-Kicks erzeugt.
- Die Backend- und Supervisor-Logs seit Wartungsbeginn enthalten keine der
  geprüften Transport-/Decoderfehler, Worker-Timeouts, Tracebacks oder
  Datenbank-Lock-Timeouts.
- Alle 498 bewusst ungeklärten negativen Spielzeiten (396/102) und die 72 alten
  RCON3-Protokolle stimmen per Anzahl und Inhaltsdigest mit dem Ausgangszustand
  überein. Benutzerkonfiguration, Migrationsstände und die gesicherten
  Konfigurationsdateien sind unverändert.
- Die Rollenstatistik enthält nach der Prüfung 310.018 Zeilen gegenüber
  309.960 bei der Vorprüfung: Der laufende Betrieb schreibt weiter.

Beim späteren Abruf des Nachweises gab es einmal einen SSH-Verbindungs-Timeout;
der erneute Abruf funktionierte. Zwei PowerShell-HTTPS-Anfragen vom Arbeitsplatz
liefen ebenfalls in einen Timeout. Die anschließende IPv4-Gegenprüfung lieferte
von dort HTTP 200 in 0,26 beziehungsweise 0,22 Sekunden; auch die direkten
Hostprüfungen waren erfolgreich. Die Ursache dieser einzelnen Client-Timeouts
wurde nicht bestimmt; ein Zusammenhang mit dem Indexaufbau wurde nicht belegt.

Die Indexwartung lief ohne erforderlichen Rollback. Ein späteres Problem mit
einem einzelnen Index wäre gezielt zu untersuchen; dafür nicht pauschal die
gesamte Datenbank zurückspielen und zwischenzeitliche Live-Daten überschreiben.
Das weitere Größenwachstum sollte vor einer Wiederholung der Wartung gemessen
werden. Automatische Löschfristen wurden nicht aktiviert.

Private Nachweise: `baseline.json`, `backup.json`, `restore-verified.json`,
`reindex-complete.json`, `verified.json` sowie Konfigurationsmanifest und Logs
im genannten Sicherungsordner. In Git liegen nur dieser Bericht und die
aggregierten Indexgrößen.
