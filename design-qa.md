+# Design QA — Konfigurationsformulare und Live-Einsatz

## Vergleichsbasis Konfigurationsformulare

- Referenz: finale Nutzervorlage (`codex-clipboard-79491ed8-28e5-4c2b-b580-7dfa4d38f2fb.png`)
- Referenzgröße: 1683 × 935 Pixel
- Implementierung: `/settings/automods/no-leader` im lokalen Demo-Modus
- Prüfzustand: Deutsch, Formularmodus, Abschnitt „Warnen“, Testbetrieb, ungespeicherte Änderung
- Implementierungsaufnahme: `no-leader-warning-final-qa-v3.png`
- Gemeinsamer Vergleich: `no-leader-reference-vs-implementation-final-v2.png`

## Visueller Vergleich Konfigurationsformulare

Referenz und Implementierung wurden bei identischer Viewportgröße in einer gemeinsamen Side-by-Side-Grafik verglichen. Die Implementierung übernimmt die wesentlichen sichtbaren Merkmale der gewählten Richtung:

- kompakter Seitentitel mit Status direkt am Titel;
- Formular/JSON-Umschaltung unterhalb des Kopfs;
- zusammenhängende Drei-Spalten-Arbeitsfläche ohne getrennte Karten;
- sieben nummerierte Konfigurationsschritte mit aktiver Stufe;
- Warnmodus mit den Optionen Überspringen, Anzahl und Unbegrenzt;
- numerische Schrittsteuerungen für Anzahl und Intervall;
- verständliche Platzhalter und eine aufgelöste Spielnachrichten-Vorschau;
- Wirkungskette und Erreichbarkeitsprüfung in der Zusammenfassung;
- direkt angeschlossene, sticky Speicherleiste mit eindeutigem Entwurfsstatus.

Die bestehenden globalen Navigations- und Matchstatus-Komponenten bleiben unverändert und folgen weiterhin dem aktuellen CRCON-Layout.

Die Vorlage zeigt im rechten Bereich exemplarisch „Kick kann nicht erreicht werden“. Die Implementierung berechnet diesen Status dagegen aus den tatsächlich gewählten Warn-, Bestrafungs- und Kick-Zeiten. Im geprüften Zustand ist „Kick ist erreichbar“ daher die fachlich korrekte, bewusst beibehaltene Ausgabe.

## Responsive und funktionale Prüfung Konfigurationsformulare

- 1683 × 935: Drei-Spalten-Layout und sticky Aktionsleiste geprüft.
- 768 × 900: Formular und Zusammenfassung umbrechen ohne abgeschnittene Inhalte.
- 390 × 844: mobile Abschnittsnavigation, Formularelemente und Aktionsbereich geprüft.
- 1440 Pixel und 390 Pixel: kein horizontaler Seitenüberlauf.
- Formular → JSON → Formular: Entwurf und rohe Backend-Platzhalter bleiben erhalten.
- Deutsche Anzeigenamen wie `{Spielername}` und `{Truppname}` werden bidirektional auf die unveränderten Backend-Platzhalter abgebildet.
- Abschnittsnavigation: Vorschau und Zusammenfassung reagieren auf Warnmodus, Anzahl und Intervall.
- Änderung → Zurücksetzen: Dirty-State wird gesetzt und anschließend korrekt entfernt.
- Speichern im lokalen Demo-Modus: Werte bleiben nach einem erneuten Laden erhalten.
- Ungültiges JSON: Editor meldet den Fehler, ohne den letzten gültigen Entwurf zu verlieren.
- HLL und HLL: Vietnam: beide Spielprofile durch den gleichen Formular- und Validierungsfluss geprüft.
- Zielgerichtete E2E-Suite: 12 von 12 Tests erfolgreich.
- Produktions-Build: erfolgreich.
- `git diff --check`: erfolgreich.

## Ergebnis Konfigurationsformulare

Keine offenen P0-, P1- oder P2-Designabweichungen im umgesetzten Formularfluss.

## Formularfamilie

