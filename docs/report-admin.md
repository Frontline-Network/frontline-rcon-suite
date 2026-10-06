# Report-Admin: erste, regelbasierte Version

Diese Version verarbeitet neue `!admin`-Reports zu fehlender
Führungskommunikation, Teamkills und optional Cheatverdacht. Sie benötigt keinen KI-Zugang und erzeugt
keine Modellkosten. Freie KI-Textgenerierung und weitere Sanktionen sind nicht
Teil dieser ersten Version. Standard: **deaktiviert**, Betriebsart **Probelauf**.

## Freigegebene Regeln

- Kommunikation: eine eindeutig erkannte Beschwerde gegen den aktuellen
  Squadleader/Commander des eigenen Teams führt im Aktivmodus direkt zum Kick.
  Kein Vote, keine Vorwarnung. RCON kann das Schweigen **nicht nachweisen**;
  diese Regel vertraut der Meldung und kann durch Falschmeldungen missbraucht
  werden. UI und Discord weisen auf diese Grenze hin.
- Teamkills: **keine starre Anzahl-Schwelle**. Nach einer Meldung wird der einzelne
  Fall mit bis zu 15 Minuten Kontext geprüft, begrenzt auf Server, Runde und
  aktuelle Sitzungen. Ab dem jüngsten Teamkill bleiben 60 Sekunden für eine
  freiwillige Entschuldigung; der Beschuldigte wird nicht darauf hingewiesen.
  Ein bereits länger zurückliegender Teamkill benötigt keine zusätzliche Wartezeit.
  Beide Seiten, Reihenfolge, Chat und mögliche Explosionsserien werden betrachtet.
  Eine Entschuldigung, Teamkills des Melders, gegenseitige Teamkills oder sonstiger
  widersprüchlicher Kontext führen zur manuellen Prüfung. Auch weitere Teamkills
  nach einer Entschuldigung beweisen nicht automatisch Absicht.
  Ein einzelner TK kann einen Kick begründen, aber nur zusammen mit einer zeitnahen,
  ausdrücklichen eigenen Absichtserklärung im protokollierten Chat. Der konservative
  DE/EN-Erkenner akzeptiert dafür vollständige Sätze wie „I teamkilled you on purpose“
  oder „Ich habe dich absichtlich geteamkillt“, keine bloßen Stichworte, Zitate,
  Verneinungen, Fragen oder freien Interpretationen. Ein solcher Satz muss innerhalb
  von 60 Sekunden nach einem tatsächlich protokollierten TK des Spielers liegen.
  Weitere unklare Chatnachrichten im zeitlichen Umfeld verhindern einen automatischen
  Kick. Fehlende Entschuldigung oder viele Teamkills alleine reichen niemals.
- Cheatverdacht (separat aktivierbar, standardmäßig aus): **nur Prüfung für Admins**,
  kein automatischer Kick oder Bann. 1-, 5- und 15-Minuten-Fenster, tatsächliche
  Waffen je Kill, Opfer, Multikill-Kandidaten und optionaler Rollenverlauf werden
  dokumentiert. Infanterie, MG, Panzer und Artillerie werden nicht gleich bewertet.
  Die konservativen Killraten-Heuristiken sind lediglich Priorisierungshilfen:
  Infanterie/Scharfschütze >3, MG >5, Panzer >8, Artillerie >10 Kills pro Minute,
  jeweils in **beiden vollständig beobachteten 5- und 15-Minuten-Fenstern**.
  Nenner ist Beobachtungszeit, nicht die unbekannte Zeit in einer bestimmten Rolle.
  Keine dieser unkalibrierten Schwellen, ein hoher K/D-Wert oder mehrere Meldungen
  beweist Cheating. Unbekannte Waffen und unvollständige Zeitfenster werden ausgewiesen.
  Mehrere unabhängige Melder erhöhen nur die Priorität. Ziel-/Sichtdaten fehlen.
  Für einen menschlich bestätigten Cheatfall wird in Discord bei „Tempbann“
  **24 Stunden vorbelegt**, aber nicht automatisch ausgeführt. Zusätzliche Belege
  und eine manuelle Entscheidung bleiben erforderlich.
