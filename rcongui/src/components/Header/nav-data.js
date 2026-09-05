import HomeIcon from "@mui/icons-material/Home";
import SportsEsportsIcon from "@mui/icons-material/SportsEsports";
import BoltIcon from "@mui/icons-material/Bolt";
import GroupsIcon from "@mui/icons-material/Groups";
import PeopleIcon from "@mui/icons-material/PeopleAlt";
import TextSnippetIcon from "@mui/icons-material/TextSnippet";
import SimCardAlertIcon from "@mui/icons-material/SimCardAlert";
import SmartToyIcon from "@mui/icons-material/SmartToy";
import WebhookIcon from "@mui/icons-material/Webhook";
import SettingsIcon from "@mui/icons-material/Settings";
import DnsIcon from "@mui/icons-material/Dns";
import PersonOffIcon from "@mui/icons-material/PersonOff";
import NoTransferIcon from "@mui/icons-material/NoTransfer";
import SpaIcon from "@mui/icons-material/Spa";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import RestaurantIcon from "@mui/icons-material/Restaurant";
import ChatIcon from "@mui/icons-material/Chat";
import VideocamIcon from "@mui/icons-material/Videocam";
import PrivacyTipIcon from "@mui/icons-material/PrivacyTip";
import RateReviewIcon from "@mui/icons-material/RateReview";
import TimerOffIcon from "@mui/icons-material/TimerOff";
import DriveFileRenameOutlineIcon from "@mui/icons-material/DriveFileRenameOutline";
import SportsMartialArtsIcon from "@mui/icons-material/SportsMartialArts";
import CableIcon from "@mui/icons-material/Cable";
import ScoreboardIcon from "@mui/icons-material/Scoreboard";
import GavelIcon from "@mui/icons-material/Gavel";
import BrowseGalleryIcon from "@mui/icons-material/BrowseGallery";
import HourglassBottomIcon from "@mui/icons-material/HourglassBottom";
import MiscellaneousServicesIcon from "@mui/icons-material/MiscellaneousServices";
import NoStrollerIcon from "@mui/icons-material/NoStroller";
import MapIcon from "@mui/icons-material/Map";
import AccountBalanceIcon from "@mui/icons-material/AccountBalance";
import FolderIcon from "@mui/icons-material/Folder";
import ViewCarouselIcon from "@mui/icons-material/ViewCarousel";
import AnalyticsIcon from "@mui/icons-material/Analytics";
import StreamIcon from "@mui/icons-material/Stream";
import ThreeSixtyIcon from "@mui/icons-material/ThreeSixty";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import HowToVoteIcon from "@mui/icons-material/HowToVote";
import AdsClickIcon from "@mui/icons-material/AdsClick";
import ElectricalServicesIcon from "@mui/icons-material/ElectricalServices";
import SettingsSuggestIcon from "@mui/icons-material/SettingsSuggest";
import GradeIcon from "@mui/icons-material/Grade";
import AdminPanelSettingsIcon from "@mui/icons-material/AdminPanelSettings";
import DraftsIcon from "@mui/icons-material/Drafts";
import SpellcheckIcon from "@mui/icons-material/Spellcheck";
import DvrIcon from "@mui/icons-material/Dvr";
import OndemandVideoIcon from "@mui/icons-material/OndemandVideo";
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech";
import SearchIcon from "@mui/icons-material/Search";
import BalanceIcon from "@mui/icons-material/Balance";
import PhoneAndroidIcon from "@mui/icons-material/PhoneAndroid";

