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

## Phase 2 · Paket 2.2 – Mobile Live-Einsatzsteuerung

### Inventar und Risiko

- Betroffene Route: `/views/live`.
- Betroffene Komponenten: Handlungsbedarf-/Gefechtsstatus, Spieler-Schnellfilter und mobile Spielerzeilen.
- Datenverträge und gespeicherte Konfigurationen: unverändert. `teamsLiveQueryOptions`, `GET_LIVE_LOGS`, globaler Spielstatus, Tabellenfilter, Zeilenauswahl, Serveraktionen und zentrale Spieleraktionen werden unverändert weiterverwendet. Das neue Mobile-Select setzt dieselben TanStack-Tabellenfilter wie die bisherigen Toggle-Buttons.
- Ausgangslage: Desktop besaß bereits eine belastbare Split View. Mobile versteckte Lagekarten und Filter in zwei horizontalen Scrollbereichen; wichtige Commander-Warnungen, Kontextwerte und einzelne Filter waren ohne seitliches Suchen nicht vollständig sichtbar. Die mobile Spielerzeile färbte Namen zusätzlich nach Team und wich bei der Schriftstärke vom bereits vereinheitlichten Desktop-Tisch ab.

### Umsetzung

- Commander- und Truppführerwarnungen erhalten auf Mobile die volle Breite und stehen in Dringlichkeitsreihenfolge untereinander.
- VIP-, Watchlist-, Spielstand- und Kartenkontext folgen als kompaktes Zweispaltenraster. Der Spielstand verwendet Mobile eine kurze Beschriftung; längere Kontextwerte dürfen zwei Zeilen belegen.
- Der horizontale Spieler-Schnellfilter wurde auf Mobile durch ein sichtbar beschriftetes, tastaturbedienbares Select mit denselben fünf Filterwerten und aktuellen Zählern ersetzt. Desktop behält die schnelle Buttonleiste.
- Mobile Spielernamen und K/D-Werte folgen mit neutraler Textfarbe und Gewicht 300 wieder der vereinbarten Tabellen-Typografie. Fraktion, Trupp und Rolle bleiben direkt in der zweiten Zeile sichtbar.
- Einsatz/Protokoll-Tabs, Suchfeld, erweiterte Auswahlfilter, Tabellenkonfiguration, Player-Detail-Sheet und alle Server-/Spieleraktionen bleiben unverändert erreichbar.

### Validierung

- Vite-Production-Build mit produktionsäquivalentem API-Basispfad `/api/`: bestanden; nur die bekannte Chunk-Größenwarnung bleibt bestehen.
- Verträge: Design Foundation, Seitensemantik, Action Feedback, Polling Budget, Konfigurationskompatibilität, Admin-Aktionen, Operator-Copy und Navigation Shell bestanden.
- Browserprüfung: Desktop 1440 × 900 visuell unverändert; Mobile 390 × 844 und 320 × 720 ohne sichtbaren horizontalen Dokumentüberlauf.
- Funktionsprüfung: Mobile Schnellfilter per Tastatur geöffnet und „Achsenmächte · 3“ gewählt; die Liste zeigte danach exakt drei Spieler. Einsatz/Protokoll-Wechsel funktionierte in beide Richtungen.
- Detailprüfung: mobiles Spieler-Detail-Sheet geöffnet und mit Escape geschlossen.
- Theme- und Farbsehprüfung: helles Theme mit Deuteranopie über die echte Darstellungsoberfläche geprüft und ohne Speicherung verworfen.
- Design QA: zwei Iterationen nach dem Ausgangsvergleich; gekürzte Kontextbeschriftungen und Zeilenumbruch wurden im zweiten Lauf korrigiert. Keine offenen P0/P1/P2-Findings, Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: null Errors.
- Lint: weiterhin nicht ausführbar, weil im Checkout kein ESLint-Paket beziehungsweise Binary installiert ist.

### Rückrollbarkeit

Das Paket ist frontend-, datenbank- und konfigurationsneutral. Es erfordert weder Backup noch Migration und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.

## Phase 2 · Paket 2.3 – Teamführung und Autobalancer

### Inventar und Risiko

