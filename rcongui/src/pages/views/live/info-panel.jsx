import { extractTeamState } from "@/utils/extractPlayers";
import {
  ErrorOutline,
  MapOutlined,
  SportsScoreOutlined,
  StarOutline,
  VisibilityOutlined,
} from "@mui/icons-material";
import { Box, ButtonBase, Stack, Typography, alpha } from "@mui/material";
import { useTranslation } from "react-i18next";
import { DEFAULT_LIVE_CARDS } from "./live-view-preferences.mjs";

const UNASSIGNED = "unassigned";

const filterValuesMatch = (left, right) =>
  JSON.stringify(left) === JSON.stringify(right);

const AlertItem = ({ item, onFilter, isActive }) => {
  const Icon = item.icon;
  const interactive = Boolean(item.filter && onFilter);
  const content = (
    <Stack
      alignItems={{
        xs: item.type === "warning" ? "center" : "flex-start",
        md: "flex-start",
      }}
      direction={{
        xs: item.type === "warning" ? "row" : "column",
        md: "column",
      }}
      justifyContent="space-between"
      spacing={0.75}
      sx={{ height: "100%", minWidth: 0, overflow: "hidden", width: "100%" }}
    >
      <Icon
        sx={{
          color: `${item.color}.main`,
          flex: "0 0 auto",
          fontSize: "1.05rem",
        }}
      />
      <Box sx={{ minWidth: 0, textAlign: "left", width: "100%" }}>
        <Typography
          variant="caption"
          sx={{
            color: "text.secondary",
            display: "block",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            width: "100%",
          }}
        >
          <Box component="span" sx={{ display: { xs: "inline", md: "none" } }}>
            {item.mobileLabel ?? item.label}
          </Box>
          <Box component="span" sx={{ display: { xs: "none", md: "inline" } }}>
            {item.label}
          </Box>
        </Typography>
        <Typography
          variant="h6"
          title={item.value}
          sx={{
            display: { xs: "-webkit-box", md: "block" },
            fontVariantNumeric: "tabular-nums",
            lineHeight: 1.15,
            overflow: "hidden",
            textOverflow: "ellipsis",
            WebkitBoxOrient: "vertical",
            WebkitLineClamp: { xs: 2, md: 1 },
            whiteSpace: { xs: "normal", md: "nowrap" },
            width: "100%",
          }}
        >
          {item.value}
        </Typography>
      </Box>
      <Typography
        color={
          item.type === "warning" ? `${item.color}.light` : "text.secondary"
        }
        variant="caption"
        sx={{ mt: "auto" }}
      >
        {item.priority}
      </Typography>
    </Stack>
  );

  const sx = (theme) => ({
    border: `1px solid ${alpha(theme.palette[item.color].main, 0.28)}`,
    borderLeft: `3px solid ${theme.palette[item.color].main}`,
    bgcolor: alpha(theme.palette[item.color].main, 0.045),
    gridColumn: { xs: item.type === "warning" ? "1 / -1" : "auto", md: "auto" },
    minHeight: { xs: item.type === "warning" ? 72 : 92, md: 92 },
    minWidth: 0,
    px: 1.25,
    py: 0.75,
    width: "100%",
    ...(isActive
      ? {
          bgcolor: alpha(theme.palette[item.color].main, 0.16),
          boxShadow: `inset 0 0 0 1px ${alpha(
            theme.palette[item.color].main,
            0.48
          )}`,
        }
      : {}),
    ...(interactive
      ? {
          cursor: "pointer",
          "&:hover": { bgcolor: alpha(theme.palette[item.color].main, 0.1) },
          "&:focus-visible": {
            outline: `2px solid ${theme.palette.primary.main}`,
          },
        }
      : {}),
  });

  return interactive ? (
    <ButtonBase
      aria-pressed={isActive}
      onClick={() => onFilter(item.filter)}
      sx={sx}
    >
      {content}
    </ButtonBase>
  ) : (
    <Box sx={sx}>{content}</Box>
  );
};

