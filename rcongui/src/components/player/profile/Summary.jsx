import { Box, Typography, Divider, Stack } from "@mui/material";
import dayjs from "dayjs";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Chip } from "@mui/material";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium";
import PersonIcon from "@mui/icons-material/Person";
import FlagIcon from "@mui/icons-material/Flag";
import FlagList from "./FlagList";
import WatchlistList from "./WatchlistList";
import VipList from "./VipList";
import { useTranslation } from "react-i18next";

const PlayerProfileSummary = ({
  firstSeen,
  lastSeen,
  vip,
  otherVips,
  sessionCount,
  flags,
  totalPlaytime,
  names,
  watchlist,
  player,
  compact = false,
}) => {
  const { t } = useTranslation();
  return (
    <Stack
      spacing={compact ? 1.5 : 3}
      sx={
        compact
          ? {
              "& .MuiTypography-h6": {
                fontSize: "0.875rem",
                lineHeight: 1.5,
                letterSpacing: "0.03em",
              },
              "& .MuiTypography-h6 > .MuiSvgIcon-root": {
                fontSize: "1.125rem",
                color: "text.secondary",
              },
              "& .MuiTypography-body1": {
                fontSize: "0.8125rem",
                lineHeight: 1.6,
              },
            }
          : undefined
      }
    >
      <Box
        component="section"
        sx={
          compact
            ? {
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: 1,
              }
            : undefined
        }
      >
        <Typography
          variant="h6"
          sx={{
            mb: compact ? 0 : 1,
            display: "flex",
            alignItems: "center",
            gap: 1,
          }}
        >
          <FlagIcon /> {t("playerDrawer.summary.flags")}
        </Typography>
        <FlagList player={player} flags={flags} />
      </Box>

      <Divider />

      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
        >
          <CalendarTodayIcon /> {t("playerDrawer.summary.activity")}
        </Typography>
        {compact ? (
          <>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: "repeat(2, minmax(0, 1fr))",
                gap: 1,
                mb: 1.5,
              }}
            >
              {[
                [t("playerDrawer.summary.visits"), sessionCount],
                [
                  t("playerDrawer.summary.playtime"),
                  `${Math.floor(totalPlaytime / 3600)} ${t(
                    "playerDrawer.summary.hours"
                  )}`,
                ],
              ].map(([label, value]) => (
                <Box
                  key={label}
                  sx={{
                    px: 1.25,
                    py: 1,
                    bgcolor: "action.hover",
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <Typography variant="caption" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography sx={{ fontWeight: 600 }}>{value}</Typography>
                </Box>
              ))}
            </Box>
            <Box
              component="dl"
              sx={{
                display: "grid",
                gridTemplateColumns: "auto minmax(0, 1fr)",
                gap: 0.5,
                columnGap: 1.5,
                m: 0,
              }}
            >
              {[
                [t("playerDrawer.summary.firstSeen"), firstSeen],
                [t("playerDrawer.summary.lastSeen"), lastSeen],
              ].map(([label, value]) => (
                <Box key={label} sx={{ display: "contents" }}>
                  <Typography component="dt" color="text.secondary">
                    {label}
                  </Typography>
                  <Typography
                    component="dd"
                    sx={{ m: 0, textAlign: "right", overflowWrap: "anywhere" }}
                  >
                    {dayjs(value).format("LLL")}
                  </Typography>
                </Box>
              ))}
            </Box>
          </>
        ) : (
          <Stack spacing={0.5}>
            <Typography>
              {t("playerDrawer.summary.firstSeen")}:{" "}
              {dayjs(firstSeen).format("LLL")}
            </Typography>
            <Typography>
              {t("playerDrawer.summary.lastSeen")}:{" "}
              {dayjs(lastSeen).format("LLL")}
            </Typography>
            <Typography>
              {t("playerDrawer.summary.visits")}: {sessionCount}
            </Typography>
            <Typography>
              {t("playerDrawer.summary.playtime")}:{" "}
              {Math.floor(totalPlaytime / 3600)}{" "}
              {t("playerDrawer.summary.hours")}
            </Typography>
          </Stack>
        )}
      </Box>

      <Divider />

      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
        >
          <WorkspacePremiumIcon /> {t("playerDrawer.summary.vipStatus")}
        </Typography>
        <VipList vip={vip} otherVips={otherVips} />
      </Box>

      <Divider />

      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
        >
          <VisibilityIcon /> {t("playerDrawer.summary.watchlist")}
        </Typography>
        <WatchlistList watchlist={watchlist} />
      </Box>

      <Divider />

      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
        >
          <PersonIcon /> {t("playerDrawer.summary.aliases")}
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          {names?.map((nameObj, index) => (
            <Chip
              key={nameObj.id ?? `${nameObj.name}-${index}`}
              label={nameObj.name}
              variant="outlined"
              size="small"
            />
          ))}
        </Box>
      </Box>
    </Stack>
  );
};

export default PlayerProfileSummary;
