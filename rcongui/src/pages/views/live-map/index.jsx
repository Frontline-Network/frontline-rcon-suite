import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { Link } from "react-router-dom";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  Tab,
  Tabs,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import PageHeader from "@/components/shared/PageHeader";
import { useAuth } from "@/hooks/useAuth";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { getThemeTeamColor } from "@/themes/teamColors";
import { isFakeMode } from "@/mirage/demo-data";
import { normalizeGame } from "@/utils/game-context";
import TacticalMap from "./TacticalMap";
import CalibrationPanel from "./CalibrationPanel";
import ArchiveDialog from "./ArchiveDialog";
import DetectionPanel from "./DetectionPanel";
import DetectionSettings from "./DetectionSettings";
import ReplayControls from "./ReplayControls";
import { liveMapRequest, canUse } from "./api";
import {
  filterPlayers,
  frameAt,
  trailSegments,
  projectionReady,
} from "./geometry.mjs";
import { copy } from "./copy";
import { tacticalPollInterval, sampleAge, sampleIsStale } from "./polling.mjs";
import { visibleKillConnections } from "./kill-events.mjs";

const ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: true,
});
const panel = {
  border: 1,
  borderColor: "divider",
  bgcolor: "background.paper",
  minWidth: 0,
};
const localDateTime = (timestamp) => {
  const date = new Date(timestamp * 1000);
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
};

