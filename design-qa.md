# Design QA — Konfigurationsformulare und Live-Einsatz

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
