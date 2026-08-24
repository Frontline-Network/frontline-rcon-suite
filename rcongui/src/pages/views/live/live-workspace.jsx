import {
  AssessmentOutlined,
  GroupsRounded,
  MapRounded,
  TableChartOutlined,
  TimerOutlined,
  WifiRounded,
} from "@mui/icons-material";
import {
  Box,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import { useTranslation } from "react-i18next";

const Metric = ({ icon, label, value }) => (
  <Stack
    direction="row"
    alignItems="center"
    spacing={0.75}
    sx={{ minWidth: 0, whiteSpace: "nowrap" }}
  >
    <Box sx={{ color: "primary.main", display: "grid", placeItems: "center" }}>
      {icon}
    </Box>
    <Box sx={{ minWidth: 0 }}>
      <Typography
        variant="caption"
        sx={{
          color: "text.secondary",
          display: { xs: "none", xl: "block" },
          lineHeight: 1,
        }}
      >
        {label}
      </Typography>
      <Typography variant="subtitle2" noWrap sx={{ lineHeight: 1.25 }}>
        {value}
      </Typography>
    </Box>
  </Stack>
);

export const LiveCommandBar = ({
  gameData,
  playerCount,
  isFetching,
  layoutMode,
  onLayoutModeChange,
  splitDisabled,
}) => {
  const { t } = useTranslation();
  const mapName = gameData?.current_map?.pretty_name ?? "–";
  const timeRemaining = gameData?.raw_time_remaining ?? "--:--:--";

  return (
    <Box
      component="section"
      aria-label={t("views.live.commandBar")}
      sx={(theme) => ({
        border: `1px solid ${theme.palette.divider}`,
        bgcolor: "background.paper",
        mb: 1,
      })}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        alignItems={{ xs: "stretch", md: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{ px: { xs: 1, md: 1.5 }, py: 1 }}
      >
        <Typography variant="h6" sx={{ whiteSpace: "nowrap" }}>
          {t("views.live.title")}
        </Typography>

        <Stack
          direction="row"
          alignItems="center"
          spacing={{ xs: 1.25, lg: 2.25 }}
          sx={{ minWidth: 0, overflowX: "auto", scrollbarWidth: "thin" }}
        >
          <Metric
            icon={<GroupsRounded sx={{ fontSize: "1rem" }} />}
            label={t("views.live.players")}
            value={`${playerCount}/100`}
          />
          <Metric
            icon={<MapRounded sx={{ fontSize: "1rem" }} />}
            label={t("views.live.currentMap")}
            value={mapName}
          />
          <Metric
            icon={<TimerOutlined sx={{ fontSize: "1rem" }} />}
            label={t("views.live.remainingTime")}
            value={timeRemaining}
          />
          <Stack
            direction="row"
            alignItems="center"
            spacing={0.5}
            sx={{ whiteSpace: "nowrap" }}
          >
            <WifiRounded
              sx={{
                color: isFetching ? "warning.main" : "success.main",
                fontSize: "1rem",
              }}
            />
            <Typography
              variant="caption"
              sx={{ color: isFetching ? "warning.light" : "success.light" }}
            >
              {isFetching ? t("views.live.updating") : t("views.live.liveNow")}
            </Typography>
          </Stack>
        </Stack>
      </Stack>

      <ToggleButtonGroup
        value={layoutMode}
        exclusive
        onChange={(_, value) => value && onLayoutModeChange(value)}
        aria-label={t("views.live.layout")}
        size="small"
        sx={(theme) => ({
          borderTop: `1px solid ${theme.palette.divider}`,
          display: "flex",
          px: 1,
          py: 0.75,
          "& .MuiToggleButton-root": {
            border: 0,
            borderRadius: 0,
            gap: 0.75,
            minHeight: 36,
            px: { xs: 1.25, sm: 2.5 },
          },
          "& .Mui-selected": {
            boxShadow: `inset 0 -2px 0 ${theme.palette.primary.main}`,
          },
        })}
      >
        <ToggleButton
          value="split"
          disabled={splitDisabled}
          title={splitDisabled ? t("views.live.splitUnavailable") : undefined}
          aria-describedby={
            splitDisabled ? "live-split-unavailable" : undefined
          }
        >
          <GroupsRounded sx={{ fontSize: "1rem" }} />
          {t("views.live.splitView")}
        </ToggleButton>
        <ToggleButton value="players">
          <TableChartOutlined sx={{ fontSize: "1rem" }} />
          {t("views.live.players")}
        </ToggleButton>
        <ToggleButton value="logs">
          <AssessmentOutlined sx={{ fontSize: "1rem" }} />
          {t("views.live.logs")}
        </ToggleButton>
      </ToggleButtonGroup>
      {splitDisabled ? (
        <Typography
          id="live-split-unavailable"
          sx={{
            position: "absolute",
            width: 1,
            height: 1,
            p: 0,
            m: -1,
            overflow: "hidden",
            clip: "rect(0 0 0 0)",
            whiteSpace: "nowrap",
            border: 0,
          }}
        >
          {t("views.live.splitUnavailable")}
        </Typography>
      ) : null}
    </Box>
  );
};
