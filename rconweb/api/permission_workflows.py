"""UI-only permission bundles. Never grant, migrate or enforce permissions here.

Explicit page bundles are verified against endpoint declarations in tests. An
unavailable prerequisite disables a bundle instead of suggesting partial access.
"""
from .permission_help import RESOURCES, permission_help
from .permission_presets import LIVE_READ, OBSERVE


CONFIG_TITLES_EN = {
    "camera_config": "Admin camera notifications",
    "real_vip_config": "VIP rules",
    "votekick_autotoggle_config": "Automatic vote-kick settings",
    "auto_mod_level_config": "Automod: player levels",
    "auto_mod_no_leader_config": "Automod: squads without a leader",
    "auto_mod_seeding_config": "Automod: seeding",
    "auto_mod_solo_tank_config": "Automod: solo tanks",
    "tk_ban_on_connect_config": "Teamkill bans on joining",
    "expired_vip_config": "Expired VIP access",
    "server_name_change_config": "Server name at hosting provider",
    "log_line_discord_webhook_config": "Discord: log events",
    "name_kick_config": "Automatic player-name checks",
    "rcon_connection_settings_config": "Game-server connection",
    "rcon_server_settings_config": "RCON general settings",
    "scorebot_config": "Discord: scoreboard",
    "steam_config": "Steam integration",
    "vac_game_bans_config": "VAC and game bans",
    "admin_pings_discord_webhooks_config": "Discord: admin reports",
    "audit_discord_webhooks_config": "Discord: admin actions",
    "camera_discord_webhooks_config": "Discord: admin camera",
    "chat_discord_webhooks_config": "Discord: game chat",
    "kills_discord_webhooks_config": "Discord: kills and teamkills",
    "watchlist_discord_webhooks_config": "Discord: watchlist",
    "chat_commands_config": "Player chat commands",
    "rcon_chat_commands_config": "RCON chat commands",
    "log_stream_config": "Live log stream",
    "seed_vip_config": "Seeding VIP rewards",
    "watch_killrate_config": "Kill-rate monitoring",
}


# id, DE/EN title, read codenames, optional (DE, EN, additional codenames) actions
WORKFLOWS = (
    ("console", "Konsolen-Admins", "Console admins",
     {"can_view_admins", "can_view_admin_ids", "can_view_admin_groups"}, (
         ("Rolle vergeben", "Assign role", {"can_add_admin_roles"}),
         ("Rolle entziehen", "Remove role", {"can_remove_admin_roles"}),
     )),
    ("live", "Live-Ansicht & Teams", "Live view & teams", LIVE_READ, ()),
    ("players", "Spielerakten & Protokolle", "Player records & logs", OBSERVE, (
        ("Support: Nachrichten, Kommentare & Beobachtung", "Support: messages, comments & watchlist",
         {"can_message_players", "can_add_player_comments", "can_add_player_watch", "can_remove_player_watch"}),
        ("Spieler kicken", "Kick players", {"can_kick_players"}),
        ("Spieler bestrafen", "Punish players", {"can_punish_players"}),
        ("Spieler temporär sperren", "Temporarily ban players", {"can_temp_ban_players"}),
        ("Spieler dauerhaft sperren", "Permanently ban players", {"can_perma_ban_players"}),
    )),
    ("vips", "VIP-Liste", "VIP list", {"can_view_vip_ids"}, (
        ("VIP vergeben", "Grant VIP", {"can_add_vip"}),
        ("VIP entziehen", "Remove VIP", {"can_remove_vip"}),
        ("VIP-Liste exportieren", "Export VIP list", {"can_download_vip_list"}),
    )),
    ("blacklists", "Sperrlisten", "Blacklists", {"can_view_blacklists"}, (
        ("Sperrlisteneinträge verwalten", "Manage blacklist entries", {"can_add_blacklist_records", "can_change_blacklist_records", "can_delete_blacklist_records"}),
        ("Spieler entsperren", "Unban players", {"can_delete_blacklist_records", "can_remove_temp_bans", "can_remove_perma_bans"}),
    )),
    ("votemap", "Kartenabstimmung", "Map voting",
     {"can_view_votemap_status", "can_view_votemap_config", "can_view_map_whitelist", "can_view_all_maps"}, (
         ("Abstimmungsregeln ändern", "Change voting rules", {"can_change_votemap_config"}),
         ("Kartenauswahl ändern", "Change map whitelist", {"can_set_map_whitelist", "can_reset_map_whitelist"}),
     )),
    ("rotation", "Kartenrotation", "Map rotation",
     {"can_view_map_rotation", "can_view_all_maps", "can_view_current_map_sequence", "can_view_map_shuffle_enabled"}, (
         ("Rotation bearbeiten", "Edit rotation", {"can_add_map_to_rotation", "can_add_maps_to_rotation", "can_remove_map_from_rotation", "can_remove_maps_from_rotation"}),
     )),
    ("templates", "Nachrichtenvorlagen", "Message templates", {"can_view_message_templates"}, (
        ("Vorlagen bearbeiten", "Edit templates", {"can_add_message_templates", "can_edit_message_templates", "can_delete_message_templates"}),
    )),
    ("broadcast", "Automatische Servernachrichten", "Automatic server messages",
     {"can_view_broadcast_message", "can_view_auto_broadcast_config", "can_view_message_templates"}, (
         ("Nachrichtenregeln bearbeiten", "Edit message rules", {"can_change_auto_broadcast_config"}),
     )),
    ("autobalancer", "Autobalancer", "Autobalancer", {"can_view_autobalancer"}, (
        ("Eingriffe ausführen", "Execute interventions", {"can_execute_autobalancer"}),
        ("Automatik konfigurieren", "Configure automation", {"can_change_autobalancer_config"}),
    )),
    ("services", "Hintergrunddienste", "Background services", {"can_view_available_services"}, (
        ("Dienste starten / stoppen", "Start / stop services", {"can_toggle_services"}),
    )),
)


