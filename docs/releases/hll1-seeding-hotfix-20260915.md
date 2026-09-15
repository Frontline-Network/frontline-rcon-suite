# HLL1: Seeding-Hotfix am 15.09.2026

Auf ausdrücklichen Wunsch ohne reguläres GitHub-Release auf **hll1.fln.gg**
ausgerollt. Abschlussprüfung: **17:10:04 UTC / 19:10:04 Uhr MESZ**.
Seeding bleibt deaktiviert. Es wurden keine Spieler zum Test verwarnt,
bestraft oder gekickt.

## Ausgerollter Umfang

- Fix-Commit: `7c1be969cf56d6609b3ff71ac7070caef2476919`.
- Lokales Image: `frontline/hll1-seeding:hotfix-7c1be969`.
- Image-ID: `sha256:025474826b61bd08302f89faca4983700c13009ae0e66900ae2d99ba7c81edf1`.
- Basis: das zuvor tatsächlich laufende offizielle v0.8.4-Image
  `sha256:a11edc6b714593c3e1db28a39f95822d36ff8ec75e267bfe2b64a5dddc62fbf2`.
- Genau zwei kopierte Produktionsdateien: `rcon/automods/geofence.py` und
  `rcon/automods/seeding_rules.py`. Keine neuen Produktionsabhängigkeiten.
- Nur `backend_1` und `supervisor_1` im Compose-Projekt `fln_hll_srv1`
  wurden neu erstellt. Datenbank, Redis, Frontend und übrige Container wurden
  anhand ihrer IDs, Images, Status und Startzeiten als unverändert geprüft.
- Kein Neustart des eigentlichen Spielservers; keine Schema-Migration.
- Die öffentliche Versionsanzeige bleibt **v0.8.4**. Der Zusatzfix ist über
  Image-Tag und das Image-Label `gg.fln.hotfix.commit` nachvollziehbar.

Der Fix enthält die fünf korrigierten HLL-Kartenseiten, den Schutz vor
Seeding-Maßnahmen im squadlosen Beitrittszustand und den Nullpositionsschutz
gegen falsche Offensivpunkte-Fallbacks. Carentan ist geometrisch unverändert;
dort greift insbesondere der Schutz gegen falsche HQ-Positionen ohne Squad.

## Sicherung und Rückweg

Alle folgenden Pfade liegen auf HLL1 unter:

```text
/home/frontline/hll/srv1/hll_rcon_tool
```

Backupverzeichnis (nur für den Eigentümer zugänglich):

```text
.deploy-backups/seeding-map-sides-20260915-7c1be969/
```

Enthalten sind:

- `postgres.dump`: 1.207.109.073 Bytes, vollständiger PostgreSQL-Custom-Dump.
- `postgres-globals.sql`: Rollensicherung.
- `configuration.tar.gz`: `.env`, Konfigurationsverzeichnis, Basis-Compose und
  die tatsächlich verwendete Supervisor-Konfiguration.
- `compose.before.json`: vollständige vorherige Ausrollungskonfiguration.
- `image-before.tar`: 651.900.928 Bytes, bisheriges Image zusätzlich exportiert.
- `manifest.json`: SHA-256-Prüfsummen und Größen sämtlicher Sicherungen.

Der Datenbankdump wurde mit `pg_restore --list` sowie durch vollständiges
Lesen/Dekomprimieren mit `pg_restore -f /dev/null` geprüft. Das ist eine
Archivprüfung, **keine** behauptete vollständige Wiederherstellung in eine
Testdatenbank. Bei diesem reinen Code-Hotfix gab es keine Migration.
Ältere Backups wurden nicht verändert oder gelöscht.

Ausrollungszustand, Build-Kontext und Prüfbelege:

```text
.deploy-state/seeding-map-sides-20260915-7c1be969/
```

Maßgebliche Konfiguration für diesen Hotfix:
`compose.hotfix.json` in diesem Zustandsverzeichnis. Darin wurden ausschließlich
die Images der beiden betroffenen Dienste ersetzt. Benutzerkonfiguration und
aufgelöste Umgebungsvariablen wurden mit dem vorherigen Zustand verglichen.

Rollback bei Bedarf durch einen berechtigten Betreiber:

```sh
docker compose --project-directory /home/frontline/hll/srv1/hll_rcon_tool \
  -p fln_hll_srv1 \
  -f /home/frontline/hll/srv1/hll_rcon_tool/.deploy-backups/seeding-map-sides-20260915-7c1be969/compose.before.json \
  up -d --no-deps --no-build --pull never backend_1 supervisor_1
```

Immer die beiden Servicenamen explizit angeben: Die alte Installationskonfiguration
enthält zusätzliche stillgelegte Backend-/Supervisor-Dienste. Kein allgemeines
`compose up` ausführen. Keine automatische Datenbankrücksicherung und kein
automatisches Einschalten von Seeding. Das Basis-Image ist zusätzlich als
`frontline/hll1-seeding:rollback-before-7c1be969` markiert und im Backup enthalten.

## Erfolgreiche Abnahme

- Alle **318 Seeding-Tests** im gebauten Linux-Image, isoliert mit
  `--network none` und ausschließlich flüchtigen Testabhängigkeiten.
- SHA-256-Abgleich beider geänderter Dateien in beiden laufenden Diensten.
- Vollständiger Fingerabdruck der Datenbank-Benutzerkonfiguration unverändert;
  Seeding weiterhin aus, Kick-Einstellung unverändert aus.
- Alle 18 Supervisor-Prozesse `RUNNING`.
- Öffentliche `/views/live` und `/api/get_version`: HTTP 200.
- Verbindung zum Spielserver: St. Marie du Mont Warfare, 40 Spieler zum
  Prüfzeitpunkt; Live-Map-Snapshot 1,57 Sekunden alt.
- Im geprüften Neustartfenster keine neuen Fehler in Automod-/API-Protokollen.
- Die Live-Map übernahm zunächst nach Ablauf der vorhandenen zweiminütigen
  Collector-Sperre; anschließend wieder frische Daten. Die Sperre wurde nicht
  manuell gelöscht, und es wurde kein zweiter Datensammler erzwungen.

Keine Ausrollung auf RCON3/4, Ente oder andere Instanzen. Kein GitHub-Release
und keine Registry-Veröffentlichung für diesen schmalen Hotfix.
