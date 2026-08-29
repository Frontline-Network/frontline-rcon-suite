import { Box, Typography, Divider, Stack } from "@mui/material";
import dayjs from "dayjs";
import VisibilityIcon from "@mui/icons-material/Visibility";
import { Chip } from "@mui/material";
import CalendarTodayIcon from "@mui/icons-material/CalendarToday";
import WorkspacePremiumIcon from "@mui/icons-material/WorkspacePremium";
import PersonIcon from "@mui/icons-material/Person";
import EmergencyIcon from "@mui/icons-material/Emergency";
import FlagIcon from "@mui/icons-material/Flag";
import FlagList from "./FlagList";
import WatchlistList from "./WatchlistList";
import VipList from "./VipList";
import CopyableText from "@/components/shared/CopyableText";
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
  eosId,
  player,
}) => {
  const { t } = useTranslation();
  return (
    <Stack spacing={3}>
      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
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
            {Math.floor(totalPlaytime / 3600)} {t("playerDrawer.summary.hours")}
          </Typography>
        </Stack>
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

      <Divider />

      <Box component="section">
        <Typography
          variant="h6"
          sx={{ mb: 1, display: "flex", alignItems: "center", gap: 1 }}
        >
          <EmergencyIcon /> EOS ID
        </Typography>
        <Box sx={{ display: "flex", flexWrap: "wrap", gap: 1 }}>
          <CopyableText
            label={eosId ?? t("playerDrawer.summary.unset")}
            text={eosId}
          />
        </Box>
      </Box>
    </Stack>
  );
};

export default PlayerProfileSummary;
