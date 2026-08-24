# Design QA — Konfigurationsformulare

## Vergleichsbasis

- Referenz: finale Nutzervorlage (`codex-clipboard-79491ed8-28e5-4c2b-b580-7dfa4d38f2fb.png`)
- Referenzgröße: 1683 × 935 Pixel
- Implementierung: `/settings/automods/no-leader` im lokalen Demo-Modus
- Prüfzustand: Deutsch, Formularmodus, Abschnitt „Warnen“, Testbetrieb, ungespeicherte Änderung
- Implementierungsaufnahme: `no-leader-warning-final-qa-v3.png`
- Gemeinsamer Vergleich: `no-leader-reference-vs-implementation-final-v2.png`

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

Die Vorlage zeigt im rechten Bereich exemplarisch „Kick kann nicht erreicht werden“. Die Implementierung berechnet diesen Status dagegen aus den tatsächlich gewählten Warn-, Bestrafungs- und Kick-Zeiten. Im geprüften Zustand ist „Kick ist erreichbar“ daher die fachlich korrekte, bewusst beibehaltene Ausgabe.

## Responsive und funktionale Prüfung

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

## Ergebnis

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

final result: passed
