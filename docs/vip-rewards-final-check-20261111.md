# Abschließender lokaler Funktionstest der VIP-Belohnungen

Stand: 11. November 2026, nach der Desktop-/Mobilüberarbeitung `97d17c10`.

## Ergebnis

**82 Backend-Prüfungen und 9 Browsertests bestanden.** Darin enthalten sind
acht neue Spielersimulationen mit HLL- und HLLV-Testprofilen. Es wurde kein neuer
Funktionsfehler festgestellt; Änderungen dieses Checks betreffen Tests und
Dokumentation. Keine Ausrollung oder Änderung an produktiven Servern.

## Simulierte Spielerabläufe

Die Simulationen verwenden die echte Ereigniswarteschlange, den regulären
Worker-Schritt, die Berechnungslogik, das Vergabejournal und die Zustelllogik.
Die Zeit wird vorgerückt; eine Spielstunde oder ein Wochenwechsel benötigt
deshalb keine reale Wartezeit. Der RCON-Adapter speichert VIP-Schreibzugriffe und
private Nachrichten lokal. Netzwerkverbindungen sind im Test ausdrücklich gesperrt.

| Ablauf | Erwartung und geprüftes Ergebnis |
| --- | --- |
| Test-Alice sammelt Unterstützungspunkte | 2.000 Punkte in einer Runde und weitere 3.000 über Folgerunde/weitere Beobachtungen ergeben das eingestellte Ziel von 5.000. Genau 6 Stunden VIP werden gutgeschrieben und privat bestätigt. |
| Vorhandenes VIP | Die 6 Stunden verlängern das bestehende Ablaufdatum. Die vorhandene VIP-Beschreibung bleibt erhalten. |
| Zusätzliche Punkte derselben Woche | Keine zweite Wochenbelohnung. Nach dem nächsten Montag wird der Zähler neu begonnen und eine weitere Belohnung möglich. |
| Seeding, Disconnect und Datenlücke | Während der Pause und in unbeobachteten Intervallen gibt es keine nachträglichen Punkte. Nach einer Unterbrechung muss die fünfminütige Freigabe wieder erreicht werden. |
| Ausschluss | Test-Excluded erreicht sogar mehr Punkte, erhält aber weder Wochenfortschritt noch VIP. |
| Privater Statusbefehl | `!teamvip` antwortet nur dem anfragenden Testspieler, vor Zielerreichung mit `3000 / 5000`. |
| Freiwilliger Teamausgleich | Test-Volunteer meldet sich per `!balance` an, wechselt ins kleinere Team und bleibt volle 15 Minuten. Erst dann folgen 2 Stunden VIP und eine private Nachricht. |
| Ungültiger Teamausgleich | Ein erzwungener Wechsel, ein Disconnect vor Ablauf und ein Wechsel ohne Anmeldung lösen keine Belohnung aus. |
| Eine volle Spielstunde | Test-Regular erfüllt Nahkampf, Waffen-Challenge, Wochenaktivität, Event, Spielzeit-Meilenstein und Rundentreue. Sechs getrennte Gutschriften ergeben zusammen 20 Stunden VIP. |
| Wiederholte Ereignisse und Limits | Ein doppeltes Kill-Ereignis wird nicht doppelt belohnt. Ein weiterer gültiger Nahkampfkill wird wegen des eingestellten Vergabelimits im Journal als übersprungen geführt. |
| Später Beitritt | Der Testspieler mit nur fünf Minuten Teilnahme erhält keine Rundentreue-, Event-, Wochenaktivitäts- oder Stundenbelohnung. |
| Probelauf | Die gleichen berechtigten Vergaben stehen als Vorschau im Journal. **Null VIP-Schreibzugriffe und null Spielernachrichten.** |

Jeder Ablauf wird mit Steam-ID-Testdaten für HLL und 32-stelligen Test-IDs für
HLLV durchgeführt. Der regelmäßige Worker liest zwischen den Schritten seinen
gespeicherten Zustand aus der lokalen Testdatenbank; die Tests halten keine
separate, vereinfachte Belohnungsberechnung vor.

## Formularprüfung

- Aktivieren/deaktivieren und bedingtes Anzeigen der Felder.
- Speichern/verwerfen sowie Beibehalten ungespeicherter Werte beim Tab-/Regelwechsel.
- Wochenziel, VIP-Dauer, Mindestspielzeit, Rundenanteil und Vergabezeiträume.
- Waffenwahl, leere aktive Waffen-Challenge und mehrere ausgewählte Waffen.
- Spielersuche/Ausschlüsse, Zeitzone und konfigurierbarer Statusbefehl.
- Wochenaktivität, Teamausgleich, Meilensteine und Event mit Beginn/Ende.
- Navigation bei Leserechten; bearbeitende Eingaben und Speichern sind gesperrt.
- Desktop-/Mobilbedienung, kein horizontaler Seitenüberlauf, keine Laufzeitfehler
  im zusätzlich geprüften kombinierten Formularablauf.

Die Browser-Vorschau verwendet Mirage und setzt ihre simulierten Daten beim
Neuladen zurück. Die Speicherung in den Backend-Simulationen wird separat geprüft.
Der erfolgreiche Frontend-Build aus dem unmittelbar vorherigen Check gilt
weiterhin: Der Anwendungscode wurde hier nicht geändert.

## Reproduzierbarkeit und Grenzen

- Browsertests: `rcongui/e2e/vip-rewards-local.spec.mjs` (9 Tests, 55,1 Sekunden).
- Backend: `tests/test_vip_rewards.py`, `tests/test_vip_weekly_support.py`,
  `tests/test_vip_rewards_scenarios.py` (82 Tests, 8,04 Sekunden).
- Umgebung: `HLL_MAINTENANCE_CONTAINER=1`, `SERVER_NUMBER=99`, `PYTHONPATH=.`.
- Lokale Nachweise:
  `C:/Users/chris/OneDrive/Dokumente/Autobalancer/outputs/vip-simulation-20261111/backend-final.log`
  und `final/<Testfall>/evidence.json`. Die JSON-Dateien enthalten ausschließlich
  synthetische Spieler, Konfiguration, Journal, VIP-Schreibzugriffe und Nachrichten.
- Browsernachweis für das Eventformular:
  `outputs/next-release-local-20261111/final-check-event-mobile.png` im Workspace.
- Für SQLite werden PostgreSQL-JSON-Spalten lokal abgebildet; prozessübergreifende
  Sperren sind ersetzt. Dieser Lauf prüft weder PostgreSQL-Parallelität noch die
  echte Netzwerkverbindung oder Anzeige der Nachrichten in HLL/HLLV.
- Die vorhandenen isolierten PostgreSQL-/HTTP-Prüfungen sind gesondert in
  `docs/vip-rewards-staging.md` dokumentiert. Sie wurden in diesem lokalen Check
  nicht erneut aufgerufen. Ein kontrollierter Live-Probelauf bleibt ein eigener Schritt.
