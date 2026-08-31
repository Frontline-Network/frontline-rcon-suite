import { useEffect, useMemo, useState } from "react";
import {
  alpha,
  Box,
  Button,
  Divider,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import ChatBubbleOutlineIcon from "@mui/icons-material/ChatBubbleOutline";
import GpsFixedIcon from "@mui/icons-material/GpsFixed";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import LoginIcon from "@mui/icons-material/Login";
import LogoutIcon from "@mui/icons-material/Logout";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import DescriptionOutlinedIcon from "@mui/icons-material/DescriptionOutlined";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import PersonOutlineIcon from "@mui/icons-material/PersonOutline";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import KeyboardDoubleArrowLeftIcon from "@mui/icons-material/KeyboardDoubleArrowLeft";
import KeyboardDoubleArrowRightIcon from "@mui/icons-material/KeyboardDoubleArrowRight";
import { useTranslation } from "react-i18next";
import { useGlobalStore } from "@/stores/global-state";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import {
  buildEventSummary,
  formatEventTime,
  getCategoryCounts,
  getEventCategory,
  getEventLabel,
  getRoundWindow,
  getTopPlayers,
  removePlayerIds,
} from "./event-utils";

const EventIcon = ({ log, sx }) => {
  const category = getEventCategory(log.type);
  const props = { sx: { fontSize: 17, ...sx } };
  if (category === "admin") return <GavelOutlinedIcon {...props} />;
  if (category === "chat") return <ChatBubbleOutlineIcon {...props} />;
  if (category === "kills") return <GpsFixedIcon {...props} />;
  if (category === "teamkills") return <ReportProblemOutlinedIcon {...props} />;
  if (category === "connections") {
    return String(log.type).toUpperCase() === "DISCONNECTED" ? (
      <LogoutIcon {...props} />
    ) : (
      <LoginIcon {...props} />
    );
  }
  if (category === "round") return <FlagOutlinedIcon {...props} />;
  return <DescriptionOutlinedIcon {...props} />;
};

const eventColor = (category) => {
  if (category === "teamkills") return "error.main";
  if (category === "kills") return "error.light";
  if (category === "chat") return "info.main";
  if (category === "connections") return "success.main";
  if (category === "admin") return "primary.main";
  if (category === "round") return "text.secondary";
  return "text.secondary";
};

const sectionSx = {
  border: "1px solid",
  borderColor: "divider",
  bgcolor: "background.paper",
  borderRadius: 0,
};

const formatMode = (mode, t) => {
  if (!mode) return "–";
  const normalized = String(mode).toLowerCase();
  const translated = t(`maps.gameModes.${normalized}`, { defaultValue: "" });
  return translated || mode.charAt(0).toUpperCase() + mode.slice(1);
};

function TimelineRow({ log, selected, onSelect }) {
  const { t } = useTranslation();
  const category = getEventCategory(log.type);

  return (
    <Box
      component="button"
      type="button"
      onClick={() => onSelect(log)}
      aria-pressed={selected}
      sx={(theme) => ({
        appearance: "none",
        width: "100%",
        display: "grid",
        gridTemplateColumns: {
          xs: "34px minmax(0, 1fr)",
          sm: "34px 116px 136px minmax(0, 1fr)",
        },
        gridTemplateAreas: {
          xs: '"marker summary" "marker meta"',
          sm: '"marker time type summary"',
        },
        alignItems: "center",
        minHeight: { xs: 54, sm: 42 },
        p: 0,
        border: 0,
        borderBottom: "1px solid",
        borderBottomColor: "divider",
        borderLeft: "2px solid",
        borderLeftColor: selected ? "primary.main" : "transparent",
        color: "text.primary",
        bgcolor: selected
          ? alpha(theme.palette.primary.main, 0.09)
          : "transparent",
        textAlign: "left",
        cursor: "pointer",
        "&:hover": { bgcolor: alpha(theme.palette.primary.main, 0.055) },
        "&:focus-visible": {
          outline: `2px solid ${theme.palette.primary.main}`,
          outlineOffset: -2,
        },
      })}
    >
      <Box
        sx={{
          gridArea: "marker",
          alignSelf: "stretch",
          display: "grid",
          placeItems: "center",
          borderRight: "1px solid",
          borderColor: "divider",
          color: eventColor(category),
        }}
      >
        <EventIcon log={log} />
      </Box>
      <Typography
        variant="caption"
        sx={{
          display: { xs: "none", sm: "block" },
          gridArea: "time",
          px: 1,
          color: "text.secondary",
          fontVariantNumeric: "tabular-nums",
          whiteSpace: "nowrap",
        }}
      >
        {formatEventTime(log.event_time)}
      </Typography>
      <Stack
        direction="row"
        alignItems="center"
        spacing={0.75}
        sx={{
          display: { xs: "none", sm: "flex" },
          gridArea: "type",
          minWidth: 0,
          px: 1,
          color: eventColor(category),
        }}
      >
        <Typography
          variant="caption"
          sx={{
            fontWeight: 700,
            letterSpacing: "0.05em",
            whiteSpace: "nowrap",
          }}
        >
          {getEventLabel(log.type, t)}
        </Typography>
      </Stack>
      <Typography
        variant="body2"
        sx={{
          gridArea: "summary",
          minWidth: 0,
          px: 1,
          py: { xs: 0.75, sm: 0.5 },
          overflow: "hidden",
          textOverflow: "ellipsis",
          whiteSpace: { xs: "normal", sm: "nowrap" },
          color: "text.primary",
        }}
      >
        {buildEventSummary(log, t)}
      </Typography>
      <Typography
        variant="caption"
        sx={{
          display: { xs: "block", sm: "none" },
          gridArea: "meta",
          px: 1,
          pb: 0.75,
          color: "text.secondary",
        }}
      >
        {getEventLabel(log.type, t)} ·{" "}
        {formatEventTime(log.event_time, "DD.MM.YYYY · HH:mm:ss")}
      </Typography>
    </Box>
  );
}

function RoundOverview({ logs, category, onCategoryChange, selectedLog }) {
  const { t } = useTranslation();
  const gameState = useGlobalStore((state) => state.gameState);
  const server = useGlobalStore((state) => state.serverState);
  const counts = useMemo(() => getCategoryCounts(logs), [logs]);
  const topPlayers = useMemo(() => getTopPlayers(logs), [logs]);
  const roundWindow = useMemo(() => getRoundWindow(logs), [logs]);
  const map = gameState?.current_map;
  const mapName =
    map?.pretty_name ||
    map?.map?.pretty_name ||
    t("records.gameLogs.timeline.unknownMap");
  const mode = formatMode(map?.game_mode, t);

  return (
    <Stack
      spacing={1}
      sx={{ position: { xl: "sticky" }, top: { xl: 12 }, alignSelf: "start" }}
    >
      <Box sx={sectionSx}>
        <Typography
          variant="subtitle2"
          sx={{
            px: 1.5,
            py: 1.25,
            color: "primary.main",
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          {t("records.gameLogs.timeline.roundOverview")}
        </Typography>
        <Box
          sx={{
            p: 1.5,
            display: "grid",
            gridTemplateColumns: "minmax(95px, .8fr) minmax(0, 1fr)",
            gap: 0.75,
          }}
        >
          {[
            [t("records.gameLogs.timeline.map"), mapName],
            [t("records.gameLogs.timeline.gameMode"), mode],
            [
              t("records.gameLogs.timeline.roundStart"),
              roundWindow.start
                ? roundWindow.start.format("DD.MM.YYYY HH:mm:ss")
                : "–",
            ],
            [
              t("records.gameLogs.timeline.roundEnd"),
              roundWindow.end
                ? roundWindow.end.format("DD.MM.YYYY HH:mm:ss")
                : "–",
            ],
            [
              t("records.gameLogs.server"),
              server?.short_name || server?.name || "–",
            ],
            [t("records.gameLogs.timeline.duration"), roundWindow.duration],
          ].map(([label, value]) => (
            <Box key={label} sx={{ display: "contents" }}>
              <Typography variant="caption" color="text.secondary">
                {label}
              </Typography>
              <Typography
                variant="caption"
                sx={{ color: "text.primary", overflowWrap: "anywhere" }}
              >
                {value}
              </Typography>
            </Box>
          ))}
        </Box>

        <Divider />
        <Typography
          variant="caption"
          sx={{
            display: "block",
            px: 1.5,
            pt: 1.25,
            pb: 0.5,
            color: "primary.main",
            fontWeight: 700,
            letterSpacing: "0.06em",
          }}
        >
          {t("records.gameLogs.timeline.eventsByType")}
        </Typography>
        <Stack sx={{ px: 1.5, pb: 1.25 }}>
          {[
            ["kills", t("records.gameLogs.timeline.categories.kills")],
            ["teamkills", t("records.gameLogs.timeline.categories.teamkills")],
            ["chat", t("records.gameLogs.timeline.categories.chat")],
            [
              "connections",
              t("records.gameLogs.timeline.categories.connections"),
            ],
            ["admin", t("records.gameLogs.timeline.categories.admin")],
            ["round", t("records.gameLogs.timeline.categories.round")],
          ].map(([id, label]) => (
            <Button
              key={id}
              color="inherit"
              onClick={() => onCategoryChange(category === id ? "all" : id)}
              sx={{
                minHeight: 30,
                px: 0,
                justifyContent: "space-between",
                borderRadius: 0,
                color: category === id ? "primary.main" : "text.secondary",
              }}
            >
              <Typography
                component="span"
                variant="caption"
                sx={{ fontWeight: 700 }}
              >
                {label}
              </Typography>
              <Typography
                component="span"
                variant="caption"
                sx={{
                  color: id === "teamkills" ? "error.main" : "text.primary",
                }}
              >
                {counts[id] || 0}
              </Typography>
            </Button>
          ))}
          <Stack
            direction="row"
            justifyContent="space-between"
            sx={{
              pt: 0.75,
              mt: 0.25,
              borderTop: "1px solid",
              borderColor: "divider",
            }}
          >
            <Typography variant="caption">
              {t("records.gameLogs.timeline.total")}
            </Typography>
            <Typography variant="caption">{counts.all}</Typography>
          </Stack>
        </Stack>

        <Divider />
        <Typography
          variant="caption"
          sx={{
            display: "block",
            px: 1.5,
            pt: 1.25,
            pb: 0.75,
            color: "primary.main",
            fontWeight: 700,
            letterSpacing: "0.06em",
          }}
        >
          {t("records.gameLogs.timeline.activity")}
        </Typography>
        <Stack spacing={0.5} sx={{ px: 1.5, pb: 1.5 }}>
          {topPlayers.length ? (
            topPlayers.map((player, index) => (
              <Stack
                key={player.name}
                direction="row"
                spacing={1}
                alignItems="center"
              >
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ width: 14 }}
                >
                  {index + 1}.
                </Typography>
                <Typography
                  variant="caption"
                  sx={{
                    flexGrow: 1,
                    overflow: "hidden",
                    textOverflow: "ellipsis",
                    whiteSpace: "nowrap",
                  }}
                >
                  {player.name}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {player.count}
                </Typography>
              </Stack>
            ))
          ) : (
            <Typography variant="caption" color="text.secondary">
              {t("records.gameLogs.timeline.noPlayerActivity")}
            </Typography>
          )}
        </Stack>
      </Box>

      <EventDetails log={selectedLog} />
    </Stack>
  );
}

function EventDetails({ log }) {
  const { t } = useTranslation();
  const { openWithId } = usePlayerSidebar();
  const [copied, setCopied] = useState(false);
  const category = log ? getEventCategory(log.type) : "other";

  useEffect(() => setCopied(false), [log?.id]);

  if (!log) {
    return (
      <Box sx={{ ...sectionSx, p: 2 }}>
        <Typography variant="subtitle2" color="primary.main">
          {t("records.gameLogs.timeline.selectedEvent")}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {t("records.gameLogs.timeline.selectEvent")}
        </Typography>
      </Box>
    );
  }

  const copyText = async () => {
    await navigator.clipboard.writeText(log.raw || log.content || "");
    setCopied(true);
  };

  return (
    <Box sx={sectionSx}>
      <Typography
        variant="subtitle2"
        sx={{
          px: 1.5,
          py: 1.25,
          color: "primary.main",
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        {t("records.gameLogs.timeline.selectedEvent")}
      </Typography>
      <Stack spacing={1.25} sx={{ p: 1.5 }}>
        <Stack
          direction="row"
          alignItems="center"
          spacing={1}
          sx={{ color: eventColor(category) }}
        >
          <EventIcon log={log} />
          <Typography variant="subtitle2">
            {getEventLabel(log.type, t)}
          </Typography>
        </Stack>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: "92px minmax(0, 1fr)",
            gap: 0.75,
          }}
        >
          {[
            [
              t("records.gameLogs.timeline.timestamp"),
              formatEventTime(log.event_time, "DD.MM.YYYY HH:mm:ss.SSS"),
            ],
            [t("records.gameLogs.timeline.attacker"), log.player1_name || "–"],
            [t("records.gameLogs.timeline.target"), log.player2_name || "–"],
            [t("records.gameLogs.timeline.weapon"), log.weapon || "–"],
            [t("records.gameLogs.server"), log.server || "–"],
          ].map(([label, value]) => (
            <Box key={label} sx={{ display: "contents" }}>
              <Typography variant="caption" color="text.secondary">
                {label}
              </Typography>
              <Typography variant="caption" sx={{ overflowWrap: "anywhere" }}>
                {value}
              </Typography>
            </Box>
          ))}
        </Box>
        {(log.player1_id || log.player2_id) && (
          <Box
            sx={{
              borderTop: "1px solid",
              borderBottom: "1px solid",
              borderColor: "divider",
              py: 1,
            }}
          >
            {[log.player1_id, log.player2_id].filter(Boolean).map((id) => (
              <Stack key={id} direction="row" alignItems="center" spacing={0.5}>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  sx={{ flexGrow: 1, overflowWrap: "anywhere" }}
                >
                  ID: {id}
                </Typography>
                <Tooltip title={t("records.gameLogs.timeline.copyId")}>
                  <IconButton
                    size="small"
                    onClick={() => navigator.clipboard.writeText(id)}
                    sx={{ borderRadius: 0 }}
                  >
                    <ContentCopyIcon sx={{ fontSize: 15 }} />
                  </IconButton>
                </Tooltip>
              </Stack>
            ))}
          </Box>
        )}
        <Box>
          <Typography variant="caption" color="text.secondary">
            {t("records.gameLogs.timeline.message")}
          </Typography>
          <Typography
            variant="body2"
            sx={{ mt: 0.5, overflowWrap: "anywhere" }}
          >
            {removePlayerIds(log.content)}
          </Typography>
        </Box>
        <Box>
          <Typography variant="caption" color="text.secondary">
            {t("records.gameLogs.timeline.rawLog")}
          </Typography>
          <Typography
            component="pre"
            variant="caption"
            sx={{
              m: 0,
              mt: 0.5,
              p: 1,
              bgcolor: "background.default",
              border: "1px solid",
              borderColor: "divider",
              whiteSpace: "pre-wrap",
              overflowWrap: "anywhere",
            }}
          >
            {log.raw || "–"}
          </Typography>
        </Box>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={0.75}>
          <Button
            variant="outlined"
            startIcon={<ContentCopyIcon />}
            onClick={copyText}
            fullWidth
          >
            {copied
              ? t("records.gameLogs.timeline.copied")
              : t("records.gameLogs.timeline.copy")}
          </Button>
          {log.player1_id && (
            <Button
              variant="outlined"
              startIcon={<PersonOutlineIcon />}
              onClick={() => openWithId(log.player1_id)}
              fullWidth
            >
              {t("records.gameLogs.timeline.profile")}
            </Button>
          )}
        </Stack>
      </Stack>
    </Box>
  );
}

function TimelinePagination({
  pageIndex,
  pageSize,
  total,
  onPageIndexChange,
  onPageSizeChange,
}) {
  const { t } = useTranslation();
  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const canPrevious = pageIndex > 0;
  const canNext = pageIndex < pageCount - 1;

  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      alignItems={{ xs: "stretch", sm: "center" }}
      spacing={1}
      sx={{ px: 1.5, py: 1 }}
    >
      <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1 }}>
        {t("records.gameLogs.timeline.loadedCount", {
          shown: Math.min(total, (pageIndex + 1) * pageSize),
          total,
        })}
      </Typography>
      <Stack
        direction="row"
        alignItems="center"
        justifyContent="flex-end"
        spacing={0.25}
      >
        <IconButton
          size="small"
          disabled={!canPrevious}
          onClick={() => onPageIndexChange(0)}
          sx={{ borderRadius: 0 }}
          aria-label={t("common.pagination.first")}
        >
          <KeyboardDoubleArrowLeftIcon />
        </IconButton>
        <IconButton
          size="small"
          disabled={!canPrevious}
          onClick={() => onPageIndexChange(pageIndex - 1)}
          sx={{ borderRadius: 0 }}
          aria-label={t("common.pagination.previous")}
        >
          <KeyboardArrowLeftIcon />
        </IconButton>
        <Typography variant="caption" sx={{ px: 0.75, whiteSpace: "nowrap" }}>
          {t("common.pagination.page", {
            current: pageIndex + 1,
            total: pageCount,
          })}
        </Typography>
        <IconButton
          size="small"
          disabled={!canNext}
          onClick={() => onPageIndexChange(pageIndex + 1)}
          sx={{ borderRadius: 0 }}
          aria-label={t("common.pagination.next")}
        >
          <KeyboardArrowRightIcon />
        </IconButton>
        <IconButton
          size="small"
          disabled={!canNext}
          onClick={() => onPageIndexChange(pageCount - 1)}
          sx={{ borderRadius: 0 }}
          aria-label={t("common.pagination.last")}
        >
          <KeyboardDoubleArrowRightIcon />
        </IconButton>
        <FormControl size="small" sx={{ minWidth: 112, ml: 0.5 }}>
          <InputLabel id="game-log-page-size-label">
            {t("records.gameLogs.timeline.perPage")}
          </InputLabel>
          <Select
            labelId="game-log-page-size-label"
            value={pageSize}
            label={t("records.gameLogs.timeline.perPage")}
            onChange={(event) => onPageSizeChange(Number(event.target.value))}
            sx={{ borderRadius: 0 }}
          >
            {[50, 100, 250, 500].map((size) => (
              <MenuItem key={size} value={size}>
                {size}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
      </Stack>
    </Stack>
  );
}

export default function GameLogsTimeline({
  logs,
  allLogs,
  category,
  onCategoryChange,
}) {
  const { t } = useTranslation();
  const gameState = useGlobalStore((state) => state.gameState);
  const [selectedLog, setSelectedLog] = useState(
    logs.find((log) => getEventCategory(log.type) === "teamkills") ||
      logs[0] ||
      null
  );
  const [pageIndex, setPageIndex] = useState(0);
  const [pageSize, setPageSize] = useState(100);

  useEffect(() => {
    setPageIndex(0);
    setSelectedLog(
      logs.find((log) => getEventCategory(log.type) === "teamkills") ||
        logs[0] ||
        null
    );
  }, [logs]);

  const visibleLogs = useMemo(
    () => logs.slice(pageIndex * pageSize, pageIndex * pageSize + pageSize),
    [logs, pageIndex, pageSize]
  );
  const map = gameState?.current_map;
  const mapName =
    map?.pretty_name ||
    map?.map?.pretty_name ||
    t("records.gameLogs.timeline.unknownMap");
  const mode = formatMode(map?.game_mode, t);
  const roundWindow = getRoundWindow(logs);

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: "minmax(0, 1fr)",
        "@media (min-width: 1440px)": {
          gridTemplateColumns: "minmax(0, 1fr) 320px",
        },
        gap: 1,
        alignItems: "start",
      }}
    >
      <Box sx={sectionSx}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ xs: "flex-start", sm: "center" }}
          spacing={1}
          sx={{
            px: 1.5,
            py: 1.25,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography
            variant="subtitle2"
            sx={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
          >
            {t("records.gameLogs.timeline.roundHeading", {
              map: mapName,
              mode,
            })}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ fontVariantNumeric: "tabular-nums" }}
          >
            {roundWindow.start && roundWindow.end
              ? `${roundWindow.start.format("HH:mm")}–${roundWindow.end.format(
                  "HH:mm"
                )}`
              : "–"}
          </Typography>
          <Box sx={{ flexGrow: 1 }} />
          <Typography variant="caption" color="text.secondary">
            {t("records.gameLogs.timeline.eventsInSelection", {
              count: logs.length,
            })}
          </Typography>
        </Stack>

        {visibleLogs.length ? (
          <Box>
            {visibleLogs.map((log) => (
              <TimelineRow
                key={log.id || `${log.event_time}-${log.raw}`}
                log={log}
                selected={
                  (selectedLog?.id || selectedLog?.raw) === (log.id || log.raw)
                }
                onSelect={setSelectedLog}
              />
            ))}
          </Box>
        ) : (
          <Stack
            alignItems="center"
            spacing={1}
            sx={{ px: 2, py: 8, textAlign: "center" }}
          >
            <DescriptionOutlinedIcon color="disabled" />
            <Typography variant="subtitle2">
              {t("records.gameLogs.timeline.noEvents")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("records.gameLogs.timeline.adjustFilters")}
            </Typography>
            {category !== "all" && (
              <Button
                variant="outlined"
                onClick={() => onCategoryChange("all")}
              >
                {t("records.gameLogs.timeline.showAll")}
              </Button>
            )}
          </Stack>
        )}

        <TimelinePagination
          pageIndex={pageIndex}
          pageSize={pageSize}
          total={logs.length}
          onPageIndexChange={setPageIndex}
          onPageSizeChange={(value) => {
            setPageSize(value);
            setPageIndex(0);
          }}
        />
      </Box>

      <RoundOverview
        logs={allLogs}
        category={category}
        onCategoryChange={onCategoryChange}
        selectedLog={selectedLog}
      />
    </Box>
  );
}