Die freigegebene Arbeitsfläche wurde anschließend auf die weiteren schema-basierten
Konfigurationsseiten übertragen. Visuell geprüft wurden die Referenz und die lokale
Seeding-Seite in derselben Vergleichsansicht. Dabei bleiben Seitentitel, Status,
Formular/JSON-Umschaltung, nummerierte Abschnittsnavigation, zusammenhängende
Drei-Spalten-Arbeitsfläche, Wirkungskette und Speicherleiste konsistent. Der Inhalt
der Schritte wird fachlich aus dem jeweiligen Schema gebildet und nicht künstlich
an die No-Leader-Felder angeglichen.

Direkt abgedeckte Seiten:

- Level-Regeln
- Seeding-Regeln
- Solo-Panzer verhindern
- VAC- und Spielsperren prüfen
- Teamkill-Sperre beim Beitritt
- Namensfilter
- Seeder-VIP-Belohnung
- Abgelaufene VIPs bereinigen

Weitere Konfigurationen mit JSON-Schema verwenden denselben Arbeitsflächen-Rahmen
und werden automatisch in verständliche Abschnitte gruppiert. Verschachtelte
Seeder-VIP-Felder bleiben im visuellen Formular editierbar; die vollständige
Rohkonfiguration bleibt im erweiterten JSON-Modus erreichbar.

- Acht benannte Desktop-Seiten: Navigation, Zusammenfassung und Speichern geprüft.
- Seeding und Seeder-VIP: 390 × 844 ohne horizontalen Überlauf geprüft.
- Neue Formularfamilie: 11 von 11 E2E-Tests erfolgreich.
- Bestehende No-Leader-Seite: 12 von 12 Regressionstests erfolgreich.
- Produktions-Build: erfolgreich.

## Live-Einsatz — Option 1

- Referenz: `exec-61a73ce0-5b1a-48a7-9aa9-4c09f0575469.png`
- Implementierung: `/views/live` im lokalen Demo-Modus, 1683 × 935 Pixel
- Gemeinsamer Vergleich: `frontline-live-design-qa.png`
- Geteilte Spieler-/Protokoll-Arbeitsfläche, Schnellfilter und kompaktes Einsatzprofil geprüft.
- Spieler-, Protokoll- und geteilte Ansicht wechseln ohne Datenverlust.
- Spielerauswahl blendet Nachricht, Bestrafung, Kick und weitere Aktionen als sticky Aktionsleiste ein.
- Aktionsdialog für ausgewählte Spieler öffnet korrekt, ohne bei der Prüfung eine Spielaktion auszuführen.
- Unter 1100 Pixel wird die gleichzeitige Teilung deaktiviert; Spieler und Protokoll bleiben über die Ansichtsumschaltung erreichbar.
- Produktions-Build erfolgreich; keine Browser-Laufzeitfehler festgestellt.
- Keine offenen P0-, P1- oder P2-Designabweichungen.

## Live-Protokoll — kompakte Ereignisdarstellung

