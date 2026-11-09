# RCON1/2: geprüftes Archiv und Löschvorschau

Stand: 9. November 2026, Abschluss 18:37 UTC / 19:37 Uhr Berlin.
Auftrag: alte RCON1/2-Protokolle archivieren, die Wiederherstellung prüfen und
anschließend eine Löschliste vorlegen. **Produktiv gelöschte Zeilen: 0.**
RCON3/4, geschützte Daten und vorhandene Sicherungen bleiben erhalten.

## Zur Prüfung vorgelegte Liste

Der feste Stichtag aus der vorausgehenden Analyse wurde beibehalten:
`event_time < 2026-05-13T17:13:05.976499Z`, ausschließlich Serverkennung `1`
oder `2`. Die Auswahl wird bei einer späteren Freigabe nicht stillschweigend
auf einen neueren Stichtag ausgedehnt.

| Serverkennung | Archivierte Altprotokolle | Löschkandidaten | Bleiben erhalten |
| --- | ---: | ---: | ---: |
| RCON1 | 17.338.942 | 769.416 | 16.569.526 |
| RCON2 | 49.974 | 14.920 | 35.054 |
| Gesamt | **17.388.916** | **784.336** | **16.604.580** |

Die Kandidaten sind ausschließlich gewöhnliche `KILL`-Ereignisse. RCON1:
13. Dezember 2022 bis 10. Mai 2026; RCON2: 12. März 2024 bis
29. November 2025. Dies sind die äußersten Zeitgrenzen der ausgewählten Zeilen,
keine pauschal zum Löschen freigegebenen Zeiträume oder ID-Bereiche.

| Jahr (UTC) | RCON1-Kandidaten | RCON2-Kandidaten |
| --- | ---: | ---: |
| 2021 | 0 | 0 |
| 2022 | 18.103 | 0 |
| 2023 | 251.393 | 0 |
| 2024 | 289.520 | 43 |
| 2025 | 192.530 | 14.877 |
| 2026 | 17.870 | 0 |

Die [Monatsübersicht](rcon12-log-deletion-preview-20261109.csv) enthält alle
archivierten Monate samt Kandidaten und verbleibenden Zeilen. Die exakte Liste
liegt als `deletion-candidates.csv.gz` im unten genannten privaten Archivordner
und als geprüfte lokale Kopie unter
`outputs/rcon12-log-archive-20261109/deletion-candidates.csv.gz` im Arbeitsbereich.
Sie enthält für jede vorgeschlagene Zeile ID, Serverkennung, UTC-Ereigniszeit
und eine SHA-256-Prüfsumme aller archivierten Felder. Größe: 37.301.593 Byte.

SHA-256 der komprimierten exakten Kandidatenliste:

```text
0703da50d6e3d5a80f23aa2efe9c68db092639918986e6a5e75fa7db885bfe8c
```

## Warum der größte Teil erhalten bleibt

Im stillgelegten Altbestand wurden zusätzlich **65.498 negative Spielzeiten**
gefunden: 63.946 unter Kennung 1 und 1.552 unter Kennung 2. Sie betreffen
8.325 beziehungsweise 187 Runden und reichen bis 2021 zurück. Diese Altfälle
wurden nicht korrigiert oder auf null gesetzt. Die separat geschützten
498 RCON3/4-Einträge bleiben ebenfalls unverändert.

Die Vorschau verwendet absichtlich breite Schutzregeln: Sobald ein Spieler
auf RCON1 beziehungsweise RCON2 eine ungeklärte negative Spielzeit hat, bleibt
seine gesamte vorhandene Kill-Historie auf diesem Server erhalten, einschließlich
Ereignissen, in denen er das Opfer ist. Das betrifft 31.389 beziehungsweise
1.159 unterschiedliche interne Spielerkennungen. Es wird hier nicht behauptet,
dass jedes dieser Ereignisse einzeln für eine spätere Reparatur notwendig ist.
Die breite Auswahl vermeidet eine vorschnelle Einschränkung der Belege.

