import {
  List,
  Card,
  ListItem,
  ListItemButton,
  CardHeader,
  CardContent,
  Box,
  Typography,
} from "@mui/material";
import { Link } from "react-router-dom";
import dayjs from "dayjs";
import PlayCircleIcon from "@mui/icons-material/PlayCircle";
import StopCircleIcon from "@mui/icons-material/StopCircle";
import { useTranslation } from "react-i18next";
import { getMapModeLabel } from "@/utils/mapLabels";

const GamesCard = ({ games }) => {
  const { t } = useTranslation();
  return (
    <Card>
      <CardHeader title={t("dashboard.lastGames")} />
      <CardContent>
        <List dense sx={{ minWidth: 300 }}>
          {games.map((game) => {
            const size = 80;
            const ratio = 9 / 16;
            const matchMap = game.map;
            const duration =
              game.end && game.start
                ? Math.round(
                    (new Date(game.end) - new Date(game.start)) / 60000
                  )
                : null;

            // Helper function to get duration color
            const getDurationColor = (duration) => {
              if (!duration) return "text.secondary";
              if (duration < 20) return "error.main";
              if (duration < 35) return "warning.main";
              if (duration < 50) return "warning.light";
              if (duration < 75) return "success.main";
              return "secondary.main";
            };

            return (
              <ListItem key={game.id} disablePadding>
                <ListItemButton
                  component={Link}
                  to={`/stats/games/${game.id}`}
                  sx={{
                    "&:hover": { backgroundColor: "action.hover" },
                    color: "text.primary",
                    gap: 2,
                    py: { xs: 1.5, sm: 1 },
                  }}
                >
                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: { xs: "column", sm: "row" },
                      gap: { xs: 0, sm: 1 },
                    }}
                  >
                    <img
                      src={"/maps/icons/" + matchMap.image_name}
                      width={size}
                      height={size * ratio}
                      alt=""
                      style={{ borderRadius: 2 }}
                    />
                    <Box sx={{ display: "flex", flexDirection: "column" }}>
                      <Typography variant="body1" sx={{ fontWeight: 600 }}>
                        {matchMap.map.pretty_name}
                      </Typography>
                      <Typography
                        variant="subtitle2"
                        sx={{
                          borderRadius: 1,
                          fontSize: "0.75rem",
                          fontWeight: 500,
                          lineHeight: 1,
                        }}
                      >
                        {getMapModeLabel(t, matchMap.game_mode)}
                      </Typography>
                    </Box>
                  </Box>

                  <Box sx={{ flexGrow: 1 }}></Box>

                  <Box
                    sx={{
                      display: "flex",
                      flexDirection: { xs: "column", sm: "row" },
                    }}
                  >
                    <Box
                      sx={{
                        display: "flex",
                        flexDirection: "column",
                        width: "180px",
                      }}
                    >
                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "row",
                          gap: 0.5,
                          alignItems: "center",
                        }}
                      >
                        <StopCircleIcon sx={{ width: 16, height: 16 }} />
                        <Typography
                          variant="subtitle2"
                          sx={{
                            whiteSpace: "nowrap",
                          }}
                        >
                          {dayjs(game.end).format("lll")}
                        </Typography>
                      </Box>
                      <Box
                        sx={{
                          display: "flex",
                          flexDirection: "row",
                          gap: 0.5,
                          alignItems: "center",
                        }}
                      >
                        <PlayCircleIcon sx={{ width: 16, height: 16 }} />
                        <Typography
                          variant="subtitle2"
                          sx={{
                            whiteSpace: "nowrap",
                          }}
                        >
                          {dayjs(game.start).format("lll")}
                        </Typography>
                      </Box>
                    </Box>
                    <Box
                      sx={{
                        display: "flex",
                        flexDirection: "row",
                        alignItems: "center",
                        gap: 1,
                        justifyContent: "space-between",
                        flexGrow: 1,
                      }}
                    >
                      <Typography
                        variant="h6"
                        sx={{
                          whiteSpace: "nowrap",
                          width: "50px",
                          fontSize: "1.25rem",
                          color:
                            game.result?.allied > game.result?.axis
                              ? "success.main"
                              : game.result?.allied < game.result?.axis
                              ? "error.main"
                              : "text.primary",
                        }}
                      >
                        {game.result?.allied ?? "?"} -{" "}
                        {game.result?.axis ?? "?"}
                      </Typography>
                      <Typography
                        sx={{
                          color: (theme) => getDurationColor(duration),
                          fontWeight: 500,
                          width: "70px",
                        }}
                      >
                        {duration
                          ? `${duration} min`
                          : t("dashboard.inProgress")}
                      </Typography>
                    </Box>
                  </Box>
                </ListItemButton>
              </ListItem>
            );
          })}
        </List>
      </CardContent>
    </Card>
  );
};

export default GamesCard;
