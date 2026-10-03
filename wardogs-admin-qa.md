# Wardogs: integrierte Administration und verständliche Berechtigungen

Stand: 3. Oktober 2026

## Ergänzung: sechs Wardogs-Farbstile

Unter „Darstellung & Farben“ bietet Wardogs jetzt Original/Rosé, Eisblau, Smaragd, Bernstein, Amethyst und Schiefer. Das separate Feld `wardogsStyle` erhält die Wahl beim Wechsel zwischen Frontline und Wardogs; bestehende Einstellungen verwenden Rosé. Vorschau, Abbrechen und benutzerbezogenes Speichern nutzen den vorhandenen Ablauf. Ältere Clients dürfen neuere Farbstile und Schnellzugriffe nicht überschreiben, wenn die jeweiligen Felder fehlen.

Akzente, Navigation, Logo, Auswahl-/Fokuszustände und der statische Hintergrundschimmer folgen dem Farbstil. Die hellen Varianten haben eigene dunklere Akzente. Warnungs-, Fehler- und Teamfarben bleiben an die bestehende semantische Palette bzw. den Farbenblindmodus gebunden. Die Administration verwendet dieselben Akzentpaare, synchronisiert die Vorschau ohne Formular-Neuladen und berücksichtigt Hell/Dunkel/System auch separat. Aktualisierte Admin-Skripte erhalten eine neue Asset-Version gegen veraltete Browser-Caches.

Bei der Browserprüfung wurde ein bestehender Konflikt mit mehreren Tabs sichtbar: MUI schrieb bereits die ungespeicherte Modusvorschau in einen gemeinsamen Speicher, während andere Tabs ihren eigenen gespeicherten Modus zurückschrieben. Die Darstellung wird jetzt ausschließlich über die benutzerbezogenen App-Einstellungen gespeichert (`storageManager={null}` im MUI-Provider). Eine helle Vorschau in einem Tab ließ den anderen geprüften Tab dunkel; Abbrechen stellte den gespeicherten Zustand wieder her.

Validierung: 26 Admin-Tests und 12 Appearance-API-Tests erfolgreich; Produktionsbuild, Übersetzungs-, Design-Foundation-, Farbsehmodus- und neuer Wardogs-Farbvertrag erfolgreich. Der Farbvertrag prüft alle sechs Paare auf mindestens 4,5:1 Kontrast gegen ihre hellen/dunklen Flächen und passende Beschriftungsfarben sowie Übereinstimmung zwischen React und Django. Vorhandene Build-Warnung zu großen Chunks bleibt bestehen.

Browser: alle sechs Stile in Hell und Dunkel mit identischen Akzenten im RCON und Admin; Fehlerfarbe bleibt innerhalb eines Modus gleich. Systemmodus stimmt ebenfalls überein. Theme-Wechsel erhält den Wardogs-Farbstil. Eisblau gespeichert, neu geladen und wiedergefunden; anschließend ursprüngliches Rosé/Dunkel wieder gespeichert. Mobile Vorschau bei 390 × 844 ohne horizontalen Überlauf (Dialog 388/388 px, Farbauswahl 346/346 px). Admin-Speichern hat im dunklen Modus dunkle Schrift auf dem farbigen Hintergrund. Keine Benutzer- oder Gruppenrechte verändert.

Aufnahmen: `../output/wardogs-theme/admin/32-wardogs-color-styles-light.png`, `33-wardogs-color-styles-dark.png`, `34-wardogs-color-styles-mobile.png`, `35-wardogs-blue-administration.png`.

## Aktuelle Nachprüfung: handlungsfähige Rollenvorlagen

Die Vorlagen wurden gegen die tatsächlichen API-Berechtigungen und die Loader der betroffenen Seiten abgeglichen. Aktueller Umfang: „Nur lesen“ 28, „Support“ 32, „Moderator“ 49 und „Spielbetrieb“ 57 Rechte. Die weiter unten dokumentierten ursprünglichen Zahlen gehören zum ersten Implementierungsstand.