| Vorrangiger Grund für Aufbewahrung | Zeilen |
| --- | ---: |
| Alle anderen Ereignisarten: Chat, Nachrichten, Teamkills, Admin-Maßnahmen, Verbindungen, Runden- und Teamwechsel usw. | 5.697.439 |
| Kill-Historie von Spielern mit ungeklärter Spielzeit | 9.431.078 |
| Kontext unvollständiger oder widersprüchlicher Runden | 1.363.145 |
| Kill-Historie zu offenen Reports | 75.537 |
| Fehlende Spielerzuordnung | 21.512 |
| Keine Zuordnung zu einer abgeschlossenen Runde mit gespeicherten Spielerstatistiken | 15.869 |
| Gesamt | **16.604.580** |

Die Gründe sind disjunkt gezählt: Bei mehreren passenden Schutzregeln wird
jeweils der erste zutreffende Grund ausgewiesen. Es wurden außerdem explizite
Log-ID-Verweise in elf JSON-Spalten von Report-, Moderations- und
Abstimmungstabellen sowie vorhandene Rundenanalysen berücksichtigt. Die
untersuchten JSON-Daten enthalten 183 unterschiedliche Log-Verweise; die
referenzierten Ereignisse sind keine Kandidaten.

Für offene Reports wurden Melder und Zielspieler aller vier Server betrachtet:
352 offene Fälle, davon 52 auf RCON1/2. Über die archivierte ID-Nachschlagetabelle
ließen sich 256 unterschiedliche Spielerkennungen zuordnen. Deren Kill-Historie
bleibt serverübergreifend aus der Liste ausgeschlossen. Die Zuordnung erfolgt
über gespeicherte IDs; unbekannte zusätzliche Identitäten werden nicht erraten.

Bei unvollständigen Runden, vorhandenen Rundenanalysen und zeitlich passenden
offenen Reports wurde zusätzlich ein Tag Kontext vor und nach den relevanten
Grenzen geschützt. Fehlt ein plausibles Rundenende, wird konservativ die nächste
bekannte Rundengrenze beziehungsweise der Archivstichtag verwendet. Ein
Kandidat muss außerdem einer abgeschlossenen Runde mit Spielerstatistiken
zugeordnet sein. Zeitstempel mit ein bis sechs Nachkommastellen wurden
einheitlich auf Mikrosekunden normalisiert; Grenzfälle, Zeitzonen, überlappende
Intervalle und Lücken wurden separat geprüft.

## Archiv und Wiederherstellung

Privater Archivordner auf dem RCON-Host:

```text
/root/hll_rcon_tool/.deploy-state/rcon12-log-archive-20261109/
```

Das Archiv umfasst den gesamten ausgewählten Altbestand, auch die geschützten
Zeilen. Die kleinere Kandidatenliste ist davon getrennt.

| Datei | Größe |
| --- | ---: |
| `log_lines.csv.gz` | 976.096.119 Byte |
| `steam_id_64.csv.gz` | 8.423.693 Byte |
| `pre-data.sql` und `post-data.sql` zusammen | 4.946 Byte |

Die ID-Tabelle ist die gemeinsame Nachschlagetabelle für die beiden
Spielerverweise jeder Protokollzeile. Sie wurde zur vollständigen
Wiederherstellbarkeit mitarchiviert; ihre Datensätze sind ausdrücklich keine
Löschkandidaten. Das Hauptarchiv belegt zusammen rund 984,5 MB. Dazu kommen
die Kandidatenliste, eine Liste zusätzlich geschützter Kill-IDs und Prüfnachweise.

SHA-256 von `log_lines.csv.gz`:

```text
648d266561ca516939fb236f8b885b9686f4c878e444ffc8dfb91badfeb759fa
```

