import { Box, Stack, Typography } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import HistoryOutlinedIcon from "@mui/icons-material/HistoryOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import RedeemOutlinedIcon from "@mui/icons-material/RedeemOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import { useTranslation } from "react-i18next";

const durationParts = (duration, t) => {
  const units = ["years", "weeks", "days", "hours", "minutes"];
  const parts = units
    .filter((unit) => Number(duration?.[unit]) > 0)
    .map((unit) =>
      t(`settings.configForms.workbench.profileSummary.duration.${unit}`, {
        count: duration[unit],
      })
    );
  return (
    parts.join(" · ") ||
    t("settings.configForms.workbench.profileSummary.noDuration")
  );
};

const compactTimeParts = (duration) =>
  ["hours", "minutes", "seconds"]
    .map((unit) => Number(duration?.[unit]) || 0)
    .reduce((total, value, index) => total + value * [3600, 60, 1][index], 0);

const levelItems = (data, t) => [
  {
    icon: RuleOutlinedIcon,
    label: t("settings.configForms.level.sections.rules.title"),
    value: t("settings.configForms.level.summary.levelRange", {
      min: data?.min_level ?? 0,
      max: data?.max_level ?? "–",
    }),
  },
  {
    icon: HistoryOutlinedIcon,
    label: t("settings.configForms.level.sections.warnings.title"),
    value: t("settings.configForms.workbench.profileSummary.count", {
      count: data?.number_of_warnings ?? 0,
      interval: data?.warning_interval_seconds ?? 0,
    }),
  },
  {
    icon: GavelOutlinedIcon,
    label: t("settings.configForms.level.sections.punishments.title"),
    value: t("settings.configForms.workbench.profileSummary.count", {
      count: data?.number_of_punishments ?? 0,
      interval: data?.punish_interval_seconds ?? 0,
    }),
  },
  {
    icon: CheckCircleOutlineIcon,
    label: t("settings.configForms.level.sections.kick.title"),
    value: data?.kick_after_max_punish
      ? t("settings.configForms.workbench.profileSummary.kick", {
          seconds: data?.kick_grace_period_seconds ?? 0,
        })
      : t("settings.configForms.workbench.profileSummary.disabled"),
  },
];

const vacItems = (data, t) => [
  {
    icon: HistoryOutlinedIcon,
    label: t("settings.configForms.vacBans.sections.rules.title"),
    value: t("settings.configForms.vacBans.summary.history", {
      days: data?.vac_history_days ?? 0,
      count: data?.game_ban_threshhold ?? 0,
    }),
  },
  {
    icon: GavelOutlinedIcon,
    label: t("settings.configForms.vacBans.sections.actions.title"),
    value: t("settings.configForms.vacBans.summary.action", {
      id: data?.blacklist_id ?? "–",
      expiry: t(
        data?.auto_expire
          ? "settings.configForms.vacBans.summary.expiring"
          : "settings.configForms.vacBans.summary.permanent"
      ),
    }),
  },
  {
    icon: ShieldOutlinedIcon,
    label: t("settings.configForms.vacBans.sections.exemptions.title"),
    value: t("settings.configForms.vacBans.summary.flags", {
      count: data?.whitelist_flags?.length ?? 0,
    }),
  },
];

const tkItems = (data, t) => [
  {
    icon: HistoryOutlinedIcon,
    label: t("settings.configForms.tkBans.sections.detection.title"),
    value: t("settings.configForms.tkBans.summary.detection", {
      minutes: data?.max_time_after_connect_minutes ?? 0,
      count: data?.teamkill_tolerance_count ?? 0,
    }),
  },
  {
    icon: GavelOutlinedIcon,
    label: t("settings.configForms.tkBans.sections.actions.title"),
    value: t("settings.configForms.tkBans.summary.action", {
      id: data?.blacklist_id ?? "–",
      duration: durationParts(data?.ban_duration, t),
    }),
  },
  {
    icon: ShieldOutlinedIcon,
    label: t("settings.configForms.tkBans.sections.exemptions.title"),
    value: t("settings.configForms.tkBans.summary.exemptions", {
      weapons: data?.excluded_weapons?.length ?? 0,
      flags:
        data?.whitelist_players?.has_flag?.length ??
        data?.whitelist_players?.flags?.length ??
        0,
    }),
  },
  {
    icon: NotificationsNoneOutlinedIcon,
    label: t("settings.configForms.tkBans.sections.notifications.title"),
    value: t(
      data?.discord_webhook_url
        ? "settings.configForms.workbench.profileSummary.notificationsActive"
        : "settings.configForms.workbench.profileSummary.notificationsInactive"
    ),
  },
];

