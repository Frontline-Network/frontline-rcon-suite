import { useCallback, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import {
  getCoreRowModel,
  getExpandedRowModel,
  getFilteredRowModel,
  getPaginationRowModel,
  getSortedRowModel,
  useReactTable,
} from "@tanstack/react-table";
import { Box, Skeleton, Stack, Tab, Tabs, Typography } from "@mui/material";
import AccessTimeOutlinedIcon from "@mui/icons-material/AccessTimeOutlined";
import ArrowBackIosNewIcon from "@mui/icons-material/ArrowBackIosNew";
import CalendarTodayOutlinedIcon from "@mui/icons-material/CalendarTodayOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import FingerprintOutlinedIcon from "@mui/icons-material/FingerprintOutlined";
import GpsFixedOutlinedIcon from "@mui/icons-material/GpsFixedOutlined";
import LocalFireDepartmentOutlinedIcon from "@mui/icons-material/LocalFireDepartmentOutlined";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import SportsMmaOutlinedIcon from "@mui/icons-material/SportsMmaOutlined";
import TrackChangesOutlinedIcon from "@mui/icons-material/TrackChangesOutlined";
import VolunteerActivismOutlinedIcon from "@mui/icons-material/VolunteerActivismOutlined";
import dayjs from "dayjs";
import { useTranslation } from "react-i18next";

import { ActionMenu } from "@/features/player-action/ActionMenu";
import { generatePlayerActions } from "@/features/player-action/actions";
import { gameQueryOptions } from "@/queries/game-query";
import { getGameDuration } from "@/utils/lib";
import { resolveMapImageName } from "@/utils/map-images.mjs";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";

import { createGameColumns } from "./game-columns";
import { getHistoricalPlayerLabel } from "./game-detail-utils";
import PlayersTable from "./game-table";

const HISTORICAL_PLAYER_ACTIONS = generatePlayerActions({
  multiAction: false,
  onlineAction: false,
});

export const DOSSIER_BORDER = "rgba(214, 184, 112, 0.2)";

const METRIC_KEYS = [
  "kills",
  "combat",
  "support",
  "offense",
  "defense",
  "kills_streak",
];

const METRIC_ICONS = {
  kills: GpsFixedOutlinedIcon,
  combat: SportsMmaOutlinedIcon,
  support: VolunteerActivismOutlinedIcon,
  offense: LocalFireDepartmentOutlinedIcon,
  defense: ShieldOutlinedIcon,
  kills_streak: TrackChangesOutlinedIcon,
};

const SectionHeading = ({ children, id, component = "h2" }) => (
  <Typography
    component={component}
    id={id}
    variant="overline"
    color="primary.main"
    sx={{
      display: "flex",
      alignItems: "center",
      minHeight: 36,
      px: 1.5,
      fontWeight: 900,
      letterSpacing: "0.11em",
      borderBottom: "1px solid",
      borderColor: DOSSIER_BORDER,
    }}
  >
    {children}
  </Typography>
);

const RankedMetric = ({ playerStats, statsKey, limit = 6 }) => {
  const { t } = useTranslation();
  const Icon = METRIC_ICONS[statsKey];
  const title = t("stats.gameDetails.metrics." + statsKey, {
    defaultValue: statsKey.replace("_", " ").toUpperCase(),
  });
  const leaders = useMemo(
    () =>
      [...playerStats]
        .filter((player) => Number.isFinite(Number(player?.[statsKey])))
        .sort((a, b) => Number(b[statsKey]) - Number(a[statsKey]))
        .filter((player) => Number(player[statsKey]) > 0)
        .slice(0, limit),
    [limit, playerStats, statsKey]
  );

  return (
    <Box sx={{ minWidth: 0, p: { xs: 1.25, md: 1.5 } }}>
      <Stack direction="row" alignItems="center" gap={1} sx={{ mb: 0.75 }}>
        <Icon aria-hidden="true" sx={{ color: "primary.main", fontSize: 19 }} />
        <Typography
          variant="overline"
          sx={{ fontWeight: 900, letterSpacing: "0.1em" }}
        >
          {title}
        </Typography>
      </Stack>
      {leaders.length ? (
        <Stack gap={0.25}>
          {leaders.map((player, index) => (
            <Box
              key={player.player_id ?? statsKey + "-" + index}
              sx={{
                display: "grid",
                gridTemplateColumns: "24px minmax(0, 1fr) auto",
                alignItems: "baseline",
                minHeight: 20,
                gap: 0.75,
              }}
            >
              <Typography
                variant="body2"
                color={index === 0 ? "text.primary" : "text.secondary"}
              >
                {index + 1}
              </Typography>
              <Typography
                variant="body2"
                noWrap
                sx={{
                  color: index === 0 ? "text.primary" : "text.secondary",
                }}
              >
                {getHistoricalPlayerLabel(player)}
              </Typography>
              <Typography
                variant="body2"
                color="primary.main"
                sx={{
                  fontWeight: 800,
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {player[statsKey]}
              </Typography>
            </Box>
          ))}
        </Stack>
      ) : (
        <Typography variant="body2" color="text.secondary">
          {t("stats.gameDetails.noMetricData")}
        </Typography>
      )}
    </Box>
  );
};

export const PerformanceMatrix = ({ playerStats }) => {
  const { t } = useTranslation();
  const [mobileMetric, setMobileMetric] = useState(METRIC_KEYS[0]);

  return (
    <Box data-theme-surface="panel"
      component="section"
      aria-labelledby="completed-game-performance-heading"
      sx={{ border: "1px solid", borderColor: DOSSIER_BORDER }}
    >
      <SectionHeading id="completed-game-performance-heading">
        {t("stats.gameDetails.bestPerformances")}
      </SectionHeading>
      <Tabs
        value={mobileMetric}
        onChange={(_, value) => setMobileMetric(value)}
        variant="scrollable"
        scrollButtons="auto"
        aria-label={t("stats.gameDetails.metricFilter")}
        sx={{
          display: { xs: "flex", sm: "none" },
          minHeight: 40,
          borderBottom: "1px solid",
          borderColor: DOSSIER_BORDER,
          "& .MuiTab-root": {
            minHeight: 40,
            borderRadius: 0,
            px: 1.5,
          },
        }}
      >
        {METRIC_KEYS.map((metric) => (
          <Tab
            key={metric}
            value={metric}
            label={t("stats.gameDetails.metrics." + metric)}
          />
        ))}
      </Tabs>
      <Box sx={{ display: { xs: "block", sm: "none" } }}>
        <RankedMetric playerStats={playerStats} statsKey={mobileMetric} />
      </Box>
      <Box
        sx={{
          display: { xs: "none", sm: "grid" },
          gridTemplateColumns: {
            sm: "repeat(2, minmax(0, 1fr))",
            lg: "repeat(3, minmax(0, 1fr))",
          },
          "& > *": {
            borderRight: "1px solid",
            borderBottom: "1px solid",
            borderColor: DOSSIER_BORDER,
          },
          "& > *:nth-of-type(2n)": {
            borderRight: { sm: 0, lg: "1px solid" },
          },
          "& > *:nth-of-type(3n)": { borderRight: { lg: 0 } },
          "& > *:nth-last-of-type(-n+2)": {
            borderBottom: { sm: 0, lg: "1px solid" },
          },
          "& > *:nth-last-of-type(-n+3)": {
            borderBottom: { lg: 0 },
          },
        }}
      >
        {METRIC_KEYS.map((metric) => (
          <RankedMetric
            key={metric}
            playerStats={playerStats}
            statsKey={metric}
          />
        ))}
      </Box>
    </Box>
  );
};

const Fact = ({ icon: Icon, label, value }) => (
  <Box
    sx={{
      display: "grid",
      gridTemplateColumns: "20px minmax(70px, 0.8fr) minmax(0, 1fr)",
      alignItems: "center",
      gap: 0.75,
    }}
  >
    <Icon aria-hidden="true" sx={{ color: "text.secondary", fontSize: 17 }} />
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ textTransform: "uppercase" }}
    >
      {label}
    </Typography>
    <Typography
      variant="body2"
      noWrap
      sx={{ fontVariantNumeric: "tabular-nums" }}
    >
      {value}
    </Typography>
  </Box>
);

export const MatchDossier = ({
  mapLayer,
  result,
  start,
  end,
  id,
  serverNumber,
}) => {
  const { t } = useTranslation();
  const [imageFailed, setImageFailed] = useState(false);
  const startValue = dayjs(start);
  const endValue = dayjs(end);
  const hasStart = startValue.isValid();
  const hasEnd = endValue.isValid();
  const mapName =
    mapLayer?.map?.pretty_name ??
    mapLayer?.pretty_name ??
    t("stats.games.unknownMap");
  const descriptor = [
    mapName,
    mapLayer?.game_mode ? getMapModeLabel(t, mapLayer.game_mode) : null,
    mapLayer?.environment
      ? getMapEnvironmentLabel(t, mapLayer.environment)
      : null,
  ]
    .filter(Boolean)
    .join(" · ");
  const imageName = resolveMapImageName(mapLayer);
  const alliesScore = result?.allied ?? "?";
  const axisScore = result?.axis ?? "?";

  return (
    <Box component="section" aria-labelledby="completed-game-heading">
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "flex-start", sm: "center" }}
        justifyContent="space-between"
        gap={0.5}
        sx={{ minHeight: 34, px: 1 }}
      >
        <Typography
          component="h1"
          id="completed-game-heading"
          variant="overline"
          color="primary.main"
          sx={{ fontWeight: 900, letterSpacing: "0.12em" }}
        >
          {t("stats.gameDetails.completedGame")}
        </Typography>
        <Typography
          component={Link}
          to="/stats/games"
          variant="overline"
          color="text.secondary"
          sx={{
            display: "inline-flex",
            alignItems: "center",
            gap: 0.75,
            textDecoration: "none",
            "&:hover": { color: "primary.main" },
          }}
        >
          <ArrowBackIosNewIcon sx={{ fontSize: 12 }} />
          {t("stats.gameDetails.backToArchive")}
        </Typography>
      </Stack>
      <Box data-theme-surface="panel"
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "minmax(220px, 0.85fr) minmax(300px, 1.15fr)",
            lg: "31% 41% 28%",
          },
          border: "1px solid",
          borderColor: DOSSIER_BORDER,
          minHeight: { lg: 182 },
          overflow: "hidden",
        }}
      >
        <Box
          sx={{
            minHeight: { xs: 168, sm: 205, lg: 182 },
            borderRight: { sm: "1px solid" },
            borderColor: DOSSIER_BORDER,
            bgcolor: "background.paper",
            position: "relative",
          }}
        >
          {imageName && !imageFailed ? (
            <Box
              component="img"
              src={"/maps/" + imageName}
              alt={mapName}
              onError={() => setImageFailed(true)}
              sx={{
                display: "block",
                width: "100%",
                height: "100%",
                position: "absolute",
                inset: 0,
                objectFit: "cover",
              }}
            />
          ) : (
            <Stack
              alignItems="center"
              justifyContent="center"
              gap={1}
              sx={{ height: "100%", color: "text.disabled" }}
            >
              <MapOutlinedIcon />
              <Typography variant="caption">{mapName}</Typography>
            </Stack>
          )}
        </Box>
        <Stack
          alignItems="center"
          justifyContent="center"
          gap={1.25}
          sx={{
            minWidth: 0,
            px: { xs: 1.5, md: 2 },
            py: { xs: 2, lg: 1.5 },
            borderRight: { lg: "1px solid" },
            borderColor: DOSSIER_BORDER,
          }}
        >
          <Typography
            variant="subtitle1"
            color="text.secondary"
            noWrap
            sx={{ maxWidth: "100%" }}
          >
            {descriptor}
          </Typography>
          <Stack
            direction="row"
            alignItems="center"
            justifyContent="center"
            gap={{ xs: 1, sm: 1.5, md: 2 }}
          >
            <Typography
              variant="overline"
              color="info.light"
              sx={{
                display: { xs: "none", sm: "block" },
                fontWeight: 900,
              }}
            >
              {t("views.team.allies")}
            </Typography>
            <Typography
              sx={{
                color: "info.main",
                fontFamily:
                  '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
                fontWeight: 900,
                fontSize: { xs: "3.25rem", md: "4rem" },
                lineHeight: 0.95,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {alliesScore}
            </Typography>
            <Typography
              sx={{
                color: "text.primary",
                fontSize: { xs: "2rem", md: "2.6rem" },
                lineHeight: 1,
              }}
            >
              :
            </Typography>
            <Typography
              sx={{
                color: "error.main",
                fontFamily:
                  '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
                fontWeight: 900,
                fontSize: { xs: "3.25rem", md: "4rem" },
                lineHeight: 0.95,
                fontVariantNumeric: "tabular-nums",
              }}
            >
              {axisScore}
            </Typography>
            <Typography
              variant="overline"
              color="error.light"
              sx={{
                display: { xs: "none", sm: "block" },
                fontWeight: 900,
              }}
            >
              {t("views.team.axis")}
            </Typography>
          </Stack>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: { xs: "block", sm: "none" } }}
          >
            {t("stats.games.scoreLabel", {
              allied: alliesScore,
              axis: axisScore,
            })}
          </Typography>
        </Stack>
        <Box
          sx={{
            gridColumn: { sm: "1 / -1", lg: "auto" },
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              lg: "1fr",
            },
            alignContent: "center",
            gap: 0.9,
            p: { xs: 1.5, md: 2 },
            borderTop: { xs: "1px solid", lg: 0 },
            borderColor: DOSSIER_BORDER,
          }}
        >
          <Fact
            icon={CalendarTodayOutlinedIcon}
            label={t("stats.gameDetails.date")}
            value={hasStart ? startValue.format("L") : "–"}
          />
          <Fact
            icon={AccessTimeOutlinedIcon}
            label={t("stats.gameDetails.start")}
            value={hasStart ? startValue.format("LT") : "–"}
          />
          <Fact
            icon={AccessTimeOutlinedIcon}
            label={t("stats.gameDetails.end")}
            value={hasEnd ? endValue.format("LT") : "–"}
          />
          <Fact
            icon={AccessTimeOutlinedIcon}
            label={t("stats.gameDetails.duration")}
            value={hasStart && hasEnd ? getGameDuration(start, end) : "–"}
          />
          {serverNumber != null ? (
            <Fact
              icon={DnsOutlinedIcon}
              label={t("stats.gameDetails.server")}
              value={t("stats.gameDetails.serverNumber", {
                number: serverNumber,
              })}
            />
          ) : null}
          {id != null ? (
            <Fact
              icon={FingerprintOutlinedIcon}
              label={t("stats.gameDetails.gameId")}
              value={id}
            />
          ) : null}
        </Box>
      </Box>
    </Box>
  );
};