- Moderator: Kicken war bereits enthalten. Ergänzt sind Truppentfernung/-auflösung, permanente Banns, beide für das gemeinsame Entbannen erforderlichen Rechte, Blacklist-Einträge einschließlich Entsperren, Markierungen sowie operative Autobalancer-Prüfung und Ausführung. Die Autobalancer-Konfiguration ist kein Bestandteil dieser Vorlage.
- Spielerakten: Der Loader ruft `get_bans` auf, wofür temporäre UND permanente Bannlisten-Leserechte erforderlich sind. Beide gehören nun zu den drei Rollen mit Spielerakten. Historische Protokolle erhalten das tatsächlich verwendete `can_view_historical_logs`. Das ungenutzte alte `can_view_players` wurde entfernt; `can_view_get_players` bleibt enthalten.
- Spielbetrieb: Kartenwechsel und -folge, Rotation einschließlich Shuffle, Kartenziele, Wetter, Runden-/Aufwärmzeit, Kartenabstimmungen einschließlich Konfiguration und aktueller Abstimmungssteuerung. Willkommensnachrichten und die aktuelle Kampagnen-Seite einschließlich Status und Nachrichtentests sind enthalten. Deren Config-API benötigt andere Rechte als die bisher allein abgedeckte Broadcast-API. Die Vorlage erbt nicht mehr pauschal die gesamte Spielerakten-Rolle. Spielersanktionen lassen sich durch zusätzliches Übernehmen von „Moderator“ ergänzen.
- Formular: ausdrückliche Vorschau vor der Übernahme, Schaltfläche „Vorlage übernehmen“, sichtbare Bestätigung der Formularauswahl und Hinweis auf das anschließende Sichern. Die Kombination ergänzt nur fehlende Rechte; die Rücknahme entfernt nur die letzte Ergänzung.

25 Django-Tests erfolgreich. Sie prüfen neben den bisherigen Admin-Verträgen echte Django-Gruppenvererbung gegen die aktuellen `ENDPOINT_PERMISSIONS` und Autobalancer-Dekoratoren, einschließlich mehrteiliger Voraussetzungen für Entbannen, Blacklist-Entsperren, Kartenfolge und Truppwechsel. Rollenabgrenzungen und Kombination wurden ebenfalls geprüft. JavaScript-Syntaxprüfung erfolgreich; keine Spielserveraktion ausgelöst.

Browserprüfung in einem separaten, ungespeicherten Gruppenformular: Moderator-Vorschau lässt Auswahl bei 0, Übernahme ergibt 49; Spielbetrieb ergänzt 39 auf insgesamt 88; Rücknahme stellt exakt die vorherigen 49 IDs wieder her. Spielbetrieb allein ergibt 57, Rücknahme 0. Bei 390 × 844 kein horizontaler Überlauf (Hauptseite 390/390 px, eingebettetes Formular 348/348 px). Das bereits offene Benutzerformular wurde nicht neu geladen oder gespeichert. Screenshots: `../output/wardogs-theme/admin/30-roles-operations-applied.png` und `31-roles-mobile.png`.

## Umsetzung

