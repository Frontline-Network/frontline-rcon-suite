# Autobalancer: verlässliche Freiwilligenaufrufe

## Anlass (HLL1, 15. September 2026)

Die Prüfung zeigte zwei unterschiedliche Ursachen für den Eindruck, dass der
Autobalancer nichts tut:

- Die Konfiguration steht auf `manual`: Ein Vorschlag allein löst keinen Wechsel
  aus. Ein Admin muss freigeben; danach ist weiterhin ein frisches Todesereignis
  nötig. Der reguläre Ablauf gleicht Spielerzahlen aus, nicht allein Teamstärke.
- Ein einziger Unterschied zwischen Spielstands- und Spielerlisten-Zählung
  löschte die laufende Freiwilligenphase bzw. den Vorschlag. Auch ein kurzzeitig
  ausgeglichener Spielerstand beendete die Einladung vor ihrer angekündigten
  Frist. `!balance` wurde außerhalb der Freiwilligenphase still ignoriert.

Belege vor dem vorherigen Seeding-Hotfix: drei akzeptierte Meldungen um 15:34 UTC;
ein nicht freigegebener Vorschlag mit Abbruch wegen Teamzählungen um 15:36 UTC;
Einladungen um 16:23:58 UTC, danach zwei unbeantwortete Meldungen innerhalb der
30-Sekunden-Frist. Die groben Statusproben enthalten nicht den exakten Auslöser
jedes einzelnen Zustandswechsels.

## Änderungen

- Exakte, aktuelle Chatbefehle werden auch ohne offene Einladung privat
  beantwortet. Groß-/Kleinschreibung und äußere Leerzeichen sind egal;
  zusätzliche Argumente bleiben unberücksichtigt. Der konfigurierte Befehl gilt
  auch in Einladungen mit der bisherigen `!balance`-Vorlage.
- Modus, abgelaufene Frist, falsches Team, Commander-Schutz, Verbindungs- und
  Wechsel-Schonzeit sowie die Regel zum Zusammenhalten eines Squads werden
  erklärt. Im manuellen Modus nennen Einladung und Bestätigung die nötige
  Admin-Freigabe ausdrücklich.
- Doppelte Logzeilen werden nicht erneut verarbeitet. Antworten sind pro Spieler
  und Server auf einen Befehl je fünf Sekunden begrenzt; fehlende, zukünftige oder
  mehr als 60 Sekunden alte Zeitstempel lösen keine Antwort aus.
- Bei ausschließlich abweichenden Teamzählungen bleiben Beobachtung, Einladung
  und Vorschlag während einer kurzen Datenpause erhalten. Das gesamte
  Pausenbudget beträgt maximal 15 Sekunden je laufendem Ablauf, auch über mehrere
  kurze Unterbrechungen hinweg. Unsichere Zeit zählt nicht zur stabilen
  Beobachtungsdauer. Einladungs- und Freigabefristen werden nicht verlängert.
- Rechtzeitige Antworten während der Pause werden mit ursprünglichem Zeitstempel
  vorgemerkt und erst mit sicheren Daten geprüft. Stream-Quittierung und
  gespeicherte Vormerkungen verhindern den Verlust bzw. ein Zurücksetzen des
  Ereignis-Lesestands.
- Der Einladungskontext wird vor der ersten Direktnachricht gespeichert. So kann
  bereits der erste Empfänger antworten, während weitere Einladungen noch laufen.
- Ein kurzer Ausgleich der Spielerzahlen lässt eine bereits versandte Einladung
  bis zur angekündigten Frist offen. Sind die Teams dann ausgeglichen, endet sie
  ohne Wechsel. Ein klares Ungleichgewicht in die Gegenrichtung beendet sie.
- Längere Datenprobleme, andere Schutzgründe, Karten-/Moduswechsel, Abschalten und
  Admin-Abbruch beenden den Ablauf. Betroffene Teilnehmer werden privat
  informiert. Technische Details und freie Admin-Texte werden nicht an Spieler
  weitergegeben. Fehlgeschlagene Einladungen bzw. Bestätigungsnachrichten löschen
  keine ansonsten gültigen Meldungen.
- Ein bereits ausgeführter Teamwechsel wird bestätigt und protokolliert, bevor
  der nun ausgeglichene Spielerstand den Ablauf beendet. Ein fehlgeschlagenes
  Bestätigungs-Popup macht einen bestätigten Wechsel nicht nachträglich ungültig.

## Unveränderte Sicherheitsgrenzen

Auf unsicheren Daten wird weder ausgewählt noch freigegeben, scharfgeschaltet
oder gewechselt. Bereits scharfgeschaltete Kandidaten werden bei unsicheren
Daten weiterhin sofort verworfen; Todesereignisse werden nicht für eine spätere
Ausführung aufgehoben. Die Bestätigung eines bereits gesendeten Wechsels darf
kurz auf konsistente Daten warten, nie über die vorhandene Bestätigungsfrist
hinaus. Sie löst keinen erneuten Wechsel aus.

Pausierte Vorschläge erscheinen nach außen als `blocked` mit `paused_phase`;
die bisherige interne Phase bleibt erhalten. Die Freigabe-Schnittstelle lehnt
pausierte sowie abgelaufene Vorschläge ab. Eine vor der Pause gültige Freigabe
kann erst nach erneuter Sicherheits- und Kandidatenprüfung wirksam werden.

Keine Datenbankmigration und keine Änderung gespeicherter Serverkonfigurationen.
HLL1 bleibt auf `manual`; Seeding bleibt ausgeschaltet. Diese Änderung aktiviert
keinen automatischen Betrieb.

## Prüfung und Auslieferung

Regressionstests decken Chatverarbeitung, Datenpausen, Fristen, Berechtigungen,
Abbrüche, private Empfänger, Stream-Verarbeitung und Wechselbestätigung ab.
Commander-Ausschluss wird für HLL- und HLLV-Rollen geprüft. API-Tests verwenden die
echten dekorierten Endpunkte mit isolierten Speicher-/RCON-Ersatzobjekten.

Lokaler Testlauf am 15. September 2026: **640 erfolgreich**, einschließlich
Autobalancer, Seeding/Geofences, HLL-/HLLV-Spielprofilen, Log-Verarbeitung,
Chat-Webhook-Diagnose, Konfigurationscache und Worker-Topologie. Weitere drei
Tests aus `tests/test_log_recorder.py` konnten ohne konfigurierte Testdatenbank
(`HLL_DB_URL`) nicht eingerichtet werden; sie sind nicht als bestanden gezählt.
Die Prüfung benutzt ausdrücklich keine Produktionsdatenbank.

Die Änderungen sind lokal getestet; ein Spieltest mit echten Spielern und die
Ausrollung sind getrennte Schritte. Dafür müssen Log-Verarbeitung,
Autobalancer-Dienst und API denselben Code-Stand erhalten. Die vorhandenen
Seeding-Hotfixes bleiben Teil der Ausgangsbasis. Kein Release oder Deployment
ist Bestandteil dieses lokalen Fixes.