const rawNavMenus = [
  {
    links: [
      {
        name: "Home",
        to: "/",
        icon: <HomeIcon />,
      },
    ],
  },
  {
    name: "Apps setup",
    icon: <PhoneAndroidIcon />,
    links: [
      {
        name: "Frontline App",
        to: "/apps",
        icon: <PhoneAndroidIcon />,
      },
      {
        name: "Discord Report Bot",
        to: "/apps/discord-report-bot",
        icon: <SmartToyIcon />,
      },
    ],
  },
  {
    name: "Views",
    icon: <ViewCarouselIcon />,
    links: [
      {
        name: "Live",
        to: "/views/live",
        icon: <BoltIcon />,
      },
      {
        name: "Team",
        to: "/views/team",
        icon: <GroupsIcon />,
      },
      { name: "Live map", to: "/views/live-map", icon: <MapIcon /> },
      {
        name: "Autobalancer",
        to: "/views/autobalancer",
        icon: <BalanceIcon />,
      },
    ],
  },
  {
    name: "Maps",
    icon: <MapIcon />,
    links: [
      {
        name: "Change",
        to: "/settings/maps/change",
        icon: <RestartAltIcon />,
      },
      {
        name: "Rotation",
        to: "/settings/maps/rotation",
        icon: <ThreeSixtyIcon />,
      },
      {
        name: "Objectives",
        to: "/settings/maps/objectives",
        icon: <AdsClickIcon />,
      },
      {
        name: "Votemap",
        to: "/settings/maps/votemap",
        icon: <HowToVoteIcon />,
      },
    ],
  },
  {
    name: "Records",
    icon: <FolderIcon />,
    links: [
      {
        name: "Players",
        to: "/records/players",
        icon: <PeopleIcon />,
      },
      {
        name: "Vips",
        to: "/records/vips",
        icon: <GradeIcon />,
      },
      {
        name: "Blacklist",
        to: "/records/blacklists",
        icon: <AccountBalanceIcon />,
      },
      {
        name: "Game Logs",
        to: "/records/game-logs",
        icon: <TextSnippetIcon />,
      },
      {
        name: "Audit Logs",
        to: "/records/audit-logs",
        icon: <TextSnippetIcon />,
      },
    ],
  },
  {
    name: "Settings",
    icon: <SettingsIcon />,
    links: [
      {
        name: "General",
        to: "/settings/general",
        icon: <SettingsIcon />,
      },
      {
        name: "Services",
        to: "/settings/services",
        icon: <ElectricalServicesIcon />,
      },
      {
        name: "Welcome message",
        to: "/settings/welcome-message",
        icon: <DvrIcon />,
      },
      {
        name: "Broadcast message",
        to: "/settings/broadcast-message",
        icon: <OndemandVideoIcon />,
      },
      {
        name: "Console Admins",
        to: "/settings/console-admins",
        icon: <AdminPanelSettingsIcon />,
      },
      {
        name: "Templates",
        to: "/settings/templates/message",
        icon: <DraftsIcon />,
      },
      {
        name: "Profanity filter",
        to: "/settings/profanity-filter",
        icon: <SpellcheckIcon />,
      },
      {
        name: "Autosettings",
        to: "/settings/autosettings",
        icon: <SettingsSuggestIcon />,
      },
    ],
  },
  {
    name: "Webhooks",
    icon: <WebhookIcon />,
    links: [
      {
        name: "Discord & Communication",
        to: "/settings/integrations",
        icon: <WebhookIcon />,
      },
      {
        name: "Audit",
        to: "/settings/webhooks/audit",
        icon: <SimCardAlertIcon />,
      },
      {
        name: "Admin Ping",
        to: "/settings/webhooks/admin-ping",
        icon: <PrivacyTipIcon />,
      },
      {
        name: "Watchlist",
        to: "/settings/webhooks/watchlist",
        icon: <RemoveRedEyeIcon />,
      },
      {
        name: "Camera",
        to: "/settings/webhooks/camera",
        icon: <VideocamIcon />,
      },
      {
        name: "Chat",
        to: "/settings/webhooks/chat",
        icon: <ChatIcon />,
      },
      {
        name: "Kill/TK",
        to: "/settings/webhooks/kills",
        icon: <RestaurantIcon />,
      },
      {
        name: "Log Line",
        to: "/settings/webhooks/log-line",
        icon: <TextSnippetIcon />,
      },
    ],
  },
  {
    name: "Automods",
    icon: <SmartToyIcon />,
    links: [
      {
        name: "Level",
        to: "/settings/automods/level",
        icon: <NoStrollerIcon />,
      },
      {
        name: "No Leader",
        to: "/settings/automods/no-leader",
        icon: <PersonOffIcon />,
      },
      {
        name: "Seeding",
        to: "/settings/automods/seeding",
        icon: <SpaIcon />,
      },
      {
        name: "No Solo Tank",
        to: "/settings/automods/no-solo-tank",
        icon: <NoTransferIcon />,
      },
      {
        name: "VAC/Game Bans",
        to: "/settings/others/vac-bans",
        icon: <AccountBalanceIcon />,
      },
      {
        name: "TK Ban On Connect",
        to: "/settings/others/tk-bans",
        icon: <GavelIcon />,
      },
      {
        name: "Name Kicks",
        to: "/settings/others/name-kicks",
        icon: <SportsMartialArtsIcon />,
      },
    ],
  },
  {
    name: "Others",
    icon: <MiscellaneousServicesIcon />,
    links: [
      {
        name: "Seeder VIP Reward",
        to: "/settings/others/seed-vip",
        icon: <MilitaryTechIcon />,
      },
      {
        name: "RCON Game Server Connection",
        to: "/settings/others/game-server",
        icon: <CableIcon />,
      },
      {
        name: "CRCON Settings",
        to: "/settings/others/crcon",
        icon: <DnsIcon />,
      },
      {
        name: "Chat Commands",
        to: "/settings/others/chat-commands",
        icon: <RateReviewIcon />,
      },
      {
        name: "RCON Chat Commands",
        to: "/settings/others/rcon-chat-commands",
        icon: <RateReviewIcon />,
      },
      {
        name: "Scoreboard",
        to: "/settings/others/scoreboard",
        icon: <ScoreboardIcon />,
      },
      {
        name: "Steam API",
        to: "/settings/others/steam",
        icon: <RemoveRedEyeIcon />,
      },
      {
        name: "Expired VIP",
        to: "/settings/others/expired-vip",
        icon: <TimerOffIcon />,
      },
      {
        name: "GTX Server Name Change",
        to: "/settings/others/gtx-server",
        icon: <DriveFileRenameOutlineIcon />,
      },
      {
        name: "Log Stream",
        to: "/settings/others/log-stream",
        icon: <StreamIcon />,
      },
      {
        name: "Watch Kill Rate",
        to: "/settings/others/watch-kill-rate",
        icon: <SearchIcon />,
      },
    ],
  },
  {
    name: "Stats",
    icon: <AnalyticsIcon />,
    links: [
      {
        name: "Live Sessions",
        to: "/stats/live-sessions",
        icon: <BrowseGalleryIcon />,
      },
      {
        name: "Live Statistics",
        to: "/stats/live-game",
        icon: <SportsEsportsIcon />,
      },
      {
        name: "Games",
        to: "/stats/games",
        icon: <HourglassBottomIcon />,
      },
    ],
  },
];

