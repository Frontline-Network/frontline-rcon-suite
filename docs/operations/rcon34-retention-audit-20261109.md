# RCON3/4: Aufbewahrung und Speicherpotenzial geprüft

Stand: 9. November 2026, 18:20 Uhr Europe/Berlin. Die Produktivdatenbank wurde
nur lesend untersucht. Es wurden keine Datensätze gelöscht, keine Indizes im
Produktivsystem neu aufgebaut und keine Aufbewahrungsfristen geändert.

**Empfehlung: zuerst die acht bestehenden Indizes der Autobalancer-Rollenstatistik
neu aufbauen.** Eine wiederhergestellte Kopie benötigt dafür 110 MB statt
1,79 GB. Das gemessene Potenzial beträgt rund 1,68 GB, ohne Datensätze zu
entfernen. Die alten Spielprotokolle auf RCON3/4 sollten vorerst bleiben.

## Konkrete Kandidaten

| Priorität | Gegenstand | Gemessener Umfang | Empfehlung |
| --- | --- | --- | --- |
| 1 | Acht Indizes von `autobalance_player_role_stats` | 1.790.214.144 Byte produktiv; 110.084.096 Byte in der frischen Kopie | Mit aktueller geprüfter Sicherung einzeln neu aufbauen; rund 1,68 GB Potenzial. Bestehende Indexdefinitionen und alle Datensätze behalten. Noch nicht produktiv ausgeführt. |
| 2 | Spielprotokolle unter den stillgelegten Serverkennungen 1 und 2 | 17.388.916 Einträge älter als 180 Tage | Eigene Archivierungs- und Löschliste erstellen. Keine pauschale Freigabe aus dem Auftrag für RCON3/4 ableiten. Historische Zuordnung, Moderationsbelege und Wiederherstellbarkeit zuerst prüfen. |
| 3 | Alte Broadcast-Änderungen im gemeinsamen Audit | 1.494.967 `set_broadcast`-Einträge älter als 365 Tage; etwa 696 MB logische Zeilengröße | Separat prüfbarer Kandidat. Das Audit hat keine Serverspalte; eine Bereinigung wäre nicht auf RCON3/4 begrenzt. Keine Sanktionen oder sonstigen Audit-Befehle mitlöschen. |
| Behalten | Spielprotokolle von RCON3/4 älter als 90 Tage | 72 auf RCON3, keine auf RCON4 | Alle 72 liegen im Kontext noch ungeklärter Spielzeiten. Eine Frist von 180 Tagen würde hier fast nichts sparen und Belege gefährden. |
| Behalten | Autobalancer-Snapshots und Rollenstatistiken | Keine Einträge älter als 180 Tage; auf RCON3/4 auch keine älter als 90 Tage | Die bestehende 180-Tage-Regel vorerst beibehalten. Die Daten werden für historische Auswertungen verwendet. |

GB und MB sind hier dezimal. Zeilenanzahlen sind keine Speicherprognose.
Insbesondere sind die 696 MB Audit-Zeilengröße nicht mit sofort frei werdendem
Platz gleichzusetzen. Ein `DELETE` stellt PostgreSQL zunächst Platz zur internen
Wiederverwendung bereit; die Dateien auf dem Host werden dadurch nicht
zwangsläufig kleiner. Die Einsparungen der Kandidaten dürfen daher nicht einfach
addiert werden.

## Altersverteilung der Spielprotokolle

Fester Vergleichszeitpunkt: `2026-11-09T17:13:05.976499Z` (18:13 Uhr Berlin).
Die Gesamtzahlen umfassen Ereignisse bis einschließlich dieses Zeitpunkts;
„älter“ bedeutet strikt vor dem Zeitpunkt minus 90, 180 beziehungsweise 365
Tagen. Zeitstempel ohne Zeitzone in den Ereignistabellen wurden als UTC behandelt.

| Serverkennung | Ereignisse insgesamt | Älter als 90 Tage | Älter als 180 Tage | Älter als 365 Tage |
| --- | ---: | ---: | ---: | ---: |
| 1 | 17.643.502 | 17.642.987 | 17.338.942 | 17.197.798 |
| 2 | 247.013 | 240.279 | 49.974 | 49.278 |
| 3 | 2.417.136 | 72 | 72 | 72 |
| 4 | 719.693 | 0 | 0 | 0 |

Insgesamt sind es 21.027.344 Ereignisse. Rund 85 % liegen unter den Kennungen
1 und 2. Die Zuordnung ist die in der Datenbank gespeicherte Serverkennung;
sie allein belegt nicht die Herkunft jedes historischen Imports.

