import { extractTeamState } from "@/utils/extractPlayers";
import { Box, Divider, Stack, Typography } from "@mui/material";
import WarningIcon from "@mui/icons-material/Warning";
import { useTranslation } from "react-i18next";

const UNASSIGNED = "unassigned"

const InfoPanel = ({ gameData, playersData }) => {
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
      type: "info",
      label: t("views.live.vips"),
      value: vipsCount,
    });
  }

  const watchedCount = playersData.filter((player) => player.profile.watchlist?.is_watched).length;
  if (watchedCount > 0) {
    content.push({
      type: "info",
      label: t("views.live.watched"),
      value: watchedCount,
    });
  }

  const teamStates = {
    axis: gameData?.axis ? extractTeamState(gameData?.axis) : null,
    allies: gameData?.allies ? extractTeamState(gameData?.allies) : null,
    lobby: gameData?.[UNASSIGNED] ? extractTeamState(gameData?.[UNASSIGNED]) : null,
  }

  for (const team in teamStates) {
    if (team !== "lobby" && playersData.length > 0 && teamStates[team] && !teamStates[team].commander) {
      content.push({
        type: "warning",
        label: teamLabel(team),
        value: t("views.live.noCommander"),
      });
    }

    if (team !== "lobby" && playersData.length > 0 && teamStates[team] && teamStates[team].no_sl_squads.length > 0) {
      content.push({
        type: "warning",
        label: `${teamLabel(team)} · ${t("views.live.noSquadLeader")}`,
        value: teamStates[team].no_sl_squads.map((squad) => squad.toUpperCase()).join(", "),
      });
    }

    if (teamStates[team] && teamStates[team].players_in_lobby.length > 0) {
      content.push({
        type: "info",
        label: team !== "lobby" ? `${teamLabel(team)} · ${t("views.live.lobby")}` : t("views.live.allLobby"),
        value: teamStates[team].players_in_lobby.length,
      });
    }
  }

  content.push({
    type: "info",
    label: t("views.live.nextMap"),
    value: gameData?.next_map?.pretty_name ?? "–",
  });

  return (
    <Stack direction="row" flexWrap="wrap" alignItems="center" columnGap={1} divider={<Divider orientation="vertical" flexItem />}  sx={{ border: "1px solid theme.palette.divider", p: 0.5 }}> 
      {content.sort((a) => a.type === "warning" ? -1 : 1).map((item, index) => (
        <Box key={index} sx={{ display: "flex", alignItems: "center", gap: 0.5, textWrap: "nowrap" }}>
          {item.type === "warning" && <WarningIcon sx={{ color: "warning.main", fontSize: 12 }} />}
          <Typography variant="caption">{item.label}: {item.value}</Typography>
        </Box>
      ))}
    </Stack>
  );
};

export default InfoPanel;