const linkTranslationKeys = {
  "/": "navigation.links.home",
  "/apps": "navigation.links.frontlineApp",
  "/apps/discord-report-bot": "navigation.links.discordReportBot",
  "/views/live": "navigation.links.live",
  "/views/team": "navigation.links.team",
  "/views/live-map": "navigation.links.liveMap",
  "/settings/maps/change": "navigation.links.changeMap",
  "/settings/maps/rotation": "navigation.links.rotation",
  "/settings/maps/objectives": "navigation.links.objectives",
  "/settings/maps/votemap": "navigation.links.votemap",
  "/records/players": "navigation.links.players",
  "/records/vips": "navigation.links.vips",
  "/records/blacklists": "navigation.links.blacklist",
  "/records/game-logs": "navigation.links.gameLogs",
  "/records/audit-logs": "navigation.links.auditLogs",
  "/settings/general": "navigation.links.general",
  "/settings/services": "navigation.links.services",
  "/settings/welcome-message": "navigation.links.welcomeMessage",
  "/settings/broadcast-message": "navigation.links.broadcastMessage",
  "/settings/console-admins": "navigation.links.consoleAdmins",
  "/settings/templates/message": "navigation.links.templates",
  "/settings/profanity-filter": "navigation.links.profanityFilter",
  "/settings/autosettings": "navigation.links.autosettings",
  "/settings/integrations": "navigation.links.discordCommunication",
  "/settings/webhooks/audit": "navigation.links.audit",
  "/settings/webhooks/admin-ping": "navigation.links.adminPing",
  "/settings/webhooks/watchlist": "navigation.links.watchlist",
  "/settings/webhooks/camera": "navigation.links.camera",
  "/settings/webhooks/chat": "navigation.links.chat",
  "/settings/webhooks/kills": "navigation.links.kills",
  "/settings/webhooks/log-line": "navigation.links.logLine",
  "/settings/automods/level": "navigation.links.level",
  "/settings/automods/no-leader": "navigation.links.noLeader",
  "/settings/automods/seeding": "navigation.links.seeding",
  "/settings/automods/no-solo-tank": "navigation.links.noSoloTank",
  "/settings/others/vac-bans": "navigation.links.vacBans",
  "/settings/others/tk-bans": "navigation.links.tkBans",
  "/settings/others/name-kicks": "navigation.links.nameKicks",
  "/settings/others/seed-vip": "navigation.links.seedVip",
  "/settings/others/game-server": "navigation.links.gameServer",
  "/settings/others/crcon": "navigation.links.crcon",
  "/settings/others/chat-commands": "navigation.links.chatCommands",
  "/settings/others/rcon-chat-commands": "navigation.links.rconCommands",
  "/settings/others/scoreboard": "navigation.links.scoreboard",
  "/settings/others/steam": "navigation.links.steam",
  "/settings/others/expired-vip": "navigation.links.expiredVip",
  "/settings/others/gtx-server": "navigation.links.gtxServer",
  "/settings/others/log-stream": "navigation.links.logStream",
  "/settings/others/watch-kill-rate": "navigation.links.watchKillRate",
  "/stats/live-sessions": "navigation.links.liveSessions",
  "/stats/live-game": "navigation.links.liveGame",
  "/stats/games": "navigation.links.games",
};

