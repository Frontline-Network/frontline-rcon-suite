import Drawer, { drawerClasses } from "@mui/material/Drawer";
import { useTranslation } from "react-i18next";
import { getContextNavigationSurface } from "./navigation/navigation-surfaces";
import MobileCommandNavigation from "./navigation/MobileCommandNavigation";

const MobileDrawer = ({ open, toggleDrawer }) => {
  const { t } = useTranslation();

  return (
    <Drawer
      anchor="left"
      open={open}
      onClose={toggleDrawer}
      PaperProps={{
        id: "mobile-primary-navigation",
        component: "aside",
        "aria-label": t("navigation.primary"),
      }}
      sx={(theme) => ({
        zIndex: theme.zIndex.drawer + 1,
        [`& .${drawerClasses.paper}`]: {
          ...getContextNavigationSurface(theme),
          width: "100vw",
          maxWidth: "100vw",
          overflow: "hidden",
          borderRadius: "0 !important",
          pt: "env(safe-area-inset-top)",
          pb: "env(safe-area-inset-bottom)",
          pl: "env(safe-area-inset-left)",
          pr: "env(safe-area-inset-right)",
        },
      })}
    >
      <MobileCommandNavigation open={open} onClose={toggleDrawer} />
    </Drawer>
  );
};

function AdminSideMenuMobile({ open, toggleDrawer }) {
  return <MobileDrawer open={open} toggleDrawer={toggleDrawer} />;
}

export default AdminSideMenuMobile;