- `/administration/*` verwendet die echte RCON-Navigation, Schnellzugriffe, Toolbar und Darstellungseinstellungen. Die vorhandenen Django-Formulare werden innerhalb dieses Rahmens eingebettet. Anmeldung, Berechtigungsprüfung, Validierung, CSRF und Speicherung bleiben bei Django.
- Reiter für Übersicht, Benutzer, Gruppen, API-Schlüssel und mobile Geräte folgen den tatsächlich erlaubten Verwaltungsbereichen. Der Navigationseintrag setzt `is_staff` voraus.
- Das Wardogs-Benutzerformular ordnet Anmeldung und persönliche Daten nebeneinander an. Zugang/Status, Gruppen, Einzelrechte und Kontodaten bilden getrennte Abschnitte. Auf schmalen Bildschirmen werden die Spalten untereinander angeordnet.
- Gruppen sind direkt auswählbar und durchsuchbar. Die Anzahl ihrer Rechte wird angezeigt. Die zugrunde liegende Django-Mehrfachauswahl bleibt für Validierung und Übermittlung erhalten.
- Berechtigungen erhalten deutsche Bezeichnungen und konkrete Beschreibungen, Themenbereiche, Suche, einen Filter für zugewiesene Rechte und optional technische Kennungen. Direkte Rechte und Rechte aus Gruppen werden getrennt gezählt; Gruppenherkunft, Vollzugriff und inaktive Konten werden erläutert. Es werden keine Rollen oder Zugriffe automatisch vergeben.
- Die Sprache der eingebetteten Verwaltung folgt der RCON-Auswahl (Deutsch/Englisch). Die ausführlichen Beschreibungen sind derzeit Deutsch; Englisch verwendet überwiegend die vorhandenen Originalbezeichnungen mit ergänzenden Hinweisen.
- Wardogs-Farben und Formularanordnung sind vom bisherigen Theme getrennt. Die neue Rechteerklärung ist eine funktionale Erweiterung der Rechteauswahl.

## Überprüfung

- 15 Django-Tests erfolgreich: eingeschränkte Staff-Konten, Nicht-Staff, ursprüngliche Frontline-Übersicht, fehlende Darstellungspräferenzen, neun Formular-/Listenansichten, CSRF auch bei eingebetteten POSTs, Formularvalidierung, vollständige Zuordnung aller aktuellen `can_*`-Rechte, Rechte-Speicherung ohne Erweiterung, validierte Gruppenwahl, Same-Origin-Einbettung, Suche und Sprachwechsel.
- Produktionsbuild erfolgreich mit `REACT_APP_API_URL=/api/`. Bestehende Warnung zu großen JavaScript-Chunks bleibt bestehen.
- Navigation-, Design-Foundation-, Übersetzungs- und CSRF-Vertragsprüfungen erfolgreich; Syntaxprüfung der neuen Browser-Skripte erfolgreich.
- Browserprüfung bei 1600 × 1000 und 390 × 844: Übersicht, Benutzerliste/-formular, Gruppenliste/-formular, API-Liste und Geräteliste. Mobile Benutzerformulare und Listen haben keinen Seitenüberlauf; breite Tabellen scrollen innerhalb ihrer Tabellenfläche.
- Suchfilter ändern keine Auswahl. Testweise gesetzte direkte Rechte und Gruppen wurden vor dem Verlassen zurückgesetzt und nicht gespeichert. Gruppenvererbung bleibt beim Filtern erhalten. Verwaltungsreiter bleiben nach dem Laden auf dem gewählten Bereich.
- Behoben: alte Django-Maximalbreite trotz ausgeblendeter Seitenleiste, mobile Formbreiten, native Zwei-Listen-Gruppenauswahl, abgeschnittene Suchfelder, Rücksprung beim Reiterwechsel sowie ein bestehender Nullzugriff im API-Schlüssel-Formskript.

## Lokale Vorschau und Grenzen

Die Prüfung verwendet echte Projektmodelle, Admin-Klassen, Vorlagen und Formulare mit Django 4.2.30. Dafür läuft `scripts/preview_admin.py` auf `127.0.0.1:8042` mit einer isolierten SQLite-Demodatenbank. Der Vite-Proxy auf Port 3042 wird über die ignorierte `.env.local` mit `VITE_CRCON_ADMIN_URL=http://127.0.0.1:8042` verbunden.

Start: `python scripts/preview_admin.py`. Tests: `python scripts/preview_admin.py --test`. Benötigt Django aus den Projektanforderungen; für diese Prüfung liegt eine lokale Umgebung unter `../output/wardogs-admin-venv` vor.

Demodaten, zufällige lokale Zugangsdaten und SQLite liegen ausschließlich unter `../output/wardogs-admin-preview`. Die Vorschau lädt keine Produktionskonfiguration und verbindet sich mit keinem Spielserver. Produktion und echte Benutzerrechte wurden nicht verändert. Eine Prüfung gegen den vollständigen produktiven Backend-Stack steht deshalb noch aus.

