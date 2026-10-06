# Report-Admin: erste, regelbasierte Version

Diese Version verarbeitet ausschließlich neue `!admin`-Reports zu fehlender
Führungskommunikation und Teamkills. Sie benötigt keinen KI-Zugang und erzeugt
keine Modellkosten. Freie KI-Textgenerierung und weitere Sanktionen sind nicht
Teil dieser ersten Version. Standard: **deaktiviert**, Betriebsart **Probelauf**.

## Freigegebene Regeln

- Kommunikation: eine eindeutig erkannte Beschwerde gegen den aktuellen
  Squadleader/Commander des eigenen Teams führt im Aktivmodus direkt zum Kick.
  Kein Vote, keine Vorwarnung. RCON kann das Schweigen **nicht nachweisen**;
  diese Regel vertraut der Meldung und kann durch Falschmeldungen missbraucht
  werden. UI und Discord weisen auf diese Grenze hin.
- Teamkills: nach einer Meldung mindestens **5 gespeicherte TEAM KILL-Ereignisse
  in den 300 Sekunden vor dem Report**, begrenzt auf das laufende Match und den
  jeweiligen Server. Keine normalen Kills, keine Selbsttötungen, keine Daten
  anderer Spieler. Die Anzahl beweist keine Absicht; auch ein einzelner Unfall
  mit mehreren Opfern kann die Schwelle erreichen.
- Alle anderen Fälle bleiben manuell, insbesondere Cheating, Sabotage und Chat-
  oder Namensverstöße. Keine Banns oder Nachrichten-Warnungen durch dieses Modul.

Beispiele: `!Admin Able squad keine Komms`, `!admin commander is not talking`,
`!admin BattlefieldHero teamkills`. Der kleine DE/EN-Erkenner ist bewusst kein
allgemeines Sprachmodell: nicht unterstützte, gemischte, zitierte oder unklare
Formulierungen bleiben normale Reports. Auch die Beschwerde muss erkennbar sein;
ein Squadname allein genügt nicht.

## Spielerzuordnung

Aktueller, eindeutiger Online-Spieler; Melder und Ziel im selben Team,
standardmäßig keine Selbstmeldung. Für Kommunikation muss der Melder einem Squad angehören oder
Commander sein; das Ziel muss eine Führungsrolle haben. Squadbezeichnungen,
Commander-Aliasse und die HLL/HLLV-Rollen stammen aus dem bestehenden Parser.

Spielernamen werden unabhängig vom Parser nochmals geprüft. Ein exakter Treffer
hat Vorrang. Bei Tippfehlern gilt ein vollständiger Namenskandidat mit mindestens
6 normalisierten Zeichen. Einfügen, Löschen, Ersetzen und benachbarte Vertauschungen
werden berücksichtigt: maximal ein Fehler je vier Zeichen, insgesamt höchstens
drei. Der zweitbeste Online-Name (auch im anderen Team) muss mindestens zwei
Änderungen weiter entfernt sein. Mehrere Report-Ziele, kurze Namensreste oder
konkurrierende Treffer werden nicht automatisch bestätigt. Normale Report-
Erkennung und ihre Vorschläge bleiben unverändert.

Das Ziel wird einmal an Spieler-ID, aufgezeichnete Sitzung, Team und bei
Kommunikation Führungsposition gebunden. Direkt vor der Aktion werden die
aktuelle Spielerliste, Sitzung, Karte und Einstellungen erneut geprüft; es wird
nicht stattdessen ein Nachfolger gewählt.

## Konfiguration und Nachrichten

Apps → Discord-Report-Bot → **Report-Admin – Kommunikation & Teamkills**.
Serverbezogene Aktivierung, Probelauf/Aktivmodus und beide Regeln einzeln.
Konfiguration benötigt `can_manage_discord_report_bot`; Aktivierung zusätzlich
`can_kick_players`. Session-Schreibzugriffe bleiben CSRF-geschützt.

**Selbstmeldungen für Tests zulassen** (`allow_self_reports`, standardmäßig aus)
hebt ausschließlich die Selbstmeldesperre des Report-Admins auf diesem Server auf.
Im Aktivmodus sind das **echte Kicks**, kein zusätzlicher Probelauf. Online-Zuordnung,
Führungsrolle, Sitzungsprüfung, Discord-Zustellung und Teamkill-Schwelle gelten
unverändert. Beim Führungsvote bleiben Selbstmeldungen gesperrt. Nach dem Test
wieder ausschalten und speichern; bereits manuell abgelegte Reports werden
auch beim Einschalten nicht nachträglich ausgeführt.

