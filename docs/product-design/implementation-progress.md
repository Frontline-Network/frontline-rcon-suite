# Frontline RCON Product Design – Umsetzungsprotokoll

Dieses Protokoll begleitet die paketweise Umsetzung des Product-Design-Konzepts. Es dokumentiert pro Paket Ausgangslage, Eingriffsbereich, Datenrisiko, Prüfung und Rückrollbarkeit. Ein Eintrag bedeutet nicht automatisch Release oder Rollout.

## Phase 0 · Paket 0.1 – Design-Grundlage

### Inventar und Ausgangslage

- Betroffene Routen: alle Routen, da die Änderung über `AppTheme` und die zentralen MUI-Komponenten wirkt.
- Betroffene Komponenten: Button-Basis, Outlined Inputs, Feldlabels und Hilfetexte, Chips, Alerts, Dialoge, Akkordeons, Menüs, Selects und Tabs.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Das Paket enthält ausschließlich Darstellungstokens und Komponenten-Overrides.
- Ausgangslage: uneinheitliche Radien von 8 bis 999 Pixeln, kein verbindlicher globaler Tastatur-Fokusring und Theme-Aussehen konnte zusätzliche Frontline-Metadaten überschreiben.

### Umsetzung

- Verbindliche Frontline-Geometrie eingeführt: Struktur 0 px, Controls 2 px, Overlays 4 px; vollständig runde Formen bleiben ausschließlich semantisch runden Elementen vorbehalten.
- Themefarbener, gut sichtbarer 2-px-Fokusring für interaktive MUI-Basiskomponenten ergänzt.
- Fokuszustände für Eingaben, Selects, Menüs und Tabs vereinheitlicht.
- Chips, Alerts, Dialoge und Akkordeons an die neue Geometrie angebunden.
- Frontline-Geometrie bleibt beim Wechsel von Preset, Hell/Dunkel und Farbsehmodus erhalten; ältere Farbschemata erhalten einen sicheren Fallback.
- Ein ausführbarer Design-Foundation-Contract schützt die zentralen Tokens vor Regressionen.

### Validierung

- Production Build: bestanden.
- Design-Foundation-Contract: bestanden.
- Appearance-E2E: drei von drei Tests bestanden, einschließlich Mobile-Dialog, benutzerdefinierter Akzentfarbe und Deuteranopie.
- Manuelle Browserprüfung: Desktop und 390 × 844 Mobile bestanden; genau eine H1 auf der geprüften Einstellungsseite; Fokusring, Preset-Vorschau und Farbsehmodus sichtbar korrekt.
- Bestehende Navigationstests: Desktop bestanden. Vier Mobile-Assertions referenzieren die inzwischen entfernte Navigationssuche beziehungsweise die alte Drawer-Struktur und werden im Navigationspaket aktualisiert; sie sind keine Regression dieses Theme-Pakets.
- Lint: im aktuellen Checkout nicht ausführbar, weil das vorhandene `lint`-Skript auf ein nicht installiertes ESLint-Binary verweist.

### Rückrollbarkeit

Das Paket ist datenbank- und konfigurationsneutral. Es kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Ein Backup oder eine Datenmigration ist nicht erforderlich.

## Phase 0 · Paket 0.2 – Seitensemantik und Zustände

### Inventar und Ausgangslage

- Betroffene Routen: Übersicht, automatische Einstellungen, Spielerprofil und dessen Unterseiten, Systemdiagnose mit fünf Konfigurationsbereichen, Sektoren, Apps, Discord Report Bot, Autobalancer und Meldungen.
- Betroffene Komponenten: `PageHeader`, neue gemeinsame `PageState`, Tabellen-Leerzustand, Konfigurationslayouts, Sektoren-Bestätigungsdialog und ausgewählte Form-Controls.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Die vorhandenen Loader, Actions, API-Kommandos, Formularwerte und Speichervorgänge wurden nicht geändert.
- Ausgangslage: einzelne Seiten ohne semantische Hauptüberschrift, versteckte doppelte H1 in eingebetteten Konfigurationslayouts, uneinheitliche Lade-/Fehler-/Leerzustände und einzelne Selects ohne stabile Label-Verknüpfung.

### Umsetzung