Screenshots: `../output/wardogs-theme/admin/`, insbesondere die finalen Benutzer- und Berechtigungsansichten sowie die mobilen Aufnahmen `15-mobile-users-final.png` und `16-mobile-rights-final.png`.

## Ergänzung: Wardogs-Hintergrund

Der gemeinsame Seitenhintergrund erhält den roten Schimmer und sparsame Lichtpunkte aus der Referenz. Er ist statisch, wird mit CSS-Verläufen dargestellt und bleibt beim Scrollen im Hintergrund. Die eingebettete Administration ist zwischen den Karten transparent; Karten und Formulare behalten ihre eigenen Flächen. Im hellen Modus wird der Effekt abgeschwächt, Frontline bleibt unverändert.

Geprüft auf Dashboard und Administration, mobil bei 390 × 844 ohne Seitenüberlauf sowie über die Vorschau für Hell und Frontline. Produktionsbuild und Design-Foundation-Prüfung erfolgreich. Keine zusätzlichen Bilddateien oder Animationen.

## Ergänzung: Rollenvorlagen für Gruppen

Gruppenformulare bieten „Nur lesen“ (24 Rechte), „Support“ (28), „Moderator“ (35) und „Spielbetrieb“ (50) als Ausgangspunkt. Jede Vorlage zeigt ihre Beschreibung, die vollständige Rechtevorschau und die Anzahl neu hinzukommender Rechte. Die Übernahme ergänzt die Auswahl; vorhandene Rechte bleiben erhalten. Die letzte Ergänzung lässt sich zurücknehmen. Erst das normale Sichern des Formulars schreibt die Gruppenrechte.

Die Vorlagen verwenden explizite Listen vorhandener CRCON-Rechte, begrenzt auf die zulässigen Optionen des Formularfelds. Sie vergeben keinen Administrator- oder Staff-Status und keine Kontenverwaltung, Zugangsdatenverwaltung oder rohen RCON-Befehle. Neue Berechtigungen werden nicht automatisch in Vorlagen aufgenommen. Direkte Benutzerrechte bleiben individuell; wiederverwendbare Rollen werden über Gruppen zugewiesen.

18 Django-Tests erfolgreich, einschließlich Vorlagenabgleich mit vorhandenen Berechtigungen, Begrenzung auf erlaubte Feldoptionen und unveränderter Gruppenrechte beim Öffnen. JavaScript-Syntaxprüfung und Diff-Prüfung erfolgreich. Im Browser geprüft: Vorschau ohne Auswahländerung, Übernahme mit überschneidenden und zusätzlichen Einzelrechten (2 → 36), Rücknahme auf die ursprünglichen 2 Rechte sowie Synchronisierung der nativen Formularwerte. Testentwurf verworfen; keine Gruppe oder Rechtezuweisung gespeichert. Responsive Prüfung bei 390 × 844 ohne Seitenüberlauf. Screenshot: `../output/wardogs-theme/admin/25-role-presets-final.png`.

Die lokale Demoinitialisierung ergänzt Standardrechte nur noch bei erstmaliger Anlage einer Demo-Gruppe; vorhandene Gruppen werden beim Serverstart nicht verändert.

## Ergänzung: Rechte gesammelt an- und abwählen

Die Rechteauswahl bietet globale Aktionen sowie Aktionen pro aufgeklapptem Themenbereich. Ohne Filter wirken sie auf alle Rechte, einschließlich zugeklappter Bereiche. Mit Suche oder „Nur vergebene Rechte“ ändern sie ausschließlich die passenden Treffer. Beschriftung, Anzahl der betroffenen Rechte und deaktivierte Aktionen bei leerer Auswahl machen den Umfang sichtbar. Die ursprünglichen Django-Felder werden synchronisiert; gespeichert wird weiterhin ausschließlich über das Formular.