Pro Regel kann eine vorhandene Vorlage aus **Gründe / REASON** ausgewählt werden.
Platzhalter: `{player_name}`, `{teamkills}`, `{minutes}`. Nur Textsubstitution,
keine Befehle oder Auswertung von Vorlagencode. Fehlt die Vorlage, wird der
integrierte DE/EN-Text verwendet. Der genaue gesendete Grund wird protokolliert.

Aktivierung ersetzt die automatische Führungsvote-Zuordnung für neue Reports auf
diesem Server und bricht noch nicht ausgeführte alte Votes ab. Ein bereits
angelaufener Vote-Kick muss erst abgeschlossen sein. Die bisherigen Vote-
Einstellungen werden nicht überschrieben; nach Abschalten gilt wieder der alte
Report-Workflow. Ausstehende Report-Admin-Verfahren werden beim Konfigurations-
wechsel beendet und nicht später wiederaufgenommen.

## Ausführung und Discord

Die bestehende Routines-Laufzeit führt einen isolierten Fünf-Sekunden-Schritt aus;
ein PostgreSQL-Owner-Lock verhindert doppelte Worker. Es wird kein zusätzlicher
Supervisor-Prozess benötigt. Zustände und Belege liegen im bestehenden Incident-
Journal; keine neue Datenbankmigration erforderlich.

Der ursprüngliche Report muss in Discord zugestellt sein, bevor gekickt wird.
Älter als 30 Sekunden eingehende Reports werden nicht automatisch angenommen;
nach spätestens 60 Sekunden werden wartende Fälle manuell. Die Bulk-Spielerliste
darf maximal 10 Sekunden alt sein. Datenfehler, fehlende Sitzungen, Kartenwechsel,
Admin-Übernahme, geänderte Ziele oder Einstellungen verhindern den Kick.

Vor dem Netzwerkaufruf wird ein dauerhafter Sende-Marker committed. Es gibt
genau einen nicht wiederholenden Kick-Versuch. Nur ein ausdrücklich bestätigter
Erfolg schließt den Report. Timeout, Ausnahme, unklare Antwort oder Neustart
bedeuten manuelle Prüfung, nicht Wiederholung. Weitere automatische Versuche
gegen dasselbe Ziel werden fünf Minuten lang gesperrt. Manuelle Aktionen und
Einstellungen teilen die Ausführungssperre; ein laufender Versand ist nicht
nachträglich rückgängig zu machen.

Discord bearbeitet dieselbe Report-Karte und zeigt Regel, Ziel, Prüfergebnis,
Teamkill-Anzahl und Ergebnis. Handlungsbedarf/Probelauf erzeugt eine erneute
Admin-Benachrichtigung. Einzelne Prüfschritte erzeugen keine zusätzlichen Pings.
Ein bestätigter Kick wird zusätzlich prominent als **„Automatisch gekickt“**
im Titel markiert, mit einer grünen Karte, einem vorangestellten Feld für
Spieler/Aktion/Grund und dem Report-Admin als automatischem Bearbeiter.
Probeläufe, unklare Ergebnisse und manuell geschlossene Reports tragen diese
Erfolgskennzeichnung nicht. Die Anzeige folgt der Discord-Sprache DE/EN.
Nach einem bestätigten und gespeicherten Kick erhält ausschließlich der Melder
eine kurze private DE/EN-Erfolgsbestätigung mit dem Namen des gekickten Spielers.
Keine Erfolgsmeldung im Probelauf oder bei unklarem/fehlgeschlagenem Kick.
Ein Selbstmelder erhält keine Nachricht, da er selbst gekickt wurde. Offline-
Melder, geänderte Sitzungen/Teams und veraltete Daten werden übersprungen.
Die Nachricht ist eine Information, keine Verwarnung. Ihr Versand wird im
Incident-Journal protokolliert, bei Fehlern nicht automatisch wiederholt und
ändert niemals das bereits gespeicherte Kick-Ergebnis.
Allgemeine Chat-Webhooks spiegeln bei aktivem Report-Admin keine `!admin`-Reports;
der Admin-Report bleibt erhalten. Bereits global geschriebener Chat bleibt im
Spiel öffentlich.

## Tests und Einführung

Synthetische Backend-/API- und Discord-Tests ohne echte Spieleraktionen;
Frontend-Build. Vor produktivem Einsatz: Backend und gemeinsamer Discord-Dienst
zusammen aktualisieren, Backup erstellen, Probelauf prüfen und Aktivierung
ausdrücklich freigeben. Insbesondere PostgreSQL-Sperren und echte Kick-Antworten
von HLL/HLLV müssen im Pilotbetrieb überprüft werden. Kein Rollout oder Aktivieren
ist Bestandteil des lokalen Entwicklungscommits.
