// Operator documentation for this CRCON fork. Keep role descriptions in sync
// with rconweb/api/permission_presets.py; endpoint contracts come from the API.
export const helpArticles = [
  {
    id: "start",
    title: { de: "Einstieg & Navigation", en: "Getting started & navigation" },
    summary: {
      de: "Server wählen, Ansichten finden und Änderungen sicher übernehmen.",
      en: "Choose a server, find views and apply changes confidently.",
    },
    body: {
      de: `### Den richtigen Server wählen
Prüfe vor einer Aktion den ausgewählten Server und den Verbindungsstatus. Live-Daten und Serveraktionen beziehen sich auf den jeweiligen Serverkontext. Benutzerverwaltung und persönliche Darstellung haben einen eigenen Geltungsbereich.

### Schnell zur passenden Ansicht
- **Live-Betrieb:** Spieler, Ereignisse und Teamverteilung während einer laufenden Runde beobachten.
- **Moderation:** Spielerakten und Blacklists für Nachverfolgung und Sanktionen verwenden.
- **Spielsteuerung:** Karten, Rotation, Kartenabstimmungen und Servereinstellungen bearbeiten.
- **Automatisierung:** Automods und Regeln konfigurieren. Der Autobalancer besitzt außerdem eine eigene Betriebsansicht.
- **Historie:** Spielprotokolle, ausgeführte Aktionen und abgeschlossene Runden nachvollziehen.

Nutze die Suche in der Kopfzeile, um Seiten zu finden. Im Wardogs-Theme öffnet das Menü-Symbol links die Hauptnavigation; darunter liegen deine persönlichen QuickIcons.

### Änderungen übernehmen
Formulare übernehmen Änderungen erst über ihre jeweilige Speichern- oder Anwenden-Aktion. Lies vor einer Bestätigung den angezeigten Umfang, insbesondere bei Kartenwechseln, Spieleraktionen und Sammelaktionen. Eine Erfolgsmeldung bestätigt die Übernahme; ein geänderter Eingabewert allein tut dies nicht.

### Fehlende Funktionen
Die verfügbaren Aktionen hängen von deinen Rechten und den Fähigkeiten des Gameservers ab. Eine ausgegraute Aktion oder eine fehlende Seite ist deshalb nicht automatisch ein Darstellungsfehler.`,
      en: `### Choose the correct server
Check the selected server and connection status before an action. Live data and server actions use the current server context. User administration and personal appearance have their own scope.

### Find the right view
- **Live operations:** Watch players, events and team balance during a round.
- **Moderation:** Use player records and blacklists to investigate and apply sanctions.
- **Game operations:** Manage maps, rotation, map voting and server settings.
- **Automation:** Configure automods and rules. The autobalancer also has a dedicated operations view.
- **History:** Review game logs, administrative actions and completed rounds.

Use the search in the header to find pages. In Wardogs, the menu icon on the left opens the main navigation; your personal QuickIcons appear below it.

### Apply changes
Forms apply edits through their save or apply action. Check the displayed scope before confirming, especially for map changes, player actions and bulk operations. A success message confirms the change; editing an input alone does not.

### Missing features
Available actions depend on your permissions and the game server's capabilities. A disabled action or missing page is not necessarily a display problem.`,
    },
  },
  {
    id: "moderation",
    title: {
      de: "Live-Betrieb & Moderation",
      en: "Live operations & moderation",
    },
    summary: {
      de: "Spieler finden, Vorfälle prüfen und passend reagieren.",
      en: "Find players, investigate incidents and take appropriate action.",
    },
    body: {
      de: `### Einen Vorfall bearbeiten
1. Öffne **Live** und grenze Spieler oder Ereignisse mit den Filtern ein.
2. Öffne die betroffene Person und prüfe Name, Spieler-ID, Team und relevante Protokolle. Ähnliche Namen sind kein zuverlässiges Identitätsmerkmal.
3. Wähle die passende Aktion: Nachricht, Bestrafung, Kick, Teamwechsel oder Bann – abhängig von Situation und Rechten.
4. Prüfe Ziel, Begründung und gegebenenfalls Dauer im Dialog, bevor du bestätigst.
5. Kontrolliere die Rückmeldung und halte relevante Informationen als Kommentar in der Spielerakte fest.

### Kick, Bann und Blacklist
Ein **Kick** entfernt einen Spieler aus der laufenden Sitzung. Ein **temporärer Bann** verhindert die Rückkehr für seine Laufzeit, ein **permanenter Bann** bis zur Aufhebung. Eine **Blacklist** verwaltet Einträge und deren Regeln im CRCON. Das Löschen eines Eintrags ist nicht in jedem Ablauf mit dem Entfernen eines bereits bestehenden Serverbanns gleichzusetzen; verwende die dafür vorgesehene Entbannen-Aktion.

### Autobalancer
Prüfe in der Autobalancer-Ansicht den Status, die Teamlage und vorgeschlagene Maßnahmen. Die Vorlage **Moderator** erlaubt das Prüfen und Ausführen von Vorschlägen. Änderungen an der Autobalancer-Konfiguration benötigen zusätzliche Rechte.

### Verlauf und Filter
Live-Filter beeinflussen die Anzeige, nicht die gespeicherten Ereignisse. Für ältere Vorgänge nutze Spielerakten und historische Spielprotokolle. Das Audit-Protokoll dokumentiert administrative Aktionen, soweit die jeweilige Aktion dort erfasst wird.`,
      en: `### Handle an incident
1. Open **Live** and narrow down players or events using the filters.
2. Open the player and check their name, player ID, team and relevant logs. Similar names are not a reliable identity check.
3. Choose the appropriate action: message, punish, kick, switch team or ban, depending on the situation and your permissions.
4. Review the target, reason and duration where applicable before confirming.
5. Check the result and record relevant information as a comment in the player's record.

### Kicks, bans and blacklists
A **kick** removes a player from the current session. A **temporary ban** prevents returning for its duration; a **permanent ban** lasts until removed. A **blacklist** manages records and their rules in CRCON. Deleting a record does not necessarily remove an existing server ban; use the appropriate unban action.

### Autobalancer
Check the status, team situation and proposed actions in the autobalancer view. The **Moderator** preset allows reviewing and executing proposals. Editing the autobalancer configuration requires additional permissions.

### History and filters
Live filters change what is displayed, not the stored events. Use player records and historical game logs for older incidents. Audit logs record administrative actions where the relevant action supports auditing.`,
    },
  },
  {
    id: "maps",
    title: { de: "Karten & Spielbetrieb", en: "Maps & match operations" },
    summary: {
      de: "Kartenwechsel, Rotation, Abstimmungen und Spielregeln unterscheiden.",
      en: "Understand map changes, rotation, voting and match settings.",
    },
    body: {
      de: `### Aktuelle und nächste Karte
Die aktuelle Karte zeigt den laufenden Einsatz. Die nächste Karte beschreibt den vorgesehenen Folgeschritt. Prüfe beim Kartenwechsel, ob die Aktion sofort wirkt oder einen späteren Wechsel vorbereitet. Ein sofortiger Wechsel unterbricht die laufende Runde.

### Rotation und Kartenabstimmung
Die **Rotation** legt die Kartenfolge fest. Die **Whitelist** begrenzt die für den jeweiligen Ablauf zugelassenen Karten. **Votemap** steuert die Kartenabstimmung und deren Ergebnis. Zufallsreihenfolge und Abstimmung können beeinflussen, welche Karte tatsächlich folgt.

1. Prüfe den ausgewählten Server und seine verfügbaren Karten.
2. Bearbeite Rotation oder Abstimmungsregeln im passenden Bereich.
3. Speichere die Konfiguration und kontrolliere den aktuellen Status der Abstimmung beziehungsweise Kartenfolge.

### Kartenziele, Wetter und Zeiten
Verfügbarkeit und Wirkung hängen vom Spiel und Server ab. Nutze die Hinweise zur jeweiligen Einstellung. Eine gespeicherte Einstellung kann erst mit dem nächsten passenden Spielzustand wirksam werden.

### Welche Rolle passt?
**Spielbetrieb** umfasst Kartensteuerung, Rotation, Abstimmungen, Kartenziele, Wetter, Runden- und Aufwärmzeiten sowie Willkommensnachrichten und Kampagnen. Für Kicks, Banns und andere Spielersanktionen ergänze **Moderator**.`,
      en: `### Current and next map
The current map is the active match. The next map shows the planned following step. Check whether a map action takes effect immediately or prepares a later change. An immediate change interrupts the ongoing round.

### Rotation and map voting
**Rotation** defines the map sequence. The **whitelist** limits the maps allowed in the relevant workflow. **Votemap** controls map voting and its outcome. Shuffle and voting can affect which map actually follows.

1. Check the selected server and its available maps.
2. Edit rotation or voting rules in the relevant area.
3. Save the configuration and check the current vote status or map sequence.

### Objectives, weather and timers
Availability and effects depend on the game and server. Read the guidance for each setting. A saved setting may only take effect at the next applicable game state.

### Which role fits?
**Match operations** includes map control, rotation, voting, objectives, weather, match and warmup timers, welcome messages and campaigns. Add **Moderator** for kicks, bans and other player sanctions.`,
    },
  },
  {
    id: "messages",
    title: { de: "Nachrichten & Automatisierung", en: "Messages & automation" },
    summary: {
      de: "Willkommensnachricht, Broadcast und Kampagnen richtig einsetzen.",
      en: "Use welcome messages, broadcasts and campaigns effectively.",
    },
    body: {
      de: `### Den passenden Nachrichtentyp verwenden
- **Direktnachricht:** gezielt an eine ausgewählte Person senden.
- **Willkommensnachricht:** den konfigurierten Begrüßungstext für den Server bearbeiten.
- **Broadcast:** den serverweiten Broadcast-Text steuern.
- **Kampagnen:** Nachrichten anhand von Zielgruppen, Zeitplänen und Bedingungen versenden.

### Eine Kampagne vorbereiten
1. Wähle den passenden Kampagnentyp und bearbeite Text und Bedingungen.
2. Prüfe verfügbare Platzhalter und die Vorschau. Nicht jeder Nachrichtentyp unterstützt dieselben Platzhalter.
3. Prüfe Zielgruppe, Wartezeiten und Pausenregeln, soweit die Kampagne diese anbietet.
4. Nutze eine Testnachricht bewusst: Sie wird tatsächlich an den ausgewählten Spieler gesendet.
5. Speichere die Konfiguration und kontrolliere den Versandstatus beziehungsweise das Protokoll.

Beim **VIP-Lebenszyklus** erzeugt der Testmodus Zielgruppen und Protokolle, ohne automatische Nachrichten zu senden. Eine ausdrücklich ausgelöste Testnachricht wird auch dort versendet.

### Automatische Regeln
Automods und Auto-Settings können den Spielbetrieb selbstständig beeinflussen. Prüfe Bedingungen, Aktivierung und mögliche Überschneidungen mit anderen Regeln. Vorschau, Validierung und Speichern erfüllen unterschiedliche Aufgaben: Eine erfolgreiche Prüfung aktiviert eine Regel nicht automatisch.`,
      en: `### Choose the right message type
- **Direct message:** send to a selected player.
- **Welcome message:** edit the server's configured greeting.
- **Broadcast:** manage the server-wide broadcast text.
- **Campaigns:** send messages based on audiences, schedules and conditions.

### Prepare a campaign
1. Choose the campaign type and edit its message and conditions.
2. Check supported placeholders and the preview. Different message types support different placeholders.
3. Review the audience, delays and pause rules where available.
4. Use test messages deliberately: they are actually sent to the selected player.
5. Save the configuration and check delivery status or logs.

In **VIP lifecycle** test mode, audiences and logs are generated without automatic delivery. An explicitly triggered test message is still sent.

### Automatic rules
Automods and Auto-Settings can affect matches automatically. Check conditions, activation and overlap with other rules. Previewing, validating and saving serve different purposes: a successful validation does not automatically enable a rule.`,
    },
  },
  {
    id: "roles",
    title: {
      de: "Benutzer, Rollen & Rechte",
      en: "Users, roles & permissions",
    },
    summary: {
      de: "Gruppen mit Vorlagen einrichten und Zugriffe nachvollziehen.",
      en: "Set up groups using presets and understand effective access.",
    },
    body: {
      de: `### Eine Rolle anlegen
1. Öffne **Administration → Gruppen → Hinzufügen** und vergib einen aussagekräftigen Namen.
2. Wähle eine Vorlage und lies deren Beschreibung. Die Auswahl zeigt zunächst nur die Vorschau.
3. Klicke **Vorlage übernehmen**. Die Rechte werden zur bisherigen Auswahl hinzugefügt.
4. Ergänze weitere Vorlagen oder passe einzelne Rechte an. Prüfe die Auswahl und klicke **Sichern**.
5. Öffne das Benutzerkonto, ordne ihm die Gruppe zu und speichere auch das Konto.

### Die Vorlagen im Überblick
| Vorlage | Aufgaben |
| --- | --- |
| Nur lesen | Live-Daten, Spielerakten, Bannlisten und historische Spielprotokolle ansehen. |
| Support | Zusätzlich Nachrichten senden, Kommentare schreiben und Spieler beobachten. |
| Moderator | Zusätzlich kicken, bestrafen, temporär und permanent bannen, entbannen, Team- und Truppaktionen sowie Blacklist-Einträge und Markierungen bearbeiten. Autobalancer-Vorschläge prüfen und ausführen. |
| Spielbetrieb | Karten, Rotation, Zufallsreihenfolge, Ziele, Wetter, Zeiten und Kartenabstimmungen steuern. Willkommensnachrichten, Broadcasts und Kampagnen verwalten. |

**Moderator + Spielbetrieb** kombiniert Spielermaßnahmen und Spielsteuerung. Die Vorlagen vergeben keine Benutzerverwaltung, keine freie RCON-Konsole und keine VIP-Vergabe. Autobalancer-Konfigurationsrechte gehören ebenfalls nicht zur Moderator-Vorlage.

Vorlagen sind Ausgangspunkte. Änderungen an einer Vorlage verändern bereits gespeicherte Gruppen nicht nachträglich. Das erneute Übernehmen ergänzt Rechte; es entfernt keine vorhandenen Rechte.

### Mehrere Rechte auswählen
Die Gesamtauswahl schaltet alle aktuell gefilterten Rechte um. Jede Kategorie besitzt zusätzlich eine eigene Auswahl, auch wenn sie zugeklappt ist. Bei aktiver Suche wirken Sammelaktionen auf die passenden Treffer. Leere die Suche, wenn du die gesamte Rechteauswahl bearbeiten möchtest. Erst **Sichern** übernimmt die Änderungen.

### Wie Rechte zusammenwirken
Die wirksamen Rechte eines Kontos setzen sich aus **allen Gruppen und zusätzlich direkt vergebenen Rechten** zusammen. Das Abwählen eines direkten Rechts entzieht kein Recht, das weiterhin über eine Gruppe vergeben wird.

- **Konto aktiv:** erlaubt die Anmeldung. Ein deaktiviertes Konto kann sich nicht anmelden.
- **Zugang zur Administration (Staff):** erlaubt den grundsätzlichen Zugang zur Verwaltung; die nötigen Modellrechte kommen hinzu. Dies vergibt nicht automatisch alle RCON-Rechte.
- **Superuser:** besitzt sämtliche Berechtigungen. Für normale Moderatoren ist dieses Kennzeichen nicht erforderlich.

### Eine Aktion ist trotzdem gesperrt
Prüfe zuerst die Rechtebeschreibung und gegebenenfalls die API-Referenz: Einige Aktionen benötigen mehrere Rechte gleichzeitig. Kontrolliere alle zugewiesenen Gruppen, speichere die Änderung und lade die Ansicht des betroffenen Nutzers neu.`,
      en: `### Create a role
1. Open **Administration → Groups → Add** and choose a descriptive name.
2. Select a preset and read its description. Selecting it initially shows a preview only.
3. Click **Apply preset**. Its permissions are added to the current selection.
4. Combine presets or adjust individual permissions. Review the selection and click **Save**.
5. Open the user account, assign the group and save the account as well.

### Available presets
| Preset | Tasks |
| --- | --- |
| Read only | View live data, player records, ban lists and historical game logs. |
| Support | Also send messages, add comments and manage the player watchlist. |
| Moderator | Also kick, punish, temporarily and permanently ban, unban, perform team and squad actions, and manage blacklist records and flags. Review and execute autobalancer proposals. |
| Match operations | Control maps, rotation, shuffle, objectives, weather, timers and map voting. Manage welcome messages, broadcasts and campaigns. |

**Moderator + Match operations** combines player actions and match control. Presets do not grant user administration, raw RCON console access or VIP assignment. Autobalancer configuration permissions are not included in Moderator either.

Presets are starting points. Updating a preset does not change previously saved groups. Applying it again adds permissions; it does not remove existing permissions.

### Select multiple permissions
The overall selection toggles all currently filtered permissions. Each category has its own selection, even when collapsed. With an active search, bulk actions affect matching results. Clear the search to work on the entire permission selection. Changes take effect only after **Save**.

### How permissions combine
An account's effective permissions are the union of **all its groups and directly assigned permissions**. Clearing a direct permission does not remove a permission still granted by a group.

- **Active account:** permits sign-in. An inactive account cannot sign in.
- **Administration access (Staff):** permits entry to administration; relevant model permissions are also needed. This does not automatically grant all RCON permissions.
- **Superuser:** has every permission. Regular moderators do not need this flag.

### An action is still unavailable
Check the permission description and the API reference: some actions require multiple permissions at once. Review all assigned groups, save the change and reload the affected user's view.`,
    },
  },
  {
    id: "appearance",
    title: {
      de: "Theme, Farbstile & QuickIcons",
      en: "Theme, colour styles & QuickIcons",
    },
    summary: {
      de: "Deine Oberfläche und Schnellzugriffe persönlich einrichten.",
      en: "Personalise your interface and shortcuts.",
    },
    body: {
      de: `### Theme und Farbe ändern
1. Öffne **Darstellung** über die Navigation oder das Benutzermenü.
2. Wähle **Wardogs** oder eines der vorhandenen Frontline-Themes.
3. Im Wardogs-Theme stehen sechs Farbstile zur Verfügung: Rose, Eisblau, Smaragd, Bernstein, Amethyst und Schiefer.
4. Wähle einen hellen, dunklen oder vom System gesteuerten Modus. Bei Bedarf kannst du außerdem die Farbdarstellung für Farbsehschwächen anpassen.
5. Prüfe die unmittelbare Vorschau und speichere. **Abbrechen** stellt deine vorherige Darstellung wieder her.

Die Darstellung gehört zu deinem Benutzerkonto. Falls ein älteres Backend diese Einstellungen noch nicht speichern kann, weist der Dialog auf die lokale Speicherung im Browser hin.

### QuickIcons anpassen
Im Wardogs-Theme befindet sich unter den Schnellzugriffen eine gestrichelte **Anpassen**-Schaltfläche. Öffne sie, suche die gewünschten Seiten und wähle deine Favoriten. Ordne sie mit den Pfeilen nach oben oder unten und speichere die Auswahl.

QuickIcons zeigen nur Ziele an, auf die du Zugriff hast. Verliert ein Konto ein Recht, wird der betreffende Schnellzugriff ausgeblendet. Das Menü-Symbol oberhalb der Trennlinie bleibt der Zugang zur vollständigen Navigation.

### Auf kleinen Bildschirmen
Die Navigation lässt sich über das Menü-Symbol öffnen. Nicht jede Desktop-Leiste wird auf dem Smartphone dauerhaft eingeblendet. Die Dokumentation erreichst du auch über das Benutzermenü.`,
      en: `### Change theme and colour
1. Open **Appearance** from navigation or the user menu.
2. Choose **Wardogs** or one of the existing Frontline themes.
3. Wardogs offers six colour styles: Rose, Ice blue, Emerald, Amber, Amethyst and Slate.
4. Select light, dark or system mode. You can also adjust colours for colour vision differences.
5. Review the immediate preview and save. **Cancel** restores your previous appearance.

Appearance belongs to your user account. If an older backend cannot save these preferences, the dialog explains that they will be stored locally in the browser.

### Customise QuickIcons
In Wardogs, use the dashed **Customise** button below the shortcuts. Search for pages and select your favourites. Move them up or down using the arrows and save the selection.

QuickIcons show only destinations you can access. If an account loses a permission, its corresponding shortcut is hidden. The menu icon above the divider remains the entry point to the full navigation.

### Small screens
Open navigation using the menu icon. Some desktop bars are not permanently displayed on phones. Documentation is also available from the user menu.`,
    },
  },
  {
    id: "troubleshooting",
    title: { de: "Häufige Fragen & Fehler", en: "Common questions & errors" },
    summary: {
      de: "Fehlende Rechte, veraltete Daten und Speicherprobleme einordnen.",
      en: "Understand missing permissions, stale data and save failures.",
    },
    body: {
      de: `### Warum kann ich eine Seite sehen, aber nichts ändern?
Leserechte und Änderungsrechte sind getrennt. Einige Seiten bündeln mehrere Funktionen mit unterschiedlichen Anforderungen. Die Sichtbarkeit einer Seite ist keine Zusage, dass jede Aktion darauf erlaubt ist.

### Warum zeigt die Ansicht keine aktuellen Daten?
Prüfe den ausgewählten Server, den Verbindungsstatus und den Zeitpunkt der letzten Aktualisierung. Eine unterbrochene Verbindung oder eine leere gefilterte Liste bedeutet nicht, dass der Gameserver leer ist. Entferne Filter, um die Ansicht einzugrenzen.

### Warum wurde meine Änderung nicht gespeichert?
Lies die Fehlermeldung und prüfe Pflichtfelder, Wertebereiche und Berechtigungen. Nach einer abgelaufenen Sitzung musst du dich neu anmelden. Bei einem unklaren Ergebnis einer Serveraktion kontrolliere zuerst den tatsächlichen Zustand, bevor du dieselbe Aktion erneut auslöst.

### Warum kann eine Gruppe ein Recht trotz Abwahl weiterhin nutzen?
Weitere Gruppen oder direkt vergebene Rechte können denselben Zugriff erlauben. Superuser besitzen unabhängig von der sichtbaren Auswahl alle Rechte. Prüfe deshalb das gesamte Benutzerkonto.

### Was braucht das Team für eine Fehlersuche?
Notiere Seite, Server, Zeitpunkt, genaue Fehlermeldung und die Schritte zum Problem. Gib an, ob der Fehler beim Laden, Prüfen oder Speichern auftritt. API-Schlüssel und Passwörter gehören nicht in Screenshots oder Fehlerberichte.`,
      en: `### Why can I view a page but not change anything?
Read and change permissions are separate. Some pages combine features with different requirements. Being able to view a page does not guarantee permission for every action on it.

### Why is the data not current?
Check the selected server, connection status and last update time. A disconnected view or an empty filtered list does not mean the game server is empty. Clear filters to narrow down the cause.

### Why was my change not saved?
Read the error and check required fields, value ranges and permissions. An expired session requires signing in again. If a server action has an uncertain outcome, check the actual state before repeating it.

### Why does a user retain a permission after it was cleared?
Other groups or direct permissions may grant the same access. Superusers have all permissions regardless of the visible selection. Review the entire user account.

### What helps the team investigate?
Record the page, server, time, exact error and steps to reproduce. Explain whether the problem occurs during loading, validation or saving. Do not include API keys or passwords in screenshots or issue reports.`,
    },
  },
];

