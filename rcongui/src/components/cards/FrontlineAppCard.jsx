import {
  ArrowForward as ArrowForwardIcon,
  PhoneAndroid as PhoneAndroidIcon,
  QrCode2 as QrCodeIcon,
} from "@mui/icons-material";
import { Box, Button, Card, CardContent, Stack, Typography } from "@mui/material";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const FrontlineAppCard = () => {
  const { t } = useTranslation();

  return (
    <Card
      sx={(theme) => ({
        height: "100%",
        border: "1px solid",
        borderColor: "primary.main",
        background: `linear-gradient(115deg, ${theme.palette.background.paper} 0%, ${theme.palette.action.hover} 100%)`,
      })}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 }, "&:last-child": { pb: { xs: 2, md: 2.5 } } }}>
        <Stack direction={{ xs: "column", md: "row" }} spacing={2} alignItems={{ md: "center" }} justifyContent="space-between">
          <Stack direction="row" spacing={2} alignItems="center">
            <Box
              sx={(theme) => ({
                display: "grid",
                placeItems: "center",
                width: 48,
                height: 48,
                borderRadius: 2,
                color: "primary.contrastText",
                bgcolor: "primary.main",
                boxShadow: `0 8px 22px ${theme.palette.primary.main}40`,
              })}
            >
              <PhoneAndroidIcon />
            </Box>
            <Box>
              <Typography variant="overline" color="primary.main" sx={{ fontWeight: 700, lineHeight: 1 }}>
                {t("dashboard.frontlineApp.eyebrow")}
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {t("dashboard.frontlineApp.title")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("dashboard.frontlineApp.description")}
              </Typography>
            </Box>
          </Stack>
          <Button component={Link} to="/apps" variant="contained" endIcon={<ArrowForwardIcon />}>
            {t("dashboard.frontlineApp.action")}
          </Button>
        </Stack>
        <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mt: 2, color: "text.secondary" }}>
          <QrCodeIcon fontSize="small" />
          <Typography variant="caption">{t("dashboard.frontlineApp.hint")}</Typography>
        </Stack>
      </CardContent>
    </Card>
  );
};

export default FrontlineAppCard;
