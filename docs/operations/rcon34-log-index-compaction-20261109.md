# Physische Verkleinerung der gemeinsamen Log-Indizes

Am 9. November 2026 nach der freigegebenen
[RCON1/2-Protokollbereinigung](rcon12-log-cleanup-20261109.md) ausgeführt.
Der Auftrag war, freigegebenen Platz tatsächlich an das Dateisystem zurückzugeben,
ohne weitere Datensätze zu entfernen. RCON3/4 blieben in Betrieb.

## Ergebnis

Vier aufgeblähte Indizes von `public.log_lines` wurden zwischen
20:01:47 und 20:03:41 UTC / 21:01:47 und 21:03:41 Uhr Berlin nacheinander mit
`REINDEX INDEX CONCURRENTLY` neu aufgebaut. Abschlussprüfung: 20:05:05 UTC.

| Messwert | Vorher | Nach Abschlussprüfung |
| --- | ---: | ---: |
| Alle sechs Log-Indizes | 8.904.622.080 Byte | 6.535.225.344 Byte |
| Gesamte Datenbank, unmittelbar vor/nach Wartung | 24.086.217.583 Byte | 21.717.345.135 Byte |
| Hauptdatei der Logtabelle | 7.760.822.272 Byte | 7.760.822.272 Byte |
| Freier Hostspeicher, unmittelbar vor/nach Wartung | 568.606.973.952 Byte | 570.942.910.464 Byte |

Die Log-Indizes sind damit **2.369.396.736 Byte / 2,37 GB kleiner** (26,6 %).
Die alten Indexdateien sind entfernt beziehungsweise auf 0 Byte freigegeben;
es handelt sich nicht nur um intern wiederverwendbare PostgreSQL-Seiten.
Die exakten Einzelwerte stehen in der
[Indexvergleichstabelle](rcon34-log-index-compaction-20261109.csv).
Unberührte Indizes können durch laufende neue Logs geringfügig wachsen.

Der freie Hostspeicher stieg über das unmittelbare Wartungsintervall um
2.335.936.512 Byte. Gegenüber der früheren Ausgangsmessung inklusive Vorbereitung
(568.957.140.992 Byte frei) beträgt der Nettozuwachs **1.985.769.472 Byte / 1,99 GB**.
Andere laufende Dienste schreiben ebenfalls auf diesen Datenträger; die
Dateisystemdifferenz ist deshalb nicht identisch mit der Indexersparnis.
Alle GB-Angaben sind dezimal.

## Auswahl und Sicherung

`pgstattuple_approx` ergab für den Tabellenkörper ungefähr 410.706.688 Byte
freien Platz (5,29 %). Der größere vermeidbare Platzverbrauch lag in den Indizes:
mittlere Blattfüllung 61,21 % beim eindeutigen Logindex, 64,83/67,25 % bei den
Spielerindizes und 70,47 % beim Zeitindex. Primärschlüssel und Server/Zeit-Index
mit 86,15/83,46 % wurden nicht neu aufgebaut. Die Diagnose-Erweiterung wurde
nur innerhalb einer anschließend zurückgerollten Transaktion verwendet;
installierte Erweiterungen sind unverändert.

Der frisch erstellte, vollständig mit `pg_restore` dekodierte Datenbankdump
von 19:39:33 UTC wurde erneut vollständig auf seine SHA-256 geprüft:

```text
/root/hll_rcon_tool/.deploy-state/rcon12-log-deletion-20261109/postgres.dump
3.718.279.465 Byte
6043d7f7e7cb7ee42f54cd46663923d85da784322f87cb330b67659f5d2be4fc
```

