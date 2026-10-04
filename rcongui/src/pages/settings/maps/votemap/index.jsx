import {
  Box,
  Stack,
  Tabs,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import BallotOutlinedIcon from "@mui/icons-material/BallotOutlined";
import HowToVoteOutlinedIcon from "@mui/icons-material/HowToVoteOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import { Outlet, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { NavLinkTab } from "@/components/shared/NavLinkTab";
import { useAuth } from "@/hooks/useAuth";
import { isFakeMode } from "@/mirage/demo-data";
import PageHeader from "@/components/shared/PageHeader";

function VotemapPage() {
  const { t } = useTranslation();
  const location = useLocation();
  const theme = useTheme();
  const mobile = useMediaQuery(theme.breakpoints.down("md"));
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
      mobileLabel: t("navigation.workspaces.live"),
      description: t("maps.votemapWorkbench.liveTabDescription"),
      href: "/settings/maps/votemap",
      icon: <HowToVoteOutlinedIcon fontSize="small" />,
      permissions: ["can_view_votemap_status"],
    },
    {
      label: t("maps.votemapWorkbench.poolTab"),
      mobileLabel: t("maps.votemapWorkbench.poolTab"),
      description: t("maps.votemapWorkbench.poolTabDescription"),
      href: "/settings/maps/votemap/whitelist",
      icon: <BallotOutlinedIcon fontSize="small" />,
      permissions: ["can_view_map_whitelist", "can_view_all_maps"],
    },
    {
      label: t("maps.votemapWorkbench.settingsTab"),
      mobileLabel: t("maps.votemapWorkbench.settingsTab"),
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
        width: "100%",
        boxSizing: "border-box",
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
      <PageHeader
        eyebrow={t("maps.votemapWorkbench.eyebrow")}
        title={t("maps.votemap")}
        subtitle={t("maps.votemapWorkbench.subtitle")}
      />

      <Box data-theme-surface="panel"
        component="nav"
        className="wardogs-page-tabs"
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
          variant={mobile ? "fullWidth" : "scrollable"}
          scrollButtons={mobile ? false : "auto"}
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
              px: { xs: 0.75, sm: 2 },
              py: 1.15,
              boxSizing: "border-box",
            },
          }}
        >
          {tabs.map(({ href, label, mobileLabel, description, icon }) => (
            <NavLinkTab
              key={href}
              to={href}
              icon={icon}
              iconPosition="start"
              label={
                <Stack
                  alignItems="flex-start"
                  sx={{ minWidth: 0, width: "100%", overflow: "hidden" }}
                >
                  <Typography
                    variant="body2"
                    fontWeight={800}
                    noWrap
                    sx={{
                      width: "100%",
                      maxWidth: "100%",
                      fontSize: { xs: "0.72rem", sm: "0.875rem" },
                    }}
                  >
                    {mobile ? mobileLabel : label}
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

      <Box data-theme-surface="panel"
        className="wardogs-map-workspace"
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