const readExamples = `
\`\`\`bash
# CRCON_API_URL: e.g. https://rcon.example/api (without a trailing slash)
# CRCON_API_KEY: the key assigned to your integration account
curl --fail-with-body "$CRCON_API_URL/get_status" \\
  -H "Authorization: Bearer $CRCON_API_KEY"

curl --fail-with-body "$CRCON_API_URL/get_recent_logs" \\
  -H "Authorization: Bearer $CRCON_API_KEY" \\
  -H "Content-Type: application/json" \\
  --data '{"start":0,"end":20,"filter_action":["CHAT"]}'
\`\`\`
`;

export const apiGuide = {
  de: `### Basisadresse und Anmeldung
Die Beispiele verwenden die API-Basisadresse eurer Installation mit dem Pfad **/api**. Bei getrenntem Frontend und Backend gilt die konfigurierte Backend-Adresse.

Für Integrationen lässt ein berechtigter Administrator einen **API-Schlüssel** anlegen und einem Benutzer zuweisen. Der Schlüssel benötigt mindestens 32 Zeichen; verwende einen zufällig erzeugten Wert und bewahre das Original sicher auf. Er wird mit **Authorization: Bearer DEIN_API_SCHLUESSEL** gesendet. Es gelten die Rechte des zugeordneten Kontos. Schlüssel gehören in eine geschützte Umgebungsvariable, nicht in URLs oder öffentlichen Frontend-Code.

Im Browser verwendet das RCON eine angemeldete Sitzung. Ändernde Anfragen mit Sitzungscookie benötigen grundsätzlich den passenden CSRF-Token aus dem Cookie **csrftoken** im Header **X-CSRFToken**. Die Anwendung übernimmt das. Externe Integrationen sollten Bearer-Anmeldung ohne Sitzungscookies verwenden.

### Zwei Abfragen zum Einstieg
Die erste Abfrage benötigt **api.can_view_get_status**, die zweite **api.can_view_recent_logs**. Beide lesen Daten; der zweite Endpunkt akzeptiert dafür auch POST.
${readExamples}
### Parameter und Antworten
GET-Parameter werden in der Query-Zeichenfolge übergeben. Wiederholte Schlüssel werden bei den RCON-Endpunkten als Liste eingelesen. POST/PUT verwenden in der Regel ein JSON-Objekt und **Content-Type: application/json**; Uploads haben eigene Formate. Spieler-IDs sollten als Zeichenketten übertragen werden.

Die typische JSON-Antwort enthält **result**, **command**, **arguments**, **failed**, **error** und **version**. Prüfe sowohl den HTTP-Status als auch **failed** und **error**. Rückgabetypen in der Referenz beschreiben das Ergebnis innerhalb von **result**. CSV-Exporte und Downloads können davon abweichen.

### Fehler verstehen
| Status | Bedeutung / nächster Schritt |
| --- | --- |
| 400 | Anfrage oder Werte prüfen; die Fehlermeldung nennt häufig die Ursache. |
| 401 | Anmeldung oder API-Schlüssel fehlt beziehungsweise wird nicht akzeptiert. |
| 403 | Rechte oder CSRF-Prüfung fehlgeschlagen. Fehlertext und Authentifizierungsart prüfen. |
| 404 / 405 | Pfad beziehungsweise HTTP-Methode mit der Referenz dieses Backends abgleichen. |
| 429 | Abfragelimit erreicht; Abstände vergrößern. |
| 500 / 504 | Backend-Fehler beziehungsweise Zeitüberschreitung; Serverzustand und Protokolle prüfen. |

### Grenzen der automatisch erzeugten Referenz
Die Einträge stammen aus **get_api_documentation** des verbundenen Backends. Die Registrierung nennt Methoden und Rechte, Python-Signaturen liefern Parameter und Typen. Nicht jedes JSON-Feld oder Antwortschema ist darüber sichtbar. Eine leere Parametertabelle bedeutet deshalb nicht automatisch, dass keine Eingabe erforderlich ist. Leere Rechteangaben bedeuten ebenso wenig, dass ein Endpunkt ohne Anmeldung aufrufbar ist. Erläuterungen sind auf Deutsch und Englisch verfügbar. Zusätzliche technische Hinweise aus dem Backend bleiben in ihrer Originalsprache; ältere Backends zeigen gegebenenfalls nur diese Quelltexte.`,
  en: `### Base URL and authentication
Examples use your installation's API base URL with the **/api** path. If frontend and backend are separate, use the configured backend address.

For integrations, an authorised administrator creates an **API key** and assigns it to a user. Keys require at least 32 characters; use a randomly generated value and keep the original secure. Send it as **Authorization: Bearer YOUR_API_KEY**. The associated account's permissions apply. Keep keys in a protected environment variable, not URLs or public frontend code.

In the browser, CRCON uses an authenticated session. Mutating requests with a session cookie generally require the matching CSRF token from the **csrftoken** cookie in the **X-CSRFToken** header. The application handles this. External integrations should use Bearer authentication without session cookies.

### Two introductory queries
The first query requires **api.can_view_get_status**, the second **api.can_view_recent_logs**. Both read data; the second endpoint also accepts POST for this purpose.
${readExamples}
### Parameters and responses
Pass GET parameters in the query string. Repeated keys are read as a list by RCON endpoints. POST/PUT generally accept a JSON object with **Content-Type: application/json**; uploads have their own formats. Send player IDs as strings.

A typical JSON response contains **result**, **command**, **arguments**, **failed**, **error** and **version**. Check the HTTP status as well as **failed** and **error**. Return types in the reference describe the value inside **result**. CSV exports and downloads may differ.

### Understanding errors
| Status | Meaning / next step |
| --- | --- |
| 400 | Check request fields and values; the error often explains the cause. |
| 401 | Authentication or the API key is missing or not accepted. |
| 403 | Permission or CSRF check failed. Check the error and authentication method. |
| 404 / 405 | Check the path or HTTP method against this backend's reference. |
| 429 | Request limit reached; increase the interval between requests. |
| 500 / 504 | Backend error or timeout; check server state and logs. |

### Limits of the generated reference
Entries come from **get_api_documentation** on the connected backend. Registration supplies methods and permissions; Python signatures supply arguments and types. Not every JSON field or response schema is visible through this mechanism. An empty argument table does not automatically mean that no input is required. An empty permission list does not imply anonymous access either. Explanations are available in German and English. Additional technical notes from the backend retain their original language; older backends may only provide these source notes.`,
};