export const GameTable = ({ playerStats, columns }) => {
  const [playersRowSelection, setPlayersRowSelection] = useState({});
  const [playerActionMenu, setPlayerActionMenu] = useState({
    anchorEl: null,
    player: null,
  });
  const [pagination, setPagination] = useState({
    pageIndex: 0,
    pageSize: 100,
  });
  const [columnVisibility, setColumnVisibility] = useState({
    kpm: false,
    tk_streak: false,
    td: false,
    td_streak: false,
  });
  const openPlayerActionMenu = useCallback((anchorEl, player) => {
    setPlayerActionMenu({ anchorEl, player });
  }, []);
  const setPlayerActionMenuAnchor = useCallback((anchorEl) => {
    setPlayerActionMenu((current) => ({ ...current, anchorEl }));
  }, []);

  const table = useReactTable({
    data: playerStats,
    columns,
    getRowCanExpand: () => true,
    getCoreRowModel: getCoreRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getExpandedRowModel: getExpandedRowModel(),
    getPaginationRowModel: getPaginationRowModel(),
    onRowSelectionChange: setPlayersRowSelection,
    onPaginationChange: setPagination,
    onColumnVisibilityChange: setColumnVisibility,
    getRowId: (row) => row.player_id,
    meta: {
      openPlayerActionMenu,
      activePlayerActionId: playerActionMenu.anchorEl
        ? playerActionMenu.player?.player_id
        : null,
    },
    initialState: {
      sorting: [{ id: "time", desc: true }],
    },
    state: {
      rowSelection: playersRowSelection,
      pagination,
      columnVisibility,
    },
  });

  const selectedPlayers = useMemo(
    () =>
      table
        .getSelectedRowModel()
        .rows.map((row) => row.original)
        .filter(Boolean)
        .map((playerRow) => ({
          player_id: playerRow.player_id,
          name: playerRow.player,
        })),
    [playersRowSelection, table]
  );

  return (
    <>
      <PlayersTable
        table={table}
        selectedPlayers={selectedPlayers}
        onColumnVisibilityChange={(columnId, visible) =>
          setColumnVisibility((current) => ({
            ...current,
            [columnId]: visible,
          }))
        }
      />
      {playerActionMenu.player ? (
        <ActionMenu
          actions={HISTORICAL_PLAYER_ACTIONS}
          recipients={playerActionMenu.player}
          anchorEl={playerActionMenu.anchorEl}
          setAnchorEl={setPlayerActionMenuAnchor}
          menuId="completed-game-player-actions-menu"
        />
      ) : null}
    </>
  );
};

