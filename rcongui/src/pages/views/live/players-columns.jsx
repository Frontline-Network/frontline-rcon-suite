import {
  Box,
  Checkbox,
  IconButton,
  Stack,
  styled,
  Tooltip,
  Typography,
} from "@mui/material";
import { ErrorOutline, Star, Warning } from "@mui/icons-material";
import { yellow } from "@mui/material/colors";
import { alpha } from "@mui/material/styles";
import dayjs from "dayjs";
import { CountryFlag } from "@/components/shared/CountryFlag";
import {
  getPlayerTier,
  getTierColors,
} from "@/utils/lib";
import { countRecentWarnings, hasRecentWarnings } from "@/utils/player-warnings.mjs";
import { SortableHeader, TextButton } from "@/components/table/styles";
import RemoveRedEyeIcon from "@mui/icons-material/RemoveRedEye";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import CopyableText from "@/components/shared/CopyableText";
import { FontAwesomeIcon } from "@fortawesome/react-fontawesome";
import Emoji from "@/components/shared/Emoji";
import { useThemedImages } from "@/hooks/useThemedImages";
import {
  getPlatformIcon,
  getPlatformLabel,
} from "@/constants/platforms";
import { getPlayerIdentity } from "@/utils/player-identity.mjs";
import { getTeamkillRisk } from "@/utils/teamkill-risk.mjs";
import { getFactionIconSrc } from "@/utils/factionIcons";
import { formatRoleLabel, formatSquadLabel } from "./player-display-labels";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";

export const Square = styled(Box)(({ theme }) => ({
  display: "flex",
  alignItems: "start",
  justifyContent: "center",
  width: "1em",
  height: "1em",
  lineHeight: "1em",
  fontWeight: "bold",
  backgroundColor: theme.palette.background.paper,
}));

const LevelColored = styled(Box, {
  shouldForwardProp: (prop) => prop !== "level",
})(({ theme, level }) => {
  if (!level) return {};
  const tier = getPlayerTier(level);
  return {
    color: getTierColors(theme.palette.mode)[tier],
  };
});

// TODO
// const TKColored = styled(Box, {
//   shouldForwardProp: (prop) => prop !== "teamKills",
// })(({ theme, teamKills }) => {
//   if (!teamKills) return {};
//   return {
//     color: getTeamKillColor(teamKills, theme) || "inherit",
//   };
// });

const Center = styled(Box)(() => ({
  display: "grid",
  justifyItems: "center",
  alignContent: "center",
}));

const iconFontSize = "1em";
const emojiFontSize = "0.85em";
const getBanDetailText = (t, detail) => {
  if (detail.scope === "direct" && detail.type === "gameServer") {
    return t("views.table.activeBanDirect");
  }
  if (detail.scope === "direct") {
    return t("views.table.activeBlacklistDirect", {
      list: detail.record?.blacklist?.name ?? "–",
    });
  }

  const game = t(`playerIdentity.games.${detail.account?.game}`);
  if (detail.type === "gameServer") {
    return t("views.table.activeBanLinked", {
      game,
      name: detail.account?.name,
    });
  }
  return t("views.table.activeBlacklistLinked", {
    game,
    name: detail.account?.name,
    list: detail.record?.blacklist?.name ?? "–",
  });
};

