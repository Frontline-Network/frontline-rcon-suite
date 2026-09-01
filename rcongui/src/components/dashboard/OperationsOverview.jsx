import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  CircularProgress,
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
import { buildLiveBalanceStatus } from "@/pages/views/team/live-balance.mjs";

const TEAM_NAMES = ["allies", "axis"];
const TEAM_TONES = { allies: "info.main", axis: "error.main" };

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
  borderRadius: 0,
  minWidth: 0,
};

const formatDuration = (seconds, fallback) => {
  const value = Number(seconds);
  if (!Number.isFinite(value)) return fallback;
  return dayjs.duration(Math.max(0, value), "seconds").format("HH:mm:ss");
};

const environmentTranslationKey = (environment) => {
  const known = new Set(["day", "night", "dusk", "dawn", "rain", "overcast"]);
  return known.has(environment)
    ? `dashboard.operations.environments.${environment}`
    : null;
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
        <Typography id={id} component="h2" variant="h6" color="primary.main">
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
        gridTemplateColumns: "96px minmax(0, 1fr) 64px 112px",
        minHeight: 66,
        borderBottom: "1px solid",
        borderColor: "divider",
        "&:last-of-type": { borderBottom: 0 },
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={0.75}
        sx={{ px: 1.5, borderRight: "1px solid", borderColor: "divider" }}
      >
        <Icon sx={{ color: task.tone, fontSize: 22 }} aria-hidden />
        <Typography
          variant="caption"
          sx={{ color: task.tone, textTransform: "uppercase" }}
        >
          {t(task.priorityKey)}
        </Typography>
      </Stack>
      <Stack justifyContent="center" sx={{ px: 1.5, minWidth: 0 }}>
        <Typography
          variant="subtitle2"
          sx={{ textTransform: "uppercase" }}
          noWrap
        >
          {t(task.titleKey)}
        </Typography>
        <Typography variant="body2" color="text.secondary" noWrap>
          {task.context}
        </Typography>
      </Stack>
      <Stack alignItems="center" justifyContent="center">
        <Typography variant="caption" color="text.secondary">
          {task.age}
        </Typography>
      </Stack>
      <Button
        component={Link}
        to={task.to}
        color="primary"
        endIcon={<ChevronRightRoundedIcon />}
        sx={{
          borderLeft: "1px solid",
          borderColor: "divider",
          borderRadius: 0,
        }}
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
        <Typography variant="h6" sx={{ color: TEAM_TONES[team] }}>
          {t(teamKey)}
        </Typography>
      </Stack>
      <Typography variant="h4">{count}</Typography>
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
      <Typography variant="h3" sx={{ color: TEAM_TONES[team] }}>
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
        gridTemplateColumns: "58px 28px 190px minmax(0, 1fr) 72px",
        alignItems: "center",
        minHeight: 38,
        px: 1.5,
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
        variant="subtitle2"
        sx={{ textTransform: "uppercase" }}
        noWrap
      >
        {t(meta.label)}
      </Typography>
      <Typography variant="body2" color="text.secondary" noWrap>
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
  const language = i18n.resolvedLanguage === "en" ? "en" : "de";
  const status = useGlobalStore((state) => state.status);
  const serverState = useGlobalStore((state) => state.serverState);
  const gameState = useGlobalStore((state) => state.gameState);
  const onlinePlayers = useGlobalStore((state) => state.onlinePlayers);
  const connectionHealth = useGlobalStore((state) => state.connectionHealth);
  const { data: teams, isLoading: teamsLoading } = teamsLiveQuery({
    staleTime: 15_000,
    refetchInterval: false,
  });
  const [mapImageFailed, setMapImageFailed] = useState(false);
  const currentMap = gameState?.current_map;
  const nextMap = gameState?.next_map;
  const imageName = currentMap?.image_name;

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
    return result.slice(0, 4);
  }, [adminReport, balance, needsBalance, noLeaderSquads, notablePlayer, t]);

  const attentionCount = tasks.filter(
    (task) => task.key !== "notable-player"
  ).length;
  const primaryTask = tasks.find((task) => task.key !== "notable-player");
  const serverName =
    status?.name ||
    status?.short_name ||
    serverState?.name ||
    serverState?.short_name ||
    t("dashboard.unknownServer");
  const mapName = currentMap?.pretty_name || t("matchStatus.unknownMap");
  const nextMapName = nextMap?.pretty_name || t("common.unknown");
  const mode = currentMap?.game_mode || t("common.unknown");
  const environmentKey = environmentTranslationKey(currentMap?.environment);
  const environment = environmentKey
    ? t(environmentKey)
    : currentMap?.environment || t("common.unknown");
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
              advantagedTeam === "allies"
                ? "dashboard.allies"
                : "dashboard.axis"
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

  return (
    <Stack spacing={1.5} data-testid="operations-overview">
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            md: "minmax(0, 1.05fr) minmax(360px, 0.95fr)",
          },
          gap: 1.5,
        }}
      >
        <Stack
          component="section"
          aria-labelledby="shift-situation-title"
          justifyContent="space-between"
          sx={{ ...panelSx, p: 2.5, minHeight: 210 }}
        >
          <Box>
            <Typography
              id="shift-situation-title"
              component="h2"
              variant="h6"
              color="primary.main"
            >
              {t("dashboard.operations.situation.title")}
            </Typography>
            <Typography
              variant="h2"
              sx={{
                mt: 0.8,
                color: attentionCount ? "error.main" : "success.main",
                textTransform: "uppercase",
              }}
            >
              {attentionCount
                ? t("dashboard.operations.situation.attention", {
                    count: attentionCount,
                  })
                : t("dashboard.operations.situation.clear")}
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 1, maxWidth: 720 }}>
              {attentionCount
                ? t("dashboard.operations.situation.summary", {
                    reports: adminReport ? 1 : 0,
                    squads: noLeaderSquads.length,
                    balance: needsBalance ? 1 : 0,
                  })
                : t("dashboard.operations.situation.clearSummary")}
            </Typography>
          </Box>
          {primaryTask ? (
            <Button
              component={Link}
              to={primaryTask.to}
              variant="contained"
              startIcon={<ReportProblemRoundedIcon />}
              endIcon={<ChevronRightRoundedIcon />}
              sx={{ alignSelf: "flex-start", minWidth: 280, mt: 2 }}
            >
              {t(primaryTask.actionKey)}
            </Button>
          ) : (
            <Stack
              direction="row"
              alignItems="center"
              spacing={1}
              sx={{ mt: 2 }}
            >
              <CheckCircleRoundedIcon color="success" />
              <Typography variant="subtitle2" color="success.main">
                {t("dashboard.operations.situation.noAction")}
              </Typography>
            </Stack>
          )}
        </Stack>

        <Box
          component="section"
          aria-labelledby="current-match-title"
          sx={panelSx}
        >
          <Stack direction="row" sx={{ minHeight: 210, height: "100%" }}>
            {imageName && !mapImageFailed ? (
              <Box
                component="img"
                src={`/maps/${imageName}`}
                onError={() => setMapImageFailed(true)}
                alt={`${mapName} · ${environment}`}
                sx={{
                  width: "48%",
                  minWidth: 210,
                  objectFit: "cover",
                  filter: "saturate(0.75) contrast(1.08) brightness(0.72)",
                  borderRight: "1px solid",
                  borderColor: "divider",
                }}
              />
            ) : (
              <Stack
                alignItems="center"
                justifyContent="center"
                sx={{
                  width: "48%",
                  minWidth: 210,
                  bgcolor: "background.default",
                  color: "text.secondary",
                  borderRight: "1px solid",
                  borderColor: "divider",
                }}
              >
                <MapRoundedIcon sx={{ fontSize: 48 }} />
              </Stack>
            )}
            <Stack
              justifyContent="space-between"
              sx={{ flex: 1, minWidth: 0, p: 2 }}
            >
              <Box>
                <Typography
                  id="current-match-title"
                  component="h2"
                  variant="overline"
                  color="primary.main"
                >
                  {t("dashboard.operations.match.title")}
                </Typography>
                <Typography
                  variant="h4"
                  sx={{ textTransform: "uppercase" }}
                  noWrap
                >
                  {mapName}
                </Typography>
                <Typography
                  variant="caption"
                  color="primary.light"
                  sx={{ textTransform: "uppercase" }}
                >
                  {mode} · {environment}
                </Typography>
              </Box>
              <Divider sx={{ my: 1.5 }} />
              <Stack
                direction="row"
                divider={<Divider orientation="vertical" flexItem />}
                spacing={1.5}
              >
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: "uppercase" }}
                  >
                    {t("dashboard.players")}
                  </Typography>
                  <Typography variant="h5">{players}</Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: "uppercase" }}
                  >
                    {t("matchStatus.remaining")}
                  </Typography>
                  <Typography variant="h5">{remaining}</Typography>
                </Box>
                <Box sx={{ flex: 1 }}>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: "uppercase" }}
                  >
                    {t("dashboard.status")}
                  </Typography>
                  <Stack direction="row" alignItems="center" spacing={0.7}>
                    <RadioButtonCheckedRoundedIcon
                      sx={{
                        color: isOnline ? "success.main" : "error.main",
                        fontSize: 14,
                      }}
                    />
                    <Typography variant="h6">{statusLabel}</Typography>
                  </Stack>
                </Box>
              </Stack>
            </Stack>
          </Stack>
        </Box>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            md: "minmax(0, 1.05fr) minmax(360px, 0.95fr)",
          },
          gap: 1.5,
        }}
      >
        <Box
          component="section"
          aria-labelledby="open-tasks-title"
          sx={panelSx}
        >
          <PanelHeader
            id="open-tasks-title"
            title={t("dashboard.operations.tasks.title")}
            helper={t("dashboard.operations.tasks.sorted")}
          />
          <Box
            aria-hidden
            sx={{
              display: "grid",
              gridTemplateColumns: "96px minmax(0, 1fr) 64px 112px",
              px: 1.5,
              minHeight: 30,
              alignItems: "center",
              borderBottom: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="caption" color="text.secondary">
              {t("dashboard.operations.tasks.columns.priority")}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ pl: 1.5 }}
            >
              {t("dashboard.operations.tasks.columns.context")}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              textAlign="center"
            >
              {t("dashboard.operations.tasks.columns.age")}
            </Typography>
            <Typography
              variant="caption"
              color="text.secondary"
              textAlign="center"
            >
              {t("dashboard.operations.tasks.columns.action")}
            </Typography>
          </Box>
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
          <Button
            component={Link}
            to="/records/game-logs"
            fullWidth
            endIcon={<ChevronRightRoundedIcon />}
            sx={{
              borderTop: "1px solid",
              borderColor: "divider",
              borderRadius: 0,
            }}
          >
            {t("dashboard.operations.tasks.all")}
          </Button>
        </Box>

        <Stack spacing={1.5}>
          <Box
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
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns:
                    "minmax(0, 1fr) minmax(0, 1fr) minmax(190px, 1.1fr)",
                  py: 2,
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
                <Stack
                  alignItems="center"
                  justifyContent="center"
                  spacing={0.8}
                  sx={{
                    px: 2,
                    borderLeft: "1px solid",
                    borderColor: "divider",
                    textAlign: "center",
                  }}
                >
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    sx={{ textTransform: "uppercase" }}
                  >
                    {t("dashboard.operations.teamStatus.verdict")}
                  </Typography>
                  <BalanceRoundedIcon
                    sx={{ color: verdict.tone, fontSize: 34 }}
                  />
                  <Typography variant="h6" sx={{ color: verdict.tone }}>
                    {verdict.title}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {verdict.description}
                  </Typography>
                </Stack>
              </Box>
            ) : (
              <EmptyState>
                {t("dashboard.operations.teamStatus.noDataDescription")}
              </EmptyState>
            )}
          </Box>

          <Box
            component="section"
            aria-labelledby="current-round-title"
            sx={panelSx}
          >
            <PanelHeader
              id="current-round-title"
              title={t("dashboard.operations.round.title")}
            />
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns:
                  "110px minmax(0, 1fr) 112px minmax(0, 1fr)",
                alignItems: "stretch",
                minHeight: 96,
              }}
            >
              {imageName && !mapImageFailed ? (
                <Box
                  component="img"
                  src={`/maps/${imageName}`}
                  alt=""
                  sx={{
                    width: 110,
                    height: "100%",
                    objectFit: "cover",
                    filter: "saturate(0.7) brightness(0.72)",
                  }}
                />
              ) : (
                <Stack
                  alignItems="center"
                  justifyContent="center"
                  sx={{ bgcolor: "background.default" }}
                >
                  <MapRoundedIcon color="disabled" />
                </Stack>
              )}
              <Stack
                justifyContent="center"
                sx={{
                  px: 1.5,
                  borderRight: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.operations.round.map")}
                </Typography>
                <Typography variant="subtitle2" noWrap>
                  {mapName}
                </Typography>
                <Typography variant="caption" color="primary.light">
                  {mode} · {environment}
                </Typography>
              </Stack>
              <Stack
                justifyContent="center"
                sx={{
                  px: 1.5,
                  borderRight: "1px solid",
                  borderColor: "divider",
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {t("matchStatus.remaining")}
                </Typography>
                <Typography variant="h6">{remaining}</Typography>
              </Stack>
              <Stack justifyContent="center" sx={{ px: 1.5 }}>
                <Typography variant="caption" color="text.secondary">
                  {t("dashboard.operations.round.nextMap")}
                </Typography>
                <Typography variant="subtitle2" noWrap>
                  {nextMapName}
                </Typography>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {serverName}
                </Typography>
              </Stack>
            </Box>
            <Stack
              direction="row"
              sx={{ borderTop: "1px solid", borderColor: "divider" }}
            >
              <Button
                component={Link}
                to="/views/live"
                variant="contained"
                startIcon={<VisibilityRoundedIcon />}
                sx={{ flex: 1, borderRadius: 0 }}
              >
                {t("dashboard.openLive")}
              </Button>
              <Button
                component={Link}
                to="/views/team"
                startIcon={<GroupsRoundedIcon />}
                sx={{ flex: 1, borderRadius: 0 }}
              >
                {t("dashboard.operations.round.teams")}
              </Button>
            </Stack>
          </Box>
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
            borderTop: "1px solid",
            borderColor: "divider",
            borderRadius: 0,
          }}
        >
          {t("dashboard.operations.events.all")}
        </Button>
      </Box>
    </Stack>
  );
}
