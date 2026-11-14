"""Explicit, editable starting points for group forms, never automatic grants.

Keep allowlists explicit: new permissions must not silently enter a role.
They only reference choices already available to Django's permission field.
"""

LIVE_READ = frozenset({
    "can_view_get_status", "can_view_gamestate", "can_view_current_map",
    "can_view_next_map", "can_view_player_slots", "can_view_round_time_remaining",
    "can_view_team_objective_scores", "can_view_all_maps", "can_view_get_players",
    "can_view_playerids", "can_view_player_info", "can_view_detailed_player_info",
    "can_view_detailed_players", "can_view_team_view", "can_view_recent_logs",
    "can_view_structured_logs",
})
OBSERVE = LIVE_READ | {
    "can_view_game_logs", "can_view_historical_logs", "can_view_player_history",
    "can_view_player_profile", "can_view_player_comments", "can_view_player_bans",
    "can_view_player_messages", "can_view_message_templates",
    "can_view_standard_punishment_messages",
    # The player records loader calls get_bans, which requires BOTH read rights.
    "can_view_temp_bans", "can_view_perma_bans", "can_view_blacklists",
}
SUPPORT = OBSERVE | {
    "can_message_players", "can_add_player_comments",
    "can_add_player_watch", "can_remove_player_watch",
}
MODERATE = SUPPORT | {
    "can_kick_players", "can_punish_players", "can_temp_ban_players",
    "can_perma_ban_players", "can_remove_temp_bans", "can_remove_perma_bans",
    "can_switch_players_on_death", "can_switch_players_immediately",
    "can_remove_player_from_squad", "can_disband_squad",
    "can_flag_player", "can_unflag_player",
    # unblacklist_player requires delete-record plus both unban rights.
    # Managing records does not grant control over the blacklist containers.
    "can_add_blacklist_records", "can_change_blacklist_records",
    "can_delete_blacklist_records",
    "can_view_autobalancer", "can_execute_autobalancer",
}
OPERATE = LIVE_READ | {
    "can_view_map_rotation", "can_view_map_whitelist",
    "can_view_current_map_sequence", "can_view_votemap_status",
    "can_view_map_shuffle_enabled", "can_change_map_shuffle_enabled",
    "can_change_current_map", "can_add_map_to_rotation", "can_add_maps_to_rotation",
    "can_remove_map_from_rotation", "can_remove_maps_from_rotation",
    "can_add_map_to_whitelist", "can_add_maps_to_whitelist",
    "can_remove_map_from_whitelist", "can_remove_maps_from_whitelist",
    "can_set_map_whitelist", "can_reset_map_whitelist",
    "can_set_match_timer", "can_remove_match_timer",
    "can_set_warmup_timer", "can_remove_warmup_timer",
    "can_change_game_layout", "can_set_dynamic_weather_enabled",
    "can_view_votemap_config", "can_change_votemap_config",
    "can_add_map_to_votemap", "can_remove_map_from_votemap",
    "can_set_votemap_winner", "can_add_votemap_vote",
    "can_reset_votemap_state", "can_send_votemap_reminder",
    "can_view_broadcast_message", "can_change_broadcast_message",
    # The campaigns page uses the config/status API, not just legacy broadcast.
    "can_view_auto_broadcast_config", "can_change_auto_broadcast_config",
    "can_message_players", "can_view_message_templates",
    "can_view_welcome_message", "can_change_welcome_message",
    "can_view_standard_broadcast_messages", "can_view_standard_welcome_messages",
}

PRESETS = (
    ("observer", "Nur lesen", "Read only",
     "Live-Daten, Spielerakten, Bannlisten und historische Spielprotokolle ansehen.",
     "Read live data, player profiles, ban lists and historical game logs.", OBSERVE),
    ("support", "Support", "Support",
     "Zusätzlich Nachrichten senden, Kommentare schreiben und Spieler beobachten.",
     "Also send messages, add player comments and manage the watchlist.", SUPPORT),
    ("moderator", "Moderator", "Moderator",
     "Spieler moderieren: Support-Rechte, Kicks, Bestrafungen, Team- und Truppaktionen, temporäre und permanente Banns, Entbannen, Blacklist-Einträge und Markierungen. Autobalancer-Vorschläge prüfen und ausführen.",
     "Moderate players: support permissions, kicks, punishment, team and squad actions, temporary and permanent bans, unbanning, blacklist records and flags. Review and execute autobalancer proposals.", MODERATE),
    ("operations", "Spielbetrieb", "Match operations",
     "Den Spielbetrieb steuern: Kartenwechsel, Rotation und Zufallsreihenfolge, Kartenziele, Wetter, Runden- und Aufwärmzeit sowie Kartenabstimmungen konfigurieren und bedienen. Willkommensnachrichten, Broadcasts und Nachrichtenkampagnen verwalten. Für Spielersanktionen zusätzlich „Moderator“ übernehmen.",
     "Run matches: manage map changes, rotation and shuffle, objectives, weather, match and warmup timers, and map voting. Manage welcome messages, broadcasts and message campaigns. Also apply Moderator for player sanctions.", OPERATE),
)


PRESETS_FR = {
    "observer": ("Consultation uniquement", "Consulter les données en direct, les profils des joueurs, les listes de bannissement et les anciens journaux de jeu."),
    "support": ("Assistance", "Envoyer aussi des messages, ajouter des commentaires et gérer la liste de surveillance."),
    "moderator": ("Modérateur", "Modérer les joueurs : droits d'assistance, expulsions, sanctions, actions sur les équipes et escouades, bannissements temporaires et permanents, levée des bannissements, entrées de liste de blocage et signalements. Examiner et exécuter les propositions de l'équilibreur."),
    "operations": ("Gestion des parties", "Gérer les changements et la rotation des cartes, l'ordre aléatoire, les objectifs, la météo, les minuteries et les votes de cartes. Gérer les messages de bienvenue et les campagnes de messages. Ajouter le rôle Modérateur pour les sanctions de joueurs."),
}


def permission_presets(permissions, german=True, language=None):
    available = {
        permission.codename: str(permission.pk)
        for permission in permissions
        if permission.content_type.app_label == "api" and permission.content_type.model == "rconuser"
    }
    result = []
    for key, de, en, description_de, description_en, codes in PRESETS:
        ids = [available[code] for code in sorted(codes) if code in available]
        if ids:
            title, description = PRESETS_FR[key] if language == "fr" else (de, description_de) if german else (en, description_en)
            result.append({"id": key, "title": title,
                           "description": description,
                           "permissions": ids})
    return result
