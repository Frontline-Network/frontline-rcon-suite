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
        to: "stats/live-sessions",
        icon: <BrowseGalleryIcon />,
      },
      {
        name: "Live Game",
        to: "stats/live-game",
        icon: <SportsEsportsIcon />,
      },
      {
        name: "Games",
        to: "stats/games",
        icon: <HourglassBottomIcon />,
      },
    ],
  },
];

const groupTranslationKeys = {
  "Apps setup": "navigation.groups.appsSetup",
  Views: "navigation.groups.views",
  Maps: "navigation.groups.maps",
  Records: "navigation.groups.records",
  Settings: "navigation.groups.settings",
  Webhooks: "navigation.groups.webhooks",
  Automods: "navigation.groups.automods",
  Others: "navigation.groups.others",
  Stats: "navigation.groups.stats",
};

const linkTranslationKeys = {
  "/": "navigation.links.home",
  "/apps": "navigation.links.frontlineApp",
  "/apps/discord-report-bot": "navigation.links.discordReportBot",
  "/views/live": "navigation.links.live",
  "/views/team": "navigation.links.team",
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
  "stats/live-sessions": "navigation.links.liveSessions",
  "stats/live-game": "navigation.links.liveGame",
  "stats/games": "navigation.links.games",
};

export const navMenus = rawNavMenus.map((menu, index) => ({
  ...menu,
  id: menu.name?.toLowerCase() || `root-${index}`,
  translationKey: groupTranslationKeys[menu.name],
  links: menu.links.map((link) => ({
    ...link,
    translationKey: linkTranslationKeys[link.to],
  })),
}));
