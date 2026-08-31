# Design QA · Phase 4.3 – Kommunikation und Integrationen

## Prüfgrundlage

- Source Visual Truth: `.codex/audits/full-rcon-concept/screenshots/desktop/welcome-message.png`, `.codex/audits/full-rcon-concept/screenshots/mobile/welcome-message.png`, `.codex/audits/full-rcon-concept/screenshots/desktop/integrations.png`, `.codex/audits/full-rcon-concept/screenshots/mobile-390/integrations.png`, `.codex/audits/full-rcon-concept/screenshots/desktop/integration-audit.png` sowie die freigegebenen Seitenziele 37–39 und 54–65 in `docs/product-design/rcon-product-concept.md`.
- Bereits vorhandene Zielstruktur: Willkommensnachricht mit Editor, Vorlagen und Ingame-Vorschau; Kampagnen mit Inhalt, Zielgruppe, Ausspielung, Test und Zustellaktivität; Integrationshub mit elf kompatiblen Modulen und gemeinsamem Connector-Editor.
- Aktuelle Teiländerung: mobile Integrationsfilter als vollständig sichtbares 2×2-Raster sowie geführte, rekursive Schlüssel-/Wert-Felder anstelle eines JSON-Texteditors für dynamische Konfigurationsobjekte. Schema-definierte Felder bleiben als beschriftete, validierte Controls erhalten und können nicht versehentlich als dynamischer Eintrag gelöscht werden; nur unbekannte Bestandsfelder erscheinen getrennt als „Weitere Einträge (Kompatibilität)“.

## Prüfzustand und Vergleichseingänge

- Implementierung: `.codex/phase43-after/desktop-integrations-1280x720.png`, `.codex/phase43-after/desktop-integration-audit-1280x720.png`, `.codex/phase43-after/mobile-integrations-390x844.png`, `.codex/phase43-after/mobile-integration-audit-390x844.png` und `.codex/phase43-after/mobile-rcon-chat-commands-form-390x844.png`.
- Gemeinsame Same-State-Vergleiche: `.codex/phase43-after/compare-desktop-audit.png` und `.codex/phase43-after/compare-mobile-integrations.png`. Source und Implementierung liegen dort ohne Skalierung nebeneinander.
- Theme- und Farbseh-Evidenz: `.codex/phase43-after/desktop-appearance-light-deuteranopia-dialog-1280x720.png` und `.codex/phase43-after/desktop-integration-audit-light-deuteranopia-1280x720.png`.
- Viewports: Desktop 1280 × 720 CSS- und Bildpixel, Mobile 390 × 844 CSS- und Bildpixel, jeweils Browser-Dichte 1. Der primäre Zustand verwendet Frontline Gold, dunkles Theme, Standard-Farbsehen, deutsche Sprache, Demo-Server 2 und HLL mit 98/100 Spielern.

## Full-View- und Fokusvergleich

Desktop behält die freigegebene tabellarische Integrationsübersicht mit kompaktem Konfigurationsbereich bei. Der Same-State-Vergleich zeigt keine unbeabsichtigte Verschiebung von Header, Spalten, Modulzeile oder Ziel-Editor. Mobile ersetzt dagegen gezielt die zuvor abgeschnittene horizontale Filterleiste durch ein vollständig sichtbares 2×2-Raster. Dadurch sind alle vier Kategorien ohne seitliches Scrollen erreichbar, während die Modulliste und die feste Bottom-Navigation ihren Rhythmus behalten.

Im Fokusvergleich wurden der sensible Audit-Webhook und die tief verschachtelte RCON-Chatbefehls-Konfiguration geprüft. Der Webhook bleibt maskiert und besitzt eine beschriftete Einblenden-Aktion. RCON-Befehle, Bedingungen, Zahlenbereiche, boolesche Zustände, Listen und verschachtelte Objekte erscheinen als geführte Eingaben; Endanwender sehen keinen JSON-Editor und müssen keine JSON-Syntax beherrschen.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [behoben] [P1] Die vier mobilen Integrationsfilter lagen in einer horizontal scrollenden Zeile und konnten abgeschnitten erscheinen. Sie verwenden jetzt zwei vollständig sichtbare Spalten auf 390 Pixeln und vier Spalten ab dem nächsten Breakpoint.
- [behoben] [P1] Dynamische Objekte fielen auf einen JSON-Texteditor zurück. Sie werden jetzt als benannte Einstellungen, primitive Werte, Listen und rekursive Untereinstellungen bearbeitet.
- [behoben] [P1] Schema-definierte Felder und zusätzliche Bestandsfelder wurden bei Objekten mit `additionalProperties` gemeinsam als löschbare Schlüssel-/Wert-Zeilen behandelt. Feste Schemafelder bleiben nun in ihren geführten Controls; nur unbekannte Zusatzfelder erscheinen getrennt unter „Weitere Einträge (Kompatibilität)“.
- [P3] Die lokale Entwicklungsumgebung protokolliert ausschließlich die bereits bekannte React-Router-v7-Future-Flag-Warnung. Es traten keine Console-Errors und kein sichtbares Runtime-Fehleroverlay auf.

## Pflichtflächen und Accessibility

- Typografie, eckige Formensprache, Abstände, Rahmen, Primärfarbe und Statusfarben verwenden unverändert das Frontline-Designsystem. Hell plus Deuteranopie wurde live geprüft und anschließend wieder auf Dunkel plus Standard zurückgestellt.
- Mobile Hub, Audit-Detail und RCON-Konfiguration bleiben innerhalb von 390 Pixeln ohne horizontalen Dokumentüberlauf. Desktop bleibt bei 1280 Pixeln ebenfalls überlauffrei und besitzt genau eine `h1`.
- Alle elf Module sind native Buttons mit `aria-expanded`; Suche und Filter besitzen zugängliche Namen und Gruppensemantik. Entfernen-, Einblenden-, Hinzufügen-, Zurücksetzen- und Speichern-Aktionen sind beschriftet. Die sichtbaren Formularfelder werden über native MUI-Labels oder Gruppennamen zugeordnet; das zusätzliche MUI-Mess-Textarea ist korrekt `aria-hidden` und nicht fokussierbar.
- Status wird nicht ausschließlich über Farbe vermittelt. Text, Icons, Rahmen und `aria-pressed` ergänzen Aktiv-, Konfiguriert-, Auswahl- und Warnzustände.

## Fachliche und funktionale Prüfung

- Filter „Befehle“ und Suche nach „RCON“ reduzieren die Modulliste korrekt; Zurücksetzen stellt alle Module wieder her.
- Audit öffnet ohne Laufzeitfehler, zeigt das vorhandene Ziel maskiert und enthält keinen erweiterten JSON-Schalter oder JSON-Textarea.
- RCON-Chatbefehle rendern bestehende Listen, verschachtelte Bedingungen, Zahlen und boolesche Werte rekursiv. Neue dynamische Schlüssel lassen sich nur mit eindeutigem Namen ergänzen; doppelte oder leere Schlüssel werden verhindert.
- Unbekannte Bestandsfelder bleiben durch `mergeConfigWithSchema` erhalten. Kein API-, RCON-, Discord- oder Gameserververtrag wurde verändert; während der QA wurde keine mutierende Aktion außerhalb des lokalen Fake-Backends ausgelöst.
- Theme und Farbsehmodus wurden über die reale Benutzeroberfläche auf Hell plus Deuteranopie umgestellt, auf der Audit-Konfiguration geprüft und anschließend auf Dunkel plus Standard zurückgesetzt.

## Automatisierte Evidenz

- Produktionsbuild mit `REACT_APP_API_URL=/api/`: bestanden.
- Kommunikations-Workbench, Konfigurationskompatibilität, Designfundament, Seitensemantik, Aktionsfeedback, Operator-Copy, Navigation, Configuration Workbench, Adminaktionen und initiales Bundle-Budget: bestanden.
- Initial Entry: 400,98 kB raw / 121,50 kB gzip; initiales JavaScript: 1.498,11 kB raw / 480,37 kB gzip.
- Browsergerenderte Implementierung, Primärinteraktionen, Semantik, Theme/Farbsehmodus, Konsolenprüfung, Mobile-Overflow und visueller Same-State-Vergleich: bestanden.

final result: passed

---

# Design QA · Phase 4.2 – Sektorsteuerung und Kartenabstimmung

## Prüfgrundlage

- Source Visual Truth: die unveränderten Ausgangszustände unter `.codex/phase42-baseline/` sowie das freigegebene Produktkonzept in `docs/product-design/rcon-product-concept.md` für die Routen `/settings/maps/objectives`, `/settings/maps/votemap`, `/settings/maps/votemap/whitelist` und `/settings/maps/votemap/settings`.
- Implementierung: `.codex/phase42-after/desktop-objectives.png`, `.codex/phase42-after/desktop-votemap-status.png`, `.codex/phase42-after/desktop-votemap-pool.png`, `.codex/phase42-after/desktop-votemap-settings.png`, die vier gleichnamigen Mobile-Aufnahmen sowie `.codex/phase42-after/mobile-objectives-selection.png`.
- Gemeinsame Vergleichseingänge: `.codex/phase42-after/compare-desktop-objectives.png`, `.codex/phase42-after/compare-mobile-objectives.png`, `.codex/phase42-after/compare-mobile-votemap-status.png`, `.codex/phase42-after/compare-mobile-votemap-pool.png` und `.codex/phase42-after/compare-mobile-votemap-settings.png`.
- Theme- und Farbseh-Evidenz: `.codex/phase42-after/desktop-objectives-light-deuteranopia.png`.
- Viewports und Normalisierung: Desktop 1440 × 900 CSS- und Bildpixel, Mobile 390 × 844 CSS- und Bildpixel, Browser-Dichte 1. Die Screenshots enthalten ausschließlich den App-Viewport.
- Zustand: Frontline Gold, dunkles Theme, deutsche Sprache, Demo-Server 2, HLL, 98/100 Spieler. Die Theme-Prüfung verwendete Hell plus Deuteranopie und wurde anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Die Sektorsteuerung ersetzt das defekte, abstrakte Raster durch die echte taktische Karte und eine native 5×5-Zielauswahl. Karte, Reihenfortschritt, Zufallskriterien und die unmittelbare Neustartwirkung bilden nun einen zusammenhängenden Arbeitsablauf. Mobile trennt die Aufgaben bewusst in „Taktische Karte“ und „Sektorfolge“, anstatt beide dichten Bereiche gleichzeitig zu stapeln. Die Kartenabstimmung bleibt fachlich in Live-Betrieb, Kartenpool und Einstellungen gegliedert, zeigt diese drei Aufgaben aber auf 390 Pixeln vollständig, ohne horizontales Dokumentscrollen oder verdeckte Abschlussaktionen.

## Fokusvergleich

- Sektoren: ein gültiges Ziel wurde direkt auf der taktischen Karte gewählt; der Fortschritt wechselte von null auf eine festgelegte Reihe und die mobile Auswahlansicht blieb innerhalb von 390 Pixeln.
- Neustartbestätigung: der Dialog zeigte Zielserver `[GER] Frontline Network | #2`, aktuelle Karte Foy, betroffene 98 Spieler und alle fünf Reihen. Zufällige Reihen werden lokalisiert als „Zufällig“ bezeichnet. Abbrechen schloss den Dialog ohne API- oder Gameserveraktion.
- Kartenpool: Kursk wurde dem lokalen Entwurf hinzugefügt, der Dirty-Zustand und drei Poolkarten wurden sichtbar; anschließend wurde der Entwurf zurückgesetzt, ohne zu speichern.
- Einstellungen: eine Auswahlregel wurde geändert, der Dirty-Zustand erschien und Zurücksetzen stellte den Serverstand wieder her.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Die bestehende In-App-Browser-Bindung verlor nach den vollständigen Desktop-/Mobile- und Theme-Aufnahmen ihre lokale Vorschauverbindung. Daher wurden Browserkonsolen-Ereignisse und die Enter-Aktivierung der nativen Sektorbuttons nach der letzten reinen Copy-Kürzung nicht erneut aufgezeichnet. Die Controls sind echte `button`-Elemente mit zugänglichem Namen, `aria-pressed` und Fokusdarstellung; Produktionsbuild und Semantikvertrag prüfen den finalen Codezustand.

## Pflichtflächen

- Fonts und Typografie: gemeinsamer `PageHeader`, vorhandene Frontline-Schriftfamilie, kondensierte Versalien und klar getrennte Status-, Anweisungs- und Wirkungstexte. Die letzten mobilen Tab- und Erinnerungslabels wurden bewusst auf „Live“ und „Letzte Erinnerung“ verkürzt.
- Spacing und Layout: Desktop als taktische Karte plus Sektorfolge, Mobile als expliziter Aufgabenwechsel. Für alle vier Mobile-Routen gilt in der geprüften Endstruktur `main.scrollWidth === main.clientWidth === 380`; Abschlussleisten verdecken keinen Formularinhalt.
- Farben und Tokens: ausschließlich vorhandene Theme-, Rahmen-, Auswahl-, Warn-, Erfolgs- und Gefahrentokens. Hell plus Deuteranopie wurde live geprüft; Auswahl und Wirkung werden zusätzlich über Text, Icon, Nummer und Rahmen vermittelt.
- Bilder und Assets: die vorhandene echte taktische Karte wird über die Karten-ID beziehungsweise als kompatibler Fallback über den Kartennamen geladen. Etablierte MUI-Icons bleiben erhalten; keine Platzhalter, CSS-Zeichnungen, Emojis oder handgebauten SVGs.
- Copy und Inhalt: aktuelle Karte, Anzahl festgelegter Reihen, Zufallskriterien, Neustartwirkung, Zielserver und betroffene Spieler werden vor der Ausführung erklärt. Die Kartenabstimmung beschreibt Live-Zustand, Poolentwurf und Auswahlregeln getrennt.
- Icons und Zustände: Ziel gewählt, Zufall, Poolentwurf, gespeichert, geändert, zurücksetzen und unmittelbarer Neustart verwenden dieselbe Iconfamilie. Kein Status ist ausschließlich farbcodiert.
- Responsivität und Accessibility: native Buttons je taktischem Ziel, `aria-pressed`, individuelle zugängliche Namen, semantische Tabs, beschriftete Auswahlfelder, sichtbare Fokusdarstellung und mobile Aufgabenflächen ohne horizontalen Überlauf.

## Fachliche und funktionale Prüfung