- `PageHeader` als semantischer, beschrifteter Seitenkopf mit stabiler Titel-ID vereinheitlicht.
- Wiederverwendbare Zustände für Laden, Leer, Fehler, Offline, Konflikt, Berechtigung und Erfolg ergänzt; Ladezustände verwenden jetzt Skeletons statt eines isolierten Spinners.
- Übersicht, automatische Einstellungen, Spielerprofile, Systemdiagnose, Apps, Discord Report Bot, Autobalancer, Sektoren und Meldungen auf genau eine sichtbare H1 pro gerenderter Ansicht umgestellt.
- Eingebettete Konfigurationsköpfe werden nicht mehr nur visuell versteckt, sondern semantisch gar nicht gerendert; dadurch bleibt auch für Hilfstechnologien genau ein Seitentitel bestehen.
- Beschriftungen für Bereichsauswahl und Votemap-Auswahl stabil mit ihren Controls verbunden.
- Sektorensteuerung mit konsistentem Seitenkopf sowie eindeutig beschriftetem Bestätigungsdialog und handlungsbezogener Primäraktion versehen.
- Ein ausführbarer Page-Semantics-Contract schützt H1-, Label-, Dialog- und State-Verknüpfungen vor Regressionen.

### Validierung

- Production Build: bestanden.
- Design-Foundation-Contract und Page-Semantics-Contract: bestanden.
- Manuelle Browserprüfung: 15 priorisierte Desktop-Routen und vier 390 × 844-Mobile-Routen geprüft; kein horizontaler Seitenüberlauf, genau eine sichtbare H1 je vollständig geladener Ansicht.
- Formularprüfung: Votemap-Einstellungen, Sektoren und Log-Line mit benannten Eingaben, Selects und Checkboxen geprüft; interne, für Hilfstechnologien verborgene MUI-Inputs bleiben ohne eigenen Namen, der jeweils bedienbare Combobox-Trigger ist korrekt beschriftet.
- Dialogprüfung: Sektorenänderung besitzt einen eindeutigen Titel, eine Beschreibung, Abbrechen und die konkrete Primäraktion „Sektoren ändern“.
- Tastaturprüfung: sichtbarer 2-px-Fokusring auf der Meldungsnavigation.
- Themeprüfung: Tactical Blue mit Deuteranopie-Vorschau geprüft und anschließend ohne Speichern verworfen; Symbole, Beschriftungen und Umrandungen blieben als redundante Zustandsträger erhalten.
- Lint: weiterhin nicht ausführbar, weil im aktuellen Checkout kein ESLint-Binary installiert ist.

### Rückrollbarkeit

Das Paket verändert ausschließlich Frontend-Semantik und Darstellung. Es benötigt weder Datenmigration noch Backup und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder veröffentlicht noch ausgerollt.

## Phase 0 · Paket 0.3 – Vollständiger Konsistenz-Audit und Aktionsfeedback

### Inventar und Ausgangslage

- Betroffene Routen: alle 75 im Produktkonzept dokumentierten Seiten; zusätzlich wurden 42 formular-, filter- oder tabellenlastige Risikorouten einzeln auf zugängliche Bezeichnungen geprüft.
- Betroffene Komponenten: Spielerakten-Karten, Kartenrotation, Live-Einsatz, Audit- und Spielprotokollfilter, Sperrlistenfilter, Votemap-Kartenpool, Vorlageneditor, Live-Spiel- und Live-Sitzungsfilter, Kampagnen-Aktionsleiste sowie die gemeinsamen Zustandskomponenten.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Das Paket ändert weder Loader/Actions noch API-Payloads, Datenbankschemata oder persistierte Formularwerte.
- Ausgangslage: Spielerakten erzeugten pro Karte eine zusätzliche H1; Rotation und Live-Einsatz hatten keine Seiten-H1. Einzelne sichtbare Selects und Vorlagenfelder besaßen nur Platzhalter oder eine nicht am bedienbaren MUI-Trigger ankommende Beschriftung. Erfolgs- und Fehlerfeedback folgte keinem gemeinsamen, exklusiven Ergebnismodell.

### Umsetzung

