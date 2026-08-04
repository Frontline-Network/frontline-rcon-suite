import { styled } from "@mui/material/styles";
import MuiDrawer, { drawerClasses } from "@mui/material/Drawer";
import Box from "@mui/material/Box";
import Divider from "@mui/material/Divider";
import SelectContent from "./SelectContent";
import MenuContent from "./MenuContent";
import { navMenus } from "../Header/nav-data";
import { List, ListItem, ListItemText } from "@mui/material";
import ConnectionStatus from "./sidebar/ConnectionStatus";
import AboutDialog from "./sidebar/About";
import { useAppStore } from "@/stores/app-state";
import { UserActions } from "./sidebar/UserActions";
import SystemUsage from "./sidebar/SystemUsage";
import FrontlineBrand from "./FrontlineBrand";
import { Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

const drawerWidth = 252;

const Drawer = styled(MuiDrawer, {
  shouldForwardProp: (prop) => prop !== "open",
})(({ open }) => ({
  width: drawerWidth,
  flexShrink: 0,
  boxSizing: "border-box",
  mt: 10,
  [`& .${drawerClasses.paper}`]: {
    width: drawerWidth,
    boxSizing: "border-box",
    ...(!open && {
      width: 0,
    }),
  },
}));

export const MenuDrawer = ({ open, children }) => {
  return (
    <Drawer
      variant="permanent"
      open={open}
      sx={{
        width: open ? drawerWidth : 0,
        display: { xs: "none", lg: "block" },
        [`& .${drawerClasses.paper}`]: {
          backgroundColor: "background.paper",
          borderRightColor: "divider",
        },
      }}
    >
      {children}
    </Drawer>
  );
};

export default function SideMenu() {
  const openDrawer = useAppStore((state) => state.openDrawer);
  const { t } = useTranslation();

  return (
    <MenuDrawer open={openDrawer}>
      <FrontlineBrand />
      <Box sx={{ px: 2, pb: 1.5 }}>
        <Typography variant="caption" color="primary.light" sx={{ textTransform: "uppercase" }}>
          {t("sidebar.server")}
        </Typography>
        <Box sx={{ mt: 0.75 }}>
          <SelectContent />
        </Box>
      </Box>
      <List dense disablePadding sx={{ color: theme => theme.palette.text.secondary, px: 1.25 }}>
        <ConnectionStatus />
        <SystemUsage />
      </List>
      <Divider />
      <MenuContent navigationTree={navMenus} />
      <Divider />
      <List dense disablePadding sx={{ color: theme => theme.palette.text.secondary, px: 1.25 }}>
        <AboutDialog />
      </List>
      <UserActions />
    </MenuDrawer>
  );
}