- Bestehende Verträge bleiben erhalten: `changeObjectives({ objectives, random_constraints })`, Kartenpool- und Kartenabstimmungs-Konfiguration sowie Loader- und Query-Verhalten wurden nicht erweitert oder umbenannt.
- Die Zielauswahl bleibt auf exakt fünf Reihen begrenzt. Nicht gültige Außenfelder bleiben gesperrt; explizite Ziele und zufällige Reihen können weiterhin kombiniert werden.
- Der Bestätigungsdialog fasst den tatsächlich aktuellen Entwurf zusammen und führt erst über die vorhandene Admin-Aktion zum unmittelbaren Kartenneustart. Während der QA wurde keine mutierende API-, RCON- oder Gameserveraktion ausgelöst.
- Der Kartenpool behält verfügbare Karten und gespeicherten Pool als getrennte Entwurfsflächen. Die mobile Abschlussleiste ist statisch und überlagert weder Filter noch Karten.
- Das numerische MUI-Maß `width: 1` im unsichtbaren Live-Bereich wurde zu `1px` korrigiert. Dadurch erzeugt die Statusseite keinen unbeabsichtigten 100-Prozent-Zusatzblock mehr.
- Produktionsbuild sowie Design-, Semantik-, Aktions-, Operator-Copy-, Navigations-, Konfigurations-, Kompatibilitäts- und Admin-Vertragsprüfungen bestanden.
- Bundle-Budget: 400,98 kB Entry-JavaScript bei 121,50 kB gzip und 1.498,11 kB initiales JavaScript bei 480,36 kB gzip; alle Grenzwerte eingehalten. Die neuen Workbench-Texte bleiben im lazy geladenen Kartenpaket.

## Vergleichshistorie

1. Ausgangsvergleich: [P1] Die taktische Karte war im Demo-/Fallbackzustand defekt, weil ausschließlich `map.id` verwendet wurde. Die Bildauflösung nutzt nun kompatibel `map.id ?? map.name`.
2. Erste Mobile-Prüfung: [P1] scrollbare Tabs und Seitenbreiten-Hacks schnitten Aufgaben ab und erzeugten horizontalen Überlauf. Mobile verteilt alle drei Kartenabstimmungsaufgaben gleichmäßig; die Wurzelbreite bleibt 100 Prozent.
3. Statusprüfung: [P1] der visuell versteckte Live-Bereich nutzte bei MUI `width: 1` und wurde dadurch 100 Prozent breit. Explizite `1px` beseitigen den Zusatzüberlauf.
4. Kartenpool-Prüfung: [P1] die klebende mobile Abschlussleiste überdeckte Karten und Filter. Der Pool verwendet nun die statische mobile Abschlussleiste.
5. Finaler Copy- und Dichtevergleich: [P2] lange Live- und Erinnerungslabels waren auf 390 Pixeln zu dominant. Die Labels wurden gekürzt, ohne ihre Bedeutung oder zugänglichen Seitentitel zu verlieren.
6. Finale gemeinsame Vorher-/Nachher-Vergleiche bei identischen Viewports: keine offenen P0-, P1- oder P2-Findings.

## Implementation Checklist

- [x] Alle vier Routen vor und nach der Änderung auf Desktop und 390 × 844 Mobile geprüft.
- [x] Fünf gemeinsame Vorher-/Nachher-Vergleiche bei identischem Zustand visuell beurteilt.
- [x] Taktisches Ziel, mobile Aufgabenansicht, Neustartdialog, Poolentwurf, Einstellungsentwurf und Zurücksetzen geprüft.
- [x] Theme, Deuteranopie, Semantik und Mobile-Overflow geprüft.
- [x] Bestehende API-, Payload-, Persistenz- und Gameserververträge unverändert erhalten.
- [x] Produktionsbuild, Bundle-Budget und neun statische Vertragsprüfungen bestanden.

final result: passed

---

# Design QA · Phase 4.1 – Kartenbetrieb und Rotation

## Prüfgrundlage

- Source Visual Truth: die unveränderten Ausgangszustände unter `.codex/phase41-baseline/` sowie das freigegebene Produktkonzept in `docs/product-design/rcon-product-concept.md` für die Routen `/settings/maps/change`, `/settings/maps/rotation`, `/settings/maps/rotation/sequence` und `/settings/maps/rotation/settings`.
- Implementierung: `.codex/phase41-after/desktop-change.png`, `.codex/phase41-after/desktop-rotation.png`, `.codex/phase41-after/desktop-sequence.png`, `.codex/phase41-after/desktop-settings.png`, `.codex/phase41-after/mobile-change.png`, `.codex/phase41-after/mobile-rotation.png`, `.codex/phase41-after/mobile-rotation-draft.png`, `.codex/phase41-after/mobile-sequence.png` und `.codex/phase41-after/mobile-settings.png`.
- Gemeinsame Vergleichseingänge: `.codex/phase41-after/compare-desktop-change.png`, `.codex/phase41-after/compare-desktop-rotation.png` und `.codex/phase41-after/compare-mobile-rotation.png`.
- Theme- und Farbseh-Evidenz: `.codex/phase41-after/desktop-light-deuteranopia.png`.
- Viewports und Normalisierung: Desktop 1440 × 900 CSS- und Bildpixel, Mobile 390 × 844 CSS- und Bildpixel, Browser-Dichte 1. Die Screenshots enthalten ausschließlich den App-Viewport.
- Zustand: Frontline Gold, dunkles Theme, deutsche Sprache, Demo-Server 2, HLL, 98/100 Spieler, drei veröffentlichte Karten. Theme-Prüfung in Hell plus Deuteranopie und anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Der Kartenwechsel ersetzt den generischen Kartenblock durch eine klar benannte Sofortaktion mit aktuellem und nächstem Kartenstatus, gezieltem Katalog und einer einzigen Bestätigung mit Spielerwirkung, Zielserver und Vorlauf. Der Rotationseditor trennt Katalog und unveröffentlichten Entwurf, macht den Serverstand sichtbar und veröffentlicht Änderungen erst über eine eindeutige Abschlussaktion. Die feste Kartenfolge verwendet dieselbe Arbeitslogik, während die Ausspielungseinstellungen ausschließlich die tatsächlich unterstützte Mischoption zeigen. Alle Flächen bleiben eckig, themenfähig und innerhalb der bestehenden Frontline-Hierarchie.

## Fokusvergleich

- Kartenwechsel: der Bestätigungsdialog wurde mit 98/100 betroffenen Spielern, 60 Sekunden Vorlauf und „Frontline #2“ geprüft; Abbrechen schloss ihn ohne API-Aktion.
- Rotation: eine zweite Carentan-Variante erzeugte den Dirty-Zustand, aktivierte „Rotation veröffentlichen“ und blieb als bewusste Gewichtung sichtbar. Zurücksetzen stellte den gespeicherten Serverstand wieder her.
- Mobile Entwurfsansicht: Wechsel zwischen „Katalog“ und „Entwurf“, sichtbare Pfeilaktionen und vollständige drei Aufgabentabs bei 390 Pixeln geprüft.
- Ausspielung: Vorschau der ersten fünf beziehungsweise vorhandenen drei Karten, Entwurfsumschalter sowie statische mobile Abschlussleiste geprüft.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Lange Kartennamen werden auf 390 Pixeln gezielt gekürzt, damit Verschiebe- und Entfernen-Aktionen als 44-Pixel-Ziele erreichbar bleiben. Vollständige Namen bleiben über den Kartenkontext und zugängliche Aktionsnamen erhalten.

## Pflichtflächen

- Fonts und Typografie: gemeinsamer `PageHeader`, bestehende Frontline-Schriftfamilie, kondensierte Versalien, Gewichte und Laufweiten. Feldlabels, Statuszeile und Entwurfszustand besitzen eine klare Hierarchie ohne problematische Umbrüche.
- Spacing und Layout: Desktop als geteilte Arbeitsfläche, Mobile als bewusster Katalog-/Entwurfwechsel. Nach dem Grid-Fix gilt bei 390 × 844 `main.scrollWidth === main.clientWidth === 380`; die mobile Abschlussleiste verdeckt keinen Inhalt.
- Farben und Tokens: ausschließlich vorhandene Theme-, Rahmen-, Auswahl-, Warn-, Erfolgs- und Gefahrentokens. Hell plus Deuteranopie wurde live geprüft; Zustände bleiben zusätzlich über Text, Icon und Rahmen erkennbar.
- Bilder und Assets: vorhandene echte Kartenbilder und etablierte MUI-Icons werden wiederverwendet; keine Platzhalter, CSS-Zeichnungen, Emojis oder handgebauten SVGs.
- Copy und Inhalt: deutsche und englische Kartenwerkstatt-Texte werden erst beim Betreten des Kartenbereichs als i18n-Ressource geladen. Dadurch bleibt die neue Führung verständlich, ohne das anfängliche JavaScript-Budget zu vergrößern.
- Icons und Zustände: Karte hinzufügen, verschieben, entfernen, kopieren, zurücksetzen und speichern verwenden dieselbe Iconfamilie. Gespeichert, geändert, leer, doppelt und Sofortaktion sind nicht allein farbcodiert.
- Responsivität und Accessibility: sichtbare Feldlabels, semantische Tabs und Buttons, zugängliche Namen je Karte, Tastaturpfeile zusätzlich zu Drag-and-drop, mobile 44-Pixel-Aktionen und kein horizontaler Überlauf.

## Fachliche und funktionale Prüfung

- Bestehende Verträge bleiben erhalten: `SET_MAP({ map_name })`, `SET_MAP_ROTATION({ map_names })`, `SET_MAP_SEQUENCE({ map_names })` und die vorhandene Shuffle-Einstellung. Keine neue API, kein neues Datenfeld und keine automatische Serveraktion.
- Suche berücksichtigt Kartenname und interne Karten-ID; Spielmodus und Umgebung bleiben kombinierbar. Filter zurücksetzen und Ergebniszahl wurden geprüft.
- Drag-and-drop bleibt erhalten; Enter auf einer Verschiebeaktion änderte die Reihenfolge, Zurücksetzen stellte den gespeicherten Zustand wieder her. Doppelte Einträge bleiben bewusst möglich.
- Leere Entwürfe werden deutlich gewarnt, aber nicht fachlich blockiert, weil der bestehende Serververtrag das vollständige Leeren weiterhin zulässt.
- Ein mutierendes `maps.sort(...)` wurde durch `[...maps].sort(...)` ersetzt. Dadurch verändert die Ansicht nicht mehr das geteilte Demo-/Loader-Array und erzeugt keinen falschen Dirty-Zustand.
- Browserkonsole: null Errors. Produktionsbuild und alle Design-, Semantik-, Aktions-, Navigations-, Konfigurations- und Admin-Vertragsprüfungen bestanden.
- Bundle-Budget: 400,91 kB Entry-JavaScript und 1.498,06 kB initiales JavaScript bei 480,35 kB gzip; alle Grenzwerte eingehalten. Die kartenspezifischen Übersetzungen liegen im lazy geladenen Kartenpaket.

## Vergleichshistorie

1. Erster Vergleich: [P2] Der Entwurf war nach dem Laden fälschlich geändert. Ursache war das mutierende Sortieren eines geteilten Arrays; die Sortierung arbeitet nun auf einer Kopie.
2. Erste Mobile-Prüfung: [P2] Das zweispaltige MUI-Grid erzeugte negative Breite und horizontalen Überlauf; die Arbeitsfläche verwendet nun ein begrenztes CSS-Grid und eine statische mobile Abschlussleiste.
3. Zweite Mobile-Prüfung: [P2] Der dritte Aufgabentab war bei 390 Pixeln nicht vollständig erreichbar. Mobile blendet dekorative Tab-Icons aus und verteilt alle drei Aufgaben gleichmäßig.
4. Finale Vergleichseingänge bei identischen Viewports: Kartenwechsel, Rotation und Mobile besitzen keine offenen P0-, P1- oder P2-Findings.

## Implementation Checklist

- [x] Alle vier Routen vor und nach der Änderung auf Desktop und 390 × 844 Mobile geprüft.
- [x] Gemeinsame Vorher-/Nachher-Vergleiche bei identischem Zustand visuell beurteilt.
- [x] Karte auswählen, Bestätigung abbrechen, Filter, Entwurf, Duplikat, Tastaturreihenfolge, Zurücksetzen und Einstellungsentwurf geprüft.
- [x] Theme, Deuteranopie, Semantik, Browserkonsole und Mobile-Overflow geprüft.
- [x] Bestehende API-, Payload-, Persistenz- und Serververträge unverändert erhalten.
- [x] Produktionsbuild, Bundle-Budget und neun statische Vertragsprüfungen bestanden.

final result: passed

---

# Kartenabstimmungs-Einstellungen – Design QA

## Vergleichsgrundlage

- Gewählte visuelle Richtung: Option 2 „Regelwerk-Matrix“.
- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-51d781dc-d5d7-4954-af99-e90d525b712f.png`
- Implementierte Route: `http://127.0.0.1:3005/settings/maps/votemap/settings`
- Desktop-Screenshot: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\votemap-settings-option2-desktop.png`
- Kombinierter Vergleich: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\votemap-settings-option2-comparison.png`
- Mobile Evidenz: `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\votemap-settings-option2-mobile-390.png` und `C:\Users\chris\OneDrive\Dokumente\Autobalancer\hll_rcon_tool-steam-enrichment\.tmp\votemap-settings-option2-mobile-320.png`
- Source und Desktop-Implementierung: jeweils 1487 × 1058 px, Geräteskalierung 1.
- Zustand: dunkles Frontline-Theme, deutsche Sprache, Demo-Server, Einstellungen gespeichert, Detailbereiche geschlossen.

## Visuelles Ergebnis

Keine offenen P0-, P1- oder P2-Abweichungen.

- Informationsarchitektur: Die Effekt-Zusammenfassung, die zweispaltige Matrix aus Modusanzahl und Auswahlregeln sowie die drei nachgelagerten Detailbereiche entsprechen der gewählten Richtung.
- Designlinie: eckige Konturen, dunkle grün-schwarze Flächen, goldene Akzente, kompakte Typografie und bestehende Theme-Tokens bleiben erhalten.
- Datenmodell: Die im Mockup angedeutete Gewichtung je Spielmodus wurde bewusst nicht übernommen, da sie im Servermodell nicht existiert. Vorhandene globale VIP- und Markierungsgewichte bleiben vollständig konfigurierbar.
- Dichte: Zeilen, Schalter und Abstände wurden nach dem ersten Vergleich verdichtet, ohne Touch-Ziele oder Lesbarkeit zu verlieren.
- Mobile: Hauptbereiche stapeln sich, die Effektwerte laufen einspaltig, die Seite erzeugt bei 390 px und 320 px keinen horizontalen Dokument-Overflow. Die Aktionsleiste liegt mobil nicht mehr über dem Formular.

