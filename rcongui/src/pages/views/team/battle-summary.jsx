import { Box, Chip, Stack, Typography } from "@mui/material";
import GroupsIcon from "@mui/icons-material/Groups";
import MapOutlinedIcon from "@mui/icons-material/MapOutlined";
import MilitaryTechOutlinedIcon from "@mui/icons-material/MilitaryTechOutlined";
import PersonOffOutlinedIcon from "@mui/icons-material/PersonOffOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import { useTranslation } from "react-i18next";

const formatRemainingTime = (value) => {
  if (value == null || value === "") return "–";
  if (typeof value === "string") return value;

  const totalSeconds = Math.max(0, Number(value) || 0);
  const hours = Math.floor(totalSeconds / 3600);
  const minutes = Math.floor((totalSeconds % 3600) / 60);
  const seconds = Math.floor(totalSeconds % 60);
  return [hours, minutes, seconds]
    .map((part) => String(part).padStart(2, "0"))
    .join(":");
};

const TeamCount = ({ side, count, label, playerLabel }) => (
  <Box className={`battle-team battle-team--${side}`}>
    <GroupsIcon aria-hidden />
    <Box>
      <Typography variant="overline">{label}</Typography>
      <Typography variant="h4" component="p">
        {count ?? 0}
        <Typography component="span" variant="body2">
          {" "}
          {playerLabel}
        </Typography>
      </Typography>
    </Box>
  </Box>
);

const Issue = ({ icon, title, detail, severity = "warning" }) => (
  <Box className={`battle-issue battle-issue--${severity}`}>
    {icon}
    <Box>
      <Typography variant="subtitle2">{title}</Typography>
      <Typography variant="caption" color="text.secondary">
        {detail}
      </Typography>
    </Box>
  </Box>
);

const BattleSummary = ({ gameData, teams }) => {
  const { t } = useTranslation();
  const allies = teams?.allies;
  const axis = teams?.axis;
  const lobby = teams?.lobby;
  const currentMap = gameData?.current_map;
  const noCommanderCount = [allies, axis].filter(
    (team) => team && !team.commander
  ).length;
  const noLeaderCount =
    (allies?.no_sl_squads?.length ?? 0) + (axis?.no_sl_squads?.length ?? 0);
  const unassignedCount =
    (lobby?.count ?? 0) +
    [allies, axis].reduce(
      (sum, team) =>
        sum +
        (team?.squads?.find((squad) => squad.name === "unassigned")?.players
          ?.length ?? 0),
      0
    );

  return (
    <Box
      component="section"
      aria-labelledby="battle-summary-title"
      sx={{
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        overflow: "hidden",
        backgroundColor: "background.paper",
        mb: 1.5,
        "& .battle-main": {
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "minmax(0, 1fr) auto minmax(0, 1fr)",
          },
          alignItems: "stretch",
        },
        "& .battle-team": {
          display: "flex",
          alignItems: "center",
          gap: 1.5,
          px: { xs: 1.5, md: 2.5 },
          py: 1.25,
          minWidth: 0,
          "& .MuiSvgIcon-root": { fontSize: 34 },
          "& .MuiTypography-overline": { lineHeight: 1.1 },
          "& .MuiTypography-h4": { fontWeight: 800, lineHeight: 1.1 },
        },
        "& .battle-team--allies": {
          color: "info.light",
          background:
            "linear-gradient(90deg, rgba(33,150,243,.10), transparent)",
        },
        "& .battle-team--axis": {
          justifyContent: { sm: "flex-end" },
          textAlign: { sm: "right" },
          color: "error.light",
          background:
            "linear-gradient(270deg, rgba(244,67,54,.10), transparent)",
        },
        "& .battle-score": {
          minWidth: { sm: 180 },
          px: 2,
          py: 1.1,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          borderLeft: { sm: "1px solid" },
          borderRight: { sm: "1px solid" },
          borderTop: { xs: "1px solid", sm: 0 },
          borderBottom: { xs: "1px solid", sm: 0 },
          borderColor: "divider",
        },
        "& .battle-issues": {
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "repeat(3, minmax(0, 1fr))",
          },
          borderTop: "1px solid",
          borderColor: "divider",
        },
        "& .battle-issue": {
          display: "flex",
          gap: 1,
          alignItems: "center",
          px: 1.5,
          py: 1,
          minWidth: 0,
          "& + .battle-issue": {
            borderLeft: { md: "1px solid" },
            borderTop: { xs: "1px solid", md: 0 },
            borderColor: "divider",
          },
        },
        "& .battle-issue--warning > .MuiSvgIcon-root": {
          color: "warning.main",
        },
        "& .battle-map": {
          display: "flex",
          flexWrap: "wrap",
          gap: 1.5,
          alignItems: "center",
          px: 1.5,
          py: 0.75,
          borderTop: "1px solid",
          borderColor: "divider",
          color: "text.secondary",
        },
      }}
    >
      <Box className="battle-main">
        <TeamCount
          side="allies"
          count={gameData?.num_allied_players ?? allies?.count}
          label={t("views.team.allies")}
          playerLabel={t("views.team.players")}
        />
        <Box className="battle-score">
          <Stack direction="row" spacing={0.75} alignItems="center">
            <MilitaryTechOutlinedIcon color="primary" aria-hidden />
            <Typography
              id="battle-summary-title"
              variant="caption"
              color="text.secondary"
            >
              {t("views.team.liveScore")}
            </Typography>
          </Stack>
          <Typography variant="h4" component="p" sx={{ fontWeight: 800 }}>
            {gameData?.allied_score ?? 0} : {gameData?.axis_score ?? 0}
          </Typography>
        </Box>
        <TeamCount
          side="axis"
          count={gameData?.num_axis_players ?? axis?.count}
          label={t("views.team.axis")}
          playerLabel={t("views.team.players")}
        />
      </Box>

      <Box className="battle-issues">
        <Issue
          icon={<PersonOffOutlinedIcon aria-hidden />}
          title={t("views.team.issueCommander", { count: noCommanderCount })}
          detail={t("views.team.issueCommanderDetail")}
        />
        <Issue
          icon={<ReportProblemOutlinedIcon aria-hidden />}
          title={t("views.team.issueLeaders", { count: noLeaderCount })}
          detail={t("views.team.issueLeadersDetail")}
        />
        <Issue
          icon={<GroupsIcon aria-hidden />}
          title={t("views.team.issueUnassigned", { count: unassignedCount })}
          detail={t("views.team.issueUnassignedDetail")}
          severity={unassignedCount ? "warning" : "ok"}
        />
      </Box>

      <Box className="battle-map">
        <MapOutlinedIcon fontSize="small" aria-hidden />
        <Typography variant="body2" sx={{ color: "text.primary" }}>
          {currentMap?.pretty_name ?? t("common.unknown")}
        </Typography>
        {currentMap?.game_mode && (
          <Chip
            size="small"
            label={t(`views.team.gameModes.${currentMap.game_mode}`, {
              defaultValue: currentMap.game_mode,
            })}
            variant="outlined"
          />
        )}
        <ScheduleOutlinedIcon fontSize="small" aria-hidden />
        <Typography variant="body2">
          {formatRemainingTime(gameData?.raw_time_remaining)}
        </Typography>
      </Box>
    </Box>
  );
};

export default BattleSummary;
