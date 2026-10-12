"""Operator-facing explanations of the permissions declared in api.models.

This is presentation metadata, never an authorization policy or role preset.
Unknown extension permissions retain their real name instead of guessing scope.
"""

CATEGORIES = {
    "players": ("Spieler & Moderation", "Players & moderation"),
    "maps": ("Karten & Spielablauf", "Maps & match settings"),
    "automation": ("Automatisierung", "Automation"),
    "vip": ("VIP & Seeding", "VIP & seeding"),
    "messages": ("Nachrichten & Vorlagen", "Messages & templates"),
    "logs": ("Protokolle & Statistiken", "Logs & statistics"),
    "integrations": ("Integrationen", "Integrations"),
    "system": ("Server & Betrieb", "Server & operations"),
    "accounts": ("Konten & Zugänge", "Accounts & access"),
    "tactical": ("Taktische Daten", "Tactical data"),
    "mobile": ("Mobile Geräte & Meldungen", "Mobile devices & incidents"),
    "other": ("Weitere Rechte", "Other permissions"),
    "internal": ("Interne Systemrechte · nur für Wartung", "Internal system permissions · maintenance only"),
}

# resource: readable title, the concrete object being read/changed, category
RESOURCES = {
    "auto_broadcast_config": ("Automatische Broadcasts", "die Zeitpläne und Regeln automatischer Servernachrichten", "messages"),
    "auto_settings": ("Automatische Serverprofile", "die Bedingungen und Werte automatisch angewendeter Serverprofile", "automation"),
    "autobalance_enabled": ("Automatischer Teamausgleich", "den Aktivierungszustand des spielinternen Teamausgleichs", "maps"),
    "autobalance_threshold": ("Teamausgleich: Grenzwert", "den erlaubten Unterschied zwischen den Teamgrößen", "maps"),
    "broadcast_message": ("Broadcast-Nachricht", "den aktuellen Nachrichtentext des Servers", "messages"),
    "camera_config": ("Admin-Kamera: Hinweise", "die Benachrichtigungen beim Betreten der Admin-Kamera", "messages"),
    "current_map": ("Aktuelle Karte", "die momentan laufende Karte", "maps"),
    "discord_webhooks": ("Discord-Webhooks", "die konfigurierten Discord-Ziele und Webhook-Adressen", "integrations"),
    "idle_autokick_time": ("Kick bei Inaktivität", "die Wartezeit bis zum automatischen Kick inaktiver Spieler", "maps"),
    "max_ping_autokick": ("Kick bei hohem Ping", "die Ping-Grenze für automatische Kicks", "maps"),
    "profanities": ("Chat-Wortfilter", "die vom Spiel zensierten Wörter", "players"),
    "queue_length": ("Warteschlange", "die maximale Zahl wartender Spieler", "maps"),
    "real_vip_config": ("VIP-Regeln", "die Einstellungen der VIP-Verwaltung", "vip"),
    "server_name": ("Servername", "den angezeigten Namen des Spielservers", "system"),
    "shared_standard_messages": ("Geteilte Standardtexte", "die gemeinsam verwendeten Nachrichtenvorlagen", "messages"),
    "team_switch_cooldown": ("Teamswechsel: Wartezeit", "die Wartezeit zwischen freiwilligen Teamwechseln", "maps"),
    "vip_slots": ("Reservierte VIP-Plätze", "die Anzahl reservierter VIP-Slots", "vip"),
    "votekick_autotoggle_config": ("Votekick-Automatik", "die Regeln zur automatischen Aktivierung von Abstimmungskicks", "automation"),
    "votekick_enabled": ("Votekicks", "den Aktivierungszustand der Kick-Abstimmungen im Spiel", "maps"),
    "votekick_threshold": ("Votekick: Stimmenzahl", "die erforderlichen Stimmen für einen Abstimmungskick", "maps"),
    "votemap_config": ("Kartenabstimmung: Regeln", "die Auswahl-, Abstimmungs- und Nachrichtenregeln von Votemap", "maps"),
    "welcome_message": ("Willkommensnachricht", "den beim Beitritt angezeigten Begrüßungs- oder Regeltext", "messages"),
    "admin_groups": ("Konsolen-Admins: verfügbare Rollen", "die verfügbaren Spielserver-Adminrollen. Zum Öffnen der Seite werden zusätzlich Menü-Zugriff und Adminliste benötigt", "accounts"),
    "admin_ids": ("Konsolen-Admins: Liste und Spieler-IDs", "Namen, Spieler-IDs und Rollen eingetragener Konsolen-Admins. Dieses Recht wird zum Laden der Adminliste benötigt", "accounts"),
    "admins": ("Konsolen-Admins: Menü-Zugriff", "den Konsolen-Adminbereich. Zum Laden der Seite werden zusätzlich die Rechte für die Adminliste und die verfügbaren Rollen benötigt", "accounts"),
    "all_maps": ("Verfügbare Karten", "die vollständige Auswahl spielbarer Karten", "maps"),
    "audit_logs": ("Admin-Aktionsprotokoll", "die protokollierten Verwaltungsaktionen und ihre Ergebnisse", "logs"),
    "audit_logs_autocomplete": ("Aktionsprotokoll: Suchvorschläge", "die Suchvorschläge zum Filtern des Admin-Aktionsprotokolls", "logs"),
    "available_services": ("Dienste", "den Zustand der Hintergrunddienste wie Automod", "system"),
    "connection_info": ("RCON-Verbindung", "die Verbindungsinformationen von CRCON zum Spielserver", "system"),
    "date_scoreboard": ("Statistik nach Datum", "die nach Datum aufgeschlüsselten Spielstatistiken", "logs"),
    "detailed_player_info": ("Spielerdetails", "Spieler-ID, Rolle, Ausrüstung, Trupp und weitere Live-Spielerdetails", "players"),
    "game_logs": ("Spielprotokolle", "die ursprünglichen Protokollzeilen des Spielservers", "logs"),
    "gamestate": ("Aktueller Spielzustand", "den aktuellen Zustand der Partie", "maps"),
    "get_players": ("Verbundene Spieler", "Namen, Spieler-IDs, VIP-Status und Sitzungen verbundener Spieler", "players"),
    "get_status": ("Serverstatus", "Servername, laufende Karte und Spielerzahl", "system"),
    "historical_logs": ("Ältere Protokolle", "die gespeicherten Protokolle vergangener Ereignisse", "logs"),
    "ingame_admins": ("Admins im Spiel", "die aktuell auf dem Spielserver anwesenden Admins", "accounts"),
    "map_rotation": ("Kartenrotation", "die eingestellte Reihenfolge der Karten", "maps"),
    "map_whitelist": ("Votemap-Kartenauswahl", "die für Kartenabstimmungen freigegebenen Karten", "maps"),
    "next_map": ("Nächste Karte", "die als Nächstes vorgesehene Karte", "maps"),
    "online_admins": ("Angemeldete CRCON-Admins", "die aktuell in CRCON angemeldeten Admins", "accounts"),
    "online_console_admins": ("Anwesende Konsolen-Admins", "die Spielernamen verbundener Spielserver-Admins", "accounts"),
    "other_crcon_servers": ("Weitere Server", "die anderen Server derselben CRCON-Installation", "system"),
    "perma_bans": ("Dauerhafte Banns", "die dauerhaft gesperrten Spieler", "players"),
    "player_bans": ("Sperren eines Spielers", "die temporären und dauerhaften Banns eines bestimmten Spielers", "players"),
    "player_comments": ("Spielerkommentare", "die internen Kommentare in Spielerakten", "players"),
    "player_history": ("Spielerhistorie", "die gespeicherten Spielerakten im Bereich Historie", "players"),
    "player_info": ("Spieler-Stammdaten", "Name, Spieler-ID, Land und bekannte Steam-Sperren", "players"),
    "player_messages": ("Gesendete Spielernachrichten", "die an Spieler versendeten Nachrichten", "messages"),
    "player_profile": ("Spielerprofil", "die ausführliche Profilseite eines Spielers", "players"),
    "player_slots": ("Spielerplätze", "die aktuelle und maximal erlaubte Spielerzahl", "system"),
    "playerids": ("Spieler-IDs", "Namen und Spieler-IDs der verbundenen Spieler", "players"),
    "players": ("Spielerliste", "die Liste aller aktuell verbundenen Spieler", "players"),
    "recent_logs": ("Live-Protokoll", "die neuesten Spielereignisse in der Live-Ansicht", "logs"),
    "round_time_remaining": ("Verbleibende Rundenzeit", "die Restzeit der aktuellen Runde", "maps"),
    "structured_logs": ("Aufbereitete Protokolle", "die nach Ereignistyp aufgeschlüsselten Spielprotokolle", "logs"),
    "team_objective_scores": ("Team-Punktestand", "die von den Teams gehaltenen Ziele und ihren Punktestand", "maps"),
    "detailed_players": ("Detaillierte Spielerliste", "die ausführlichen Live-Daten aller verbundenen Spieler", "players"),
    "team_view": ("Team- und Truppübersicht", "die nach Team und Trupp gegliederten Spielerdetails", "players"),
    "temp_bans": ("Temporäre Banns", "die zeitlich befristeten Spielersperren", "players"),
    "vip_count": ("Anwesende VIPs", "die Zahl aktuell verbundener VIP-Spieler", "vip"),
    "vip_ids": ("VIP-Liste", "die VIP-Spieler und die Ablaufzeit ihrer VIP-Zugänge", "vip"),
    "votemap_status": ("Kartenabstimmung: Stand", "die Kandidaten, Stimmen und Ergebnisse der Kartenabstimmung", "maps"),
    "current_map_sequence": ("Gemischte Kartenfolge", "die aktuelle, vom Map-Shuffle erzeugte Kartenfolge", "maps"),
    "map_shuffle_enabled": ("Kartenrotation mischen", "die Aktivierung des zufälligen Mischens der Kartenrotation", "maps"),
    "auto_mod_level_config": ("Automod: Spielerlevel", "die Levelgrenzen, Ausnahmen und Maßnahmen der Level-Automod", "automation"),
    "auto_mod_no_leader_config": ("Automod: Truppführung", "die Erkennung und Maßnahmen für Trupps ohne Führung", "automation"),
    "auto_mod_seeding_config": ("Automod: Seeding", "die während des Seedings geltenden Regeln und Maßnahmen", "automation"),
    "auto_mod_solo_tank_config": ("Automod: Solo-Panzer", "die Erkennung und Maßnahmen gegen allein besetzte Panzer", "automation"),
    "tk_ban_on_connect_config": ("Teamkill-Sperren beim Beitritt", "die Prüfung und Sperrregeln für Teamkiller beim Verbindungsaufbau", "automation"),
    "expired_vip_config": ("Abgelaufene VIPs", "die Regeln zum Verarbeiten abgelaufener VIP-Zugänge", "vip"),
    "server_name_change_config": ("Servername beim Hoster", "die Hoster-/SFTP-Einstellungen für Servernamensänderungen einschließlich Zugangsdaten", "integrations"),
    "log_line_discord_webhook_config": ("Discord: Protokollereignisse", "die Discord-Ziele und Regeln für Protokollmeldungen", "integrations"),
    "name_kick_config": ("Automatische Namensprüfung", "die Namensfilter, Ausnahmen und Kick-Regeln", "automation"),
    "rcon_connection_settings_config": ("Spielserver-Verbindung", "die RCON-Verbindungs- und Pool-Einstellungen", "system"),
    "rcon_server_settings_config": ("CRCON-Grundeinstellungen", "die Identität, Links, Aktualisierungsraten und Grundeinstellungen dieser CRCON-Instanz", "system"),
    "scorebot_config": ("Discord: Scoreboard", "die Veröffentlichung von Spielständen in Discord", "integrations"),
    "standard_broadcast_messages": ("Broadcast-Vorlagen", "die gemeinsam gespeicherten Broadcast-Texte", "messages"),
    "standard_punishment_messages": ("Maßnahmen: Textvorlagen", "die gemeinsamen Begründungen für Moderationsmaßnahmen", "messages"),
    "standard_welcome_messages": ("Begrüßungsvorlagen", "die gemeinsam gespeicherten Willkommensnachrichten", "messages"),
    "steam_config": ("Steam-Anbindung", "die Einstellungen und Zugangsdaten der Steam-API-Anbindung", "integrations"),
    "vac_game_bans_config": ("VAC- und Spielbanns", "die Beitrittsprüfung auf VAC-/Game-Banns und die daraus folgenden Sperren", "automation"),
    "admin_pings_discord_webhooks_config": ("Discord: Admin-Ruf", "die Weiterleitung von Admin-Hilferufen an Discord", "integrations"),
    "audit_discord_webhooks_config": ("Discord: Admin-Aktionen", "die Discord-Benachrichtigungen zu Verwaltungsaktionen", "integrations"),
    "camera_discord_webhooks_config": ("Discord: Admin-Kamera", "die Discord-Meldungen zur Benutzung der Admin-Kamera", "integrations"),
    "chat_discord_webhooks_config": ("Discord: Spielchat", "die Spiegelung des Spielchats in Discord", "integrations"),
    "kills_discord_webhooks_config": ("Discord: Kills und Teamkills", "die Benachrichtigungen über Kills und Teamkills in Discord", "integrations"),
    "watchlist_discord_webhooks_config": ("Discord: Beobachtungsliste", "die Discord-Meldungen zu beobachteten Spielern", "integrations"),
    "chat_commands_config": ("Spieler-Chatbefehle", "die im Spiel verfügbaren Chatbefehle", "integrations"),
    "rcon_chat_commands_config": ("RCON-Chatbefehle", "die über den Spielchat ausführbaren RCON-Befehle und ihre Regeln", "integrations"),
    "log_stream_config": ("Protokollstream", "die Puffer- und Aktualisierungseinstellungen des Live-Protokolls", "logs"),
    "blacklists": ("Blacklists", "die verfügbaren Sperrlisten und ihre Einstellungen", "players"),
    "message_templates": ("Nachrichtenvorlagen", "die gemeinsam verwendeten Textvorlagen", "messages"),
    "seed_vip_config": ("VIP als Seeding-Belohnung", "die Voraussetzungen, Dauer und Nachrichten für Seeding-VIP-Belohnungen", "vip"),
    "webhook_queues": ("Webhook-Warteschlangen", "den Versandstatus und die Warteschlangen der Webhooks", "integrations"),
    "watch_killrate_config": ("Killrate überwachen", "die Zeitfenster, Grenzwerte, Ausnahmen und Meldungen der Killrate-Überwachung", "automation"),
    "autobalancer": ("Autobalancer: Status und Verlauf", "die Auswertungen und bisherigen Eingriffe des erweiterten Autobalancers", "automation"),
    "autobalancer_config": ("Autobalancer: Regeln", "die Grenzwerte, Betriebsart und Schutzregeln des erweiterten Autobalancers", "automation"),
    "population_history": ("Bevölkerungsverlauf", "die gespeicherten Spielerzahlen und Seeding-Versuche", "logs"),
    "live_map": ("Taktische Live-Karte", "die privaten Positionsdaten und ihren Verlauf auf der taktischen Karte", "tactical"),
    "live_map_cases": ("Taktische Fallbelege", "die privaten Beweisdaten taktischer Untersuchungen", "tactical"),
    "admin_incidents": ("Mobile Meldungen", "die eingegangenen Admin-Meldungen und ihren Bearbeitungsstand", "mobile"),
}

