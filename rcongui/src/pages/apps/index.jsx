import {
  LaptopWindows as LaptopWindowsIcon,
  PhoneAndroid as PhoneAndroidIcon,
  QrCode2 as QrCodeIcon,
  Security as SecurityIcon,
} from "@mui/icons-material";
import { Box, Button, Card, CardContent, Chip, Grid2 as Grid, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import CrconAppSettings from "@/pages/settings/general-group/crcon-app";

const FrontlineAppsPage = () => {
  const { t } = useTranslation();

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
        <Grid size={{ xs: 12, lg: 8 }}>
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
                  <Chip icon={<LaptopWindowsIcon />} label={t("apps.frontline.devices")} />
                </Stack>

                <Typography variant="body2" color="text.secondary">
                  {t("apps.frontline.detail")}
                </Typography>

                <Stack direction={{ xs: "column", sm: "row" }} spacing={1.25}>
                  <Button component="a" href="https://webapp.fln.gg" target="_blank" rel="noreferrer" variant="outlined">
                    {t("apps.frontline.open")}
                  </Button>
                </Stack>
              </Stack>
            </CardContent>
          </Card>
        </Grid>
        <Grid size={{ xs: 12, lg: 4 }}>
          <Card sx={{ height: "100%" }}>
            <CardContent sx={{ p: { xs: 2.5, md: 3 } }}>
              <Stack spacing={1.25}>
                <Typography variant="h6">{t("apps.how.title")}</Typography>
                {["one", "two", "three"].map((step, index) => (
                  <Stack key={step} direction="row" spacing={1.25} alignItems="flex-start">
                    <Box sx={{ display: "grid", placeItems: "center", flex: "0 0 auto", width: 24, height: 24, borderRadius: "50%", bgcolor: "primary.main", color: "primary.contrastText", fontSize: 13, fontWeight: 700 }}>
                      {index + 1}
                    </Box>
                    <Typography variant="body2" color="text.secondary">{t(`apps.how.${step}`)}</Typography>
                  </Stack>
                ))}
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
