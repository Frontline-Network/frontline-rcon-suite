import { Box, Stack, Tabs, Typography } from "@mui/material";
import BallotOutlinedIcon from "@mui/icons-material/BallotOutlined";
import HowToVoteOutlinedIcon from "@mui/icons-material/HowToVoteOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";

function VotemapPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const { permissions } = useAuth();
  const fakeMode = isFakeMode();
  const granted = new Set(
    (permissions?.permissions ?? []).map((entry) =>
      typeof entry === "string" ? entry : entry.permission
    )
  );
  const canView = (requiredPermissions) =>
    fakeMode ||
    permissions?.is_superuser ||
    requiredPermissions.every((permission) => granted.has(permission));
  const tabs = [
    {
      label: t("maps.votemapWorkbench.liveTab"),
      description: t("maps.votemapWorkbench.liveTabDescription"),
      href: "/settings/maps/votemap",
      icon: <HowToVoteOutlinedIcon fontSize="small" />,
      permissions: ["can_view_votemap_status"],
    },
    {
      label: t("maps.votemapWorkbench.poolTab"),
      description: t("maps.votemapWorkbench.poolTabDescription"),
      href: "/settings/maps/votemap/whitelist",
      icon: <BallotOutlinedIcon fontSize="small" />,
      permissions: ["can_view_map_whitelist", "can_view_all_maps"],
    },
    {
      label: t("maps.votemapWorkbench.settingsTab"),
      description: t("maps.votemapWorkbench.settingsTabDescription"),
      href: "/settings/maps/votemap/settings",
      icon: <TuneOutlinedIcon fontSize="small" />,
      permissions: ["can_view_votemap_config"],
    },
  ].filter(({ permissions: requiredPermissions }) =>
    canView(requiredPermissions)
  );
  const activeHref = location.pathname.endsWith("/whitelist")
    ? "/settings/maps/votemap/whitelist"
    : location.pathname.endsWith("/settings")
    ? "/settings/maps/votemap/settings"
    : "/settings/maps/votemap";
  const activeTab = tabs.findIndex(({ href }) => href === activeHref);

  return (
    <Box
      data-testid="votemap-workbench"
      sx={{
        width: "auto",
        minWidth: 0,
        maxWidth: 1540,
        mx: "auto",
        pb: 3,
        "& .MuiButton-root, & .MuiIconButton-root, & .MuiChip-root, & .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline, & .MuiFilledInput-root, & .MuiPaper-root":
          {
            borderRadius: 0,
          },
      }}
    >
      <Box component="header" sx={{ mb: 1.5 }}>
        <Typography
          variant="overline"
          color="primary.main"
          sx={{ display: "block", letterSpacing: "0.08em", mb: 0.25 }}
        >
          {t("maps.votemapWorkbench.eyebrow")}
        </Typography>
        <Typography component="h1" variant="h4" fontWeight={850}>
          {t("maps.votemap")}
        </Typography>
        <Typography
          variant="body2"
          color="text.secondary"
          sx={{ mt: 0.5, maxWidth: 880 }}
        >
          {t("maps.votemapWorkbench.subtitle")}
        </Typography>
      </Box>

      <Box
        component="nav"
        aria-label={t("maps.votemapWorkbench.navigation")}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          overflowX: "auto",
          scrollbarWidth: "thin",
        }}
      >
        <Tabs
          aria-label={t("maps.votemapWorkbench.navigation")}
          value={activeTab >= 0 ? activeTab : false}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            minHeight: 62,
            "& .MuiTabs-indicator": { height: 2 },
            "& .MuiTab-root": {
              minHeight: 62,
              minWidth: { xs: 158, md: 220 },
              alignItems: "flex-start",
              borderRight: "1px solid",
              borderColor: "divider",
              px: 2,
              py: 1.15,
            },
          }}
        >
          {tabs.map(({ href, label, description, icon }) => (
            <NavLinkTab
              key={href}
              to={href}
              icon={icon}
              iconPosition="start"
              label={
                <Stack alignItems="flex-start" sx={{ minWidth: 0 }}>
                  <Typography variant="body2" fontWeight={800} noWrap>
                    {label}
                  </Typography>
                  <Typography
                    variant="caption"
                    color="text.secondary"
                    noWrap
                    sx={{ display: { xs: "none", sm: "block" } }}
                  >
                    {description}
                  </Typography>
                </Stack>
              }
            />
          ))}
        </Tabs>
      </Box>

      <Box
        sx={{
          mt: 1.25,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          minWidth: 0,
        }}
      >
        <Outlet />
      </Box>
    </Box>
  );
}

export default VotemapPage;