## Vergleichsverlauf

1. Der erste gemeinsame Vergleich zeigte als P2, dass die beiden Hauptbereiche erst bei einer zu großen Viewport-Breite nebeneinander standen. Der Breakpoint wurde von `xl` auf `lg` verschoben.
2. Der zweite Vergleich zeigte als P2 eine zu große vertikale Dichte in den Auswahlregeln. Zeilenhöhen, Innenabstände und Trenner wurden kompakter abgestimmt.
3. Die mobile Prüfung zeigte als P1, dass die klebende Aktionsleiste auf 320 px den Formularinhalt weitgehend überdeckte. `ConfigActionBar` unterstützt nun eine separat abschaltbare mobile Klebeposition; diese Seite verwendet den statischen mobilen Modus.
4. Die mobile Prüfung zeigte außerdem als P1 eine abgeschnittene Effekt-Zusammenfassung. Die Seitenbreite wird am Viewport begrenzt und die vier Kennzahlen wechseln auf kleinen Displays in eine einspaltige Anordnung.
5. Post-Fix-Evidenz: 390 px und 320 px haben jeweils `scrollWidth === clientWidth`; die Desktop-Matrix bleibt zweispaltig.

## Funktions- und Qualitätsprüfung

- Modus-Stepper getestet: Warfare `4 → 5`, Gesamtsumme `7 → 8`, Dirty-Zustand und Save-Aktivierung; Zurücksetzen stellte `7` und den sauberen Zustand wieder her.
- Detailbereich Nachrichten getestet: öffnen, Textentwurf ändern, schließen, erneut öffnen; der Entwurf blieb erhalten.
- Pflichtplatzhalter getestet: Fehlt `{map_selection}`, erscheint die Fehlermeldung und Speichern bleibt gesperrt.
- Zahlenvalidierung, Null-Untergrenze und deaktivierte Minus-Schaltflächen bei `0` sind sichtbar und funktionsfähig.
- Unbekannte künftige Serverfelder werden beim Speichern erhalten; der extern änderbare Runtime-Schalter `enabled` wird weiterhin separat zusammengeführt.
- Browserkonsole: keine Laufzeitfehler; ausschließlich die bereits bestehende React-Router-Future-Flag-Warnung.
- Produktionsbuild: bestanden; nur die bestehende Warnung für große Chunks.
- Vertragsprüfungen: Config-Kompatibilität, Polling-Budget und Admin-Aktionsvertrag bestanden.

## Fokusvergleich

Ein zusätzlicher Ausschnitt war nicht notwendig. Der kombinierte 2990 × 1058-px-Vergleich zeigt Source und Umsetzung vollständig nebeneinander; die relevanten Hauptbereiche, Zusammenfassung, Matrix und Aktionsleiste sind gleichzeitig beurteilbar.

final result: passed

---

# Design QA · Phase 3.3 – Vertrauensabhängige Sperrregeln prüfen

## Prüfgrundlage

- Source Visual Truth: die unveränderten Workbench-Ausgangszustände in `.codex/phase33-baseline/vac-bans-baseline-desktop-1440x900.png`, `.codex/phase33-baseline/vac-bans-baseline-mobile-390x844.png`, `.codex/phase33-baseline/tk-bans-baseline-desktop-1440x900.png` und `.codex/phase33-baseline/tk-bans-baseline-mobile-390x844.png`; fachliche Zielwahrheit zusätzlich aus `rcon/hooks.py`, `rcon/workers.py`, `rcon/automods/tk_autoban.py`, `rcon/user_config/vac_game_bans.py` und `rcon/user_config/ban_tk_on_connect.py`.
- Implementierung: `.codex/phase33-baseline/vac-bans-after-desktop-1440x900.png`, `.codex/phase33-baseline/vac-bans-after-mobile-390x844.png`, `.codex/phase33-baseline/tk-bans-after-desktop-1440x900.png` und `.codex/phase33-baseline/tk-bans-after-mobile-390x844.png`.
- Fokuszustände: `.codex/phase33-baseline/vac-bans-test-desktop-1440x900.png`, `.codex/phase33-baseline/vac-bans-test-mobile-390x844.png`, `.codex/phase33-baseline/tk-bans-test-desktop-1440x900.png` und `.codex/phase33-baseline/tk-bans-test-mobile-390x844.png`.
- Theme-Evidenz: `.codex/phase33-baseline/tk-bans-theme-deuteranopia-1440x900.png`.
- Viewports und Normalisierung: Desktop jeweils 1440 × 900 CSS- und Bildpixel, Mobile jeweils 390 × 844 CSS- und Bildpixel, Browser-Dichte 1. Die Screenshots enthalten ausschließlich den App-Viewport.
- Primärzustand: Frontline Gold, dunkler Modus, Standard-Farbsehen. Theme-Prüfung in Hell plus Deuteranopie und anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Ausgangs- und Nachher-Aufnahmen beider Routen wurden bei identischen Viewports und identischem gespeichertem Regelzustand gemeinsam geöffnet. Informationsarchitektur, eckige Workbench-Flächen, Abschnittsnavigation, Formularfelder, Zusammenfassung und Abschlussleiste bleiben unverändert. Neu ist ausschließlich die klare Aktion „Auswirkung testen“: Desktop neben dem Regelkopf und zusätzlich in der Abschlussleiste, Mobile einmal direkt unter dem Modus beziehungsweise Regelkopf. Der zusätzliche Einstieg verschiebt Mobile Inhalt nach unten, priorisiert aber bewusst die sicherheitskritische Vorschau vor den editierbaren Details und erzeugt keinen horizontalen Überlauf.

## Fokusvergleich

Die VAC- und TK-Drawer-Aufnahmen wurden gemeinsam beurteilt. Beide verwenden dieselbe eckige Testoberfläche, unterscheiden aber ihre Datengüte und Ausnahmen fachgerecht. VAC zeigt gespeicherten Steam-Datenzustand, Sperrhistorie, Hintergrundaktualisierung und Folgeprüfung. TK zeigt Profil-/VIP-Verfügbarkeit, Logfenster, Toleranz, Sperrmaßnahme und nachgelagerten Auditstatus. Nach dem Ausführen springt der lange Drawer automatisch so weit, dass die erwartete Entscheidung und ihre nummerierte Ablaufkette sichtbar sind. Desktop und Mobile bleiben vertikal scrollbar; bei 390 × 844 gilt `scrollWidth === clientWidth`.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Die aktuelle In-App-Browser-Bindung stellt auf diesem Host keine Console- oder CDP-Ereignisfähigkeit bereit. Es erschien kein Fehler-Overlay und alle Browserpfade sowie Vertragsprüfungen bestanden; ein separater Konsolen-Eventnachweis bleibt für einen späteren Lauf mit verfügbarer Capability offen.

## Pflichtflächen

- Fonts und Typografie: bestehende Frontline-Schriftfamilie, Gewichte, Versalien, Zeilenhöhen und Feldlabels werden wiederverwendet. Lange Vertrauenshinweise und Ergebnisbegründungen umbrechen auf 390 Pixeln lesbar; Stufen bleiben als kompakte, nummerierte Textbausteine scannbar.
- Spacing und Layout: eckige 0-Pixel-Radien, 44-Pixel-Primäraktionen, vorhandene Abschnittsabstände und das 480-Pixel-Desktop-Seitenpanel bleiben konsistent. Mobile belegt exakt 390 × 844 und besitzt keinen horizontalen Dokumentüberlauf.
- Farben und Tokens: ausschließlich bestehende Theme-, Rahmen-, Info-, Warn-, Fehler- und Erfolgsfarben. Hell plus Deuteranopie wurde live geprüft; Entscheidung und Risiko bleiben zusätzlich über Überschrift, Text, Icon, Rahmen und Ablaufstufe erkennbar.
- Bild- und Assetqualität: keine neuen Bildassets erforderlich. Frontline-Logo und etablierte MUI-Icons bleiben erhalten; keine Platzhalter, CSS-Zeichnungen, Emojis oder handgebauten SVGs.
- Copy und Inhalt: Die Texte unterscheiden fehlende, ungültige, unbekannt alte und veraltete Steam-Daten; sie erklären explizit die erste gespeicherte Prüfung und die spätere Hintergrundprüfung. Bei TK werden unsichere Profil-Ausnahmen, N-plus-eins-Toleranz, ein ignoriertes Jahresfeld und ein möglicherweise erst nach der Sperre fehlschlagender Discord-Platzhalter transparent benannt.
- Icons und Zustände: Simulation, Information, Entscheidung und Warnung verwenden dieselbe Iconfamilie. Aus, keine Aktion, Ausnahme, nicht belastbar, Konfigurationsfehler und Sperrmaßnahme sind nicht allein farbcodiert.
- Responsivität und Accessibility: beschriftete Comboboxen und Number Inputs, semantische Buttons, zugänglicher Schließen-Button, modaler Fokuskontext und `aria-live`-Ergebnis. Light-/Farbsehmodus besitzt weiterhin Text- und Symbolredundanz.

## Fachliche und funktionale Prüfung

- VAC: Aus, fehlender/ungültiger Datensatz, unbekanntes Alter, veraltete Daten, Markierungsausnahme, kein belastbarer Sperrzeitpunkt, Zeitraumüberschreitung, Schwelle, ungültiger Grundplatzhalter und Sperrmaßnahme werden deterministisch abgebildet.
- VAC: Die Oberfläche sagt korrekt, dass gespeicherte Daten zuerst synchron geprüft werden und die Hintergrundaktualisierung danach eine zweite Prüfung auslösen kann. Es wird keine Aktualität vorgetäuscht, wenn `updated` fehlt.
- TK: deaktivierte Regel, fehlendes Profil, nicht verfügbare VIP-Liste, VIP-/Sitzungs-/Markierungsausnahme, fehlender Beitritt, ausgenommene Waffe, Zeitfenster, eigene Kills/Tode und Teamkilltoleranz werden abgebildet.
- TK: `teamkill_tolerance_count = 2` löst erst beim dritten Teamkill aus. Die Laufzeit zeigt die explizit konfigurierte Einheit „24 Stunden“ statt der rechnerisch gleichen, aber inkonsistenten Form „1 Tag“.
- TK: Die bestehende Demokonfiguration mit `{player_name}` wird nicht stillschweigend umgeschrieben; die Vorschau warnt, dass der Backendvertrag nur `{player}` formatiert und die Benachrichtigung nach einer bereits ausgeführten Sperre fehlschlagen kann.
- Bei fehlendem Spielerprofil läuft die bestehende TK-Prüfung weiter und kennzeichnet VIP-, Sitzungs- und Markierungsausnahmen als unsicher. Ein verfügbarer VIP beendet die Prüfung vor der Maßnahme.
- Der Wirkungstest liest nur den aktuellen Formularentwurf, speichert nichts und sendet keine API-, RCON-, Steam- oder Gameserveraktion.

## Vergleichshistorie

1. Ausgangsvergleich: Beide Workbenches waren visuell konsistent, besaßen aber keine sichere Vorschau für daten- und vertrauensabhängige Entscheidungen.
2. Erste Umsetzung: [P2] Eine Laufzeit von 24 Stunden wurde im Testergebnis als „1 Tage“ dargestellt, obwohl die Workbench „24 Stunden“ zeigte. Die Simulation bewahrt nun die explizit konfigurierten Dauerkomponenten und lokalisiert Singular und Plural korrekt.
3. Erste Interaktionsprüfung: [P1] Das Ergebnis der langen TK-Simulation entstand unterhalb des sichtbaren Drawer-Bereichs. Die gemeinsame Testoberfläche scrollt neue Ergebnisse jetzt ohne Animation in den nächstgelegenen sichtbaren Bereich; die Post-Fix-Messung zeigt das Ergebnis Mobile von y = 392 bis y = 844.
4. Post-Fix-Vergleich bei identischen Viewports: Dauer, Entscheidung, Risikohinweis und Ablaufstufen sind sichtbar; keine offenen P0-, P1- oder P2-Findings.

## Implementation Checklist

- [x] Vorher und Nachher je Route und Viewport gemeinsam verglichen.
- [x] VAC- und TK-Fokuszustände auf Desktop und 390 × 844 Mobile geprüft.
- [x] 23 deterministische Vertrauens- und Fail-safe-Fälle gegen die Backend-Reihenfolge geprüft.
- [x] Fehlende Daten, veraltete Daten, unsichere Ausnahmen und nachgelagerte Auditfehler sichtbar gemacht.
- [x] Theme, Deuteranopie, Semantik und Mobile-Overflow geprüft.
- [x] Keine API-, Payload-, Persistenz-, Steam- oder Gameserveraktion ergänzt.

final result: passed

---

# Design QA · Phase 3.2 – Automod-Eskalation testen

## Prüfgrundlage

- Source Visual Truth: die unveränderten Workbench-Ausgangszustände in `.codex/phase32-baseline/no-leader-baseline-desktop-1440x900.png`, `.codex/phase32-baseline/no-leader-baseline-mobile-390x844.png`, `.codex/phase32-baseline/no-solo-tank-baseline-desktop-1440x900.png` und `.codex/phase32-baseline/no-solo-tank-baseline-mobile-390x844.png`; fachliche Zielwahrheit zusätzlich aus `rcon/automods/no_leader.py`, `rcon/automods/no_solotank.py`, `rcon/user_config/auto_mod_no_leader.py` und `rcon/user_config/auto_mod_solo_tank.py`.
- Implementierung: `.codex/phase32-baseline/no-leader-after-desktop-1440x900.png`, `.codex/phase32-baseline/no-leader-after-mobile-390x844.png`, `.codex/phase32-baseline/no-solo-tank-after-desktop-1440x900.png` und `.codex/phase32-baseline/no-solo-tank-after-mobile-390x844.png`.
- Fokuszustände: `.codex/phase32-baseline/no-leader-test-desktop-1440x900.png`, `.codex/phase32-baseline/no-leader-test-mobile-390x844.png`, `.codex/phase32-baseline/no-solo-tank-test-desktop-1440x900.png` und `.codex/phase32-baseline/no-solo-tank-test-mobile-390x844.png`.
- Theme-Evidenz: `.codex/phase32-baseline/no-solo-tank-theme-deuteranopia-1440x900.png`.
- Viewports und Normalisierung: Desktop jeweils 1440 × 900 CSS-Pixel und Bildpixel, Mobile jeweils 390 × 844 CSS-Pixel und Bildpixel, Browser-Dichte 1. Screenshots enthalten ausschließlich den App-Viewport.
- Primärzustand: Frontline Gold, dunkler Modus, Standard-Farbsehen; „Ohne Truppführer“ im Modus Beobachten, „Kein Solo-Panzer“ im Modus Aktiv. Theme-Prüfung im hellen Modus plus Deuteranopie und anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Die Ausgangs- und Nachher-Aufnahmen beider Routen wurden bei identischem Viewport und identischem gespeicherten Regelzustand im selben Vergleichseingang geöffnet. Informationsarchitektur, eckige Oberflächen, Typografie, Abschnittsnavigation und vorhandene Konfigurationsfelder bleiben unverändert. Neu ist ausschließlich die klar beschriftete Aktion „Auswirkung testen“: Desktop steht sie neben der Modussteuerung und zusätzlich in der Abschlussleiste, Mobile einmal kompakt direkt unter dem Modus. Dadurch bleibt die vertraute Workbench-Dichte erhalten und der Test ist vor dem Speichern erreichbar.

