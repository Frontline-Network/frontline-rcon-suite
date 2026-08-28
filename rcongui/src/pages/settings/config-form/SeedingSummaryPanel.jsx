import { Box, Stack, Typography } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ChevronRightIcon from "@mui/icons-material/ChevronRight";
import FlagOutlinedIcon from "@mui/icons-material/FlagOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import Groups2OutlinedIcon from "@mui/icons-material/Groups2Outlined";
import PlayArrowOutlinedIcon from "@mui/icons-material/PlayArrowOutlined";
import SportsEsportsOutlinedIcon from "@mui/icons-material/SportsEsportsOutlined";
import { useTranslation } from "react-i18next";

const ROOT = "settings.configForms.seedingWorkbench";

const mapSize = (value, child) => {
  if (Array.isArray(value)) return value.length;
  if (!value || typeof value !== "object") return 0;
  const nested = child ? value[child] : value;
  return nested && typeof nested === "object" ? Object.keys(nested).length : 0;
};

const ruleActive = (value, child) => {
  if (typeof value === "boolean") return value;
  if (!value || typeof value !== "object") return false;
  if (child && mapSize(value, child) === 0) return false;
  return Number(value.max_players) > 0;
};

const finiteNumber = (...values) => {
  const value = values.find(
    (candidate) =>
      candidate !== null &&
      candidate !== undefined &&
      candidate !== "" &&
      Number.isFinite(Number(candidate))
  );
  return value === undefined ? 0 : Number(value);
};

const formatStage = (count, interval, t) => {
  if (Number(count) === 0) return t(`${ROOT}.status.skipped`);
  if (Number(count) === -1) return t(`${ROOT}.summary.unlimited`, { interval });
  return t(`${ROOT}.summary.count`, {
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
        borderRight: {
          xs: 0,
          md: border ? "1px solid" : 0,
        },
        borderBottom: {
          xs: border ? "1px solid" : 0,
          md: 0,
        },
        borderColor: "divider",
      }}
    >
      <Stack direction="row" spacing={1.5} alignItems="flex-start">
        <Box
          aria-hidden="true"
          sx={{
            color: "primary.main",
            display: "flex",
            flex: "0 0 auto",
            mt: 0.15,
          }}
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

function RuleState({ icon, label, active }) {
  return (
    <Stack
      component="li"
      direction="row"
      spacing={0.55}
      alignItems="center"
      sx={{
        minWidth: 0,
        color: active ? "text.primary" : "text.disabled",
        listStyle: "none",
      }}
    >
      <Box
        aria-hidden="true"
        sx={{
          color: active ? "primary.main" : "text.disabled",
          display: "flex",
        }}
      >
        {icon}
      </Box>
      <Typography variant="caption" color="inherit" noWrap>
        {label}
      </Typography>
    </Stack>
  );
}

function ReactionStage({ label, value, active }) {
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

export default function SeedingSummaryPanel({ data = {} }) {
  const { t } = useTranslation();
  const rolesActive =
    ruleActive(data.disallowed_roles, "roles") ||
    (Array.isArray(data.disallowed_roles) && data.disallowed_roles.length > 0);
  const weaponsActive =
    ruleActive(data.disallowed_weapons, "weapons") ||
    (Array.isArray(data.disallowed_weapons) &&
      data.disallowed_weapons.length > 0);
  const capActive = ruleActive(data.enforce_cap_fight);
  const activeRules = [rolesActive, weaponsActive, capActive].filter(
    Boolean
  ).length;

  const globalMinimum = finiteNumber(
    data.dont_do_anything_below_this_number_of_players,
    data.min_players,
    data.disallowed_roles?.min_players,
    data.disallowed_weapons?.min_players,
    data.enforce_cap_fight?.min_players
  );

  const warningActive = Number(data.number_of_warnings) !== 0;
  const punishActive = Number(data.number_of_punishments) !== 0;
  const kickActive = Boolean(data.kick_after_max_punish);
  const operationNotice = data.enabled
    ? data.dry_run
      ? t(`${ROOT}.summary.testNotice`)
      : t(`${ROOT}.summary.activeNotice`)
    : t(`${ROOT}.summary.inactiveNotice`);

  return (
    <Box
      component="aside"
      aria-label={t(`${ROOT}.summary.title`)}
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
          eyebrow={t(`${ROOT}.fields.globalMinimum`)}
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
            {globalMinimum} {t(`${ROOT}.players`)}
          </Typography>
        </OverviewSegment>

        <OverviewSegment
          icon={<CheckCircleOutlineIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.summary.title`)}
          detail={
            <Stack
              component="ul"
              direction="row"
              spacing={1.15}
              useFlexGap
              flexWrap="wrap"
              aria-label={t(`${ROOT}.summary.activeRules`, {
                count: activeRules,
              })}
              sx={{ p: 0, m: 0, mt: 0.7 }}
            >
              <RuleState
                icon={<Groups2OutlinedIcon sx={{ fontSize: 15 }} />}
                label={t(`${ROOT}.rules.roles.title`)}
                active={rolesActive}
              />
              <RuleState
                icon={<SportsEsportsOutlinedIcon sx={{ fontSize: 15 }} />}
                label={t(`${ROOT}.rules.weapons.title`)}
                active={weaponsActive}
              />
              <RuleState
                icon={<FlagOutlinedIcon sx={{ fontSize: 15 }} />}
                label={t(`${ROOT}.rules.cap.title`)}
                active={capActive}
              />
            </Stack>
          }
        >
          <Typography variant="subtitle1" component="p">
            {t(`${ROOT}.summary.activeRules`, { count: activeRules })}
          </Typography>
        </OverviewSegment>

        <OverviewSegment
          icon={<GavelOutlinedIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.summary.reaction`)}
          border={false}
        >
          <Stack
            component="ol"
            direction={{ xs: "column", sm: "row" }}
            spacing={{ xs: 0.8, sm: 1 }}
            alignItems={{ xs: "stretch", sm: "center" }}
            aria-label={t(`${ROOT}.summary.reaction`)}
            sx={{ p: 0, m: 0 }}
          >
            <ReactionStage
              label={t(`${ROOT}.actions.warning.title`)}
              value={formatStage(
                data.number_of_warnings,
                data.warning_interval_seconds,
                t
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
              label={t(`${ROOT}.actions.punish.title`)}
              value={formatStage(
                data.number_of_punishments,
                data.punish_interval_seconds,
                t
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
              label={t(`${ROOT}.actions.kick.title`)}
              value={
                kickActive
                  ? t(`${ROOT}.summary.kick`, {
                      seconds: data.kick_grace_period_seconds ?? 0,
                    })
                  : t(`${ROOT}.status.skipped`)
              }
              active={kickActive}
            />
          </Stack>
        </OverviewSegment>
      </Box>
    </Box>
  );
}
