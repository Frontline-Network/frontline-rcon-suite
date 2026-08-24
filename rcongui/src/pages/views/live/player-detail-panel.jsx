import { useEffect, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import ContentCopyOutlinedIcon from "@mui/icons-material/ContentCopyOutlined";
import GavelIcon from "@mui/icons-material/Gavel";
import PersonSearchOutlinedIcon from "@mui/icons-material/PersonSearchOutlined";
import SportsEsportsOutlinedIcon from "@mui/icons-material/SportsEsportsOutlined";
import { ActionButton } from "@/features/player-action/ActionMenu";
import {
  generatePlayerActions,
  blacklistAction,
  kickAction,
  messageAction,
  punishAction,
} from "@/features/player-action/actions";
import { getPlatformLabel } from "@/constants/platforms";
import { getTeamkillRisk } from "@/utils/teamkill-risk.mjs";

const EMPTY_VALUE = "–";
const DEFAULT_PRIMARY_ACTIONS = [
  messageAction,
  punishAction,
  kickAction,
  blacklistAction,
];
const LEGACY_BAN_ACTIONS = new Set(["Temp Ban", "Perma Ban"]);

const asFiniteNumber = (value, fallback = 0) => {
  const parsed = Number(value);
  return Number.isFinite(parsed) ? parsed : fallback;
};

const formatPlaytime = (seconds) => {
  const totalMinutes = Math.max(0, Math.floor(asFiniteNumber(seconds) / 60));
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;

  if (hours > 0) return `${hours}h ${String(minutes).padStart(2, "0")}m`;
  return `${minutes}m`;
};

const countRecentActions = (actions) => {
  const earliest = Date.now() - 24 * 60 * 60 * 1000;
  return actions.filter((action) => {
    const timestamp = Date.parse(action?.time);
    return Number.isFinite(timestamp) && timestamp > earliest;
  }).length;
};

/**
 * Builds the stable display model used by the expanded live-player row.
 * Live data differs slightly between HLL, HLL: Vietnam and older CRCON
 * versions, so every nested field is optional and normalized here.
 */
export const getPlayerDetailModel = (value = {}) => {
  const player = value && typeof value === "object" ? value : {};
  const profile =
    player.profile && typeof player.profile === "object" ? player.profile : {};
  const kills = asFiniteNumber(player.kills);
  const deaths = asFiniteNumber(player.deaths);
  const playtimeSeconds = asFiniteNumber(
    player.map_playtime_seconds ??
      player.current_playtime_seconds ??
      profile.current_playtime_seconds
  );
  const calculatedKpm =
    playtimeSeconds > 0 ? kills / (playtimeSeconds / 60) : 0;
  const receivedActions = Array.isArray(profile.received_actions)
    ? profile.received_actions
    : [];
  const banDetails = Array.isArray(player.activeBanStatus?.details)
    ? player.activeBanStatus.details
    : [];
  const hasActiveBan = Boolean(player.activeBanStatus?.isActive);

  return {
    name: player.name ?? profile.name ?? EMPTY_VALUE,
    playerId: player.player_id ?? profile.player_id ?? EMPTY_VALUE,
    platform:
      getPlatformLabel(
        player.platform ?? profile.platform ?? profile.soldier?.platform
      ) ?? EMPTY_VALUE,
    clan:
      player.clan_tag ??
      profile.clan_tag ??
      profile.soldier?.clan_tag ??
      EMPTY_VALUE,
    team: player.team ?? EMPTY_VALUE,
    unit: player.unit_name ?? player.unit ?? EMPTY_VALUE,
    role: player.role ?? EMPTY_VALUE,
    level: player.level ?? profile.soldier?.level ?? EMPTY_VALUE,
    kills,
    deaths,
    kd:
      player.kill_death_ratio == null
        ? deaths > 0
          ? kills / deaths
          : kills
        : asFiniteNumber(player.kill_death_ratio),
    kpm: asFiniteNumber(player.kills_per_minute, calculatedKpm),
    teamkillRisk: getTeamkillRisk(player),
    playtime: formatPlaytime(playtimeSeconds),
    scores: {
      combat: asFiniteNumber(player.combat),
      offense: asFiniteNumber(player.offense),
      defense: asFiniteNumber(player.defense),
      support: asFiniteNumber(player.support),
    },
    isVip: Boolean(player.is_vip || profile.vips?.length),
    isWatched: Boolean(profile.watchlist?.is_watched),
    warningsCount: countRecentActions(receivedActions),
    bansCount: hasActiveBan ? Math.max(1, banDetails.length) : 0,
  };
};

const InlineFact = ({ label, value, icon, grow = false, children }) => (
  <Stack
    direction="row"
    alignItems="center"
    spacing={0.55}
    sx={{
      minWidth: 0,
      flex: grow ? "1 1 220px" : "0 1 auto",
      whiteSpace: "nowrap",
    }}
  >
    {icon}
    <Typography variant="caption" sx={{ color: "text.secondary" }}>
      {label}
    </Typography>
    {children ?? (
      <Typography variant="caption" noWrap title={String(value)}>
        {value}
      </Typography>
    )}
  </Stack>
);

const Stat = ({ label, value, tone = "text.primary" }) => (
  <Box
    sx={(theme) => ({
      borderLeft: `1px solid ${theme.palette.divider}`,
      minWidth: 0,
      px: { xs: 0.7, sm: 1 },
      textAlign: "center",
    })}
  >
    <Typography
      component="span"
      variant="caption"
      sx={{ color: "text.secondary", display: "block", lineHeight: 1.15 }}
    >
      {label}
    </Typography>
    <Typography
      component="strong"
      variant="caption"
      sx={{
        color: tone,
        display: "block",
        fontVariantNumeric: "tabular-nums",
        lineHeight: 1.35,
        mt: 0.2,
      }}
    >
      {value}
    </Typography>
  </Box>
);

const StatusFact = ({ label, value, tone = "text.primary" }) => (
  <Box
    sx={(theme) => ({
      borderLeft: `1px solid ${theme.palette.divider}`,
      minWidth: 58,
      px: 1,
    })}
  >
    <Typography
      component="span"
      variant="caption"
      sx={{ color: "text.secondary", display: "block", lineHeight: 1.15 }}
    >
      {label}
    </Typography>
    <Typography
      component="strong"
      variant="caption"
      sx={{ color: tone, display: "block", lineHeight: 1.35, mt: 0.2 }}
    >
      {value}
    </Typography>
  </Box>
);

const CopyPlayerId = ({ playerId }) => {
  const { t } = useTranslation();
  const [copied, setCopied] = useState(false);
  const canCopy =
    playerId !== EMPTY_VALUE &&
    typeof navigator !== "undefined" &&
    typeof navigator.clipboard?.writeText === "function";

  useEffect(() => {
    if (!copied) return undefined;
    const timeout = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timeout);
  }, [copied]);

  const handleCopy = async (event) => {
    event.stopPropagation();
    if (!canCopy) return;

    try {
      await navigator.clipboard.writeText(playerId);
      setCopied(true);
    } catch {
      setCopied(false);
    }
  };

  const copyLabel = `${t("common.copy")} ${t("views.table.playerId")}`;

  return (
    <Stack direction="row" alignItems="center" spacing={0.25} minWidth={0}>
      <Typography
        component="code"
        variant="caption"
        noWrap
        title={playerId}
        sx={{ color: "text.secondary", maxWidth: "24ch" }}
      >
        {playerId}
      </Typography>
      <Tooltip title={copied ? t("common.copied") : copyLabel}>
        <span>
          <IconButton
            aria-label={copyLabel}
            disabled={!canCopy}
            onClick={handleCopy}
            size="small"
            sx={{ width: 24, height: 24 }}
          >
            {copied ? (
              <CheckIcon color="success" sx={{ fontSize: "0.9rem" }} />
            ) : (
              <ContentCopyOutlinedIcon sx={{ fontSize: "0.9rem" }} />
            )}
          </IconButton>
        </span>
      </Tooltip>
    </Stack>
  );
};

