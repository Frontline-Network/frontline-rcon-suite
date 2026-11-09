# Discord Report Bot und KI-Moderation

## Komponenten

CRCON bleibt die maßgebliche Quelle für Incidents, Rollenfreigaben, Claims,
Revisionen, Spielaktionen und Audit-Ereignisse. Der optionale
`discord_report_worker` überträgt vollständige Incident-Ereignisse über eine
idempotente Outbox. Der separat betriebene Frontline-Dienst verwaltet Discord,
führt die KI-Analyse aus und speichert genau eine Discord-Nachrichtenzuordnung pro
Incident.

Der zentrale Dienst speichert keine Report-, Chat- oder Namenstexte dauerhaft.
Verdächtige Chat- und Namenskandidaten sowie Shadow-Ergebnisse verbleiben in der
CRCON-Datenbank und werden nach 30 Tagen gelöscht. Normale Incidents verwenden
`INCIDENT_RETENTION_DAYS` mit Fallback auf `MOBILE_INCIDENT_RETENTION_DAYS`.

## CRCON-Konfiguration

```dotenv
DISCORD_REPORTS_ENABLED=true
DISCORD_SERVICE_URL=https://discord-service.example.org
DISCORD_CALLBACK_BASE_URL=https://callback.example.org
AI_MODERATION_ENABLED=true

# Generische Werte; leere Werte verwenden weiterhin die MOBILE_*-Einstellungen.
INCIDENT_CAPTURE_ENABLED=true
INCIDENT_TRIGGERS=!admin,@admin
INCIDENT_CONTEXT_MODE=enabled
INCIDENT_CONTEXT_FUZZY_THRESHOLD=0.74
INCIDENT_RETENTION_DAYS=90
```

Den Worker mit dem Compose-Profil `discord` starten. Danach unter
`Einstellungen -> Integrationen -> Discord Report Bot` die Frontline-App
installieren, Guild, gemeinsamen Report-Kanal und Moderatorrollen verbinden und
die erlaubten Aktionen wählen.

Eine Installation unterstützt genau eine Guild und einen gemeinsamen Kanal.
Mehrere Gameserver derselben CRCON-Installation werden durch Servername,
Servernummer und Spiel (`hll` oder `hll_vietnam`) im Embed unterschieden.

Für mehrere Kundendiscords verwendet der zentrale Dienst einen kurzlebigen,
installationseindeutigen OAuth-State. Der bei Discord ausgewählte Server wird
serverseitig an die CRCON-Installations-ID gebunden; die Guild-ID ist im Browser
nicht frei editierbar. Dafür müssen in der zentralen Service-Umgebung
`DISCORD_SERVICE_DISCORD_APPLICATION_ID`,
`DISCORD_SERVICE_DISCORD_CLIENT_SECRET` und
`DISCORD_SERVICE_DISCORD_OAUTH_REDIRECT_URI` gesetzt sein. Die Redirect URI muss
im Discord Developer Portal exakt registriert sein.

Verkaufte Installationen verwenden `DISCORD_CALLBACK_BASE_URL`. Der
Callback-Broker speichert ausschließlich die Installations-ID, die öffentliche
HTTPS-Zieladresse und technische Lifecycle-Daten. Das WordPress-Admin-Secret und
die getrennte Discord-zu-Broker-Fähigkeit werden nie an CRCON-Container oder
Browser übertragen.

## KI und Shadow-Rollout

Reports, Chat und Namen sind getrennt schaltbar. Chat verlässt CRCON erst nach
dem lokalen Begriffs-/Regex-/Ausnahmefilter. Ein unveränderter Spielername wird
pro Spieler, normalisiertem Namen, Modell und Regelprofil nicht erneut geprüft.
Neue oder geänderte Namen warten bis zur nächsten UTC-Halbstundengrenze und
werden dann in Gruppen von bis zu 50 Namen mit einem gemeinsamen Modellaufruf
klassifiziert. Jedes Ergebnis wird anschließend wieder einzeln validiert und
dem richtigen Spieler zugeordnet.

