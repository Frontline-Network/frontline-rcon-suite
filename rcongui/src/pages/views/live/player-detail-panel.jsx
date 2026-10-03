import { useMemo } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  Stack,
  Typography,
  alpha,
} from "@mui/material";
import GavelIcon from "@mui/icons-material/Gavel";
import PersonSearchOutlinedIcon from "@mui/icons-material/PersonSearchOutlined";
import SportsEsportsOutlinedIcon from "@mui/icons-material/SportsEsportsOutlined";
import StarBorderRoundedIcon from "@mui/icons-material/StarBorderRounded";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import { ActionButton } from "@/features/player-action/ActionMenu";
import {
  generatePlayerActions,
  blacklistAction,
  kickAction,
  messageAction,
  punishAction,
} from "@/features/player-action/actions";
import { getPlatformLabel } from "@/constants/platforms";
import { getPlayerIdentity } from "@/utils/player-identity.mjs";
import PlayerIdentifiers from "@/components/player/profile/Identifiers";
import { getTeamkillRisk } from "@/utils/teamkill-risk.mjs";
import { countRecentWarnings } from "@/utils/player-warnings.mjs";
import { formatRoleLabel, formatSquadLabel } from "./player-display-labels";

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
      getPlatformLabel(getPlayerIdentity(player).platform) || EMPTY_VALUE,
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
    warningsCount: countRecentWarnings(receivedActions),
    bansCount: hasActiveBan ? Math.max(1, banDetails.length) : 0,
  };
};

const InlineFact = ({ label, value, icon, grow = false, children }) => (
  <Stack
    className="player-detail-inline-fact"
    direction="row"
    alignItems="center"
    spacing={0.55}
    sx={{
      minWidth: 0,
      flex: grow ? "1 1 180px" : "0 1 auto",
      whiteSpace: "nowrap",
    }}
  >
    {icon}
    {label ? (
      <Typography variant="caption" sx={{ color: "text.secondary" }}>
        {label}
      </Typography>
    ) : null}
    {children ?? (
      <Typography
        variant="caption"
        noWrap
        title={String(value)}
        sx={{ fontWeight: 600 }}
      >
        {value}
      </Typography>
    )}
  </Stack>
);

