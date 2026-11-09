# Aufbewahrung auf RCON3/4: Vorschlag zur Entscheidung

**Aktualisierung:** Die lesende Untersuchung ist abgeschlossen. Maßgeblich sind
jetzt der [Prüfbericht mit Kandidaten](rcon34-retention-audit-20261109.md) und
die zugehörigen CSV-Auswertungen. Die 72 alten RCON3-Spielprotokolle liegen
vollständig im Kontext ungeklärter Spielzeiten und bleiben erhalten. Auf
RCON4 gibt es keine Protokolle älter als 90 Tage. Als erste Wartung empfiehlt
sich der Neuaufbau der acht Autobalancer-Rollenindizes: Die isolierte Kopie
zeigt rund 1,68 GB Potenzial ohne Datenlöschung. Produktiv wurde nichts geändert.

Der folgende Abschnitt dokumentiert den ursprünglichen Vorschlag vor dieser
Untersuchung; er ist keine Freigabe für Löschungen.

Stand: 9. November 2026. Es wurde keine Datenbereinigung aktiviert und nichts
aus der Historie gelöscht. Die gemeinsame Datenbank ist laut heutiger Prüfung
25,74 GB groß; 16,66 GB entfallen einschließlich Indizes auf Spielprotokolle.
Dies sind belegte Größen, keine zugesicherte Ersparnis durch eine Bereinigung.

| Daten | Vorschlag | Vor einer Freigabe erforderlich |
| --- | --- | --- |
| Spielprotokolle in der Datenbank | Zunächst 180 Tage online behalten. | Altersverteilung und Anzahl ermitteln; abgeschlossene Rundenstatistiken prüfen. Belege für offene Moderationsfälle und noch mögliche Spielzeit-Rekonstruktionen gesondert sichern. |
| Audit-Protokolle zu Admin-Maßnahmen | Vorerst vollständig behalten. | Mit den Admins vereinbaren, wie lange Entscheidungen nachvollziehbar bleiben sollen. Nicht zusammen mit gewöhnlichen Spielereignissen löschen. |
| Autobalancer-Snapshots und Rollenstatistiken | Vorerst vollständig behalten. | Nutzung durch Auswertungen und historische Bewertungen klären; erst dann Verdichtung oder eine Frist festlegen. Eine Live-Entscheidung bedeutet nicht automatisch, dass alle historischen Daten nutzlos sind. |
| Rundenstatistiken, Spielerprofile, Sanktionen und offene Reports | Behalten. | Keine Löschung im Rahmen dieser Optimierung vorgesehen. |
| Anwendungsdateien unter `/logs` | Bestehende Rotation nutzen und ihre Wirkung kontrollieren. | Die Rotation wurde repariert. Archivanzahl und Größe nach einigen Tagen erneut messen, bevor die Aufbewahrung verkürzt wird. |
| Datenbank- und Konfigurationsbackups | Aktuelle geprüfte Sicherung und den letzten funktionierenden Rücksprungstand behalten. | Ältere Sicherungen nur anhand einer Liste mit Datum, Instanz und Zweck freigeben; unklare Sicherungen behalten. |

Der vorhandene Befehl `runtime_data_retention` ist standardmäßig deaktiviert
und zeigt ohne `--execute` nur eine begrenzte Vorschau. Er berücksichtigt
derzeit keine Ausnahmen für Moderationsbelege. Deshalb reicht es nicht, einfach
eine Frist einzutragen und ihn automatisch ausführen zu lassen. Außerdem ist er
global für die gemeinsame Datenbank und an `SERVER_NUMBER=1` gebunden; die
stillgelegten RCON1/2 dürfen dafür nicht wieder gestartet werden.

Nach Zustimmung zur gewünschten Frist folgt zuerst eine lesende Vorschau mit
einem festen Stichtag, betroffenen Instanzen, Fall-Ausnahmen und der tatsächlich
ermittelten Zeilenanzahl. Erst nach Prüfung dieser Liste und einer frischen,
validierten Sicherung kann in kleinen Batches gelöscht werden. Ein `DELETE`
gibt PostgreSQL Platz zunächst zur internen Wiederverwendung frei; freie GB auf
dem Host entstehen dadurch nicht zwingend sofort. Eine Tabellen-Neuschreibung
mit Sperren und zusätzlichem Platzbedarf wäre eine gesonderte Wartungsmaßnahme.

Die Spielzeit-Reparaturen haben gezeigt, warum Rohprotokolle wertvoll sind.
Die noch unklaren historischen Einträge bleiben bis zur Entscheidung erhalten.