- Alle 75 dokumentierten Seiten auf genau eine sichtbare H1 vereinheitlicht. Spieler-Karten verwenden nun H2, während Spielerprofile weiterhin eine H1 behalten; Rotation und Live-Einsatz besitzen einen eigenen kompakten Seitenkopf.
- Sichtbare Labels für Auditparameter, Spielersuche, Sperrlistenwahl, Kartenspielmodus und Umgebung sowie Titel/Inhalt/Zeit/Nachricht im Vorlageneditor ergänzt.
- MUI-Selects in Spielhistorie, Live-Sitzungen und Live-Spiel über `inputProps` beziehungsweise stabile `InputLabel`-/`labelId`-Paare korrekt mit ihrer zugänglichen Bezeichnung verbunden.
- Gemeinsames `ActionResult` mit genau einem exklusiven Zustand eingeführt: laufend, erfolgreich, teilweise erfolgreich, Fehler, Konflikt, fehlende Berechtigung oder destruktive Auswirkung. Ziel, Zeitpunkt, System, Ursache, beibehaltene Konfiguration, nächster Schritt, Wiederholen und Audit-Link können einheitlich ausgegeben werden.
- `PageState` um laufende, teilweise erfolgreiche und destruktive Zustände ergänzt. Kampagnenspeicherung verwendet das gemeinsame Aktionsfeedback und erzeugt keine parallele Erfolgs- und Fehlermeldung mehr.
- Ausführbare Verträge für Aktionsfeedback und die neu abgesicherten H1-/Label-Verknüpfungen ergänzt.

### Validierung

- Production Build: bestanden; lediglich die bereits bekannte Vite-Warnung zu vorhandenen Chunks über 500 kB bleibt bestehen.
- Verträge: Design Foundation, Seitensemantik, Aktionsfeedback, Operator-Copy und Konfigurationskompatibilität bestanden.
- Vollständiger H1-Audit: alle 75 dokumentierten Routen direkt geladen; nach den Korrekturen genau eine sichtbare H1 je Seite.
- Strenger Label-Audit: 42 Risikorouten mit ausschließlich sichtbaren und bedienbaren Inputs, Textareas, Selects und Combobox-Triggern geprüft; kein unbenanntes Control verbleibt.
- Responsive Prüfung: Live-Einsatz, Spielerakten, Rotation, Audit-Protokolle und Kampagnen bei 390 × 844 ohne horizontalen Dokumentüberlauf und mit genau einer H1 geprüft.
- Aktionsprüfung: Kampagnenänderung lokal gespeichert; genau ein höflich angekündigter Erfolgsstatus, kein gleichzeitiger Alert. Anschließend wurde der Testwert wieder auf den Ausgangszustand zurückgesetzt.
- Theme- und Farbsehprüfung: Tactical Blue mit Deuteranopie-Vorschau geprüft und ohne Speichern verworfen; Status blieb zusätzlich durch Text, Symbol und Umrandung erkennbar.
- Tastaturprüfung: fokussierbare Navigation mit sichtbarem Fokusindikator geprüft. Die neuen Aktionsbuttons besitzen Textbeschriftungen und nutzen die gemeinsame Button-Basis.

### Rückrollbarkeit

Das Paket ist vollständig frontend- und konfigurationsneutral. Es kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder zu GitHub übertragen noch veröffentlicht, ausgerollt oder auf einer Produktionsinstanz aktiviert.

## Phase 1 · Globale Navigation, Serverwechsel und mobile Shell

### Inventar und Ausgangslage

- Betroffene Routen: alle 75 Seiten über die globale Shell; funktional besonders `/`, `/mobile/operations`, `/views/live` sowie mobile Detailrouten wie `/stats/games/:gameId`.
- Betroffene Komponenten: Desktop-Kommandoleiste, mobiles Mehr-Panel, globaler Serverstatus, Mobile Bottom Navigation, Breadcrumb-/Zurücknavigation und Dashboard-Startentscheidung.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Loader, Actions, API-Kommandos, Serverlistenformat, Ziel-URL-Aufbau und persistierte Benutzereinstellungen bleiben erhalten.
- Ausgangslage: Mobile `/` leitete still auf die Live-Ansicht um; „Betrieb“ war nur eine Nebenroute. Der Serverwechsel saß separat in Desktop- und Mobile-Rail, während der globale Serverstatus nicht interaktiv war. Mobile Detailseiten boten im festen Kopf keinen eindeutigen Rückweg und der Statuskopf belegte durch ein 2 × 2-Raster unnötig viel Höhe.

### Umsetzung