Im Browser geprüft: alle 263 Rechte auswählen und wieder abwählen; drei VIP-Suchtreffer ändern, während ein ausgeblendetes Einzelrecht erhalten bleibt; alle 16 VIP-Rechte über die Bereichsauswahl ergänzen und bei aktivem Zuweisungsfilter entfernen; beide Aktionen bei null Treffern deaktiviert. Im Benutzerformular bleiben nach der Sammelabwahl alle zwei geerbten Gruppenrechte wirksam und die Gruppenmitgliedschaft unverändert. Keine Änderungen gespeichert. JavaScript-Syntaxprüfung erfolgreich.

Mobil bei 390 × 844 ohne Seitenüberlauf; Aktionen umbrechen bei Bedarf. Screenshots: `../output/wardogs-theme/admin/26-bulk-permissions-mobile.png` und `../output/wardogs-theme/admin/27-bulk-permissions-final.png`.

## Ergänzung: Kategorieauswahl direkt in der Kopfzeile

Jeder Themenbereich hat nun eine stets sichtbare Checkbox mit leerem, vollständigem oder gemischtem Zustand. Die Auswahl funktioniert auch bei geschlossenen Bereichen. Checkbox und Aufklappen sind getrennte Bedienelemente; die Checkbox besitzt eine Klickfläche von 44 × 46 Pixeln. Bei aktiven Filtern werden weiterhin nur passende Rechte geändert, im Benutzerformular ausschließlich direkte Rechte.

Browserprüfung mit Maus und Tastatur: VIP-Bereich geschlossen auswählen (16 Rechte) und abwählen, gemischten Zustand nach einem einzelnen ausgewählten Recht erkennen, Teilmenge vervollständigen und andere Kategorien unverändert lassen. Gefilterte Kategorieauswahl erfasst nur die drei VIP-Suchtreffer. Native Formularwerte und Zähler bleiben synchron. Mobile Prüfung bei 390 × 844 ohne horizontalen Überlauf; Theme-Formularregeln verschieben die Checkboxen nicht. Alle Testauswahlen verworfen, keine Rechte gespeichert. JavaScript-Syntaxprüfung erfolgreich. Screenshots: `../output/wardogs-theme/admin/28-category-selection-mobile.png` und `../output/wardogs-theme/admin/29-category-selection-final.png`.

## Ergänzung: Bedienhilfe und API-Referenz (03.10.2026)

Unter `/documentation` gibt es eine integrierte deutsch/englische Bedienhilfe mit sieben Themen: Einstieg, Moderation, Spielbetrieb, Nachrichten/Automatisierung, Benutzer/Rollen/Rechte, Darstellung/QuickIcons und Fehlerhilfe. Die Rollenbeschreibung entspricht den aktuellen expliziten Vorlagen, einschließlich permanenter Banns und Autobalancer-Ausführung für Moderator sowie der Kombination mit Spielbetrieb. Die Dokumentation ist über Navigation, Benutzermenü, globale Seitensuche und einen Hilfe-Link im Admin-Kopf erreichbar; sie kann auch als QuickIcon gewählt werden.

Die API-Referenz lädt `get_api_documentation` vom konfigurierten Backend. Sie zeigt Methoden, Quellbeschreibungen, Parameter samt Typen und Standardwerten, Rückgabetypen sowie die gemeinsam erforderlichen Rechte. Suche, Methodenfilter, Pagination und direkte URLs erleichtern den Zugriff. Suchfilter und ausgewählter Endpunkt bleiben beim Neuladen erhalten. Ein aufklappbarer Einstieg erklärt API-Schlüssel, Sitzung/CSRF, Anfragebeispiele, Antwortumschlag und Fehlercodes. Die Referenz führt keine RCON-Aktionen aus. Nicht dokumentierte Felder und fehlende Beschreibungen werden ausdrücklich als solche kenntlich gemacht.

Die lokale Mirage-Vorschau verwendet einen gekennzeichneten Snapshot der 385 Endpunktregistrierungen dieses Quellstands, einschließlich mobiler Endpunkte. Dafür wurden ausschließlich Wrapper und Signaturen introspektiert; keine Spielbefehle ausgeführt. Produktion verwendet keinen Fallback auf diesen Snapshot.