- Alle anderen Fälle bleiben manuell, insbesondere Sabotage und Chat-
  oder Namensverstöße. Keine Banns oder Nachrichten-Warnungen durch dieses Modul.

Beispiele: `!Admin Able squad keine Komms`, `!admin commander is not talking`,
`!admin BattlefieldHero teamkills`. Der kleine DE/EN-Erkenner ist bewusst kein
allgemeines Sprachmodell: nicht unterstützte, gemischte, zitierte oder unklare
Formulierungen bleiben normale Reports. Auch die Beschwerde muss erkennbar sein;
ein Squadname allein genügt nicht.

## Spielerzuordnung

Aktueller, eindeutiger Online-Spieler; bei Kommunikation und Teamkills Melder und Ziel im selben Team,
standardmäßig keine Selbstmeldung. Für Kommunikation muss der Melder einem Squad angehören oder
Commander sein; das Ziel muss eine Führungsrolle haben. Cheatmeldungen können
einen Spieler des gegnerischen Teams betreffen. Squadbezeichnungen,
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

Apps → Discord-Report-Bot → oberer Einrichtungsassistent → **KI & Report-Admin**.
Serverbezogene Aktivierung, Probelauf/Aktivmodus und die drei Regeln einzeln.
Mit **Report-Regeln speichern** separat speichern; die optionale KI-Verbindung
für Chat/Namen darunter wird dadurch nicht eingerichtet oder verändert.
Konfiguration benötigt `can_manage_discord_report_bot`; Aktivierung zusätzlich
`can_kick_players`. Session-Schreibzugriffe bleiben CSRF-geschützt.

**Selbstmeldungen für Tests zulassen** (`allow_self_reports`, standardmäßig aus)
hebt ausschließlich die Selbstmeldesperre des Report-Admins auf diesem Server auf.
Im Aktivmodus sind das **echte Kicks**, kein zusätzlicher Probelauf. Online-Zuordnung,
Führungsrolle, Sitzungsprüfung, Discord-Zustellung und Teamkill-Einzelfallprüfung gelten
unverändert. Nach dem Test
wieder ausschalten und speichern; bereits manuell abgelegte Reports werden
auch beim Einschalten nicht nachträglich ausgeführt.

Pro Regel kann eine vorhandene Vorlage aus **Gründe / REASON** ausgewählt werden.
Platzhalter: `{player_name}`, `{teamkills}`, `{minutes}`. Nur Textsubstitution,
keine Befehle oder Auswertung von Vorlagencode. Fehlt die Vorlage, wird der
integrierte DE/EN-Text verwendet. `{minutes}` ist der tatsächliche Kontextzeitraum,
nicht mehr fest fünf Minuten. Vorhandene eigene Vorlagen mit festen „5 in 5“-Texten
müssen deshalb überprüft werden; sie werden nicht ungefragt überschrieben.
Der genaue gesendete Grund wird protokolliert.

Führungsabstimmungen sind aus der aktiven Report-/Chat-Verarbeitung und dem
Einrichtungsbereich entfernt. `!yes`/`!no` sind nicht mehr dafür reserviert. Auch
bei deaktiviertem Report-Admin startet kein neuer Vote. Beim Runtime-Start werden
offene Altverfahren beendet, unklare Sendeversuche als unklar markiert und alte
Vote-Aktivierungen zurückgenommen; kein neuer Versand und keine Wiederholung.
Historische Datensätze, Anzeige/Abbruch-API und intern gemeinsam benutzte
Identitäts-/Sperrhelfer bleiben kompatibel erhalten; die Aktivierungs-API lehnt
neue Aktivierungen ab. Es werden keine Historientabellen gelöscht.
Ausstehende Report-Admin-Verfahren werden beim Konfigurationswechsel beendet
und nicht später wiederaufgenommen.

## Ausführung und Discord

Die bestehende Routines-Laufzeit führt einen isolierten Fünf-Sekunden-Schritt aus;
ein PostgreSQL-Owner-Lock verhindert doppelte Worker. Es wird kein zusätzlicher
Supervisor-Prozess benötigt. Zustände und Belege liegen im bestehenden Incident-
Journal; keine neue Datenbankmigration erforderlich.

