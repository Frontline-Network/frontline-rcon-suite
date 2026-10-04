import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { alpha } from "@mui/material/styles";
import { useTranslation } from "react-i18next";
import { useQuery } from "@tanstack/react-query";
import {
  Box,
  Button,
  CircularProgress,
  Chip,
  LinearProgress,
  Divider,
  Stack,
  Typography,
} from "@mui/material";
import AdminPanelSettingsRoundedIcon from "@mui/icons-material/AdminPanelSettingsRounded";
import BalanceRoundedIcon from "@mui/icons-material/BalanceRounded";
import CheckCircleRoundedIcon from "@mui/icons-material/CheckCircleRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import ErrorRoundedIcon from "@mui/icons-material/ErrorRounded";
import FlagRoundedIcon from "@mui/icons-material/FlagRounded";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import LoginRoundedIcon from "@mui/icons-material/LoginRounded";
import LogoutRoundedIcon from "@mui/icons-material/LogoutRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import RadioButtonCheckedRoundedIcon from "@mui/icons-material/RadioButtonCheckedRounded";
import ReportProblemRoundedIcon from "@mui/icons-material/ReportProblemRounded";
import ShieldRoundedIcon from "@mui/icons-material/ShieldRounded";
import StarRoundedIcon from "@mui/icons-material/StarRounded";
import SwapHorizRoundedIcon from "@mui/icons-material/SwapHorizRounded";
import VisibilityRoundedIcon from "@mui/icons-material/VisibilityRounded";
import WarningAmberRoundedIcon from "@mui/icons-material/WarningAmberRounded";
import dayjs from "dayjs";

import { teamsLiveQuery } from "@/queries/teams-live-query";
import { useGlobalStore } from "@/stores/global-state";
import { CONNECTION_STATE } from "@/utils/connectionHealth";
import { resolveMapImageName } from "@/utils/map-images.mjs";
import { buildLiveBalanceStatus } from "@/pages/views/team/live-balance.mjs";
import { useAuth } from "@/hooks/useAuth";
import { canUse, liveMapRequest } from "@/pages/views/live-map/api";

const TEAM_NAMES = ["allies", "axis"];
const TEAM_TONES = { allies: "info.main", axis: "error.main" };
const MAX_VISIBLE_TASKS = 5;

const EVENT_META = {
  ADMIN_REPORTS: {
    label: "dashboard.operations.events.labels.adminReport",
    tone: "error.main",
    icon: ErrorRoundedIcon,
    state: "dashboard.operations.events.states.open",
  },
  CONNECTED: {
    label: "dashboard.operations.events.labels.joined",
    tone: "info.main",
    icon: LoginRoundedIcon,
    state: "dashboard.operations.events.states.info",
  },
  DISCONNECTED: {
    label: "dashboard.operations.events.labels.left",
    tone: "text.secondary",
    icon: LogoutRoundedIcon,
    state: "dashboard.operations.events.states.info",
  },
  TEAMSWITCH: {
    label: "dashboard.operations.events.labels.teamSwitch",
    tone: "warning.main",
    icon: SwapHorizRoundedIcon,
    state: "dashboard.operations.events.states.info",
  },
  "TEAM KILL": {
    label: "dashboard.operations.events.labels.teamKill",
    tone: "warning.main",
    icon: WarningAmberRoundedIcon,
    state: "dashboard.operations.events.states.review",
  },
  "MATCH START": {
    label: "dashboard.operations.events.labels.matchStart",
    tone: "primary.main",
    icon: MapRoundedIcon,
    state: "dashboard.operations.events.states.info",
  },
  "MATCH ENDED": {
    label: "dashboard.operations.events.labels.matchEnd",
    tone: "primary.main",
    icon: FlagRoundedIcon,
    state: "dashboard.operations.events.states.info",
  },
  "ADMIN KICKED": {
    label: "dashboard.operations.events.labels.adminAction",
    tone: "warning.main",
    icon: AdminPanelSettingsRoundedIcon,
    state: "dashboard.operations.events.states.done",
  },
  "ADMIN BANNED": {
    label: "dashboard.operations.events.labels.adminAction",
    tone: "warning.main",
    icon: AdminPanelSettingsRoundedIcon,
    state: "dashboard.operations.events.states.done",
  },
};

const panelSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.paper",
  borderRadius: (theme) => `${theme.frontline.geometry.radius.structure}px`,
  minWidth: 0,
  overflow: "hidden",
};

const formatDuration = (seconds, fallback) => {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return fallback;
  return dayjs.duration(Math.max(0, value), "seconds").format("HH:mm:ss");
};

function PanelHeader({ title, helper, action, id }) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      alignItems={{ sm: "baseline" }}
      justifyContent="space-between"
      spacing={0.5}
      sx={{
        px: 2,
        py: 1.4,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Stack direction="row" alignItems="baseline" spacing={1.5} minWidth={0}>
        <Typography
          id={id}
          component="h2"
          variant="h6"
          sx={(theme) => ({
            color:
              theme.frontline.appearance.preset === "wardogs"
                ? "text.primary"
                : "primary.main",
          })}
        >
          {title}
        </Typography>
        {helper ? (
          <Typography variant="caption" color="text.secondary">
            {helper}
          </Typography>
        ) : null}
      </Stack>
      {action}
    </Stack>
  );
}

function EmptyState({ children }) {
  return (
    <Stack
      alignItems="center"
      justifyContent="center"
      spacing={1}
      sx={{ p: 4 }}
    >
      <CheckCircleRoundedIcon color="success" />
      <Typography variant="body2" color="text.secondary" textAlign="center">
        {children}
      </Typography>
    </Stack>
  );
}

function TaskRow({ task, t }) {
  const Icon = task.icon;
  return (
    <Box
      data-testid={`operations-task-${task.key}`}
      sx={{
        display: "grid",
        gridTemplateColumns: "36px minmax(0, 1fr) auto",
        alignItems: "center",
        gap: 1.5,
        p: 2,
        borderBottom: 1,
        borderColor: "divider",
        "&:last-of-type": { borderBottom: 0 },
        "&:hover": { bgcolor: "action.hover" },
      }}
    >
      <Box
        sx={{
          display: "grid",
          placeItems: "center",
          width: 36,
          height: 36,
          bgcolor: "action.hover",
          borderRadius: "6px",
        }}
      >
        <Icon sx={{ color: task.tone, fontSize: 21 }} aria-hidden />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Stack
          direction="row"
          alignItems="center"
          gap={1}
          flexWrap="wrap"
          sx={{ mb: 0.5 }}
        >
          <Typography
            component="h3"
            variant="subtitle2"
            sx={{ overflowWrap: "anywhere" }}
          >
            {t(task.titleKey)}
          </Typography>
          <Typography variant="caption" sx={{ color: task.tone }}>
            {t(task.priorityKey)}
          </Typography>
        </Stack>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{
            overflowWrap: "anywhere",
            display: "-webkit-box",
            WebkitLineClamp: 2,
            WebkitBoxOrient: "vertical",
            overflow: "hidden",
          }}
          title={task.context}
        >
          {task.context}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {task.age}
        </Typography>
      </Box>
      <Button
        component={Link}
        to={task.to}
        endIcon={<ChevronRightRoundedIcon />}
        sx={{ minWidth: 0, minHeight: 40, px: 1.25, whiteSpace: "nowrap" }}
      >
        {t(task.actionKey)}
      </Button>
    </Box>
  );
}