# action: title, concrete effect, category. These override generic resource verbs.
ACTIONS = {
    "edit_player_soldier": ("Soldatenprofil bearbeiten", "Ändert die Soldatendetails eines Spielers.", "players"),
    "edit_player_account": ("Spielkonto bearbeiten", "Ändert die in CRCON gespeicherten Spielkontodetails.", "players"),
    "disband_squad": ("Trupp auflösen", "Löst einen bestehenden Trupp auf dem Spielserver auf.", "players"),
    "remove_player_from_squad": ("Spieler aus Trupp entfernen", "Entfernt einen Spieler aus seinem aktuellen Trupp.", "players"),
    "set_warmup_timer": ("Aufwärmzeit festlegen", "Setzt eine benutzerdefinierte Dauer für die Aufwärmphase.", "maps"),
    "set_match_timer": ("Rundenzeit festlegen", "Setzt eine benutzerdefinierte Dauer für die Runde.", "maps"),
    "remove_match_timer": ("Rundenzeit zurücksetzen", "Entfernt die benutzerdefinierte Rundenzeit.", "maps"),
    "remove_warmup_timer": ("Aufwärmzeit zurücksetzen", "Entfernt die benutzerdefinierte Aufwärmzeit.", "maps"),
    "set_dynamic_weather_enabled": ("Dynamisches Wetter umschalten", "Aktiviert oder deaktiviert dynamisches Wetter im Spiel.", "maps"),
    "add_admin_roles": ("Konsolen-Admins: Rolle vergeben", "Erteilt einem Spieler eine Adminrolle auf dem Spielserver. Dies ist keine RCON-Benutzergruppe.", "accounts"),
    "remove_admin_roles": ("Konsolen-Admins: Rolle entziehen", "Entfernt die Adminrolle eines Spielers auf dem Spielserver. Dies ändert keine RCON-Benutzergruppe.", "accounts"),
    "add_map_to_rotation": ("Karte zur Rotation hinzufügen", "Ergänzt die Kartenrotation um eine Karte.", "maps"),
    "add_maps_to_rotation": ("Mehrere Karten zur Rotation hinzufügen", "Ergänzt die Kartenrotation um mehrere Karten in einem Vorgang.", "maps"),
    "remove_map_from_rotation": ("Karte aus Rotation entfernen", "Entfernt eine Karte aus der Kartenrotation.", "maps"),
    "remove_maps_from_rotation": ("Mehrere Karten aus Rotation entfernen", "Entfernt mehrere Karten in einem Vorgang aus der Rotation.", "maps"),
    "add_map_to_whitelist": ("Karte für Votemap freigeben", "Nimmt eine Karte in die Liste für Kartenabstimmungen auf.", "maps"),
    "add_maps_to_whitelist": ("Mehrere Karten für Votemap freigeben", "Nimmt mehrere Karten in die Votemap-Liste auf.", "maps"),
    "remove_map_from_whitelist": ("Karte aus Votemap-Liste entfernen", "Entfernt eine Karte aus der Liste zulässiger Votemap-Karten.", "maps"),
    "remove_maps_from_whitelist": ("Mehrere Votemap-Karten entfernen", "Entfernt mehrere Karten aus der Votemap-Liste.", "maps"),
    "set_map_whitelist": ("Votemap-Liste ersetzen", "Ersetzt die freigegebene Kartenauswahl für Votemap.", "maps"),
    "reset_map_whitelist": ("Votemap-Liste zurücksetzen", "Setzt die freigegebene Kartenauswahl zurück.", "maps"),
    "add_player_comments": ("Spielerkommentar schreiben", "Fügt einer Spielerakte einen internen Kommentar hinzu.", "players"),
    "add_player_watch": ("Spieler beobachten", "Setzt einen Spieler auf die Beobachtungsliste.", "players"),
    "remove_player_watch": ("Beobachtung beenden", "Entfernt einen Spieler von der Beobachtungsliste.", "players"),
    "add_vip": ("VIP vergeben", "Gewährt einem Spieler VIP-Zugang.", "vip"),
    "remove_vip": ("VIP entziehen", "Entfernt den VIP-Zugang eines Spielers.", "vip"),
    "remove_all_vips": ("Alle VIPs entfernen", "Entfernt sämtliche VIP-Einträge in einem Vorgang.", "vip"),
    "download_vip_list": ("VIP-Liste exportieren", "Lädt die VIP-Liste als Datei herunter.", "vip"),
    "upload_vip_list": ("VIP-Liste importieren", "Übernimmt VIP-Einträge aus einer hochgeladenen Datei.", "vip"),
    "ban_profanities": ("Wörter sperren", "Fügt Wörter zum spielinternen Chat-Wortfilter hinzu.", "players"),
    "unban_profanities": ("Wörter freigeben", "Entfernt Wörter aus dem spielinternen Chat-Wortfilter.", "players"),
    "change_current_map": ("Laufende Karte wechseln", "Wechselt die aktuelle Karte des Spielservers und greift damit in die laufende Partie ein.", "maps"),
    "clear_crcon_cache": ("CRCON-Cache leeren", "Leert den Redis-Zwischenspeicher von CRCON.", "system"),
    "flag_player": ("Spieler markieren", "Fügt einem Spieler eine Markierung in CRCON hinzu.", "players"),
    "unflag_player": ("Spielermarkierung entfernen", "Entfernt eine Markierung aus der Spielerakte.", "players"),
    "kick_players": ("Spieler kicken", "Entfernt einen Spieler sofort vom Server. Der Spieler erhält dadurch allein keinen Bann und kann erneut beitreten.", "players"),
    "message_players": ("Spielern Nachrichten senden", "Sendet eine Nachricht an Spieler im Spiel.", "messages"),
    "perma_ban_players": ("Spieler dauerhaft bannen", "Sperrt einen Spieler ohne festes Ablaufdatum für den Server.", "players"),
    "temp_ban_players": ("Spieler vorübergehend bannen", "Sperrt einen Spieler für eine begrenzte Zeit für den Server.", "players"),
    "punish_players": ("Spieler bestrafen", "Führt die Bestrafen-Aktion im Spiel aus. Sie tötet den aktuellen Soldaten; der Spieler wird dadurch nicht vom Server gebannt.", "players"),
    "remove_perma_bans": ("Dauerhaften Bann aufheben", "Entfernt eine dauerhafte Serversperre eines Spielers.", "players"),
    "remove_temp_bans": ("Temporären Bann aufheben", "Entfernt eine befristete Serversperre vor ihrem Ablauf.", "players"),
    "reset_votekick_threshold": ("Votekick-Grenzwerte zurücksetzen", "Setzt die erforderlichen Stimmenzahlen für Kick-Abstimmungen zurück.", "maps"),
    "reset_votemap_state": ("Kartenabstimmung zurücksetzen", "Setzt die aktuelle Votemap-Auswahl und die abgegebenen Stimmen zurück.", "maps"),
    "run_raw_commands": ("Freie RCON-Befehle ausführen", "Sendet frei eingegebene Befehle direkt an den Spielserver. Der Umfang hängt vom Befehl ab und ist nicht auf eine einzelne Verwaltungsaktion begrenzt.", "system"),
    "send_votemap_reminder": ("An Kartenabstimmung erinnern", "Sendet allen Spielern eine Erinnerung an die Kartenabstimmung.", "messages"),
    "switch_players_immediately": ("Spieler sofort verschieben", "Verschiebt einen Spieler sofort in das andere Team.", "players"),
    "switch_players_on_death": ("Spieler beim Tod verschieben", "Plant einen Teamwechsel beim nächsten Tod des Spielers.", "players"),
    "toggle_services": ("Dienste starten oder stoppen", "Aktiviert oder deaktiviert CRCON-Hintergrunddienste, beispielsweise Automod.", "system"),
    "restart_webserver": ("CRCON-Webserver neu starten", "Startet den Webserver neu. Dies ist kein Neustart des gesamten Docker-Stacks oder Spielservers.", "system"),
    "add_blacklist_records": ("Spieler auf Blacklist setzen", "Trägt einen Spieler in eine Sperrliste ein.", "players"),
    "change_blacklist_records": ("Blacklist-Eintrag bearbeiten", "Bearbeitet einen Sperrlisteneintrag oder hebt die Sperrlistenzuordnung eines Spielers auf.", "players"),
    "delete_blacklist_records": ("Blacklist-Eintrag löschen", "Löscht einen Eintrag aus einer Sperrliste.", "players"),
    "create_blacklists": ("Blacklist anlegen", "Erstellt eine neue Sperrliste.", "players"),
    "delete_blacklists": ("Blacklist löschen", "Löscht eine bestehende Sperrliste.", "players"),
    "change_game_layout": ("Kartenziele ändern", "Ändert das Spiellayout beziehungsweise die ausgewählten Ziele einer Karte.", "maps"),
    "add_message_templates": ("Textvorlage anlegen", "Erstellt eine neue gemeinsam nutzbare Nachrichtenvorlage.", "messages"),
    "edit_message_templates": ("Textvorlage bearbeiten", "Ändert eine bestehende gemeinsame Nachrichtenvorlage.", "messages"),
    "delete_message_templates": ("Textvorlage löschen", "Löscht eine gemeinsame Nachrichtenvorlage.", "messages"),
    "change_webhook_queues": ("Webhook-Warteschlange bereinigen", "Entfernt Nachrichten aus der Versandwarteschlange des Webhook-Dienstes.", "integrations"),
    "execute_autobalancer": ("Autobalancer-Eingriffe freigeben", "Bestätigt oder verwirft vorgeschlagene Autobalancer-Eingriffe. Eine Bestätigung kann Teamwechsel auslösen.", "automation"),
    "remove_map_from_votemap": ("Votemap-Kandidat entfernen", "Entfernt eine Karte aus der derzeit laufenden Kartenabstimmung.", "maps"),
    "add_map_to_votemap": ("Votemap-Kandidat hinzufügen", "Ergänzt die aktuelle Kartenabstimmung um eine Karte.", "maps"),
    "set_votemap_winner": ("Votemap-Gewinner festlegen", "Bestimmt die nächste Karte trotz laufender Kartenabstimmung.", "maps"),
    "add_votemap_vote": ("Votemap-Stimme hinzufügen", "Fügt manuell eine Stimme zur Kartenabstimmung hinzu.", "maps"),
    "manage_own_mobile_devices": ("Eigene Geräte verwalten", "Koppelt eigene mobile Geräte und widerruft deren Zugang.", "mobile"),
    "manage_all_mobile_devices": ("Alle mobilen Geräte verwalten", "Prüft gekoppelte Geräte aller Benutzer und kann deren Zugang widerrufen.", "mobile"),
    "create_admin_incidents": ("Mobile Meldung erstellen", "Legt einen neuen Admin-Vorfall zur Bearbeitung an.", "mobile"),
    "claim_admin_incidents": ("Mobile Meldung übernehmen", "Übernimmt die Zuständigkeit für einen Admin-Vorfall.", "mobile"),
    "resolve_admin_incidents": ("Mobile Meldung abschließen", "Schließt einen bearbeiteten Admin-Vorfall ab.", "mobile"),
    "reassign_admin_incidents": ("Mobile Meldung neu zuweisen", "Überträgt die Zuständigkeit für einen Admin-Vorfall.", "mobile"),
    "mark_seeding_sessions": ("Seeding-Versuch markieren", "Startet oder beendet die manuelle Erfassung eines Seeding-Versuchs.", "vip"),
    "manage_leadership_votes": ("Abstimmungen zur Truppführung verwalten", "Konfiguriert die Abstimmungen zur Truppführung.", "automation"),
    "manage_live_map": ("Taktische Karte konfigurieren", "Ändert die Erfassung taktischer Daten und die geschützten Spieler.", "tactical"),
    "manage_live_map_archives": ("Taktische Archive verwalten", "Erstellt, verlängert oder löscht Archive taktischer Rundendaten.", "tactical"),
    "manage_discord_report_bot": ("Discord-Meldebot konfigurieren", "Ändert den Discord-Meldebot und seine KI-Moderationseinstellungen.", "integrations"),
    "control_eventador_events": ("Eventador-Partie steuern", "Bereitet Schritte der Eventador-Spielsteuerung vor und führt sie aus.", "integrations"),
}