- Mobile `/` rendert nun die echte Betriebsübersicht; `/mobile/operations` bleibt als kompatible Bestandsroute erhalten.
- Bottom Navigation trennt „Einsatz“ (`/views/live`) eindeutig von „Betrieb“ (`/`) und markiert beide Ziele korrekt.
- Der vorhandene Serverwechsel wurde in die globale Serverstatusleiste integriert. Er bewahrt Route, Query und Hash, zeigt Spielkontext und Verbindungszustand, öffnet dasselbe zugängliche Menü und stellt den Fokus nach Escape wieder her.
- Doppelte Serverwechsel-Controls wurden aus Desktop-Rail und mobilem Mehr-Panel entfernt.
- Der mobile Statuskopf wurde auf eine kompakte einzeilige Server-/Spieler-/Karten-/Restzeitstruktur reduziert; seine gemessene Höhe beträgt 109 Pixel einschließlich Rahmen und stimmt mit dem 108-Pixel-Layout-Offset überein.
- Mobile Detailseiten erhalten einen 44 × 44 Pixel großen, beschrifteten Rückweg zur passenden übergeordneten Route.
- Der auf Mobile nur per CSS versteckte Desktop-Header wird nicht mehr zusätzlich in den DOM gerendert; dadurch bleiben IDs und Testselektoren eindeutig.
- Ein ausführbarer Navigation-Shell-Contract sowie reine Node-Tests schützen mobile Zielzuordnung und Serverwechsel-URL-Verhalten.

### Validierung

- Production Build: bestanden; nur die bekannte Chunk-Größenwarnung bleibt bestehen.
- Verträge: Navigation Shell, Design Foundation, Seitensemantik und Konfigurationskompatibilität bestanden.
- Node-Tests: Workspace-Zuordnung, mobile Zielzuordnung, Serverreihenfolge, Deduplizierung sowie Erhalt von Route/Query/Hash bestanden.
- Mobile Browserprüfung: 390 × 844 Startseite bleibt auf `/`, zeigt genau eine H1 „Betrieb“, besitzt keinen horizontalen Überlauf und markiert „Betrieb“ in der Bottom Navigation.
- Mobile Mehr-Panel: keine Navigationssuche, kein doppelter Serverwechsel, alle Workspaces erreichbar, Spielbetrieb mit sechs Zielen und eckigen 44-Pixel-Touchzielen geprüft.
- Mobile Detailprüfung: `/stats/games/fln-demo-1` zeigt den sichtbaren Rückweg zu `/stats/games`; geladene Seite besitzt eine H1.
- Desktop Browserprüfung: 1440 × 900 mit genau einer H1, globalem Serverwechsel, unveränderter Rail-/Panelstruktur und ohne horizontalen Überlauf.
- Tastaturprüfung: Servermenü geöffnet, mit Escape geschlossen und Fokus auf den globalen Trigger zurückgeführt.
- Theme- und Farbsehprüfung: Tactical Blue plus Deuteranopie live geprüft und ohne Speichern verworfen; Navigation und Serverstatus bewegten sich korrekt mit den Tokens.
- Design QA: Source und Implementierung im gleichen 338 × 884-Spielbetriebszustand direkt nebeneinander verglichen; keine P0/P1/P2-Findings, Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: im sauberen Abschlusslauf ohne HMR- oder Viewportwechsel keine Fehler; nur die bekannte React-Router-v7-Future-Flag-Warnung im Entwicklungsmodus.

### Rückrollbarkeit

Das Paket ist frontend-, datenbank- und konfigurationsneutral. Es erfordert weder Backup noch Migration und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.

## Phase 2 · P0-Inventur der betrieblichen Kernpfade

### Routen, Komponenten und Datenverträge

- Meldungen: `/incidents` verwendet React Query mit `GET_MOBILE_INCIDENTS` im 15-Sekunden-Takt und `UPDATE_MOBILE_INCIDENT` mit unveränderter Incident-ID, Operation und Revision.
- Live-Betrieb: `/views/live` verwendet die bestehenden Live-Spieler-, Spielstatus-, Serveraktions- und Protokollkomponenten. Tabellen-, Aktions- und Logverträge bleiben getrennt und werden in späteren Phase-2-Paketen konsolidiert.
- Spieler und Moderation: `/records/players` sowie die Spieler-Detailrouten verwenden weiterhin `GET_PLAYERS_RECORDS`, `GET_BANS`, URL-basierte Filter und die zentrale `ActionBar`.
- Sperrlisten: `/records/blacklists` und `/records/blacklists/manage` behalten ihre bestehenden Loader, Suchparameter, Zuweisungsaktionen und Synchronisationskomponenten.
- Dienste: `/settings/services` verwendet den Router-Loader für Dienste, Dead Letters, Diagnosevorschau und Operational Health sowie die bestehende POST-Action für `TOGGLE_SERVICE`.
- Spiel- und Audit-Protokolle: `/records/game-logs` und `/records/audit-logs` verwenden weiterhin URL-basierte Filter, unveränderte Loader-Kommandos und bestehende Exportfunktionen.
- Ausgangslage: alle priorisierten Routen wurden im Fake-Modus bei 1440 × 900 und 390 × 844 visuell erfasst. Jede vollständig geladene Route besitzt genau eine H1; der sichtbarste verpflichtende Mobile-Überlauf bestand in der abgeschnittenen Statusnavigation der Meldungsseite.