## Fokusvergleich

Die vier Drawer-Aufnahmen wurden gemeinsam verglichen. Beide Regeln verwenden dieselbe eckige Testoberfläche, reduzieren die Eingaben aber auf den jeweiligen Fachkontext: Truppzustand und Rolle bei fehlender Führung, Trupptyp und Besatzungsgröße beim Solo-Panzer. Ergebnis, Erläuterung und Stufenfolge bleiben am Desktop und auf 390-Pixel-Mobile lesbar; Mobile scrollt vertikal und erzeugt keinen horizontalen Dokumentüberlauf.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- Keine offenen P3-Polish-Punkte im Umfang dieses Pakets.

## Pflichtflächen

- Fonts und Typografie: vorhandene Frontline-Schriftfamilie, Gewichte, Versalien und Zeilenhöhen werden wiederverwendet. Titel, Hinweis, Felder, Ergebnis und nummerierte Stufen besitzen eine klare Hierarchie ohne problematische Umbrüche.
- Spacing und Layout: Desktop-Drawer mit bestehender Seitenpanelbreite, Mobile vollflächig und scrollbar; 44-Pixel-Aktionen, eckige Eingabeflächen und der vertikale Rhythmus entsprechen der Workbench. Bei 390 × 844 gilt `scrollWidth === clientWidth`.
- Farben und Tokens: ausschließlich bestehende Theme-, Rahmen-, Info-, Warn-, Fehler- und Erfolgsfarben. Heller Modus plus Deuteranopie wurde live geprüft; Text, Icon, Überschrift und Rahmen kennzeichnen Zustände zusätzlich zur Farbe.
- Bild- und Assetqualität: keine neuen Bildassets erforderlich. Vorhandenes Frontline-Logo und etablierte MUI-Icons bleiben erhalten; keine Platzhalter, CSS-Zeichnungen oder handgebauten SVGs.
- Copy und Inhalt: Deutsche und englische Texte erklären Beispielzustand, Wirkung, Schwellen und die Nicht-Invasivität des Tests. Die Oberfläche sagt ausdrücklich, dass nichts gespeichert und keine Gameserveraktion gesendet wird.
- Icons und Zustände: vorhandene Beaker-, Info- und Statusicons aus derselben Bibliothek. Aus, Beobachten und Aktiv sowie erlaubt, ausgenommen, wartend, pausiert und eskalierend werden nicht allein farbcodiert.
- Responsivität und Accessibility: beschriftete Comboboxen, Number Inputs, optionales Flagfeld, zugänglicher Schließen-Button und modaler Fokuskontext. Primäraktionen sind semantische Buttons; bei 390 × 844 kein horizontaler Überlauf.

## Fachliche und funktionale Prüfung

- Die Simulation spiegelt die bestehende Backend-Reihenfolge: globale Mindestzahl, Erkennung, Flag-/Level-/Rollen-Ausnahmen, Bestätigungen, Warnungen, Bestrafungen, Kick sowie Server- und Truppschwellen.
- `-1` bleibt eine unbegrenzte und terminale Warn- beziehungsweise Bestrafungsstufe. `0` deaktiviert eine Stufe, ohne eine nicht erreichbare Folgeaktion vorzutäuschen.
- Ohne Truppführer: vollständige Wirkungskette im Beobachtungsmodus, vorhandener Truppführer und globale Mindestzahl im Browser geprüft.
- Kein Solo-Panzer: vollständige aktive Wirkungskette sowie besetzter Panzertrupp mit zwei Mitgliedern im Browser geprüft.
- Schließen und erneutes Öffnen verwirft das alte Ergebnis. Ein Wechsel zwischen den beiden Profilarten setzt die Beispieldaten auf passende Standardwerte zurück.
- Browserkonsole: null Errors; ausschließlich die bekannte React-Router-v7-Future-Flag-Warnung im Entwicklungsmodus.

## Vergleichshistorie

1. Ausgangsvergleich: Beide Workbenches waren visuell bereits konsistent, besaßen aber keine sichere Vorschau ihrer vierstufigen Wirkungskette.
2. Umsetzung: gemeinsamer, lazy geladener Test-Drawer plus reine, datenvertragsneutrale Simulationslogik ergänzt. Der erste Vertragstest zeigte, dass ein „nur erkannt“-Beispiel wegen des realen Levelschutzes korrekt als Ausnahme galt; der Testdatensatz wurde auf Level 100 korrigiert, nicht die Fachlogik.
3. Finale Browser- und Bildprüfung bei identischen Viewports: keine offenen P0-, P1- oder P2-Findings.

## Implementation Checklist

- [x] Vorher und Nachher je Route und Viewport gemeinsam verglichen.
- [x] Drawer-Fokuszustände auf Desktop und Mobile gemeinsam geprüft.
- [x] Zwölf deterministische Eskalationsfälle gegen die Backend-Reihenfolge geprüft.
- [x] Theme, Deuteranopie, Semantik und Mobile-Overflow geprüft.
- [x] Keine API-, Payload-, Persistenz- oder Gameserveraktion ergänzt.

final result: passed

---

# Design QA · Phase 3.1 Konfigurations-Workbench und Level-Wirkungstest

## Prüfgrundlage

- Source Visual Truth: `.codex/phase3-foundation/level-baseline-mobile-390x844.png` für die bestehende Level-Regelstruktur sowie `.codex/phase3-foundation/seeding-baseline-desktop-1440x900.png` für die freigegebene eckige Konfigurations-Workbench, Modussteuerung und Änderungsleiste.
- Implementierung: `.codex/phase3-foundation/level-final-desktop-1440x900.png`, `.codex/phase3-foundation/level-final-mobile-390x844.png`, `.codex/phase3-foundation/level-test-final-desktop-1440x900.png` und `.codex/phase3-foundation/level-test-final-mobile-390x844.png`.
- Viewports und Normalisierung: Mobile jeweils 390 × 844 CSS-Pixel bei Browser-Dichte 1 und 390 × 844 Bildpixeln; Desktop jeweils 1440 × 900 CSS-Pixel bei Browser-Dichte 1 und 1440 × 900 Bildpixeln. Die Aufnahmen enthalten ausschließlich den App-Viewport ohne Browser-Chrome.
- Zustände: Frontline Gold, dunkler Modus, Standard-Farbsehen; Level-Regel im Modus „Aus“ sowie Wirkungstest vor und nach einer lokalen Simulation. Heller Modus plus Deuteranopie wurde zusätzlich live geprüft und ohne Speicherung verworfen.

## Full-View-Vergleich

Ausgangs- und Implementierungsaufnahmen wurden im selben Vergleichseingang geöffnet. Die Level-Seite bewahrt Navigation, Zusammenfassung, Abschnittsreihenfolge und sämtliche Formfelder, ergänzt aber die bereits freigegebene dreistufige Modussteuerung um einen klaren, lokal arbeitenden Einstieg „Auswirkung testen“. Die gemeinsame Änderungsleiste zeigt nun Geltungsbereich und Validierungszustand, ohne den bestehenden Speicher- und Wiederherstellungsfluss zu verändern. Mobile bleibt die erste Aufgabe im Viewport sichtbar; Desktop nutzt die vorhandene horizontale Arbeitsfläche ohne neue Karten- oder Radius-Sprache.

## Fokusvergleich

Der Wirkungstest wurde als eigener Fokusvergleich in Desktop- und Mobile-Aufnahmen geprüft. Desktop öffnet ein 480-Pixel-Seitenpanel, Mobile einen exakt 390 × 844 Pixel großen Vollbild-Drawer. Überschrift, Sicherheitsinformation, Beispielwerte, Rollenwahl, optionale Markierung und primäre Simulationsaktion sind vollständig lesbar. Es wurden ausschließlich vorhandene MUI-Icons und Theme-Tokens verwendet; keine Platzhalter, CSS-Zeichnungen oder neu erfundenen Bildassets.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Der erste Fokus liegt beim Öffnen auf dem semantischen Drawer-Abschnitt und nicht direkt auf dem Schließen-Button. Alle interaktiven Elemente liegen in korrekter Tab-Reihenfolge, besitzen zugängliche Namen und bleiben innerhalb des modalen Fokuskontexts.

## Pflichtflächen

- Fonts und Typografie: bestehende Frontline-Schriftfamilie, kondensierte Versalien, Gewichte, Zeilenhöhen und Laufweiten bleiben unverändert. Der neue Testtitel, Feldlabels, Statusstufen und Footer-Metadaten bilden eine klare Hierarchie ohne problematische Umbrüche.
- Spacing und Layout: eckige 0-Pixel-Radien, kompakte Rahmen, bestehende Abschnittsabstände und 44-Pixel-Aktionen bleiben konsistent. Level, Seeding und Ohne Truppführer besitzen bei 390 × 844 keinen horizontalen Dokumentüberlauf; der mobile Drawer belegt exakt den Viewport.
- Farben und Tokens: Akzent, Information, Erfolg, Warnung und deaktivierte Zustände verwenden vorhandene Theme-Tokens. Heller Modus plus Deuteranopie wurde live geprüft; Status bleibt zusätzlich über Text, Symbol und Umrandung erkennbar.
- Bild- und Assetqualität: vorhandenes Frontline-Logo und die etablierte MUI-Iconbibliothek werden wiederverwendet. Es wurden keine neuen Rasterbilder, handgebauten SVGs, Emoji- oder CSS-Assets eingeführt.
- Copy und Inhalt: „Auswirkung testen“ und „Simulation ausführen“ unterscheiden Entwurfstest und Persistenz eindeutig. Der Hinweis erklärt ausdrücklich, dass weder gespeichert noch eine Nachricht an den Gameserver gesendet wird. Rollenbezeichnungen sind lokalisiert.
- Icons und Zustände: Modus, Simulation, Information und Ergebnis verwenden dieselbe Iconfamilie. Aus, Beobachten, Aktiv, bereit, ungültig und Simulationsergebnis werden nicht allein farbcodiert.
- Responsivität und Accessibility: Desktop 1440 × 900 und Mobile 390 × 844 geprüft; genau eine H1, beschriftete Eingaben, zugänglicher Schließen-Button, `aria-live`-Ergebnis und praktische Touch-Ziele vorhanden.

## Interaktionen und Datenverträge

- Gemeinsame Modussteuerung auf Level, Seeding und Ohne Truppführer geprüft; Wechsel erzeugt den bestehenden Dirty-Zustand, Wiederherstellen setzt gespeicherte Werte zurück.
- Acht deterministische Level-Szenarien prüfen Aus, Wartezustand, Ausnahmen, globale Grenzen, rollenbezogene Eskalation, erkannte Verstöße ohne aktive Maßnahme und erlaubte Spieler.
- Der Wirkungstest liest ausschließlich sichtbare Formularwerte, speichert nichts und ruft keine API auf. Loader, Actions, Feldnamen, Merge-Verhalten, Payloads und unbekannte Konfigurationswerte bleiben unverändert.
- Browserkonsole im Abschlusslauf: null Errors.

## Vergleichshistorie

1. Ausgangsvergleich: [P2] Modussteuerung war zwischen geführten Formularen und Seeding doppelt implementiert; [P2] die neue Simulation zeigte nach Schließen und erneutem Öffnen noch das vorherige Ergebnis; [P2] eine direkte Einbindung hätte den gemeinsamen Konfigurationschunk unnötig vergrößert.
2. Umsetzung: gemeinsame `ConfigOperationModeControl`, wiederverwendbare Änderungsmetadaten und lazy-geladener Level-Test ergänzt. Der Ergebniszustand wird beim Schließen zurückgesetzt.
3. Finale Desktop-/Mobile-Aufnahmen bei identischen Viewports und erneute Browserprüfung: keine offenen P0-, P1- oder P2-Findings. Das initiale Bundle-Budget bleibt mit exakt 1.500,00 kB Rohgröße innerhalb des Vertrags.

## Implementation Checklist

- [x] Source und Implementierung im selben Vergleichseingang geprüft.
- [x] Level, Seeding und Ohne Truppführer funktional gegen den gemeinsamen Modusvertrag geprüft.
- [x] Wirkungstest vor und nach Simulation sowie nach erneutem Öffnen geprüft.
- [x] Desktop, Mobile, Theme, Deuteranopie, Semantik und Browserkonsole geprüft.
- [x] Produktionsbuild, Bundle-Budget und alle relevanten Vertragschecks bestanden.
- [x] Keine API-, Persistenz- oder Konfigurationsmigration eingeführt.

final result: passed

---

# Design QA · Phase 2.5 Dienste, Spiel- und Audit-Protokolle

## Prüfgrundlage

