// Operator documentation for this CRCON fork. Keep role descriptions in sync
// with rconweb/api/permission_presets.py; endpoint contracts come from the API.
export const helpArticles = [
  {
    id: "updates",
    title: { de: "Updates & Changelogs", en: "Updates & changelogs" },
    summary: { de: "Änderungen der installierten Version direkt im RCON lesen.", en: "Read changes for the installed version directly in RCON." },
    body: {
      de: `### Der Update-Kanal

Über **Update-Kanal** im Benutzermenü oder in der Navigation findest du die Changelogs dieser RCON-Installation. Im Aurora-Theme befindet sich der Einstieg zusätzlich unten in der Hauptnavigation. Die aktuelle Version ist gekennzeichnet; der Versionsverlauf enthält ältere stabile Releases. Die Suche durchsucht Titel, Versionen und Texte.

### Erst nach dem Aufspielen

Ein neues Release auf GitHub wird hier erst sichtbar, wenn **Frontend und Backend dieselbe veröffentlichte Version** verwenden. Bei einem laufenden Versionswechsel, einer Entwicklungsfassung oder unbekannter Version erscheint ein Hinweis. Ein direkter Link auf eine neuere Versionsnummer umgeht diese Prüfung nicht. Der Versionsverlauf ist kein Protokoll darüber, wann frühere Versionen tatsächlich installiert waren.

### Was ist neu?

Für ausgewählte Releases erscheint auf der Übersicht eine kurze Einblendung mit einem Hauptthema und bis zu zwei weiteren Verbesserungen. Sie übernimmt dein Theme und deine Sprache; **DE / EN** wechselt die Anwendungssprache. Während du Formulare oder andere Dialoge bedienst, wird keine Einblendung darübergelegt.

Die Einblendung erscheint einmal pro Konto und Version. Dieser Status wird auf dem Server gespeichert und gilt auch auf anderen Geräten. **Später** erinnert nach 24 Stunden erneut, sobald du die Übersicht besuchst. Über **Was ist neu?** im Benutzermenü oder Update-Kanal kannst du sie jederzeit wieder öffnen. Dieser Status ist unabhängig vom Lesestand des Changelogs. Fehlen vollständig gepflegte deutsche und englische Highlights, bleibt der normale Changelog verfügbar.

### Gelesen und ungelesen

**Neu für dich** kennzeichnet die aktuelle Version, solange du sie noch nicht als gelesen markiert hast. Der Lesestand wird in diesem Browser für dein Konto und diese RCON-Adresse gespeichert. Das Lesen verändert keine Einstellungen und installiert keine Updates.

### Ohne GitHub-Zugang

Die Changelogs werden aus unserem privaten Repository übernommen und direkt im RCON angezeigt. Dafür brauchst du nur deine normale RCON-Anmeldung. Es werden keine Repository-Links, externen Bilder oder Zugangsdaten geladen. Die Texte bleiben in der Sprache des veröffentlichten Releases.`,
      en: `### The update channel

Open **Update channel** in the account menu or navigation to read this RCON installation's changelogs. Aurora also provides a link at the bottom of its main navigation. The current version is labelled; the history contains earlier stable releases. Search covers titles, versions and notes.

### After deployment

A new GitHub release only appears when **frontend and backend run the same published version**. An incomplete rollout, development build or unknown version shows an explanation instead. A direct link to a newer version cannot bypass this check. The history is not a log of when earlier versions were actually installed.

### What's new?

Selected releases include a short overview spotlight with one main feature and up to two further improvements. It uses your theme and language; **DE / EN** changes the application language. It never opens over a form or another dialog you are using.

The spotlight appears once per account and version. This status is stored on the server and shared across devices. **Later** postpones the reminder for 24 hours until you visit the overview again. Reopen it at any time using **What's new?** in the account menu or update channel. Its status is independent of the changelog's read status. If complete German and English highlights have not been provided, the normal changelog remains available.

### Read status

**New for you** identifies the current version until you mark it as read. This browser remembers that status for your account and RCON address. Reading notes changes no settings and installs no updates.

### No GitHub account required

Notes are copied from our private repository and displayed inside RCON. Only your normal RCON sign-in is required. Repository links, external images and credentials are not loaded. Notes retain the language of the published release.`,
    },
  },
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

Nutze die Suche in der Kopfzeile, um Seiten zu finden. Im Aurora-Theme öffnet das Menü-Symbol links die Hauptnavigation; darunter liegen deine persönlichen QuickIcons.

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

Use the search in the header to find pages. In Aurora, the menu icon on the left opens the main navigation; your personal QuickIcons appear below it.

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

### Eigenes Passwort und Wiederherstellung
Unter **Benutzermenü → Passwort ändern** änderst du dein eigenes Passwort direkt im RCON. Die geltenden Passwortregeln stehen am Formular. Du bleibst in diesem Browser angemeldet; andere Browsersitzungen werden ungültig.

Über **Passwort vergessen?** auf der Anmeldung kannst du einen Link anfordern. Er gilt 30 Minuten und ist nach erfolgreicher Verwendung ungültig. Ein aktives Konto mit lokalem Passwort und einer erreichbaren E-Mail-Adresse ist Voraussetzung. Falls keine Nachricht ankommt, prüfe den Spamordner und kontaktiere die Administration. Die Antwort verrät nicht, ob eine Adresse registriert ist.

Für Administratoren: Der Mailversand muss über SMTP eingerichtet und mit **CRCON_PASSWORD_RESET_ENABLED** aktiviert werden. **CRCON_PUBLIC_URL** legt die feste HTTPS-Adresse für E-Mail-Links fest. Die SMTP-Felder stehen in **default.env**; Zugangsdaten gehören in die private **.env**. Bei Port 587 wird üblicherweise TLS, bei Port 465 SSL verwendet. Anschließend Backend-Container mit der aktualisierten Compose-Konfiguration neu erstellen. Solange die Einrichtung fehlt, zeigt die Oberfläche die Wiederherstellung als nicht verfügbar an.

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

### Your password and account recovery
Use **User menu → Change password** to update your own password within CRCON. The form shows the active password rules. You remain signed in in this browser; other browser sessions become invalid.

Use **Forgot password?** on the sign-in page to request a link. It expires after 30 minutes and becomes invalid after successful use. An active account with a local password and a reachable email address is required. Check your spam folder and contact an administrator if no message arrives. The response does not reveal whether an address is registered.

For administrators: Configure SMTP and enable **CRCON_PASSWORD_RESET_ENABLED**. **CRCON_PUBLIC_URL** fixes the HTTPS origin for email links. SMTP fields are listed in **default.env**; put credentials in your private **.env**. Port 587 typically uses TLS; port 465 uses SSL. Then recreate the backend containers with the updated Compose configuration. Until configuration is complete, the interface shows recovery as unavailable.

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
2. Wähle **Aurora** oder **Vanguard** und anschließend deinen Farbstil.
3. Im Aurora-Theme stehen sechs Farbstile zur Verfügung: Rose, Eisblau, Smaragd, Bernstein, Amethyst und Schiefer.
4. Wähle einen hellen, dunklen oder vom System gesteuerten Modus. Bei Bedarf kannst du außerdem die Farbdarstellung für Farbsehschwächen anpassen.
5. Prüfe die unmittelbare Vorschau und speichere. **Abbrechen** stellt deine vorherige Darstellung wieder her.

Die Darstellung gehört zu deinem Benutzerkonto. Falls ein älteres Backend diese Einstellungen noch nicht speichern kann, weist der Dialog auf die lokale Speicherung im Browser hin.

Im dunklen Modus wechselt das statische Hintergrundbild passend zum Farbstil. Es enthält keine Animationen. Im hellen Modus bleibt die helle Hintergrundfläche erhalten.

### QuickIcons anpassen
Im Aurora-Theme befindet sich unter den Schnellzugriffen eine gestrichelte **Anpassen**-Schaltfläche. Öffne sie, suche die gewünschten Seiten und wähle deine Favoriten. Ordne sie mit den Pfeilen nach oben oder unten und speichere die Auswahl.

QuickIcons zeigen nur Ziele an, auf die du Zugriff hast. Verliert ein Konto ein Recht, wird der betreffende Schnellzugriff ausgeblendet. Das Menü-Symbol oberhalb der Trennlinie bleibt der Zugang zur vollständigen Navigation.

### Auf kleinen Bildschirmen
Die Navigation lässt sich über das Menü-Symbol öffnen. Nicht jede Desktop-Leiste wird auf dem Smartphone dauerhaft eingeblendet. Die Dokumentation erreichst du auch über das Benutzermenü.`,
      en: `### Change theme and colour
1. Open **Appearance** from navigation or the user menu.
2. Choose **Aurora** or **Vanguard**, then select your colour style.
3. Aurora offers six colour styles: Rose, Ice blue, Emerald, Amber, Amethyst and Slate.
4. Select light, dark or system mode. You can also adjust colours for colour vision differences.
5. Review the immediate preview and save. **Cancel** restores your previous appearance.

Appearance belongs to your user account. If an older backend cannot save these preferences, the dialog explains that they will be stored locally in the browser.

In dark mode, the static background image follows the selected colour style. It contains no animation. Light mode retains its light background surface.

### Customise QuickIcons
In Aurora, use the dashed **Customise** button below the shortcuts. Search for pages and select your favourites. Move them up or down using the arrows and save the selection.

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
  fr: `### Adresse de base et authentification
Les exemples utilisent l’adresse de base de l’API de votre installation avec le chemin **/api**. Si le frontend et le backend sont séparés, utilisez l’adresse configurée du backend.

Pour une intégration, un administrateur autorisé crée une **clé API** et l’attribue à un utilisateur. Les clés doivent contenir au moins 32 caractères ; utilisez une valeur aléatoire et conservez l’original en sécurité. Envoyez-la dans **Authorization: Bearer VOTRE_CLE_API**. Les droits du compte associé s’appliquent. Stockez la clé dans une variable d’environnement protégée, jamais dans une URL ou du code frontend public.

Dans le navigateur, CRCON utilise une session authentifiée. Les requêtes de modification avec cookie de session nécessitent généralement le jeton CSRF correspondant, issu du cookie **csrftoken**, dans l’en-tête **X-CSRFToken**. L’application s’en charge. Les intégrations externes devraient utiliser l’authentification Bearer sans cookie de session.

### Deux premières requêtes
La première requête nécessite **api.can_view_get_status**, la seconde **api.can_view_recent_logs**. Toutes deux lisent des données ; le second point d’accès accepte aussi POST à cette fin.
${readExamples}
### Paramètres et réponses
Transmettez les paramètres GET dans la chaîne de requête. Les clés répétées sont interprétées comme une liste par les points d’accès RCON. POST/PUT acceptent généralement un objet JSON avec **Content-Type: application/json** ; les téléchargements vers le serveur ont leurs propres formats. Transmettez les identifiants des joueurs sous forme de chaînes.

Une réponse JSON type contient **result**, **command**, **arguments**, **failed**, **error** et **version**. Vérifiez le statut HTTP ainsi que **failed** et **error**. Les types de retour de la référence décrivent la valeur contenue dans **result**. Les exports CSV et téléchargements peuvent différer.

### Comprendre les erreurs
| Statut | Signification / étape suivante |
| --- | --- |
| 400 | Vérifiez les champs et valeurs ; l’erreur explique souvent la cause. |
| 401 | Authentification ou clé API manquante ou refusée. |
| 403 | Échec d’une vérification de droit ou CSRF. Vérifiez l’erreur et la méthode d’authentification. |
| 404 / 405 | Comparez le chemin ou la méthode HTTP à la référence de ce backend. |
| 429 | Limite de requêtes atteinte ; augmentez l’intervalle entre les requêtes. |
| 500 / 504 | Erreur backend ou délai dépassé ; vérifiez l’état du serveur et ses journaux. |

### Limites de la référence générée
Les entrées proviennent de **get_api_documentation** du backend connecté. L’enregistrement fournit les méthodes et autorisations ; les signatures Python fournissent les arguments et les types. Tous les champs JSON et schémas de réponse ne sont pas nécessairement visibles. Une table d’arguments vide ne signifie pas forcément qu’aucune entrée n’est requise. Une liste d’autorisations vide ne signifie pas non plus que l’accès anonyme est possible. Les descriptions fournies par le serveur peuvent être en allemand ou en anglais ; les notes techniques supplémentaires conservent leur langue d’origine. Les anciens backends peuvent ne fournir que ces notes.`,
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