Als KI-Anbieter sind ein eigener verschlüsselt in CRCON gespeicherter API-Key
und ein ChatGPT/Codex-Login auswählbar. Frontline stellt kein KI-Kontingent und
keinen kostenpflichtigen Fallback bereit. API-Aufrufe
schicken verdächtige Chatkandidaten zuerst an `omni-moderation-latest`; nur ein
Omni-Treffer oder eine harte lokale Regel startet die ausführliche Modellanalyse.
Die semantische Namensprüfung verwendet direkt das ausgewählte günstige
Namensmodell mit `store: false`, festem Systemprompt, ohne Tools und mit strengem
Ausgabeschema. Der Codex-Modus verwendet den offiziellen
Device-Code-Login, liest die im Abonnement verfügbaren Modelle dynamisch und
führt jede Analyse als isolierten, flüchtigen Read-only-Turn aus. Spieltext wird
ausschließlich als nicht vertrauenswürdige Evidenz behandelt. Siehe die offiziellen Hinweise zu
[GPT-5.6 Luna](https://developers.openai.com/api/docs/models/gpt-5.6-luna),
[omni-moderation-latest](https://developers.openai.com/api/docs/models/omni-moderation-latest)
und [API-Datenkontrollen](https://developers.openai.com/api/docs/guides/your-data).

Im Shadow-Modus können Chat- und Namensanalysen unabhängig vom Risikowert keinen
Discord-Incident erzeugen. Außerhalb des Shadow-Modus gelten 0,90 als
Incident-Schwelle und 0,70 als lokale Review-Schwelle; ein harter Regeltreffer
überspringt die Risikoschwelle. Die produktive Freigabe dieser Quellen setzt im
repräsentativen Eval mindestens 95 % Präzision bei Risiko >= 0,90 voraus.

## Aktionssicherheit

KI-Ausgaben sind immer editierbare Empfehlungen und führen nie selbst eine
Spielaktion aus. Discord-Interaktionen sind signiert; CRCON prüft anschließend
noch einmal Installation, Guild, Kanal, aktuelle Rollen aus der signierten
Interaktion, Aktionsfreigabe, Incident-Revision und Idempotenz.

Unabhängig von diesen KI-Empfehlungen kann der neue, serverbezogene
[regelbasierte Report-Admin](report-admin.md) ausdrücklich aktiviert werden.
Er verarbeitet ausschließlich Kommunikations- und Teamkill-Reports und darf
im Aktivmodus nach seinen Prüfungen selbst kicken. Standardmäßig bleibt er
deaktiviert; der Probelauf führt keine Spielaktion aus. Die Dokumentation dort
beschreibt insbesondere die Grenzen der Namenszuordnung und fehlende
Sprachnachweise sowie die nötige Pilotprüfung.

Normale Reports verwenden das Bedienmodell des bisherigen Frontline-Reportbots:
Spieleraktionen stehen in der ersten Reihe, Melder-, Squad- und Log-Funktionen in
der zweiten und Ablehnen, Papierkorb sowie manuelle Bearbeitung in der dritten.
Es gibt keinen separaten Übernehmen-Schritt. Der erste zulässige Buttonklick
beansprucht den Incident atomar in CRCON für diesen Discord-Administrator. Das
Embed wird grün und zeigt den Bearbeiter im Footer; konkurrierende Administratoren
können den Report danach nicht verändern. Nachrichten und Log-Abfragen lassen den
Report offen, eine manuelle Bearbeitung erhält einen Abschluss-Button und
erfolgreiche Spielmaßnahmen schließen den Report.

Permaban, Blacklist und Squad-Auflösung benötigen einen Grund, eine Vorschau und
eine zweite Bestätigung. Bestätigungen sind kurzlebig, an den vorbereitenden
Discord-Nutzer gebunden und nur einmal verwendbar. Claiming verhindert parallele
Bearbeitung.

Fallen der kundeneigene KI-Zugang oder dessen Nutzungslimit aus, wird der Report weiterhin in Discord
zugestellt und die KI als nicht verfügbar markiert. Fällt Discord oder der
Frontline-Dienst aus, hält die Outbox das Ereignis mit exponentiellem Backoff zur
erneuten Zustellung vor; CRCON und Mobile Admin bleiben funktionsfähig.

## Betriebsstatus und Diagnose

`GET /api/discord/v1/status` liefert ausschließlich technische Zustände aus
lokalen Daten: Einrichtungsstatus, Direkt-/Broker-Modus, letzten Test, letzte
erfolgreiche Outbox-Zustellung, letzten Zustellversuch und Anzahl wartender
Ereignisse. Dieser Abruf startet keine Discord-, Broker- oder KI-Anfrage und
enthält weder Reporttexte noch Fähigkeiten oder Schlüssel.

Ein Administrator kann mit `POST /api/discord/v1/diagnostics` bewusst einen
Rundtest auslösen. Dabei prüft der zentrale Dienst die installierte Guild und den
konfigurierten Kanal und sendet anschließend einen authentifizierten,
inhaltsfreien Ping über denselben direkten Callback oder Callback-Broker zurück
an CRCON. Das Ergebnis unterscheidet zentralen Dienst, Discord-Bindung und
Callback. Es speichert nur Zustand, Zeitpunkt, Laufzeit und einen begrenzten
Fehlercode. Freie Fehlermeldungen externer Dienste werden nicht persistiert.

Der Rundtest läuft nur auf Anforderung, ist rate-limitiert und erzeugt kein
Hintergrund-Polling. `POST /api/discord/v1/test-message` speichert analog den
Zeitpunkt und den Erfolg der letzten Testnachricht. Dadurch kann die Oberfläche
später zwischen „noch nie getestet“, „erfolgreich“, „fehlgeschlagen“ und
„Diagnose teilweise verfügbar“ unterscheiden, ohne glaubwürdige Beispieldaten
zu erfinden.

## Datenschutz und Evals

`chat_classifications.db`, Bot-Logs und Klassifikationsdaten werden nicht
committed oder automatisch übertragen. Qualitätsbeispiele dürfen nur nach
explizitem Opt-in anonymisiert exportiert werden. Für Offline-Evals müssen
Spieler- und Discord-IDs vor einem Export entfernt werden.