- Die geteilte Arbeitsfläche priorisiert die Spielerliste mit einem Verhältnis von 72/28; das Protokoll kann weiterhin maximiert werden.
- Die Seitenzuordnung wird platzsparend über die Farbe des Spielernamens dargestellt. Die redundante Angabe `(axis|allies/Spieler-ID)` wird unabhängig von Groß-/Kleinschreibung aus Anzeige und Kopiertext entfernt.
- Spielernamen bleiben vollständig sichtbar, sind per Tastatur erreichbar und öffnen weiterhin das Spielerprofil.
- Kill- und Teamkill-Ereignisse verwenden Pfeil und neutrales Waffensymbol; der unveränderte Waffenname steht als Tooltip bereit.
- Chat-Ereignisse zeigen den Spieler in einer eigenen Zeile und die Nachricht darunter. Lange Texte brechen in der geteilten wie in der maximierten Ansicht um.
- Der Kopierbutton übernimmt den bereinigten Nachrichtentext ohne versteckte Spieler-ID; bei nicht verfügbarer Clipboard-API bleibt der manuelle Fallback erreichbar.
- Geteilte Ansicht visuell und per DOM-Messung geprüft: Protokollbreite 405 Pixel, keine horizontale Überbreite, lange Zeilen erhöhen die Ereignishöhe korrekt.
- Maximierte Protokollansicht geprüft: kein horizontaler Seitenüberlauf und keine gekappten Nachrichten.
- Frischer Browserstart: keine neuen Laufzeitfehler; verbleibend ist ausschließlich die bekannte React-Router-Zukunftswarnung.
- Semantische Ereignissymbole im Live-Protokoll verwenden gezielt Font Awesome: Sprechblasen für Chat, Fadenkreuz für Kills, Totenkopf für Teamkills, Richterhammer für Admin-Aktionen und Flagge für Match-Ereignisse. Die Fraktion wird direkt am Spielernamen dargestellt; die übrige Bedienoberfläche bleibt bei MUI.
- Kill-Darstellung mit Font-Awesome-Pfeil und -Waffensymbol geprüft; der exakte Waffenname bleibt im Tooltip erhalten. Auch Kopieren und Kopiert-Bestätigung verwenden innerhalb des Live-Protokolls die kompakteren Font-Awesome-Symbole.
- Geteilte Ansicht mit Chat- und Kill-Filter erneut geprüft: alle neuen Symbole werden bei 405 Pixel Protokollbreite vollständig dargestellt; horizontaler Überlauf bleibt bei 0 Pixel.
- Die separate Fraktionsmarke wurde zugunsten von mehr Textbreite wieder entfernt. Stattdessen sind die Spielernamen selbst eingefärbt: Achsenmächte rot, Alliierte blau; bei Kills wird jede beteiligte Person separat ausgewertet, bei Teamkills bleibt die gemeinsame Seite erhalten.
- Die Fraktionszuordnung bleibt trotz der kompakten Darstellung über Tooltip und zugängliche Namensbeschriftung lesbar. Im Kill-Filter wurden 0 Lobby-Zuordnungen und 0 Pixel horizontaler Überlauf gemessen.
- Die zusätzlichen Live-Protokoll-Symbole erhöhen den komprimierten Live-Chunk um rund 1,7 kB.
- Produktions-Build erfolgreich.

## Live-Spielertabelle — kompakte Einsatzansicht

- Die geteilte Spieler-/Protokollansicht ist bei jedem neuen Seitenaufruf der Standard; Fokusansichten bleiben innerhalb der laufenden Sitzung auswählbar.
- Die Mindestbreiten der Sammelspalten wurden nach Inhalt priorisiert: Name, Team/Trupp/Rolle, Kampf/Risiko und Status benötigen keine pauschalen 30 Zeichen mehr.
- Spielernamen zeigen ihre Seite direkt über die Textfarbe: Achsenmächte rot, Alliierte blau. Lange Namen werden gekürzt und bleiben vollständig per Tooltip lesbar.
- Die redundante Fraktionsgrafik in der Zuordnung wurde entfernt; Team, Trupp und Rolle bleiben ausgeschrieben und bei langen Werten per Tooltip zugänglich.
- Statuswerte verwenden kompakte, beschriftete Symbole mit Tooltip und `aria-label`; VIP, Beobachtung, Warnung und aktive Sperre bleiben unterscheidbar.
- Schnellfilter können bei geringer Breite umbrechen, statt eine schwer erreichbare horizontale Scrollleiste zu erzeugen.
- In der geteilten Ansicht gemessen: Spielertabelle 1069 Pixel breit, 0 Pixel horizontaler Überlauf, Name und Aktionsspalte bleiben sticky erreichbar.
- Der Test erfolgt mit „Alle Spieler“, nicht mit dem leeren Filter „Auffällig“: Eine einzeln ausgewählte Zusatzspalte erzeugt exakt eine zusätzliche Tabellenspalte und wechselt nachvollziehbar zu „Eigene Ansicht“.
- Der Spaltenwähler zeigt verständliche deutsche Bezeichnungen statt interner IDs; zusammengesetzter Spielername und einzelne Namensspalte sind eindeutig voneinander unterschieden.
- Mit 27 eingeblendeten Spalten wurde eine Überbreite von 672 Pixeln erzeugt. Die synchronisierte obere Scrollleiste erscheint automatisch, entspricht mit 1741 Pixeln exakt der Tabellenbreite und lässt Name sowie Aktionen sticky erreichbar.
- Bei einer einzelnen Zusatzspalte bleibt die Tabelle ohne Überbreite; die obere Scrollleiste wird dann automatisch ausgeblendet.
- Produktions-Build und Browser-Laufzeittest erfolgreich.

## Seeder-VIP-Belohnung — Option 3

