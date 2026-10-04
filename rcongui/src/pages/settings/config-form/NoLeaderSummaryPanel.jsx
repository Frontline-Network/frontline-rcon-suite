import { Box, Stack, Typography } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import SearchOutlinedIcon from "@mui/icons-material/SearchOutlined";
import { useTranslation } from "react-i18next";

const formatStage = (count, interval, t, root) => {
  if (Number(count) === 0) return t(`${root}.summary.skipped`);
  if (Number(count) === -1) {
    return t(`${root}.summary.unlimited`, { interval: interval ?? 0 });
  }
  return t(`${root}.summary.count`, {
    count: count ?? 0,
    interval: interval ?? 0,
  });
};

function OverviewSegment({ icon, eyebrow, children, detail, border = true }) {
  return (
    <Box
      component="section"
      sx={{
        minWidth: 0,
        px: { xs: 1.75, sm: 2.25, lg: 2.75 },
        py: { xs: 1.75, md: 2.1 },
        borderRight: { xs: 0, md: border ? "1px solid" : 0 },
        borderBottom: { xs: border ? "1px solid" : 0, md: 0 },
        borderColor: "divider",
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Box
          aria-hidden="true"
          sx={{ color: "primary.main", display: "flex", mt: 0.15 }}
        >
          {icon}
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mb: 0.35, letterSpacing: "0.05em" }}
          >
            {eyebrow}
          </Typography>
          {children}
          {detail}
        </Box>
      </Stack>
    </Box>
  );
}

function ReactionStage({ label, value, active = true }) {
  return (
    <Box component="li" sx={{ minWidth: 0, flex: "1 1 0", listStyle: "none" }}>
      <Typography
        variant="body2"
        sx={{
          color: active ? "text.primary" : "text.disabled",
          fontWeight: 750,
        }}
      >
        {label}
      </Typography>
      <Typography
        variant="caption"
        color={active ? "text.secondary" : "text.disabled"}
        sx={{ display: "block", mt: 0.2 }}
      >
        {value}
      </Typography>
    </Box>
  );
}

export default function NoLeaderSummaryPanel({
  data = {},
  translationRoot = "settings.configForms.noLeader",
}) {
  const { t } = useTranslation();
  const root = `${translationRoot}.workbench`;
  const minimum = Math.max(
    0,
    Number(data.dont_do_anything_below_this_number_of_players) || 0
  );
  const checks = Math.max(0, Number(data.number_of_notes) || 0);
  const warningActive = Number(data.number_of_warnings) !== 0;
  const punishActive = Number(data.number_of_punishments) !== 0;
  const kickActive = Boolean(data.kick_after_max_punish);
  const kickReachable =
    kickActive &&
    Number(data.number_of_warnings) !== -1 &&
    Number(data.number_of_punishments) > 0;
  const exceptionCount =
    (data.immune_roles?.length || 0) +
    (data.whitelist_flags?.length || 0) +
    (Number(data.immune_player_level) > 0 ? 1 : 0);
  const operationNotice = data.enabled
    ? data.dry_run
      ? t(`${root}.summary.testNotice`)
      : t(`${root}.summary.activeNotice`)
    : t(`${root}.summary.inactiveNotice`);

  return (
    <Box data-theme-surface="panel"
      component="aside"
      aria-label={t(`${root}.summary.title`)}
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 0,
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "0.82fr 1fr 1.55fr" },
        }}
      >
        <OverviewSegment
          icon={<PlayArrowOutlinedIcon fontSize="small" />}
          eyebrow={t(`${root}.summary.startCondition`)}
          detail={
            <Typography
              variant="caption"
              color={
                data.enabled && !data.dry_run
                  ? "success.main"
                  : "text.secondary"
              }
              sx={{ display: "block", mt: 0.65, maxWidth: 300 }}
            >
              {operationNotice}
            </Typography>
          }
        >
          <Typography variant="h5" component="p" sx={{ lineHeight: 1.15 }}>
            {minimum === 0
              ? t(`${root}.summary.immediate`)
              : t(`${root}.summary.fromPlayers`, { count: minimum })}
          </Typography>
        </OverviewSegment>

        <OverviewSegment
          icon={<SearchOutlinedIcon fontSize="small" />}
          eyebrow={t(`${root}.summary.detection`)}
          detail={
            <Stack spacing={0.45} sx={{ mt: 0.65 }}>
              <Stack direction="row" spacing={0.65} alignItems="center">
                <CheckCircleOutlineIcon
                  sx={{ fontSize: 15, color: "primary.main" }}
                />
                <Typography variant="caption" color="text.secondary">
                  {t(`${root}.summary.checks`, {
                    count: checks,
                    interval: data.notes_interval_seconds ?? 0,
                  })}
                </Typography>
              </Stack>
              <Stack direction="row" spacing={0.65} alignItems="center">
                <Groups2OutlinedIcon
                  sx={{ fontSize: 15, color: "primary.main" }}
                />
                <Typography variant="caption" color="text.secondary">
                  {t(`${root}.summary.exceptions`, { count: exceptionCount })}
                </Typography>
              </Stack>
            </Stack>
          }
        >
          <Typography variant="subtitle1" component="p">
            {checks === 0
              ? t(`${root}.summary.noConfirmation`)
              : t(`${root}.summary.confirmedViolation`)}
          </Typography>
        </OverviewSegment>

        <OverviewSegment
          icon={<GavelOutlinedIcon fontSize="small" />}
          eyebrow={t(`${root}.summary.reaction`)}
          border={false}
        >
          <Stack
            component="ol"
            direction={{ xs: "column", sm: "row" }}
            spacing={{ xs: 0.8, sm: 1 }}
            alignItems={{ xs: "stretch", sm: "center" }}
            sx={{ p: 0, m: 0 }}
          >
            <ReactionStage
              label={t(`${root}.summary.warn`)}
              value={formatStage(
                data.number_of_warnings,
                data.warning_interval_seconds,
                t,
                root
              )}
              active={warningActive}
            />
            <ChevronRightIcon
              aria-hidden="true"
              sx={{
                color: "primary.main",
                fontSize: 18,
                flex: "0 0 auto",
                transform: { xs: "rotate(90deg)", sm: "none" },
              }}
            />
            <ReactionStage
              label={t(`${root}.summary.punish`)}
              value={formatStage(
                data.number_of_punishments,
                data.punish_interval_seconds,
                t,
                root
              )}
              active={punishActive}
            />
            <ChevronRightIcon
              aria-hidden="true"
              sx={{
                color: "primary.main",
                fontSize: 18,
                flex: "0 0 auto",
                transform: { xs: "rotate(90deg)", sm: "none" },
              }}
            />
            <ReactionStage
              label={t(`${root}.summary.kick`)}
              value={
                kickReachable
                  ? t(`${root}.summary.kickAfter`, {
                      seconds: data.kick_grace_period_seconds ?? 0,
                    })
                  : kickActive
                  ? t(`${root}.summary.unreachable`)
                  : t(`${root}.summary.skipped`)
              }
              active={kickReachable}
            />
          </Stack>
        </OverviewSegment>
      </Box>
    </Box>
  );
}
