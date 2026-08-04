import Divider from "@mui/material/Divider";
import Drawer, { drawerClasses } from "@mui/material/Drawer";
import Stack from "@mui/material/Stack";
import MenuContent from "./MenuContent";
import SelectContent from "./SelectContent";
import { Box, List } from "@mui/material";
import { navMenus } from "../Header/nav-data";
import ConnectionStatus from "./sidebar/ConnectionStatus";
import AboutDialog from "./sidebar/About";
import { UserActions } from "./sidebar/UserActions";
import SystemUsage from "./sidebar/SystemUsage";
import FrontlineBrand from "./FrontlineBrand";
import LanguageSelector from "./LanguageSelector";

const MobileDrawer = ({ open, toggleDrawer, children }) => {
  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={toggleDrawer}
      sx={{
        zIndex: (theme) => theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          backgroundImage: "none",
          backgroundColor: "background.paper",
          minWidth: 240,
          width: { xs: "100%", sm: "auto" },
        },
      }}
    >
      <Stack sx={{ height: "100%" }}>{children}</Stack>
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
      <MenuContent navigationTree={navMenus} isMobile={true} />
      <List dense sx={{ color: theme => theme.palette.text.secondary }}>
        <AboutDialog />
      </List>
      <Stack direction="row" sx={{ gap: 1, px: 1.5, py: 0.5 }}>
        <LanguageSelector />
      </Stack>
      <Divider />
      <UserActions />
    </MobileDrawer>
  );
}

export default AdminSideMenuMobile;