- Referenz: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-5a0cb3d4-fbdb-4e4a-88ae-ad6f8caa41a1.png`
- Implementierung: `/settings/others/seed-vip` im lokalen Demo-Modus
- Vergleichszustand: Deutsch, Formularmodus, Aktiv, Abschnitt „Voraussetzungen“, gespeicherte Ausgangswerte
- Gemeinsamer Vergleich: `C:\Users\chris\AppData\Local\Temp\seed-vip-option3-comparison-final.png`
- Vergleichsgröße: Referenz und Umsetzung jeweils 1487 × 1058 Pixel

### Sichtbarer Vergleich

- Die ausgewählte Option 3 wurde in die bestehende Frontline-Arbeitsfläche übertragen, ohne Navigation, Typografie, Farbwelt oder eckige Komponenten neu zu erfinden.
- Ziel, Qualifikation und Belohnung bilden oberhalb des Formulars eine kompakte, sofort verständliche Wirkungskette.
- Das Ergebnis-Briefing löst die aktuelle Konfiguration in einen verständlichen Satz und vier operative Schritte auf.
- Team-Zielwerte, Mindestspielzeit, Anwesenheitsbedingung und Fortschrittsmeldungen sind als vier flache Entscheidungszeilen aufgebaut.
- Wirksame Werte stehen im Hauptfluss. Legacy-Minimalwerte, Rückfallpuffer und Darstellungsoptionen befinden sich in klar bezeichneten erweiterten Bereichen.
- Die Speicherleiste bleibt bei der Referenzgröße vollständig sichtbar; die zuvor doppelte Abschnittsüberschrift und die redundante Gültigkeitsmeldung wurden entfernt.

### Fachliche und funktionale Prüfung

- Die Zusammenfassung verwendet die tatsächlich wirksamen Felder `max_allies` und `max_axis`; die gespeicherten, aber aktuell nicht ausgewerteten `min_*`-Felder werden nicht als wirksame Zielspanne dargestellt.
- Gekoppelte Teamwerte geprüft: eine Änderung bei den Alliierten aktualisiert bei aktiver Kopplung beide Seiten und die Wirkungsvorschau sofort.
- Qualifikations-Presets und Anwesenheitsmodus aktualisieren Formular, Zusammenfassung und Dirty-State korrekt.
- Belohnungsdauer und kumulative beziehungsweise neu berechnete VIP-Laufzeit werden mit einer Ergebnisvorschau erklärt.
- Spielertexte bleiben einzeln aufklappbar; vorhandene Platzhalter sind direkt einsetzbar.
- Webhook-Liste wird editierbar dargestellt; leere und vorhandene Zustände sind abgedeckt.
- JSON-Modus bleibt als vollständiger technischer Fallback erhalten. Das nicht wirksame Kompatibilitätsfeld `forward` wird im vereinfachten Hauptfluss nicht als funktionierende Steuerung ausgegeben.

### Responsive und technische Prüfung

- 1487 × 1058: vollständige Entscheidungsoberfläche und Speicherleiste ohne Überdeckung geprüft.
- 390 × 844: kein horizontaler Seitenüberlauf (`scrollWidth = innerWidth = 390`); Navigation und Zusammenfassung brechen kontrolliert um.
- Produktionsnaher Vite-Build im Fake-Modus: bestanden.
- Browserkonsole: keine neuen Fehler; ausschließlich die bestehende React-Router-v7-Future-Flag-Warnung.
- Keine offenen P0-, P1- oder P2-Designabweichungen im neuen Seeder-VIP-Formular.

final result: passed

# Design-QA: Seeder-VIP Option 3 — Feinschliff

## Vergleichsgrundlage

- Zielbild: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-5a0cb3d4-fbdb-4e4a-88ae-ad6f8caa41a1.png`
- Browser-gerenderte Umsetzung: `C:\Users\chris\AppData\Local\Temp\seed-vip-polish-final-desktop.png`
- Gemeinsamer Vergleich: `C:\Users\chris\AppData\Local\Temp\seed-vip-polish-final-compare.png`
- Lokale Route: `http://127.0.0.1:3001/settings/others/seed-vip`

## Feinschliff

