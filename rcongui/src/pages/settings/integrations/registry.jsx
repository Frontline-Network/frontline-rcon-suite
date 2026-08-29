import AssignmentOutlinedIcon from "@mui/icons-material/AssignmentOutlined";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import ChatBubbleOutlineOutlinedIcon from "@mui/icons-material/ChatBubbleOutlineOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import PhotoCameraOutlinedIcon from "@mui/icons-material/PhotoCameraOutlined";
import ScoreboardOutlinedIcon from "@mui/icons-material/ScoreboardOutlined";
import SecurityOutlinedIcon from "@mui/icons-material/SecurityOutlined";
import TerminalOutlinedIcon from "@mui/icons-material/TerminalOutlined";
import TextSnippetOutlinedIcon from "@mui/icons-material/TextSnippetOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";

export const integrationModules = [
  {
    slug: "audit",
    category: "webhooks",
    type: "audit",
    command: "audit_discord_webhooks_config",
    legacyPath: "/settings/webhooks/audit",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.audit.name",
    purposeKey: "settings.integrations.modules.audit.purpose",
    viewPermission: "can_view_audit_discord_webhooks_config",
    changePermission: "can_change_audit_discord_webhooks_config",
    icon: AssignmentOutlinedIcon,
  },
  {
    slug: "admin-ping",
    category: "webhooks",
    type: "admin-ping",
    command: "admin_pings_discord_webhooks_config",
    legacyPath: "/settings/webhooks/admin-ping",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.adminPing.name",
    purposeKey: "settings.integrations.modules.adminPing.purpose",
    viewPermission: "can_view_admin_pings_discord_webhooks_config",
    changePermission: "can_change_admin_pings_discord_webhooks_config",
    icon: CampaignOutlinedIcon,
  },
  {
    slug: "watchlist",
    category: "webhooks",
    type: "watchlist",
    command: "watchlist_discord_webhooks_config",
    legacyPath: "/settings/webhooks/watchlist",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.watchlist.name",
    purposeKey: "settings.integrations.modules.watchlist.purpose",
    viewPermission: "can_view_watchlist_discord_webhooks_config",
    changePermission: "can_change_watchlist_discord_webhooks_config",
    icon: VisibilityOutlinedIcon,
  },
  {
    slug: "camera",
    category: "webhooks",
    type: "camera",
    command: "camera_discord_webhooks_config",
    legacyPath: "/settings/webhooks/camera",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.camera.name",
    purposeKey: "settings.integrations.modules.camera.purpose",
    viewPermission: "can_view_camera_discord_webhooks_config",
    changePermission: "can_change_camera_discord_webhooks_config",
    icon: PhotoCameraOutlinedIcon,
  },
  {
    slug: "chat",
    category: "webhooks",
    type: "chat",
    command: "chat_discord_webhooks_config",
    legacyPath: "/settings/webhooks/chat",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.chat.name",
    purposeKey: "settings.integrations.modules.chat.purpose",
    viewPermission: "can_view_chat_discord_webhooks_config",
    changePermission: "can_change_chat_discord_webhooks_config",
    icon: ChatBubbleOutlineOutlinedIcon,
  },
  {
    slug: "kills",
    category: "webhooks",
    type: "kills",
    command: "kills_discord_webhooks_config",
    legacyPath: "/settings/webhooks/kills",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.kills.name",
    purposeKey: "settings.integrations.modules.kills.purpose",
    viewPermission: "can_view_kills_discord_webhooks_config",
    changePermission: "can_change_kills_discord_webhooks_config",
    icon: GavelOutlinedIcon,
  },
  {
    slug: "log-line",
    category: "webhooks",
    type: "log-line",
    command: "log_line_webhook_config",
    legacyPath: "/settings/webhooks/log-line",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.logLine.name",
    purposeKey: "settings.integrations.modules.logLine.purpose",
    viewPermission: "can_view_log_line_discord_webhook_config",
    changePermission: "can_change_log_line_discord_webhook_config",
    icon: TextSnippetOutlinedIcon,
  },
  {
    slug: "scoreboard",
    category: "others",
    type: "scoreboard",
    command: "scoreboard_config",
    legacyPath: "/settings/others/scoreboard",
    group: "discord",
    kind: "discord",
    nameKey: "settings.integrations.modules.scoreboard.name",
    purposeKey: "settings.integrations.modules.scoreboard.purpose",
    viewPermission: "can_view_scorebot_config",
    changePermission: "can_change_scorebot_config",
    icon: ScoreboardOutlinedIcon,
  },
  {
    slug: "chat-commands",
    category: "others",
    type: "chat-commands",
    command: "chat_commands_config",
    legacyPath: "/settings/others/chat-commands",
    group: "communication",
    kind: "commands",
    nameKey: "settings.integrations.modules.chatCommands.name",
    purposeKey: "settings.integrations.modules.chatCommands.purpose",
    viewPermission: "can_view_chat_commands_config",
    changePermission: "can_change_chat_commands_config",
    icon: TerminalOutlinedIcon,
  },
  {
    slug: "rcon-chat-commands",
    category: "others",
    type: "rcon-chat-commands",
    command: "rcon_chat_commands_config",
    legacyPath: "/settings/others/rcon-chat-commands",
    group: "communication",
    kind: "commands",
    nameKey: "settings.integrations.modules.rconCommands.name",
    purposeKey: "settings.integrations.modules.rconCommands.purpose",
    viewPermission: "can_view_rcon_chat_commands_config",
    changePermission: "can_change_rcon_chat_commands_config",
    icon: SecurityOutlinedIcon,
  },
  {
    slug: "gtx-server",
    category: "others",
    type: "gtx-server",
    command: "server_name_change_config",
    legacyPath: "/settings/others/gtx-server",
    group: "communication",
    kind: "hosting",
    nameKey: "settings.integrations.modules.gtxServer.name",
    purposeKey: "settings.integrations.modules.gtxServer.purpose",
    viewPermission: "can_view_server_name_change_config",
    changePermission: "can_change_server_name_change_config",
    icon: DnsOutlinedIcon,
  },
];

export const integrationGroups = [
  {
    id: "discord",
    labelKey: "settings.integrations.groups.discord",
  },
  {
    id: "communication",
    labelKey: "settings.integrations.groups.communication",
  },
];

export const getIntegrationBySlug = (slug) =>
  integrationModules.find((module) => module.slug === slug);

export const getIntegrationByCommand = (command) =>
  integrationModules.find((module) => module.command === command);

export const getIntegrationByLegacyPath = (path) =>
  integrationModules.find((module) => module.legacyPath === path);