Prüfung:
- Produktionsbuild erfolgreich; bekannte Warnung zu großen Chunks bleibt.
- Vier API-Referenz-Tests erfolgreich: reales Katalogformat, mehrere erforderliche Rechte, Filterkombinationen, ungültige Antworten und ältere unvollständige Einträge.
- i18n-, Navigation-, Design-Foundation- und Page-Semantics-Prüfungen erfolgreich.
- Browser: Hilfesuche, leere Trefferliste/Zurücksetzen, API- und Berechtigungssuche, Methodenfilter, Direktlink und Reload, Beispiele, deutscher/englischer Inhalt sowie Admin-Hilfelink geprüft.
- Desktop 1280/1600 px und Smartphone 390 × 844 geprüft. Mobil ersetzt eine Auswahl die Seitenliste; kein horizontaler Überlauf (380 px Inhalt / 380 px Scrollbreite). Tabellen erhalten eine ausreichend breite erste Spalte. Sprache und Viewport nach der Prüfung zurückgesetzt.
- Zusätzliche globale Bundle-Budget-Prüfung meldet eine Überschreitung: etwa 1.590 kB raw / 506 kB gzip initial, gegenüber 1.525 / 500 kB Budget. Diese Größenprüfung ist nicht bestanden. Die Dokumentationsseite selbst wird über eine Lazy-Route geladen; die Überschreitung wurde hier nicht durch eine Änderung der Grenzwerte kaschiert.
- Keine Gruppen, Berechtigungen, API-Schlüssel oder Servereinstellungen geändert.

Screenshots: `../output/wardogs-theme/admin/36-documentation-help-desktop.png`, `37-documentation-api-mobile.png`, `38-documentation-api-desktop.png`.


## Ergänzung: Beschreibungen der API-Referenz (03.10.2026)

Alle 385 registrierten Endpunkte erhalten Erläuterungen auf Deutsch und Englisch. Die Texte wurden anhand der jeweiligen Implementierung ergänzt, einschließlich Konfigurationsschema, Validierung, Speichern, Moderationsaktionen, Betriebsdiagnose und mobiler API. Unterschiede wie Simulation gegenüber echtem Nachrichtenversand, Freigabe gegenüber späterer Ausführung und Gameserver-Reconnect gegenüber Gameserver-Neustart werden ausdrücklich erklärt.

Der Backend-Katalog liefert die Texte als zusätzliches Feld `description_translations`. Originaldocstrings, Methoden, Parameter und Berechtigungen bleiben unverändert. Die Oberfläche wählt die aktuelle Sprache und hält Originalhinweise aufklappbar bereit. Die Suche berücksichtigt beide Texte. Ältere Backends funktionieren weiter mit ihren vorhandenen Docstrings; unbekannte Endpunkte bekommen keine geratenen Beschreibungen. Der WebSocket-Pfad wird mit seinem tatsächlichen Präfix `/ws/` angezeigt.

Prüfung:
- Echte Backend-Introspektion in isolierten Testeinstellungen: 385 eindeutige Einträge mit beiden Sprachen, bestehende Metadaten exakt unverändert; Vorschau-Snapshot daraus aktualisiert. Keine Spielbefehle ausgeführt.
- 8 Frontend-Tests für Katalog, Filter, Sprachwechsel, technische Quelltexte, ältere Antworten und HTTP-/WebSocket-Pfade bestanden.
- 3 Python-Tests für vollständige Übersetzungen, unveränderte Metadaten und unbekannte Endpunkte bestanden.
- 4 QuickIcon-Tests, 26 Admin-Tests, 12 Appearance-API-Tests sowie i18n-, Wardogs-Farb-, Navigations-, Design- und Semantikprüfungen bestanden.
- Produktionsbuild erfolgreich. Das bekannte globale Bundle-Budget bleibt überschritten: 1.590,23 kB raw / 505,82 kB gzip statt 1.525 / 500 kB. Grenzwerte unverändert.
- Browser: deutsche Suche nach „Teamwechsel“, Sprachwechsel DE/EN, technische Hinweise per Tastatur, Desktop 1600 × 1000 und Mobil 390 × 844 geprüft. Mobil 390 px Viewport und Scrollbreite, kein horizontaler Überlauf. Sprache und Viewport nach der Prüfung zurückgesetzt.
- Screenshots: `../output/wardogs-theme/admin/39-api-descriptions-desktop.png` und `40-api-descriptions-mobile.png`.

