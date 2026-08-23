# Design QA — Konfigurationsformulare

## Vergleichsbasis

- Referenz: gewählte Variante 2 (`exec-3b5661b8-d5d3-446f-96a4-470936ff7afa.png`)
- Referenzgröße: 1683 × 935 Pixel
- Implementierung: `/settings/automods/no-leader` im lokalen Demo-Modus
- Prüfzustand: Deutsch, Formularmodus, Abschnitt „Warnen“, Testbetrieb, ungespeicherte Änderung

## Visueller Vergleich

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

## Responsive und funktionale Prüfung

- 1683 × 935: Drei-Spalten-Layout und sticky Aktionsleiste geprüft.
- 768 × 900: Formular und Zusammenfassung umbrechen ohne abgeschnittene Inhalte.
- 390 × 844: mobile Abschnittsnavigation, Formularelemente und Aktionsbereich geprüft.
- Formular → JSON → Formular: Entwurf bleibt erhalten.
- Änderung → Zurücksetzen: Dirty-State wird gesetzt und anschließend korrekt entfernt.
- Produktions-Build: erfolgreich.
- `git diff --check`: erfolgreich.

## Ergebnis

Keine offenen P0-, P1- oder P2-Designabweichungen im umgesetzten Formularfluss.

final result: passed
