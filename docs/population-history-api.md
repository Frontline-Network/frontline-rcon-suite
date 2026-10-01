# Spielerzahlen und Seeding über die CRCON-API

Der Dienst `population_history` speichert die vom Gameserver gemeldete Belegung
standardmäßig alle 30 Sekunden für 60 Tage in PostgreSQL. Er verwendet
`get_slots()` (verbundene Spieler und Slot-Limit), keine Schätzung aus Spielzeiten
oder Teamzuordnungen. Verbundene AFK-Spieler werden damit mitgezählt, sofern der
Gameserver sie als verbunden meldet. Warteschlangen sind keine belegten Slots.
Die bestehende RCON-Schicht kann Slot-Abfragen bis zu fünf Sekunden cachen.
Eine spezielle Unterscheidung zwischen aktiven Spielern und eigenen Seedern gibt
es im Slot-Zähler nicht; diese muss getrennt erhoben werden.

## Aktivierung und vorhandene Daten

Nach einem regulären Deployment dieser Version sind die vorhandenen
Alembic- und Django-Migrationen auszuführen, bevor Backend und Supervisor mit
dem neuen Code starten. Das normale Maintenance-Verfahren führt diese Schritte
bereits aus. Die Migrationen heißen `f4b9c2d6e310` und
`0039_population_history_permissions`. Es ist kein RedisTimeSeries-Modul und
keine neue Python-Abhängigkeit erforderlich.

In der geteilten Supervisor-Konfiguration startet `population_history` als
eigener Prozess. Im kombinierten Modus läuft er als eigener Dienst im gemeinsamen
Runtime-Prozess. Beide verwenden denselben Recorder. Eine transaktionsgebundene
PostgreSQL-Sperre pro Server verhindert parallele RCON-Abfragen; der Primärschlüssel
aus Servernummer und Messintervall verhindert doppelte Datensätze. Abgebrochene
Prozesse verlieren ihre Datenbanksperre automatisch. Fehlgeschlagene RCON-Abfragen
werden mit `status=rcon_error` und `player_count=null` gespeichert. Bei einem
Datenbank- oder Prozessausfall bleiben Zeitlücken. Nach Wiederanlauf werden nur
neue Messungen gesammelt.

Prüfung nach Deployment: Dienststatus kontrollieren und den Endpunkt mit
`resolution=raw` für die letzten Minuten abfragen. `first_available_at` und
`last_available_at` zeigen den ersten und letzten noch gespeicherten erfolgreichen
Messzeitpunkt. Vor der ersten Messung sind beide `null`. Es gibt keinen
automatischen historischen Backfill.

Der ältere `rcon/stats_loop.py`-Einstieg führt nun denselben PostgreSQL-Recorder
aus. Seine `Series`-/`PlayerCount`-Lesefunktionen sowie eventuell vorhandene
RedisTimeSeries-Daten bleiben bestehen. Diese Altbestände werden nicht automatisch
in den neuen Endpunkt gemischt: Erfassungsintervall, Fehlversuche und Metadaten
sind dort nicht zuverlässig bekannt. Ebenso bleibt die ungenutzte alte
`server_counts`-Tabelle unverändert. Aus Runden-Spielzeiten wird keine vermeintlich
exakte Historie erzeugt.

## Konfiguration

Die bestehende Settings-CLI unterstützt folgenden Server-Eintrag, zum Beispiel
in `/config/population.json`:

```json
{
  "1_PopulationHistoryUserConfig": {
    "enabled": true,
    "interval_seconds": 30,
    "retention_days": 60
  }
}
```

Im Backend-Container mit der allgemeinen CLI ausführen:

```sh
./manage.py set_user_settings 1 /config/population.json --dry-run true
./manage.py set_user_settings 1 /config/population.json --dry-run false
```

Erlaubte Intervalle: 15, 30 oder 60 Sekunden. Aufbewahrung: 1–365 Tage.
Änderungen werden beim nächsten Recorder-Durchlauf übernommen. Die Bereinigung
erfolgt stündlich pro Server, auch bei deaktivierter Erfassung. Eine kürzere
Aufbewahrung löscht ältere Messungen bei der nächsten Bereinigung.
Seeding-Markierungen bleiben als kleine, manuelle Protokolle bestehen.
Bei 30 Sekunden entstehen maximal 2.880 Messungen pro Tag und Server.

