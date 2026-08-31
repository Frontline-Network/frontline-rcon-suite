import {
  Box,
  Divider,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import { ActionIconButton } from "@/features/player-action/ActionMenu";
import {
  blacklistAction,
  kickAction,
  messageAction,
  punishAction,
} from "@/features/player-action/actions";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { getColoredFactionIconSrc } from "@/utils/lib";
import LinkedAccounts from "@/components/player/profile/LinkedAccounts";
import {
  formatSessionDuration,
  getPlayerKdr,
  getPlayerSessionSeconds,
  getRoleLabel,
  getTeamLabel,
} from "./live-session-utils";

const Metric = ({ label, value }) => (
  <Box
    sx={{
      minWidth: 0,
      px: 1,
      py: 1.1,
      borderRight: "1px solid",
      borderBottom: "1px solid",
      borderColor: "divider",
      "&:nth-of-type(3n)": { borderRight: 0 },
      "&:nth-last-of-type(-n+3)": { borderBottom: 0 },
    }}
  >
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
        display: "block",
        textTransform: "uppercase",
        letterSpacing: 0.8,
      }}
    >
      {label}
    </Typography>
    <Typography
      sx={{
        mt: 0.25,
        fontSize: "1rem",
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value}
    </Typography>
  </Box>
);

const ContextValue = ({ label, value, children }) => (
  <Box sx={{ minWidth: 0 }}>
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{
        display: "block",
        textTransform: "uppercase",
        letterSpacing: 0.8,
      }}
    >
      {label}
    </Typography>
    <Typography component="div" sx={{ mt: 0.25, overflowWrap: "anywhere" }}>
      {children ?? value ?? "–"}
    </Typography>
  </Box>
);

const InspectorAction = ({ action, player, label }) => (
  <ActionIconButton
    action={action}
    recipients={player}
    label={label}
    icon={
      <Stack alignItems="center" gap={0.35}>
        <action.icon sx={{ fontSize: 18 }} />
        <Typography
          variant="caption"
          sx={{ fontSize: "0.64rem", lineHeight: 1 }}
        >
          {label}
        </Typography>
      </Stack>
    }
    sx={{
      width: "100%",
      height: 50,
      border: "1px solid",
      borderColor: "divider",
      borderRadius: 0,
    }}
  />
);