const TeamkillRisk = ({ value, t, compact = false }) => {
  const risk = getTeamkillRisk(value);
  const levelLabel = t(`views.table.teamKillRisk.${risk.level}`);
  const description = t("views.table.teamKillRisk.description", {
    count: risk.count,
    level: levelLabel,
  });
  const color =
    risk.level === "high"
      ? "error.main"
      : risk.level === "caution"
      ? "warning.main"
      : "success.main";
  const Icon = risk.level === "high" ? ErrorOutline : Warning;

  return (
    <Tooltip
      arrow
      title={
        <Stack spacing={0.25}>
          <Typography variant="caption" fontWeight="bold">
            {description}
          </Typography>
          <Typography variant="caption">
            {t("views.table.teamKillRisk.thresholds")}
          </Typography>
        </Stack>
      }
    >
      <Box
        role="img"
        aria-label={description}
        sx={{
          alignItems: "center",
          color,
          display: "inline-flex",
          fontVariantNumeric: "tabular-nums",
          fontWeight: 700,
          gap: 0.25,
          whiteSpace: "nowrap",
        }}
      >
        {risk.level !== "none" ? (
          <Icon aria-hidden="true" sx={{ fontSize: "1em" }} />
        ) : null}
        <Typography component="span" variant="caption" fontWeight="inherit">
          {compact ? `TK ${risk.count}` : `${risk.count} ${levelLabel}`}
        </Typography>
      </Box>
    </Tooltip>
  );
};