- Alle fünf Bereichsreiter besitzen nun kurze, vollständig lesbare Untertitel; die Desktop-Navigation zeigt keine abgeschnittenen Satzfragmente mehr.
- Gleiche Teamziele werden als „25 je Team“ zusammengefasst. Bei abweichenden Zielen nennt die Oberfläche beide Seiten eindeutig.
- Der Ablauftext verwendet natürliche deutsche und englische Formulierungen statt „25 bzw. 25“.
- VIP-Dauer, Ablauftext und Ergebnisvorschau verwenden korrekte Einzahl und Mehrzahl für einen bzw. mehrere Tage.
- Die Zusammenfassung beschreibt die Verlängerungslogik konkret als „verlängert Laufzeit“ bzw. „beginnt ab Abschluss“.
- Die bestehende eckige Frontline-Designlinie, Seitenstruktur und Feldlogik blieben unverändert.

## Interaktionen und technische Prüfung

- Gekoppelte und getrennte Teamziele, Zusammenfassung und Ablauftext: bestanden.
- Belohnung auf einen Tag ändern, Einzahl prüfen und auf sieben Tage zurücksetzen: bestanden.
- Nach dem Rücksetzen entspricht der Formularzustand wieder vollständig den gespeicherten Werten.
- Desktop bei 1487 × 1058: kein horizontaler Überlauf; `mainScrollWidth` entspricht `mainClientWidth`.
- Mobil bei 390 × 844: Dokument- und Body-Breite bleiben 390 Pixel; alle Formularbereiche und Bedienelemente sind im DOM erreichbar.
- Produktionsbuild mit Vite (`--mode fake`): bestanden.
- Direkter Side-by-Side-Vergleich zeigt keine offenen P0-, P1- oder P2-Abweichungen im bearbeiteten Feinschliff.

final result: passed

# Live-Ansicht: natürliche Spielerliste und festes Live-Protokoll

## Vergleichsgrundlage

- Ausgangszustand: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-scroll-behavior-before.png`
- Seitenscroll-Test: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-scroll-behavior-after-page.png`
- Protokollscroll-Test: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-scroll-behavior-after-feed.png`
- Lokale Route: `http://127.0.0.1:3001/views/live`
- Testzustand: geteilte Desktopansicht mit 98 simulierten Spielern, davon 49 Alliierte und 49 Achsenmächte.

## Korrigiertes Höhen- und Scrollmodell

- Die Spielerliste besitzt keine feste oder an das Protokoll gekoppelte Höhe. Ihre Länge ergibt sich ausschließlich aus Suchergebnis, Filtern und Spielerzeilen.
- Das Live-Protokoll besitzt in der geteilten Desktopansicht eine feste, viewportbezogene Höhe und bleibt als vollständige Card am rechten Rand klebend erreichbar.
- Nur der Ereignisbereich des Live-Protokolls scrollt intern. Kopf, Filter und Seitennavigation bleiben innerhalb der festen Card sichtbar.
- Ein Mausradereignis außerhalb des Protokoll-Feeds bewegt die Seite und damit die natürliche Spielerliste; das klebende Protokoll bleibt erreichbar.
- Ein Mausradereignis über dem Feed bewegt ausschließlich dessen Ereignisse. `overscroll-behavior: contain` verhindert ungewolltes Weiterreichen an die Seite.
- Auf schmalen beziehungsweise nicht geteilten Ansichten fällt die Card wieder in den normalen Seitenfluss zurück.
- Diese Festlegung ersetzt die frühere QA-Annahme, beide Panels müssten dieselbe Höhe besitzen und gemeinsam über den Hauptbereich scrollen.

## Testdaten und Prüfung

- 92 zusätzliche lokale Demo-Spieler ergänzt; zusammen mit den sechs vorhandenen Spielern werden 98 von 100 Plätzen dargestellt.
- Spieler-IDs, Level, Spielzeiten und Leistungswerte bleiben realistisch, positiv und reproduzierbar.
- Browserprüfung Seitenscroll: bestanden; Spielerzeilen bewegen sich, die Protokoll-Card bleibt vollständig sichtbar.
- Browserprüfung Feedscroll: bestanden; Spielerposition und Seitenstand bleiben unverändert, nur Protokollereignisse wechseln.
- Produktionsbuild: bestanden.
- Keine P0-, P1- oder P2-Abweichung im bearbeiteten Höhen- und Scrollverhalten.

final result: passed

## Live-Spielerdetails — einzeilige Tabelle mit Aufklappbereich