Die gemeinsame Datenbank belegt etwa 25,76 GB. Die größten untersuchten Bereiche
sind Spielprotokolle mit 16,66 GB, Autobalancer-Snapshots mit 2,73 GB,
Rollenstatistiken mit 1,86 GB und Audit-Protokolle mit 1,59 GB, jeweils inklusive
Indizes und gegebenenfalls ausgelagerten großen Feldinhalten.

Die [vollständige Alterstabelle](rcon34-retention-age-counts-20261109.csv)
enthält außerdem Snapshots, Rollenstatistiken und das gemeinsame Audit.
Dieses Audit enthält 2.551.648 Einträge, davon 2.539.727 älter als 90 Tage,
2.452.561 älter als 180 Tage und 1.704.525 älter als 365 Tage.

## Belege, die erhalten bleiben müssen

- Die bewusst noch unveränderten **498 negativen Spielzeiten** sind weiterhin
  vorhanden: 396 auf RCON3 in 99 Runden und 102 auf RCON4 in 38 Runden.
  Die ältesten betroffenen RCON3-Runden stammen vom September 2025.
- Die 72 alten RCON3-Protokolle stammen vom 13./14. September 2025.
  Elf liegen innerhalb betroffener Runden, alle 72 im erweiterten Kontext
  von einem Tag vor beziehungsweise nach deren Grenzen. Darunter sind
  Verbindungs-, Runden- und Teamwechselereignisse, die zur Rekonstruktion
  benötigt werden können. Die zeitliche Nähe beweist keine vollständige
  Rekonstruierbarkeit, rechtfertigt aber ihre Aufbewahrung.
- RCON3 hat 274, RCON4 26 noch offene Reports (`new` oder `claimed`).
  Die gefundenen Ereignis-Payloads von 39 RCON3-Fällen verweisen auf 183
  unterschiedliche Log-IDs; 118 davon gehören zu offenen Fällen. Alle
  referenzierten Logs sind vorhanden, keiner ist älter als 180 Tage.
  Zusätzlich kann der umgebende Chat nötig sein. Für RCON4 wurden in den
  untersuchten JSON-Feldern keine expliziten IDs gefunden; das ist kein
  Beleg dafür, dass keine Protokolle benötigt werden.
- Unter Kennung 1/2 existieren zusätzlich 52 offene Reports. Eine spätere
  Archivierung dieser Kennungen muss deren Belege ebenfalls berücksichtigen.
- Rundenstatistiken, Spielerprofile, Maßnahmen und frühere Reparaturbelege
  bleiben erhalten. Die Dateien der Spielzeit-Rekonstruktion unter
  `.deploy-state/playtime-reconstruction-20261025/`, einschließlich
  `followup-643`, sind weiterhin vorhanden.

Es gibt keine direkte Fremdschlüsselbindung der Reports an `log_lines`.
Log-IDs stehen jedoch in JSON-Payloads. Eine Löschprüfung allein anhand von
Fremdschlüsseln würde diese Abhängigkeit übersehen.

## Gemessener Indexvergleich

Die vollständige Tabelle `autobalance_player_role_stats` wurde mit einem
lesenden `pg_dump` exportiert und in einer isolierten PostgreSQL-Kopie mit
derselben Version 12.22 und denselben acht Indexdefinitionen wiederhergestellt.
Die Kopie enthielt 309.843 Zeilen. Es gab keine Auswahl oder Löschung von Zeilen.

| Messung | Byte |
| --- | ---: |
| Acht bestehende Produktivindizes am Vergleichszeitpunkt | 1.790.214.144 |
| Dieselben acht Indizes der frischen Kopie | 110.084.096 |
| Differenz | 1.680.130.048 |

Der größte Einzelunterschied betrifft den Index auf `round_id`: rund 600 MB
gegenüber 15,5 MB. Die [Einzelmessungen](rcon34-role-index-comparison-20261109.csv)
sind beigefügt. Dies ist ein in der Kopie gemessenes Wartungspotenzial, keine
bereits freigegebene Kapazität und keine bytegenaue Garantie für den Live-Neuaufbau.
Während der getrennten Prüfungen liefen reguläre Schreibvorgänge weiter;
deshalb können Zeilenzahlen und Größen zwischen Messzeitpunkten leicht abweichen.

Die untersuchten Indizes waren gültig und bereit. Die Rollenstatistik weist
rund 12,55 Millionen kumulierte Updates, keine HOT-Updates und 1.129
Autovacuum-Läufe auf. Die Statistik zählt seit dem 30. Juli 2025 und beschreibt
nicht die Last eines einzelnen Tages. Das Ergebnis spricht für stark gewachsene
Indizes trotz laufender Tabellenpflege; eine Datenkorruption wurde nicht
festgestellt. Ein Index mit null gemessenen Suchvorgängen wird deshalb nicht
automatisch als entbehrlich eingestuft.