- Betroffene Routen: `/views/team` und `/views/autobalancer`.
- Betroffene Komponenten: Gefechtsstatus, Team- und Truppfilter, Kapazitätsindikatoren, Autobalancer-Navigation, Handlungsempfehlung, operative Zeitleiste und Navigationszuordnung.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Team-, Trupp-, Autobalancer-Status-, Kandidaten-, Pilot- und Einstellungsverträge werden ausschließlich gelesen beziehungsweise über die bereits vorhandenen Aktionen bedient. Es gibt keine Migration und keine neue Persistenz.
- Ausgangslage: Mobile verbrauchte der Teamstatus den größten Teil des ersten Viewports. Beim Autobalancer war die horizontale Bereichsnavigation abgeschnitten; der betriebliche Ablauf war als zusammenhängende Entscheidungskette schwer erkennbar.

### Umsetzung

- Die Teamansicht verdichtet Mobile Mannschaften, Spielstand und Problemlage, ohne die informationsreiche Desktopansicht zu verändern. Alle Filter und der Autobalancer-Einstieg liegen nun im ersten mobilen Viewport.
- Der Statusfilter unterscheidet zusätzlich überbelegte Trupps. Kapazität wird anhand des vorhandenen Trupptyps ermittelt; Problemindikatoren unterscheiden fehlende Führung und Überbelegung über Text, Symbol und zugängliche Beschriftung.
- Der Autobalancer ist in der Informationsarchitektur dem Live-Betrieb zugeordnet. Mobile verwendet ein beschriftetes Bereichs-Select, Desktop weiterhin die schnelle Tabnavigation.
- Die neue operative Zeitleiste strukturiert den bestehenden Status in Live-Zustand, Balance-Delta, geplante Verschiebung, letzten Eingriff und Cooldown. Sie erfindet keine ausgeführten Aktionen und kennzeichnet fehlende Backenddaten transparent.
- Englische Standardbezeichnungen für Alliierte und Achsenmächte werden im deutschen Moderator-Dashboard normalisiert; individuelle Backendbezeichnungen bleiben erhalten.

### Validierung

- Vite-Production-Build mit API-Basispfad `/api/`: bestanden; nur die bekannte Chunk-Größenwarnung bleibt.
- Verträge: Design Foundation, Seitensemantik, Action Feedback, Polling Budget, Konfigurationskompatibilität, Admin-Aktionen, Operator-Copy, Navigation Shell und initiales Bundle-Budget bestanden.
- Browserprüfung: Teams und Autobalancer bei 1440 × 900 sowie 390 × 844 geprüft; beide mobilen Routen besitzen keinen horizontalen Dokumentüberlauf.
- Tastaturprüfung: Autobalancer-Bereichsselect auf „Vorschläge prüfen“ und Team-Statusselect auf „Überbelegt“ umgestellt.
- Theme- und Farbsehprüfung: helles Theme plus Deuteranopie geprüft und ohne Speicherung verworfen.
- Semantik: genau eine H1 pro Route; Autobalancer-Breadcrumb unter „Live-Betrieb“.
- Design QA: drei Vergleichsschritte einschließlich Korrektur englischer Teambezeichnungen; keine offenen P0/P1/P2-Findings, Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: null Errors.
- Lint: weiterhin nicht ausführbar, weil im Checkout kein ESLint-Paket beziehungsweise Binary installiert ist.

### Bekannte Datenlücken

- Der Teamvertrag liefert keinen Zustand für gesperrte Rollen. Eine entsprechende Filteroption wird erst mit einer kompatiblen Backend-Erweiterung ergänzt.
- Der Autobalancer-Status liefert keinen belastbaren letzten tatsächlich ausgeführten Eingriff. Die Oberfläche benennt diesen Zustand ausdrücklich, statt einen Zeitwert vorzutäuschen.

### Rückrollbarkeit

Das Paket ist frontend-, datenbank- und konfigurationsneutral. Es erfordert weder Backup noch Migration und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.

## Phase 2 · Paket 2.4 – Spielerakten und Sperrlistenverwaltung

### Inventar und Risiko

- Betroffene Routen: `/records/players`, `/records/players/:playerId`, die vorhandenen Spielerprofil-Unteransichten, `/records/blacklists` und `/records/blacklists/manage`.
- Betroffene Komponenten: Spielerfilter, zentrale Mehrfachauswahl-Aktionen, Statuskennzeichnung der Spielerakte, Profilreihenfolge, Sperrlisten-Karten, Master-Detail-Verwaltung sowie Erstellen-/Bearbeiten-Dialog.
- Datenverträge und gespeicherte Konfigurationen: unverändert. `GET_PLAYERS_RECORDS`, `GET_BANS`, `GET_PLAYER`, `GET_PLAYER_MESSAGES`, Spielerkommentare, URL-Filter, Sperrlisten-Loader und alle bestehenden Erstellen-/Bearbeiten-/Löschen-Payloads werden unverändert verwendet. Unbekannte Synchronisationsarten und Servernummern bleiben beim Bearbeiten erhalten.
- Ausgangslage: Mobile war der Spielerfilter zusammen mit einer dauerhaft sichtbaren Symbolleiste zu hoch. In der Spielerakte lag die lange Zusammenfassung vor der eigentlichen Arbeitsfläche. Die Sperrlistenverwaltung war Desktop sehr weit verteilt und Mobile als abgeschnittene Pseudotabelle schwer bedienbar.

