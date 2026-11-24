# RAM und Laufzeit nach v0.9.34

Arbeitsbasis ist `master` bei `291d32b6`. Die Ausgangsmessung stammt vom 24. November 2026 um 01:23 Uhr MEZ auf dem gemeinsamen Host von RCON3 und weiteren Installationen. Am Ende der 30-Sekunden-Stichprobe meldete RCON3 fünf Spieler. Kosten bei voller Runde und beim Kartenwechsel sind noch offen.

## Ausgangswerte

Vier Messpunkte im Abstand von zehn Sekunden. Der Working Set entspricht `memory.current - inactive_file` der jeweiligen cgroup. Die letzte Spalte ist CPU-Zeit im Messfenster als Anteil eines Kerns.

| Dienst | Working Set in MiB | CPU |
|---|---:|---:|
| RCON3 Supervisor | 411 | 7,4 % |
| RCON3 Backend | 206 | 7,5 % |
| RCON3 Frontend | 4 | 0,2 % |
| Gemeinsamer Hintergrundworker | 187 | 2,0 % |
| Gemeinsames Redis | 558 | 4,0 % |
| Gemeinsames PostgreSQL | 651 | 15,3 % |

Der größte Einzelprozess im RCON3-Supervisor war der gemeinsame Python-Laufzeitprozess mit rund 347 MiB proportionalem Speicher (PSS). PostgreSQL belegte in seiner cgroup rund 111 MiB anonymen Speicher. Die Datenbank- und Redis-Werte umfassen mehrere Instanzen.

Die anschließende betriebliche Abschaltung von RCON4 betrifft dessen Frontend, Supervisor und Backend. Ihre unmittelbar vor dem Stopp gemessenen Working Sets summierten sich auf 406,9 MiB. Diese Einsparung fließt separat in die Betriebsbilanz ein.

## Erste Änderung im Arbeitszweig

`live_stats_loop` nutzt einen gemeinsamen Snapshot für Sitzungs- und Rundenstatistik. Nach dem letzten Leser hielt die lokale Variable sämtliche dekodierten Seiten bis in die Wartezeit. Der Kandidat gibt diese Referenz vor dem Warten frei.

Im isolierten Backend-Release-Image liefen zwei Leser über je 10.000 synthetische Einträge in Seiten zu 500. Beide Varianten lasen 20 Seiten aus der Quelle. Beide Leser lieferten in beiden Varianten dieselbe Prüfsumme. Python 3.12 meldete über `tracemalloc` während der Wartezeit 3.439.568 Byte im Ausgangsstand und 17.512 Byte im Kandidaten. Die Spitze beim Verarbeiten lag in beiden Läufen bei 3.443.913 Byte. Eine Verringerung des Container-Working-Sets im Spielbetrieb ist noch zu messen.

Der neue Regressionstest reproduzierte die gehaltene Referenz auf dem Ausgangsstand. Im Kandidaten bestanden alle 21 Tests aus `test_performance_runtime.py`, `test_performance_hotpaths.py` und `test_select_deployment_services.py`.

## Nächste Arbeitspakete

1. **Redis-Loghistorie.** Die gemessenen Listen `logs_history` belegen über mehrere logische Datenbanken geschätzt 228 MiB. Weitere 169 MiB entfallen auf `log_history`. Der aktuelle Standardname in `rcon/utils.py` ist `logs_history`. Zuerst die Leser und Schreiber je eingesetzter Version sowie die Herkunft der zweiten Liste nachweisen. Danach mit einer isolierten Datenkopie eine kompaktere Speicherung prüfen. Ereignisreihenfolge, verfügbare Historie und bestehende Leser beim Upgrade gehören zur Abnahme.
2. **Python-Laufzeit unter Last.** Supervisor und Backend mit derselben Ereignisfolge auf Ausgangsstand und Kandidat vergleichen. Während einer gut besuchten Runde und über einen Kartenwechsel Working Set, PSS, CPU, Log-Verarbeitungsverzug und p95-Antwortzeiten messen. Die Zahl der Spieler, den Aufwärmzeitraum und die Zahl der Admin-Clients zu beiden Messungen festhalten.
3. **Freigabe.** Identische Statistik- und API-Ergebnisse mit demselben Replay prüfen. Anschließend das Upgrade von v0.9.34 für HLL und Vietnam sowie den Fortbestand abgeschalteter Instanzen testen. Die Pilotmessung muss den RAM-Gewinn unter vergleichbarer Last zeigen und Auswirkungen auf Latenz und Rückstau beziffern.