Der Testcontainer hatte kein Netzwerk, keine veröffentlichten Ports, keine
Produktivvolumes und war auf eine CPU, 2 GB RAM und 1 GB temporären
Datenbankspeicher begrenzt. Er wurde nach dem Test entfernt. Der private
Tabellenexport ist 17.939.610 Byte groß; SHA-256:

```text
ffc1006a22a0153cf9eb11487baa687072dde884d6188e95e9b7b962f670e6ba
```

Der Tabellenexport ersetzt keine vollständige Sicherung vor einer späteren
Produktivwartung. Für diese wäre eine neue geprüfte Datenbank- und
Konfigurationssicherung anzulegen. Anschließend sollten die acht vorhandenen
Indizes einzeln mit `REINDEX INDEX CONCURRENTLY` aufgebaut und nach jedem
Schritt Gültigkeit, Last, freie Kapazität und Anwendungszustand geprüft werden.
Dieses Verfahren erlaubt gleichzeitige Schreibzugriffe, benötigt aber
zusätzlichen Speicher und I/O und kann auf bestehende Transaktionen warten.
Es ist keine lastfreie Operation. Siehe
[PostgreSQL-12-Dokumentation zu REINDEX](https://www.postgresql.org/docs/12/sql-reindex.html).

Nach einem Neuaufbau sollte das erneute Wachstum gemessen werden. Ein
regelmäßiger Neuaufbau ohne Messung oder das Entfernen bestehender Indizes ist
aus dieser Prüfung nicht abgeleitet.

## Vorhandene Aufbewahrungslogik

`runtime_data_retention` ist auf den aktiven Backends nicht per
`HLL_LOG_RETENTION_DAYS` oder `HLL_AUDIT_RETENTION_DAYS` aktiviert.
Der vorhandene Befehl ist an `SERVER_NUMBER=1` gebunden und arbeitet global
auf der gemeinsamen Datenbank. Seine Altersfilter enthalten keine Ausnahmen
für offene Reports oder Spielzeit-Rekonstruktionen. Er darf deshalb nicht
einfach mit 180 Tagen und `--execute` eingeschaltet werden. RCON1/2 müssen
dafür nicht wieder gestartet werden.

Die getrennte Autobalancer-Aufbewahrung verwendet bereits 180 Tage. Das wurde
in beiden laufenden Backends sowie anhand der täglichen Redis-Sperre geprüft.
Es gibt aktuell in keiner der vier Kennungen Snapshots oder Rollenstatistiken,
die diese Grenze überschreiten. Historische Rollenbewertungen verwenden einen
90-Tage-Bereich; Rundenanalysen können auf Snapshots oder ersatzweise Rohlogs
zugreifen. Bereits gespeicherte Analyseergebnisse decken nicht alle Runden ab.
Die Live-Anzeige allein ist daher kein Grund, diese Historie zu löschen.

Geprüfte Codepfade:

- `rcon/retention.py` und `rconweb/api/management/commands/runtime_data_retention.py`:
  globale Altersfilter und Aktivierung.
- `rcon/autobalancer/telemetry.py`, `service.py` und `store.py`:
  180 Tage und tägliche Ausführung.
- `rcon/autobalancer/history.py`:
  historische Rollenbewertung und Rundenanalyse mit Log-Fallback.

## Ausführung und Grenzen

Die SQL-Auswertungen liefen mit `BEGIN READ ONLY`, festen Zeitlimits,
kurzem Lock-Timeout und abschließendem `ROLLBACK`. Es wurden keine Erweiterungen
installiert und keine Dienste neu gestartet. Die Auswertungen liefern genaue
Zählungen zum beschriebenen Ereignis-Stichtag, aber keinen über alle Abfragen
festgehaltenen transaktionalen Snapshot des weiterlaufenden Systems.

Private Prüfdateien und Tabellenexport liegen auf dem Host unter
`/root/hll_rcon_tool/.deploy-state/retention-audit-20261109/`.
Die veröffentlichten CSV-Dateien enthalten nur aggregierte Zahlen, keine
Spielernamen, IDs, Chatnachrichten oder Zugangsdaten. Zum Abschluss um
17:20 UTC liefen alle sechs untersuchten RCON3/4-Container; beide Backends
meldeten `healthy`, die Neustartzähler standen auf null. Es blieb kein
Testcontainer bestehen. Diese Momentaufnahme ersetzt keine Beobachtung über
einen vollständigen Betriebstag.

Unabhängig vom Speicher sollte ein PostgreSQL-Upgrade vorbereitet werden:
Version 12 wird seit dem 21. November 2024 nicht mehr unterstützt.
Ein Major-Upgrade benötigt einen getesteten Migrationsweg und ist kein bloßer
Wechsel des Image-Tags. Es gehört in eine getrennte Wartung, siehe die
[offizielle Versionsübersicht](https://www.postgresql.org/support/versioning/).