const Stat = ({ label, value, tone = "text.primary" }) => (
  <Box
    className="player-detail-stat"
    sx={(theme) => ({
      alignContent: "center",
      borderLeft: `1px solid ${theme.palette.divider}`,
      display: "grid",
      minHeight: 44,
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
        fontSize: "0.78rem",
        fontWeight: 700,
        fontVariantNumeric: "tabular-nums",
        lineHeight: 1.35,
        mt: 0.2,
      }}
    >
      {value}
    </Typography>
  </Box>
);

const StatusFact = ({ label, value, tone = "text.primary", icon }) => (
  <Stack
    className="player-detail-status"
    direction="row"
    alignItems="center"
    spacing={0.7}
    sx={(theme) => ({
      bgcolor: alpha(theme.palette.common.white, 0.025),
      border: `1px solid ${alpha(theme.palette.common.white, 0.09)}`,
      borderRadius: 0,
      minHeight: 34,
      minWidth: 82,
      px: 0.85,
      py: 0.35,
    })}
  >
    <Box aria-hidden="true" sx={{ color: tone, display: "flex" }}>
      {icon}
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Typography
        component="span"
        variant="caption"
        sx={{ color: "text.secondary", display: "block", lineHeight: 1.05 }}
      >
        {label}
      </Typography>
      <Typography
        component="strong"
        variant="caption"
        sx={{ color: tone, display: "block", fontWeight: 700, lineHeight: 1.25 }}
      >
        {value}
      </Typography>
    </Box>
  </Stack>
);

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
  onActionStart,
  renderActions,
}) {
  const { t, i18n } = useTranslation();
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
  const roleLabel = formatRoleLabel(t, detail.role);
  const unitLabel = formatSquadLabel(detail.unit);
  const yesLabel = t("common.yes", { defaultValue: "Ja" });
  const noLabel = t("common.no", { defaultValue: "Nein" });
  const noneLabel = t("common.none", { defaultValue: "Keine" });
  const riskColor =
    detail.teamkillRisk.level === "high"
      ? "error.main"
      : detail.teamkillRisk.level === "caution"
      ? "warning.main"
      : "text.primary";
  const decimalFormatter = useMemo(
    () =>
      new Intl.NumberFormat(i18n.resolvedLanguage || i18n.language || "de", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
    [i18n.language, i18n.resolvedLanguage]
  );

  const actionContent = renderActions ? (
    renderActions({
      player,
      online,
      primaryActions: visiblePrimaryActions,
      secondaryActions,
    })
  ) : (
    <Stack
      className="player-detail-actions"
      direction="row"
      flexWrap="wrap"
      justifyContent="flex-end"
      gap={0.6}
      alignItems="center"
    >
      {visiblePrimaryActions.map((action) => (
        <ActionButton
          key={action.name}
          action={action}
          icon={action === blacklistAction ? GavelIcon : undefined}
          label={compactActionLabel(action)}
          onBeforeAction={onActionStart}
          recipients={player}
          variant="outlined"
          color={action === blacklistAction ? "warning" : "inherit"}
          sx={{
            fontSize: "0.72rem",
            minHeight: 34,
            px: 0.9,
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
          color="inherit"
          sx={{
            fontSize: "0.72rem",
            minHeight: 34,
            px: 0.9,
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
        bgcolor: alpha(theme.palette.background.paper, 0.98),
        borderBottom: `1px solid ${theme.palette.divider}`,
        borderLeft: `3px solid ${theme.palette.primary.main}`,
        borderTop: `1px solid ${alpha(theme.palette.primary.main, 0.3)}`,
        boxShadow: `inset 0 1px 0 ${alpha(theme.palette.common.white, 0.035)}`,
        boxSizing: "border-box",
        containerName: "player-detail",
        containerType: "inline-size",
        left: 0,
        maxWidth: "100cqi",
        minWidth: 0,
        overflow: "visible",
        overflowAnchor: "none",
        position: "sticky",
        scrollMarginTop: "9rem",
        textAlign: "left",
        width: "100cqi",
      })}
    >
      <Box
        className="player-detail-identity"
        sx={(theme) => ({
          backgroundColor: alpha(theme.palette.common.white, 0.012),
          display: "grid",
          gridTemplateColumns:
            "minmax(280px, 1.35fr) minmax(130px, 0.65fr) minmax(300px, 1.35fr)",
          minHeight: 34,
          "& > .player-detail-group": {
            alignItems: "center",
            display: "flex",
            gap: 1,
            minWidth: 0,
            px: 1.25,
            py: 0.7,
          },
          "& > .player-detail-group + .player-detail-group": {
            borderLeft: `1px solid ${alpha(theme.palette.divider, 0.72)}`,
          },
          "@container player-detail (max-width: 900px)": {
            gridTemplateColumns: "minmax(0, 1.35fr) minmax(130px, 0.65fr)",
            "& .player-id-copy": {
              height: 44,
              minHeight: 44,
              minWidth: 44,
              width: 44,
            },
            "& > .player-detail-context": {
              borderLeft: 0,
              borderTop: `1px solid ${theme.palette.divider}`,
              gridColumn: "1 / -1",
            },
          },
          "@container player-detail (max-width: 600px)": {
            gridTemplateColumns: "minmax(0, 1fr)",
            "& > .player-detail-group": {
              alignItems: "flex-start",
              flexWrap: "wrap",
            },
            "& > .player-detail-group + .player-detail-group": {
              borderLeft: 0,
              borderTop: `1px solid ${theme.palette.divider}`,
            },
            "& > .player-detail-context": { gridColumn: "auto" },
            "& .player-detail-inline-fact": {
              minWidth: 0,
              whiteSpace: "normal",
            },
          },
        })}
      >
        <Stack className="player-detail-group" direction="row" sx={{ flexWrap: "wrap" }}>
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
          <PlayerIdentifiers player={player} />
        </Stack>
        <Stack className="player-detail-group" direction="row">
          <InlineFact
            label={`${t("views.table.clanTag")}:`}
            value={detail.clan}
          />
        </Stack>
        <Stack
          className="player-detail-group player-detail-context"
          direction="row"
          flexWrap="wrap"
        >
          <InlineFact
            label={`${t("views.table.faction", {
              defaultValue: "Fraktion",
            })}:`}
            value={teamLabel}
          />
          <InlineFact label={`${t("views.table.unit")}:`} value={unitLabel} />
          <InlineFact label={`${t("views.table.role")}:`} value={roleLabel} />
        </Stack>
      </Box>

      <Box
        sx={(theme) => ({
          backgroundColor: alpha(theme.palette.common.black, 0.08),
          borderBottom: `1px solid ${theme.palette.divider}`,
          borderTop: `1px solid ${theme.palette.divider}`,
          display: "grid",
          gridTemplateColumns: "repeat(11, minmax(54px, 1fr))",
          minHeight: 48,
          py: 0.55,
          "& > .player-detail-stat:first-of-type": { borderLeft: 0 },
          "@container player-detail (max-width: 760px)": {
            gridTemplateColumns: "repeat(6, minmax(58px, 1fr))",
            "& > .player-detail-stat:nth-of-type(6n + 1)": { borderLeft: 0 },
            "& > .player-detail-stat:nth-of-type(n + 7)": {
              borderTop: `1px solid ${theme.palette.divider}`,
              pt: 0.65,
            },
          },
          "@container player-detail (max-width: 520px)": {
            gridTemplateColumns: "repeat(4, minmax(58px, 1fr))",
            "& > .player-detail-stat": {
              borderLeft: `1px solid ${theme.palette.divider}`,
            },
            "& > .player-detail-stat:nth-of-type(4n + 1)": { borderLeft: 0 },
            "& > .player-detail-stat:nth-of-type(n + 5)": {
              borderTop: `1px solid ${theme.palette.divider}`,
              pt: 0.65,
            },
          },
          "@container player-detail (max-width: 360px)": {
            gridTemplateColumns: "repeat(3, minmax(58px, 1fr))",
            "& > .player-detail-stat": {
              borderLeft: `1px solid ${theme.palette.divider}`,
            },
            "& > .player-detail-stat:nth-of-type(3n + 1)": { borderLeft: 0 },
            "& > .player-detail-stat:nth-of-type(n + 4)": {
              borderTop: `1px solid ${theme.palette.divider}`,
              pt: 0.65,
            },
          },
        })}
      >
        <Stat label={t("views.table.level")} value={detail.level} />
        <Stat label={t("views.table.kills")} value={detail.kills} />
        <Stat label={t("views.table.deaths")} value={detail.deaths} />
        <Stat label="K/D" value={decimalFormatter.format(detail.kd)} />
        <Stat label="KPM" value={decimalFormatter.format(detail.kpm)} />
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

      <Box
        className="player-detail-footer"
        sx={(theme) => ({
          alignItems: "center",
          backgroundColor: alpha(theme.palette.common.white, 0.012),
          display: "grid",
          gap: 1,
          gridTemplateColumns: "minmax(290px, auto) minmax(0, 1fr)",
          minHeight: 44,
          px: 1.25,
          py: 0.75,
          "& .player-detail-actions": { minWidth: 0 },
          "& .player-detail-actions .MuiButton-root": {
            bgcolor: alpha(theme.palette.common.white, 0.025),
            borderColor: alpha(theme.palette.common.white, 0.14),
            borderRadius: 0,
            boxShadow: "none",
            "&:hover": {
              bgcolor: alpha(theme.palette.primary.main, 0.08),
              borderColor: alpha(theme.palette.primary.main, 0.55),
            },
          },
          "@container player-detail (max-width: 850px)": {
            alignItems: "stretch",
            gridTemplateColumns: "minmax(0, 1fr)",
            "& .player-detail-actions": { justifyContent: "flex-start" },
            "& .player-detail-actions .MuiButton-root": { minHeight: 44 },
          },
          "@container player-detail (max-width: 600px)": {
            "& .player-id-copy": {
              height: 44,
              minHeight: 44,
              minWidth: 44,
              width: 44,
            },
            "& .player-detail-actions > *": { flex: "1 1 9rem", minWidth: 0 },
            "& .player-detail-actions .MuiButton-root": {
              minHeight: 44,
              width: "100%",
            },
          },
        })}
      >
        <Stack direction="row" flexWrap="wrap" alignItems="center" gap={0.55}>
          <StatusFact
            label={t("views.table.vip")}
            value={detail.isVip ? yesLabel : noLabel}
            tone={detail.isVip ? "warning.main" : "text.primary"}
            icon={<StarBorderRoundedIcon sx={{ fontSize: "1rem" }} />}
          />
          <StatusFact
            label={t("views.live.watched")}
            value={detail.isWatched ? yesLabel : noLabel}
            tone={detail.isWatched ? "primary.light" : "text.primary"}
            icon={<VisibilityOutlinedIcon sx={{ fontSize: "1rem" }} />}
          />
          <StatusFact
            label={t("views.table.warnings")}
            value={detail.warningsCount || noneLabel}
            tone={detail.warningsCount ? "warning.main" : "text.primary"}
            icon={<WarningAmberRoundedIcon sx={{ fontSize: "1rem" }} />}
          />
        </Stack>
        <Box sx={{ minWidth: 0 }}>{actionContent}</Box>
      </Box>
    </Box>
  );
}