- Source Visual Truth: bestehende funktionsfähige Ansichten in `.codex/phase25-baseline/services-desktop-1440x900.png`, `.codex/phase25-baseline/services-mobile-390x844.png`, `.codex/phase25-baseline/game-logs-desktop-1440x900.png`, `.codex/phase25-baseline/game-logs-mobile-390x844.png`, `.codex/phase25-baseline/audit-logs-desktop-1440x900.png` und `.codex/phase25-baseline/audit-logs-mobile-390x844.png`; Zielhierarchie zusätzlich aus dem freigegebenen Product-Design-Konzept für `/settings/services`, `/records/game-logs` und `/records/audit-logs`.
- Implementierung: `.codex/phase25-baseline/services-after-desktop-1440x900.png`, `.codex/phase25-baseline/services-after-mobile-390x844.png`, `.codex/phase25-baseline/game-logs-after-desktop-1440x900.png`, `.codex/phase25-baseline/game-logs-after-mobile-390x844.png`, `.codex/phase25-baseline/audit-logs-after-desktop-1440x900.png` und `.codex/phase25-baseline/audit-logs-after-mobile-390x844.png`.
- Viewports und Normalisierung: Mobile jeweils 390 × 844 CSS-Pixel bei Browser-Dichte 1 und 390 × 844 Bildpixeln; Desktop jeweils 1440 × 900 CSS-Pixel bei Browser-Dichte 1 und 1440 × 900 Bildpixeln. Die Aufnahmen enthalten nur den App-Viewport ohne Browser-Chrome.
- Zustände: Frontline Gold, dunkler Modus, Standard-Farbsehen; Dienste mit simulierten Laufzeitdaten, Spiel- und Audit-Protokolle mit realistischen Mirage-Demodaten. Helles Theme plus Deuteranopie wurde separat live geprüft und anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Die Vorher- und Nachher-Aufnahmen wurden je Route bei identischem Viewport gemeinsam beurteilt. Die Diensteansicht führt jetzt von Betriebsbereitschaft und Fehlerlage über die Abhängigkeitskette RCON → Worker → Scheduler zu den einzelnen Steuerungen. Desktop bleibt kompakt, während Mobile die Kette vertikal und bereits im ersten Viewport verständlich zeigt. Spiel- und Audit-Protokolle bewahren ihre dichten Desktop-Arbeitsflächen, reduzieren Mobile aber die zuvor hohen Filterblöcke auf Suche, klaren Filtereinstieg und wenige aktive Kategorien. Dadurch erscheinen die ersten relevanten Ereignisse beziehungsweise Auditzeilen bereits im ersten mobilen Viewport.

## Fokusvergleich

Ein zusätzlicher Bildausschnitt war nicht erforderlich. Statuszusammenfassung, Dienstekette, Dienststeuerung, mobile Such-/Filterleiste sowie erste Protokollzeilen sind in den vollständigen Desktop- und Mobile-Aufnahmen lesbar. Die Filter-Drawer und der Audit-Detail-Drawer wurden zusätzlich interaktiv im Browser geprüft, weil ihre Zustände nicht gleichzeitig mit der Listenansicht sichtbar sein können.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Im Entwicklungsmodus protokolliert React Router weiterhin die bekannte Future-Flag-Warnung zu `v7_startTransition`. Es gibt keine route-spezifischen Runtime-Fehler und kein sichtbares Fehlverhalten.

## Pflichtflächen

- Fonts und Typografie: bestehende Frontline-Schriftfamilie, kondensierte Versalien, Gewichte und Zeilenhöhen bleiben erhalten. Kennzahlen, Dienstzustände, Ereignistypen, Zeitangaben und Filterbeschriftungen besitzen eine klare, scanbare Hierarchie ohne problematische Überlagerung.
- Spacing und Layout: Dienste nutzen eine eckige, eng geführte Betriebskette. Mobile Filter reduzieren den ersten Viewport auf die primäre Suchaufgabe und öffnen Detailfelder in einem Vollhöhen-Drawer. Bei 390 × 844 und 1440 × 900 entsteht kein horizontaler Dokumentüberlauf.
- Farben und Tokens: Flächen, Rahmen, Status und Auswahl verwenden ausschließlich vorhandene Theme- und Semantik-Tokens. Heller Modus plus Deuteranopie wurde live geprüft; Zustand bleibt zusätzlich über Text, Icon und Umrandung verständlich.
- Bild- und Assetqualität: Die datengetriebenen Ansichten benötigen keine neuen Bilder. Frontline-Branding und etablierte MUI-Icons werden wiederverwendet; keine Platzhalter, CSS-Zeichnungen, Emojis oder handgebauten SVG-Ersatzassets wurden eingeführt.
- Copy und Inhalt: Betriebsbereitschaft, Fehlerlage, Abhängigkeit, Betriebswirkung sowie die mobilen Filteraktionen sind auf Deutsch und Englisch knapp benannt. Es werden keine Zustände oder Betriebszusagen erfunden.
- Icons und Zustände: RCON, Worker, Scheduler, Start, Stopp, Filter, Export und Detailansicht verwenden eine gemeinsame Iconfamilie und zugängliche Beschriftungen. Aktiv, Fehler, ausgewählt und deaktiviert werden nicht allein über Farbe vermittelt.
- Responsivität und Accessibility: je Route genau eine H1; 390 × 844 und 1440 × 900 ohne horizontalen Überlauf; beschriftete Filter-Drawer, 44-Pixel-Aktionen, semantische Formfelder und bestehende Tastatur-Fokusdarstellung geprüft.

## Interaktionen und Datenverträge

- Audit-Suche mit `Wotan` abgesendet; die bestehende Query `parameters=Wotan&time_sort=desc&page_size=50&page=1` blieb vollständig erhalten und reduzierte die Liste auf einen Treffer.
- Auditzeile geöffnet; der bestehende Detail-Drawer zeigte Akteur, Ziel, ID, Server, lokale und UTC-Zeit, übermittelte Werte und Ergebnis.
- Spielprotokoll-Suche mit `FLN_Wolf` abgesendet; die bestehende Query bewahrte `limit=500`, `time_sort=desc`, `exact_player=false`, `exact_action=false` und `player_name=FLN_Wolf`.
- Die mobilen Drawer führen weiterhin sämtliche bisherigen Zeit-, Server-, Aktions-, Exakt-, Sortier- und Seitengrößenfelder. Versteckte Formfelder sichern beim Portal-Rendering die vorhandenen GET-Verträge.
- Dienst-Loader, Dead-Letter-, Diagnose- und Health-Verträge sowie die POST-Felder `service_name` und `action` (`start`/`stop`) bleiben unverändert. Für die QA wurde keine laufende Dienstaktion ausgelöst.

## Vergleichshistorie

1. Ausgangsvergleich: [P2] Mobile Dienste erklärten Abhängigkeiten nicht zusammenhängend; [P2] Spiel- und Audit-Filter verdrängten den eigentlichen Protokollinhalt aus dem ersten Viewport; [P1] die mobile Spielprotokollzeile überlagerte Zeit- und Ereignisspalten.
2. Umsetzung: Betriebskette und kompakte Dienststeuerungen ergänzt; mobile Primärfilter mit Detail-Drawern eingeführt; mobile Timeline-Metadaten in eine eigene, nicht überlagernde Zeile verschoben.
3. Erste Nachher-Prüfung: Die „Alle Filter entfernen“-Beschriftung beanspruchte auf Mobile unnötig Breite. Der mobile Zustand wurde auf eine zugänglich beschriftete Iconaktion verdichtet.
4. Finale Vorher-/Nachher-Vergleiche bei identischen Viewports: keine offenen P0-, P1- oder P2-Findings.

## Technische Validierung

- Produktionsbuild bestanden; ausschließlich die bekannte Warnung für bestehende Chunks über 500 kB bleibt.
- Design Foundation, Seitensemantik, Action Feedback, Konfigurationskompatibilität, Admin-Aktionsvertrag, Operator-Copy und Navigation Shell bestanden.
- Initiales Bundle-Budget bestanden: 1.499,96 kB raw / 483,01 kB gzip; Entry 401,44 kB raw / 121,64 kB gzip.
- Browserkonsole: keine Errors; zwei Instanzen der bekannten React-Router-v7-Future-Flag-Warnung im Entwicklungsmodus.

## Implementation Checklist

- [x] Source und Umsetzung je Route im selben Vergleichseingang geprüft.
- [x] Desktop und 390 × 844 ohne horizontalen Dokumentüberlauf geprüft.
- [x] Spiel- und Auditfilter sowie Audit-Detail funktional geprüft.
- [x] Theme, Deuteranopie, Semantik und sichtbare Fokusdarstellung geprüft.
- [x] Loader-, GET-, POST-, Export- und Konfigurationsverträge beibehalten.
- [x] Keine offenen P0-, P1- oder P2-Findings.

final result: passed

---

# Design QA · Phase 2.3 Teams und Autobalancer

## Vergleichsziel

- Source Visual Truth: `.codex/phase23b-baseline/team-mobile-390x844.png`, `.codex/phase23b-baseline/team-desktop-1440x900.png`, `.codex/phase23b-baseline/autobalancer-mobile-390x844.png` sowie die Routenanforderungen für Teams und Autobalancer in `docs/product-design/rcon-product-concept.md`.
- Implementierung: `.codex/phase23b-baseline/team-after-mobile-viewport.png`, `.codex/phase23b-baseline/team-after-desktop-viewport.png`, `.codex/phase23b-baseline/autobalancer-final-mobile-390x844.png` und `.codex/phase23b-baseline/autobalancer-final-desktop-1440x900.png`.
- Primärer Vergleichszustand: Frontline Gold, dunkler Modus, Standard-Farbsehen, simulierte Live-Daten; Teamübersicht mit Gefechtsstatus und Autobalancer-Liveübersicht.

## Normalisierung

- Mobile Source und Implementierung: 390 × 844 CSS-Pixel bei Browser-Dichte 1.
- Desktop Source und Implementierung: 1440 × 900 CSS-Pixel bei Browser-Dichte 1.
- Browser-Chrome wurde nicht erfasst. Die vollständigen Viewports enthalten alle für diesen Vergleich relevanten Kopf-, Status-, Filter- und Arbeitsbereiche.

## Full-View- und Fokusvergleich

Die Teamansicht behält auf Desktop ihre dichte Führungsstruktur. Mobile wurde der zuvor hohe, vertikal gestapelte Gefechtsstatus zu einer dreispaltigen Team-/Spielstand-/Team-Zeile mit direkt anschließender dreispaltiger Problemlage verdichtet. Dadurch sind Autobalancer-Hinweis und alle Teamfilter bereits im ersten 390 × 844-Viewport erreichbar. Der Fokusvergleich umfasste Gefechtsstatus, Problemlage, Teamfilter und Kapazitätszustände.

Der Autobalancer ersetzt auf Mobile die abgeschnittene horizontale Tabnavigation durch ein beschriftetes Bereichs-Select. Desktop behält die schnelle Tabreihe. Eine fünfstufige operative Zeitleiste ordnet Live-Zustand, Balance-Delta, geplante Verschiebung, letzten Eingriff und Cooldown. Der Fokusvergleich umfasste den Bereichswechsel, den nächsten empfohlenen Schritt und die vollständige Zeitleiste; zusätzliche Ausschnitte waren nicht erforderlich, da alle Beschriftungen in den Full-View-Aufnahmen lesbar sind.

## Findings und Iterationen

1. Ausgangsvergleich: Der mobile Teamstatus beanspruchte zu viel Höhe; die Autobalancer-Tabs wurden horizontal abgeschnitten.
2. Erste Umsetzung: Teamstatus, Problemindikatoren, Statusfilter und mobile Bereichsauswahl wurden verdichtet beziehungsweise neu geordnet. Dabei blieben in der deutschen Autobalancer-Ansicht die Backend-Standardbezeichnungen „Allies“ und „Axis“ sichtbar; dies wurde als P2-Copy-Inkonsistenz bewertet.
3. Korrektur: Die beiden englischen Standardwerte werden in diesem deutschen Dashboard als „Alliierte“ und „Achsenmächte“ normalisiert. Andere, vom Backend gelieferte Teambezeichnungen bleiben unverändert erhalten. Der erneute Vergleich zeigte keine offenen P0-, P1- oder P2-Befunde.

Verbleibende Datenlücken:

- **P3:** Der aktuelle Teamvertrag liefert keinen Zustand für gesperrte Rollen. Der entsprechende Filter wird deshalb nicht vorgetäuscht und bleibt eine spätere, explizite Vertragserweiterung.
- **P3:** Der Autobalancer-Status liefert keinen verlässlichen letzten tatsächlich ausgeführten Eingriff. Die Zeitleiste kennzeichnet diesen Zustand transparent, statt einen Zeitpunkt zu erfinden.

## Pflichtflächen und Interaktionen

- Typografie und Layout: bestehende Frontline-Hierarchie, eckige Flächen, kompakte Karten und konsistente Abstände; bei 390 × 844 gilt `scrollWidth === clientWidth === 390` auf beiden Routen.
- Farben und Tokens: ausschließlich bestehende Theme- und Semantik-Tokens. Status bleibt zusätzlich über Text, Icons und Rahmen erkennbar. Helles Theme plus Deuteranopie wurde geprüft und ohne Speicherung verworfen.
- Assets: vorhandenes Frontline-Branding und die etablierte MUI-Iconbibliothek; keine Platzhalter, CSS-Zeichnungen oder neu erfundenen Bildassets.
- Copy: kurze deutsche Operator-Texte; keine nicht belegten Zusagen oder erfundenen Zustände.
- Tastatur: Autobalancer-Bereichsselect sowie Team-Statusselect mit Enter geöffnet und ausgewählt; „Vorschläge prüfen“ und „Überbelegt“ wurden korrekt aktiviert.
- Semantik: beide Routen besitzen genau eine H1; Autobalancer ist in Breadcrumb und Navigation unter „Live-Betrieb“ eingeordnet.
- Browserkonsole: null Errors in den sauberen Abschlussläufen.

final result: passed

---

# Design QA · Phase 2.2 Mobile Live-Einsatz

## Vergleichsziel

- Source Visual Truth: `.codex/phase23-baseline/live-desktop-1440x900.png`, `.codex/phase23-baseline/live-mobile-390x844.png` und die bestätigte Zielbeschreibung in `docs/product-design/rcon-product-concept.md` für `/views/live`.
- Implementierung: `.codex/phase23-baseline/live-final-desktop-1440x900.png`, `.codex/phase23-baseline/live-final-mobile-390x844.png` sowie die zusätzliche schmale Evidenz `.codex/phase23-baseline/live-after-mobile-320x720.png`.
- Zustand: Frontline Gold, dunkler Modus, Standard-Farbsehen, Einsatz-Tab aktiv, sechs Demo-Spieler, zwei Commander-Warnungen, VIP-/Watchlist-Kontext und unveränderte Live-Protokolldaten.

## Normalisierung

- Desktop: Source und Implementierung jeweils 1440 × 900 Pixel bei 1440 × 900 CSS-Pixeln und Dichte 1.
- Mobile: Source und Implementierung jeweils 390 × 844 Pixel bei 390 × 844 CSS-Pixeln und Dichte 1.
- Zusätzlicher Responsive-Check: 320 × 720 Pixel bei Dichte 1.
- Alle Vergleiche zeigen dieselbe Route, Sprache, Theme-Familie und denselben primären Einsatz-Zustand ohne Browser-Chrome.

## Full-View-Vergleich

