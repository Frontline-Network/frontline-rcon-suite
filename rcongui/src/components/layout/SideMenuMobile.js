import Divider from "@mui/material/Divider";
import Drawer, { drawerClasses } from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import MenuContent from "./MenuContent";
import SelectContent from "./SelectContent";
import { Box, IconButton, List } from "@mui/material";
import CloseRoundedIcon from "@mui/icons-material/CloseRounded";
import { navMenus } from "../Header/nav-data";
import ConnectionStatus from "./sidebar/ConnectionStatus";
import AboutDialog from "./sidebar/About";
import { UserActions } from "./sidebar/UserActions";
import SystemUsage from "./sidebar/SystemUsage";
import FrontlineBrand from "./FrontlineBrand";
import LanguageSelector from "./LanguageSelector";
import { useTranslation } from "react-i18next";

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
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          backgroundImage: "none",
          backgroundColor: "background.paper",
          minWidth: 240,
          width: { xs: "100%", sm: "auto" },
          pt: "env(safe-area-inset-top)",
          pb: "env(safe-area-inset-bottom)",
          pl: "env(safe-area-inset-left)",
          pr: "env(safe-area-inset-right)",
        },
      }}
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
  return (
    <MobileDrawer open={open} toggleDrawer={toggleDrawer}>
      <FrontlineBrand />
      <Box sx={{ px: 1.5, pb: 1 }}><SelectContent /></Box>
      <List dense sx={{ color: theme => theme.palette.text.secondary }}>
        <ConnectionStatus />
        <SystemUsage />
      </List>
      <Divider />
      <MenuContent
        navigationTree={navMenus}
        isMobile={true}
        onNavigate={toggleDrawer}
      />
      <List dense sx={{ color: theme => theme.palette.text.secondary }}>
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