const linksByRoute = Object.fromEntries(
  rawNavMenus
    .flatMap((menu) => menu.links)
    .map((link) => [
      link.to,
      {
        ...link,
        translationKey: linkTranslationKeys[link.to],
      },
    ])
);

// Navigation follows the jobs administrators perform. The routes stay stable;
// this is deliberately only a clearer information architecture on top of the
// existing pages.
const taskGroupDefinitions = [
  {
    id: "live-operations",
    translationKey: "navigation.groups.liveOperations",
    icon: <BoltIcon />,
    routes: [
      "/views/live",
      "/views/team",
      "/views/live-map",
      "/views/autobalancer",
      "/stats/live-game",
    ],
  },
  {
    id: "players-moderation",
    translationKey: "navigation.groups.playersModeration",
    icon: <PeopleIcon />,
    routes: [
      "/records/players",
      "/records/vips",
      "/records/blacklists",
      "/settings/console-admins",
      "/settings/templates/message",
      "/settings/profanity-filter",
    ],
  },
  {
    id: "maps-game-operations",
    translationKey: "navigation.groups.mapsGameOperations",
    icon: <MapIcon />,
    routes: [
      "/settings/maps/change",
      "/settings/maps/rotation",
      "/settings/maps/objectives",
      "/settings/maps/votemap",
      "/settings/welcome-message",
      "/settings/broadcast-message",
    ],
  },
  {
    id: "automation",
    translationKey: "navigation.groups.automation",
    icon: <SmartToyIcon />,
    routes: [
      "/settings/autosettings",
      "/settings/automods/level",
      "/settings/automods/no-leader",
      "/settings/automods/seeding",
      "/settings/automods/no-solo-tank",
      "/settings/others/vac-bans",
      "/settings/others/tk-bans",
      "/settings/others/name-kicks",
      "/settings/others/seed-vip",
      "/settings/others/expired-vip",
    ],
  },
  {
    id: "apps-setup",
    translationKey: "navigation.groups.appsSetup",
    icon: <PhoneAndroidIcon />,
    routes: ["/apps", "/apps/discord-report-bot"],
  },
  {
    id: "integrations",
    translationKey: "navigation.groups.integrations",
    icon: <WebhookIcon />,
    routes: ["/settings/integrations"],
  },
  {
    id: "server-configuration",
    translationKey: "navigation.groups.serverConfiguration",
    icon: <SettingsIcon />,
    routes: ["/settings/general"],
  },
  {
    id: "logs-analytics",
    translationKey: "navigation.groups.logsAnalytics",
    icon: <AnalyticsIcon />,
    routes: [
      "/records/game-logs",
      "/records/audit-logs",
      "/stats/live-sessions",
      "/stats/games",
    ],
  },
  {
    id: "system-diagnostics",
    translationKey: "navigation.groups.systemDiagnostics",
    icon: <MiscellaneousServicesIcon />,
    routes: ["/settings/services"],
  },
];