Der Export erfolgte in lesenden Transaktionen, sortiert nach ID, mit expliziter
Spaltenreihenfolge, UTF-8, UTC und CSV-Nullmarker. Er wurde in eine isolierte
PostgreSQL-12.22-Kopie aus demselben Image wieder eingelesen. Diese hatte kein
Netzwerk, keine veröffentlichten Ports, keine Produktivvolumes und war auf
zwei CPUs sowie 3 GB RAM begrenzt.

Die Wiederherstellung war um 18:31:28 UTC erfolgreich. Alle Tabellenindizes
und Fremdschlüssel waren gültig. Beide Tabellen wurden erneut vollständig als
kanonisches CSV exportiert: Byteanzahl und SHA-256 stimmen mit den ursprünglichen
Exporten überein. Damit wurden alle exportierten Felder verglichen, nicht nur
Zeilenanzahlen oder Stichproben.

Anschließend wurden alle **784.336 Kandidaten** zusätzlich in die isolierte
Kopie eingelesen und geprüft: eindeutige und sortierte IDs, passende
Serverkennung, identische Ereigniszeit, Alter vor dem festen Stichtag,
Ereignisart `KILL`, vorhandene Spielerkennungen und vollständige
Zeilen-Prüfsummen. Es gab keine Abweichung.

Die Testkopie und ihr eigens angelegtes Datenverzeichnis wurden nach den
Prüfungen entfernt. Bereits vorhandene Testdatenbanken, Backups und aktive
Konfigurationen blieben bestehen. Die Produktivzählungen des Altbestands
stimmen weiterhin überein; RCON3/4-Schutzbelege, Konfigurationen und
Containerzustände sind unverändert. Beide RCON-Oberflächen waren bei der
abschließenden Prüfung erreichbar.

## Grenzen und nächster Freigabeschritt

Die Kandidaten belegen in der wiederhergestellten Tabelle zusammen
**258.705.036 Byte logische Datensatzgröße**, etwa 259 MB. Das ist keine Zusage
für unmittelbar frei werdenden Festplattenplatz und enthält keine zugesicherte
Indexersparnis. Ein späteres `DELETE` würde zunächst Datenbankplatz zur
Wiederverwendung schaffen. Eine physische Verkleinerung benötigt eine gesondert
geplante Wartung. Aktuell wurde durch die Archivierung zusätzlicher Speicher
belegt; es wurde noch keine Bereinigung ausgeführt.

Vor einer späteren Löschung sind die konkrete Kandidatenliste freizugeben,
eine aktuelle Sicherung zu erstellen und neue beziehungsweise geänderte
Moderations- und Rekonstruktionsbezüge erneut zu prüfen. Geänderte Zeilen werden
ausgenommen. Es darf nur anhand der dann noch passenden exakten IDs in kleinen
Chargen gelöscht werden; keine allgemeine Löschung nach Server und Alter.

Eine Erweiterung der Liste wäre eine zusätzliche Entscheidung über den Umgang
mit den geschützten historischen Daten. Rundenstatistiken, Spielerprofile,
Moderations-/Audit-Einträge, RCON3/4-Protokolle und die neueren RCON1/2-Protokolle
gehören nicht zur vorgelegten Löschliste. Nach einer Freigabe würden nur die
ausgewählten alten Kill-Detailereignisse aus der Online-Historie verschwinden;
sie bleiben im geprüften Archiv wiederherstellbar.

Private Belege: `archive.json`, `archive-manifest.json`, `README.txt`,
`protection-context.private.json`, `restore-verified.json`,
`deletion-preview.json`, `manifest-verified.json` und `final.json`.
Das Archivmanifest enthält Datei-Prüfsummen; die README beschreibt die
Wiederherstellung in einer separaten Datenbank und die Berechnung der
Zeilen-Prüfsummen. In Git werden nur dieser Bericht und die Monatsübersicht
aufgenommen, keine Chattexte, Spielerkennungen oder großen Archivdateien.