## Ergänzung: Eigenes Passwort und Wiederherstellung (04.10.2026)

`/account/password` ist eine native Kontoseite im jeweils gewählten RCON-Theme. Das Benutzermenü und die bisherigen `/accounts/password_change`-Adressen führen dorthin. Die Seite zeigt das eigene Konto, die tatsächlich konfigurierten Django-Passwortregeln und die Auswirkungen auf bestehende Sitzungen. Formular und Hinweise stehen auf Desktop nebeneinander, mobil untereinander.

Die Anmeldung bietet „Passwort vergessen?“. Die öffentlichen Seiten für E-Mail-Anforderung und neues Passwort unterstützen Deutsch/Englisch, das gewählte Theme und den Wardogs-Hintergrund. Django übernimmt Passwortprüfung, CSRF, Tokenprüfung und Sitzungsverwaltung. Die Links gelten 30 Minuten, werden nach Verwendung ungültig und enthalten ausschließlich den konfigurierten HTTPS-Ursprung. Der Token wird vor Anzeige des Formulars aus der URL entfernt und an die Sitzung gebunden. Es gibt keine automatische Anmeldung nach einem Reset. Antworten auf E-Mail-Anforderungen verraten nicht, ob die Adresse einem aktiven Konto zugeordnet ist; Versand und Anfragen sind begrenzt. Fehlerausgaben enthalten keine Passwörter, Tokens oder Empfänger.

SMTP ist bewusst konfigurierbar und standardmäßig deaktiviert. `default.env`, beide Compose-Vorlagen, das bestehende Mobile-Admin-Overlay und die Bedienhilfe enthalten die Einrichtung. Die lokale Admin-Vorschau verwendet weiterhin ausschließlich ihre isolierten Demo-Konten und verschickt keine E-Mails. Zugangsdaten aus der freigegebenen lokalen Datei wurden außerhalb von Git hinterlegt; keine Zugangsdaten befinden sich in diesem Commit. Für die Aktivierung nach Deployment müssen der öffentliche HTTPS-Ursprung und `CRCON_PASSWORD_RESET_ENABLED` gesetzt werden.