## Analyse-Zugang

Mit einem vorhandenen CRCON-Administrator im Django-Admin einen eigenen aktiven
Benutzer für die Analyse anlegen. Er benötigt weder Staff- noch Superuser-Rechte.
Ihm ausschließlich `api.can_view_population_history` zuweisen. Für Abfragen
anderer Servernummern innerhalb derselben CRCON-Datenbank ist zusätzlich
`api.can_view_other_crcon_servers` erforderlich. Ohne diese Berechtigung ist nur
die Servernummer der angesprochenen Backend-Instanz zulässig.

Unter **Django API Keys** einen Schlüssel für diesen Benutzer hinterlegen. Dafür
einen zufälligen Schlüssel mit mindestens 32 Zeichen aus einem Passwortmanager
verwenden und das Original sicher speichern; CRCON speichert den Hash. Der
Analyse-Client sendet den Schlüssel als `Authorization: Bearer …` über HTTPS.
Den Schlüssel nur im Secret-Speicher des Clients aufbewahren, nicht im Browser,
in der URL oder im Repository. Löschen des API-Key-Eintrags widerruft ihn;
deaktivierte Benutzer erhalten keinen Zugriff. Vorhandene Benutzer werden durch
die Migration nicht automatisch berechtigt.

## Spielerzahl-Endpunkt

`GET /api/get_player_count_history`

| Parameter | Bedeutung |
| --- | --- |
| `from`, `to` | Pflicht; ISO-Zeit mit Zeitzone oder Unix-Sekunden; `[from,to)` |
| `server` | Optional; stabile `SERVER_NUMBER`, Standard: aktuelles Backend |
| `resolution` | `raw`, `1m`, `5m` (Standard), `15m`, `60m` |
| `limit` | 1–5.000 Punkte, Standard 5.000 |

Maximal 31 Tage je Abfrage. Aggregierte Intervalle sind an UTC ausgerichtet;
Randintervalle werden auf den angefragten Zeitraum begrenzt. Bei zu vielen
Aggregatpunkten wird HTTP 400 zurückgegeben: Zeitraum verkürzen oder Auflösung
erhöhen. Rohdaten sind paginiert: `next_from` als neues `from` verwenden, `to`
beibehalten und fortsetzen, bis `next_from=null`. Es gibt keine stillen Kürzungen.

```sh
curl --fail-with-body --get 'https://hll1.fln.gg/api/get_player_count_history' \
  --header 'Authorization: Bearer <CRCON_ANALYSIS_API_KEY>' \
  --data-urlencode 'from=2026-09-26T00:00:00Z' \
  --data-urlencode 'to=2026-09-26T01:00:00Z' \
  --data-urlencode 'server=1' \
  --data-urlencode 'resolution=5m'
```

Datumswerte dem tatsächlich vorhandenen Zeitraum anpassen. Antworten verwenden
die bestehende CRCON-Hülle mit `failed`, `error` und `result`. Beispiel eines
Aggregatpunkts unter `result.points` (illustrative Werte):

```json
{
  "from": "2026-09-26T00:00:00Z",
  "to": "2026-09-26T00:05:00Z",
  "mean": 32.5,
  "min": 25,
  "max": 40,
  "sample_count": 8,
  "failed_sample_count": 1,
  "sampling_coverage": 0.8
}
```

`mean` ist das arithmetische Mittel gültiger Stichproben, kein zeitgewichtetes
Integral. Bei wechselndem Messintervall sollte für Vergleiche ein einheitlicher
Zeitraum gewählt oder anhand der Rohdaten ausgewertet werden. Fehlversuche gehen
nicht als 0 in Mittelwert, Minimum oder Maximum ein. Leere Intervalle erhalten
`null` für alle drei Werte, `sample_count=0` und `sampling_coverage=0`.

`sampling_coverage` beschreibt den Anteil des Abfrage-/Aggregatzeitraums, dessen
geplante Messintervalle erfolgreiche Stichproben haben: Eine gültige 30-Sekunden-
Stichprobe zählt als ein abgedecktes 30-Sekunden-Messintervall. Das ist eine
Vollständigkeitskennzahl der Aufzeichnung, keine kontinuierliche Beobachtung.
Bei einem mitten im Messintervall liegenden `from` werden zuvor gestartete
Intervalle konservativ nicht mitgezählt. Gruppierung und Filter beziehen sich auf
`scheduled_at`; `captured_at` in Rohdaten bezeichnet den Zeitpunkt, zu dem die
Slot-Antwort empfangen wurde. Zu spät eingetroffene Antworten zählen als Fehler.

