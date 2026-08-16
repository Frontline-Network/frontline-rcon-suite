import {
  AutoAwesome as AiIcon,
  Forum as ForumIcon,
  Language as LanguageIcon,
  PhoneAndroid as PhoneAndroidIcon,
  QrCode2 as QrCodeIcon,
  Security as SecurityIcon,
  SmartToy as DiscordBotIcon,
} from "@mui/icons-material";
import { Box, Button, Card, CardContent, Chip, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { Link as RouterLink } from "react-router-dom";
import CrconAppSettings from "@/pages/settings/general-group/crcon-app";

const FrontlineAppsPage = () => {
  const { t } = useTranslation();
  const companionUrl = "https://webapp.fln.gg";

  return (
    <Box sx={{ py: { xs: 2, md: 2.5 } }}>
      <Typography variant="overline" color="primary.main" sx={{ fontWeight: 700 }}>
        {t("apps.eyebrow")}
      </Typography>
      <Typography variant="h3" sx={{ textTransform: "uppercase" }}>
        {t("apps.title")}
      </Typography>
      <Typography color="text.secondary" sx={{ mt: 0.5, maxWidth: 720 }}>
        {t("apps.subtitle")}
      </Typography>

      <Grid container spacing={2} sx={{ mt: 2.5 }}>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card
            sx={(theme) => ({
              height: "100%",
              border: "1px solid",
              borderColor: "primary.main",
              background: `linear-gradient(125deg, ${theme.palette.background.paper} 0%, ${theme.palette.action.hover} 100%)`,
            })}
          >
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack spacing={2.5}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Box sx={{ display: "grid", placeItems: "center", width: 52, height: 52, borderRadius: 2, bgcolor: "primary.main", color: "primary.contrastText" }}>
                    <PhoneAndroidIcon fontSize="large" />
                  </Box>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>{t("apps.frontline.title")}</Typography>
                    <Typography color="text.secondary">{t("apps.frontline.description")}</Typography>
                  </Box>
                </Stack>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} useFlexGap flexWrap="wrap">
                  <Chip icon={<SecurityIcon />} label={t("apps.frontline.security")} />
                  <Chip icon={<QrCodeIcon />} label={t("apps.frontline.qr")} />
                  <Chip icon={<LanguageIcon />} label={t("apps.frontline.devices")} />
                </Stack>

                <Typography variant="body2" color="text.secondary">
                  {t("apps.frontline.detail")}
                </Typography>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                  <Button component="a" href="#frontline-pairing" variant="contained">
                    {t("apps.frontline.setup")}
                  </Button>
                  <Button component="a" href={companionUrl} target="_blank" rel="noreferrer" variant="outlined">
                    {t("apps.frontline.open")}
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 6 }}>
          <Card
            sx={{
              height: "100%",
              border: "1px solid rgba(88, 101, 242, 0.65)",
              background: "linear-gradient(135deg, rgba(88, 101, 242, 0.2) 0%, rgba(88, 101, 242, 0.04) 70%)",
            }}
          >
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack spacing={2.5}>
                <Stack direction="row" spacing={1.5} alignItems="center">
                  <Box sx={{ display: "grid", placeItems: "center", width: 52, height: 52, borderRadius: 2, bgcolor: "#5865F2", color: "white" }}>
                    <DiscordBotIcon fontSize="large" />
                  </Box>
                  <Box>
                    <Typography variant="h4" sx={{ fontWeight: 700 }}>{t("apps.discord.title")}</Typography>
                    <Typography color="text.secondary">{t("apps.discord.description")}</Typography>
                  </Box>
                </Stack>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1} useFlexGap flexWrap="wrap">
                  <Chip icon={<ForumIcon />} label={t("apps.discord.reports")} />
                  <Chip icon={<SecurityIcon />} label={t("apps.discord.permissions")} />
                  <Chip icon={<AiIcon />} label={t("apps.discord.ai")} />
                </Stack>

                <Typography variant="body2" color="text.secondary">
                  {t("apps.discord.detail")}
                </Typography>

                <Button
                  component={RouterLink}
                  to="/apps/discord-report-bot"
                  variant="contained"
                  sx={{ alignSelf: "flex-start", bgcolor: "#5865F2", "&:hover": { bgcolor: "#4752C4" } }}
                >
                  {t("apps.discord.setup")}
                </Button>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
      </Grid>
      <Box id="frontline-pairing" sx={{ mt: 3 }}>
        <CrconAppSettings showUtilities={false} frontlinePresentation />
      </Box>
    </Box>
  );
};

export default FrontlineAppsPage;
