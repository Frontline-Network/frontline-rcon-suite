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
