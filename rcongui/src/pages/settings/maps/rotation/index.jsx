import { Box, Stack, Tabs, Typography } from "@mui/material";
import FormatListNumberedIcon from "@mui/icons-material/FormatListNumbered";
import RouteOutlinedIcon from "@mui/icons-material/RouteOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { NavLinkTab } from "@/components/shared/NavLinkTab";
import PageHeader from "@/components/shared/PageHeader";

function MapRotation() {
  const { t } = useTranslation();
  const location = useLocation();
  const tabs = [
    {
      href: "/settings/maps/rotation",
      to: "",
      label: t("maps.builder"),
      description: t("maps.rotationWorkbench.builderTabDescription"),
      icon: <RouteOutlinedIcon fontSize="small" />,
    },
    {
      href: "/settings/maps/rotation/sequence",
      to: "sequence",
      label: t("maps.sequence"),
      description: t("maps.rotationWorkbench.sequenceTabDescription"),
      icon: <FormatListNumberedIcon fontSize="small" />,
    },
    {
      href: "/settings/maps/rotation/settings",
      to: "settings",
      label: t("maps.settings"),
      description: t("maps.rotationWorkbench.settingsTabDescription"),
      icon: <TuneOutlinedIcon fontSize="small" />,
    },
  ];
  const activeHref = location.pathname.endsWith("/sequence")
    ? "/settings/maps/rotation/sequence"
    : location.pathname.endsWith("/settings")
    ? "/settings/maps/rotation/settings"
    : "/settings/maps/rotation";
  const activeTab = tabs.findIndex(({ href }) => href === activeHref);

  return (
    <Box
      data-testid="map-rotation-workbench"
      sx={{
        width: "100%",
        maxWidth: "100%",
        boxSizing: "border-box",
        minWidth: 0,
        "@media (min-width: 1600px)": { maxWidth: 1540 },
        mx: "auto",
        pb: 3,
        "& .MuiButton-root, & .MuiIconButton-root, & .MuiChip-root, & .MuiToggleButton-root, & .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline, & .MuiPaper-root":
          { borderRadius: 0 },
      }}
    >
      <PageHeader
        eyebrow={t("maps.rotationWorkbench.eyebrow")}
        title={t("maps.rotation")}
        subtitle={t("maps.rotationWorkbench.subtitle")}
      />

      <Box
        component="nav"
        aria-label={t("maps.rotationWorkbench.navigation")}
        sx={{
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          overflowX: "auto",
          scrollbarWidth: "thin",
        }}
      >
        <Tabs
          value={activeTab}
          aria-label={t("maps.rotationWorkbench.navigation")}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          sx={{
            minHeight: 62,
            "& .MuiTabs-indicator": { height: 2 },
            "& .MuiTabs-list": { width: { xs: "100%", md: "auto" } },
            "& .MuiTabs-scrollButtons": {
              display: { xs: "none", md: "inline-flex" },
            },
            "& .MuiTab-iconWrapper": {
              display: { xs: "none", sm: "inline-flex" },
            },
            "& .MuiTab-root": {
              minHeight: 62,
              minWidth: { xs: 0, md: 220 },
              flex: { xs: "0 0 33.333%", md: "0 0 auto" },
              alignItems: "flex-start",
              borderRight: "1px solid",
              borderColor: "divider",
              px: { xs: 1, md: 2 },
              py: 1.15,
            },
          }}
        >
          {tabs.map(({ href, to, label, description, icon }) => (
            <NavLinkTab
              key={href}
              to={to}
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

export default MapRotation;
