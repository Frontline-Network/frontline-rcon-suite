import { useEffect, useMemo, useState } from "react";
import { useLoaderData } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  Alert,
  Box,
  Button,
  Divider,
  Drawer,
  FormControl,
  IconButton,
  LinearProgress,
  MenuItem,
  Select,
  Skeleton,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
  useMediaQuery,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import ArrowDownwardIcon from "@mui/icons-material/ArrowDownward";
import ArrowUpwardIcon from "@mui/icons-material/ArrowUpward";
import DownloadIcon from "@mui/icons-material/Download";
import GroupIcon from "@mui/icons-material/Group";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import TimerOutlinedIcon from "@mui/icons-material/TimerOutlined";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import { ActionMenuButton } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { downloadGame } from "@/features/download-game";
import { gameQueryOptions } from "@/queries/game-query";
import { cmd } from "@/utils/fetchUtils";
import { demoMapLayers, demoScorePlayers, isFakeMode } from "@/mirage/demo-data";
import LiveGameInspector from "./LiveGameInspector";
import LiveTeamTable from "./LiveTeamTable";
import {
  formatMatchDuration,
  getLayerLabel,
  getLayerMode,
  getPlayerSearchText,
  getSnapshotAge,
  getTeamSummary,
  isSnapshotStale,
  normalizeLiveGamePlayer,
  sortLiveGamePlayers,
} from "./live-game-utils";

const createDemoLivePlayers = () =>
  Array.from({ length: 36 }, (_, index) => {
    const base = demoScorePlayers[index % demoScorePlayers.length];
    const team = index % 2 ? "axis" : "allies";
    const kills = Math.max(0, 34 - index);
    const deaths = 3 + (index % 11);
    return {
      ...base,
      player_id: `${base.player_id.slice(0, -2)}${String(index + 1).padStart(2, "0")}`,
      player: index < demoScorePlayers.length ? base.player : `${base.player}_${index + 1}`,
      team,
      faction: team === "allies" ? "us" : "ger",
      status: index % 7 === 0 ? "offline" : index % 5 === 0 ? "idle" : "online",
      kills,
      deaths,
      teamkills: index % 9 === 0 ? 2 : index % 5 === 0 ? 1 : 0,
      kills_streak: Math.max(1, 10 - (index % 8)),
      kill_death_ratio: Number((kills / Math.max(1, deaths)).toFixed(2)),
      kills_per_minute: Number((kills / (58 + (index % 30))).toFixed(2)),
      time_seconds: Math.max(420, 4080 - index * 88),
      combat: 610 - index * 9,
      offense: 340 - index * 4,
      defense: 300 - index * 3,
      support: 460 - index * 5,
      weapons: { "M1 GARAND": Math.max(1, kills - 4), "MK2 GRENADE": index % 5 },
      most_killed: { [demoScorePlayers[(index + 1) % demoScorePlayers.length].player_id]: 4 + (index % 5) },
      death_by: { [demoScorePlayers[(index + 2) % demoScorePlayers.length].player_id]: 2 + (index % 4) },
    };
  });

export const loader = async () => {
  if (isFakeMode()) {
    return {
      stats: {
        stats: createDemoLivePlayers(),
        snapshot_timestamp: Math.floor(Date.now() / 1000),
        refresh_interval_sec: 15,
      },
      game: {
        time_remaining: 3427,
        score: { allied: 3, axis: 2 },
        current_map: { map: demoMapLayers[0], start: Math.floor(Date.now() / 1000) - 3600 },
        next_map: { map: demoMapLayers[1], start: null },
        player_count: 86,
        max_player_count: 100,
        player_count_by_team: { allied: 43, axis: 43 },
      },
    };
  }
  const [stats, game] = await Promise.all([
    cmd.GET_LIVE_GAME(),
    cmd.GET_PUBLIC_GAME_STATE(),
  ]);
  return { stats, game };
};