function TeamStrength({ team, count, rating, noLeaderCount, t }) {
  const teamKey = team === "allies" ? "dashboard.allies" : "dashboard.axis";
  return (
    <Stack alignItems="center" spacing={0.6} sx={{ minWidth: 0, px: 1 }}>
      <Stack direction="row" alignItems="center" spacing={0.75}>
        <ShieldRoundedIcon sx={{ color: TEAM_TONES[team] }} aria-hidden />
        <Typography
          component="h3"
          variant="h6"
          sx={{ color: TEAM_TONES[team] }}
        >
          {t(teamKey)}
        </Typography>
      </Stack>
      <Typography component="p" variant="h4">
        {count}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase" }}
      >
        {t("dashboard.operations.teamStatus.players")}
      </Typography>
      <Divider flexItem sx={{ my: 0.5 }} />
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase" }}
      >
        {t("dashboard.operations.teamStatus.strengthIndex")}
      </Typography>
      <Typography component="p" variant="h3" sx={{ color: TEAM_TONES[team] }}>
        {rating}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase" }}
      >
        {t("dashboard.operations.teamStatus.withoutLeader", {
          count: noLeaderCount,
        })}
      </Typography>
    </Stack>
  );
}

function EventRow({ event, language, t }) {
  const meta = EVENT_META[event.group] ??
    EVENT_META[event.action] ?? {
      label: "dashboard.operations.events.labels.activity",
      tone: "text.secondary",
      icon: RadioButtonCheckedRoundedIcon,
      state: "dashboard.operations.events.states.info",
    };
  const Icon = meta.icon;
  const time = Number(event.timestamp)
    ? new Date(event.timestamp).toLocaleTimeString(language, {
        hour: "2-digit",
        minute: "2-digit",
      })
    : t("common.unknown");
  const fallbackMessage = event.user_1?.name
    ? t("dashboard.operations.events.playerContext", {
        player: event.user_1.name,
      })
    : t("dashboard.operations.events.noContext");

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "58px 28px 170px minmax(0, 1fr) 72px",
        columnGap: 1,
        alignItems: "center",
        minHeight: 48,
        px: 2,
        py: 1,
        "&:hover": { bgcolor: "action.hover" },
        borderBottom: "1px solid",
        borderColor: "divider",
        "&:last-of-type": { borderBottom: 0 },
      }}
    >
      <Typography variant="caption" color="text.secondary">
        {time}
      </Typography>
      <Icon sx={{ color: meta.tone, fontSize: 18 }} aria-hidden />
      <Typography
        component="p"
        variant="subtitle2"
        sx={{ textTransform: "uppercase" }}
        noWrap
      >
        {t(meta.label)}
      </Typography>
      <Typography
        variant="body2"
        color="text.secondary"
        title={event.message || fallbackMessage}
        sx={{
          overflowWrap: "anywhere",
          display: "-webkit-box",
          WebkitLineClamp: 2,
          WebkitBoxOrient: "vertical",
          overflow: "hidden",
        }}
      >
        {event.message || fallbackMessage}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          color: meta.tone,
          textTransform: "uppercase",
          textAlign: "right",
        }}
      >
        {t(meta.state)}
      </Typography>
    </Box>
  );
}