### Umsetzung

- Mobile Spielersuche und Filter zu einer kompakten Zweieraktion verdichtet; erweiterte Felder öffnen in einem beschrifteten, scrollbareren Drawer. Alle bestehenden Query-Parameter und Formfeldnamen bleiben erhalten.
- Die zentrale Spieleraktionsleiste wird nur bei tatsächlicher Auswahl gerendert. Mobile bleibt sie oberhalb der Bottom Navigation erreichbar; Auswahlanzahl und Aufheben sind sichtbar, alle bestehenden Aktionen bleiben zugänglich.
- Spielerstatus wird mit beschrifteten, eckigen Chips statt ausschließlich über unbeschriftete Symbole vermittelt. Ohne Risiko- oder Sonderstatus erscheint ein neutraler Klartext.
- Die Spielerakte priorisiert Mobile Identität, Status und aufgabenbezogene Tabs; die lange Aktenübersicht folgt danach. Desktop behält die vertraute Zweispaltenstruktur.
- Die Sperrlistenverwaltung wurde zu einer eckigen Master-Detail-Arbeitsfläche mit Kennzahlen, auswählbaren Listenkarten, Reichweite, Synchronisationsbeschreibung und Wirkhinweis ausgebaut.
- Erstellen und Bearbeiten verwenden ein strukturiertes Formular mit Listenname, Synchronisationswirkung und Serverreichweite; Mobile öffnet es vollflächig. Bestehende Werte werden nicht normalisiert oder verworfen.
- Die bestehende Eintragsseite `/records/blacklists` blieb bewusst erhalten, weil sie bereits der freigegebenen operativen Arbeitsweise entspricht.

### Validierung

- Vite-Production-Build mit API-Basispfad `/api/`: bestanden; nur die bekannte Chunk-Größenwarnung bleibt.
- Verträge: Design Foundation, Seitensemantik, Action Feedback, Konfigurationskompatibilität, Admin-Aktionen, Operator-Copy und Navigation Shell bestanden.
- Initiales Bundle-Budget: bestanden mit 1.499,65 kB Rohgröße und 482,85 kB gzip; neu eingeführte UI-Copy verwendet bestehende Übersetzungen, wo sie semantisch passen.
- Browserprüfung: Spielerakten, Spielerprofil und Sperrlistenverwaltung bei 390 × 844; Sperrlistenverwaltung zusätzlich bei 1440 × 900. Alle geprüften Zustände besitzen keinen horizontalen Dokumentüberlauf.
- Funktionsprüfung: Spieler-ID-Filter erzeugt die bestehende URL-Query; Mehrfachauswahl blendet die Aktionsregion ein und wieder aus; Profil-Tab wechselt; Sperrlistenwahl per Enter aktualisiert das Detailpanel; bestehende Bearbeitungswerte und mobiles Vollbildformular geprüft.
- Theme- und Farbsehprüfung: heller Modus plus Deuteranopie live geprüft und anschließend ohne Speicherung verworfen.
- Semantik: genau eine native H1 pro Route; sichtbare Formfelder und Dialoge sind beschriftet, Status und Auswahl werden nicht allein über Farbe vermittelt.
- Design QA: Vorher-/Nachher-Vergleich bei identischen Viewports; die erste zu früh erfasste Aufnahme wurde verworfen und nach vollständigem Laden wiederholt. Keine offenen P0/P1/P2-Findings, Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: keine route-spezifischen Runtime-Fehler. Eine bekannte globale MUI-Tooltip-`anchorEl`-Warnung kann beim Wechsel von den Benutzeraktionen in den Darstellungsdialog auftreten und ist als P3-Shell-Befund dokumentiert.
- Lint: weiterhin nicht ausführbar, weil im Checkout kein ESLint-Paket beziehungsweise Binary installiert ist.

### Rückrollbarkeit

Das Paket verändert ausschließlich Frontend-Darstellung und Interaktionsreihenfolge. Es erfordert weder Datenmigration noch Backup und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.

## Phase 2 · Paket 2.5 – Dienste, Spiel- und Audit-Protokolle