Ein Rohdatenpunkt enthält `scheduled_at`, `captured_at`, `interval_seconds`,
`status`, `player_count`, `max_players` und `map`. Die Karte wird zusätzlich
abgefragt und kann bei Metadatenfehlern `null` sein; die Belegung bleibt gültig.
Es werden keine Spielernamen oder Spieler-IDs ausgegeben oder gespeichert.

HTTP-Status: 401 ohne gültige Anmeldung, 403 ohne Berechtigung bzw. bei inaktivem
Konto, 400 bei ungültigen Parametern, 405 bei falscher Methode und 503 bei nicht
verfügbarem Statistik-Speicher. Auch bei `lock_stats_api=false` bleiben diese
Endpunkte geschützt. Der Client muss HTTP-Status und `failed` auswerten.

## Seeding-Versuche markieren

Die bisherigen Seeding-Regeln und Seed-VIP-Zustände liefern keine dauerhafte,
eindeutige Historie eigener Seeding-Versuche. Daher werden Versuche explizit
markiert. Der reine Analyse-Zugang erhält dafür keine Schreibrechte.

`POST /api/mark_seeding_session` benötigt separat
`api.can_mark_seeding_sessions`. Der Client erzeugt eine UUID und sendet:

```json
{"action":"start","session_id":"a076d481-2b61-4fd3-9940-71c7b938d703","seeder_count":8}
```

Zum Beenden dieselbe UUID mit `action=end` und ohne `seeder_count` senden.
Wiederholte identische Requests sind idempotent; pro Server kann nur ein Versuch
offen sein. Start und Ende erhalten die aktuelle UTC-Zeit. Der Endpunkt arbeitet
ausschließlich auf dem angesprochenen Server. Browser-Sitzungen benötigen den
vorhandenen CSRF-Schutz; externe Bearer-Clients benötigen keine Sitzung.

`GET /api/get_seeding_sessions?from=…&to=…&server=1` benötigt die Leseberechtigung
und liefert überlappende Versuche mit ID, Server, Beginn, optionalem Ende,
optionalem `seeder_count` und `source=manual`. Die Zeit- und Antwortlimits
entsprechen der Spielerzahl-API. Interne Betreiberzuordnungen bleiben im
Datensatz, werden im Analyse-Endpunkt aber nicht ausgegeben.

`seeder_count=null` bedeutet unbekannt. Der optionale Wert ist eine manuelle
Angabe zu Beginn und keine fortlaufende Messung. Vergessene offene Versuche werden
nicht automatisch beendet; Clients müssen sie als unvollständig behandeln.

## Interpretation und Tests

Mit diesen Daten lassen sich beispielsweise Zeit bis 50/80 Spieler und die
anschließende Belegung untersuchen. Zwischen Stichproben ist der genaue
Schwellenübertritt unbekannt. Für deutsche Tagesprofile die UTC-Zeit erst bei
der Auswertung nach `Europe/Berlin` umrechnen, einschließlich Sommerzeit.
Hohe Belegung nach Seeding beweist allein keinen kausalen Nutzen. Dafür braucht
es vergleichbare Tage ohne Seeding und belastbare Angaben zum eigenen Einsatz.

Gezielte Tests:

```sh
HLL_MAINTENANCE_CONTAINER=1 RCONWEB_TEST_MODE=1 SERVER_NUMBER=1 \
  python -m pytest tests/test_population_history.py tests/test_population_api.py \
  tests/test_population_postgres.py tests/test_stats_loop.py \
  tests/test_supervisor_cli.py tests/test_supervisor_runtime.py
python -m django test api.test_population --settings=rconweb.rconweb.test_settings
```

`POPULATION_TEST_DB_URL` aktiviert echte PostgreSQL-Parallelitätstests in einem
isolierten temporären Schema einer ausdrücklich vorgesehenen Testdatenbank.
Die Backend-CI setzt diese Variable. Ohne sie werden diese beiden Tests
übersprungen. Keine Produktionsdatenbank als Testdatenbank verwenden.
