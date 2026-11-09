# Freigegebene RCON1/2-Protokollbereinigung

Ausgeführt am 9. November 2026 nach ausdrücklicher Freigabe der
[geprüften Liste](rcon12-log-archive-review-20261109.md). Die Löschung endete
um 19:43:39 UTC / 20:43:39 Uhr Berlin; die inhaltliche Abschlussprüfung
um 19:45:11 UTC / 20:45:11 Uhr Berlin.

## Ergebnis

| Instanz | Gelöscht | Geschützte alte Protokolle verbleiben |
| --- | ---: | ---: |
| RCON1 | 769.416 | 16.569.526 |
| RCON2 | 14.920 | 35.054 |
| Gesamt | **784.336** | **16.604.580** |

Es wurden ausschließlich die freigegebenen gewöhnlichen `KILL`-Ereignisse
gelöscht: Serverkennung `1` oder `2`, Ereigniszeit strikt vor
`2026-05-13T17:13:05.976499Z`, exakte IDs und vollständige Zeilenprüfsummen aus
`deletion-candidates.csv.gz`. Die Liste wurde nicht erweitert. Es gab keine
übersprungenen Kandidaten und keine unklare oder fehlgeschlagene Transaktion.

Das ursprüngliche Archiv bleibt vollständig erhalten:

```text
/root/hll_rcon_tool/.deploy-state/rcon12-log-archive-20261109/
```

Die SHA-256 der freigegebenen komprimierten Kandidatenliste lautet weiterhin:

```text
0703da50d6e3d5a80f23aa2efe9c68db092639918986e6a5e75fa7db885bfe8c
```

## Sicherung und erneute Prüfung vor der Löschung

Zusätzlich zum bereits vollständig wiederhergestellten und geprüften Archiv
wurde unmittelbar vor der Löschung eine neue Sicherung der gemeinsamen
Datenbank, der PostgreSQL-Rollen und der aktiven Konfigurationsdateien erstellt:

```text
/root/hll_rcon_tool/.deploy-state/rcon12-log-deletion-20261109/
```

`postgres.dump` umfasst 3.718.279.465 Byte. Sein vollständiger Inhalt wurde
mit `pg_restore` dekodiert, das Inhaltsverzeichnis geprüft und SHA-256
festgehalten. Das ist eine Lesbarkeitsprüfung des frischen vollständigen Dumps;
die vollständige Testwiederherstellung der ausgewählten Protokolle erfolgte
bereits bei der Archivprüfung. Die Konfigurationssicherung wurde entpackend
gelesen und gegen die 19 enthaltenen Quelldateien geprüft.

SHA-256 des frischen Datenbankdumps:

```text
6043d7f7e7cb7ee42f54cd46663923d85da784322f87cb330b67659f5d2be4fc
```

Alle 784.336 Kandidaten wurden nochmals aus der laufenden Datenbank exportiert
und über sämtliche Felder mit dem freigegebenen Manifest verglichen.
`candidates-before.csv.gz` enthält zusätzlich diese frische selektive Sicherung
(45.284.355 Byte). Die Report-, Referenz-, Runden- und Rekonstruktionsbezüge
wurden neu eingelesen. Die inzwischen hinzugekommenen Reports und Log-Verweise
betrafen keinen Kandidaten; alle ursprünglichen Schutzregeln blieben gültig.

## Ausführung und Schutzgrenzen

Die Löschung erfolgte in 393 Transaktionen mit höchstens 2.000 Kandidaten.
Jede Charge sperrte nur ihre betreffenden Protokollzeilen, prüfte erneut deren
vollständige SHA-256 und die Schutzregeln und löschte anschließend ausschließlich
die passenden IDs. Serverkennung, Ereignisart und Stichtag wurden zusätzlich
direkt im `DELETE` eingeschränkt. Geänderte oder neu geschützte Zeilen wären
ausgenommen worden. Offene Reports wurden vor jeder Charge abgefragt; bei
Änderungen sowie spätestens nach 45 Sekunden wurden die Schutzbezüge neu geladen.

