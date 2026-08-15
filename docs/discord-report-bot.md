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

## KI und Shadow-Rollout

Reports, Chat und Namen sind getrennt schaltbar. Chat verlässt CRCON erst nach
dem lokalen Begriffs-/Regex-/Ausnahmefilter. Namen werden pro Spieler,
normalisiertem Namen, Modell und Regelprofil für 24 Stunden dedupliziert.

Der zentrale Ablauf verwendet zuerst `omni-moderation-latest` und anschließend
die Responses API mit `gpt-5.6-luna`, `store: false`, festem Systemprompt, ohne
Tools und mit strengem Ausgabeschema. Spieltext wird ausschließlich als nicht
vertrauenswürdige Evidenz behandelt. Siehe die offiziellen Hinweise zu
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

Permaban, Blacklist und Squad-Auflösung benötigen einen Grund, eine Vorschau und
eine zweite Bestätigung. Bestätigungen sind kurzlebig, an den vorbereitenden
Discord-Nutzer gebunden und nur einmal verwendbar. Claiming verhindert parallele
Bearbeitung.

Fallen OpenAI oder das Kontingent aus, wird der Report weiterhin in Discord
zugestellt und die KI als nicht verfügbar markiert. Fällt Discord oder der
Frontline-Dienst aus, hält die Outbox das Ereignis mit exponentiellem Backoff zur
erneuten Zustellung vor; CRCON und Mobile Admin bleiben funktionsfähig.

## Datenschutz und Evals

`chat_classifications.db`, Bot-Logs und Klassifikationsdaten werden nicht
committed oder automatisch übertragen. Qualitätsbeispiele dürfen nur nach
explizitem Opt-in anonymisiert exportiert werden. Für Offline-Evals müssen
Spieler- und Discord-IDs vor einem Export entfernt werden.
