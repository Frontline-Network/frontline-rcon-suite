"""Customer-facing questions; authorization remains in Django's permission field."""

SECTIONS = (
    ("players", "Spieler betreuen", "Support players",
     "Spieler und Teams ansehen, Meldungen prüfen und bei Bedarf moderieren.", "View players and teams, investigate reports and optionally moderate."),
    ("maps", "Karten & Spielablauf", "Maps & matches",
     "Kartenrotation und Kartenabstimmungen betreuen.", "Manage map rotation and map voting."),
    ("vip", "VIP & Seeding-Belohnung", "VIP & seeding rewards",
     "VIP-Zugänge ansehen, vergeben und die Belohnungsregeln einstellen.", "View or grant VIP access and configure reward rules."),
    ("messages", "Nachrichten", "Messages",
     "Vorlagen und automatische Servernachrichten betreuen.", "Manage templates and automatic server messages."),
    ("automation", "Automatische Moderation", "Automatic moderation",
     "Autobalancer, Levelregeln und weitere automatische Maßnahmen einstellen.", "Configure the autobalancer, level rules and other automated actions."),
    ("console", "Konsolen-Admins", "Console admins",
     "Admins im Spiel ansehen oder deren Spielserver-Rollen verwalten. Das sind keine RCON-Benutzerrollen.", "View in-game admins or manage their game-server roles. These are not RCON user roles."),
    ("technical", "Server & Anbindungen", "Server & integrations",
     "Technische Einstellungen, Hintergrunddienste und Discord-Verbindungen. Nur für erfahrene Administratoren.", "Technical settings, background services and Discord connections. For experienced administrators."),
)

# Plain-language explanations of the visible capability, not invented policy.
HELP = {
    "console": ("Darf die Rolle sehen, wer auf dem Spielserver Admin ist? Du entscheidest danach getrennt, ob sie solche Rollen vergeben oder entziehen darf.", "May this role see who is an admin on the game server? You separately choose whether it may assign or remove those roles."),
    "live": ("Zeigt verbundene Spieler, Teams, Karte, Spielstand und aktuelle Spielereignisse. Damit lassen sich noch keine Spieler bestrafen.", "Shows connected players, teams, map, score and recent game events. This does not allow player punishment."),
    "players": ("Zeigt Spielerakten, frühere Ereignisse, Kommentare, gesendete Nachrichten und Sperren. Zusätzliche Aktionen wie Nachrichten oder Kicks wählst du einzeln aus.", "Shows player records, past events, comments, sent messages and bans. Select additional actions such as messages or kicks individually."),
    "blacklists": ("Zeigt Sperrlisten und deren Einträge. Einsehen ist etwas anderes als Spieler sperren oder bestehende Sperren aufheben.", "Shows blacklists and their entries. Viewing them is separate from banning players or lifting existing bans."),
    "vips": ("Zeigt, wer VIP-Zugang hat und wann dieser endet. VIP vergeben, entziehen und exportieren sind getrennte Freigaben.", "Shows who has VIP access and when it expires. Granting, removing and exporting VIP access are separate choices."),
    "rotation": ("Zeigt die Kartenfolge und verfügbaren Karten. Bearbeiten erlaubt, Karten zur Rotation hinzuzufügen oder daraus zu entfernen.", "Shows the map sequence and available maps. Editing allows adding maps to or removing maps from the rotation."),
    "votemap": ("Zeigt Stand und Regeln der Kartenabstimmung. Regeln oder die freigegebenen Karten ändern darf die Rolle nur mit deiner zusätzlichen Freigabe.", "Shows map-voting status and rules. Changing rules or allowed maps needs your additional approval."),
    "templates": ("Zeigt gespeicherte Nachrichtenvorlagen. Bearbeiten umfasst das Anlegen, Ändern und Löschen von Vorlagen; es verschickt noch keine Nachricht.", "Shows saved message templates. Editing includes creating, changing and deleting templates; it does not send a message."),
    "broadcast": ("Zeigt automatische Servernachrichten und ihren Versandstatus. Änderungen können beeinflussen, welche Nachrichten Spieler erhalten.", "Shows automatic server messages and their delivery status. Changes can affect which messages players receive."),
    "autobalancer": ("Zeigt Auswertungen und bisherige Eingriffe. Teamwechsel ausführen und die Automatik einstellen sind getrennte Entscheidungen.", "Shows assessments and past interventions. Executing team moves and configuring automation are separate choices."),
    "services": ("Zeigt den Zustand der Hintergrunddienste. Starten oder Stoppen kann Automatikfunktionen unterbrechen.", "Shows background-service status. Starting or stopping services can interrupt automated features."),
}


def wizard_metadata(workflows, german=True):
    """Annotate the existing tested bundles; do not create new grants."""
    from .permission_help import RESOURCES
    result = []
    for section_id, de, en, help_de, help_en in SECTIONS:
        members = []
        for workflow in workflows:
            key = workflow['id']
            category = RESOURCES.get(key, ('', '', 'system'))[2]
            if key in {'live', 'players', 'blacklists'}: target = 'players'
            elif key in {'rotation', 'votemap'}: target = 'maps'
            elif key == 'vips' or category == 'vip': target = 'vip'
            elif key in {'templates', 'broadcast'} or category == 'messages': target = 'messages'
            elif key == 'autobalancer' or category == 'automation': target = 'automation'
            elif key == 'console': target = 'console'
            else: target = 'technical'
            if target != section_id:
                continue
            explanation = HELP.get(key)
            workflow['explanation'] = explanation[0 if german else 1] if explanation else (
                f"Hier geht es um {RESOURCES[key][1]}. Ansehen erlaubt noch keine Änderung. Bearbeiten kann das Verhalten des Servers verändern."
                if german else f"Review the settings for {workflow['title']}. Viewing does not allow changes. Editing can change how the server behaves.")
            members.append(key)
        if members:
            result.append({'id': section_id, 'title': de if german else en, 'description': help_de if german else help_en, 'workflows': members})
    return result
