import { Box, Card, CardActionArea, CardContent, Grid, Stack, Typography } from "@mui/material";
import GroupsRoundedIcon from "@mui/icons-material/GroupsRounded";
import MapRoundedIcon from "@mui/icons-material/MapRounded";
import BalanceRoundedIcon from "@mui/icons-material/BalanceRounded";
import SmartToyRoundedIcon from "@mui/icons-material/SmartToyRounded";
import DnsRoundedIcon from "@mui/icons-material/DnsRounded";
import SettingsRoundedIcon from "@mui/icons-material/SettingsRounded";
import ChevronRightRoundedIcon from "@mui/icons-material/ChevronRightRounded";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

const destinations = [
  { key: "teams", to: "/views/team", icon: GroupsRoundedIcon, tone: "info.main" },
  { key: "maps", to: "/settings/maps/change", icon: MapRoundedIcon, tone: "primary.main" },
  { key: "balance", to: "/views/autobalancer", icon: BalanceRoundedIcon, tone: "success.main" },
  { key: "automation", to: "/settings/autosettings", icon: SmartToyRoundedIcon, tone: "warning.main" },
  { key: "services", to: "/settings/services", icon: DnsRoundedIcon, tone: "success.main" },
  { key: "settings", to: "/settings/general", icon: SettingsRoundedIcon, tone: "text.secondary" },
];

export default function MobileOperationsHub() {
  const { t } = useTranslation();

  return (
    <Box component="section" aria-labelledby="mobile-operations-title" sx={{ pb: 2 }}>
      <Stack spacing={0.5} sx={{ mb: 2 }}>
        <Typography color="primary.light" variant="overline">
          {t("mobileOperations.eyebrow")}
        </Typography>
        <Typography id="mobile-operations-title" component="h1" variant="h4">
          {t("mobileOperations.title")}
        </Typography>
        <Typography color="text.secondary" variant="body2">
          {t("mobileOperations.subtitle")}
        </Typography>
      </Stack>

      <Grid container spacing={1.25}>
        {destinations.map(({ key, to, icon: Icon, tone }) => (
          <Grid key={key} item xs={12} sm={6}>
            <Card variant="outlined" sx={{ height: "100%", borderRadius: 0 }}>
              <CardActionArea
                component={Link}
                to={to}
                sx={{ height: "100%", minHeight: { xs: 82, sm: 96 }, p: 0 }}
              >
                <CardContent
                  sx={{
                    alignItems: "center",
                    display: "flex",
                    gap: 1.25,
                    minHeight: "inherit",
                    p: 1.25,
                    "&:last-child": { pb: 1.25 },
                  }}
                >
                  <Box
                    aria-hidden="true"
                    sx={{
                      alignItems: "center",
                      border: "1px solid",
                      borderColor: "divider",
                      color: tone,
                      display: "flex",
                      flex: "0 0 auto",
                      height: 44,
                      justifyContent: "center",
                      width: 44,
                    }}
                  >
                    <Icon />
                  </Box>
                  <Box sx={{ flexGrow: 1, minWidth: 0 }}>
                    <Typography component="h2" variant="subtitle1">
                      {t(`mobileOperations.cards.${key}.title`)}
                    </Typography>
                    <Typography
                      color="text.secondary"
                      variant="body2"
                      sx={{
                        display: "-webkit-box",
                        WebkitBoxOrient: "vertical",
                        WebkitLineClamp: { xs: 1, sm: 2 },
                        overflow: "hidden",
                      }}
                    >
                      {t(`mobileOperations.cards.${key}.description`)}
                    </Typography>
                  </Box>
                  <ChevronRightRoundedIcon aria-hidden="true" color="disabled" />
                </CardContent>
              </CardActionArea>
            </Card>
          </Grid>
        ))}
      </Grid>
    </Box>
  );
}