WORKFLOW_TITLES_FR = {
    "console": "Administrateurs du jeu", "live": "Vue en direct et équipes", "players": "Fiches des joueurs et journaux",
    "vips": "Liste VIP", "blacklists": "Listes de blocage", "votemap": "Vote de carte", "rotation": "Rotation des cartes",
    "templates": "Modèles de messages", "broadcast": "Messages automatiques du serveur", "autobalancer": "Équilibreur d'équipes", "services": "Services en arrière-plan",
}
CONFIG_TITLES_FR = {
    "camera_config": "Notifications de la caméra administrateur", "real_vip_config": "Règles VIP",
    "votekick_autotoggle_config": "Paramètres automatiques d'expulsion par vote", "auto_mod_level_config": "Modération automatique : niveaux des joueurs",
    "auto_mod_no_leader_config": "Modération automatique : escouades sans chef", "auto_mod_seeding_config": "Modération automatique : remplissage",
    "auto_mod_solo_tank_config": "Modération automatique : chars en solo", "tk_ban_on_connect_config": "Bannissements pour tirs alliés à la connexion",
    "expired_vip_config": "Accès VIP expirés", "server_name_change_config": "Nom du serveur chez l'hébergeur",
    "log_line_discord_webhook_config": "Discord : événements du journal", "name_kick_config": "Vérification automatique des noms de joueurs",
    "rcon_connection_settings_config": "Connexion au serveur de jeu", "rcon_server_settings_config": "Paramètres généraux RCON",
    "scorebot_config": "Discord : tableau des scores", "steam_config": "Intégration Steam", "vac_game_bans_config": "Bannissements VAC et de jeu",
    "admin_pings_discord_webhooks_config": "Discord : signalements aux administrateurs", "audit_discord_webhooks_config": "Discord : actions des administrateurs",
    "camera_discord_webhooks_config": "Discord : caméra administrateur", "chat_discord_webhooks_config": "Discord : discussion du jeu",
    "kills_discord_webhooks_config": "Discord : éliminations et tirs alliés", "watchlist_discord_webhooks_config": "Discord : liste de surveillance",
    "chat_commands_config": "Commandes de discussion des joueurs", "rcon_chat_commands_config": "Commandes de discussion RCON", "log_stream_config": "Flux de journal en direct",
    "seed_vip_config": "Récompenses VIP de remplissage", "watch_killrate_config": "Surveillance du taux d'éliminations",
}
ACTION_TITLES_FR = {
    "View": "Consulter", "Assign role": "Attribuer un rôle", "Remove role": "Retirer un rôle",
    "Support: messages, comments & watchlist": "Assistance : messages, commentaires et surveillance", "Kick players": "Expulser des joueurs", "Punish players": "Sanctionner des joueurs",
    "Temporarily ban players": "Bannir temporairement des joueurs", "Permanently ban players": "Bannir définitivement des joueurs",
    "Grant VIP": "Attribuer le VIP", "Remove VIP": "Retirer le VIP", "Export VIP list": "Exporter la liste VIP",
    "Manage blacklist entries": "Gérer les entrées de liste de blocage", "Unban players": "Lever des bannissements",
    "Change voting rules": "Modifier les règles de vote", "Change map whitelist": "Modifier les cartes autorisées",
    "Edit rotation": "Modifier la rotation", "Edit templates": "Modifier les modèles", "Edit message rules": "Modifier les règles de messages",
    "Execute interventions": "Exécuter les interventions", "Configure automation": "Configurer l'automatisation", "Start / stop services": "Démarrer ou arrêter les services", "Edit settings": "Modifier les paramètres",
}


def permission_workflows(permissions, german=True, language=None):
    available = {p.codename: p for p in permissions
                 if p.content_type.app_label == "api" and p.content_type.model == "rconuser"}
    definitions = list(WORKFLOWS)
    # Matching config read/write permissions are discoverable together. Complex
    # multi-panel pages above are explicitly enumerated instead.
    for resource, (title, _, _) in RESOURCES.items():
        if not resource.endswith("_config") or resource in {"votemap_config", "auto_broadcast_config"}:
            continue
        read, change = f"can_view_{resource}", f"can_change_{resource}"
        if read not in available:
            continue
        english = CONFIG_TITLES_EN.get(resource, available[read].name.removeprefix("Can view ").removeprefix("the "))
        definitions.append((resource, title, english, {read}, (
            ("Einstellungen bearbeiten", "Edit settings", {change}),
        ) if change in available else ()))
    result = []
    for key, de, en, read, actions in definitions:
        if not set(read) & available.keys():
            continue
        bundles = []
        for index, (title_de, title_en, codes) in enumerate([
            ("Anzeigen", "View", set(read)),
            *((de, en, set(read) | set(extra)) for de, en, extra in actions),
        ]):
            bundles.append({
                "id": f"{key}:{index}", "title": ACTION_TITLES_FR.get(title_en, title_en) if language == "fr" else title_de if german else title_en,
                "kind": "read" if index == 0 else "action",
                "permissions": [str(available[c].pk) for c in sorted(codes) if c in available],
                "unavailable": sorted(set(codes) - available.keys()),
                "sensitive": any(permission_help(available[c], german)["sensitive"] for c in codes if c in available),
            })
        result.append({"id": key, "title": WORKFLOW_TITLES_FR.get(key, CONFIG_TITLES_FR.get(key, en)) if language == "fr" else de if german else en, "bundles": bundles})
    return result
