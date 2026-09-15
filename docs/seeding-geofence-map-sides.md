# Seeding: Kartenseiten und Beitrittszustand

Stand: 15. September 2026. Codefix auf `codex/seeding-map-sides`, Basis `v0.8.4`.
Die Untersuchung auf HLL1 war lesend. Keine Ausrollung, Reaktivierung oder
Änderung der Produktionskonfiguration ist Bestandteil dieses Fixes.

## Ursachen und Korrekturen

### Fünf gespiegelte HLL-Kartenseiten

Die gebundene Bibliothek `hllrcon==2.0.0.0` enthält falsche Angriffsrichtungen
für St. Marie du Mont, Purple Heart Lane, Kursk, Kharkov und Elsenborn Ridge.
Der Bibliotheksautor korrigierte genau diese fünf Einträge in
[35d428a, „Fix HLL maps have incorrect orientation“](https://github.com/timraay/hllrcon/commit/35d428a0686bf21e759e18a6f27a4b949528c40c).
Die korrigierten Daten sind ab `hllrcon` 2.0.0.3 enthalten.

Der lokale Geofence-Resolver übernimmt ausschließlich diese fünf Datenwerte:
Alliierte `TOP_TO_BOTTOM`, Achsenmächte die Gegenrichtung. Kein pauschales
Umdrehen aller Karten; keine Veränderung der gemeinsam genutzten
Bibliotheksobjekte. Die expliziten Werte bleiben auch nach einer späteren
Bibliotheksaktualisierung richtig, statt die Korrektur nochmals umzukehren.
Ein umfassendes Dependency-Upgrade mit zusätzlichen HLLV-/Protokolländerungen
ist bewusst nicht Teil dieser Fehlerbehebung.

### Squadlos im Beitritts-/Spawnmenü

HLL meldet beim Beitritt teilweise ein zufälliges HQ, auch das gegnerische.
Der Schutz gegen anfänglich unveränderte Positionen folgt bereits dem
[Referenzprojekt hll-geofences](https://github.com/FlorianSW/hll-geofences/blob/main/worker/worker.go).
Er genügte jedoch nicht: Die Seeding-Prüfung behandelte den Platzhalter
`unassigned` wie einen echten Squad. Wechselnde Menüdaten konnten dadurch
echte Bereichsverwarnungen auslösen.

Die Squad-Prüfung überspringt jetzt `unassigned`, leere und fehlende
Squadnamen. Hier entstehen weder Verwarnungen noch Bestrafungsfortschritt.
Das gilt auch für verzögerte Offensivpunkte und gemeldete Rollen. Der
Commander bleibt eine gültige, separat geprüfte Führungsgruppe.

Außerdem sperrt eine bekannte Nullposition `(0, 0, 0)` die Bereichsprüfung
auch bei fehlenden Kartenmetadaten. Sie darf nicht versehentlich als
„Position unbekannt“ den Offensivpunkte-Fallback auslösen.
Der Fallback für tatsächlich fehlende Positionsdaten bleibt unverändert.
Die allgemeine Seeding-Begrüßung beim Verbinden bleibt ebenfalls unverändert;
sie ist keine gezählte Regelverwarnung.

## Lesender Abgleich mit HLL1

### St. Marie du Mont Warfare

Am 15.09.2026 zwischen 16:19:31 und 16:23:01 UTC (18:19–18:23 Uhr MESZ)
wurden 21 Seeding-PUNISH-Aktionen gegen 18 Spieler gespeichert, keine
Seeding-KICK-Aktion. Alle 21 nächstgelegenen vorausgehenden Positionsproben
waren höchstens drei Sekunden alt und lagen auf der eigenen Teamseite.
Diese anonymisierten, auf Zentimeter gerundeten Koordinaten werden als
Regressionstest wiedergegeben. Der korrigierte Resolver lässt sie passieren
und erkennt dieselbe Stelle für das jeweils andere Team als verbotenen Sektor.

### Carentan Warfare Night

Carentan ist **nicht gespiegelt**. Alliierte greifen von negativem nach
positivem X an; die Achsenmächte umgekehrt. Die eigene Rastergröße von
20.160 cm bleibt erhalten. Bei `max_caps=3` liegen die äußeren Grenzen des
erlaubten Mittelbereichs bei X = +/-20.160 cm.

Abgleich mit 1.927 gespeicherten Frames der vorangegangenen HLL1-Runde:
13 beobachtete HQ-Spawnübergänge bereits zugeordneter Alliierter lagen auf
negativem X, fünf der Achsenmächte auf positivem X. Es handelt sich um
beobachtete Null-zu-Position-Übergänge, nicht um eine vollständige Spawnstatistik.

Vier echte Verwarnungen an squadlose Spieler sind mit den historischen
Positionsdaten abgleichbar:

| Zeitpunkt UTC | Team | Squadstatus | Gemeldetes X (gerundet) |
| --- | --- | --- | ---: |
| 15:32:50 | Alliierte | unassigned | 97.987 cm |
| 15:33:51 | Alliierte | unassigned | 97.987 cm |
| 16:00:26 | Achsenmächte | unassigned | -96.470 cm |
| 16:01:28 | Achsenmächte | unassigned | -96.470 cm |

Die Proben lagen jeweils höchstens 1,2 Sekunden vom Warnzeitpunkt entfernt.
Es gibt acht entsprechende Logeinträge, weil jede dieser vier Aktionen
doppelt protokolliert wurde. Die positive/negative Koordinate des gegnerischen
HQ ist hier **kein** Nachweis, dass diese squadlosen Spieler dort gespawnt waren.
Die neuen Integrationstests prüfen Beitritt, erste Koordinate nach Squadwahl,
eigenes HQ und anschließenden echten Grenzübertritt getrennt für beide Teams.

Die zwei früheren Carentan-PUNISH-Aktionen um 16:00/16:01 UTC gehörten dagegen
zur verbotenen Tankcommander-Rolle, nicht zur Bereichsprüfung. Eine Position
im eigenen HQ allein widerlegt keine Rollenregel.

HLL1 war beim letzten Konfigurationsabgleich weiterhin deaktiviert;
`kick_after_max_punish` war ebenfalls aus. Der individuell hinterlegte
Verwarnungstext kündigt trotzdem einen späteren Kick an. Dieser irreführende
Konfigurationstext wurde nicht ungefragt überschrieben.

## Verifikation

- Unabhängige Geometrie-Fixtures für alle 20 HLL- und sechs HLLV-Karten der
  gebundenen Bibliothek: beide Teams, `max_caps` 2/3/4, eigenes/gegnerisches HQ,
  genaue Rasterkante und ein Zentimeter Abstand beidseits der Grenze.
- Explizite Nachtests für alle fünf korrigierten Karten bei beiden Spielständen,
  echte Bestrafung im feindlichen Sektor, kein Kick bei deaktivierten Kicks,
  Rückkehr in den erlaubten Bereich und unveränderte gemeinsame Kartenobjekte.
- Squadlose Spieler mit veränderlichen Positionen, Offensivpunkten und Rollen;
  Nullpositionen ohne Kartenmetadaten; Commander in HLL und HLLV.
- Vor der Seitenkorrektur: 74 fehlschlagende Prüfungen im gezielten Testlauf.
  Vor dem Beitrittsschutz: weitere 20 reproduzierte Fehlerfälle.
- Nach den Korrekturen: **318 Seeding-Tests erfolgreich**.
- Erweiterte Auswahl aus Automods, Rollen-/Teamadaptern, Karten und Live-Map:
  **541 erfolgreich**, ein unabhängiger Test bewusst ausgenommen.
  `test_get_slots_replaces_implausible_hll_count_with_connected_player_count`
  scheitert lokal an leerem `caplog.text`, obwohl die erwartete Warnung auf
  stderr erscheint. Derselbe Fehler ist auch im unveränderten separaten
  Leadership-Arbeitsverzeichnis reproduzierbar; kein Seeding-Fehler.

Reproduktion (mit Repository als `PYTHONPATH`, `HLL_MAINTENANCE_CONTAINER=1`,
`RCONWEB_TEST_MODE=1` und `SERVER_NUMBER=1`):

```sh
python -m pytest tests/test_seeding_map_sides.py tests/test_seeding_geofence.py tests/test_seeding_rules_automod.py -q
```

Die Tests gegen 26 Karten sind Geometrie-/Integrationstests mit Fixtures,
keine behaupteten Live-Abnahmen aller Karten. Live-Daten wurden für die
genannten HLL1-Runden auf SMDM und Carentan geprüft. Keine Migration nötig.
Vor einer gesondert freigegebenen Ausrollung: Datenbank/Konfiguration sichern,
Zielversion bauen und kontrolliert prüfen; Seeding nicht automatisch einschalten.