const InfoPanel = ({
  gameData,
  playersData,
  onFilter,
  activeFilters = [],
  visibility = DEFAULT_LIVE_CARDS,
}) => {
  const { t } = useTranslation();
  const content = [];
  const teamLabel = (team) => {
    if (team === "axis") return t("views.team.axis");
    if (team === "allies") return t("views.team.allies");
    return t("views.live.lobby");
  };

  const vipsCount = playersData.filter((player) => player.is_vip).length;
  if (visibility.vips && vipsCount > 0) {
    content.push({
      key: "vips",
      type: "info",
      label: t("views.live.vips"),
      value: vipsCount,
      color: "warning",
      icon: StarOutline,
      priority: t("views.live.priorityMedium"),
      filter: { columnId: "vip", value: true },
    });
  }

  const watchedCount = playersData.filter(
    (player) => player.profile.watchlist?.is_watched
  ).length;
  if (visibility.watched && watchedCount > 0) {
    content.push({
      key: "watched",
      type: "info",
      label: t("views.live.watched"),
      value: watchedCount,
      color: "primary",
      icon: VisibilityOutlined,
      priority: t("views.live.priorityMedium"),
      filter: { columnId: "watchlist", value: true },
    });
  }

  const teamStates = {
    axis: gameData?.axis ? extractTeamState(gameData.axis) : null,
    allies: gameData?.allies ? extractTeamState(gameData.allies) : null,
    lobby: gameData?.[UNASSIGNED]
      ? extractTeamState(gameData[UNASSIGNED])
      : null,
  };

  for (const team in teamStates) {
    const state = teamStates[team];
    if (
      team !== "lobby" &&
      playersData.length > 0 &&
      state &&
      !state.commander &&
      visibility.commander
    ) {
      content.push({
        key: `${team}-commander`,
        type: "warning",
        label: teamLabel(team),
        value: t("views.live.noCommander"),
        color: "error",
        icon: ErrorOutline,
        priority: t("views.live.priorityHigh"),
        filter: { columnId: "team", value: team },
      });
    }

    if (
      team !== "lobby" &&
      playersData.length > 0 &&
      state?.no_sl_squads.length > 0 &&
      visibility.squad_leaders
    ) {
      content.push({
        key: `${team}-leaders`,
        type: "warning",
        label: `${teamLabel(team)} · ${t("views.live.noSquadLeader")}`,
        value: state.no_sl_squads
          .map((squad) => squad.toUpperCase())
          .join(", "),
        color: "warning",
        icon: ErrorOutline,
        priority: t("views.live.priorityHigh"),
        filter: { columnId: "unit", value: state.no_sl_squads },
      });
    }
  }

  if (visibility.score)
    content.push({
      key: "score",
      type: "info",
      label: `${t("views.live.score")} · ${t("views.team.allies")} : ${t(
        "views.team.axis"
      )}`,
      mobileLabel: t("views.live.score"),
      value: `${gameData?.allied_score ?? 0} : ${gameData?.axis_score ?? 0}`,
      color: "secondary",
      icon: SportsScoreOutlined,
      priority: t("views.live.priorityInfo"),
    });

  if (visibility.next_map)
    content.push({
      key: "next-map",
      type: "info",
      label: t("views.live.nextMap"),
      value: gameData?.next_map?.pretty_name ?? "–",
      color: "info",
      icon: MapOutlined,
      priority: t("views.live.priorityInfo"),
    });

  if (content.length === 0) return null;

  return (
    <Box
      component="section"
      aria-label={t("views.live.actionableStatus")}
      sx={{ mb: 1 }}
    >
      <Typography
        component="h2"
        sx={{
          color: "primary.light",
          display: { xs: "block", md: "none" },
          mb: 0.75,
        }}
        variant="overline"
      >
        {t(
          content.some((item) => item.type === "warning")
            ? "views.live.reviewNow"
            : "views.live.statusCards"
        )}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: `repeat(${Math.min(content.length, 2)}, minmax(0, 1fr))`,
            sm: `repeat(${Math.min(content.length, 3)}, minmax(0, 1fr))`,
            md: `repeat(${Math.min(content.length, 3)}, minmax(0, 1fr))`,
            lg: `repeat(${Math.min(content.length, 6)}, minmax(0, 1fr))`,
          },
          gap: 0.75,
          minWidth: 0,
        }}
      >
        {content
          .sort((a, b) =>
            a.type === b.type ? 0 : a.type === "warning" ? -1 : 1
          )
          .map((item) => {
            const isActive =
              Boolean(item.filter) &&
              activeFilters.length === 1 &&
              activeFilters[0].id === item.filter.columnId &&
              filterValuesMatch(activeFilters[0].value, item.filter.value);

            return (
              <AlertItem
                key={item.key}
                item={item}
                onFilter={onFilter}
                isActive={isActive}
              />
            );
          })}
      </Box>
    </Box>
  );
};

export default InfoPanel;
