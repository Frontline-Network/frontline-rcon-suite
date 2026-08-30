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