- Referenz: `C:\Users\chris\AppData\Local\Temp\codex-clipboard-293adc55-14e9-4b10-887e-206a35b38935.png`.
- Implementierung: `/views/live` im lokalen Demo-Modus mit genau einer kompakten Tabellenzeile pro Spieler und höchstens einem geöffneten Detailbereich.
- Finalaufnahme: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-player-list-implementation\04-expanded-anthracite.png`.
- Gemeinsamer Vergleich: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-player-list-implementation\reference-vs-anthracite.png`.
- Geschlossene Spielerzeilen sind am Desktop 38 Pixel hoch; Identität, Truppzuordnung, Kampf/Risiko, Status, Aktionen und Zeit bleiben in einer Zeile.
- Der geöffnete Bereich zeigt Identität, Werte, Status und die kompakten Aktionen Nachricht, Bestrafen, Kicken, Bannen und Profil. Die getrennten Temp-/Permabann-Aktionen und das redundante Drei-Punkte-Menü wurden entfernt.
- Der Detailbereich verwendet dieselbe neutrale Anthrazitfläche wie die Trupp- und Spielerzeilen (`rgb(10, 13, 10)`); die goldene linke Kante kennzeichnet weiterhin den aktiven Datensatz.
- Öffnen eines zweiten Spielers schließt den vorherigen Detailbereich; Escape schließt den Bereich und gibt den Fokus an den Auslöser zurück.
- Produktions-Build sowie der HLL-/HLL-Vietnam-Teamkill-Vertragstest sind erfolgreich.
- Der visuelle Side-by-Side-Vergleich zeigt keine offenen P0-, P1- oder P2-Abweichungen für die umgesetzte Spielerliste.

final result: passed

## Teamübersicht — Option 1

- Zielbild: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-8f0fad35-c9c7-4410-8440-541bfec882af.png`
- Implementierung: `/views/team` im lokalen Demo-Modus.
- Implementierungsaufnahme: `team-implementation-final.png`
- Gemeinsamer Vergleich: `team-design-comparison-final.png`
- Visuelle Hierarchie entspricht Lösung 1: Gefechtslage, Problemlage, kompakter Autobalancer, Filterleiste und zweispaltige Teamkarten.
- Trupps sind standardmäßig kompakt und lassen sich gezielt öffnen; Spielerwerte erscheinen erst in der Detailstufe.
- Suche, Rollenfilter, Truppfilter und Statusfilter sind beschriftet und in der zentralen Arbeitsleiste gebündelt.
- Truppauswahl, Mehrfachauswahl, feste Aktionsleiste und Zurücksetzen der Auswahl wurden im Browser ausgeführt.
- HLL und HLL: Vietnam rendern ohne rohe Rollen- oder Trupptypen und ohne Browserfehler.
- Desktop, Tablet und Mobilzustände wurden ohne horizontalen Seitenüberlauf geprüft; unterhalb des Desktop-Breakpoints wird auf ein Team mit Team-Tabs umgestellt.
- Keine doppelten DOM-IDs und keine unbeschrifteten sichtbaren Buttons in der Teamansicht.
- Deutsch und Englisch sind für alle neuen statischen Texte vorhanden.
- Produktionsbuild mit Vite (`--mode fake`) und `git diff --check` erfolgreich.
- Die lokale Fake-Datenquelle enthält nur einen Beispieltrupp pro Team; Raster, Gruppierung, Scrollverhalten und Aufklappmechanik sind für vollständige Serverbesetzungen ausgelegt.
- Auswahlzustand erneut gegen das Zielbild geprüft: Die Aktionsleiste ist nun viewport-fest und erscheint unmittelbar nach der Auswahl eines Trupps, unabhängig von der Scrollposition.
- Direkte Mehrfachaktionen sind ohne verborgenes Drei-Punkte-Menü erreichbar: Nachricht, Kick, Temp/Perma-Bann über die Sperrliste, Teamwechsel und Trupp-Kick; weitere berechtigte Aktionen bleiben unter „Weitere“ verfügbar. Die veralteten separaten Tempban- und Permaban-Einträge wurden dort entfernt.
- Vergleichsaufnahme: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\product-design-references\team-view\team-selection-actions-comparison.png`.
- Bei 1280 × 900 liegen alle sieben sichtbaren Aktionsbuttons vollständig innerhalb der Leiste; es gibt keinen internen Überlauf. Bei 760 × 850 und 390 × 844 bleibt die Leiste vollständig im Viewport, die Aktionen sind horizontal erreichbar und die Seite erzeugt keinen horizontalen Überlauf.
- Dieselbe Truppauswahl und Aktionsleiste wurde für HLL und HLL: Vietnam ohne Browserfehler geprüft.

