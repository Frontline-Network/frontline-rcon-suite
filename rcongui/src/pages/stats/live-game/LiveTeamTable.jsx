import {
  Box,
  Checkbox,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import WarningAmberIcon from "@mui/icons-material/WarningAmber";
import KeyboardArrowLeftIcon from "@mui/icons-material/KeyboardArrowLeft";
import KeyboardArrowRightIcon from "@mui/icons-material/KeyboardArrowRight";
import { getColoredFactionIconSrc } from "@/utils/lib";
import { formatMatchDuration, getTeamSummary } from "./live-game-utils";

const GRID_TEMPLATE = "34px minmax(112px, 1fr) 34px 34px 50px 38px 56px";

const MetricHeader = ({ label, title, align = "right" }) => (
  <Tooltip title={title} placement="top">
    <Typography
      component="span"
      sx={{
        minWidth: 0,
        textAlign: align,
        color: "text.secondary",
        fontSize: "0.66rem",
        fontWeight: 700,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}
    >
      {label}
    </Typography>
  </Tooltip>
);

const TeamMetric = ({ label, value, tone }) => (
  <Stack direction="row" gap={0.45} alignItems="baseline">
    <Typography
      component="span"
      sx={{
        color: "text.disabled",
        fontSize: "0.64rem",
        letterSpacing: "0.06em",
        textTransform: "uppercase",
      }}
    >
      {label}
    </Typography>
    <Typography
      component="span"
      sx={{
        color: tone ?? "text.primary",
        fontSize: "0.74rem",
        fontWeight: 600,
        fontVariantNumeric: "tabular-nums",
      }}
    >
      {value}
    </Typography>
  </Stack>
);

export default function LiveTeamTable({
  team,
  label,
  players,
  selectedPlayerId,
  checkedIds,
  onPlayerSelect,
  onPlayerCheck,
  onTeamCheck,
  page,
  pageSize,
  onPageChange,
  t,
}) {
  const summary = getTeamSummary(players);
  const accent = team === "allies" ? "info.main" : "error.main";
  const checkedCount = players.filter((player) => checkedIds.has(player.player_id)).length;
  const allChecked = players.length > 0 && checkedCount === players.length;
  const partiallyChecked = checkedCount > 0 && !allChecked;
  const pageCount = Math.max(1, Math.ceil(players.length / pageSize));
  const safePage = Math.min(page, pageCount - 1);
  const visiblePlayers = players.slice(safePage * pageSize, (safePage + 1) * pageSize);
  const rangeStart = players.length ? safePage * pageSize + 1 : 0;
  const rangeEnd = Math.min((safePage + 1) * pageSize, players.length);

  return (
    <Box data-theme-surface="panel"
      component="section"
      className="wardogs-live-team-table"
      aria-label={label}
      sx={{
        minWidth: 0,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          px: 1.25,
          py: 1,
          borderTop: "2px solid",
          borderTopColor: accent,
          borderBottom: "1px solid",
          borderBottomColor: "divider",
        }}
      >
        <Stack direction="row" alignItems="center" justifyContent="space-between" gap={1}>
          <Stack direction="row" alignItems="center" gap={0.85} minWidth={0}>
            <Box
              component="img"
              src={getColoredFactionIconSrc(team)}
              alt=""
              width={22}
              height={22}
              sx={{ objectFit: "contain", flexShrink: 0 }}
            />
            <Box minWidth={0}>
              <Typography
                component="h2"
                sx={{
                  color: accent,
                  fontSize: "0.92rem",
                  fontWeight: 700,
                  letterSpacing: "0.055em",
                  lineHeight: 1.1,
                  textTransform: "uppercase",
                }}
              >
                {label}
              </Typography>
              <Typography
                sx={{
                  mt: 0.25,
                  color: "text.secondary",
                  fontSize: "0.67rem",
                  fontVariantNumeric: "tabular-nums",
                }}
              >
                {t("stats.liveGame.playerCount", { count: players.length })}
              </Typography>
            </Box>
          </Stack>
          <Stack direction="row" gap={{ xs: 0.75, sm: 1.1 }} flexWrap="wrap" justifyContent="flex-end">
            <TeamMetric label={t("stats.liveGame.killsShort")} value={summary.kills} />
            <TeamMetric label="K/D" value={summary.kdr.toFixed(2)} />
            <TeamMetric
              label="TK"
              value={summary.teamkills}
              tone={summary.teamkills > 0 ? "warning.main" : undefined}
            />
          </Stack>
        </Stack>
      </Box>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: GRID_TEMPLATE,
          alignItems: "center",
          minHeight: 34,
          px: 0.55,
          columnGap: 0.35,
          borderBottom: "1px solid",
          borderColor: "divider",
          bgcolor: "rgba(255,255,255,0.018)",
        }}
      >
        <Checkbox
          size="small"
          checked={allChecked}
          indeterminate={partiallyChecked}
          onChange={(event) => onTeamCheck(players, event.target.checked)}
          inputProps={{ "aria-label": t("stats.liveGame.selectTeam", { team: label }) }}
          sx={{ p: 0.5, borderRadius: 0 }}
        />
        <MetricHeader label={t("stats.liveGame.player")} title={t("stats.liveGame.player")} align="left" />
        <MetricHeader label="K" title={t("stats.gameDetails.metrics.kills")} />
        <MetricHeader label={t("liveViews.deathsShort")} title={t("stats.gameDetails.deaths")} />
        <MetricHeader label="K/D" title={t("stats.liveGame.kdr")} />
        <MetricHeader label="TK" title={t("stats.gameDetails.teamKills")} />
        <MetricHeader label={t("stats.liveGame.timeShort")} title={t("stats.gameDetails.duration")} />
      </Box>

      <Box role="rowgroup">
        {players.length === 0 ? (
          <Stack alignItems="center" justifyContent="center" sx={{ minHeight: 164, px: 2 }}>
            <Typography color="text.secondary" sx={{ textAlign: "center", fontSize: "0.8rem" }}>
              {t("stats.liveGame.noPlayers")}
            </Typography>
          </Stack>
        ) : (
          visiblePlayers.map((player) => {
            const inspected = player.player_id === selectedPlayerId;
            const checked = checkedIds.has(player.player_id);
            const online = player.status === "online";
            const idle = player.status === "idle";
            const offline = player.status === "offline";

            return (
              <Box
                key={player.player_id}
                role="row"
                tabIndex={0}
                data-inspected={String(inspected)}
                onClick={() => onPlayerSelect(player)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" || event.key === " ") {
                    event.preventDefault();
                    onPlayerSelect(player);
                  }
                }}
                sx={{
                  position: "relative",
                  display: "grid",
                  gridTemplateColumns: GRID_TEMPLATE,
                  alignItems: "center",
                  minHeight: { xs: 44, sm: 34 },
                  px: 0.55,
                  columnGap: 0.35,
                  borderBottom: "1px solid",
                  borderColor: "divider",
                  cursor: "pointer",
                  outline: 0,
                  bgcolor: inspected ? "action.selected" : "transparent",
                  "&::before": inspected
                    ? {
                        content: '\"\"',
                        position: "absolute",
                        inset: "0 auto 0 0",
                        width: 2,
                        bgcolor: "primary.main",
                      }
                    : undefined,
                  "&:hover": { bgcolor: inspected ? "action.selected" : "action.hover" },
                  "&:focus-visible": {
                    boxShadow: (theme) => `inset 0 0 0 2px ${theme.palette.primary.main}`,
                  },
                  "&:last-of-type": { borderBottom: 0 },
                }}
              >
                <Checkbox
                  size="small"
                  checked={checked}
                  onClick={(event) => event.stopPropagation()}
                  onChange={(event) => onPlayerCheck(player, event.target.checked)}
                  inputProps={{
                    "aria-label": t("stats.liveGame.selectPlayer", { player: player.player }),
                  }}
                  sx={{ p: 0.5, borderRadius: 0 }}
                />
                <Stack direction="row" alignItems="center" gap={0.65} minWidth={0}>
                  <Tooltip
                    title={
                      online
                        ? t("stats.liveGame.statusOnline")
                        : idle
                          ? t("stats.liveGame.statusIdle")
                          : offline
                            ? t("stats.liveGame.statusOffline")
                            : t("stats.liveGame.statusUnknown")
                    }
                  >
                    <Box
                      component="span"
                      sx={{
                        width: 6,
                        height: 6,
                        flexShrink: 0,
                        bgcolor: online ? "success.main" : idle ? "warning.main" : offline ? "text.disabled" : "text.secondary",
                      }}
                    />
                  </Tooltip>
                  <Tooltip title={player.player} enterDelay={450}>
                    <Typography
                      component="span"
                      sx={{
                        minWidth: 0,
                        overflow: "hidden",
                        textOverflow: "ellipsis",
                        whiteSpace: "nowrap",
                        color: "text.primary",
                        fontSize: "0.75rem",
                        fontWeight: inspected ? 600 : 400,
                      }}
                    >
                      {player.player}
                    </Typography>
                  </Tooltip>
                </Stack>
                <Typography sx={numericCell}>{player.kills}</Typography>
                <Typography sx={numericCell}>{player.deaths}</Typography>
                <Typography sx={{ ...numericCell, color: player.kill_death_ratio >= 2 ? "success.main" : "text.primary" }}>
                  {player.kill_death_ratio.toFixed(2)}
                </Typography>
                <Tooltip title={player.teamkills > 0 ? t("stats.liveGame.teamkillWarning") : ""}>
                  <Stack direction="row" alignItems="center" justifyContent="flex-end" gap={0.25}>
                    {player.teamkills > 0 && <WarningAmberIcon sx={{ fontSize: 12, color: "warning.main" }} />}
                    <Typography sx={{ ...numericCell, color: player.teamkills > 0 ? "warning.main" : "text.secondary" }}>
                      {player.teamkills}
                    </Typography>
                  </Stack>
                </Tooltip>
                <Typography sx={numericCell}>{formatMatchDuration(player.time_seconds, false)}</Typography>
              </Box>
            );
          })
        )}
      </Box>

      <Stack
        direction="row"
        alignItems="center"
        justifyContent="space-between"
        gap={1}
        sx={{ minHeight: 44, px: 1, py: 0.6, borderTop: "1px solid", borderColor: "divider" }}
      >
        <Typography sx={{ color: "text.secondary", fontSize: "0.65rem", fontVariantNumeric: "tabular-nums" }}>
          {t("stats.liveGame.range", { from: rangeStart, to: rangeEnd, total: players.length })}
        </Typography>
        <Stack direction="row" alignItems="center" gap={0.35}>
          <IconButton
            size="small"
            disabled={safePage <= 0}
            onClick={() => onPageChange(Math.max(0, safePage - 1))}
            aria-label={t("common.pagination.previous")}
            sx={{ border: "1px solid", borderColor: "divider", borderRadius: 0 }}
          >
            <KeyboardArrowLeftIcon sx={{ fontSize: 16 }} />
          </IconButton>
          <Typography sx={{ minWidth: 36, textAlign: "center", fontSize: "0.65rem", fontVariantNumeric: "tabular-nums" }}>
            {safePage + 1}/{pageCount}
          </Typography>
          <IconButton
            size="small"
            disabled={safePage >= pageCount - 1}
            onClick={() => onPageChange(Math.min(pageCount - 1, safePage + 1))}
            aria-label={t("common.pagination.next")}
            sx={{ border: "1px solid", borderColor: "divider", borderRadius: 0 }}
          >
            <KeyboardArrowRightIcon sx={{ fontSize: 16 }} />
          </IconButton>
        </Stack>
      </Stack>
    </Box>
  );
}

const numericCell = {
  minWidth: 0,
  textAlign: "right",
  color: "text.secondary",
  fontSize: "0.72rem",
  fontWeight: 400,
  fontVariantNumeric: "tabular-nums",
  whiteSpace: "nowrap",
};
