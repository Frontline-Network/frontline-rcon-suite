import {
  AutoAwesome as AiIcon,
  Forum as ReportsIcon,
  Security as SecurityIcon,
  SmartToy as DiscordBotIcon,
} from "@mui/icons-material";
import { Box, Chip, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import DiscordReportBotCard from "@/pages/settings/general-group/crcon-app/DiscordReportBotCard";

const DiscordReportBotPage = () => {
  const { t } = useTranslation();

  return (
    <Box sx={{ py: { xs: 2, md: 2.5 }, maxWidth: 1280, mx: "auto" }}>
      <Box
        sx={(theme) => ({
          position: "relative",
          overflow: "hidden",
          p: { xs: 2.5, md: 4 },
          mb: 3,
          borderRadius: 3,
          border: "1px solid",
          borderColor: "rgba(88, 101, 242, 0.55)",
          background: `linear-gradient(125deg, rgba(88, 101, 242, 0.22) 0%, ${theme.palette.background.paper} 62%)`,
          "&::after": {
            content: '""',
            position: "absolute",
            width: 260,
            height: 260,
            borderRadius: "50%",
            right: -90,
            top: -120,
            bgcolor: "rgba(88, 101, 242, 0.14)",
          },
        })}
      >
        <Stack direction={{ xs: "column", sm: "row" }} spacing={2.5} alignItems={{ sm: "center" }}>
          <Box
            sx={{
              display: "grid",
              placeItems: "center",
              width: 68,
              height: 68,
              flex: "0 0 auto",
              borderRadius: 2.5,
              bgcolor: "#5865F2",
              color: "white",
              boxShadow: "0 12px 30px rgba(88, 101, 242, 0.3)",
            }}
          >
            <DiscordBotIcon sx={{ fontSize: 38 }} />
          </Box>
          <Box sx={{ position: "relative", zIndex: 1 }}>
            <Typography variant="overline" color="primary.main" sx={{ fontWeight: 800 }}>
              {t("apps.discord.eyebrow")}
            </Typography>
            <Typography component="h1" variant="h3" sx={{ fontWeight: 800 }}>
              {t("settings.discordReports.title")}
            </Typography>
            <Typography color="text.secondary" sx={{ mt: 0.75, maxWidth: 760 }}>
              {t("apps.discord.pageSubtitle")}
            </Typography>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap" sx={{ mt: 2 }}>
              <Chip icon={<ReportsIcon />} label={t("apps.discord.reports")} />
              <Chip icon={<SecurityIcon />} label={t("apps.discord.permissions")} />
              <Chip icon={<AiIcon />} label={t("apps.discord.ai")} />
            </Stack>
          </Box>
        </Stack>
      </Box>

      <DiscordReportBotCard />
    </Box>
  );
};

export default DiscordReportBotPage;