const CompletedGamePage = () => {
  const { t } = useTranslation();
  const { gameId } = useParams();
  const { data, isLoading, error } = useQuery({
    ...gameQueryOptions.detail(gameId),
  });
  const playerStats = Array.isArray(data?.player_stats)
    ? data.player_stats
    : [];
  const hasAssignments = playerStats.some(
    (player) =>
      typeof player?.role === "string" || typeof player?.unit === "string"
  );
  const columns = useMemo(
    () => createGameColumns(t, { showAssignments: hasAssignments }),
    [hasAssignments, t]
  );

  if (isLoading) {
    return (
      <Stack gap={2} sx={{ p: { xs: 1.5, md: 3 } }}>
        <Skeleton variant="rectangular" height={34} />
        <Skeleton variant="rectangular" height={182} />
        <Skeleton variant="rectangular" height={360} />
      </Stack>
    );
  }

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        {t("stats.gameDetails.loadError", { message: error.message })}
      </Box>
    );
  }

  return (
    <Box
      className="wardogs-completed-game"
      sx={{
        p: { xs: 1, sm: 1.5, md: 2 },
        minHeight: "100%",
        overflow: "visible",
      }}
    >
      <Stack gap={1.5}>
        <MatchDossier
          mapLayer={data.map}
          result={data.result}
          start={data.start}
          end={data.end}
          id={data.id}
          serverNumber={data.server_number}
        />
        <PerformanceMatrix playerStats={playerStats} />
        <GameTable playerStats={playerStats} columns={columns} />
      </Stack>
    </Box>
  );
};

export default CompletedGamePage;
