import { DebouncedSearchInput } from "@/components/shared/DebouncedSearchInput";
import {
  Alert,
  Box,
  Button,
  ButtonBase,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Skeleton,
  Stack,
  Tab,
  Tabs,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import RadioButtonCheckedIcon from "@mui/icons-material/RadioButtonChecked";
import ReplayIcon from "@mui/icons-material/Replay";
import dayjs from "dayjs";
import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import { Link, useSearchParams } from "react-router-dom";
import { getGameDuration } from "@/utils/lib";
import { getMapEnvironmentLabel, getMapModeLabel } from "@/utils/mapLabels";
import NavPagination from "./nav-pagination";

const JOURNAL_BORDER = "rgba(214, 184, 112, 0.2)";

function GameMapThumbnail({ game }) {
  const [failed, setFailed] = useState(false);
  const imageName = game?.map?.image_name;

  if (!imageName || failed) {
    return (
      <Box
        aria-hidden="true"
        sx={{
          width: { xs: 68, sm: 88 },
          height: { xs: 42, sm: 50 },
          display: "grid",
          placeItems: "center",
          bgcolor: "action.hover",
          color: "text.disabled",
          border: "1px solid",
          borderColor: "divider",
          flexShrink: 0,
        }}
      >
        <MapOutlinedIcon fontSize="small" />
      </Box>
    );
  }

  return (
    <Box
      component="img"
      src={`/maps/icons/${imageName}`}
      alt=""
      onError={() => setFailed(true)}
      sx={{
        width: { xs: 68, sm: 88 },
        height: { xs: 42, sm: 50 },
        objectFit: "cover",
        border: "1px solid",
        borderColor: "divider",
        flexShrink: 0,
      }}
    />
  );
}

function LoadingJournal() {
  return (
    <Stack aria-label="loading games">
      {Array.from({ length: 6 }, (_, index) => (
        <Stack
          key={index}
          direction="row"
          alignItems="center"
          gap={2}
          sx={{
            minHeight: 66,
            px: 1.5,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          <Skeleton variant="text" width={56} />
          <Skeleton variant="rectangular" width={88} height={50} />
          <Skeleton variant="text" width="32%" />
          <Skeleton variant="text" width={180} sx={{ ml: "auto" }} />
        </Stack>
      ))}
    </Stack>
  );
}

function groupGamesByDate(games) {
  const groups = [];
  const groupIndex = new Map();

  games.forEach((game) => {
    const start = dayjs(game?.start);
    const key = start.isValid() ? start.format("YYYY-MM-DD") : "unknown";

    if (!groupIndex.has(key)) {
      const group = { key, date: start.isValid() ? start : null, games: [] };
      groupIndex.set(key, group);
      groups.push(group);
    }

    groupIndex.get(key).games.push(game);
  });

  return groups;
}

export function GameListTable({
  games,
  total,
  page,
  pageSize,
  maxPages,
  isLoading,
  isFetching,
  isError,
  error,
  onRetry,
}) {
  const { t } = useTranslation();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const [searchParams, setSearchParams] = useSearchParams();
  const [search, setSearch] = useState("");
  const [period, setPeriod] = useState("all");
  const [environment, setEnvironment] = useState("all");
  const [mode, setMode] = useState("all");

  const safeGames = Array.isArray(games) ? games : [];
  const modeOptions = useMemo(
    () => [
      ...new Set(safeGames.map((game) => game?.map?.game_mode).filter(Boolean)),
    ],
    [safeGames]
  );
  const environmentOptions = useMemo(
    () => [
      ...new Set(
        safeGames.map((game) => game?.map?.environment).filter(Boolean)
      ),
    ],
    [safeGames]
  );

  const baseFilteredGames = useMemo(() => {
    const needle = search.trim().toLocaleLowerCase();
    const now = dayjs();

    return safeGames.filter((game) => {
      const start = dayjs(game?.start);
      const mapName =
        game?.map?.map?.pretty_name ?? game?.map?.pretty_name ?? "";
      const gameId = String(game?.id ?? "");
      const matchesSearch =
        !needle ||
        mapName.toLocaleLowerCase().includes(needle) ||
        gameId.toLocaleLowerCase().includes(needle);
      const matchesPeriod =
        period === "all" ||
        (start.isValid() && now.diff(start, "day") <= Number(period));
      const matchesEnvironment =
        environment === "all" || game?.map?.environment === environment;

      return matchesSearch && matchesPeriod && matchesEnvironment;
    });
  }, [environment, period, safeGames, search]);

  const visibleGames = useMemo(
    () =>
      mode === "all"
        ? baseFilteredGames
        : baseFilteredGames.filter((game) => game?.map?.game_mode === mode),
    [baseFilteredGames, mode]
  );
  const groups = useMemo(() => groupGamesByDate(visibleGames), [visibleGames]);

  const modeCounts = useMemo(() => {
    const counts = new Map();
    baseFilteredGames.forEach((game) => {
      const gameMode = game?.map?.game_mode;
      if (gameMode) counts.set(gameMode, (counts.get(gameMode) ?? 0) + 1);
    });
    return counts;
  }, [baseFilteredGames]);

  const resetFilters = () => {
    setSearch("");
    setPeriod("all");
    setEnvironment("all");
    setMode("all");
  };

  const updatePageSize = (event) => {
    const next = new URLSearchParams(searchParams);
    next.set("page", "1");
    next.set("page_size", String(event.target.value));
    setSearchParams(next);
  };

  const groupLabel = (group) => {
    if (!group.date) return t("stats.games.unknownDate");
    const today = dayjs().startOf("day");
    const groupDay = group.date.startOf("day");
    const prefix = groupDay.isSame(today)
      ? t("stats.games.today")
      : groupDay.isSame(today.subtract(1, "day"))
      ? t("stats.games.yesterday")
      : null;
    const date = group.date.format("DD. MMMM YYYY");
    return prefix ? `${prefix} · ${date}` : date;
  };

  const rangeStart = total === 0 ? 0 : (page - 1) * pageSize + 1;
  const rangeEnd = Math.min(page * pageSize, total);
  const hasFilters =
    search || period !== "all" || environment !== "all" || mode !== "all";

  return (
    <Box
      component="section"
      aria-label={t("stats.games.archive")}
      aria-busy={isFetching}
      sx={{
        border: "1px solid",
        borderColor: JOURNAL_BORDER,
        bgcolor: "rgba(8, 12, 9, 0.78)",
        overflow: "hidden",
      }}
    >
      <Stack
        direction={{ xs: "column", lg: "row" }}
        sx={{ borderBottom: "1px solid", borderColor: JOURNAL_BORDER }}
      >
        <DebouncedSearchInput
          initialValue={search}
          placeholder={t("stats.games.searchPage")}
          inputProps={{ "aria-label": t("stats.games.searchPage") }}
          onChange={(value) => setSearch(String(value))}
          sx={{
            minHeight: 46,
            width: "100%",
            flex: { xs: "0 0 auto", lg: "1 1 320px" },
            "& .MuiOutlinedInput-root": { borderRadius: 0, height: 46 },
            "& fieldset": { border: 0 },
          }}
        />
        <Stack direction={{ xs: "column", sm: "row" }} sx={{ flexShrink: 0 }}>
          <FormControl
            size="small"
            sx={{
              minWidth: { xs: "100%", sm: 190 },
              "& .MuiOutlinedInput-root": { borderRadius: 0, height: 46 },
            }}
          >
            <InputLabel id="games-period-label">
              {t("stats.games.period")}
            </InputLabel>
            <Select
              labelId="games-period-label"
              value={period}
              label={t("stats.games.period")}
              onChange={(event) => setPeriod(event.target.value)}
            >
              <MenuItem value="all">{t("stats.games.allGames")}</MenuItem>
              <MenuItem value="7">
                {t("stats.games.lastDays", { count: 7 })}
              </MenuItem>
              <MenuItem value="30">
                {t("stats.games.lastDays", { count: 30 })}
              </MenuItem>
            </Select>
          </FormControl>
          <FormControl
            size="small"
            sx={{
              minWidth: { xs: "100%", sm: 190 },
              "& .MuiOutlinedInput-root": { borderRadius: 0, height: 46 },
            }}
          >
            <InputLabel id="games-environment-label">
              {t("stats.games.environment")}
            </InputLabel>
            <Select
              labelId="games-environment-label"
              value={environment}
              label={t("stats.games.environment")}
              onChange={(event) => setEnvironment(event.target.value)}
            >
              <MenuItem value="all">
                {t("stats.games.allEnvironments")}
              </MenuItem>
              {environmentOptions.map((value) => (
                <MenuItem key={value} value={value}>
                  {getMapEnvironmentLabel(t, value)}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <Button
            startIcon={<ReplayIcon />}
            onClick={resetFilters}
            disabled={!hasFilters}
            sx={{
              minHeight: 46,
              minWidth: 178,
              borderRadius: 0,
              borderLeft: "1px solid",
              borderColor: JOURNAL_BORDER,
            }}
          >
            {t("stats.games.resetFilters")}
          </Button>
        </Stack>
      </Stack>

      <Stack
        direction="row"
        alignItems="center"
        sx={{
          borderBottom: "1px solid",
          borderColor: JOURNAL_BORDER,
          minWidth: 0,
        }}
      >
        <Tabs
          value={mode}
          onChange={(_, value) => setMode(value)}
          variant="scrollable"
          scrollButtons="auto"
          aria-label={t("stats.games.modeFilter")}
          sx={{
            flex: 1,
            minHeight: 42,
            "& .MuiTab-root": { minHeight: 42, borderRadius: 0, px: 2 },
          }}
        >
          <Tab
            value="all"
            label={`${t("common.all")} ${baseFilteredGames.length}`}
          />
          {modeOptions.map((value) => (
            <Tab
              key={value}
              value={value}
              label={`${getMapModeLabel(t, value)} ${
                modeCounts.get(value) ?? 0
              }`}
            />
          ))}
        </Tabs>
        <Typography
          aria-live="polite"
          variant="overline"
          color="text.secondary"
          sx={{
            display: { xs: "none", md: "block" },
            px: 2,
            whiteSpace: "nowrap",
          }}
        >
          {t("stats.games.pageMatches", { count: visibleGames.length })}
        </Typography>
      </Stack>

      {isFetching && (
        <LinearProgress
          aria-label={t("stats.games.updating")}
          sx={{ height: 2 }}
        />
      )}

      {isError && (
        <Alert
          severity={safeGames.length ? "warning" : "error"}
          action={
            <Button color="inherit" size="small" onClick={onRetry}>
              {t("stats.games.retry")}
            </Button>
          }
          sx={{ borderRadius: 0 }}
        >
          {safeGames.length
            ? t("stats.games.partialError")
            : t("stats.games.loadError", { message: error?.message })}
        </Alert>
      )}

      {isLoading ? (
        <LoadingJournal />
      ) : groups.length ? (
        <Stack component="div">
          {groups.map((group) => (
            <Box
              component="section"
              aria-labelledby={`game-group-${group.key}`}
              key={group.key}
            >
              <Stack
                direction="row"
                alignItems="center"
                justifyContent="space-between"
                sx={{
                  minHeight: 36,
                  px: 1.5,
                  bgcolor: "rgba(255,255,255,0.015)",
                  borderBottom: "1px solid",
                  borderColor: JOURNAL_BORDER,
                  position: { xs: "sticky", md: "static" },
                  top: { xs: 0, md: "auto" },
                  zIndex: 1,
                }}
              >
                <Typography
                  component="h2"
                  id={`game-group-${group.key}`}
                  variant="overline"
                  color="primary.main"
                  sx={{ letterSpacing: "0.1em", fontWeight: 800 }}
                >
                  {groupLabel(group)}
                </Typography>
                <Typography variant="overline" color="text.secondary">
                  {t("stats.games.entries", { count: group.games.length })}
                </Typography>
              </Stack>

              {group.games.map((game) => {
                const mapName =
                  game?.map?.map?.pretty_name ??
                  game?.map?.pretty_name ??
                  t("stats.games.unknownMap");
                const start = dayjs(game?.start);
                const alliedScore = game?.result?.allied ?? "–";
                const axisScore = game?.result?.axis ?? "–";
                const modeLabel = getMapModeLabel(
                  t,
                  game?.map?.game_mode ?? t("common.unknown")
                );
                const environmentLabel = getMapEnvironmentLabel(
                  t,
                  game?.map?.environment ?? t("common.unknown")
                );
                const duration = getGameDuration(game?.start, game?.end);
                const accessibleLabel = t("stats.games.openGameLabel", {
                  map: mapName,
                  mode: modeLabel,
                  environment: environmentLabel,
                  date: start.isValid()
                    ? start.format("L LT")
                    : t("stats.games.unknownDate"),
                  allied: alliedScore,
                  axis: axisScore,
                  duration,
                });

                return (
                  <ButtonBase
                    component={Link}
                    to={`/stats/games/${game.id}`}
                    key={game.id}
                    aria-label={accessibleLabel}
                    sx={{
                      width: "100%",
                      minHeight: { xs: 84, md: 66 },
                      display: "grid",
                      gridTemplateColumns: {
                        xs: "48px 68px minmax(92px, 1fr) auto 24px",
                        sm: "64px 20px 88px minmax(170px, 1fr) minmax(150px, auto) 80px 28px",
                        lg: "82px 22px 88px minmax(220px, 1fr) minmax(250px, auto) 100px minmax(88px, 118px) 32px",
                      },
                      alignItems: "center",
                      columnGap: { xs: 0.75, md: 1.5 },
                      px: 1.5,
                      py: { xs: 0.75, md: 0.5 },
                      textAlign: "left",
                      borderBottom: "1px solid",
                      borderColor: JOURNAL_BORDER,
                      color: "text.primary",
                      "&:hover": {
                        bgcolor: "rgba(214, 184, 112, 0.06)",
                      },
                      "&:focus-visible": {
                        outline: "2px solid",
                        outlineColor: "primary.main",
                        outlineOffset: -2,
                        bgcolor: "rgba(214, 184, 112, 0.08)",
                      },
                    }}
                  >
                    <Typography
                      component="time"
                      dateTime={
                        start.isValid() ? start.toISOString() : undefined
                      }
                      sx={{
                        fontFamily:
                          '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
                        fontSize: { xs: "1rem", md: "1.15rem" },
                        fontVariantNumeric: "tabular-nums",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {start.isValid() ? start.format("LT") : "–"}
                    </Typography>
                    <RadioButtonCheckedIcon
                      aria-hidden="true"
                      sx={{
                        display: { xs: "none", sm: "block" },
                        fontSize: 13,
                        color: "text.disabled",
                      }}
                    />
                    <GameMapThumbnail game={game} />
                    <Box sx={{ minWidth: 0 }}>
                      <Typography sx={{ fontWeight: 600 }} noWrap>
                        {mapName}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        noWrap
                      >
                        {modeLabel} · {environmentLabel}
                      </Typography>
                      <Typography
                        variant="caption"
                        color="text.secondary"
                        sx={{
                          display: { xs: "block", sm: "none" },
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {duration}
                      </Typography>
                    </Box>
                    <Stack
                      direction="row"
                      alignItems="baseline"
                      justifyContent="center"
                      gap={{ xs: 0.5, lg: 1 }}
                      aria-label={t("stats.games.scoreLabel", {
                        allied: alliedScore,
                        axis: axisScore,
                      })}
                    >
                      <Typography
                        variant="overline"
                        color="info.light"
                        sx={{ display: { xs: "none", lg: "block" } }}
                      >
                        {t("stats.games.allies")}
                      </Typography>
                      <Typography
                        sx={{
                          color: "info.light",
                          fontSize: { xs: "1.1rem", md: "1.3rem" },
                          fontWeight: 800,
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {alliedScore}
                      </Typography>
                      <Typography color="text.secondary">:</Typography>
                      <Typography
                        sx={{
                          color: "error.light",
                          fontSize: { xs: "1.1rem", md: "1.3rem" },
                          fontWeight: 800,
                          fontVariantNumeric: "tabular-nums",
                        }}
                      >
                        {axisScore}
                      </Typography>
                      <Typography
                        variant="overline"
                        color="error.light"
                        sx={{ display: { xs: "none", lg: "block" } }}
                      >
                        {t("stats.games.axis")}
                      </Typography>
                    </Stack>
                    <Typography
                      color="text.secondary"
                      sx={{
                        display: { xs: "none", sm: "block" },
                        fontVariantNumeric: "tabular-nums",
                        whiteSpace: "nowrap",
                      }}
                    >
                      {duration}
                    </Typography>
                    <Typography
                      variant="caption"
                      color="text.disabled"
                      sx={{
                        display: { xs: "none", lg: "block" },
                        fontFamily: "monospace",
                      }}
                      noWrap
                    >
                      {game.id}
                    </Typography>
                    <ChevronRightIcon
                      aria-hidden="true"
                      sx={{ color: "text.secondary" }}
                    />
                  </ButtonBase>
                );
              })}
            </Box>
          ))}
        </Stack>
      ) : (
        <Stack
          alignItems="center"
          justifyContent="center"
          gap={1}
          sx={{ minHeight: 180, p: 3 }}
        >
          <Typography variant="h6">
            {safeGames.length
              ? t("stats.games.noMatchesOnPage")
              : t("stats.games.noGames")}
          </Typography>
          {hasFilters && (
            <Button onClick={resetFilters} sx={{ borderRadius: 0 }}>
              {t("stats.games.resetFilters")}
            </Button>
          )}
        </Stack>
      )}

      <Stack
        component="footer"
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ xs: "stretch", sm: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{
          minHeight: 56,
          px: 1.5,
          py: 1,
          borderTop: "1px solid",
          borderColor: JOURNAL_BORDER,
        }}
      >
        <Typography variant="caption" color="text.secondary">
          {t("stats.games.range", {
            from: rangeStart,
            to: rangeEnd,
            total,
          })}
        </Typography>
        <Stack
          direction="row"
          alignItems="center"
          justifyContent="flex-end"
          gap={1}
        >
          <NavPagination
            page={page}
            maxPages={maxPages}
            disabled={isFetching}
            compact={compact}
          />
          <FormControl size="small" sx={{ minWidth: 118 }}>
            <Select
              value={pageSize}
              onChange={updatePageSize}
              aria-label={t("stats.games.pageSize")}
              sx={{ height: 40, borderRadius: 0 }}
            >
              {[25, 50, 100].map((value) => (
                <MenuItem key={value} value={value}>
                  {t("stats.games.show", { count: value })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        </Stack>
      </Stack>
    </Box>
  );
}