Desktop bleibt bewusst unverändert: Split View, Lagekarten, Spieleroperationen und Live-Protokoll behalten ihre Proportionen und Informationsdichte. Mobile ersetzt die zwei verpflichtenden horizontalen Suchwege durch eine klare Priorität: Commander-Warnungen liegen vollständig untereinander, mittlere und informative Zustände bilden ein kompaktes Zweispaltenraster, und die Spieler-Schnellfilter werden als sichtbar beschriftetes Select bedient. Die Einsatz/Protokoll-Tabs und die Reihenfolge Serverstatus – Lage – Serveraktionen – Spieler bleiben erhalten.

## Fokusvergleich

Ein separater Bildausschnitt war nicht erforderlich. Die entscheidenden Oberflächen – Warnkarten, Kontextkarten, Einsatz/Protokoll-Tabs, Suchfeld und Spielerzeilen – sind im 1:1-Mobile-Vergleich lesbar. Das unterhalb des ersten Viewports liegende Select wurde zusätzlich im echten Browser per Tastatur geöffnet und von „Alle · 6“ auf „Achsenmächte · 3“ gestellt; die sichtbare Liste reduzierte sich auf drei Spieler. Der Spieler-Detailbereich wurde geöffnet und mit Escape geschlossen.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Bei 320 Pixeln kürzt der globale Statuskopf Kartenname und Restzeit früher als bei 390 Pixeln. Das ist die bestehende, beabsichtigte Shell-Priorisierung; alle Werte behalten zugängliche Namen und die Live-Arbeitsfläche selbst bleibt ohne seitlichen Überlauf.

## Pflichtflächen

- Fonts und Typografie: bestehende Bahnschrift-/Arial-Narrow-Hierarchie bleibt erhalten. Mobile Spielernamen und K/D-Werte verwenden nun wie die Desktop-Spielertabelle die dezente Stärke 300; Teamzugehörigkeit bleibt im Kontexttext und über Fraktionssymbole erkennbar.
- Spacing und Layout: Warnungen erhalten auf Mobile die volle Breite, Sekundärinformationen ein belastbares Zweispaltenraster. Rahmen, Abstände, 44-Pixel-Bedienelemente und eckige Formensprache bleiben konsistent. 390 × 844 und 320 × 720 zeigen keinen sichtbaren Dokumentüberlauf.
- Farben und Tokens: ausschließlich vorhandene Theme-, Status- und Transparenz-Tokens werden verwendet. Helles Theme plus Deuteranopie wurde in der echten Darstellungsoberfläche geprüft und anschließend ohne Speicherung verworfen.
- Bild- und Assetqualität: vorhandene MUI-Icons und Frontline-Assets bleiben unverändert; keine Platzhalter, CSS-Zeichnungen, Emojis oder neuen Bildassets.
- Copy und Inhalt: „Jetzt prüfen“, Prioritäten, Spielstand, nächste Karte und „Spieler-Schnellfilter“ bleiben verständlich. Der mobile Spielstand verwendet die kurze Beschriftung, während Desktop den Teamkontext vollständig behält.
- Zustände und Interaktionen: Lagekarten-Filter, beschriftetes Mobile-Select, Einsatz/Protokoll-Wechsel, Player-Detail-Sheet und Escape-Schließen geprüft. Die vorhandenen API-, Tabellen- und Aktionsverträge bleiben unverändert.
- Browserfehler: im sauberen Abschlusslauf null Console-Errors.

## Vergleichshistorie

1. Ausgangsvergleich: Mobile Lagekarten und Spieler-Schnellfilter erforderten horizontales Scrollen; wichtige Zustände und Filter lagen außerhalb des ersten sichtbaren Bereichs. Als P1-Nutzungsproblem aufgenommen.
2. Erste Korrektur: Warnungen vertikal priorisiert, Sekundärzustände gerastert und Schnellfilter durch ein beschriftetes Select ersetzt. Der direkte Vergleich zeigte noch eine gekürzte Spielstandsbeschriftung und einen unnötig einzeiligen Kartenwert als P2.
3. Zweite Korrektur: kurze Mobile-Beschriftung für den Spielstand ergänzt und Kontextwerte auf bis zu zwei Zeilen freigegeben. Erneuter 390- und 320-Pixel-Vergleich ohne offene P0/P1/P2-Findings.

## Implementation Checklist

- [x] Desktop-Split-Ansicht ohne visuelle oder funktionale Regression bewahrt.
- [x] Mobile Lagekarten ohne horizontale Pflichtnavigation priorisiert.
- [x] Spieler-Schnellfilter vollständig beschriftet und tastaturbedienbar umgesetzt.
- [x] Mobile Spielerzeilen auf neutrale, dezente Tabellen-Typografie vereinheitlicht.
- [x] Desktop, 390 × 844, 320 × 720, Tastatur, Dark/Light und Deuteranopie geprüft.
- [x] Build, Design-, Semantik-, Feedback-, Polling-, Konfigurations-, Admin-Aktions-, Operator-Copy- und Navigation-Verträge bestanden.

final result: passed

---

# Design QA · Phase 2.1 Meldungsleitstelle

## Vergleichsziel

- Source Visual Truth: `.codex/phase2-baseline/incidents-desktop.png` (1440 × 900) und `.codex/phase2-baseline/incidents-mobile.png` (390 × 844), ergänzt um die Leitstellenanforderungen in `docs/product-design/rcon-product-concept.md`.
- Implementierung: `.codex/phase2-baseline/incidents-after-desktop-final.png`, `.codex/phase2-baseline/incidents-after-mobile.png` und der fokussierte mobile Bearbeitungszustand `.codex/phase2-baseline/incidents-detail-mobile-final-viewport.png`.
- Primärer Zustand: Frontline Gold, dunkler Modus, Standard-Farbsehen, neue Meldung ausgewählt; realistische Mirage-Demodaten mit drei Statuszuständen.

## Normalisierung

- Desktop-Source und Desktop-Implementierung: jeweils 1440 × 900 Pixel bei 1440 × 900 CSS-Pixeln, Browser-Dichte 1.
- Mobile-Source und Mobile-Implementierung: jeweils 390 × 844 Pixel bei 390 × 844 CSS-Pixeln, Browser-Dichte 1.
- Die Vorher-/Nachher-Paare wurden jeweils gemeinsam in einem Vergleichsinput geöffnet. Browser-Chrome und externe Canvas-Flächen sind nicht Bestandteil der Screenshots.

## Full-View-Vergleich

Die globale Frontline-Shell, die kondensierte Typografie, die eckigen Flächen, feinen Trenner und die Gold-/Grün-Dunkel-Tonalität bleiben unverändert. Die frühere einspaltige Desktop-Liste wurde innerhalb dieser vorhandenen Sprache zu einer Leitstellenansicht erweitert: kompakte Lagekennzahlen, Einsatzwarteschlange und dauerhaft sichtbarer Vorgangskontext bilden nun eine klare Beobachten–Entscheiden–Handeln-Hierarchie. Auf Mobile ersetzt eine vollständig beschriftete Statusauswahl die zuvor rechts abgeschnittene Tabreihe. Dadurch bleibt die Filteraufgabe bei 390 Pixeln vollständig bedienbar, ohne horizontales Scrollen oder verborgene Ziele.

## Fokusvergleich

Der mobile Bearbeitungsdialog wurde separat bei 390 × 844 geprüft. Titel, Status, Server, Alter, Quelle, Meldungsgrund, Zuständigkeit, Zeitpunkte, Originalmeldung, nächster Schritt und alle zulässigen Aktionen sind innerhalb eines einzigen vertikalen Vorgangs lesbar. Die Aktionsflächen besitzen mindestens 44 Pixel Höhe, bleiben eckig und nutzen ausschließlich die vorhandene MUI-Iconfamilie. Für den früheren mobilen Detaildialog lag kein belastbares Source-Capture vor; deshalb wurde dieser Fokuszustand gegen die vorhandenen Frontline-Dialog-, Button-, Typografie- und Tokenmuster geprüft.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Der Auto-Update-Chip ist bewusst kompakt und vermittelt seinen Zustand zusätzlich über den Text „Live · 15 s“; das kleine Statussymbol ist im dunklen Theme optisch zurückhaltend. Eine stärkere Hervorhebung ist nicht erforderlich, solange die Aktualisierung normal arbeitet.

## Pflichtflächen

- Fonts und Typografie: vorhandene Bahnschrift-/Arial-Narrow-Hierarchie, Gewichte, Großbuchstaben, Laufweiten und Body-Schrift bleiben erhalten. Seitentitel, Warteschlange, Vorgangstitel, Metadaten und Aktionen sind eindeutig abgestuft.
- Spacing und Layout: 4er-Kennzahlenraster, 0,9/1,1-Desktop-Split, 16-Pixel-Arbeitsabstände, eckige Rahmen und 44-Pixel-Touchziele erzeugen eine dichte, aber scanbare Leitstellenoberfläche. Mobile besitzt bei 390 × 844 einen Dokument-`scrollWidth` von 390 Pixeln bei 390 Pixeln `clientWidth`.
- Farben und Tokens: ausschließlich vorhandene Theme-, Divider-, Action- und semantische Statusfarben. Helles Theme sowie Deuteranopie wurden über die echte Darstellungsoberfläche angewendet; Text, Symbol und Umrandung bleiben redundante Zustandsträger. Anschließend wurde der Frontline-Standard wiederhergestellt.
- Bild- und Assetqualität: Für diesen datengetriebenen Arbeitsbereich sind keine Produktbilder vorgesehen. Frontline-Logo und etablierte MUI-Icons werden unverändert wiederverwendet; keine CSS-Zeichnungen, Platzhalter oder nachgebauten SVGs.
- Copy und Inhalt: „Einsatzwarteschlange“, „Aktiver Vorgang“ und „Nächster Schritt“ erklären Aufgabe und Arbeitsrichtung. Quelle, Eingang, Aktualisierung und Originalmeldung bleiben nachvollziehbar; Deutsch und Englisch wurden ergänzt.
- Zustände und Interaktionen: Laden, Leer, Fehler, Auswahl, Live-Aktualisierung, Statusfilter, Übernehmen, Ablehnen mit Bestätigung, Abschließen und geschlossener Verlauf bleiben erhalten. „Übernehmen“ wurde gegen den unveränderten API-Vertrag erfolgreich ausgeführt.
- Accessibility: genau eine H1; Warteschlange und Detailbereich besitzen beschriftete Regionen; Filter-Select, Dialog und Aktionen haben zugängliche Namen. Escape schließt den mobilen Dialog. Status wird nicht allein über Farbe vermittelt.
- Browserfehler: null Console-Errors. Es bleibt ausschließlich die bekannte React-Router-v7-Future-Flag-Warnung im Entwicklungsmodus.

## Vergleichshistorie

1. Erster Desktop-Vergleich: [P2] „Übernommen 1“ brach im fünffach geteilten Statusfilter zweizeilig um und störte den horizontalen Rhythmus.
2. Fix: Tab-Inhalte auf eine Zeile begrenzt und horizontales Innenpadding verdichtet, ohne Zielgröße oder Beschriftung zu verkleinern.
3. Zweiter Desktop-Vergleich bei identischen 1440 × 900: alle fünf Statusziele stehen einzeilig und gleichmäßig; keine offenen P0/P1/P2-Befunde.
4. Mobile Vorher-/Nachher-Vergleich bei identischen 390 × 844: die abgeschnittene Tabnavigation ist durch eine vollständige, beschriftete Auswahl ersetzt; kein horizontaler Überlauf.

## Implementation Checklist

- [x] Source und Umsetzung bei identischen Desktop- und Mobile-Viewports verglichen.
- [x] Desktop-Warteschlange und permanenter Vorgangskontext geprüft.
- [x] Mobile Statusauswahl und Vollbildbearbeitung geprüft.
- [x] Statusmutation, Escape, Theme und Farbsehmodus geprüft.
- [x] Production Build erfolgreich; keine neuen Console-Errors.
- [x] Keine offenen P0-, P1- oder P2-Findings.

final result: passed

---

# Design QA: Konsolen-Admins, Option 1 „Berechtigungsregister“

## Prüfgrundlage

- Gewählte visuelle Richtung: Option 1 „Berechtigungsregister“.
- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-a5416038-aef0-4b7d-bee3-e0bda743fa61.png`
- Implementierte Route: `http://127.0.0.1:3005/settings/console-admins`
- Implementierung: `.codex/design-qa/console-admins-option-1/implementation.png`
- Gesamtvergleich: `.codex/design-qa/console-admins-option-1/comparison-full.png`
- Fokusvergleich: `.codex/design-qa/console-admins-option-1/comparison-focus.png`
- Mobile Evidenz: `.codex/design-qa/console-admins-option-1/mobile.png`
- Source und Desktop-Implementierung: jeweils 1487 × 1058 px, dunkles Frontline-Theme, deutsche Sprache und derselbe vorgemerkte Änderungszustand.

## Ergebnis

- Die Seite folgt der gewählten Register-Struktur: kompakter Seitenkopf mit Rollenübersicht, feste Erfassungsspalte, vollbreite Admin-Tabelle und gemeinsame Aktionsleiste.
- Die eckige Frontline-Designlinie, dunkle grün-schwarze Flächen, goldene Akzente, feine Trenner und die bestehende Typografie wurden konsequent beibehalten.
- Hinzufügen, Rollenwechsel und Entfernen sind als getrennte, farblich codierte Änderungszustände sichtbar. Keine dieser Änderungen wird vor dem abschließenden Speichern an den Server übertragen.
- Mehrfachauswahl, Namens- und Steam64-Suche, Rollenfilter sowie Import und Export sind im Tabellenkopf zusammengeführt.
- Der vom Nutzer gemeldete Höhenversatz wurde behoben: Die Mehrfachaktion lautet kompakt „3 entfernen“, bleibt einzeilig und ist nun exakt auf „Import / Export“ ausgerichtet.
- Mobil wird die Erfassung eingeklappt, die Tabelle wechselt in lesbare Einzelkarten und die Aktionsleiste bleibt nur bei tatsächlich ungespeicherten Änderungen klebend.

## Vergleichsverlauf

1. Der erste Vergleich zeigte als P1, dass das Suchfeld in der mobilen Spaltenanordnung wegen seiner Desktop-Flexbasis unnötig viel Höhe belegte. Die Flexbasis wird nun breakpointabhängig gesetzt.
2. Die mobile Prüfung zeigte als P1, dass die immer klebende Aktionsleiste Karten verdecken konnte. Im sauberen Zustand ist sie mobil statisch; bei Änderungen bleibt sie erreichbar.
3. Die Rollenreihenfolge wurde an die gewählte Richtung angepasst: Senior, Junior, Spectator. Der sichere Standard für neue Einträge bleibt bewusst Spectator.
4. Markierte Tabellenzeilen verwenden jetzt dezente, statusbezogene Flächen statt einer starken einheitlichen Auswahlfarbe.
5. Der abschließende Fokusvergleich zeigte keine offenen P0-, P1- oder P2-Abweichungen.

