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

const UNASSIGNED = "unassigned";

const AlertItem = ({ item, onFilter }) => {
  const Icon = item.icon;
  const interactive = Boolean(item.filter && onFilter);
  const content = (
    <Stack
      direction="row"
      alignItems="center"
      spacing={0.75}
      sx={{ minWidth: 0 }}
    >
      <Icon
        sx={{
          color: `${item.color}.main`,
          flex: "0 0 auto",
          fontSize: "1.05rem",
        }}
      />
      <Box sx={{ minWidth: 0, textAlign: "left" }}>
        <Typography
          variant="caption"
          noWrap
          sx={{ color: "text.secondary", display: "block" }}
        >
          {item.label}
        </Typography>
        <Typography variant="subtitle2" noWrap>
          {item.value}
        </Typography>
      </Box>
    </Stack>
  );

  const sx = (theme) => ({
    border: `1px solid ${alpha(theme.palette[item.color].main, 0.28)}`,
    borderLeft: `3px solid ${theme.palette[item.color].main}`,
    bgcolor: alpha(theme.palette[item.color].main, 0.045),
    minHeight: 52,
    minWidth: 0,
    px: 1.25,
    py: 0.75,
    width: "100%",
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
    <ButtonBase onClick={() => onFilter(item.filter)} sx={sx}>
      {content}
    </ButtonBase>
  ) : (
    <Box sx={sx}>{content}</Box>
  );
};

const InfoPanel = ({ gameData, playersData, onFilter }) => {
  const { t } = useTranslation();
  const content = [];
  const teamLabel = (team) => {
    if (team === "axis") return t("views.team.axis");
    if (team === "allies") return t("views.team.allies");
    return t("views.live.lobby");
  };

  const vipsCount = playersData.filter((player) => player.is_vip).length;
  if (vipsCount > 0) {
    content.push({
      key: "vips",
      type: "info",
      label: t("views.live.vips"),
      value: vipsCount,
      color: "warning",
      icon: StarOutline,
      filter: { columnId: "vip", value: true },
    });
  }

  const watchedCount = playersData.filter(
    (player) => player.profile.watchlist?.is_watched
  ).length;
  if (watchedCount > 0) {
    content.push({
      key: "watched",
      type: "info",
      label: t("views.live.watched"),
      value: watchedCount,
      color: "primary",
      icon: VisibilityOutlined,
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
      !state.commander
    ) {
      content.push({
        key: `${team}-commander`,
        type: "warning",
        label: teamLabel(team),
        value: t("views.live.noCommander"),
        color: "error",
        icon: ErrorOutline,
        filter: { columnId: "team", value: team },
      });
    }

    if (
      team !== "lobby" &&
      playersData.length > 0 &&
      state?.no_sl_squads.length > 0
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
        filter: { columnId: "unit", value: state.no_sl_squads },
      });
    }
  }

  content.push({
    key: "score",
    type: "info",
    label: `${t("views.live.score")} · ${t("views.team.allies")} : ${t("views.team.axis")}`,
    value: `${gameData?.allied_score ?? 0} : ${gameData?.axis_score ?? 0}`,
    color: "secondary",
    icon: SportsScoreOutlined,
  });

  content.push({
    key: "next-map",
    type: "info",
    label: t("views.live.nextMap"),
    value: gameData?.next_map?.pretty_name ?? "–",
    color: "info",
    icon: MapOutlined,
  });

  return (
    <Box
      component="section"
      aria-label={t("views.live.actionableStatus")}
      sx={{
        display: "grid",
        gridTemplateColumns: {
          xs: "repeat(1, minmax(0, 1fr))",
          sm: "repeat(2, minmax(0, 1fr))",
          lg: `repeat(${Math.min(content.length, 6)}, minmax(0, 1fr))`,
        },
        gap: 0.75,
        mb: 1,
      }}
    >
      {content
        .sort((a, b) => (a.type === b.type ? 0 : a.type === "warning" ? -1 : 1))
        .map((item) => (
          <AlertItem key={item.key} item={item} onFilter={onFilter} />
        ))}
    </Box>
  );
};

export default InfoPanel;
