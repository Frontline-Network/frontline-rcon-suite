import { styled } from "@mui/material/styles";
import AppBar from "@mui/material/AppBar";
import Stack from "@mui/material/Stack";
import MuiToolbar from "@mui/material/Toolbar";
import { tabsClasses } from "@mui/material/Tabs";
import MenuRoundedIcon from "@mui/icons-material/MenuRounded";
import SideMenuMobile from "./SideMenuMobile";
import MenuButton from "./MenuButton";
import NavbarBreadcrumbs from "./NavbarBreadcrumbs";
import { useMediaQuery, useTheme } from "@mui/system";
import ServerStatus from "../Header/server-status";
import FrontlineBrand from "./FrontlineBrand";
import { useTranslation } from "react-i18next";
import { useState } from "react";

const Toolbar = styled(MuiToolbar)({
  width: "100%",
  padding: "8px 12px",
  display: "flex",
  flexDirection: "column",
  alignItems: "start",
  justifyContent: "center",
  gap: "8px",
  flexShrink: 0,
  [`& ${tabsClasses.flexContainer}`]: {
    gap: "8px",
    p: "8px",
    pb: 0,
  },
});

const AppNavbarBase = ({ toggleDrawer, open, isSmallScreen }) => {
  const { t } = useTranslation();

  return (
    <AppBar
      position="fixed"
      sx={{
        display: { xs: "auto", lg: "none" },
        boxShadow: 0,
        bgcolor: "background.paper",
        backgroundImage: "none",
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Toolbar variant="regular">
        <Stack
          direction="row"
          sx={{
            alignItems: "center",
            flexGrow: 1,
            width: "100%",
          }}
        >
          <MenuButton aria-label={t("navigation.openMenu")} onClick={toggleDrawer}>
            <MenuRoundedIcon />
          </MenuButton>
          <FrontlineBrand compact />
          <Stack
            direction="row"
            spacing={1}
            sx={{
              justifyContent: "end",
              flexGrow: 1,
              minWidth: 0,
              overflow: "hidden",
              pl: 1,
            }}
          >
            <NavbarBreadcrumbs mobileCompact />
          </Stack>
        </Stack>
        {isSmallScreen && <ServerStatus compact={isSmallScreen || !open} />}
      </Toolbar>
    </AppBar>
  );
};

export default function AppNavbar() {
  const [openDrawer, setOpenDrawer] = useState(false);
  const toggleDrawer = () => setOpenDrawer((current) => !current);
  const theme = useTheme();
  const isSmallScreen = useMediaQuery(theme.breakpoints.down("lg"));

  return (
    <>
      <AppNavbarBase
        open={openDrawer}
        toggleDrawer={toggleDrawer}
        isSmallScreen={isSmallScreen}
      />
      <SideMenuMobile
        open={isSmallScreen ? openDrawer : false}
        toggleDrawer={isSmallScreen ? toggleDrawer : () => {}}
      />
    </>
  );
}