## Funktions- und Qualitätsprüfung

- Neuer Admin mit Name, Steam64-ID und Rolle vorgemerkt; Status „Neu“ und Änderungszähler geprüft.
- Bestehende Rolle Senior → Junior geändert; Inline-Auswahl und Status „Rolle geändert“ geprüft.
- Bestehenden Admin zum Entfernen vorgemerkt und Rückgängig-Aktion sichtbar geprüft.
- Namenssuche, Zurücksetzen der Suche sowie Einzel- und Mehrfachauswahl geprüft.
- Speicherbestätigung bei vorgemerkter Entfernung geöffnet und ohne Servermutation abgebrochen.
- Datei-Upload-Komponente korrigiert: `accept` und `onChange` liegen jetzt auf dem echten Dateifeld; der Upload-Button bleibt per Tastatur erreichbar.
- Produktionsbuild und Prettier-Prüfung bestanden; nur die bereits bestehende Chunk-Größenwarnung.
- Browserkonsole: keine Laufzeitfehler; ausschließlich die bereits bestehende React-Router-Future-Flag-Warnung.

final result: passed
---

# Design QA: Spielerakten-Karten, Richtung 1

## Prüfgrundlage

- Referenz: `.codex/audits/player-card-2026-08-30/01-current-player-cards.png`
- Umsetzung: `.codex/design-qa/player-card-direction-1/implementation.png`
- Gesamtvergleich: `.codex/design-qa/player-card-direction-1/comparison-full.png`
- Detailvergleich: `.codex/design-qa/player-card-direction-1/comparison-focus.png`
- Viewport: 2353 × 1272 Pixel, dunkles Theme, Kartenansicht mit Testdaten

## Ergebnis

- Die Karten sind deutlich kompakter und bilden weiterhin eine klar erkennbare, eckige Einheit.
- Die vier Statusaktionen sind beschriftet, semantisch gruppiert und per `aria-pressed` als Zustand erkennbar.
- Aktivität und Maßnahmen sind in zwei ruhige horizontale Informationsreihen verdichtet.
- Karten mit Markierungen zeigen bestehende Markierungen weiterhin; das Hinzufügen bleibt im Aktionsmenü verfügbar.
- Drei Spalten werden erst bei sehr breiten Ansichten verwendet. Bei mittleren Desktopbreiten werden zwei Karten pro Zeile gezeigt; mobil bleibt die etablierte Listenansicht erhalten.
- Auswahl-Checkbox, Kartenaktionen, deutsch/englische Beschriftungen und Produktions-Build wurden geprüft.

## Vergleichshistorie

1. Ausgangslage: hohe Karten, unbeschriftete Statussymbole und 2 × 2 Maßnahmenraster.
2. Umsetzung: kompakte Statusleiste, reduzierte Rahmenhierarchie und einzeilige Maßnahmenübersicht.
3. Endkontrolle: keine offenen P0-, P1- oder P2-Abweichungen; keine Funktionsregression im geprüften Karten- und Auswahlfluss.

final result: passed

---

# Design QA: Desktop-Navigation – Präzisionsindex mit Theme-Verlauf

## Prüfgrundlage

- Gewählte visuelle Richtung: verfeinerte Option 1 „Präzisionsindex“.
- Source visual truth: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-84d33f44-fabe-4685-87f9-264aa3be6c94.png`.
- Farb- und Oberflächenreferenz: der bestehende themeabhängige Verlauf der produktiven Navigation.
- Implementierte Route und Zustand: `http://127.0.0.1:3005/`, Arbeitsbereich „Live“ geöffnet, Serverauswahl geschlossen.
- Finale Browseraufnahme: `.tmp/nav-audit/07-final-square-navigation.png`.
- Gemeinsamer Gesamtvergleich: `.tmp/nav-audit/08-design-qa-final-comparison.png`.
- Fokusvergleich der Navigation: `.tmp/nav-audit/08-design-qa-final-navigation-crop.png`.
- Source und Umsetzung wurden bei 1586 × 992 px und Geräteskalierung 1 verglichen.

## Ergebnis

- Das dauerhafte 64-px-Kommando-Rail und der kompakte 244-px-Präzisionsindex ersetzen die frühere breite Navigationsleiste.
- Die Navigationssuche, die doppelte Serverkarte, die zusätzliche Markenwiederholung und der Versionsblock wurden aus dem Desktop-Kontextpanel entfernt.
- Der Serverwechsel sitzt als dauerhaft erreichbares `S2`-Kommando direkt unter dem Logo. Die Auswahl erhält echte Links, Servernummer, Spielkennung und einen textlich ergänzten Status.
- Der vom Nutzer gewünschte bestehende Theme-Verlauf bleibt auf Rail und Kontextpanel erhalten und reagiert weiterhin auf das gewählte Farbschema.
- Navigationseinträge, aktive Zustände, Server-Schalter, Server-Menüeinträge, Popover und Tooltips verwenden konsequent 0 px Radius. Computed-Style-Prüfung: Kontextnavigation `0px`, Rail `0px`, Server-Schalter `0px`, Server-Menü `0px`.
- Der Bereichstitel, die Abschnittsüberschriften, feinen Trenner und die kompakte Statuszeile folgen der eckigen Frontline-Designlinie.

## Verhalten und Accessibility

- Arbeitsbereiche lassen sich weiterhin über das Rail öffnen und schließen; Ziele bleiben semantische Links.
- Der Serverwechsler öffnet per Tastatur, schließt mit `Escape` und gibt den Fokus an den Auslöser zurück.
- Status wird zusätzlich zu Farbe durch zugängliche Namen und Textlabels vermittelt.
- Bei 1024 px bleibt die Navigation ohne horizontalen Dokument-Overflow (`scrollWidth === viewportWidth`) als Overlay bedienbar.
- Die mobile Navigation wurde im nachfolgenden QA-Schritt auf dieselbe Rail-/Präzisionsindex-Logik umgestellt.

## Technische Verifikation

- Produktionsbuild erfolgreich; nur die bereits bekannte Warnung für große Chunks bleibt bestehen.
- Pfad-, Query- und Hash-Erhalt beim Serverwechsel sowie Sortierung/Deduplizierung der Serveroptionen wurden geprüft.
- Browserinteraktionen für Arbeitsbereich, Servermenü und `Escape` ohne sichtbares Fehler-Overlay geprüft.
- Keine offenen P0-, P1- oder P2-Befunde.

final result: passed

---

# Design QA: Mobile Navigation – Präzisionsindex

## Prüfgrundlage

- Responsive Designziel: die gewählte Desktop-Richtung „Präzisionsindex“, übertragen auf einen vollflächigen mobilen Drawer.
- Ausgangszustand: `.tmp/nav-mobile-audit/02-current-mobile-drawer.png`.
- Finale Browseraufnahme bei 390 × 844 px: `.tmp/nav-mobile-audit/03-new-mobile-navigation.png`.
- Gemeinsamer Vorher-/Nachher-Vergleich: `.tmp/nav-mobile-audit/04-mobile-before-after.png`.
- Zusätzlich geprüft: 320 × 700 px, Arbeitsbereich „Spielbetrieb“ und geöffnete Serverauswahl.

## Ergebnis

- Die alte mobile Akkordeon-Navigation wurde durch dasselbe 64-px-Kommando-Rail und einen kontextabhängigen Präzisionsindex wie am Desktop ersetzt.
- Navigationssuche, breite Serverkarte, CPU-/RAM-/SSD-Block und Versionszeile entfallen aus dem mobilen Hauptfluss.
- Der Serverwechsel sitzt als eckiges `S2`-Kommando direkt unter dem Logo; das Servermenü bleibt selbst bei 320 px innerhalb des Viewports.
- Arbeitsbereiche wechseln ohne Seitenreload. Ein Navigationsziel schließt den Drawer nach dem Routenwechsel automatisch.
- Sprache und Benutzeraktionen bleiben im unteren Rail erreichbar. Alle Navigations-, Server-, Sprach- und Schließen-Schaltflächen folgen der eckigen 0-px-Radius-Designlinie.
- Der vorhandene themeabhängige Verlauf bleibt auf Rail und Kontextpanel erhalten.

## Responsivität und Accessibility

- 390 × 844 px: Rail 64 px, Kontextpanel 326 px, kein horizontaler Dokument-Overflow.
- 320 × 700 px: Rail 64 px, Kontextpanel 256 px, Servermenü 248 px breit und vollständig sichtbar.
- Zugängliche Namen für Arbeitsbereiche, Serverauswahl, Sprache, Benutzeraktionen und Schließen sind vorhanden.
- Touch-Ziele sind mindestens 44 px hoch beziehungsweise breit; aktive Navigation wird zusätzlich durch Linie, Fläche und `aria-current` vermittelt.
- Die Kerninteraktion Moderation → Spieler sowie Spielbetrieb → Karte wechseln wurde im lokalen In-App-Browser geprüft.

## Technische Verifikation

- Vite-Produktionsbuild erfolgreich; nur die bereits bekannte Chunk-Größenwarnung bleibt bestehen.
- `git diff --check` ohne Fehler.
- Keine offenen P0-, P1- oder P2-Befunde.

final result: passed

---

# Design QA: Frontline Command Rail, Option 1

## Prüfgrundlage

- Designziel: `C:\Users\chris\.codex\generated_images\01a0052a-7e8d-7411-8b78-1a415453783b\exec-c4dbe56a-f770-44a3-a78a-302baa69a3dc.png`
- Browser-Umsetzung: `.tmp/navigation-design-qa/command-rail-implementation-1440.png`
- Direkter Vergleich: `.tmp/navigation-design-qa/command-rail-comparison.png`
- Referenzgröße: 1487 × 1058 px
- Browser-Viewport: 1440 × 1024 px
- Geprüfter Zustand: dunkles Frontline-Theme, `/settings/console-admins`, Arbeitsbereich „Moderation“ geöffnet

## Vergleich und Iterationen

1. Der erste Browser-Abgleich zeigte ein doppeltes Logo, ein zu schmales 228-px-Kontextpanel und dadurch unnötige Umbrüche bei langen Bereichsnamen und im Suchfeld.
2. Das Kontextpanel wurde auf 276 px verbreitert, die Marke im Panel auf die Textvariante reduziert und die Arbeitsbereiche auf klare Kurzbezeichnungen umgestellt.
3. Der finale Vergleich zeigt dieselbe Hierarchie wie das Designziel: dauerhaftes Icon-Rail, kontextabhängiges Navigationspanel, sichtbarer Serverkontext, globale Suche und ein klar markierter aktiver Eintrag.

## Fidelity-Prüfung

- **Layout und Abstände:** Rail und Kontextpanel bilden eine eigenständige Navigationszone. Die eckigen Flächen, feinen Trennlinien und kompakten Abstände entsprechen der bestehenden Frontline-Designlinie. Das produktive Konsolen-Admin-Formular bleibt breiter und informationsreicher als das vereinfachte Mockup, ohne die Navigationshierarchie zu beeinträchtigen.
- **Typografie:** Bestehende Frontline-Schriften, Versalien, Gewichtungen und Laufweiten werden weiterverwendet. Arbeitsbereich, Seitentitel und Navigationseinträge besitzen eine klare Abstufung; im finalen 276-px-Panel entstehen keine problematischen Umbrüche.
- **Farben:** Grün-dunkle Flächen, warmer Frontline-Akzent, cyanfarbene Funktionshinweise und semantische Statusfarben werden aus den vorhandenen Tokens übernommen. Der aktive Bereich bleibt deutlich, ohne den Seiteninhalt zu überstrahlen.
- **Formen und Oberflächen:** Keine generischen runden Karten wurden eingeführt. Rail, Panel, Suchfeld, Serverwähler und Navigationseinträge folgen der eckigen Produktoberfläche.
- **Icons:** Ausschließlich vorhandene MUI-Icons aus derselben Stilfamilie; Größen, Ausrichtung, aktive und inaktive Zustände wurden im Browser geprüft.
- **Bilder und Assets:** Das vorhandene Frontline-Logo wird wiederverwendet. Es wurden keine Platzhalter, CSS-Zeichnungen oder nachgebauten SVG-Assets ergänzt.
- **Copy:** Kurze, verständliche Arbeitsbereichsnamen in Deutsch und Englisch. Die Suche besitzt einen verständlichen Leerzustand.

## Verhalten und Responsivität

- Desktop ab 1280 px: Rail und Kontextpanel bleiben stabil sichtbar; das Panel kann reduziert werden, das Rail bleibt erreichbar.
- Tablet 900–1279 px: Das Kontextpanel öffnet als Overlay. `Escape` schließt es und setzt den Fokus auf den auslösenden Arbeitsbereich zurück.
- Mobile unter 900 px: Die bestehende mobile Kopfzeile, der Vollbild-Drawer und die Bottom-Navigation bleiben aktiv; das Desktop-Rail ist ausgeblendet.
- `Ctrl+K` öffnet das Kontextpanel aus dem reduzierten Zustand und fokussiert die globale Navigationssuche.
- Die Suche filtert berechtigte und sichtbare Ziele über alle Arbeitsbereiche. Gesperrte Ziele bleiben erkennbar und semantisch deaktiviert.
- Geprüft bei 1440 × 1024, 1024 × 900 und 390 × 844: kein horizontaler Dokument-Overflow, keine überlappenden Navigationselemente.

## Accessibility

- Semantische Buttons und Links mit zugänglichen Namen, `aria-expanded`, `aria-controls` und sichtbaren Fokuszuständen.
- Tastaturzugriff für Rail, Suche und Navigationsziele; Fokus-Rückgabe nach `Escape` geprüft.
- Praktische Touch-Ziele in der mobilen Navigation bleiben erhalten.
- Status wird nicht allein über Farbe vermittelt; Text und Icons ergänzen die semantischen Zustände.

## Technische Verifikation

- Workspace-Zuordnung und Pfadnormalisierung: 4/4 Node-Tests bestanden.
- Vite-Produktionsbuild erfolgreich; nur die bereits bekannte Chunk-Größenwarnung bleibt bestehen.
- Browserprüfung ohne sichtbares Runtime-Fehler-Overlay.

## Verbleibende Abweichungen

- **P3:** Das Designziel nutzt eine vereinfachte Beispieltabelle. Die Umsetzung behält bewusst das produktive Konsolen-Admin-Formular und seine höhere Informationsdichte bei.
- **P3:** Die Serverbezeichnung wird im kompakten Panel bei sehr langen Namen visuell gekürzt; der Serverwähler selbst bleibt vollständig bedienbar.

