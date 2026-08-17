# Konkretes Optimierungsziel für Frontline RCON Suite

Der folgende Arbeitsauftrag ist der verbindliche Prompt für weitere
Performance- und Skalierungsarbeit. Änderungen dürfen nur übernommen werden,
wenn Messung, Kompatibilität und Rückrollbarkeit belegt sind.

## Zielprompt

> Optimiere die Frontline RCON Suite systematisch für den wirtschaftlichen
> Betrieb vieler paralleler CRCON-Instanzen. Reduziere CPU-Zeit, RAM,
> Prozesszahl, Datenbankverbindungen, Redis-Kommandos, Datenbank-I/O,
> Netzwerkpayloads und dauerhaftes Datenwachstum so weit wie sinnvoll, ohne
> Funktionen, Bedienbarkeit, HLL-/HLL-Vietnam-Kompatibilität, Mobile Admin,
> Discord Report Bot, Automods, Webhooks, Statistiken, RCON-Aktionen oder
> Auditierbarkeit zu verlieren.
>
> Beginne jede Optimierung mit einer reproduzierbaren Messung. Ordne Last einem
> konkreten Prozess, Endpunkt, Query, Redis-Befehl, Hintergrundloop oder
> Payload zu. Bevorzuge algorithmische Verbesserungen und das Entfernen
> redundanter Arbeit gegenüber pauschalen Ressourcenlimits. Senke keine
> Pollingfrequenz, Threadzahl oder Aufbewahrung ohne zu prüfen, welche
> Reaktionszeit oder Funktion davon abhängt.
>
> Behandle die vier Frontline-Instanzen als Produktions-Canary: RCON1 und
> RCON2 prüfen Hell Let Loose, RCON3 und RCON4 Hell Let Loose Vietnam. Rolle
> immer instanzweise aus. Warte auf echte HTTP- und WebSocket-Readiness, prüfe
> anschließend öffentliche URL, API, relevante Logs und Ressourcenwerte und
> breche bei Regressionen ab. Eine funktionierende PID allein gilt nicht als
> Readiness. Backend-Neustarts dürfen kein dauerhaftes Nginx-502 durch alte
> Docker-Adressen verursachen.
>
> Halte Datenbankänderungen strikt von normalen Runtime-Canarys getrennt.
> Führe keine Retention, Migration, Reindexierung oder Datenlöschung ohne
> Backup, Dry-Run, Kapazitätsprüfung, Wartungsfenster und ausdrückliche
> Freigabe aus. Große Tabellen und Indizes sind zunächst read-only zu
> analysieren. Löschläufe müssen begrenzt, batchweise, wiederaufnehmbar und
> standardmäßig deaktiviert sein.
>
> Sichere Kompatibilität durch Tests für Redis-Ausfälle, Queue-Idempotenz,
> Worker-Neustarts, konkurrierende Verarbeitung, API-Defaults, HLL/HLLV,
> WebSockets und externe Integrationen. Lange HTTP- oder KI-Aufrufe dürfen
> keine offenen SQL-Transaktionen halten und weder Reportzustellung noch
> Mobile Push blockieren. Hintergrunddienste sollen Verbindungen wiederverwenden,
> im Leerlauf exponentiell oder begrenzt zurückfallen und unnötige Django-
> Webchecks vermeiden.
>
> Begrenze große Standardantworten defensiv, ohne explizite paginierte oder
> interne Fachabfragen zu beschädigen. Vermeide vollständige Redis-SCANS,
> vollständige Historien-Deserialisierung, wiederholte unveränderliche
> Scoreboard-Berechnung und ungebremstes Worker-RSS. Verwende exakte
> Cache-Invalidierung, kleine Seiten, kurzlebige Ergebnis-Caches für
> unveränderliche Daten und gestaffeltes Worker-Recycling, sofern Messungen
> den Nutzen bestätigen.
>
> Dokumentiere für jede Phase: Ausgangswert, Hypothese, Codeänderung,
> Testumfang, Canary-Ergebnis, HLL-/HLLV-Abdeckung, Nebenwirkungen,
> Konfigurationsschalter und Rollback. Trenne Last der Suite von externen
> Bots oder Hostdiensten. Optimiere fremde Verbraucher nicht verdeckt durch
> inkompatible Serveränderungen; mache problematische Nutzung anhand von
> Frequenz, Antwortgröße und Laufzeit sichtbar.
>
> Abschlusskriterien sind: alle vereinbarten Tests grün oder bekannte
> Altfehler sauber abgegrenzt; RCON1–4 über einen repräsentativen Zeitraum
> stabil; keine hängenden Transaktionen oder unkontrollierten Redis-SCANS;
> messbar geringere CPU-/RAM-/I/O-Kosten; dokumentierter Rollback; keine
> Geheimnisse im Repository; und ein sauberer, reviewbarer Branch. Merge,
> Release, produktive Datenmigration und Löschung sind eigene Freigaben.

## Priorisierte nächste Messungen

1. Supervisor-Unterprozesse pro Instanz mit proportionalem RSS und CPU über
   mindestens 30 Minuten erfassen; gemeinsame read-only Laufzeiten nur dort
   konsolidieren, wo Fehlerisolation erhalten bleibt.
2. Den externen Node-Client hinter `185.164.39.118` separat untersuchen. Er
   fragt zahlreiche API-Endpunkte alle 30 Sekunden ab; dies ist nicht mit dem
   Discord-Worker zu verwechseln.
3. Dashboard-Logabrufe mit explizitem Bereich 15.000 serverseitig aggregieren,
   bevor der Bereich verkleinert wird. Die Oberfläche zeigt höchstens 100
   Einträge je Aktionsgruppe und sollte nicht den vollständigen Payload zum
   Browser übertragen müssen.
4. PostgreSQL-Index `ix_audit_log_creation_time` erst im Wartungsfenster
   aufbauen und Retention zunächst ausschließlich als Dry-Run auswerten.
5. Langzeitmessung des Gunicorn-Recyclings durchführen: RSS vor/nach Recycling,
   fehlerfreie Requests sowie keine gleichzeitigen Recyclingereignisse aller
   Instanzen.