SENSITIVE = {"run_raw_commands", "perma_ban_players", "remove_all_vips", "add_admin_roles", "manage_all_mobile_devices", "change_current_map", "toggle_services", "restart_webserver"}
SENSITIVE_RESOURCES = {"steam_config", "server_name_change_config", "discord_webhooks", "rcon_connection_settings_config"}
MODELS = {"user": "Benutzerkonten", "group": "Benutzergruppen", "permission": "Berechtigungsdatensätze", "logentry": "Django-Verwaltungsprotokolle", "contenttype": "Django-Modelltypen", "session": "Anmeldesitzungen", "djangoapikey": "API-Schlüssel", "steamplayer": "Spielkonto-Verknüpfungen", "mobiledevice": "Mobile Geräte"}


def permission_help(permission, german=True):
    code = permission.codename
    action = code.removeprefix("can_")
    category, kind, known = "other", "access", True
    sensitive = action in SENSITIVE
    if action in ACTIONS:
        title, description, category = ACTIONS[action]
        kind = "action"
    elif action.startswith(("view_", "change_")) and action.split("_", 1)[1] in RESOURCES:
        verb, resource = action.split("_", 1)
        title, scope, category = RESOURCES[resource]
        kind = "read" if verb == "view" else "change"
        title += " anzeigen" if kind == "read" else " ändern"
        description = f"Erlaubt, {scope} " + ("einzusehen. Dieses Recht allein erlaubt keine Änderungen." if kind == "read" else "zu ändern.")
        sensitive = resource in SENSITIVE_RESOURCES
    elif not code.startswith("can_") and "_" in code and code.split("_", 1)[0] in {"view", "add", "change", "delete"}:
        verb, model = code.split("_", 1)
        label = MODELS.get(model, str(permission.content_type.name))
        word = {"view": "anzeigen", "add": "anlegen", "change": "bearbeiten", "delete": "löschen"}[verb]
        title = f"{label} {word}"
        infinitive = {"view": "anzuzeigen", "add": "anzulegen", "change": "zu bearbeiten", "delete": "zu löschen"}[verb]
        description = f"Erlaubt, {label} in der Verwaltung {infinitive}."
        category, kind = "accounts", "read" if verb == "view" else "change"
        sensitive = model in {"user", "group", "permission", "djangoapikey"} and verb != "view"
        if model == "user" and verb == "change":
            description += " Umfasst auch Rollen und direkte Rechte dieser Konten; kann damit zusätzliche Zugriffe vergeben."
        if model == "group" and verb == "change":
            description += " Änderungen an Gruppenrechten wirken auf alle Mitglieder dieser Gruppe."
    else:
        title = permission.name
        description = "Zusätzliches Recht ohne geprüfte CRCON-Beschreibung. Die technische Kennung und der Originalname bleiben zur Zuordnung sichtbar."
        known = False
    if not german:
        title = permission.name.removeprefix("Can ")
        description = permission.name + "." if known else "Additional permission without a reviewed CRCON description. Check its original name and technical identifier."
        if kind == "read": description += " This permission alone does not allow changes."
        if code == "change_user": description += " Includes assigning roles and direct permissions to these accounts."
        if code == "change_group": description += " Group permissions affect all members."
    internal = (permission.content_type.app_label, permission.content_type.model) in {
        ("contenttypes", "contenttype"), ("auth", "permission"),
        ("admin", "logentry"), ("sessions", "session"),
    }
    aliases = permission.name
    if code in {"can_view_admins", "can_view_admin_ids", "can_view_admin_groups", "can_add_admin_roles", "can_remove_admin_roles", "can_view_online_console_admins"}:
        aliases += " Konsolen Console Spielserver-Admins Spielserver-Adminrollen Kennungen Game server admins"
    if german:
        console_copy = {
            "can_view_admins": ("Konsolen-Admins: Menü öffnen", "Zeigt den Menüpunkt für Konsolen-Admins. Zum Laden der Seite werden auch die Adminliste und die verfügbaren Rollen benötigt."),
            "can_view_admin_ids": ("Konsolen-Admins: Liste und Spieler-IDs anzeigen", "Lädt Namen, Spieler-IDs und Rollen der Konsolen-Admins. Ohne dieses Recht kann die Adminliste nicht geladen werden. Erlaubt keine Änderungen."),
            "can_view_admin_groups": ("Konsolen-Admins: verfügbare Rollen anzeigen", "Lädt die verfügbaren Adminrollen des Spielservers. Zum Öffnen der Seite werden auch Menü-Zugriff und Adminliste benötigt. Erlaubt keine Änderungen."),
        }
        title, description = console_copy.get(code, (title, description))
    if not german:
        console_copy = {
            "can_view_admins": ("Console admins: menu access", "Shows the console-admin menu. The page also needs the admin-list and available-roles permissions."),
            "can_view_admin_ids": ("Console admins: list and player IDs", "Reads names, player IDs and roles. Required to load the console-admin list; does not allow changes."),
            "can_view_admin_groups": ("Console admins: available roles", "Reads the available in-game admin roles. The page also needs menu access and the admin-list permission."),
            "can_add_admin_roles": ("Console admins: assign role", "Grants a player an in-game admin role, not an RCON user group."),
            "can_remove_admin_roles": ("Console admins: remove role", "Removes a player's in-game admin role, not their RCON user groups."),
        }
        title, description = console_copy.get(code, (title, description))
    if internal:
        category = "internal"
        sensitive = kind != "read"
        description += (" Internes Systemrecht; für Support und Spielermoderation nicht erforderlich. Bestehende Zuweisungen nicht ungeprüft ändern."
                        if german else " Internal system permission; not needed for support or player moderation. Review existing assignments before changing them.")
        if permission.content_type.model == "contenttype":
            description += (" Django pflegt diese Modellzuordnungen automatisch. Änderungen können Berechtigungszuordnungen beschädigen."
                            if german else " Django maintains these model references automatically. Changes can break permission mappings.")
    return {"id": str(permission.pk), "code": f"{permission.content_type.app_label}.{code}", "title": title,
            "description": description, "category": CATEGORIES[category][0 if german else 1], "kind": kind,
            "sensitive": sensitive, "documented": known, "internal": internal, "aliases": aliases}