### Inventar und Risiko

- Betroffene Routen: `/settings/services`, `/records/game-logs` und `/records/audit-logs`.
- Betroffene Komponenten: Dienstzusammenfassung, Abhängigkeitskette, Dienststeuerung, mobile Spielprotokollfilter und Timelinezeilen, mobile Auditfilter sowie Listen-/Detailzustände.
- Datenverträge und gespeicherte Konfigurationen: unverändert. Dienste-Loader, Operational Health, Supportdiagnose, Dead Letters, `TOGGLE_SERVICE`, alle GET-Queryfelder der Spiel- und Audit-Protokolle sowie die Exportpfade bleiben kompatibel. Es gibt keine Migration und keine neue Persistenz.
- Ausgangslage: Die Diensteansicht zeigte Einzelzustände, aber keine klare betriebliche Kette. Auf Mobile nahmen die vollständigen Filter beider Protokollseiten so viel Höhe ein, dass die eigentlichen Daten kaum im ersten Viewport sichtbar waren. Spielprotokollzeilen überlagerten auf schmalen Displays Zeit- und Ereignisdetails.

### Umsetzung

- Die Diensteansicht führt über eine kompakte Lagezeile und die Abhängigkeitskette RCON → Worker → Scheduler zu den einzelnen Steuerungen. Zustand, Laufzeit, letzter Start/Stopp, Fehler und Betriebswirkung bleiben direkt prüfbar.
- Mobile stapelt die Betriebskette vertikal und ordnet die Zusammenfassung in drei kompakte Kennzahlen, ohne die bestehende Steuerung oder Diagnosefunktionen zu entfernen.
- Spiel- und Audit-Protokolle behalten Desktop ihre dichten Arbeitsflächen. Mobile priorisiert Suche und wenige häufige Kategorien; sämtliche erweiterten Felder liegen in einem beschrifteten Bottom Drawer.
- Portal-rendernde Drawer bewahren über versteckte Felder alle bisherigen URL- und Formverträge. Export, Sortierung, Exaktsuche, Zeitraum, Serverfilter, Benutzer, Befehle und Seitengröße bleiben erreichbar.
- Mobile Spielprotokollzeilen erhalten eine eigene Metazeile für Ereignistyp und vollständigen Zeitpunkt; die bisherigen Desktopspalten bleiben unverändert.

### Validierung

- Vite-Production-Build bestanden; nur die bekannte Chunk-Größenwarnung bleibt.
- Verträge: Design Foundation, Seitensemantik, Action Feedback, Konfigurationskompatibilität, Admin-Aktionen, Operator-Copy und Navigation Shell bestanden.
- Initiales Bundle-Budget: bestanden mit 1.499,96 kB Rohgröße und 483,01 kB gzip; Entry 401,44 kB raw und 121,64 kB gzip.
- Browserprüfung: alle drei Routen bei 1440 × 900 und 390 × 844; kein horizontaler Dokumentüberlauf und jeweils genau eine H1.
- Funktionsprüfung: Audit-Suche `Wotan`, Audit-Detail-Drawer und Spielprotokoll-Suche `FLN_Wolf` gegen die unveränderten Queryverträge ausgeführt. Dienststeuerungen visuell und semantisch geprüft, ohne einen simulierten Prozess unnötig zu starten oder zu stoppen.
- Theme- und Farbsehprüfung: heller Modus plus Deuteranopie live geprüft und ohne Speicherung verworfen.
- Tastaturprüfung: sichtbare Fokusdarstellung auf den primären Aktionen geprüft. Wiederholtes Browser-CUA-Tabbing blieb werkzeugbedingt auf demselben Element; der automatisierte Fokusvertrag bestand.
- Design QA: Vorher-/Nachher-Vergleiche bei identischen Desktop- und Mobile-Viewports; mobile Timeline-Überlagerung und zu breite Clear-Aktion nach dem ersten Lauf korrigiert. Keine offenen P0/P1/P2-Findings, Ergebnis `passed` in `design-qa.md`.
- Browserkonsole: keine Errors; ausschließlich die bekannte React-Router-v7-Future-Flag-Warnung.

### Rückrollbarkeit

Das Paket verändert ausschließlich Frontend-Darstellung, responsive Anordnung und Interaktionsreihenfolge. Es erfordert weder Datenmigration noch Backup und kann als einzelner Git-Commit mit `git revert` zurückgenommen werden. Es wurde weder gepusht noch veröffentlicht, als PR eröffnet, ausgerollt oder auf einer Produktionsinstanz aktiviert.