Prüfung:
- 43 isolierte Django-Tests bestanden (26 Admin, 17 Passwort/Konto). Abgedeckt sind unter anderem fremde Benutzer-IDs, falsches altes Passwort, schwache/nicht übereinstimmende Passwörter, CSRF, Sitzungswechsel, inaktive/externe Konten, ungültige/abgelaufene/erneut verwendete Links, begrenzte Anfragen sowie SMTP- und Cache-Ausfall. Testmails verbleiben im Arbeitsspeicher der Tests.
- 5 Frontend-Anfragetests bestanden: erlaubte POST-Felder, CSRF-Pflicht, keine Passwörter in URLs, kein falscher Erfolg bei HTML-Antworten, kein automatisches Wiederholen von E-Mail-Anforderungen.
- 5 bestehende Nginx-/Compose-Tests, i18n-, CSRF-, Navigations-, Design- und Semantikprüfungen bestanden. Alle drei bearbeiteten Compose-Dateien sind syntaktisch geprüft, einschließlich des vorhandenen `!reset`-Tags.
- Produktionsbuild erfolgreich. Bekanntes globales Bundle-Budget weiterhin überschritten: 1.596,83 kB raw / 507,87 kB gzip statt 1.525 / 500 kB. Grenzwerte unverändert; neue Kontoseiten werden über Lazy-Routen geladen.
- Browserprüfung: Kontoseite bei 1280 px und 390 × 844, mobil genau 390 px Scrollbreite; öffentliche Wiederherstellung, ungültiger Link, Rückweg zur Linkanforderung und Einstieg über die Anmeldung; DE/EN geprüft. Keine echten Kontopasswörter verändert und keine E-Mails angefordert.
- Nach ausdrücklicher Freigabe SMTP-Anmeldung als `noreply@fln.gg` an `mail.fln.gg:587` erfolgreich (235), TLS 1.3 und gültiges Zertifikat. Keine E-Mail verschickt. Der zuerst genannte Host `smtp.fln.gg` war nicht auflösbar; `mail.fln.gg` wurde anhand der Postfix-Konfiguration des genannten Servers ermittelt. Keine produktiven Servereinstellungen geändert.
- Die Nginx-Admin-Route wurde auf `/admin` und dessen Unterpfade begrenzt, damit `/administration` auch im Produktionsbetrieb im React-Router bleibt. Die bestehenden `/accounts`-Endpunkte bleiben beim Django-Backend.
- Screenshots: `../output/wardogs-theme/admin/41-password-change-desktop.png`, `42-password-change-mobile.png`, `43-password-recovery-mobile.png`, `44-password-reset-invalid-mobile.png`.

## Ergänzung: Administration im Frontline-Theme (04.10.2026)

Die Verwaltungsübersicht und die gegliederten Benutzerformulare stehen jetzt in beiden Themes zur Verfügung. Das gemeinsame Layout übernimmt Abstände, responsive Spalten, Tabellen, Filter und Rechteauswahl. Frontline erhält seine eigenen kantigen Flächen, verdichteten Überschriften und Akzentfarben; Wardogs behält die runden Karten. Die eingebettete Verwaltung übernimmt die tatsächlich aufgelöste React-Palette einschließlich Hell/Dunkel, eigener Akzentfarbe und Farbsicht-Einstellungen. Beim Theme-Wechsel werden vorherige Inline-Farben entfernt. Die eigenständige Verwaltung hat passende Frontline-Fallbacks und führt angemeldete Nutzer beider Themes in die integrierte Ansicht.

Prüfung:
- 43 isolierte Django-Tests bestanden, einschließlich der aktualisierten Prüfung für Frontline-Übersicht und gegliedertes Benutzerformular. Berechtigungs-, CSRF- und Passworttests bleiben erfolgreich.
- Produktionsbuild, JavaScript-Syntaxprüfung und Diff-Prüfung erfolgreich. Die bekannte Build-Warnung zu großen Chunks besteht weiterhin.
- Browser bei 1440 × 1000: Übersicht, Benutzerliste/-formular, Gruppenliste/-formular, API-Schlüsselliste und Geräteliste geprüft. Suchleisten, Sammelaktionen, Filter und Formulare verwenden die Frontline-Palette.
- Frontline-Hell sowie Wardogs-Hell/Dunkel per ungespeicherter Vorschau geprüft: helle Frontline-Flächen und dunkler Text; Wardogs-Karten wieder mit 12 px Radius und ohne zurückbleibende Frontline-Inline-Farbe. Danach Vorschau verworfen.
- Mobil bei 390 × 844: Übersicht und Benutzer-/Rechteformular geprüft. Eingebetteter Inhalt 356 px breit, Scrollbreite ebenfalls 356 px. Kategorieauswahl behält ihre 44 × 46 px Klickfläche. Temporäre Viewport-Einstellung zurückgesetzt.
- Keine Benutzer, Gruppen, Rechte, Zugangsdaten oder produktiven Einstellungen gespeichert. Die bereits akzeptierte native Passwortseite wurde nicht verändert.
- Screenshots: `../output/wardogs-theme/admin/45-frontline-administration-desktop.png`, `46-frontline-user-desktop.png`, `47-frontline-permissions-mobile.png`, `48-frontline-administration-mobile.png`.
