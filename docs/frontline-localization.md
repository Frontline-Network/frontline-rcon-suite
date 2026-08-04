# Frontline CRCON – Design und Lokalisierung

## Produktregeln

- Deutsch ist die Standardsprache. Englisch ist vollständig verfügbar und der Fallback für fehlende Übersetzungen.
- Die Sprachwahl wird lokal gespeichert und ohne Neuladen angewendet.
- FLN ist das Standardtheme; das ursprüngliche CRCON-Theme bleibt über die bestehende Theme-Auswahl erreichbar.
- Produktionsrouten, API-Payloads, Konfigurationsschlüssel und Ereignis-IDs bleiben Englisch und werden nicht umbenannt.
- Sichtbare Bezeichnungen werden über Übersetzungen oder UI-Mappings lokalisiert.
- Kritische Moderationsaktionen benötigen weiterhin eine explizite Bestätigung und zeigen laufenden, erfolgreichen oder fehlgeschlagenen Zustand.

## Gemeinsame Begriffsliste

| Intern / Englisch | Deutsch | Verwendung |
| --- | --- | --- |
| Live view | Live-Ansicht / Live-Einsatz | Laufender Serverbetrieb |
| Team view | Teamübersicht | Teams und Trupps |
| Squad | Trupp | Einheit innerhalb eines Teams |
| Player records | Spielerakten | Historische Spielerprofile |
| Watchlist | Beobachtungsliste | Beobachtete Spieler |
| Blacklist | Sperrliste | Serverübergreifende Sperrverwaltung |
| Game logs | Spielprotokolle | Historische Spielereignisse |
| Audit logs | Audit-Protokolle | Administrative Änderungen |
| Map rotation | Kartenrotation | Reihenfolge der Karten |
| Objectives | Sektoren | Zielpunkte einer Karte |
| Votemap | Kartenabstimmung | Spielergesteuerte Kartenwahl |
| Whitelist | Auswahlliste | Für Kartenabstimmung zugelassene Karten |
| Autosettings | Automatische Einstellungen | Regelbasierte Serverkonfiguration |
| Message template | Nachrichtenvorlage | Wiederverwendbarer Nachrichteninhalt |
| Console admins | Konsolen-Admins | Native Gameserver-Adminrollen |
| Player actions | Spieleraktionen | Bestätigte Moderationsmaßnahmen |
| Team kill | Teamkill | Schaden oder Tod im eigenen Team |
| Game details | Spieldetails | Auswertung eines abgeschlossenen Spiels |
| Incident | Vorfall | Mobile Moderationsmeldung |
| Pairing | Kopplung | Sichere Verbindung der Mobile-App |
| Kick | Kick | Sofortiges Entfernen vom Server |
| Temporary ban | Temporäre Sperre | Zeitlich begrenzte Sperre |
| Permanent ban | Dauerhafte Sperre | Unbefristete Sperre |

## Lokale Demo-Abdeckung

Der Fake-Build verwendet ausschließlich vorhandene CRCON-Routen. Die statischen Demo-Daten in `rcongui/src/mirage/demo-data.js` verhindern externe Produktionsaufrufe für Spielerakten, Protokolle, Karten, Dienste, Einstellungen und Statistiken. Produktions-Builds führen weiterhin die bestehenden Loader und API-Befehle aus.

Für die Spielerakte nutzt der Fake-Betrieb denselben deterministischen Datensatz wie die Spielerliste. Damit bleiben Profil, Maßnahmen, Sitzungen, Namen, Kommentare und Protokolle lokal vollständig navigierbar, während der Produktionspfad unverändert die bestehenden API-Befehle verwendet.

## Mobile Sicherheit und Abhängigkeiten

Secure Storage, verschlüsselter Cache, Pairing-Payloads, Push-Relay und API-Modelle wurden nicht verändert. `sqlcipher_flutter_libs` bleibt vorerst auf `0.7.0+eol`, weil ein Austausch die native Verschlüsselungs- und Migrationskette berührt und nicht als Designänderung vorgenommen werden darf. Vor einer Aktualisierung sind ein dokumentierter Migrationspfad, Lesetests für bestehende verschlüsselte Datenbanken und Android-/iOS-Gerätetests erforderlich.

Der Web-Produktionsbaum verwendet weiterhin `package-lock.json`. Ein `pnpm audit` ist damit nicht aussagefähig (`ERR_PNPM_AUDIT_NO_LOCKFILE`); ein npm-kompatibler Audit-Lauf muss in der regulären Node-/CI-Umgebung ausgeführt werden. Der Build meldet aktuell nur die bekannte Bundle-Größenwarnung. Flutter meldet außerdem eine zukünftige Kotlin-Gradle-Migration für `mobile_scanner`; der Debug-APK-Build ist derzeit erfolgreich.

## Prüfmatrix

- Web: Fake- und Produktionsbuild
- Browser: 1440 × 1024 und 390 × 844
- Kernablauf: Live-Ansicht → Spieler auswählen → Aktion konfigurieren → bestätigen → Ergebnis
- Mobile: `flutter analyze`, Unit-/Widgettests und Debug-APK
- Design: Referenz und Implementierung gemeinsam vergleichen; `design-qa.md` muss mit `final result: passed` enden

Der aktuelle Webtest-Befehl `pnpm test -- --runInBand` ist nicht lauffähig, weil das Skript `jest` aufruft, die Abhängigkeit jedoch nicht installiert ist. Fake-/Produktionsbuild und die Browser-Routenmatrix bleiben davon unabhängig erfolgreich. Eine Test-Toolchain wird nur nach gesonderter Entscheidung ergänzt, damit keine unbeauftragte Abhängigkeitsänderung entsteht.

Letzte Mobile-Prüfung: `flutter analyze` ist ohne Befunde durchgelaufen; die fünf Widgettests für deutsche Begriffe, englischen Fallback und das Frontline-Theme sind erfolgreich. Der Debug-APK-Build ist erfolgreich. Die bekannte, nicht blockierende Kotlin-Gradle-Warnung von `mobile_scanner` bleibt separat zu bewerten. Die Navigation enthält Verbindungen, Kopplung, Vorfall-Inbox, Spielersuche, Spielerprofil und Vorfallbearbeitung; dabei bleiben Secure Storage, verschlüsselter Cache, Push-Relay und Pairing-Protokoll unverändert.

Ein `passed`-Ergebnis in der Design-QA gilt jeweils nur für den dort genannten Meilenstein. Der abschließende Produkt-QA-Lauf wird erst nach dem Abgleich aller Routen, Sprachzustände und der nativen App gesetzt.