export default function OperationsOverview({ logs, logsLoading }) {
  const { t, i18n } = useTranslation();
  const { permissions } = useAuth();
  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const status = useGlobalStore((state) => state.status);
  const serverState = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const onlinePlayers = useGlobalStore((state) => state.onlinePlayers);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const canSeeTacticalCases =
    canUse(permissions, "can_view_live_map") &&
    canUse(permissions, "can_view_live_map_cases");
  const tacticalDetections = useQuery({
    queryKey: ["live-map", window.location.origin, "dashboard-detections"],
    queryFn: () => liveMapRequest("detections?status=open&limit=20"),
    enabled: canSeeTacticalCases,
    retry: false,
    refetchInterval: 15000,
  });
  const { data: teams, isLoading: teamsLoading } = teamsLiveQuery({
    staleTime: 15_000,
    refetchInterval: false,
  });
  const [mapImageFailed, setMapImageFailed] = useState(false);
  const currentMap = gameState?.current_map;
  const nextMap = gameState?.next_map;
  const imageName = resolveMapImageName(currentMap);

  useEffect(() => setMapImageFailed(false), [imageName]);

  const noLeaderSquads = useMemo(
    () =>
      TEAM_NAMES.flatMap((team) =>
        Object.entries(teams?.[team]?.squads ?? {})
          .filter(
            ([, squad]) => squad?.has_leader === false && squad?.players?.length
          )
          .map(([name, squad]) => ({ team, name, squad }))
      ),
    [teams]
  );
  const noLeaderCounts = useMemo(
    () => ({
      allies: noLeaderSquads.filter((squad) => squad.team === "allies").length,
      axis: noLeaderSquads.filter((squad) => squad.team === "axis").length,
    }),
    [noLeaderSquads]
  );
  const balance = useMemo(() => buildLiveBalanceStatus(teams), [teams]);
  const strengthGap = balance
    ? Math.abs(balance.team_ratings.allies - balance.team_ratings.axis)
    : 0;
  const needsBalance = Boolean(
    balance &&
      (balance.required_switches > 0 ||
        strengthGap > balance.strength_thresholds.soft_limit)
  );
  const advantagedTeam = balance
    ? balance.required_switches > 0
      ? balance.team_counts.allies >= balance.team_counts.axis
        ? "allies"
        : "axis"
      : balance.team_ratings.allies >= balance.team_ratings.axis
      ? "allies"
      : "axis"
    : null;
  const adminReport = logs.find((group) => group.group === "ADMIN_REPORTS")
    ?.logs?.[0];
  const notablePlayer = onlinePlayers.find(
    (player) => player?.profile?.watchlist?.is_watched || player?.is_vip
  );
  const reviewDetection = (tacticalDetections.data?.detections || [])
    .filter((item) => ["review", "high"].includes(item.severity))
    .sort((a, b) => {
      const priority = { high: 2, review: 1 };
      return (
        priority[b.severity] - priority[a.severity] || b.last_at - a.last_at
      );
    })[0];

  const tasks = useMemo(() => {
    const taskAge = (timestamp) => {
      if (!Number(timestamp)) return t("dashboard.operations.tasks.now");
      const minutes = Math.max(
        1,
        Math.round((Date.now() - timestamp) / 60_000)
      );
      return t("dashboard.operations.tasks.minutes", { count: minutes });
    };
    const result = [];
    if (reviewDetection) {
      result.push({
        key: `tactical-${reviewDetection.id}`,
        priorityKey:
          reviewDetection.severity === "high"
            ? "dashboard.operations.priorities.high"
            : "dashboard.operations.priorities.medium",
        titleKey: "dashboard.operations.tasks.gameplayPattern",
        context: t("dashboard.operations.tasks.gameplayPatternContext", {
          player: reviewDetection.player_name || reviewDetection.player_id,
          count: reviewDetection.evidence?.signals?.length || 0,
        }),
        age: taskAge(reviewDetection.last_at * 1000),
        actionKey: "dashboard.operations.tasks.reviewReplay",
        to: `/views/live-map?round=${encodeURIComponent(
          reviewDetection.round_id
        )}&time=${reviewDetection.last_at}&player=${encodeURIComponent(
          reviewDetection.player_id
        )}`,
        tone:
          reviewDetection.severity === "high" ? "error.main" : "warning.main",
        icon: ShieldRoundedIcon,
      });
    }
    if (adminReport) {
      result.push({
        key: "admin-report",
        priorityKey: "dashboard.operations.priorities.high",
        titleKey: "dashboard.operations.tasks.adminReport",
        context:
          adminReport.message ||
          t("dashboard.operations.tasks.player", {
            player: adminReport.user_1?.name || t("common.unknown"),
          }),
        age: taskAge(adminReport.timestamp),
        actionKey: "dashboard.operations.tasks.review",
        to: "/records/game-logs",
        tone: "error.main",
        icon: ErrorRoundedIcon,
      });
    }
    if (noLeaderSquads.length) {
      const first = noLeaderSquads[0];
      result.push({
        key: "no-leader",
        priorityKey: "dashboard.operations.priorities.medium",
        titleKey: "dashboard.operations.tasks.noLeader",
        context: t("dashboard.operations.tasks.squadContext", {
          squad: first.name.toUpperCase(),
          team: t(
            first.team === "allies" ? "dashboard.allies" : "dashboard.axis"
          ),
          count: noLeaderSquads.length,
        }),
        age: t("dashboard.operations.tasks.live"),
        actionKey: "dashboard.operations.tasks.assign",
        to: "/views/team",
        tone: "warning.main",
        icon: WarningAmberRoundedIcon,
      });
    }
    if (needsBalance) {
      result.push({
        key: "balance",
        priorityKey: "dashboard.operations.priorities.medium",
        titleKey: "dashboard.operations.tasks.balance",
        context: t("dashboard.operations.tasks.balanceContext", {
          allies: Math.round(balance.team_ratings.allies),
          axis: Math.round(balance.team_ratings.axis),
        }),
        age: t("dashboard.operations.tasks.live"),
        actionKey: "dashboard.operations.tasks.balanceAction",
        to: "/views/team",
        tone: "primary.main",
        icon: BalanceRoundedIcon,
      });
    }
    if (notablePlayer) {
      const watched = notablePlayer?.profile?.watchlist?.is_watched;
      result.push({
        key: "notable-player",
        priorityKey: "dashboard.operations.priorities.low",
        titleKey: watched
          ? "dashboard.operations.tasks.watchlistArrival"
          : "dashboard.operations.tasks.vipArrival",
        context: t("dashboard.operations.tasks.player", {
          player: notablePlayer.name,
        }),
        age: t("dashboard.operations.tasks.live"),
        actionKey: "dashboard.operations.tasks.observe",
        to: "/views/live",
        tone: "success.main",
        icon: watched ? VisibilityRoundedIcon : StarRoundedIcon,
      });
    }
    return result.slice(0, MAX_VISIBLE_TASKS);
  }, [
    adminReport,
    balance,
    needsBalance,
    noLeaderSquads,
    notablePlayer,
    reviewDetection,
    t,
  ]);

  const attentionCount = tasks.filter(
    (task) => task.key !== "notable-player"
  ).length;
  const primaryTask = tasks.find((task) => task.key !== "notable-player");
  const situationItems = [
    adminReport
      ? t("dashboard.operations.situation.adminReports", { count: 1 })
      : null,
    noLeaderSquads.length
      ? t("dashboard.operations.situation.leaderlessSquads", {
          count: noLeaderSquads.length,
        })
      : null,
    needsBalance
      ? t("dashboard.operations.situation.balanceNotices", { count: 1 })
      : null,
    reviewDetection
      ? t("dashboard.operations.situation.playerReviewNotices", { count: 1 })
      : null,
  ].filter(Boolean);
  const situationSummary = new Intl.ListFormat(language, {
    style: "long",
    type: "conjunction",
  }).format(situationItems);
  const serverName =
    status?.name ||
    status?.short_name ||
    serverState?.name ||
    serverState?.short_name ||
    t("dashboard.unknownServer");
  const mapName = currentMap?.pretty_name || t("matchStatus.unknownMap");
  const nextMapName = nextMap?.pretty_name || t("common.unknown");
  const remaining = formatDuration(
    gameState?.time_remaining,
    t("common.unknown")
  );
  const currentPlayers = status?.current_players;
  const maxPlayers = status?.max_players;
  const players =
    currentPlayers != null && maxPlayers != null
      ? `${currentPlayers}/${maxPlayers}`
      : t("common.unknown");
  const isOnline =
    connectionHealth.gameServer.state === CONNECTION_STATE.ONLINE;
  const statusHelper = connectionHealth.gameServer.lastSuccessAt
    ? t("dashboard.lastUpdated", {
        time: new Date(
          connectionHealth.gameServer.lastSuccessAt
        ).toLocaleTimeString(language),
      })
    : t("dashboard.noLiveData");
  const statusLabel = t(
    `connectionStates.${
      connectionHealth.gameServer.state || CONNECTION_STATE.UNKNOWN
    }`
  );
  const allEvents = useMemo(
    () =>
      logs
        .flatMap((group) =>
          (group.logs ?? []).map((log) => ({ ...log, group: group.group }))
        )
        .sort((left, right) => Number(right.timestamp) - Number(left.timestamp))
        .slice(0, 7),
    [logs]
  );

  const verdict = !balance
    ? {
        title: t("dashboard.operations.teamStatus.noData"),
        description: t("dashboard.operations.teamStatus.noDataDescription"),
        tone: "text.secondary",
      }
    : needsBalance
    ? {
        title: t("dashboard.operations.teamStatus.advantage", {
          team: t(
            advantagedTeam === "allies" ? "dashboard.allies" : "dashboard.axis"
          ),
        }),
        description:
          balance.required_switches > 0
            ? t("dashboard.operations.teamStatus.moveRecommendation", {
                count: balance.required_switches,
                team: t(
                  advantagedTeam === "allies"
                    ? "dashboard.axis"
                    : "dashboard.allies"
                ),
              })
            : t("dashboard.operations.teamStatus.strengthRecommendation"),
        tone: "warning.main",
      }
    : {
        title: t("dashboard.operations.teamStatus.balanced"),
        description: t("dashboard.operations.teamStatus.balancedDescription"),
        tone: "success.main",
      };

  const statusTone = isOnline
    ? "success"
    : connectionHealth.gameServer.state === CONNECTION_STATE.OFFLINE
    ? "error"
    : "warning";
  const situationTone = tasks.some((task) => task.priorityKey.endsWith(".high"))
    ? "error"
    : attentionCount
    ? "warning"
    : "success";
  const playerFill =
    Number(maxPlayers) > 0 && currentPlayers != null
      ? Math.min(
          100,
          Math.max(0, (Number(currentPlayers) / Number(maxPlayers)) * 100)
        )
      : null;

  return (
    <Stack spacing={2.5} data-testid="operations-overview">
      <Box
        component="section"
        aria-labelledby="current-match-title"
        data-testid="battle-overview"
        sx={panelSx}
      >
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "minmax(0, 1fr)",
              md: "minmax(220px, .7fr) minmax(0, 2fr)",
            },
          }}
        >
          <Box
            sx={{
              position: "relative",
              minHeight: { xs: 180, md: 290 },
              overflow: "hidden",
              bgcolor: "background.default",
            }}
          >
            {imageName && !mapImageFailed ? (
              <Box
                component="img"
                src={`/maps/${imageName}`}
                onError={() => setMapImageFailed(true)}
                alt={mapName}
                sx={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  objectFit: "cover",
                  filter: "saturate(.85) brightness(.8)",
                }}
              />
            ) : (
              <Box
                sx={{ display: "grid", placeItems: "center", height: "100%" }}
              >
                <MapRoundedIcon sx={{ fontSize: 56, color: "text.disabled" }} />
              </Box>
            )}
            <Box
              sx={{
                position: "absolute",
                inset: 0,
                background:
                  "linear-gradient(180deg, transparent 45%, rgba(0,0,0,.65))",
              }}
            />
            <Typography
              variant="overline"
              sx={{
                position: "absolute",
                bottom: 20,
                left: 24,
                color: "#fff",
                letterSpacing: ".12em",
              }}
            >
              {t("dashboard.operations.round.title")}
            </Typography>
          </Box>
          <Stack gap={2.5} sx={{ p: { xs: 2, md: 3 }, minWidth: 0 }}>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="start"
              gap={2}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography
                  id="current-match-title"
                  component="h2"
                  variant="subtitle2"
                  color="text.secondary"
                  sx={{ mb: 0.75 }}
                >
                  {serverName}
                </Typography>
                <Typography
                  component="p"
                  variant="h4"
                  sx={{
                    fontSize: { xs: 25, lg: 32 },
                    lineHeight: 1.2,
                    overflowWrap: "anywhere",
                  }}
                >
                  {mapName}
                </Typography>
              </Box>
              <Chip
                size="small"
                label={statusLabel}
                color={statusTone}
                variant="outlined"
                icon={<RadioButtonCheckedRoundedIcon />}
              />
            </Stack>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns:
                  "minmax(0, .8fr) minmax(0, 1fr) minmax(0, 1.4fr)",
                gap: 2,
                py: 0.5,
              }}
            >
              <Box sx={{ minWidth: 0 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.players")}
                </Typography>
                <Typography
                  component="p"
                  variant="h5"
                  sx={{ mt: 0.5, fontVariantNumeric: "tabular-nums" }}
                >
                  {players}
                </Typography>
                {playerFill !== null && (
                  <LinearProgress
                    aria-label={t("dashboard.players")}
                    variant="determinate"
                    value={playerFill}
                    sx={{ mt: 1, maxWidth: 150, height: 3 }}
                  />
                )}
              </Box>
              <Box
                sx={{
                  minWidth: 0,
                  pl: 2,
                  borderLeft: 1,
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {t("matchStatus.remaining")}
                </Typography>
                <Typography
                  component="p"
                  variant="h5"
                  sx={{ mt: 0.5, fontVariantNumeric: "tabular-nums" }}
                >
                  {remaining}
                </Typography>
              </Box>
              <Box
                sx={{
                  minWidth: 0,
                  pl: 2,
                  borderLeft: 1,
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.operations.round.nextMap")}
                </Typography>
                <Typography
                  component="p"
                  variant="subtitle1"
                  sx={{ mt: 0.5, overflowWrap: "anywhere", lineHeight: 1.35 }}
                >
                  {nextMapName}
                </Typography>
              </Box>
            </Box>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              gap={1.5}
              flexWrap="wrap"
              sx={{ mt: "auto" }}
            >
              <Stack direction="row" gap={1}>
                <Button
                  component={Link}
                  to="/views/live"
                  variant="contained"
                  startIcon={<VisibilityRoundedIcon />}
                >
                  {t("dashboard.openLive")}
                </Button>
                <Button
                  component={Link}
                  to="/views/team"
                  variant="outlined"
                  startIcon={<GroupsRoundedIcon />}
                >
                  {t("dashboard.operations.round.teams")}
                </Button>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {statusHelper}
              </Typography>
            </Stack>
          </Stack>
        </Box>
      </Box>

      <Stack
        component="section"
        aria-labelledby="shift-situation-title"
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        gap={2}
        sx={(theme) => ({
          ...panelSx,
          p: 2.5,
          borderLeft: `3px solid ${theme.palette[situationTone].main}`,
          backgroundImage: `linear-gradient(100deg, ${alpha(
            theme.palette[situationTone].main,
            0.055
          )}, transparent 70%)`,
        })}
      >
        {attentionCount ? (
          <ReportProblemRoundedIcon
            color={situationTone}
            sx={{ fontSize: 28 }}
          />
        ) : (
          <CheckCircleRoundedIcon color="success" sx={{ fontSize: 28 }} />
        )}
        <Box sx={{ flex: 1, minWidth: 0 }}>
          <Typography
            id="shift-situation-title"
            component="h2"
            variant="caption"
            color="text.secondary"
          >
            {t("dashboard.operations.situation.title")}
          </Typography>
          <Typography component="p" variant="h6" sx={{ mt: 0.25 }}>
            {attentionCount
              ? t("dashboard.operations.situation.attention", {
                  count: attentionCount,
                })
              : t("dashboard.operations.situation.clear")}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {attentionCount
              ? t("dashboard.operations.situation.summary", {
                  details: situationSummary,
                })
              : t("dashboard.operations.situation.clearSummary")}
          </Typography>
        </Box>
        {primaryTask && (
          <Button
            component={Link}
            to={primaryTask.to}
            variant="outlined"
            endIcon={<ChevronRightRoundedIcon />}
            sx={{ flexShrink: 0, minHeight: 40 }}
          >
            {t(primaryTask.actionKey)}
          </Button>
        )}
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            lg: "minmax(0, 1.1fr) minmax(0, 1fr)",
          },
          gap: 2.5,
          alignItems: "stretch",
        }}
      >
        <Stack
          component="section"
          aria-labelledby="open-tasks-title"
          sx={panelSx}
        >
          <PanelHeader
            id="open-tasks-title"
            title={t("dashboard.operations.tasks.title")}
            helper={t("dashboard.operations.tasks.sorted")}
          />
          <Box sx={{ flex: 1 }}>
            {logsLoading || teamsLoading ? (
              <Stack
                alignItems="center"
                justifyContent="center"
                sx={{ minHeight: 200 }}
              >
                <CircularProgress size={26} />
              </Stack>
            ) : tasks.length ? (
              tasks.map((task) => <TaskRow key={task.key} task={task} t={t} />)
            ) : (
              <EmptyState>{t("dashboard.operations.tasks.empty")}</EmptyState>
            )}
          </Box>
          <Button
            component={Link}
            to="/records/game-logs"
            fullWidth
            endIcon={<ChevronRightRoundedIcon />}
            sx={{
              borderTop: 1,
              borderColor: "divider",
              borderRadius: 0,
              minHeight: 44,
            }}
          >
            {t("dashboard.operations.tasks.all")}
          </Button>
        </Stack>
        <Stack
          component="section"
          aria-labelledby="live-team-status-title"
          sx={panelSx}
        >
          <PanelHeader
            id="live-team-status-title"
            title={t("dashboard.operations.teamStatus.title")}
          />
          {teamsLoading ? (
            <Stack
              alignItems="center"
              justifyContent="center"
              sx={{ minHeight: 210 }}
            >
              <CircularProgress size={26} />
            </Stack>
          ) : balance ? (
            <>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                  py: 2,
                  flex: 1,
                  "& > :first-of-type": {
                    borderRight: 1,
                    borderColor: "divider",
                  },
                }}
              >
                <TeamStrength
                  team="allies"
                  count={balance.team_counts.allies}
                  rating={Math.round(balance.team_ratings.allies)}
                  noLeaderCount={noLeaderCounts.allies}
                  t={t}
                />
                <TeamStrength
                  team="axis"
                  count={balance.team_counts.axis}
                  rating={Math.round(balance.team_ratings.axis)}
                  noLeaderCount={noLeaderCounts.axis}
                  t={t}
                />
              </Box>
              <Stack
                direction="row"
                alignItems="center"
                gap={1.5}
                sx={{
                  p: 2,
                  borderTop: 1,
                  borderColor: "divider",
                  bgcolor: "action.hover",
                }}
              >
                <BalanceRoundedIcon
                  sx={{ color: verdict.tone, fontSize: 26 }}
                />
                <Box sx={{ minWidth: 0 }}>
                  <Typography
                    component="p"
                    variant="subtitle2"
                    sx={{ color: verdict.tone }}
                  >
                    {verdict.title}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.5 }}
                  >
                    {verdict.description}
                  </Typography>
                </Box>
              </Stack>
            </>
          ) : (
            <EmptyState>
              {t("dashboard.operations.teamStatus.noDataDescription")}
            </EmptyState>
          )}
        </Stack>
      </Box>

      <Box
        component="section"
        aria-labelledby="recent-events-title"
        sx={panelSx}
      >
        <PanelHeader
          id="recent-events-title"
          title={t("dashboard.operations.events.title")}
          helper={t("dashboard.operations.events.helper")}
        />
        {logsLoading ? (
          <Stack
            alignItems="center"
            justifyContent="center"
            sx={{ minHeight: 180 }}
          >
            <CircularProgress size={26} />
          </Stack>
        ) : allEvents.length ? (
          allEvents.map((event, index) => (
            <EventRow
              key={`${event.group}-${event.timestamp}-${index}`}
              event={event}
              language={language}
              t={t}
            />
          ))
        ) : (
          <EmptyState>{t("dashboard.operations.events.empty")}</EmptyState>
        )}
        <Button
          component={Link}
          to="/records/game-logs"
          fullWidth
          endIcon={<ChevronRightRoundedIcon />}
          sx={{
            borderTop: 1,
            borderColor: "divider",
            borderRadius: 0,
            minHeight: 44,
          }}
        >
          {t("dashboard.operations.events.all")}
        </Button>
      </Box>
    </Stack>
  );
}