export default function LiveMapPage() {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage || i18n.language || "en").split("-")[0];
  const t = (key) => (copy[language] || copy.en)[key] || key;
  const { permissions } = useAuth();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("lg"));
  const client = useQueryClient();
  const queryKey = ["live-map", window.location.origin];
  const allowed = canUse(permissions, "can_view_live_map");
  const [selected, setSelected] = useState(null);
  const [tab, setTab] = useState(0);
  const [search, setSearch] = useState("");
  const [team, setTeam] = useState("all");
  const [squad, setSquad] = useState("all");
  const [showPlayers, setShowPlayers] = useState(true);
  const [showTrails, setShowTrails] = useState(true);
  const [showEvents, setShowEvents] = useState(false);
  const [showAllKillConnections, setShowAllKillConnections] = useState(false);
  const [following, setFollowing] = useState(false);
  const stopFollowing = useCallback(() => setFollowing(false), []);
  const [scope, setScope] = useState("session");
  const [mode, setMode] = useState("live");
  const [replay, setReplay] = useState(null);
  const [replayRange, setReplayRange] = useState(null);
  const [frames, setFrames] = useState([]);
  const [liveFrames, setLiveFrames] = useState([]);
  const [playing, setPlaying] = useState(false);
  const [playbackSpeed, setPlaybackSpeed] = useState(1);
  const [timelineEvents, setTimelineEvents] = useState({
    events: [],
    markers: [],
  });
  const [notice, setNotice] = useState(null);
  const [historyEnd, setHistoryEnd] = useState(
    localDateTime(Date.now() / 1000)
  );
  const [historyRound, setHistoryRound] = useState("");
  const [savedSignal, setSavedSignal] = useState(null);
  const [detectionDetailId, setDetectionDetailId] = useState(null);
  const [archiveTarget, setArchiveTarget] = useState(null);
  const [focusedEncounter, setFocusedEncounter] = useState(null);
  const [clock, setClock] = useState(performance.now() / 1000);
  const [wasStale, setWasStale] = useState(false);
  const chunkCache = useRef(new Map());
  const timelineCache = useRef(new Map());
  const deepLinkHandled = useRef(false);
  const options = {
    enabled: allowed,
    retry: false,
    gcTime: 0,
    refetchOnWindowFocus: true,
    refetchIntervalInBackground: false,
  };
  const capabilities = useQuery({
    ...options,
    queryKey: [...queryKey, "capabilities"],
    queryFn: () => liveMapRequest("capabilities"),
    refetchInterval: (q) => tacticalPollInterval(q, 30000),
  });
  const denied = !allowed || [401, 403].includes(capabilities.error?.status);
  const live = useQuery({
    ...options,
    enabled: allowed && !denied && capabilities.data?.enabled === true,
    queryKey: [...queryKey, "snapshot"],
    queryFn: async () => {
      const started = performance.now() / 1000;
      const result = await liveMapRequest("snapshot");
      const received = performance.now() / 1000;
      return {
        ...result,
        snapshot: result.snapshot
          ? {
              ...result.snapshot,
              received_at_monotonic: received,
              transport_seconds: received - started,
            }
          : null,
      };
    },
    refetchInterval: (q) =>
      tacticalPollInterval(
        q,
        Math.max(2000, (q.state.data?.snapshot?.collector_interval || 2) * 1000)
      ),
  });
  const forbidden = denied || [401, 403].includes(live.error?.status);
  const monitors = useQuery({
    ...options,
    enabled: allowed && !forbidden,
    queryKey: [...queryKey, "monitors"],
    queryFn: () => liveMapRequest("monitors"),
    refetchInterval: (q) => tacticalPollInterval(q, 30000),
  });
  const rounds = useQuery({
    ...options,
    enabled: allowed && !forbidden,
    queryKey: [...queryKey, "rounds"],
    queryFn: () => liveMapRequest("rounds"),
    refetchInterval: (q) => tacticalPollInterval(q, 30000),
  });
  const cases = useQuery({
    ...options,
    enabled:
      allowed && !forbidden && capabilities.data?.permissions.cases === true,
    queryKey: [...queryKey, "reviews"],
    queryFn: () => liveMapRequest("reviews"),
    refetchInterval: (q) => tacticalPollInterval(q, 30000),
  });
  const tacticalSettings = useQuery({
    ...options,
    enabled:
      allowed &&
      !forbidden &&
      capabilities.data?.permissions.manage === true &&
      canUse(permissions, "can_manage_live_map"),
    queryKey: [...queryKey, "settings"],
    queryFn: () => liveMapRequest("settings"),
  });
  const detections = useQuery({
    ...options,
    enabled:
      allowed && !forbidden && capabilities.data?.permissions.cases === true,
    queryKey: [...queryKey, "detections"],
    queryFn: () => liveMapRequest("detections?limit=200"),
    refetchInterval: (q) => tacticalPollInterval(q, 15000),
  });
  const detectionDetail = useQuery({
    ...options,
    enabled:
      allowed &&
      !forbidden &&
      capabilities.data?.permissions.cases === true &&
      Boolean(detectionDetailId),
    queryKey: [...queryKey, "detections", detectionDetailId],
    queryFn: () =>
      liveMapRequest(`detections/${encodeURIComponent(detectionDetailId)}`),
  });
  const archives = useQuery({
    ...options,
    enabled:
      allowed && !forbidden && capabilities.data?.permissions.cases === true,
    queryKey: [...queryKey, "archives"],
    queryFn: () => liveMapRequest("archives"),
    refetchInterval: (q) => tacticalPollInterval(q, 30000),
  });
  const mutation = useMutation({
    mutationFn: ({ path, data, method }) => liveMapRequest(path, data, method),
    onSuccess: () => {
      setNotice({ severity: "success", text: t("updated") });
      client.invalidateQueries({ queryKey });
    },
    onError: (error) =>
      setNotice({ severity: "error", text: `${t("error")}: ${error.message}` }),
  });
  const historyMutation = useMutation({
    mutationFn: async ({
      round,
      time,
      archiveId = null,
      preservePlaying = false,
    }) => {
      const target = Math.max(round.start, Math.min(time, round.end));
      const currentStart =
        round.start + Math.floor((target - round.start) / 300) * 300;
      const starts = [currentStart - 300, currentStart, currentStart + 300]
        .map((value) => Math.max(round.start, value))
        .filter(
          (value, index, values) =>
            value < round.end && values.indexOf(value) === index
        );
      const keys = starts.map(
        (start) => `${archiveId || "recent"}:${round.round_id}:${start}`
      );
      await Promise.all(
        starts.map(async (start, index) => {
          const key = keys[index];
          if (chunkCache.current.has(key)) return;
          const params = new URLSearchParams({
            start,
            end: Math.min(round.end, start + 300),
            round_id: round.round_id,
            ...(archiveId ? { archive_id: archiveId } : {}),
          });
          const result = await liveMapRequest(`history?${params}`);
          chunkCache.current.set(key, result.frames || []);
        })
      );
      chunkCache.current = new Map(
        keys.map((key) => [key, chunkCache.current.get(key) || []])
      );
      const timelineKey = `${archiveId || "recent"}:${round.round_id}`;
      let timeline = timelineCache.current.get(timelineKey);
      if (!timeline) {
        const params = new URLSearchParams({
          start: round.start,
          end: round.end,
          round_id: round.round_id,
          ...(archiveId ? { archive_id: archiveId } : {}),
        });
        timeline = await liveMapRequest(`events?${params}`);
        timelineCache.current.set(timelineKey, timeline);
      }
      return {
        frames: [...chunkCache.current.values()]
          .flat()
          .filter(
            (frame, index, values) =>
              values.findIndex(
                (candidate) =>
                  candidate.round_id === frame.round_id &&
                  candidate.captured_at === frame.captured_at
              ) === index
          )
          .sort((a, b) => a.captured_at - b.captured_at),
        timeline,
        round,
        target,
        archiveId,
        preservePlaying,
      };
    },
    onSuccess: (result) => {
      setFrames(result.frames);
      setTimelineEvents(result.timeline);
      setReplayRange({ ...result.round, archive_id: result.archiveId });
      setReplay(result.target);
      setMode(result.archiveId ? "archive" : "replay");
      if (!result.preservePlaying) setPlaying(false);
      if (!result.frames.length)
        setNotice({ severity: "info", text: t("noHistory") });
    },
    onError: (error) => setNotice({ severity: "error", text: error.message }),
  });

  useEffect(() => {
    const timer = setInterval(() => setClock(performance.now() / 1000), 1000);
    return () => clearInterval(timer);
  }, []);
  useEffect(() => {
    if (forbidden) {
      setLiveFrames([]);
      setFrames([]);
      setSavedSignal(null);
      client.removeQueries({ queryKey });
    }
  }, [forbidden]);
  // Keep the last dated sample during a temporary empty response. This keeps
  // the camera and selection stable; age/action guards still disable actions.
  const current = capabilities.data?.enabled
    ? live.data?.snapshot ?? liveFrames.at(-1) ?? null
    : null;
  useEffect(() => {
    if (capabilities.data?.enabled === false) setLiveFrames([]);
  }, [capabilities.data?.enabled]);
  useEffect(() => {
    if (
      capabilities.data?.permissions.cases === false ||
      [401, 403].includes(cases.error?.status)
    ) {
      if (savedSignal) {
        setFrames([]);
        setSavedSignal(null);
        setReplay(null);
      }
      client.removeQueries({ queryKey: [...queryKey, "reviews"] });
    }
  }, [capabilities.data?.permissions.cases, cases.error?.status]);
  useEffect(() => {
    if (!current || forbidden) return;
    setLiveFrames((old) =>
      [
        ...old.filter(
          (f) =>
            f.round_id === current.round_id &&
            f.captured_at < current.captured_at
        ),
        current,
      ].slice(-150)
    );
  }, [current?.captured_at, forbidden]);
  useEffect(() => {
    if (!playing || replay === null || !replayRange) return;
    const timer = setInterval(
      () =>
        setReplay((value) => {
          const next = Math.min(value + playbackSpeed * 0.25, replayRange.end);
          if (next >= replayRange.end) setPlaying(false);
          return next;
        }),
      250
    );
    return () => clearInterval(timer);
  }, [playing, replay === null, replayRange, playbackSpeed]);
  useEffect(() => {
    if (
      !playing ||
      replay === null ||
      !replayRange ||
      historyMutation.isPending ||
      replayRange.end <= (frames.at(-1)?.captured_at || 0) ||
      replay < (frames.at(-1)?.captured_at || 0) - 10
    )
      return;
    historyMutation.mutate({
      round: replayRange,
      time: replay,
      archiveId: replayRange.archive_id,
      preservePlaying: true,
    });
  }, [playing, replay, replayRange, frames, historyMutation.isPending]);

  const evidenceAllowed =
    capabilities.data?.permissions.cases === true &&
    ![401, 403].includes(cases.error?.status);
  const frame =
    replay === null
      ? current
      : savedSignal && !evidenceAllowed
      ? null
      : frameAt(frames, replay);
  const players = frame?.players || [];
  const visible = useMemo(
    () => filterPlayers(players, search, team, squad),
    [players, search, team, squad]
  );
  const selectedPlayer = players.find((p) => p.player_id === selected);
  const trails = useMemo(
    () =>
      showTrails && selected && frame
        ? trailSegments(
            replay === null ? liveFrames : frames,
            selected,
            frame.round_id,
            replay ?? frame.captured_at
          )
        : [],
    [showTrails, selected, frame, replay, frames, liveFrames]
  );
  const mapEvents = useMemo(() => {
    if (!showEvents || !frame) return [];
    const at =
      replay ?? frame.captured_at + Math.max(0, sampleAge(frame, clock));
    const values =
      replay === null
        ? liveFrames.flatMap((item) => item.events || [])
        : timelineEvents.events || [];
    return visibleKillConnections({
      events: values,
      at,
      selected,
      showAll: showAllKillConnections,
    });
  }, [
    showEvents,
    frame,
    replay,
    timelineEvents,
    liveFrames,
    selected,
    showAllKillConnections,
    clock,
  ]);
  const signals =
    savedSignal && evidenceAllowed
      ? [savedSignal]
      : replay !== null
      ? []
      : current?.signals?.filter((s) =>
          !selected
            ? s.kind !== "encounter"
            : s.victim === selected || s.attacker === selected
        ) || [];
  const detectionValues = (detections.data?.detections || []).filter(
    (item) => replay === null || item.round_id === replayRange?.round_id
  );
  const canManage =
    canUse(permissions, "can_manage_live_map") &&
    capabilities.data?.permissions.manage === true;
  const canCases =
    canUse(permissions, "can_view_live_map_cases") &&
    capabilities.data?.permissions.cases === true;
  const canArchive =
    canCases &&
    capabilities.data?.archive_enabled === true &&
    capabilities.data?.permissions.archives === true &&
    canUse(permissions, "can_manage_live_map_archives");
  const age = frame && replay === null ? sampleAge(frame, clock) : null;
  const stale =
    replay === null &&
    Boolean(current) &&
    sampleIsStale(age, current.collector_interval, wasStale);
  useEffect(() => setWasStale(stale), [stale]);
  const actionable =
    replay === null &&
    current &&
    age <= Math.max(6, current.collector_interval * 3);
  const goLive = () => {
    setFocusedEncounter(null);
    setReplay(null);
    setReplayRange(null);
    setTimelineEvents({ events: [], markers: [] });
    setMode("live");
    setPlaying(false);
    setSavedSignal(null);
  };
  const selectPlayer = (id) => {
    setSelected(id);
    setFollowing(false);
  };
  const loadHistory = () => {
    setFocusedEncounter(null);
    const round = rounds.data?.find((item) => item.round_id === historyRound);
    if (!round) return;
    const target = new Date(historyEnd).getTime() / 1000;
    setSavedSignal(null);
    historyMutation.mutate({
      round,
      time: Number.isFinite(target) ? target : round.start,
      archiveId: mode === "archive" ? round.archive?.id : null,
    });
  };
  const viewEncounter = (event, signal) => {
    const round = rounds.data?.find(
      (item) => item.round_id === signal.round_id
    );
    if (!round) return;
    setSavedSignal(null);
    historyMutation.mutate(
      { round, time: event.time, archiveId: round.archive?.id || null },
      {
        onSuccess: () => {
          setFocusedEncounter({ ...event, round_id: signal.round_id });
          setReplay(event.time);
          setSelected(signal.victim);
          setFollowing(true);
          setTab(0);
        },
      }
    );
  };
  const review = (signal, action) =>
    mutation.mutate({
      path: `reviews/${signal.id}`,
      data: {
        action,
        ...(signal.review?.revision
          ? { revision: signal.review.revision }
          : {}),
      },
    });
  const openEvidence = async (id) => {
    try {
      const data = await liveMapRequest(`reviews/${id}`);
      setSavedSignal(data.signal);
      if (data.archive_id) {
        const round = (rounds.data || []).find(
          (item) => item.round_id === data.signal.round_id
        );
        if (!round) throw new Error(t("noHistory"));
        setSelected(data.signal.player_id || null);
        historyMutation.mutate({
          round,
          time: data.signal.last_at || data.signal.first_at,
          archiveId: data.archive_id,
        });
      } else {
        const evidenceFrames = data.frames || [];
        const evidenceStart =
          evidenceFrames[0]?.captured_at ?? data.signal.first_at;
        const evidenceEnd =
          evidenceFrames.at(-1)?.captured_at ?? data.signal.last_at;
        setFrames(evidenceFrames);
        setReplay(evidenceStart);
        setReplayRange({
          round_id: data.signal.round_id,
          start: evidenceStart,
          end: evidenceEnd,
          archive_id: null,
        });
        setMode("replay");
      }
      setPlaying(false);
    } catch (error) {
      setNotice({ severity: "error", text: error.message });
    }
  };
  const viewDetection = (detection) => {
    const round = rounds.data?.find(
      (item) => item.round_id === detection.round_id
    );
    if (!round) {
      setNotice({ severity: "info", text: t("noHistory") });
      return;
    }
    setSelected(detection.player_id);
    historyMutation.mutate({
      round,
      time: detection.last_at,
      archiveId: round.archive?.id || null,
    });
  };
  const stepReplay = (kind, amount) => {
    if (replay === null || !replayRange) return;
    if (kind === "seconds") {
      const target = Math.max(
        replayRange.start,
        Math.min(replay + amount, replayRange.end)
      );
      setReplay(target);
      historyMutation.mutate({
        round: replayRange,
        time: target,
        archiveId: replayRange.archive_id,
      });
      return;
    }
    const values = frames.map((item) => item.captured_at);
    const target =
      amount < 0
        ? [...values].reverse().find((value) => value < replay)
        : values.find((value) => value > replay);
    if (target !== undefined) setReplay(target);
  };
  const commitSeek = (time) => {
    if (!replayRange) return;
    historyMutation.mutate({
      round: replayRange,
      time,
      archiveId: replayRange.archive_id,
    });
  };
  const changePlayback = (next) => {
    if (!next) {
      setPlaying(false);
      return;
    }
    if (replay !== null && replayRange && replay >= replayRange.end) {
      setReplay(replayRange.start);
      historyMutation.mutate({
        round: replayRange,
        time: replayRange.start,
        archiveId: replayRange.archive_id,
        preservePlaying: true,
      });
    }
    setPlaying(true);
  };
  const eventMarks = useMemo(() => {
    const values = [
      ...(timelineEvents.events || []).map((item) => ({
        value: item.time,
        kind: item.kind || (item.teamkill ? "teamkill" : "kill"),
      })),
      ...(timelineEvents.markers || []).map((item) => ({
        value: item.time,
        kind: "detection",
      })),
    ];
    if (values.length <= 100) return values;
    return values.filter(
      (_, index) => index % Math.ceil(values.length / 100) === 0
    );
  }, [timelineEvents]);
  const markerCounts = useMemo(() => {
    const values = [
      ...(timelineEvents.events || []).map(
        (item) => item.kind || (item.teamkill ? "teamkill" : "kill")
      ),
      ...(timelineEvents.markers || []).map(() => "detection"),
    ];
    return values.reduce((counts, kind) => {
      counts[kind] = (counts[kind] || 0) + 1;
      return counts;
    }, {});
  }, [timelineEvents]);
  const selectedRound = (rounds.data || []).find(
    (item) => item.round_id === (historyRound || frame?.round_id)
  );
  const changeMode = (value) => {
    if (value === "live") {
      goLive();
      return;
    }
    setMode(value);
    setPlaying(false);
    const available = (rounds.data || []).filter(
      (item) => value !== "archive" || item.archive
    );
    const round =
      available.find((item) => item.round_id === historyRound) || available[0];
    if (round) {
      setHistoryRound(round.round_id);
      setHistoryEnd(localDateTime(round.end));
    }
  };
  useEffect(() => {
    if (deepLinkHandled.current || !rounds.data?.length) return;
    const params = new URLSearchParams(window.location.search);
    const round = rounds.data.find(
      (item) => item.round_id === params.get("round")
    );
    const time = Number(params.get("time"));
    if (!round || !Number.isFinite(time)) return;
    deepLinkHandled.current = true;
    const player = params.get("player");
    if (player) setSelected(player);
    setHistoryRound(round.round_id);
    setHistoryEnd(localDateTime(time));
    historyMutation.mutate({
      round,
      time,
      archiveId: round.archive?.id || null,
    });
  }, [rounds.data]);

  if (forbidden) return <Alert severity="warning">{t("forbidden")}</Alert>;
  if (capabilities.isLoading)
    return <CircularProgress aria-label={t("collecting")} />;
  return (
    <Box
      data-testid="live-map-page"
      sx={{
        "& .MuiButton-root, & .MuiOutlinedInput-root, & .MuiAlert-root": {
          borderRadius: 0,
        },
      }}
    >
      <PageHeader
        title={t("title")}
        subtitle={t("subtitle")}
        eyebrow={t("group")}
      />
      {isFakeMode() && <Alert severity="info">{t("demo")}</Alert>}
      {notice && (
        <Alert
          severity={notice.severity}
          onClose={() => setNotice(null)}
          sx={{ mb: 1 }}
        >
          {notice.text}
        </Alert>
      )}
      <Stack data-theme-surface="panel"
        direction="row"
        useFlexGap
        flexWrap="wrap"
        alignItems="center"
        gap={2}
        sx={{ ...panel, p: 1.5, mb: 1.5 }}
      >
        <Typography fontWeight={800}>
          S{capabilities.data?.server_number ?? "–"} ·{" "}
          {frame?.map?.pretty_name || "–"}
        </Typography>
        <Typography
          color={replay === null ? "success.main" : "warning.main"}
          fontWeight={800}
        >
          {t(replay === null ? "live" : "replay")}
        </Typography>
        <Typography variant="body2">
          {frame
            ? new Date(frame.captured_at * 1000).toLocaleString(i18n.language)
            : t("collecting")}
        </Typography>
        {replay === null && age !== null && (
          <Typography
            variant="body2"
            sx={{ minWidth: "18ch", fontVariantNumeric: "tabular-nums" }}
          >
            {t("fresh")}: {Number.isFinite(age) ? Math.floor(age) : "–"}{" "}
            {t("seconds")}
          </Typography>
        )}
        {canManage && (
          <Stack direction="row" useFlexGap flexWrap="wrap" sx={{ ml: "auto" }}>
            <FormControlLabel
              label={t("enabled")}
              control={
                <Switch
                  checked={capabilities.data?.enabled ?? false}
                  disabled={mutation.isPending}
                  onChange={(_, enabled) =>
                    mutation.mutate({ path: "settings", data: { enabled } })
                  }
                />
              }
            />
            <FormControlLabel
              label={t("monitorEnabled")}
              control={
                <Switch
                  checked={capabilities.data?.monitor_enabled ?? false}
                  disabled={mutation.isPending}
                  onChange={(_, monitor_enabled) =>
                    mutation.mutate({
                      path: "settings",
                      data: { monitor_enabled },
                    })
                  }
                />
              }
            />
          </Stack>
        )}
      </Stack>
      <Box data-theme-surface="control"
        data-testid="live-map-status"
        role="status"
        aria-live="polite"
        sx={{
          ...panel,
          height: 44,
          boxSizing: "border-box",
          px: 1.5,
          mb: 1.5,
          display: "flex",
          alignItems: "center",
          overflow: "hidden",
        }}
      >
        <Typography
          variant="body2"
          noWrap
          color={
            capabilities.error || live.error
              ? "error.main"
              : stale
              ? "warning.main"
              : "text.secondary"
          }
          title={
            capabilities.error || live.error
              ? (capabilities.error || live.error).message
              : undefined
          }
        >
          {capabilities.error || live.error
            ? t("connectionDelayed")
            : replay !== null
            ? t("replay")
            : !capabilities.data?.enabled
            ? t("disabled")
            : !current
            ? t("collecting")
            : stale
            ? t("stale")
            : current.quality?.round_confirmed === false
            ? t("roundUnknown")
            : t("receiving")}
        </Typography>
      </Box>
      {mobile && (
        <Tabs value={tab} onChange={(_, v) => setTab(v)} variant="fullWidth">
          <Tab label={t("map")} />
          <Tab label={t("details")} />
        </Tabs>
      )}
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0,1fr)",
            lg: "minmax(0,1fr) 360px",
          },
          gap: 1.5,
          alignItems: "start",
        }}
      >
        <Box
          sx={{ minWidth: 0, display: mobile && tab !== 0 ? "none" : "block" }}
        >
          <Stack data-theme-surface="panel"
            direction="row"
            useFlexGap
            flexWrap="wrap"
            gap={1}
            sx={{ ...panel, p: 1.5, mb: 1 }}
          >
            <TextField
              size="small"
              label={t("search")}
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              sx={{ flex: "1 1 180px" }}
            />
            <TextField
              size="small"
              select
              label={t("team")}
              value={team}
              onChange={(e) => {
                setTeam(e.target.value);
                setSquad("all");
              }}
              sx={{ minWidth: 140 }}
            >
              <MenuItem value="all">{t("all")}</MenuItem>
              <MenuItem value="allies">
                {t(normalizeGame(frame?.game) === "hllv" ? "south" : "allies")}
              </MenuItem>
              <MenuItem value="axis">
                {t(normalizeGame(frame?.game) === "hllv" ? "north" : "axis")}
              </MenuItem>
            </TextField>
            <TextField
              size="small"
              select
              label={t("squad")}
              value={squad}
              onChange={(e) => setSquad(e.target.value)}
              sx={{ minWidth: 125 }}
            >
              <MenuItem value="all">{t("all")}</MenuItem>
              {[
                ...new Set(
                  players
                    .filter((p) => team === "all" || p.team === team)
                    .map((p) => p.unit_name)
                    .filter(Boolean)
                ),
              ]
                .sort()
                .map((s) => (
                  <MenuItem key={s} value={s}>
                    {s}
                  </MenuItem>
                ))}
            </TextField>
          </Stack>
          <Stack direction="row" useFlexGap flexWrap="wrap" sx={{ px: 1 }}>
            <FormControlLabel
              control={
                <Checkbox
                  checked={showPlayers}
                  onChange={(_, v) => setShowPlayers(v)}
                />
              }
              label={t("players")}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={showTrails}
                  onChange={(_, v) => setShowTrails(v)}
                />
              }
              label={t("trails")}
            />
            <FormControlLabel
              control={
                <Checkbox
                  checked={showEvents}
                  onChange={(_, v) => setShowEvents(v)}
                />
              }
              label={t("killConnections")}
            />
            {showEvents && selected && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={showAllKillConnections}
                    onChange={(_, v) => setShowAllKillConnections(v)}
                  />
                }
                label={t("allKillConnections")}
              />
            )}
          </Stack>
          {showEvents && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", px: 2, pb: 1 }}
            >
              {t("killConnectionHelp")}
            </Typography>
          )}
          <TacticalMap
            encounter={focusedEncounter}
            frame={frame}
            players={visible}
            selected={selected}
            following={following}
            onSelect={selectPlayer}
            onManualNavigate={stopFollowing}
            trails={trails}
            events={mapEvents}
            animateConnections={replay === null || playing}
            connectionSpeed={replay === null ? 1 : playbackSpeed}
            showPlayers={showPlayers}
            t={t}
          />
          {canManage && replay === null && current && (
            <CalibrationPanel
              key={current.map?.map?.id}
              frame={current}
              mutation={mutation}
              t={t}
            />
          )}
          <Box data-theme-surface="panel" sx={{ ...panel, mt: 1 }}>
            <ReplayControls
              t={t}
              language={i18n.language}
              mode={mode}
              onMode={changeMode}
              rounds={rounds.data || []}
              roundId={historyRound}
              onRound={(value) => {
                setHistoryRound(value);
                const round = rounds.data?.find(
                  (item) => item.round_id === value
                );
                if (round) setHistoryEnd(localDateTime(round.end));
              }}
              historyEnd={historyEnd}
              onHistoryEnd={setHistoryEnd}
              onLoad={loadHistory}
              loading={historyMutation.isPending}
              replay={replay}
              range={replayRange}
              playing={playing}
              onPlaying={changePlayback}
              onSeek={(time) => {
                setReplay(time);
                setPlaying(false);
              }}
              onSeekCommitted={commitSeek}
              onStep={stepReplay}
              speed={playbackSpeed}
              onSpeed={setPlaybackSpeed}
              eventMarks={eventMarks}
              markerCounts={markerCounts}
              onLive={goLive}
            />
            <Stack
              direction="row"
              useFlexGap
              flexWrap="wrap"
              gap={1}
              sx={{ px: 1.5, pb: 1.5 }}
            >
              {canArchive && selectedRound && !selectedRound.archive && (
                <Button
                  onClick={() => setArchiveTarget({ round: selectedRound })}
                >
                  {t("saveRound")}
                </Button>
              )}
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ alignSelf: "center" }}
              >
                {t("retention")} · {t("gap")}
              </Typography>
            </Stack>
          </Box>
          {canManage && (
            <DetectionSettings
              settings={tacticalSettings.data}
              mutation={mutation}
              t={t}
            />
          )}
        </Box>
        <Box sx={{ display: mobile && tab !== 1 ? "none" : "grid", gap: 1.5 }}>
          <Box data-theme-surface="panel" sx={{ ...panel, p: 1.5 }}>
            <Typography variant="overline">{t("selected")}</Typography>
            {selectedPlayer ? (
              <>
                <Typography variant="h6">{selectedPlayer.name}</Typography>
                <Typography color="text.secondary" variant="body2">
                  {selectedPlayer.role} · {selectedPlayer.unit_name || "–"}
                </Typography>
                {!selectedPlayer.position_valid && (
                  <Typography color="warning.main">{t("unknown")}</Typography>
                )}
                {canManage && selectedPlayer.position && (
                  <Typography variant="caption" display="block">
                    World X: {selectedPlayer.position.x.toFixed(1)} · Y:{" "}
                    {selectedPlayer.position.y.toFixed(1)} · Z:{" "}
                    {selectedPlayer.position.z.toFixed(1)}
                  </Typography>
                )}
                <Stack direction="row" flexWrap="wrap" gap={1} sx={{ my: 1 }}>
                  <Button
                    variant={following ? "contained" : "outlined"}
                    aria-pressed={following}
                    disabled={!selectedPlayer.map_position}
                    onClick={() => setFollowing(!following)}
                  >
                    {t("follow")}
                  </Button>
                  <Button
                    component={Link}
                    to={`/records/players/${encodeURIComponent(
                      selectedPlayer.player_id
                    )}`}
                  >
                    {t("profile")}
                  </Button>
                  {actionable && (
                    <ActionMenuButton
                      recipients={selectedPlayer}
                      actions={ACTIONS}
                    />
                  )}
                </Stack>
                {canManage && replay === null && (
                  <Stack gap={1}>
                    <TextField
                      size="small"
                      select
                      label={t("scope")}
                      value={scope}
                      onChange={(e) => setScope(e.target.value)}
                    >
                      <MenuItem value="session">{t("session")}</MenuItem>
                      <MenuItem value="permanent">{t("permanent")}</MenuItem>
                    </TextField>
                    <Button
                      disabled={mutation.isPending || !actionable}
                      onClick={() =>
                        mutation.mutate({
                          path: "monitors",
                          data: { player_id: selected, scope },
                        })
                      }
                    >
                      {t("protect")}
                    </Button>
                  </Stack>
                )}
              </>
            ) : (
              <Typography variant="body2" color="text.secondary">
                {t("choose")}
              </Typography>
            )}
          </Box>
          <Box data-theme-surface="panel" sx={panel}>
            <Typography sx={{ px: 1.5, py: 1 }} fontWeight={800}>
              {t("players")} · {visible.length} {t("shown")}
            </Typography>
            <Typography sx={{ px: 1.5 }} variant="caption">
              {t("quality")}: {frame?.quality?.valid_positions ?? 0}/
              {players.length}
            </Typography>
            <Typography sx={{ px: 1.5 }} variant="caption" display="block">
              {t("mapped")}: {visible.filter((p) => p.map_position).length}/
              {visible.length}
            </Typography>
            {frame && frame.calibration?.verified !== true && (
              <Box
                component="details"
                data-testid="map-projection-details"
                sx={{ px: 1.5, py: 1 }}
              >
                <Typography
                  component="summary"
                  variant="caption"
                  sx={{ cursor: "pointer" }}
                >
                  {t("projectionDetails")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t(
                    projectionReady(frame.calibration)
                      ? "projectionHelp"
                      : "uncalibratedHelp"
                  )}
                </Typography>
              </Box>
            )}
            <Box sx={{ maxHeight: 240, overflowY: "auto" }}>
              {!visible.length && (
                <Typography sx={{ p: 1.5 }} variant="body2">
                  {t("noPlayers")}
                </Typography>
              )}
              {visible.map((p) => (
                <Button
                  key={p.player_id}
                  fullWidth
                  aria-pressed={selected === p.player_id}
                  onClick={() => selectPlayer(p.player_id)}
                  sx={{
                    justifyContent: "start",
                    textTransform: "none",
                    borderTop: 1,
                    borderColor: "divider",
                    px: 1.5,
                    bgcolor:
                      selected === p.player_id ? "action.selected" : undefined,
                  }}
                >
                  <Typography
                    component="span"
                    sx={{ color: getThemeTeamColor(theme, p.team), mr: 1 }}
                  >
                    {p.team === "axis" ? "◆" : "●"}
                  </Typography>
                  <Box sx={{ textAlign: "left", minWidth: 0 }}>
                    <Typography noWrap fontWeight={700}>
                      {p.name}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {p.unit_name || "–"} ·{" "}
                      {p.position_valid ? p.role : t("unknown")}
                    </Typography>
                  </Box>
                </Button>
              ))}
            </Box>
          </Box>
          <Box data-theme-surface="panel" sx={{ ...panel, p: 1.5 }}>
            <Typography fontWeight={800}>{t("protected")}</Typography>
            {(monitors.data || []).map((m) => (
              <Stack
                key={m.player_id}
                direction="row"
                alignItems="center"
                gap={1}
                sx={{ borderTop: 1, borderColor: "divider", py: 1 }}
              >
                <Box sx={{ flex: 1, minWidth: 0 }}>
                  <Button
                    onClick={() => setSelected(m.player_id)}
                    sx={{ p: 0, textTransform: "none" }}
                  >
                    {m.name}
                  </Button>
                  <Typography variant="caption" display="block">
                    {t(m.scope)}
                  </Typography>
                </Box>
                {canManage && (
                  <Button
                    size="small"
                    disabled={mutation.isPending}
                    onClick={() =>
                      mutation.mutate({
                        path: "monitors",
                        method: "DELETE",
                        data: { player_id: m.player_id },
                      })
                    }
                  >
                    {t("remove")}
                  </Button>
                )}
              </Stack>
            ))}
          </Box>
          {canCases && (
            <DetectionPanel
              detections={detectionValues}
              detail={detectionDetail.data}
              detailLoading={detectionDetail.isLoading}
              selected={selected}
              canCases={canCases}
              canArchive={canArchive}
              permissions={permissions}
              canUse={canUse}
              mutation={mutation}
              onReview={review}
              onReplay={viewDetection}
              onDetails={(detection) =>
                setDetectionDetailId((current) =>
                  current === detection.id ? null : detection.id
                )
              }
              onArchive={(detection) => {
                const round = (rounds.data || []).find(
                  (item) => item.round_id === detection.round_id
                );
                if (round) setArchiveTarget({ round, detection });
              }}
              t={t}
            />
          )}
          <Box data-theme-surface="panel" sx={{ ...panel, p: 1.5 }}>
            <Stack direction="row" justifyContent="space-between">
              <Typography fontWeight={800}>{t("signals")}</Typography>
              {selected && (
                <Button size="small" onClick={() => setSelected(null)}>
                  {t("all")}
                </Button>
              )}
            </Stack>
            <Typography variant="caption" color="text.secondary">
              {t("note")}
            </Typography>
            {!signals.length && (
              <Typography sx={{ mt: 1 }} variant="body2">
                {t(replay !== null ? "replayHints" : "noSignals")}
              </Typography>
            )}
            {signals.map((signal) => (
              <Box
                key={signal.id}
                sx={{
                  borderTop: 2,
                  borderColor:
                    signal.kind === "review" ? "warning.main" : "divider",
                  mt: 1.5,
                  pt: 1.5,
                }}
              >
                <Typography fontWeight={800}>
                  {t(
                    signal.kind === "review"
                      ? "review"
                      : signal.kind === "encounter"
                      ? "encounters"
                      : "repeat"
                  )}
                </Typography>
                <Typography variant="body2">
                  {signal.attacker_name || signal.attacker} →{" "}
                  {signal.victim_name || signal.victim}: {signal.count}× / 15
                  min
                </Typography>
                <Typography variant="caption" display="block">
                  {t("deaths")}: {signal.total_deaths} · {t("share")}:{" "}
                  {Math.round(signal.share * 100)} % · {t("counterkills")}:{" "}
                  {signal.counterkills}
                </Typography>
                <Typography variant="caption" display="block">
                  {t("measured")}: {signal.located_events}/{signal.count}
                </Typography>
                {signal.death_count_complete === false && (
                  <Typography variant="caption" color="warning.main">
                    {t("incompleteDeaths")}
                  </Typography>
                )}
                <Box component="details" sx={{ my: 1 }}>
                  <Typography component="summary" sx={{ cursor: "pointer" }}>
                    {t("encounters")}
                  </Typography>
                  {signal.events.map((e, index) => (
                    <Typography key={e.id} variant="caption" display="block">
                      {new Date(e.time * 1000).toLocaleTimeString(
                        i18n.language
                      )}{" "}
                      · {e.weapon || "–"} ·{" "}
                      {e.position_sample_at ? t("lastKnown") : t("unknown")}
                      {index > 0 &&
                        ` · ${Math.round(
                          e.time - signal.events[index - 1].time
                        )} ${t("seconds")} ${t("gapBetween")}`}
                      {e.map_position && (
                        <Button
                          size="small"
                          disabled={historyMutation.isPending}
                          onClick={() => viewEncounter(e, signal)}
                        >
                          {t("viewEncounter")}
                        </Button>
                      )}
                    </Typography>
                  ))}
                  {signal.events.map(
                    (e) =>
                      e.attacker_role && (
                        <Typography
                          key={`context-${e.id}`}
                          variant="caption"
                          display="block"
                        >
                          {e.attacker_role} / {e.attacker_squad || "–"} →{" "}
                          {e.victim_role} / {e.victim_squad || "–"}
                        </Typography>
                      )
                  )}
                  <Typography variant="caption" display="block" sx={{ mt: 1 }}>
                    {t("reviewHelp")}
                  </Typography>
                  <Typography variant="caption" display="block">
                    {t("context")}
                  </Typography>
                </Box>
                {signal.review && (
                  <Typography variant="caption">
                    {t("status")}: {signal.review.status}{" "}
                    {signal.review.assigned_to || ""}
                  </Typography>
                )}
                {canCases && actionable && (
                  <Stack direction="row" flexWrap="wrap" gap={0.5}>
                    {canUse(permissions, "can_claim_admin_incidents") && (
                      <Button
                        size="small"
                        disabled={mutation.isPending}
                        onClick={() => review(signal, "claim")}
                      >
                        {t("claim")}
                      </Button>
                    )}
                    {canUse(permissions, "can_resolve_admin_incidents") && (
                      <Button
                        size="small"
                        disabled={mutation.isPending}
                        onClick={() => review(signal, "dismiss")}
                      >
                        {t("dismiss")}
                      </Button>
                    )}
                    {canUse(permissions, "can_create_admin_incidents") && (
                      <Button
                        size="small"
                        disabled={mutation.isPending || signal.review?.saved}
                        onClick={() => review(signal, "save")}
                      >
                        {t(signal.review?.saved ? "saved" : "save")}
                      </Button>
                    )}
                  </Stack>
                )}
              </Box>
            ))}
          </Box>
          {canCases && (
            <Box data-theme-surface="panel" sx={{ ...panel, p: 1.5 }}>
              <Typography fontWeight={800}>{t("evidence")}</Typography>
              {Object.entries(cases.data || {}).map(([id, c]) => (
                <Stack
                  key={id}
                  direction="row"
                  useFlexGap
                  flexWrap="wrap"
                  gap={1}
                >
                  <Button
                    component={Link}
                    to={`/incidents?incident=${c.incident_id}`}
                    size="small"
                  >
                    {t("case")} · {c.status}
                  </Button>
                  {c.saved && (
                    <Button size="small" onClick={() => openEvidence(id)}>
                      {t("openEvidence")}
                    </Button>
                  )}
                </Stack>
              ))}
            </Box>
          )}
          {canCases && (
            <Box data-theme-surface="panel" sx={{ ...panel, p: 1.5 }}>
              <Typography fontWeight={800}>{t("archives")}</Typography>
              {!(archives.data?.archives || []).length && (
                <Typography variant="body2" color="text.secondary">
                  {t("noArchives")}
                </Typography>
              )}
              {(archives.data?.archives || []).map((archive) => (
                <Box
                  key={archive.id}
                  sx={{ borderTop: 1, borderColor: "divider", py: 1 }}
                >
                  <Typography variant="body2" fontWeight={700}>
                    {new Date(archive.end * 1000).toLocaleString(i18n.language)}{" "}
                    · {archive.retention_days} {t("days")}
                  </Typography>
                  <Typography
                    variant="caption"
                    color={
                      archive.expires_soon ? "warning.main" : "text.secondary"
                    }
                    display="block"
                  >
                    {t("expires")}:{" "}
                    {new Date(archive.expires_at * 1000).toLocaleDateString(
                      i18n.language
                    )}{" "}
                    · {(archive.bytes / 1024 / 1024).toFixed(1)} MiB
                    {archive.expires_soon ? ` · ⚠ ${t("expiresSoon")}` : ""}
                  </Typography>
                  {canArchive && (
                    <Stack direction="row" gap={0.5}>
                      <Button
                        size="small"
                        disabled={
                          mutation.isPending || archive.retention_days === 90
                        }
                        onClick={() =>
                          mutation.mutate({
                            path: `archives/${archive.id}`,
                            method: "PATCH",
                            data: { retention_days: 90 },
                          })
                        }
                      >
                        {t("changeRetention")}
                      </Button>
                      <Button
                        size="small"
                        color="error"
                        disabled={mutation.isPending}
                        onClick={() => {
                          if (window.confirm(t("releaseArchiveConfirm"))) {
                            mutation.mutate({
                              path: `archives/${archive.id}`,
                              method: "DELETE",
                              data: {},
                            });
                          }
                        }}
                      >
                        {t("releaseArchive")}
                      </Button>
                    </Stack>
                  )}
                </Box>
              ))}
            </Box>
          )}
        </Box>
      </Box>
      <ArchiveDialog
        open={Boolean(archiveTarget)}
        onClose={() => setArchiveTarget(null)}
        round={archiveTarget?.round}
        detection={archiveTarget?.detection}
        mutation={mutation}
        t={t}
      />
    </Box>
  );
}
