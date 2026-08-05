export const webhooks = [
  {
    path: "/settings/webhooks/audit",
    command: "audit_discord_webhooks_config",
    name: "Audit Webhooks",
    nameKey: "navigation.links.audit",
  },
  {
    path: "/settings/webhooks/admin-ping",
    command: "admin_pings_discord_webhooks_config",
    name: "Admin Ping Webhooks",
    nameKey: "navigation.links.adminPing",
  },
  {
    path: "/settings/webhooks/watchlist",
    command: "watchlist_discord_webhooks_config",
    name: "Watchlist Webhooks",
    nameKey: "navigation.links.watchlist",
  },
  {
    path: "/settings/webhooks/camera",
    command: "camera_discord_webhooks_config",
    name: "Camera Webhooks",
    nameKey: "navigation.links.camera",
  },
  {
    path: "/settings/webhooks/chat",
    command: "chat_discord_webhooks_config",
    name: "Chat Webhooks",
    nameKey: "navigation.links.chat",
  },
  {
    path: "/settings/webhooks/kills",
    command: "kills_discord_webhooks_config",
    name: "Kill/Team Kill Webhooks",
    nameKey: "navigation.links.kills",
  },
  {
    path: "/settings/webhooks/log-line",
    command: "log_line_webhook_config",
    name: "Log Line Webhooks",
    nameKey: "navigation.links.logLine",
  },
];

export const automods = [
  {
    path: "/settings/automods/level",
    command: "auto_mod_level_config",
    name: "Level Auto Mod",
    nameKey: "navigation.links.level",
  },
  {
    path: "/settings/automods/no-leader",
    command: "auto_mod_no_leader_config",
    name: "No Leader Auto Mod",
    nameKey: "navigation.links.noLeader",
  },
  {
    path: "/settings/automods/seeding",
    command: "auto_mod_seeding_config",
    name: "Seeding Auto Mod",
    nameKey: "navigation.links.seeding",
  },
  {
    path: "/settings/automods/no-solo-tank",
    command: "auto_mod_solo_tank_config",
    name: "No Solo Tank Auto Mod",
    nameKey: "navigation.links.noSoloTank",
  },
];

export const others = [
  {
    path: "/settings/others/autobalancer",
    command: "autobalancer_config",
    name: "Fair Autobalancer",
    nameKey: "navigation.links.autobalancer",
  },
  {
    path: "/settings/others/seed-vip",
    command: "seed_vip_config",
    name: "Seeder VIP Reward",
    nameKey: "navigation.links.seedVip",
  },
  {
    path: "/settings/others/game-server",
    command: "rcon_connection_settings_config",
    name: "Game Server Connection Settings",
    nameKey: "navigation.links.gameServer",
  },
  {
    path: "/settings/others/crcon",
    command: "rcon_server_settings_config",
    name: "General CRCON Settings",
    nameKey: "navigation.links.crcon",
  },
  {
    path: "/settings/others/chat-commands",
    command: "chat_commands_config",
    name: "Chat Commands Settings",
    nameKey: "navigation.links.chatCommands",
  },
  {
    path: "/settings/others/rcon-chat-commands",
    command: "rcon_chat_commands_config",
    name: "RCON Chat Commands Settings",
    nameKey: "navigation.links.rconCommands",
  },
  {
    path: "/settings/others/scoreboard",
    command: "scoreboard_config",
    name: "Scoreboard",
    nameKey: "navigation.links.scoreboard",
  },
  {
    path: "/settings/others/steam",
    command: "steam_config",
    name: "Steam API",
    nameKey: "navigation.links.steam",
  },
  {
    path: "/settings/others/vac-bans",
    command: "vac_game_bans_config",
    name: "VAC/Game Bans",
    nameKey: "navigation.links.vacBans",
  },
  {
    path: "/settings/others/tk-bans",
    command: "tk_ban_on_connect_config",
    name: "TK Ban On Connect",
    nameKey: "navigation.links.tkBans",
  },
  {
    path: "/settings/others/name-kicks",
    command: "name_kick_config",
    name: "Name Kicks",
    nameKey: "navigation.links.nameKicks",
  },
  {
    path: "/settings/others/expired-vip",
    command: "expired_vip_config",
    name: "Expired VIP",
    nameKey: "navigation.links.expiredVip",
  },
  {
    path: "/settings/others/gtx-server",
    command: "server_name_change_config",
    name: "GTX Server Name Change",
    nameKey: "navigation.links.gtxServer",
  },
  {
    path: "/settings/others/log-stream",
    command: "log_stream_config",
    name: "Log Stream",
    nameKey: "navigation.links.logStream",
  },
  {
    path: "/settings/others/watch-kill-rate",
    command: "watch_killrate_config",
    name: "Watch Kill Rate",
    nameKey: "navigation.links.watchKillRate",
  },
];
