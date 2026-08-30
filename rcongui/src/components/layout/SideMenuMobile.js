import Divider from "@mui/material/Divider";
import Drawer, { drawerClasses } from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import MenuContent from "./MenuContent";
import SelectContent from "./SelectContent";
import { Box, IconButton, List } from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import ConnectionStatus from "./sidebar/ConnectionStatus";
import AboutDialog from "./sidebar/About";
import { UserActions } from "./sidebar/UserActions";
import SystemUsage from "./sidebar/SystemUsage";
import FrontlineBrand from "./FrontlineBrand";
import LanguageSelector from "./LanguageSelector";
import { useTranslation } from "react-i18next";
import { useLocation } from "react-router-dom";
import { useAuth } from "@/hooks/useAuth";
import { buildCommandRailWorkspaces } from "./navigation/command-rail-navigation";
import { getContextNavigationSurface } from "./navigation/navigation-surfaces";

const MobileDrawer = ({ open, toggleDrawer, children }) => {
  const { t } = useTranslation();

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={toggleDrawer}
      PaperProps={{
        id: "mobile-primary-navigation",
        component: "nav",
        "aria-label": t("navigation.primary"),
      }}
      sx={(theme) => ({
        zIndex: theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          ...getContextNavigationSurface(theme),
          minWidth: 240,
          width: { xs: "100%", sm: "auto" },
          pt: "env(safe-area-inset-top)",
          pb: "env(safe-area-inset-bottom)",
          pl: "env(safe-area-inset-left)",
          pr: "env(safe-area-inset-right)",
        },
      })}
    >
      <Stack sx={{ height: "100%" }}>
        <IconButton
          aria-label={t("common.close")}
          onClick={toggleDrawer}
          sx={{
            alignSelf: "flex-end",
            display: { xs: "inline-flex", sm: "none" },
            minHeight: 44,
            minWidth: 44,
            mr: 0.5,
          }}
        >
          <CloseRoundedIcon />
        </IconButton>
        {children}
      </Stack>
    </Drawer>
  );
};

function AdminSideMenuMobile({ open, toggleDrawer }) {
  const { permissions } = useAuth();
  const location = useLocation();
  const mobileNavigationTree = buildCommandRailWorkspaces({
    pathname: location.pathname,
    permissions,
    includeLocked: true,
  }).map((workspace) => ({
    id: workspace.id,
    name: workspace.id,
    translationKey: workspace.labelTranslationKey,
    icon: workspace.icon,
    links: workspace.links,
  }));

  return (
    <MobileDrawer open={open} toggleDrawer={toggleDrawer}>
      <FrontlineBrand />
      <Box sx={{ px: 1.5, pb: 1 }}>
        <SelectContent />
      </Box>
      <Divider />
      <MenuContent
        navigationTree={mobileNavigationTree}
        isMobile={true}
        onNavigate={toggleDrawer}
      />
      <Divider />
      <List
        dense
        sx={{ color: (theme) => theme.palette.text.secondary, px: 1.25 }}
      >
        <ConnectionStatus />
        <SystemUsage />
      </List>
      <List dense sx={{ color: (theme) => theme.palette.text.secondary }}>
        <AboutDialog />
      </List>
      <Stack direction="row" sx={{ gap: 1, px: 1.5, py: 0.5 }}>
        <LanguageSelector touchSafe />
      </Stack>
      <Divider />
      <UserActions />
    </MobileDrawer>
  );
}

export default AdminSideMenuMobile;