/**
 * Flat, container-responsive detail band for one expanded live-player row.
 * `renderActions` can replace the built-in CRCON controls while retaining the
 * same information hierarchy.
 */
export default function PlayerDetailPanel({
  player = {},
  online = true,
  actions,
  primaryActions = DEFAULT_PRIMARY_ACTIONS,
  onOpenProfile,
  renderActions,
}) {
  const { t } = useTranslation();
  const detail = useMemo(() => getPlayerDetailModel(player), [player]);
  const availableActions = useMemo(
    () =>
      actions ??
      generatePlayerActions({ multiAction: false, onlineAction: online }),
    [actions, online]
  );
  const visiblePrimaryActions = useMemo(
    () => primaryActions.filter((action) => availableActions.includes(action)),
    [availableActions, primaryActions]
  );
  const secondaryActions = useMemo(
    () =>
      availableActions.filter(
        (action) =>
          !visiblePrimaryActions.includes(action) &&
          !LEGACY_BAN_ACTIONS.has(action.name)
      ),
    [availableActions, visiblePrimaryActions]
  );

  const compactActionLabel = (action) => {
    if (action === messageAction) return t("actions.sendMessage.compact");
    if (action === punishAction) return t("actions.punish.compact");
    if (action === kickAction) return t("actions.kick.compact");
    if (action === blacklistAction) return t("actions.blacklist.compact");
    return action.translationKey
      ? t(`${action.translationKey}.name`)
      : action.name;
  };

  const teamLabel = t(`views.team.${detail.team}`, {
    defaultValue: detail.team,
  });
  const roleLabel = t(`roles.${detail.role}`, {
    defaultValue: detail.role,
  });
  const yesLabel = t("common.yes", { defaultValue: "Ja" });
  const noLabel = t("common.no", { defaultValue: "Nein" });
  const noneLabel = t("common.none", { defaultValue: "Keine" });
  const riskColor =
    detail.teamkillRisk.level === "high"
      ? "error.main"
      : detail.teamkillRisk.level === "caution"
      ? "warning.main"
      : "text.primary";

  const actionContent = renderActions ? (
    renderActions({
      player,
      online,
      primaryActions: visiblePrimaryActions,
      secondaryActions,
    })
  ) : (
    <Stack direction="row" flexWrap="wrap" gap={0.5} alignItems="center">
      {visiblePrimaryActions.map((action) => (
        <ActionButton
          key={action.name}
          action={action}
          icon={action === blacklistAction ? GavelIcon : undefined}
          label={compactActionLabel(action)}
          recipients={player}
          variant="outlined"
          sx={{
            fontSize: "0.72rem",
            minHeight: 28,
            px: 0.75,
            whiteSpace: "nowrap",
          }}
        />
      ))}
      {onOpenProfile ? (
        <Button
          onClick={() => onOpenProfile(player)}
          size="small"
          startIcon={<PersonSearchOutlinedIcon />}
          variant="outlined"
          sx={{
            fontSize: "0.72rem",
            minHeight: 28,
            px: 0.75,
            whiteSpace: "nowrap",
          }}
        >
          {t("actions.viewProfileCompact", { defaultValue: "Profil" })}
        </Button>
      ) : null}
    </Stack>
  );

  return (
    <Box
      component="section"
      data-testid="live-player-detail-panel"
      aria-label={`${t("views.table.playerSummary")}: ${detail.name}`}
      sx={(theme) => ({
        // Match the neutral anthracite used by the squad and player rows.
        bgcolor: "background.paper",
        borderLeft: `3px solid ${theme.palette.primary.main}`,
        boxShadow: `inset 0 1px 0 ${theme.palette.divider}`,
        minWidth: 0,
        textAlign: "left",
      })}
    >
      <Stack
        direction="row"
        alignItems="center"
        flexWrap="wrap"
        gap={{ xs: 0.75, sm: 1.25 }}
        sx={(theme) => ({
          minHeight: 34,
          px: 1.25,
          py: 0.55,
          "& > :not(:first-of-type)": {
            borderLeft: `1px solid ${theme.palette.divider}`,
            pl: { xs: 0.75, sm: 1.25 },
          },
        })}
      >
        <InlineFact
          icon={
            <SportsEsportsOutlinedIcon
              aria-hidden="true"
              sx={{ color: "text.secondary", fontSize: "0.95rem" }}
            />
          }
          label=""
          value={detail.platform}
        />
        <InlineFact label={`${t("views.table.playerId")}:`} grow>
          <CopyPlayerId playerId={detail.playerId} />
        </InlineFact>
        <InlineFact
          label={`${t("views.table.clanTag")}:`}
          value={detail.clan}
        />
        <InlineFact label={`${t("views.table.team")}:`} value={teamLabel} />
        <InlineFact label={`${t("views.table.unit")}:`} value={detail.unit} />
        <InlineFact label={`${t("views.table.role")}:`} value={roleLabel} />
      </Stack>

      <Box
        sx={(theme) => ({
          borderBottom: `1px solid ${theme.palette.divider}`,
          borderTop: `1px solid ${theme.palette.divider}`,
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 58px), 1fr))",
          minHeight: 48,
          py: 0.65,
        })}
      >
        <Stat label={t("views.table.level")} value={detail.level} />
        <Stat label={t("views.table.kills")} value={detail.kills} />
        <Stat label={t("views.table.deaths")} value={detail.deaths} />
        <Stat label="K/D" value={detail.kd.toFixed(2)} />
        <Stat label="KPM" value={detail.kpm.toFixed(2)} />
        <Stat
          label={t("views.table.teamKillsShort")}
          value={detail.teamkillRisk.count}
          tone={riskColor}
        />
        <Stat
          label={t("views.table.combatShort")}
          value={detail.scores.combat}
        />
        <Stat
          label={t("views.table.offenseShort")}
          value={detail.scores.offense}
        />
        <Stat
          label={t("views.table.defenseShort")}
          value={detail.scores.defense}
        />
        <Stat
          label={t("views.table.supportShort")}
          value={detail.scores.support}
        />
        <Stat label={t("views.table.timeShort")} value={detail.playtime} />
      </Box>

      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{ minHeight: 42, px: 1.25, py: 0.65 }}
      >
        <Stack direction="row" flexWrap="wrap" alignItems="center">
          <StatusFact
            label={t("views.table.vip")}
            value={detail.isVip ? yesLabel : noLabel}
            tone={detail.isVip ? "warning.main" : "text.primary"}
          />
          <StatusFact
            label={t("views.live.watched")}
            value={detail.isWatched ? yesLabel : noLabel}
            tone={detail.isWatched ? "primary.light" : "text.primary"}
          />
          <StatusFact
            label={t("views.table.warnings")}
            value={detail.warningsCount || noneLabel}
            tone={detail.warningsCount ? "warning.main" : "text.primary"}
          />
        </Stack>
        <Box sx={{ flex: "0 0 auto" }}>{actionContent}</Box>
      </Stack>
    </Box>
  );
}