export default function LiveSessionInspector({ player, t }) {
  const { openWithId } = usePlayerSidebar();

  if (!player) {
    return (
      <Box sx={{ p: 2, border: "1px solid", borderColor: "divider" }}>
        <Typography color="text.secondary">
          {t("stats.liveSessions.selectPlayerHint")}
        </Typography>
      </Box>
    );
  }

  const teamLabel = getTeamLabel(t, player.team);
  const sessionSeconds = getPlayerSessionSeconds(player);
  const actions = [
    [messageAction, t("stats.liveSessions.actions.message")],
    [punishAction, t("stats.liveSessions.actions.punish")],
    [kickAction, t("stats.liveSessions.actions.kick")],
    [blacklistAction, t("stats.liveSessions.actions.ban")],
  ];

  return (
    <Box
      sx={{
        minWidth: 0,
        border: "1px solid",
        borderColor: "divider",
        borderLeft: "2px solid",
        borderLeftColor: "primary.main",
        bgcolor: "background.paper",
      }}
    >
      <Stack direction="row" alignItems="center" gap={1.25} sx={{ p: 1.5 }}>
        <img
          src={getColoredFactionIconSrc(player.faction ?? player.team)}
          width={26}
          height={26}
          alt={teamLabel}
        />
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            component="h2"
            sx={{
              fontSize: "1rem",
              fontWeight: 600,
              overflow: "hidden",
              textOverflow: "ellipsis",
              whiteSpace: "nowrap",
            }}
          >
            {player.name}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {t("stats.liveSessions.livePlayer")}
          </Typography>
        </Box>
        <Tooltip title={t("stats.liveSessions.actions.profile")}>
          <IconButton
            aria-label={t("stats.liveSessions.actions.profile")}
            onClick={() => openWithId(player.player_id)}
            size="small"
            sx={{
              borderRadius: 0,
              border: "1px solid",
              borderColor: "divider",
            }}
          >
            <PersonOutlineIcon fontSize="small" />
          </IconButton>
        </Tooltip>
      </Stack>

      <Box sx={{ px: 1.5 }}>
        <LinkedAccounts
          player={{
            ...player.profile,
            player_id: player.player_id,
            name: player.name,
          }}
          compact
          showWarnings={false}
        />
      </Box>

      <Divider />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          gap: 1,
          px: 1.5,
          py: 1.25,
        }}
      >
        <ContextValue
          label={t("stats.liveSessions.faction")}
          value={teamLabel}
        />
        <ContextValue
          label={t("stats.liveSessions.unit")}
          value={
            player.unit_name === "unassigned"
              ? "–"
              : player.unit_name?.toUpperCase()
          }
        />
        <ContextValue
          label={t("stats.liveSessions.role")}
          value={getRoleLabel(t, player.role)}
        />
      </Box>

      <Divider />

      <Box sx={{ px: 1.5, py: 1.25 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "block",
            textTransform: "uppercase",
            letterSpacing: 0.8,
          }}
        >
          {t("stats.liveSessions.sessionTime")}
        </Typography>
        <Typography
          sx={{
            mt: 0.25,
            fontSize: "1.1rem",
            fontWeight: 600,
            fontVariantNumeric: "tabular-nums",
          }}
        >
          {formatSessionDuration(sessionSeconds)}
        </Typography>
      </Box>

      <Divider />

      <Box sx={{ px: 1.5, pt: 1.25 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ textTransform: "uppercase", letterSpacing: 0.8 }}
        >
          {t("stats.liveSessions.currentPerformance")}
        </Typography>
      </Box>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "repeat(3, minmax(0, 1fr))",
          mx: 1.5,
          my: 1.25,
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        <Metric
          label={t("stats.liveSessions.kills")}
          value={Number(player.kills) || 0}
        />
        <Metric
          label={t("stats.liveSessions.deaths")}
          value={Number(player.deaths) || 0}
        />
        <Metric
          label={t("stats.liveSessions.kdrShort")}
          value={getPlayerKdr(player).toFixed(2)}
        />
        <Metric
          label={t("stats.liveSessions.combatShort")}
          value={Number(player.combat) || 0}
        />
        <Metric
          label={t("stats.liveSessions.offenseShort")}
          value={Number(player.offense) || 0}
        />
        <Metric
          label={t("stats.liveSessions.supportShort")}
          value={Number(player.support) || 0}
        />
      </Box>

      <Divider />

      <Box sx={{ px: 1.5, py: 1.25 }}>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{
            display: "block",
            mb: 1,
            textTransform: "uppercase",
            letterSpacing: 0.8,
          }}
        >
          {t("stats.liveSessions.actionsTitle")}
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
            gap: 0.5,
          }}
        >
          {actions.map(([action, label]) => (
            <InspectorAction
              key={action.name}
              action={action}
              player={player}
              label={label}
            />
          ))}
          <IconButton
            aria-label={t("stats.liveSessions.actions.profile")}
            onClick={() => openWithId(player.player_id)}
            sx={{
              width: "100%",
              height: 50,
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
            }}
          >
            <Stack alignItems="center" gap={0.35}>
              <PersonOutlineIcon sx={{ fontSize: 18 }} />
              <Typography
                variant="caption"
                sx={{ fontSize: "0.64rem", lineHeight: 1 }}
              >
                {t("stats.liveSessions.actions.profile")}
              </Typography>
            </Stack>
          </IconButton>
        </Box>
      </Box>

      <Divider />

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: "1fr 1fr",
          gap: 1.25,
          px: 1.5,
          py: 1.25,
        }}
      >
        <ContextValue
          label={t("stats.liveSessions.level")}
          value={player.level}
        />
        <ContextValue
          label={t("stats.liveSessions.defenseShort")}
          value={Number(player.defense) || 0}
        />
        <Box sx={{ gridColumn: "1 / -1" }}>
          <ContextValue label={t("stats.liveSessions.playerId")}>
            <Stack direction="row" alignItems="center" gap={0.5}>
              <Box component="span" sx={{ overflowWrap: "anywhere" }}>
                {player.player_id}
              </Box>
              <Tooltip title={t("stats.liveSessions.copyPlayerId")}>
                <IconButton
                  aria-label={t("stats.liveSessions.copyPlayerId")}
                  onClick={() =>
                    navigator.clipboard?.writeText(player.player_id)
                  }
                  size="small"
                  sx={{ borderRadius: 0, p: 0.25 }}
                >
                  <ContentCopyIcon sx={{ fontSize: 14 }} />
                </IconButton>
              </Tooltip>
            </Stack>
          </ContextValue>
        </Box>
      </Box>
    </Box>
  );
}
