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