final result: passed

# Design-QA: Live-Spielertabelle

## Vergleichsgrundlage

- Source Visual Truth (Detail-Mockup): `C:\Users\chris\AppData\Local\Temp\codex-clipboard-293adc55-14e9-4b10-887e-206a35b38935.png`
- Source Visual Truth (produktiver Ausgangszustand): `C:\Users\chris\AppData\Local\Temp\codex-clipboard-d6f03925-9527-48ab-8ff9-03ca04147fc2.png`
- Browser-gerenderte Umsetzung: `C:\Users\chris\.codex\visualizations\2026\08\15\01a0052a-7e8d-7411-8b78-1a415453783b\live-player-card-professional-final.png`
- Lokale Route: `http://127.0.0.1:3001/views/live`
- Zustand: Dark Theme, geteilte Ansicht, Operationsspalten, erster Spieler ausgeklappt, Fake-Daten.

## Maße und Normalisierung

- Detail-Mockup: 1487 × 1058 Pixel.
- Produktiver Ausgangszustand: 3440 × 1440 Pixel.
- Implementierung und finale Browseraufnahme: CSS-Viewport 1600 × 1000 Pixel.
- Zusätzlich geprüft: 1024 × 900, 768 × 900 und 390 × 844 CSS-Pixel.
- Weil Ausgangsbilder und Browseraufnahme unterschiedliche Datensätze, Dichten und Browserrahmen besitzen, erfolgte der Vergleich über dieselben sichtbaren Produktregionen: Split-Verhältnis, geschlossene Einzeiler, ausgeklapptes Detailband, Aktionsleiste, Panelunterkanten und Scrollverhalten.

## Full-View-Vergleich

- Die Spieler- und Protokollspalte behalten die gewünschte 72/28-Gewichtung.
- Beide Panels reichen bis zu derselben Unterkante und bewegen sich über den zentralen Seiten-Scroller gemeinsam.
- Weder Spielertabelle noch Live-Protokoll besitzen eine eigene vertikale Scrollfläche.
- Die Spielerzeilen bleiben geschlossen einzeilig und entsprechen der Dichte des Mockups.
- Horizontales Scrollen bleibt ausschließlich für tatsächlich zusätzliche Spalten erhalten.

## Fokusvergleich: ausgeklappter Spieler

- Das Detailband ist bündig mit der sichtbaren Tabellenfläche und überschreitet sie auch bei horizontal konfigurierten Zusatzspalten nicht.
- Die aktive Tabellenzeile, der warme Chevron-Hintergrund und die goldene linke Detailkante bilden eine zusammenhängende Auswahlfläche.
- Identität, Clan und Truppkontext bilden eine flache, klar getrennte Kopfzeile ohne unnötige Label-Leerflächen.
- Leistungswerte stehen auf Desktop in einer einzigen ruhigen Zeile mit tabellarischen Zahlen; auf schmalen Ansichten brechen sie kontrolliert in gleichmäßige Raster um.
- VIP-, Beobachtungs- und Warnstatus sind als kompakte Status-Chips von den Aktionen getrennt.
- Nachricht, Bestrafen, Kicken, Bannen und Profil bleiben kompakt; die Bannaktion besitzt den vereinbarten Hammer und eine zurückhaltende Warnfarbe.
- Bei 1024, 768 und 390 Pixeln gruppieren sich Identität, Kontext, Statistiken und Aktionen ohne abgeschnittene Inhalte und ohne horizontalen Überlauf neu.

## Pflichtflächen