const seedVipItems = (data, t) => {
  const allies = data?.requirements?.max_allies ?? 0;
  const axis = data?.requirements?.max_axis ?? 0;
  return [
    {
      icon: CheckCircleOutlineIcon,
      label: t("settings.configForms.seedVip.summary.targetLabel"),
      value: t(
        allies === axis
          ? "settings.configForms.seedVip.summary.targetEqual"
          : "settings.configForms.seedVip.summary.target",
        { count: allies, allies, axis }
      ),
    },
    {
      icon: ScheduleOutlinedIcon,
      label: t("settings.configForms.seedVip.summary.qualificationLabel"),
      value: t("settings.configForms.seedVip.summary.qualification", {
        minutes: Math.ceil(
          compactTimeParts(data?.requirements?.minimum_play_time) / 60
        ),
      }),
    },
    {
      icon: RedeemOutlinedIcon,
      label: t("settings.configForms.seedVip.sections.reward.title"),
      value: t("settings.configForms.seedVip.summary.reward", {
        duration: durationParts(data?.reward?.timeframe, t),
        mode: t(
          data?.reward?.cumulative
            ? "settings.configForms.seedVip.summary.cumulative"
            : "settings.configForms.seedVip.summary.replace"
        ),
      }),
    },
  ];
};

const expiredVipItems = (data, t) => [
  {
    icon: ScheduleOutlinedIcon,
    label: t("settings.configForms.expiredVip.sections.schedule.title"),
    value: t("settings.configForms.workbench.profileSummary.intervalMinutes", {
      count: data?.interval_minutes ?? 0,
    }),
  },
  {
    icon: NotificationsNoneOutlinedIcon,
    label: t("settings.configForms.expiredVip.sections.notifications.title"),
    value: t(
      data?.discord_webhook_url
        ? "settings.configForms.workbench.profileSummary.notificationsActive"
        : "settings.configForms.workbench.profileSummary.notificationsInactive"
    ),
  },
];

const buildItems = (profile, data, t) => {
  switch (profile.page) {
    case "level":
      return levelItems(data, t);
    case "vacBans":
      return vacItems(data, t);
    case "tkBans":
      return tkItems(data, t);
    case "seedVip":
      return seedVipItems(data, t);
    case "expiredVip":
      return expiredVipItems(data, t);
    default:
      return [];
  }
};

function SummaryItem({ icon: Icon, label, value }) {
  return (
    <Box
      sx={{
        minWidth: 0,
        display: "grid",
        gridTemplateColumns: "32px minmax(0, 1fr)",
        alignItems: "center",
        columnGap: 1.1,
        px: { xs: 1.25, md: 1.75 },
        py: 1.35,
        borderRight: { xs: 0, sm: "1px solid" },
        borderBottom: { xs: "1px solid", sm: 0 },
        borderColor: "divider",
        "&:last-of-type": { borderRight: 0, borderBottom: 0 },
      }}
    >
      <Box data-theme-surface="control"
        sx={{
          display: "grid",
          placeItems: "center",
          width: 32,
          height: 32,
          border: "1px solid",
          borderColor: "primary.main",
          color: "primary.main",
          bgcolor: "action.hover",
        }}
      >
        <Icon sx={{ fontSize: 18 }} />
      </Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", lineHeight: 1.3 }}
        >
          {label}
        </Typography>
        <Typography variant="body2" fontWeight={750} noWrap title={value}>
          {value}
        </Typography>
      </Box>
    </Box>
  );
}

export default function ConfigProfileSummaryPanel({ profile, data }) {
  const { t } = useTranslation();
  const items = buildItems(profile, data, t);
  if (!items.length) return null;

  return (
    <Box component="aside">
      <Stack data-theme-surface="panel"
        direction={{ xs: "column", sm: "row" }}
        sx={{
          display: { xs: "flex", sm: "grid" },
          gridTemplateColumns: `repeat(${items.length}, minmax(0, 1fr))`,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.default",
        }}
      >
        {items.map((item) => (
          <SummaryItem key={item.label} {...item} />
        ))}
      </Stack>
    </Box>
  );
}