Der ursprüngliche Report muss in Discord zugestellt sein, bevor gekickt wird.
Älter als 30 Sekunden eingehende Reports werden nicht automatisch angenommen;
Kommunikations- und Cheatfälle verfallen nach 60 Sekunden; Teamkill-Fälle haben
wegen der stillen Beobachtung maximal 180 Sekunden ab Reporteingang. Fällige
Prüfungen blockieren keine neu eingehenden Kommunikationsmeldungen. Die Bulk-Spielerliste
darf maximal 10 Sekunden alt sein. Datenfehler, fehlende Sitzungen, Kartenwechsel,
Admin-Übernahme, geänderte Ziele oder Einstellungen verhindern den Kick.
Bei Teamkills werden gespeicherte Logs mit frisch gelesenen Spielserver-Logs
abgeglichen und direkt vor dem Kick erneut geprüft. Fehlgeschlagene, begrenzte,
unlesbare oder nicht übereinstimmende Antworten führen zur manuellen Bearbeitung.
Die Anwendung kann fehlende Daten im Spielserver selbst nicht rekonstruieren.

Vor dem Netzwerkaufruf wird ein dauerhafter Sende-Marker committed. Es gibt
genau einen nicht wiederholenden Kick-Versuch. Nur ein ausdrücklich bestätigter
Erfolg schließt den Report. Timeout, Ausnahme, unklare Antwort oder Neustart
bedeuten manuelle Prüfung, nicht Wiederholung. Weitere automatische Versuche
gegen dasselbe Ziel werden fünf Minuten lang gesperrt. Manuelle Aktionen und
Einstellungen teilen die Ausführungssperre; ein laufender Versand ist nicht
nachträglich rückgängig zu machen.

Discord bearbeitet dieselbe Report-Karte und zeigt Regel, Ziel, Prüfergebnis,
Teamkill-Anzahl, Prüffrist, beidseitige Ereignisse, Chatbelege, Unsicherheiten und
Ergebnis. Handlungsbedarf/Probelauf erzeugt eine erneute
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
Cheatmeldungen erhalten zusätzlich nur beim Melder eine private Eingangsbestätigung;
der Beschuldigte wird nicht informiert. Dies ist keine Erfolgs- oder Sanktionsmeldung.

Discord zeigt Kampf-/Combat-, Leistungs-/Performance- und Teamkill-Felder auch
bei Squadreports (mit „SL“ als Kennzeichnung für den Squadleader, keine Squadsumme).
Bei der automatischen Zielbestätigung bleibt dessen eigener Statistik-Snapshot
erhalten. Kampfpunkte und tatsächliche Nullwerte werden angezeigt. Fehlende Daten
stehen als „–“ da. Ohne positive Runden-Spielzeit gibt es keinen erfundenen KPM-Wert;
der Bulk-RCON-Datensatz enthält diese Zeit und Killserien nicht auf allen Spielen.

## Tests und Einführung

Synthetische Backend-/API- und Discord-Tests ohne echte Spieleraktionen;
Frontend-Build. Vor produktivem Einsatz: Backend und gemeinsamer Discord-Dienst
zusammen aktualisieren, Backup erstellen, Probelauf prüfen und Aktivierung
ausdrücklich freigeben. Insbesondere PostgreSQL-Sperren und echte Kick-Antworten
von HLL/HLLV müssen im Pilotbetrieb überprüft werden. Kein Rollout oder Aktivieren
ist Bestandteil des lokalen Entwicklungscommits.

Keine neue Datenbankmigration: Die neuen Assessment-Felder liegen im bestehenden
JSON-Journal. Alte Konfigurationen bleiben lesbar (`cheating` wird zu `false`).
Bei einem Rollback zu älterem Code mit strengem Konfigurationsschema zuerst die
neue Konfiguration sichern und das Feld `cheating` entfernen oder das vorherige
Konfigurationsbackup wiederherstellen; Journalbelege und Historie behalten.
