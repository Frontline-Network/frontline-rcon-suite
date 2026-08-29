# Design QA — Live-Spiel / Option 2

## Evidence

- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-1da4afa6-0f8a-48d1-a98d-1440a8f4302d.png`
- Browser-rendered implementation: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-qa.png`
- Normalized implementation: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-qa-normalized.png`
- Same-input comparison: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\product-design\live-game-option2-comparison.png`
- Source pixels: 1487 × 1058 at 1×.
- Implementation pixels: 2353 × 1272 at 1×; CSS browser viewport 2353 × 1272.
- Normalization: the implementation was downsampled proportionally to 1487 × 804 and placed on the same 1487 × 1058 dark canvas as the source. No crop or aspect distortion was applied.
- State: German dark Frontline theme, 36 simulated players, K/D descending, one selected player, player inspector visible, 17 rows per team.

## Full-view comparison

The normalized same-input comparison was reviewed for composition, hierarchy and density. The implementation preserves the selected option's command-board structure: flat match strip, shared command toolbar, mirrored allied/axis tables, central comparison rail and right-side player inspector. Main edges align, both team surfaces are symmetrical, selection is gold, faction meaning uses icon plus label, and the page avoids rounded nested cards.

The source is a 1487 px concept while the available in-app browser viewport is materially wider. The implementation intentionally uses the additional width instead of stretching type or rows; after proportional normalization, the major-region proportions and visual hierarchy remain equivalent. Responsive behavior is defined at 1440, 900 and mobile breakpoints; the current in-app browser did not expose a viewport override for a second pixel capture.

Focused region comparison was not necessary because the original-resolution implementation capture keeps the table headers, dense rows, center metrics and inspector typography legible. Those four regions were still reviewed separately at original resolution.

## Required fidelity surfaces

- Fonts and typography: passed. Existing Frontline display/body type is preserved; labels are uppercase with restrained tracking; player names remain lighter than headers; all metrics use tabular numerals.
- Spacing and layout rhythm: passed. Flat 1 px surfaces, 8–10 px major gaps, dense 34 px desktop rows, matched team widths, and an inspector aligned to the table block.
- Colors and tokens: passed. Existing theme tokens drive background, dividers and text; cyan/allied, muted red/axis, gold/selection and semantic warning/success tones match the reference intent.
- Image and icon fidelity: passed. Existing faction image assets and MUI icons are used. No custom SVG, CSS drawing, placeholder image or emoji was introduced in the redesigned page.
- Copy and content: passed with intentional product constraints. Squad and role are not shown because the live-game endpoint does not provide reliable values. Profile-safe actions are retained for disconnected historical match participants.

## Interaction verification

- Search filters both teams together and preserves symmetric sorting.
- All / active / flagged filters work.
- Row selection updates the player inspector.
- Checkbox selection enables the shared selection action.
- Both team pagers work independently; page-size selection is available.
- Sort field and direction are interactive.
- CSV export remains connected to the full filtered live-game dataset.
- Query refresh retains the 36-player demo dataset and next-map data.
- Page reload and 15-second refetch were tested without row-count collapse.
- Production build completed successfully.

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

### Iteration 1 — blocked

- P2: the first build displayed all team rows and therefore lacked the mockup's compact footer/pagination rhythm.
- P2: the demo refresh replaced the dense 36-player initial state with six players and removed the next map.
- P2: sort direction and country used text/emoji-like glyph presentation instead of the selected icon language.

Fixes: independent team pagination, 17-row default page size, durable live-game Mirage data, stable next-map payload, MUI direction/public icons, uppercase mode label, and explicit unknown/offline status handling.

### Iteration 2 — passed

Post-fix evidence: `live-game-option2-qa.png` and `live-game-option2-comparison.png`. The mirrored table density, footer rhythm, persistent demo state, selection/inspector linkage and icon language now match the target without actionable P0/P1/P2 differences.

## Follow-up polish

- P3: capture dedicated 1000 px and 390 px screenshots when the in-app browser exposes viewport emulation; the implemented breakpoints already switch the inspector to a drawer and the teams to tabs.
- P3: a later backend enhancement could add reliable current squad/role data, but those values should not be inferred in this UI.

final result: passed