## Phase 2 · Paket 2.1 – Meldungsleitstelle

### Inventar und Risiko

- Betroffene Route: `/incidents`.
- Betroffene Komponenten: Meldungskarte, Statusfilter, Lagekennzahlen, Desktop-Detailpanel und mobiler Bearbeitungsdialog; deutsche und englische Incident-Copy.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Abrufintervall, Query-Key, Limit, Incident-ID, Operation, Revision sowie Query-Cache-Aktualisierung bleiben kompatibel. Es gibt keine Datenmigration und keine neue Persistenz.
- Ausgangslage: Desktop zeigte nur eine breite Liste und öffnete Kontext in einem Dialog. Mobile schnitt die fünfteilige Statusnavigation rechts ab, sodass nicht alle Filter ohne horizontale Navigation sichtbar waren.

### Umsetzung

- Desktop als echte Leitstelle aufgebaut: offene Vorgänge, nicht zugewiesene Meldungen, betroffene Server und älteste offene Meldung bilden eine kompakte Lageübersicht.
- Einsatzwarteschlange und dauerhaft sichtbarer Vorgangskontext liegen nebeneinander. Der erste sichtbare Vorgang ist auf Desktop direkt prüfbar; Auswahl und Status bleiben zusätzlich durch Text, Symbol, Rahmen und Akzent erkennbar.
- Der Vorgangskontext zeigt Quelle, Eingang, letzte Änderung, Melder, Zuständigkeit, Originalmeldung und einen klaren nächsten Schritt, ohne neue Backend-Annahmen einzuführen.
- Mobile ersetzt die abgeschnittene Tabreihe durch ein vollständig beschriftetes Status-Select. Die Bearbeitung öffnet als eckiger Vollbilddialog mit vertikal priorisiertem Kontext und 44-Pixel-Aktionen.
- Live-Aktualisierung und manuelles Aktualisieren sind sichtbar; Laden, Fehler, Leerzustand, Ablehnungsbestätigung und Mutationsfehler bleiben erhalten.
- Statusaktionen „Übernehmen“, „Ablehnen“ und „Abschließen“ verwenden exakt die bestehenden Operationen und Revisionswerte.

### Validierung

- Vite-Production-Build im Fake-Modus: bestanden; nur die bekannte Warnung zu bestehenden Chunks über 500 kB bleibt.
- Browserprüfung: Desktop 1440 × 900, Mobile 390 × 844 und mobiler Detailzustand geprüft. Mobile besitzt `scrollWidth === clientWidth === 390`.
- Funktionsprüfung: „Übernehmen“ erfolgreich gegen Mirage ausgeführt; aktualisierter Status und Folgeaktionen erschienen ohne Fehler.
- Tastaturprüfung: Escape schließt den mobilen Bearbeitungsdialog.
- Theme- und Farbsehprüfung: helles Theme und Deuteranopie über die echte Darstellungsoberfläche angewendet; anschließend Frontline-Standard wiederhergestellt.
- Design QA: erster Desktopvergleich fand einen zweizeiligen Tab als P2; nach einzeiliger Verdichtung erneuter identischer Vergleich ohne offene P0/P1/P2-Findings. Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: null Errors; ausschließlich die bekannte React-Router-v7-Future-Flag-Warnung.
- Lint: weiterhin nicht ausführbar, weil im Checkout kein ESLint-Paket beziehungsweise Binary installiert ist.

### Rückrollbarkeit

Das Paket ist frontend-, datenbank- und konfigurationsneutral. Es erfordert weder Backup noch Migration und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.