export const getColumns = (t, factionByTeam = {}) => [
  {
    id: "select",
    header: ({ table }) => (
      <Checkbox
        inputProps={{ "aria-label": t("common.selectAll") }}
        checked={table.getIsAllRowsSelected()}
        indeterminate={table.getIsSomePageRowsSelected()}
        onChange={table.getToggleAllRowsSelectedHandler()}
        size="small"
        sx={{
          p: 0,
        }}
      />
    ),
    cell: ({ row }) => (
      <div>
        <Checkbox
          inputProps={{
            "aria-label": t("common.selectPlayer", {
              name: row.original.name,
            }),
          }}
          checked={row.getIsSelected()}
          disabled={!row.getCanSelect()}
          indeterminate={row.getIsSomeSelected()}
          onChange={row.getToggleSelectedHandler()}
          size="small"
          sx={{
            p: 0,
          }}
        />
      </div>
    ),
    meta: {
      variant: "icon",
      sticky: "left",
      stickyOffset: 0,
    },
  },
  {
    id: "player_summary",
    header: SortableHeader(t("views.table.name"), t("views.table.name")),
    accessorFn: (row) => row.name,
    cell: ({ row }) => {
      const { openWithId } = usePlayerSidebar();
      return (
        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          sx={{
            minWidth: "12ch",
            maxWidth: "100%",
            overflow: "hidden",
            textAlign: "left",
            whiteSpace: "nowrap",
          }}
        >
          <Tooltip arrow placement="top-start" title={row.original.name}>
            <Box
              component="span"
              sx={{ display: "inline-flex", minWidth: 0, overflow: "hidden" }}
            >
              <TextButton
                onClick={() => openWithId(row.original.player_id)}
                sx={{ minWidth: 0, maxWidth: "100%", overflow: "hidden" }}
              >
                <Typography
                  component="span"
                  noWrap
                  variant="body2"
                  sx={{
                    color: (theme) => alpha(theme.palette.text.primary, 0.82),
                    display: "block",
                    fontWeight: 300,
                    maxWidth: "100%",
                  }}
                >
                  {row.original.name}
                </Typography>
              </TextButton>
            </Box>
          </Tooltip>
          <LevelColored
            component="span"
            level={row.original.level}
            sx={{
              flex: "0 0 auto",
              fontSize: "0.72rem",
              fontWeight: 700,
              lineHeight: 1,
            }}
          >
            Lv {row.original.level ?? "–"}
          </LevelColored>
        </Stack>
      );
    },
    meta: {
      variant: "playerName",
      sticky: "left",
      stickyOffset: "4.5rem",
    },
  },
  {
    id: "performance_summary",
    header: SortableHeader(
      t("views.live.performance"),
      t("views.live.performance")
    ),
    accessorFn: (row) => row.kills,
    cell: ({ row }) => (
      <Stack
        direction="row"
        alignItems="center"
        spacing={0.75}
        sx={{ minWidth: "10ch", whiteSpace: "nowrap" }}
      >
        <Tooltip
          arrow
          title={`${t("views.table.kills")}: ${row.original.kills ?? 0} · ${t(
            "views.table.deaths"
          )}: ${row.original.deaths ?? 0}`}
        >
          <Typography
            component="span"
            variant="caption"
            sx={{ color: "text.primary", whiteSpace: "nowrap" }}
          >
            K {row.original.kills ?? 0} · D {row.original.deaths ?? 0}
          </Typography>
        </Tooltip>
        <TeamkillRisk value={row.original} t={t} compact />
      </Stack>
    ),
    meta: { variant: "performanceSummary" },
  },
  {
    id: "status_summary",
    header: t("views.live.status"),
    accessorFn: (row) =>
      [
        row.is_vip,
        row.profile?.watchlist?.is_watched,
        hasRecentWarnings(row.profile),
        row.activeBanStatus?.isActive,
      ].filter(Boolean).length,
    cell: ({ row }) => {
      const items = [];
      if (row.original.is_vip) {
        items.push({
          key: "vip",
          icon: <Star sx={{ fontSize: "0.95rem" }} />,
          label: "VIP",
          color: "warning.light",
        });
      }
      if (row.original.profile?.watchlist?.is_watched) {
        items.push({
          key: "watch",
          icon: <RemoveRedEyeIcon sx={{ fontSize: "0.95rem" }} />,
          label: t("views.live.watched"),
          color: "primary.light",
        });
      }
      if (hasRecentWarnings(row.original.profile)) {
        items.push({
          key: "warning",
          icon: <Warning sx={{ fontSize: "0.95rem" }} />,
          label: t("views.live.warned"),
          color: "warning.light",
        });
      }
      if (row.original.activeBanStatus?.isActive) {
        items.push({
          key: "ban",
          icon: <ErrorOutline sx={{ fontSize: "0.95rem" }} />,
          label: t("views.table.activeBan"),
          color: "error.light",
        });
      }
      if (items.length === 0) {
        return (
          <Typography variant="caption" sx={{ color: "text.disabled" }}>
            –
          </Typography>
        );
      }
      return (
        <Stack direction="row" flexWrap="wrap" gap={0.75}>
          {items.map((item) => (
            <Tooltip key={item.key} arrow title={item.label}>
              <Box
                component="span"
                role="img"
                aria-label={item.label}
                sx={{
                  alignItems: "center",
                  color: item.color,
                  display: "inline-flex",
                  minHeight: 24,
                }}
              >
                {item.icon}
              </Box>
            </Tooltip>
          ))}
        </Stack>
      );
    },
    meta: { variant: "statusSummary" },
  },
  {
    accessorKey: "team",
    id: "team",
    header: SortableHeader(t("views.table.team"), t("views.table.team")),
    cell: ({ row }) => {
      const team = row.original.team;
      const teamLabel = t(`views.team.${team}`, {
        defaultValue: team ?? "–",
      });
      const faction = factionByTeam[team] ?? team ?? "unknown";
      return (
        <Tooltip arrow placement="top" title={teamLabel}>
          <Box
            component="img"
            src={getFactionIconSrc(faction, "colored")}
            alt={teamLabel}
            sx={{
              display: "block",
              height: 20,
              mx: "auto",
              objectFit: "contain",
              width: 20,
            }}
            onError={(event) => {
              event.currentTarget.src = getFactionIconSrc("unknown", "colored");
            }}
          />
        </Tooltip>
      );
    },
    meta: {
      variant: "teamCompact",
    },
  },
  {
    id: "unit",
    header: SortableHeader(t("views.table.unit"), t("views.table.unit")),
    accessorKey: "unit_name",
    filterFn: (row, _columnId, value) => {
      if (!value || (Array.isArray(value) && value.length === 0)) return true;
      const values = Array.isArray(value) ? value : [value];
      return values.includes(row.original.unit_name);
    },
    // Group by unit name and team
    // getGroupingValue: (row) => `${row.original.unit_name ?? "-"}-${row.original.team}`,
    cell: ({ row }) => {
      const unitLabel = formatSquadLabel(row.original.unit_name);
      return (
        <Tooltip arrow placement="top" title={unitLabel}>
          <Typography
            noWrap
            variant="caption"
            sx={{ color: "text.primary", fontWeight: 600 }}
          >
            {unitLabel}
          </Typography>
        </Tooltip>
      );
    },
    meta: {
      variant: "squadCompact",
    },
  },
  {
    id: "role",
    header: SortableHeader("R", t("views.table.role")),
    accessorKey: "role",
    cell: ({ row }) => {
      const themedImg = useThemedImages();
      return (
        <Center>
          <Square>
            <img
              src={themedImg.getRoleIconSrc(row.original.role)}
              width={16}
              height={16}
              alt={formatRoleLabel(t, row.original.role)}
              title={formatRoleLabel(t, row.original.role)}
            />
          </Square>
        </Center>
      );
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "level",
    header: SortableHeader("LVL", t("views.table.level")),
    accessorKey: "level",
    aggregationFn: "mean",
    cell: ({ row }) => {
      return (
        <LevelColored level={row.original.level} sx={{ paddingLeft: "0.75em" }}>
          {row.original.level}
        </LevelColored>
      );
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "kills",
    header: SortableHeader(t("views.table.kills"), t("views.table.kills")),
    accessorKey: "kills",
    cell: ({ row }) => {
      return <>{row.original.kills}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "deaths",
    header: SortableHeader(t("views.table.deaths"), t("views.table.deaths")),
    accessorKey: "deaths",
    cell: ({ row }) => {
      return <>{row.original.deaths}</>;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "kpm",
    header: SortableHeader("KPM", t("views.table.killsPerMinute")),
    accessorFn: (row) => {
      const kills = Number(row.kills) || 0;
      const playtime = Number(
        row.map_playtime_seconds ?? row.profile?.current_playtime_seconds ?? 0
      );
      if (!Number.isFinite(playtime) || playtime <= 0 || kills <= 0) return 0;
      return (kills / playtime) * 60;
    },
    cell: (props) => {
      return <>{props.getValue()?.toFixed(2)}</>;
    },
  },
  {
    id: "team_kills",
    header: SortableHeader(
      t("views.table.teamKillRiskLabel"),
      t("views.table.teamKillRiskLabel")
    ),
    accessorFn: (row) => getTeamkillRisk(row).count,
    filterFn: (row, _columnId, value) => {
      if (value !== "risk") return true;
      return getTeamkillRisk(row.original).count > 0;
    },
    cell: (props) => {
      return <TeamkillRisk value={props.getValue()} t={t} />;
    },
    meta: {
      variant: "short",
    },
  },
  {
    id: "combat",
    header: SortableHeader("CE", t("views.table.combat")),
    accessorKey: "combat",
    cell: ({ row }) => {
      return <>{row.original.combat}</>;
    },
  },
  {
    id: "offense",
    header: SortableHeader("OE", t("views.table.offense")),
    accessorKey: "offense",
    cell: ({ row }) => {
      return <>{row.original.offense}</>;
    },
  },
  {
    id: "defense",
    header: SortableHeader("DE", t("views.table.defense")),
    accessorKey: "defense",
    cell: ({ row }) => {
      return <>{row.original.defense}</>;
    },
  },
  {
    id: "support",
    header: SortableHeader("SE", t("views.table.support")),
    accessorKey: "support",
    cell: ({ row }) => {
      return <>{row.original.support}</>;
    },
  },
  {
    id: "vehicle_kills",
    header: SortableHeader("VK", t("views.table.vehicleKills")),
    accessorKey: "vehicle_kills",
    cell: ({ row }) => {
      return <>{row.original.vehicle_kills}</>;
    },
  },
  {
    id: "vehicles_destroyed",
    header: SortableHeader("VD", t("views.table.vehiclesDestroyed")),
    accessorKey: "vehicles_destroyed",
    cell: ({ row }) => {
      return <>{row.original.vehicles_destroyed}</>;
    },
  },
  {
    id: "actions",
    header: SortableHeader("ACT", t("common.actions")),
    accessorKey: "actions",
    cell: ({ row, table }) => {
      const isOpen =
        table.options.meta?.activePlayerActionId === row.original.player_id;
      return (
        <Tooltip title={t("actions.menu")}>
          <IconButton
            aria-controls={isOpen ? "live-player-row-actions-menu" : undefined}
            aria-expanded={isOpen ? "true" : undefined}
            aria-haspopup="true"
            aria-label={t("actions.menu")}
            data-player-name={row.original.name}
            data-testid="live-player-row-actions-trigger"
            disableRipple
            onClick={(event) =>
              table.options.meta?.openPlayerActionMenu?.(
                event.currentTarget,
                row.original
              )
            }
            sx={{
              width: "1em",
              height: "1em",
              fontSize: "1em",
            }}
          >
            <MoreHorizIcon fontSize="inherit" />
          </IconButton>
        </Tooltip>
      );
    },
    meta: {
      variant: "icon",
      sticky: "right",
      stickyOffset: 0,
    },
  },
  {
    id: "platform",
    header: SortableHeader("OS", t("views.table.platform")),
    accessorFn: (row) => getPlatformLabel(getPlayerIdentity(row).platform) || t("common.unknown"),
    cell: ({ row }) => {
      const { platform, profileUrl } = getPlayerIdentity(row.original);

      if (platform === "steam" && profileUrl)
        return (
          <Box
            component={"a"}
            sx={{
              width: 14,
              height: 24,
              textDecoration: "none",
              color: "inherit",
              "&:hover": { cursor: "pointer" },
            }}
            href={profileUrl}
            target="_blank"
            rel="noopener noreferrer"
            title={getPlatformLabel(platform)}
          >
            <FontAwesomeIcon icon={getPlatformIcon(platform)} size="sm" />
          </Box>
        );

      return (
        <Box sx={{ width: 14, height: 24 }} title={getPlatformLabel(platform) || t("common.unknown")}>
          <FontAwesomeIcon icon={getPlatformIcon(platform)} size="sm" />
        </Box>
      );
    },
  },
  {
    id: "clan-tag",
    header: SortableHeader("Clan", t("views.table.clanTag")),
    accessorKey: "clan_tag",
    cell: ({ row }) => {
      return <>{row.original.clan_tag}</>;
    },
  },
  {
    id: "name",
    header: SortableHeader("Name", t("views.table.name")),
    accessorKey: "name",
    cell: ({ row }) => {
      const { openWithId } = usePlayerSidebar();
      return (
        <Stack sx={{ textAlign: "left" }}>
          <TextButton onClick={() => openWithId(row.original.player_id)}>
            {row.original.name}
          </TextButton>
          <CopyableText
            text={row.original.player_id}
            size={"0.75em"}
            sx={{
              color: "text.secondary",
              '[data-expanded-view="false"] &': {
                display: "none",
              },
            }}
          />
        </Stack>
      );
    },
  },
  {
    id: "player_id",
    header: SortableHeader("ID"),
    accessorKey: "player_id",
    cell: ({ row }) => {
      return <CopyableText text={row.original.player_id} />;
    },
  },
  {
    id: "active_ban",
    header: SortableHeader("B", t("views.table.activeBan")),
    accessorFn: (row) => (row.activeBanStatus?.isActive ? 1 : 0),
    cell: ({ row }) => {
      const status = row.original.activeBanStatus;
      if (!status?.isActive) return null;
      return (
        <Tooltip
          arrow
          title={
            <Stack spacing={0.25}>
              <Typography variant="caption" fontWeight="bold">
                {t("views.table.activeBan")}
              </Typography>
              {status.details.map((detail, index) => (
                <Typography key={index} variant="caption">
                  {getBanDetailText(t, detail)}
                </Typography>
              ))}
              <Typography variant="caption">
                {t("views.table.activeBanNoAutomaticAction")}
              </Typography>
            </Stack>
          }
        >
          <ErrorOutline
            aria-label={t("views.table.activeBan")}
            sx={{ color: "error.main", fontSize: "1.15em" }}
          />
        </Tooltip>
      );
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "warnings",
    header: SortableHeader("!", t("views.table.recentAction")),
    accessorFn: (row) => countRecentWarnings(row.profile),
    cell: ({ row }) => {
      return hasRecentWarnings(row.original.profile) ? (
        <Warning
          sx={{
            color: (theme) =>
              theme.palette.mode === "dark" ? yellow["500"] : "inherit",
            fontSize: iconFontSize,
          }}
        />
      ) : null;
    },
    meta: {
      variant: "icon",
    },
  },
  {
    id: "watchlist",
    header: SortableHeader("W", t("views.table.watchlist")),
    accessorKey: "profile.watchlist",
    filterFn: (row, _columnId, value) =>
      !value || Boolean(row.original.profile?.watchlist?.is_watched),
    cell: ({ row }) => {
      return row.original.profile?.watchlist &&
        row.original.profile?.watchlist?.is_watched ? (
        <RemoveRedEyeIcon sx={{ fontSize: iconFontSize }} />
      ) : null;
    },
  },
  {
    id: "country",
    header: SortableHeader("CC", t("views.table.country")),
    accessorKey: "country",
    cell: ({ row }) => {
      return row.original.country && row.original.country !== "private" ? (
        <CountryFlag country={row.original.country} />
      ) : null;
    },
  },
  {
    id: "vip",
    header: SortableHeader("VIP"),
    accessorKey: "is_vip",
    filterFn: (row, _columnId, value) => !value || Boolean(row.original.is_vip),
    cell: ({ row }) => {
      return row.original.is_vip ? (
        <Star
          sx={{
            color: (theme) =>
              theme.palette.mode === "dark" ? yellow["500"] : "inherit",
            fontSize: iconFontSize,
          }}
        />
      ) : null;
    },
  },
  {
    id: "flags",
    header: t("views.table.flags").toUpperCase(),
    accessorKey: "profile.flags",
    cell: ({ row }) => {
      const flags = row.original.profile.flags;
      if (!flags || flags.length === 0) return null;
      const flagsCount = 5;
      return (
        <Stack spacing={0.5} direction={"row"} alignItems={"center"}>
          {flags
            .slice(0, flagsCount)
            .map(({ flag, comment: note, modified }) => (
              <Tooltip title={note} key={modified}>
                <Emoji emoji={flag} size={14} />
              </Tooltip>
            ))}
          {flags.length - flagsCount > 0 ? (
            <Typography
              variant="caption"
              sx={{ pr: 0.5, fontSize: emojiFontSize }}
            >{`+${flags.length - flagsCount}`}</Typography>
          ) : null}
        </Stack>
      );
    },
  },
  {
    id: "visits",
    header: SortableHeader("VISITS", t("views.table.visits")),
    accessorKey: "profile.sessions_count",
    cell: ({ row }) => {
      return <>{row.original.profile.sessions_count}</>;
    },
  },
  {
    id: "time",
    header: SortableHeader(
      t("views.table.timeShort"),
      t("views.table.currentPlaytime")
    ),
    accessorKey: "profile.current_playtime_seconds",
    aggregationFn: "mean",
    cell: ({ row }) => {
      return (
        <>
          {dayjs
            .duration(row.original.profile.current_playtime_seconds, "seconds")
            .format("H:mm")}
        </>
      );
    },
    meta: {
      variant: "short",
    },
  },
];
