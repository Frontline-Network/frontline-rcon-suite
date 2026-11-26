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

1. **Redis-Loghistorie.** Herkunft und isolierter Vergleich sind unten dokumentiert. Vor einer allgemeinen Aktivierung stehen die Messungen des gesamten Statistikzyklus, der gemeinsamen Warteschlangen und der API-Latenz bei hoher Spielerzahl aus.
2. **Python-Laufzeit unter Last.** Supervisor und Backend mit derselben Ereignisfolge auf Ausgangsstand und Kandidat vergleichen. Während einer gut besuchten Runde und über einen Kartenwechsel Working Set, PSS, CPU, Log-Verarbeitungsverzug und p95-Antwortzeiten messen. Die Zahl der Spieler, den Aufwärmzeitraum und die Zahl der Admin-Clients zu beiden Messungen festhalten.
3. **Freigabe.** Identische Statistik- und API-Ergebnisse mit demselben Replay prüfen. Anschließend das Upgrade von v0.9.34 für HLL und Vietnam sowie den Fortbestand abgeschalteter Instanzen testen. Die Pilotmessung muss den RAM-Gewinn unter vergleichbarer Last zeigen und Auswirkungen auf Latenz und Rückstau beziffern.

## Redis-Historie und Kompressionsversuch

Vor Commit `100499e9` bezog der Log-Loop seine Liste über `log_history`. Der Commit führte `LogsHistory` mit dem Standardnamen `logs_history` ein. v0.9.34 und die installierten Quellen von Backend, Supervisor, Maintenance, Hintergrundworker und Webhook-Dienst verwenden den neuen Namen. Am 24. November enthielt die RCON3-Liste aktuelle Ereignisse. Die jüngsten Einträge des alten Namens in den untersuchten Datenbanken stammten vom 9. bzw. 13. August. Externe Leser lassen sich aus dieser Prüfung nicht ausschließen. Die vorhandenen Listen bleiben für beide Clientgenerationen erhalten.

Die aktuellen Listen belegten zusammen geschätzt 228 MiB, die unter dem früheren Namen 169 MiB. Für den Vergleich wurden je 10.000 Einträge aus einer aktuellen und einer historischen Liste auf isoliertes Redis 8.10.1 kopiert. Die Testinstanzen hatten je einen CPU-Kern als Obergrenze und temporären Speicher. Werte und Spielerkennungen wurden nicht protokolliert.

| Messung | Ohne Komprimierung | Kompressionstiefe 128 |
|---|---:|---:|
| Aktuelle Liste, belegte Byte | 8.700.031 | 3.647.823 |
| Historische Liste, belegte Byte | 8.366.321 | 3.312.658 |
| Erste 500 Einträge lesen, p95 | 0,459 ms | 0,507 ms |
| Einträge 501 bis 1.000 lesen, p95 | 0,443 ms | 0,463 ms |
| 500 Einträge ab Offset 4.000 lesen, p95 | 0,451 ms | 1,979 ms |
| Anfügen und Begrenzen der Liste, p95 | 0,075 ms | 0,087 ms |

Die Latenzen sind Mediane aus vier Läufen mit je 160 lokalen Anfragen bei einem Client. Eine Tiefe von 2 verlangsamte bereits die erste Seite erheblich. Bei 128 bleiben auf beiden Seiten der Liste je 128 Quicklist-Knoten unkomprimiert. Die Größe eines Knotens hängt von den Einträgen und der Redis-Konfiguration ab.

Eine unter Tiefe 0 gespeicherte RDB-Datei wurde mit beiden Einstellungen wieder geladen. Die Anzahl und die Prüfsummen jeder geordneten Seite von 500 Einträgen stimmten über beide Listen überein. Auch nach Schreiboperationen waren die Ausgaben identisch. Ein isoliertes `CONFIG SET` allein änderte die Belegung der bereits bestehenden Testliste nicht.

### Optionaler Pilot

Bei Installationen mit dem Standard-Startbefehl lässt sich `compose.redis-list-compression.yaml` als letzte Compose-Datei für den Pilot ergänzen. Der Zusatz verwendet die vorhandene `redis.conf` und ergänzt die Startoption `--list-compress-depth 128`. Er betrifft alle geeigneten Redis-Listen dieser Instanz. Bei einem angepassten Startbefehl muss die Option in diesen übernommen werden. Deployment-Werkzeuge mit expliziter Dateiauswahl müssen den Zusatz bei jedem geplanten Redis-Neustart mitführen.