Die Logtabelle hat keine eingehenden Fremdschlüssel und keine eigenen
benutzerdefinierten Trigger. Somit wurden keine abhängigen Datensätze durch
Kaskaden gelöscht. Für jede Charge wurde ein dauerhaft geschriebenes
Ausführungsjournal mit vorbereiteten IDs und bestätigtem Commit geführt.
Die Abschlussprüfung bestätigte 393 eindeutige, vollständig abgeschlossene
Chargen sowie ausschließlich IDs aus der freigegebenen Liste.

Rundenstatistiken, Spielerprofile, Report- und Auditdatensätze, neuere
RCON1/2-Protokolle und sämtliche RCON3/4-Protokolle waren keine Löschziele.
RCON1/2 blieben abgeschaltet; es gab keine Containerneustarts oder Änderung
von RCON-Einstellungen. Vorhandene Backups und Testdatenbanken wurden nicht
entfernt.

## Abschlussnachweis

Alle bereits zu Beginn vorhandenen Protokolle außerhalb der freigegebenen
Liste wurden vor und nach der Löschung vollständig und nach ID sortiert
exportiert und gehasht. Die laufenden RCON3/4 durften währenddessen neue
Protokolle anlegen; der Vergleich begrenzte sich pro Server auf die zu Beginn
vorhandenen IDs. Der Vergleich umfasst auch die geschützten alten und neueren
RCON1/2-Einträge.

Beide Exporte umfassen exakt 7.354.848.455 Byte und besitzen dieselbe SHA-256:

```text
1815d64abacc400d9dd2f8d8a342fdf4acae4c99f33b67f6c8322534a2806d09
```

Die geprüften Archivdateien sind unverändert. Die geschützten negativen
Spielzeiten bleiben ebenfalls unverändert: 63.946 auf RCON1, 1.552 auf RCON2,
396 auf RCON3 und 102 auf RCON4. Die aktiven Konfigurationsdateien,
Datenbankkonfigurationen und Containerzustände stimmen mit dem Ausgangszustand
überein. Alle sechs Indizes der Logtabelle sind gültig. Die öffentlichen
RCON3/4-Endpunkte antworteten nach der Löschung erfolgreich mit HTTP 200.

Private Nachweise im neuen Sicherungsverzeichnis: `backup.json`,
`validated.json`, `predelete-context.private.json`, `execution-context.private.json`,
`deletion-journal.jsonl`, `deleted.json` und `final.json`. Das Journal enthält
die exakten gelöschten IDs; es wird ebenso wie die Sicherungen nicht in Git
aufgenommen.

## Wiederverwendbarer Datenbankplatz

Die normale Nachbereinigung `VACUUM (ANALYZE, TRUNCATE FALSE)` wurde um
19:50:10 UTC / 20:50:10 Uhr Berlin erfolgreich abgeschlossen. Der zunächst
stärker gedrosselte Lauf wurde wegen seines geringen Fortschritts gezielt
abgebrochen; der nachgeregelte Lauf dauerte rund 105 Sekunden. Die Einstellungen
betrafen nur diese Wartungssitzung. Die Löschtransaktionen wurden nicht
wiederholt. Auch nach der Nachbereinigung antworteten die RCON3/4-Endpunkte
erfolgreich mit HTTP 200. Details stehen in `vacuum.json` und
`vacuum-adjustment.json` im Sicherungsverzeichnis.

Es wurde kein `VACUUM FULL` ausgeführt. Die Dateien wurden nicht verkleinert:
Tabelle einschließlich Nebenrelationen rund 7,76 GB, Indizes rund 8,90 GB vor
und nach der Nachbereinigung; währenddessen kamen neue Live-Protokolle hinzu.

Die zuvor ermittelten rund 259 MB betreffen die logische Datensatzgröße.
Eine Zeilenlöschung schafft zunächst Platz zur Wiederverwendung innerhalb
der Datenbank. Sie garantiert keine entsprechende Verkleinerung der Dateien
auf dem Host. Das bestehende Archiv und die zusätzliche aktuelle Sicherung
werden ausdrücklich behalten.