- Typografie: bestehende Frontline-Familien, Gewichte und Großschreibung beibehalten; Zahlen mit tabellarischen Ziffern und lokalisierter Dezimaldarstellung.
- Spacing/Layout: gleichmäßige 1-Pixel-Trenner, kompakte 30-Pixel-Aktionen auf Desktop, 44-Pixel-Ziele auf schmalen Ansichten; keine unnötige braune Detailfläche.
- Farben/Tokens: ausschließlich bestehende MUI-/Frontline-Tokens; Gold als Auswahlkante, semantische Warn- und Fehlerfarben nur für Status und Bannaktion.
- Assets/Icons: vorhandene MUI- und Font-Awesome-Icons weiterverwendet; keine Ersatzzeichnungen oder Platzhalter.
- Copy/Inhalt: Fraktion statt generischem Team im Detailkopf; bestehende deutsche Kurzlabels (TKs, Kampf, Offensive, Defensive, Support, Zeit) beibehalten.

## Vergleichshistorie

1. P1 – Spieler- und Protokollbereich hatten voneinander unabhängige, höhenbegrenzte Scrollflächen.
   - Fix: Maximalhöhen und internes vertikales Overflow entfernt; beide Panels an den zentralen Seiten-Scroller gebunden und im Grid auf gleiche Höhe gestreckt.
   - Post-Fix-Evidenz: Browsermessung zeigt identische Panelunterkanten; Tabellenviewport und Eventstream haben jeweils `scrollHeight <= clientHeight`; der App-Hauptbereich besitzt den einzigen vertikalen Overflow.
2. P2 – Das Spieler-Detail wirkte als lose Folge von Informationen und Aktionen.
   - Fix: responsive Drei-Band-Struktur für Identität, Werte sowie Status/Aktionen; neutrale anthrazitfarbene Fläche und Goldkante für die Auswahl.
   - Post-Fix-Evidenz: Desktop-, 1024- und 768-Pixel-Aufnahmen zeigen klare Gruppierung ohne Überdeckung oder abgeschnittene Aktionen.
3. P2 – Die Tabelle erzeugte im Operationsmodus eine horizontale Zwei-Pixel-Scheinüberbreite.
   - Fix: redundante linke/rechte Tabellenränder innerhalb des bereits umrandeten Spielerpanels entfernt und Box-Sizing stabilisiert.
   - Post-Fix-Evidenz: Tabellenviewport `clientWidth = scrollWidth`; die obere horizontale Leiste ist im Standardmodus ausgeblendet.
4. P2 – Das ausgeklappte Detailband wirkte im Vergleich zum Mockup noch technisch und visuell von seiner Tabellenzeile getrennt.
   - Fix: aktive Tabellenzeile hervorgehoben, Chevron als Auswahlindikator gestaltet, neutrale Flächenhierarchie eingeführt, Status-Chips mit semantischen Icons ergänzt und Desktop-Statistiken auf eine Zeile verdichtet.
   - Post-Fix-Evidenz: direkter Bildvergleich zwischen Referenz-Mockup und finaler Browseraufnahme zeigt dieselbe Informationshierarchie; die Umsetzung bleibt kompakter und respektiert die bereits vereinbarte gemeinsame Bannaktion.

## Interaktionen und technische Prüfung

- Spielerdetail öffnen, nächsten Spieler öffnen und wieder schließen: bestanden.
- Spieler-ID kopieren sowie alle sechs Card-Buttons auf Fokus- und Zielgröße prüfen: bestanden.
- Commander-/Statusfilter aktivieren und zurücksetzen: bestanden.
- Gemeinsames Scrollen von Spieler- und Protokollpanel: bestanden.
- Responsive Card-QA: kein horizontaler Überlauf bei 1024, 768 oder 390 Pixeln; alle interaktiven Ziele dort mindestens 44 Pixel hoch.
- Browserkonsole: keine Fehler; nur bestehender React-Router-v7-Future-Flag-Hinweis.
- Produktionsbuild: bestanden.
- Admin-Aktionsvertrag: 20 Definitionen / 18 Commands bestanden.
- Teamkill-Risikovertrag für HLL und HLL Vietnam: bestanden.
- Touch-Target-Suite: 5 von 6 relevanten Prüfungen bestanden; eine bestehende Gleitkomma-Abweichung am globalen Sprachbutton (`43.999999 px`) liegt außerhalb dieser Änderung.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen in der bearbeiteten Live-Spielertabelle.

## Follow-up Polish

- P3: Der globale Sprachbutton kann separat auf eine explizite Mindestbreite von 44 Pixeln gehärtet werden; dies gehört nicht zur Live-Spielertabelle.

final result: passed