Keine offenen P0-, P1- oder P2-Befunde.

final result: passed

---

# Design QA · Phase 1 Navigation und mobile Shell

## Vergleichsziel

- Source Visual Truth: `C:\Users\chris\AppData\Local\Temp\codex-clipboard-efcfcd70-49e7-438a-87b0-e8fc0c201459.png` sowie die anschließend bestätigten Abweichungen in `docs/product-design/rcon-product-concept.md` (Navigationssuche entfernen, Serverwechsel in die globale Serverleiste verlagern, Gradient und eckige Frontline-Formensprache bewahren).
- Implementierung: `.codex/qa/phase1-mobile-game-operations-338x884.png`, `.codex/qa/phase1-mobile-home-390x844.png` und `.codex/qa/phase1-desktop-home-1440x900.png`.
- Gemeinsamer Direktvergleich: `.codex/qa/phase1-mobile-game-operations-comparison.png`.
- Primärer Vergleichszustand: Frontline Gold, dunkler Modus, Standard-Farbsehen, mobile Mehr-Navigation im Workspace „Karten & Spielbetrieb“.

## Normalisierung

- Source: 338 × 884 Pixel.
- Implementierung: 338 × 884 Pixel bei 338 × 884 CSS-Pixeln und Browser-Dichte 1.
- Vergleichsbild: 676 × 914 Pixel; beide 338 × 884-Ansichten wurden ohne Skalierung nebeneinander angeordnet, darüber liegt lediglich eine 30-Pixel-Beschriftungszeile.
- Zusätzliche Responsive-Evidenz: 390 × 844 Mobile und 1440 × 900 Desktop, jeweils ohne Browser-Chrome.

## Full-View-Vergleich

Der direkte Vergleich zeigt dieselbe Frontline-Grundstruktur: 64-Pixel-Kommandoleiste, eckige aktive Zustände, identische Gold-/Grün-Dunkel-Tonalität, dieselbe Iconfamilie, klare Workspace-Hierarchie und dieselbe Reihenfolge der sechs Spielbetriebsziele. Die im Source noch vorhandene Suche und Serverkarte fehlen in der Implementierung absichtlich; der Serverwechsel wurde gemäß freigegebenem Konzept in den globalen Serverstatus verschoben. Dadurch gewinnt das Kontextpanel vertikalen Raum, ohne die gewählte Designrichtung zu verlassen.

## Fokusvergleich

Ein zusätzlicher Ausschnitt war nicht erforderlich: Das Ziel ist selbst eine vollständige 338-Pixel-Navigationsoberfläche, und Beschriftungen, Icons, Abstände, Rahmen und Fokusflächen sind im 1:1-Vergleich lesbar. Der globale Serverstatus wurde separat in 390 × 844 und 1440 × 900 geprüft, einschließlich geöffnetem Menü und wiederhergestelltem Tastaturfokus.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Die Implementierung verwendet im mobilen Kontextkopf nur das Frontline-Signet statt Signet plus ausgeschriebenem Markennamen. Das ist eine bewusste Platzentscheidung: Der Workspace-Titel bleibt bei 338 Pixeln vollständig lesbar und die Marke ist weiterhin eindeutig.

## Pflichtflächen

- Fonts und Typografie: Bahnschrift-/Arial-Narrow-Hierarchie, kondensierte Großbuchstaben, Gewichte, Zeilenhöhe und Buchstabenabstand bleiben konsistent. Keine ungewollte Umbruch- oder Trunkierungsstelle im primären Vergleich.
- Spacing und Layout: Rail-Breite, Kontextpanel, 44-Pixel-Touchziele, eckige Rahmen, Trenner und vertikaler Rhythmus sind konsistent. Bei 390 × 844 und 1440 × 900 trat kein horizontaler Dokumentüberlauf auf.
- Farben und Tokens: Frontline Gold und der bestehende themenfähige Gradient bleiben erhalten. Tactical Blue plus Deuteranopie wurde als Live-Vorschau geprüft und anschließend ohne Speicherung zurückgesetzt.
- Bild- und Assetqualität: Das vorhandene Frontline-Logo und die etablierte MUI-Iconbibliothek werden wiederverwendet; keine Platzhalter, CSS-Zeichnungen oder neu erfundenen Assets.
- Copy und Inhalt: „Betrieb“, „Live-Betrieb“, „Karten & Spielbetrieb“, Servernummer und Statusbezeichnungen sind verständlich und konsistent. Die mobile Zurück-Aktion lautet „Zurück: Spiele“.
- Zustände und Interaktionen: Mobile Startseite, Bottom-Navigation, Mehr-Drawer, Workspace-Wechsel, Servermenü, Escape/Fokuswiederherstellung und Detail-Zurücklink geprüft.
- Browserfehler: Im sauberen Abschlusslauf ohne HMR- oder Viewportwechsel keine Console-Errors; lediglich die bekannte React-Router-v7-Future-Flag-Warnung im Entwicklungsmodus.

## Vergleichshistorie

1. Erster Vergleich: Implementierung versehentlich im Workspace „Live-Betrieb“ und mit sichtbarem Tooltip erfasst; dadurch war der Zustand nicht sourcegleich. Keine Produktänderung erforderlich.
2. Korrektur: Workspace „Karten & Spielbetrieb“ geöffnet, Maus aus dem Rail bewegt und bei identischem 338 × 884-Zustand neu erfasst.
3. Zweiter Vergleich: keine P0/P1/P2-Findings. Suche und Serverkarte sind dokumentierte, beabsichtigte Konzeptänderungen; Gradient, Informationsarchitektur, Icons und Formensprache stimmen mit der gewählten Richtung überein.

## Implementation Checklist

- [x] Source und Implementierung bei identischer Größe und identischem Workspace verglichen.
- [x] Mobile Startseite bleibt auf `/` und zeigt die Betriebsübersicht.
- [x] Serverwechsel ist global erreichbar und nicht im Mehr-Drawer dupliziert.
- [x] Bottom-Navigation und mobile Detail-Zurücknavigation geprüft.
- [x] Desktop, Mobile, Tastatur, Theme und Farbsehmodus geprüft.
- [x] Keine blockierenden visuellen oder funktionalen Abweichungen.

final result: passed

---

# Design QA · Phase 2.4 Spielerakten und Sperrlistenverwaltung

## Prüfgrundlage

- Source Visual Truth: bestehende, funktionsfähige Ansichten in `.codex/phase24-baseline/players-mobile-390x844.png`, `.codex/phase24-baseline/player-profile-mobile-390x844.png`, `.codex/phase24-baseline/blacklists-manage-desktop-1440x900.png` und `.codex/phase24-baseline/blacklists-manage-mobile-390x844.png`; Zielhierarchie zusätzlich aus dem freigegebenen Product-Design-Konzept für `/records/players`, `/records/players/:playerId` und `/records/blacklists/manage`.
- Implementierung: `.codex/phase24-baseline/players-after-mobile-qa2-390x844.png`, `.codex/phase24-baseline/player-profile-after-mobile-qa2-390x844.png`, `.codex/phase24-baseline/blacklists-manage-after-desktop-1440x900.png` und `.codex/phase24-baseline/blacklists-manage-after-mobile-390x844.png`.
- Theme-Evidenz: `.codex/phase24-baseline/blacklists-manage-theme-light-deuteranopia-1440x900.png`.
- Viewports und Normalisierung: Mobile jeweils 390 × 844 CSS-Pixel bei Browser-Dichte 1 und 390 × 844 Bildpixeln; Desktop jeweils 1440 × 900 CSS-Pixel bei Browser-Dichte 1 und 1440 × 900 Bildpixeln. Screenshots enthalten nur den App-Viewport ohne Browser-Chrome.
- Zustände: Frontline Gold, dunkler Modus, Standard-Farbsehen; Spielerakten ohne Auswahl, Spielerprofil im Tab „Profil“, Sperrlistenverwaltung mit ausgewählter Liste. Der Theme-Test verwendet hellen Modus plus Deuteranopie und wurde anschließend ohne Speicherung verworfen.

## Full-View-Vergleich

Die Vorher- und Nachher-Aufnahmen wurden je Route im selben Vergleichseingang geöffnet und bei identischem Viewport beurteilt. Die Spielerakten behalten die kompakte mobile Aktenliste, ersetzen aber die dauerhaft sichtbare Symbolleiste und den hohen Filterblock durch einen klaren Suche-/Filter-Einstieg. Das Profil bringt die aufgabenbezogenen Tabs und den editierbaren Akteninhalt vor die lange Zusammenfassung. Die Sperrlistenverwaltung wechselt von einer weit verteilten Pseudotabelle zu einer eckigen Master-Detail-Arbeitsfläche mit Reichweite, Synchronisationswirkung und klaren Listenaktionen; Mobile wird keine Spalte mehr abgeschnitten.

## Fokusvergleich

Ein zusätzlicher Ausschnitt war nicht erforderlich. Suche, Filterauslöser, Auswahlleiste, Profilstatus, Listenkarte, Detailpanel und Formularaktionen sind in den 390-Pixel- und 1440-Pixel-Aufnahmen vollständig lesbar. Die Formulare wurden zusätzlich interaktiv im Browser geprüft, einschließlich bestehender Werte, Serverauswahl und Vollbilddarstellung auf Mobile.

## Findings

- Keine verbleibenden P0-, P1- oder P2-Abweichungen.
- [P3] Beim Öffnen der globalen Benutzeraktionen und unmittelbaren Wechsel in den Darstellungsdialog protokolliert der bestehende Shell-Tooltip einmalig eine MUI-`anchorEl`-Warnung. Sie betrifft nicht die Spieler- oder Sperrlistenabläufe, erzeugt kein sichtbares Fehlverhalten und wird in einem globalen Shell-Paket separat bereinigt.

## Pflichtflächen

- Fonts und Typografie: Bestehende Frontline-Schriftfamilie, kondensierte Versalien, Gewichte und Zeilenhöhen bleiben erhalten. Überschriften, Metadaten, Risikostatus und Formlabels besitzen eine klarere Hierarchie ohne problematische Umbrüche.
- Spacing und Layout: Mobile Filter reduzieren den ersten Viewport, Auswahlaktionen erscheinen nur bei tatsächlicher Auswahl, und das Spielerprofil priorisiert den Arbeitsbereich. Die Sperrlistenverwaltung verwendet ein eckiges, rhythmisches Master-Detail-Raster; bei 390 × 844 und 1440 × 900 gilt `scrollWidth === clientWidth`.
- Farben und Tokens: Flächen, Rahmen, Auswahl, Erfolg, Gefahr und Information verwenden ausschließlich die vorhandenen Theme-Tokens. Heller Modus plus Deuteranopie wurde live geprüft; Zustand bleibt zusätzlich über Text, Symbol und Umrandung erkennbar.
- Bild- und Assetqualität: Vorhandene Avatare, Frontline-Logo und MUI-Icons werden unverändert wiederverwendet. Es wurden keine Platzhalter, CSS-Zeichnungen, handgebauten SVGs oder neuen Bildassets eingeführt.
- Copy und Inhalt: Filter, Aktenstatus, Reichweite, Serveranzahl und Synchronisationswirkung werden auf Deutsch und Englisch verständlich benannt. Unbekannte Synchronisationswerte werden transparent angezeigt und beim Bearbeiten bewahrt.
- Icons und Zustände: Statussymbole besitzen sichtbare Textlabels; Auswahl- und Listenaktionen haben zugängliche Namen. Aktiv, ausgewählt, deaktiviert und destruktiv sind nicht allein farbcodiert.
- Responsivität und Accessibility: 390 × 844 und 1440 × 900 ohne horizontalen Dokumentüberlauf; mobiler Filter als Vollhöhen-Drawer, Sperrlistenformular als Vollbilddialog, Tabs scrollbar, Listenkarte per Enter auswählbar und 44-Pixel-Aktionen geprüft.

## Interaktionen und Datenverträge

- Mobile Filter geöffnet, Spieler-ID eingetragen und mit „Ergebnisse anzeigen“ abgesendet; die bestehende Query `player_id=76561198000000001` wurde korrekt in der URL beibehalten.
- Spieler ausgewählt; die zentrale Aktionsregion erschien nur dann, alle sieben Aktionen besaßen zugängliche Namen, und „Auswahl aufheben“ entfernte die Region wieder.
- Spielerprofil-Tab „Sitzungen“ aktiviert; Status und Inhalt wechselten ohne Routen- oder Datenvertragänderung.
- Zweite Sperrliste per Enter ausgewählt; Detailpanel aktualisiert. Bearbeitungsdialog bewahrte Name, Synchronisation und Serverauswahl. Mobiles Erstellformular belegte exakt den 390 × 844-Viewport.
- Loader, Actions, API-Kommandos, Payloads und gespeicherte Konfigurationen blieben unverändert.

## Vergleichshistorie

1. Ausgangsvergleich: [P2] Mobile Spielerfilter und eine ständig sichtbare Symbolleiste verbrauchten unnötig Höhe; [P2] die lange Aktenzusammenfassung verdrängte die eigentliche Profilaufgabe; [P1] Sperrlistenverwaltung war Mobile als abgeschnittene Pseudotabelle nicht zuverlässig lesbar und Desktop zu weit verteilt.
2. Umsetzung: Mobile Filter-Drawer, bedingte Auswahlaktionsleiste, aufgabenorientierte Profilreihenfolge sowie eckige Master-Detail-Verwaltung mit responsivem Formular ergänzt. Datenverträge blieben unverändert.
3. Erste Nachher-Aufnahme: Inhalt war korrekt, aber Statuskopf und Avatare wurden vor vollständigem Laden erfasst. Die Aufnahme war nicht zustandsgleich und wurde nicht zur Freigabe verwendet.
4. Finale Vergleichsaufnahme nach vollständigem Laden bei identischen Viewports: keine offenen P0-, P1- oder P2-Findings.

## Implementation Checklist

- [x] Ausgangszustände und Implementierung je Route im selben Vergleichseingang geprüft.
- [x] Desktop und 390 × 844 ohne horizontalen Dokumentüberlauf geprüft.
- [x] Filter, Auswahlaktionen, Profil-Tabs, Listenwahl und Dialoge funktional geprüft.
- [x] Tastatur, Theme, Deuteranopie und semantische Beschriftungen geprüft.
- [x] Bestehende API-, Query-, Payload- und Konfigurationsverträge beibehalten.
- [x] Keine offenen P0-, P1- oder P2-Findings.

final result: passed