Die bestehende Konfigurationssicherung sowie alle Dateien des bereits
wiederhergestellten Protokollarchivs wurden ebenfalls geprüft und behalten.
Für diese reine Indexwartung wurde keine weitere vollständige Dump-Kopie erzeugt.
Der Tabellenkörper wurde nicht umgeschrieben: Ein `VACUUM FULL` würde während
der Umschreibung eine exklusive Tabellensperre erfordern. Der concurrent
Indexaufbau erlaubt dagegen weiter Schreibzugriffe, benötigt aber zusätzlichen
Arbeitsplatz und kann auf bestehende Transaktionen warten.
Siehe [PostgreSQL 12: REINDEX](https://www.postgresql.org/docs/12/sql-reindex.html)
und [VACUUM](https://www.postgresql.org/docs/12/routine-vacuuming.html).

## Begrenzte Ausführung

- PostgreSQL 12.22, keine Installation von `pg_repack`, kein Versionswechsel.
- Genau vier benannte Indizes, einzeln: Spieler 1, Spieler 2, Zeit, Eindeutigkeit.
- Laufzeiten: 19,77 / 18,99 / 15,41 / 56,65 Sekunden.
- Nur sitzungsbezogen: 512 MB Maintenance-Speicher, ein paralleler
  Maintenance-Worker, 3 Sekunden Sperrzeitlimit und 20 Minuten Statement-Limit.
- Kapazität, Indexzustand, unveränderte Definitionen, Dienste und HTTPS nach
  jedem Schritt geprüft; Advisory Lock gegen doppelte Ausführung.
- Keine Datenlöschung, keine Neuaktivierung von RCON1/2, keine Neustarts,
  keine Änderung von Konfiguration, Spielregeln oder Aufbewahrungsfristen.

## Daten- und Funktionsnachweis

Alle vor der vorangegangenen Löschung vorhandenen und zu erhaltenden Logs wurden
erneut vollständig nach ID sortiert exportiert, innerhalb derselben damals
festgehaltenen Server-ID-Grenzen. Ergebnis identisch mit dem geprüften Anker:

```text
7.354.848.455 CSV-Bytes
SHA-256 1815d64abacc400d9dd2f8d8a342fdf4acae4c99f33b67f6c8322534a2806d09
```

Archiv, Konfigurationsdateien, gespeicherte Konfiguration, Migrationsstände
und geschützte Vergleichsdaten stimmen weiterhin überein. Alle sechs Indizes
sind gültig und einsatzbereit; keine unvollständigen Ersatzindizes oder
offenen Maintenance-Sitzungen. Die Logtabelle behält denselben Dateipfad.

RCON3/4 lieferten HTTP 200 für Live-Seite, Versions- und Login-Endpunkt.
Die tatsächlichen Django-Views für Logs, Rundenstatistik und Scoreboard wurden
zusätzlich lesend geprüft: etwa 2–12 ms reine View-Laufzeit, Snapshots 9–15 s alt.
Das ist eine Zustandsprüfung und kein Vorher/Nachher-Performancebenchmark.
RCON3 hatte 98 Spieler online und 126 bisherige Rundenteilnehmer, RCON4 war leer.
Neue RCON3-Logs wurden während der Wartung weiter gespeichert. Im abgefragten
Live-Ergebnis gab es keine negativen Spielzeiten; geschützte historische
Problemfälle blieben unverändert. In den untersuchten neuen Backend- und
Supervisor-Logfenstern fanden sich keine geprüften Transport-, Timeout- oder
Datenbanksperrfehler.

63/63 RCON3-Reportzustellungen im letzten 24-Stunden-Fenster waren bestätigt,
keine ausstehend. Während der Wartung entstand kein neuer Report; damit ist
kein neu durchlaufener Discord- oder Kick-Test belegt.

Private Belege und Journal:

```text
/root/hll_rcon_tool/.deploy-state/rcon34-log-compaction-20261109/
inventory.json, space-measurement.json, baseline.json,
reindex-journal.json, reindex-complete.json, verified.json
```

Diese einmalige Wartung wird nicht als Datenmigration oder automatische
Bereinigung in ein Kundenupdate übernommen. Die portablen Verbesserungen und
noch offenen Upgrade-Prüfungen sind im
[Release-Prüfstand](../releases/next-performance-upgrade-readiness-20261109.md) getrennt erfasst.