const linkPermissionKeys = {
  "/views/live": ["can_view_recent_logs"],
  "/views/team": ["can_view_team_view"],
  "/views/live-map": ["can_view_live_map"],
  "/settings/maps/change": ["can_view_current_map", "can_change_current_map"],
  "/records/players": ["can_view_player_history", "can_view_player_info"],
  "/records/vips": ["can_view_vip_ids"],
  "/records/blacklists": ["can_view_blacklists"],
  "/settings/console-admins": ["can_view_admins"],
  "/settings/templates/message": ["can_view_message_templates"],
  "/settings/profanity-filter": ["can_view_profanities"],
  "/settings/maps/rotation": ["can_view_map_rotation"],
  "/settings/maps/objectives": ["can_view_all_maps"],
  "/settings/maps/votemap": [
    "can_view_votemap_status",
    "can_view_votemap_config",
    "can_view_map_whitelist",
  ],
  "/settings/welcome-message": ["can_view_welcome_message"],
  "/settings/broadcast-message": ["can_view_broadcast_message"],
  "/settings/autosettings": ["can_view_auto_settings"],
  "/settings/automods/level": ["can_view_auto_mod_level_config"],
  "/settings/automods/no-leader": ["can_view_auto_mod_no_leader_config"],
  "/settings/automods/seeding": ["can_view_auto_mod_seeding_config"],
  "/settings/automods/no-solo-tank": ["can_view_auto_mod_solo_tank_config"],
  "/settings/others/vac-bans": ["can_view_vac_game_bans_config"],
  "/settings/others/tk-bans": ["can_view_tk_ban_on_connect_config"],
  "/settings/others/name-kicks": ["can_view_name_kick_config"],
  "/settings/others/expired-vip": ["can_view_expired_vip_config"],
  "/settings/webhooks/audit": ["can_view_audit_discord_webhooks_config"],
  "/settings/webhooks/admin-ping": [
    "can_view_admin_pings_discord_webhooks_config",
  ],
  "/settings/webhooks/watchlist": [
    "can_view_watchlist_discord_webhooks_config",
  ],
  "/settings/webhooks/camera": [
    "can_view_camera_discord_webhooks_config",
    "can_view_camera_config",
  ],
  "/settings/webhooks/chat": ["can_view_chat_discord_webhooks_config"],
  "/settings/webhooks/kills": ["can_view_kills_discord_webhooks_config"],
  "/settings/webhooks/log-line": ["can_view_log_line_discord_webhook_config"],
  "/settings/others/gtx-server": ["can_view_server_name_change_config"],
  "/settings/general": [
    "can_view_team_switch_cooldown",
    "can_view_queue_length",
    "can_view_idle_autokick_time",
    "can_view_autobalance_enabled",
    "can_view_votekick_enabled",
    "can_view_vip_slots",
  ],
  "/settings/others/chat-commands": ["can_view_chat_commands_config"],
  "/settings/others/rcon-chat-commands": ["can_view_rcon_chat_commands_config"],
  "/settings/others/scoreboard": ["can_view_scorebot_config"],
  "/settings/integrations": [
    "can_view_audit_discord_webhooks_config",
    "can_view_admin_pings_discord_webhooks_config",
    "can_view_watchlist_discord_webhooks_config",
    "can_view_camera_discord_webhooks_config",
    "can_view_chat_discord_webhooks_config",
    "can_view_kills_discord_webhooks_config",
    "can_view_log_line_discord_webhook_config",
    "can_view_scorebot_config",
    "can_view_chat_commands_config",
    "can_view_rcon_chat_commands_config",
    "can_view_server_name_change_config",
  ],
  "/records/game-logs": ["can_view_game_logs"],
  "/records/audit-logs": ["can_view_audit_logs"],
  "/settings/services": ["can_view_available_services"],
  "/settings/others/game-server": ["can_view_rcon_connection_settings_config"],
  "/settings/others/crcon": ["can_view_rcon_server_settings_config"],
  "/settings/others/steam": ["can_view_steam_config"],
  "/settings/others/log-stream": ["can_view_log_stream_config"],
  "/settings/others/watch-kill-rate": ["can_view_watch_killrate_config"],
};

const linkPermissionGroups = {
  "/settings/maps/votemap": [
    ["can_view_votemap_status"],
    ["can_view_votemap_config"],
    ["can_view_map_whitelist", "can_view_all_maps"],
  ],
};

const withPermissions = (link) => ({
  ...link,
  requiredPermissions: linkPermissionKeys[link.to] || [],
  requiredPermissionGroups: linkPermissionGroups[link.to] || [],
});

export const canAccessNavLink = (link, permissions) => {
  if (permissions?.is_superuser) return true;
  if (!link?.requiredPermissions?.length) return true;

  const grantedPermissions = new Set(
    (permissions?.permissions || []).map((entry) =>
      typeof entry === "string" ? entry : entry.permission
    )
  );
  if (link.requiredPermissionGroups?.length) {
    return link.requiredPermissionGroups.some((group) =>
      group.every((permission) => grantedPermissions.has(permission))
    );
  }
  return link.requiredPermissions.some((permission) =>
    grantedPermissions.has(permission)
  );
};

export const navMenus = [
  {
    id: "root",
    links: [withPermissions(linksByRoute["/"])],
  },
  ...taskGroupDefinitions.map(({ routes, ...group }) => ({
    ...group,
    name: group.id,
    links: routes.map((route) => withPermissions(linksByRoute[route])),
  })),
];