const MatchItem = ({ label, value, icon, align = "left", emphasis = false }) => (
  <Stack
    direction="row"
    alignItems="center"
    justifyContent={align === "center" ? "center" : "flex-start"}
    gap={0.85}
    sx={{ minWidth: 0, px: 1.25, py: 1, borderRight: "1px solid", borderColor: "divider", "&:last-of-type": { borderRight: 0 } }}
  >
    {icon}
    <Box sx={{ minWidth: 0, textAlign: align }}>
      <Typography sx={{ color: "text.secondary", fontSize: "0.63rem", fontWeight: 700, letterSpacing: "0.09em", textTransform: "uppercase" }}>
        {label}
      </Typography>
      <Typography
        sx={{
          mt: 0.2,
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: "nowrap",
          fontSize: emphasis ? "1.45rem" : "0.76rem",
          fontWeight: emphasis ? 800 : 600,
          fontVariantNumeric: "tabular-nums",
          lineHeight: emphasis ? 1 : 1.25,
        }}
      >
        {value}
      </Typography>
    </Box>
  </Stack>
);

const ComparisonMetric = ({ label, allies, axis, warn = false }) => (
  <Box sx={{ px: 0.9, py: 0.85, borderBottom: "1px solid", borderColor: "divider", "&:last-of-type": { borderBottom: 0 } }}>
    <Typography sx={{ mb: 0.4, textAlign: "center", color: "text.disabled", fontSize: "0.59rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
      {label}
    </Typography>
    <Stack direction="row" justifyContent="space-between" gap={1}>
      <Typography sx={{ color: warn && allies > 0 ? "warning.main" : "info.main", fontSize: "0.76rem", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        {allies}
      </Typography>
      <Typography sx={{ color: warn && axis > 0 ? "warning.main" : "error.main", fontSize: "0.76rem", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
        {axis}
      </Typography>
    </Stack>
  </Box>
);

const ComparisonRail = ({ alliedPlayers, axisPlayers, score, t }) => {
  const allies = getTeamSummary(alliedPlayers);
  const axis = getTeamSummary(axisPlayers);
  const delta = allies.kills - axis.kills;

  return (
    <Box data-theme-surface="panel" component="aside" aria-label={t("stats.liveGame.comparison")} sx={{ minWidth: 0, border: "1px solid", borderColor: "divider", bgcolor: "background.paper" }}>
      <Box sx={{ px: 0.9, py: 1.15, textAlign: "center", borderBottom: "1px solid", borderColor: "divider" }}>
        <Typography sx={{ color: "text.secondary", fontSize: "0.59rem", fontWeight: 700, letterSpacing: "0.09em", textTransform: "uppercase" }}>
          {t("stats.liveGame.score")}
        </Typography>
        <Stack direction="row" justifyContent="center" alignItems="center" gap={0.8} sx={{ mt: 0.45 }}>
          <Typography sx={{ color: "info.main", fontSize: "1.45rem", fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>{score.allied}</Typography>
          <Typography sx={{ color: "primary.main", fontSize: "0.9rem" }}>:</Typography>
          <Typography sx={{ color: "error.main", fontSize: "1.45rem", fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>{score.axis}</Typography>
        </Stack>
      </Box>
      <ComparisonMetric label={t("stats.liveGame.killsShort")} allies={allies.kills} axis={axis.kills} />
      <ComparisonMetric label="K/D" allies={allies.kdr.toFixed(2)} axis={axis.kdr.toFixed(2)} />
      <ComparisonMetric label="TK" allies={allies.teamkills} axis={axis.teamkills} warn />
      <Box sx={{ px: 0.8, py: 1, textAlign: "center" }}>
        <Typography sx={{ color: "text.disabled", fontSize: "0.58rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          {t("stats.liveGame.balance")}
        </Typography>
        <Typography sx={{ mt: 0.3, color: Math.abs(delta) >= 20 ? "warning.main" : "text.secondary", fontSize: "0.72rem", fontWeight: 600, fontVariantNumeric: "tabular-nums" }}>
          {delta > 0 ? `+${delta} ${t("views.team.allies")}` : delta < 0 ? `+${Math.abs(delta)} ${t("views.team.axis")}` : t("stats.liveGame.even")}
        </Typography>
      </Box>
    </Box>
  );
};

const LoadingBoard = () => (
  <Stack spacing={1}>
    <Skeleton variant="rectangular" height={66} sx={{ borderRadius: 0 }} />
    <Skeleton variant="rectangular" height={46} sx={{ borderRadius: 0 }} />
    <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr", md: "1fr 120px 1fr" }, gap: 1 }}>
      <Skeleton variant="rectangular" height={540} sx={{ borderRadius: 0 }} />
      <Skeleton variant="rectangular" height={540} sx={{ borderRadius: 0 }} />
      <Skeleton variant="rectangular" height={540} sx={{ borderRadius: 0 }} />
    </Box>
  </Stack>
);

export default function LiveGamePage() {
  const { t } = useTranslation();
  const initialData = useLoaderData();
  const desktopTeams = useMediaQuery("(min-width:900px)");
  const inlineInspector = useMediaQuery("(min-width:1440px)");
  const statsQuery = useQuery({ ...gameQueryOptions.live(), initialData: initialData?.stats });
  const gameQuery = useQuery({ ...gameQueryOptions.publicState(), initialData: initialData?.game });
  const [search, setSearch] = useState("");
  const [filter, setFilter] = useState("all");
  const [sortKey, setSortKey] = useState("kill_death_ratio");
  const [sortDescending, setSortDescending] = useState(true);
  const [pageSize, setPageSize] = useState(17);
  const [teamPages, setTeamPages] = useState({ allies: 0, axis: 0 });
  const [activeMobileTeam, setActiveMobileTeam] = useState("allies");
  const [selectedPlayerId, setSelectedPlayerId] = useState(null);
  const [inspectorOpen, setInspectorOpen] = useState(false);
  const [checkedIds, setCheckedIds] = useState(() => new Set());

  const payload = statsQuery.data ?? {};
  const game = gameQuery.data ?? {};
  const players = useMemo(
    () => (Array.isArray(payload.stats) ? payload.stats : []).map(normalizeLiveGamePlayer),
    [payload.stats]
  );
  const playerNames = useMemo(() => new Map(players.map((player) => [player.player_id, player.player])), [players]);
  const normalizedSearch = search.trim().toLowerCase();
  const filteredPlayers = useMemo(() => {
    const filtered = players.filter((player) => {
      if (normalizedSearch && !getPlayerSearchText(player).includes(normalizedSearch)) return false;
      if (filter === "online" && player.status !== "online") return false;
      if (filter === "risk" && player.teamkills <= 0 && player.teamkills_streak <= 0) return false;
      return true;
    });
    return sortLiveGamePlayers(filtered, sortKey, sortDescending);
  }, [filter, normalizedSearch, players, sortDescending, sortKey]);
  const alliedPlayers = filteredPlayers.filter((player) => player.team === "allies");
  const axisPlayers = filteredPlayers.filter((player) => player.team === "axis");
  const unknownPlayers = filteredPlayers.filter((player) => player.team === "unknown");
  const selectedPlayer = players.find((player) => player.player_id === selectedPlayerId) ?? null;
  const selectedRecipients = players
    .filter((player) => checkedIds.has(player.player_id))
    .map((player) => ({ name: player.player, player_id: player.player_id }));
  const score = { allied: Number(game.score?.allied) || 0, axis: Number(game.score?.axis) || 0 };
  const stale = isSnapshotStale(payload);
  const snapshotAge = getSnapshotAge(payload.snapshot_timestamp);

  useEffect(() => {
    if (!selectedPlayerId && filteredPlayers[0]) setSelectedPlayerId(filteredPlayers[0].player_id);
  }, [filteredPlayers, selectedPlayerId]);

  useEffect(() => {
    if (inlineInspector) setInspectorOpen(false);
  }, [inlineInspector]);

  useEffect(() => {
    setTeamPages({ allies: 0, axis: 0 });
  }, [filter, normalizedSearch, pageSize, sortDescending, sortKey]);

  const handlePlayerSelect = (player) => {
    setSelectedPlayerId(player.player_id);
    if (!inlineInspector) setInspectorOpen(true);
  };

  const handlePlayerCheck = (player, checked) => {
    setCheckedIds((current) => {
      const next = new Set(current);
      if (checked) next.add(player.player_id);
      else next.delete(player.player_id);
      return next;
    });
  };

  const handleTeamCheck = (teamPlayers, checked) => {
    setCheckedIds((current) => {
      const next = new Set(current);
      teamPlayers.forEach((player) => (checked ? next.add(player.player_id) : next.delete(player.player_id)));
      return next;
    });
  };

  const commonTableProps = {
    selectedPlayerId,
    checkedIds,
    onPlayerSelect: handlePlayerSelect,
    onPlayerCheck: handlePlayerCheck,
    onTeamCheck: handleTeamCheck,
    t,
  };

  const updatedLabel = statsQuery.error
    ? t("stats.liveGame.connectionError")
    : stale && snapshotAge !== null
      ? t("stats.liveGame.staleAge", { seconds: Math.round(snapshotAge / 1000) })
      : t("stats.liveGame.liveUpdated");

  return (
    <Stack className="wardogs-live-statistics" spacing={1.25} sx={{ width: "100%", maxWidth: "none", minWidth: 0, pb: 2 }}>
      <PageHeader
        eyebrow={t("stats.liveGame.eyebrow")}
        title={t("stats.liveGame.title")}
        subtitle={t("stats.liveGame.subtitle")}
        actions={
          <Stack direction="row" alignItems="center" gap={0.7}>
            <Box component="span" sx={{ width: 7, height: 7, bgcolor: statsQuery.error ? "error.main" : stale ? "warning.main" : "success.main" }} />
            <Typography sx={{ color: statsQuery.error ? "error.main" : stale ? "warning.main" : "text.secondary", fontSize: "0.68rem" }}>{updatedLabel}</Typography>
          </Stack>
        }
      />

      <Box data-theme-surface="panel" sx={{ position: "relative", border: "1px solid", borderColor: "divider", bgcolor: "background.paper" }}>
        {(statsQuery.isFetching || gameQuery.isFetching) && <LinearProgress sx={{ position: "absolute", zIndex: 2, inset: "0 0 auto", height: 2 }} />}
        <Box sx={{ display: "grid", gridTemplateColumns: { xs: "1fr 1fr", md: "1.35fr .8fr .72fr .8fr 1.35fr" } }}>
          <MatchItem label={t("stats.liveGame.currentMap")} value={getLayerLabel(game.current_map)} icon={<MapOutlinedIcon sx={{ color: "info.main", fontSize: 18 }} />} />
          <MatchItem label={t("stats.liveGame.mode")} value={getLayerMode(game.current_map)} />
          <MatchItem label={t("stats.liveGame.score")} value={`${score.allied} : ${score.axis}`} emphasis align="center" />
          <MatchItem label={t("stats.liveGame.remaining")} value={formatMatchDuration(game.time_remaining)} icon={<TimerOutlinedIcon sx={{ color: "primary.main", fontSize: 18 }} />} />
          <MatchItem label={t("stats.liveGame.nextMap")} value={getLayerLabel(game.next_map)} icon={<MapOutlinedIcon sx={{ color: "text.secondary", fontSize: 18 }} />} />
        </Box>
      </Box>

      <Box data-theme-surface="panel"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "minmax(220px, 1fr) auto auto auto" },
          minWidth: 0,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        <Box sx={{ p: 0.65, borderRight: { lg: "1px solid" }, borderBottom: { xs: "1px solid", lg: 0 }, borderColor: "divider" }}>
          <DebouncedSearchInput placeholder={t("stats.liveGame.searchPlayer")} initialValue={search} onChange={setSearch} sx={{ width: "100%", maxWidth: "none" }} />
        </Box>
        <ToggleButtonGroup
          exclusive
          value={filter}
          onChange={(_event, value) => value && setFilter(value)}
          size="small"
          aria-label={t("stats.liveGame.filter")}
          sx={{ minWidth: 0, overflowX: "auto", borderRight: { lg: "1px solid" }, borderColor: "divider", "& .MuiToggleButton-root": { minHeight: 42, px: 1.2, border: 0, borderRight: "1px solid", borderColor: "divider", borderRadius: 0, whiteSpace: "nowrap", fontSize: "0.68rem" } }}
        >
          <ToggleButton value="all">{t("stats.liveGame.filterAll")}</ToggleButton>
          <ToggleButton value="online">{t("stats.liveGame.filterOnline")}</ToggleButton>
          <ToggleButton value="risk">{t("stats.liveGame.filterRisk")}</ToggleButton>
        </ToggleButtonGroup>
        <Stack direction="row" alignItems="center" sx={{ minWidth: 0, borderRight: { lg: "1px solid" }, borderColor: "divider" }}>
          <FormControl size="small" sx={{ minWidth: 148 }}>
            <Select
              value={sortKey}
              onChange={(event) => {
                const value = event.target.value;
                setSortKey(value);
                setSortDescending(value !== "player");
              }}
              inputProps={{ "aria-label": t("stats.liveGame.sorting") }}
              sx={{ minHeight: 42, borderRadius: 0, "& fieldset": { border: 0 } }}
            >
              <MenuItem value="kill_death_ratio">{t("stats.liveGame.sortKdr")}</MenuItem>
              <MenuItem value="kills">{t("stats.liveGame.sortKills")}</MenuItem>
              <MenuItem value="teamkills">{t("stats.liveGame.sortTeamkills")}</MenuItem>
              <MenuItem value="time_seconds">{t("stats.liveGame.sortTime")}</MenuItem>
              <MenuItem value="player">{t("stats.liveGame.sortName")}</MenuItem>
            </Select>
          </FormControl>
          <Button
            aria-label={t("stats.liveGame.toggleSortDirection")}
            onClick={() => setSortDescending((value) => !value)}
            sx={{ minWidth: 38, height: 42, borderLeft: "1px solid", borderColor: "divider", borderRadius: 0, fontVariantNumeric: "tabular-nums" }}
          >
            {sortDescending ? <ArrowDownwardIcon sx={{ fontSize: 17 }} /> : <ArrowUpwardIcon sx={{ fontSize: 17 }} />}
          </Button>
        </Stack>
        <Stack direction="row" alignItems="stretch" sx={{ minWidth: 0, overflowX: "auto" }}>
          <ActionMenuButton
            actions={generatePlayerActions({ multiAction: true, onlineAction: false })}
            recipients={selectedRecipients}
            renderButton={(props) => (
              <Button {...props} disabled={!selectedRecipients.length} startIcon={<GroupIcon />} sx={{ minHeight: 42, minWidth: 112, borderRadius: 0 }}>
                {selectedRecipients.length ? t("stats.liveGame.selected", { count: selectedRecipients.length }) : t("stats.liveGame.noneSelected")}
              </Button>
            )}
          />
          <Divider orientation="vertical" flexItem />
          <FormControl size="small" sx={{ minWidth: 82 }}>
            <Select
              value={pageSize}
              onChange={(event) => setPageSize(Number(event.target.value))}
              inputProps={{ "aria-label": t("stats.liveGame.pageSize") }}
              sx={{ minHeight: 42, borderRadius: 0, "& fieldset": { border: 0 } }}
            >
              {[17, 25, 50, 100].map((size) => (
                <MenuItem key={size} value={size}>{t("stats.liveGame.showCount", { count: size })}</MenuItem>
              ))}
            </Select>
          </FormControl>
          <Divider orientation="vertical" flexItem />
          <Button
            startIcon={<DownloadIcon />}
            onClick={() => downloadGame(filteredPlayers)}
            sx={{ minHeight: 42, px: 1.25, borderRadius: 0, whiteSpace: "nowrap" }}
          >
            {t("stats.liveGame.exportCsv")}
          </Button>
        </Stack>
      </Box>

      {(statsQuery.error || gameQuery.error) && (
        <Alert severity="warning" sx={{ borderRadius: 0 }} action={<Button onClick={() => { statsQuery.refetch(); gameQuery.refetch(); }}>{t("stats.liveGame.retry")}</Button>}>
          {statsQuery.error && gameQuery.error ? t("stats.liveGame.loadError") : t("stats.liveGame.partialError")}
        </Alert>
      )}

      {!players.length && statsQuery.isLoading ? (
        <LoadingBoard />
      ) : (
        <>
          {!desktopTeams && (
            <ToggleButtonGroup
              exclusive
              fullWidth
              value={activeMobileTeam}
              onChange={(_event, value) => value && setActiveMobileTeam(value)}
              sx={{ "& .MuiToggleButton-root": { minHeight: 44, borderRadius: 0 } }}
            >
              <ToggleButton value="allies">{t("views.team.allies")} {alliedPlayers.length}</ToggleButton>
              <ToggleButton value="axis">{t("views.team.axis")} {axisPlayers.length}</ToggleButton>
            </ToggleButtonGroup>
          )}

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: inlineInspector
                ? "minmax(330px, 1fr) 122px minmax(330px, 1fr) minmax(280px, 310px)"
                : desktopTeams
                  ? "minmax(280px, 1fr) 118px minmax(280px, 1fr)"
                  : "minmax(0, 1fr)",
              gap: 1,
              alignItems: "stretch",
              minWidth: 0,
            }}
          >
            {(desktopTeams || activeMobileTeam === "allies") && (
              <LiveTeamTable
                team="allies"
                label={t("views.team.allies")}
                players={alliedPlayers}
                page={teamPages.allies}
                pageSize={pageSize}
                onPageChange={(page) => setTeamPages((current) => ({ ...current, allies: page }))}
                {...commonTableProps}
              />
            )}
            {desktopTeams && <ComparisonRail alliedPlayers={alliedPlayers} axisPlayers={axisPlayers} score={score} t={t} />}
            {(desktopTeams || activeMobileTeam === "axis") && (
              <LiveTeamTable
                team="axis"
                label={t("views.team.axis")}
                players={axisPlayers}
                page={teamPages.axis}
                pageSize={pageSize}
                onPageChange={(page) => setTeamPages((current) => ({ ...current, axis: page }))}
                {...commonTableProps}
              />
            )}
            {inlineInspector && (
              <Box sx={{ minWidth: 0 }}>
                <LiveGameInspector player={selectedPlayer} playerNames={playerNames} t={t} />
              </Box>
            )}
          </Box>

          {unknownPlayers.length > 0 && (
            <Alert severity="info" sx={{ borderRadius: 0 }}>
              {t("stats.liveGame.unknownPlayers", { count: unknownPlayers.length })}
            </Alert>
          )}
        </>
      )}

      <Typography sx={{ color: "text.disabled", fontSize: "0.65rem" }}>
        {t("stats.liveGame.dataScope")}
      </Typography>

      <Drawer
        anchor="right"
        open={!inlineInspector && inspectorOpen}
        onClose={() => setInspectorOpen(false)}
        PaperProps={{ sx: { width: { xs: "100%", sm: 390 }, maxWidth: "100%", bgcolor: "background.default", p: 1 } }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" sx={{ mb: 1, pl: 0.5 }}>
          <Typography sx={{ fontSize: "0.72rem", fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
            {t("stats.liveGame.playerDetails")}
          </Typography>
          <IconButton aria-label={t("common.close")} onClick={() => setInspectorOpen(false)} sx={{ borderRadius: 0 }}>
            <CloseIcon />
          </IconButton>
        </Stack>
        <LiveGameInspector player={selectedPlayer} playerNames={playerNames} t={t} compact />
      </Drawer>
    </Stack>
  );
}