Bei einer Vorschau mit expliziten `-f`-Pfaden auch `--project-directory` und `--env-file` der Installation angeben. Insbesondere wenn die erste Datei in einem archivierten Deployment-Verzeichnis liegt, kann eine andere Profilauswahl sonst Dienste ausblenden. Auf RCON3 wurde das vollständig gerenderte Modell verglichen. Mit derselben Umgebung änderte der Zusatz ausschließlich den Redis-Startbefehl. Der isolierte Start mit der ausgelieferten Konfigurationsdatei bestätigte Tiefe 128 mit Zusatz und Tiefe 0 nach dessen Entfernung.

Vor dem Pilot das gerenderte Redis-Kommando prüfen. Den Neustart des gemeinsamen Redis mit aktuellem Rückfallstand im Wartungsfenster planen. Anschließend `CONFIG GET list-compress-depth`, Speicherbelegung, Verarbeitungsrückstand und p95 des vollständigen Statistikabrufs bei gleicher Last vergleichen. Für den Rückbau den Zusatz aus der Compose-Auswahl nehmen und Redis im Wartungsfenster mit seiner bisherigen Konfiguration starten. Die Auswahl des Piloten erfordert keine Löschung, Verkürzung oder Umbenennung der Historie.

## Runden-Replay auf RCON3

Am 24. November wurden zwei abgeschottete Redis-8.10.1-Instanzen auf RCON3 aus derselben fertig geschriebenen RDB-Datei geladen. Vor der Auswahl der Runde betrug `used_memory` für das gesamte Abbild 501,1 MiB bei Tiefe 0 und 186,0 MiB bei Tiefe 128. Auf die RCON3-Liste mit 100.000 Logeinträgen entfielen davon 83,8 bzw. 22,2 MiB. Das sind Redis-Allokationen im Paralleltest. Der tatsächlich frei werdende Host-RAM bei einer Umschaltung ist separat zu messen.

Die Runde vom 21. November um 17:22 Uhr MEZ umfasste 2.729 protokollierte Ereignisse mit 228 unterschiedlichen Spielerkennungen über die gesamte Runde. Das Release-Backend berechnete `current_game_stats` für den eingefrorenen Rundenendzeitpunkt. Für die Profilabfrage diente eine leere isolierte SQLite-Tabelle. Die Zeit umfasst Loglesen, Statistikberechnung und Serialisierung, aber keinen HTTP-Aufruf oder Zugriff auf produktive PostgreSQL-Profile. Die Prüfsummen der serialisierten Ergebnisse waren für alle 228 Statistiken in beiden Varianten identisch.

| Messung | Tiefe 0 | Tiefe 128 |
|---|---:|---:|
| Rundenberechnung, Median / p95 | 92,92 / 110,19 ms | 105,63 / 123,16 ms |
| Rundenberechnung bei gleichzeitiger Testwarteschlange, Median / p95 | 101,80 / 116,84 ms | 105,77 / 114,67 ms |
| Synthetisches Einreihen und Abholen, p95 | 1,458 ms | 1,923 ms |

Je Variante und Lastfall gingen 24 Berechnungen in die Auswertung ein. Aufwärmdurchläufe wurden ausgelassen und die Reihenfolge der Varianten gewechselt. Alle 316 bzw. 328 synthetischen Warteschlangenpaare lieferten den erwarteten Wert. Ein gemeinsam genutztes Redis unter mehreren gleichzeitig aktiven Spielservern, produktive Moderationsabläufe und ein Live-Rundenwechsel bleiben eigene Abnahmepunkte.

## Live-Profile und Statistikprojektion vom 26. November

Die Live-Statistik lädt die benötigten Metadaten und die neueste lokale Sitzung pro Spieler gebündelt. Die HTTP-Live-Endpunkte liefern standardmäßig kompakte Profile. Vollständige Profile sind über `compact=false` abrufbar. Die Spielerakte lädt ihre vollständige Historie beim Öffnen. Für Warnsymbole liefert die Live-Projektion einen aggregierten Zähler der letzten 24 Stunden, der Kampagnen- und VIP-Nachrichten herausfiltert. Historische Einträge ohne Autor werden berücksichtigt.

Die drei Profil-Caches tragen die Schemaversion `live-profiles-v2`, damit gleichzeitig laufende ältere Worker ihre bisherigen Profile verwenden können. Der Ladezustand der Spielerakte wartet auf das vollständige Profil. Die RAM-Anzeige nennt die Datenquelle und zeigt belegten Speicher sowie das jeweilige Limit an.

Die Schlussprüfung umfasst Backend-Tests für Cache-Versionierung, Profilprojektion und Statistikgleichheit, Tests der Warnlogik sowie Browserprüfungen für das bedarfsgesteuerte Laden der Historie. Der Produktionsbuild und der normale Meldeweg über eine Spielerakte wurden geprüft.
