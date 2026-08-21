import Grid from "@mui/material/Grid2";
import AppBar from "@mui/material/AppBar";
import Toolbar from "@mui/material/Toolbar";
import { Link as RouterLink } from "react-router-dom";
import Button from "@mui/material/Button";
import IconButton from "@mui/material/IconButton";
import ServerStatus from "./server-status";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import MenuIcon from "@mui/icons-material/Menu";
import { navMenus } from "./nav-data";
import { useTranslation } from "react-i18next";
import { LoginBox } from "./login";
import { styled, useTheme } from "@mui/material/styles";
import useMediaQuery from "@mui/material/useMediaQuery";
import {Fragment, useState} from "react";

const StyledToolbar = styled(Toolbar)(({ theme }) => ({
  display: "flex",
  flexGrow: 1,
  flexDirection: "column",
  justifyContent: "center",
  alignItems: "start",
  padding: theme.spacing(0.25),
  minHeight: 0,
  gap: theme.spacing(0.25),
  [theme.breakpoints.up("md")]: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    gap: theme.spacing(2),
    padding: theme.spacing(0.5),
  }
}));

const Nav = styled('div')(({ theme }) => ({
  display: "flex",
  flexDirection: "row",
  flexGrow: 1,
  justifyContent: "space-between",
  alignItems: "center",
  minWidth: 0,
  width: "100%",
  gap: theme.spacing(0.5),
  [theme.breakpoints.up("md")]: {
    width: "auto",
  },
}));

const initialMenuState = navMenus.reduce((state, menu) => {
  state[menu.name] = false;
  return state;
}, {});

const Header = () => {
  const { t } = useTranslation();
  const theme = useTheme();
  const isCompactViewport = useMediaQuery(theme.breakpoints.down("md"));
  const [openedMenu, setOpenedMenu] = useState(initialMenuState);
  const [anchorEl, setAnchorEl] = useState(null);
  const [mobileNavAnchorEl, setMobileNavAnchorEl] = useState(null);

  const handleOpenMenu = (name) => (event) => {
    setOpenedMenu({
      ...openedMenu,
      [name]: true,
    });
    setAnchorEl(event.currentTarget);
  };

  const handleCloseMenu = (name) => () => {
    setOpenedMenu({
      ...openedMenu,
      [name]: false,
    });
    setAnchorEl(null);
  };

  const mobileNavigationLinks = navMenus.flatMap((menu) => menu.links);

  const handleOpenMobileNavigation = (event) => {
    setMobileNavAnchorEl(event.currentTarget);
  };

  const handleCloseMobileNavigation = () => {
    setMobileNavAnchorEl(null);
  };

  return (
    <Grid container>
      <AppBar position="static">
        <StyledToolbar>
          <ServerStatus compact={isCompactViewport} />
          <Nav>
            {isCompactViewport ? (
              <Fragment>
                <IconButton
                  color="inherit"
                  aria-label="Open navigation"
                  aria-controls={mobileNavAnchorEl ? "mobile-navigation-menu" : undefined}
                  aria-haspopup="true"
                  aria-expanded={mobileNavAnchorEl ? "true" : undefined}
                  onClick={handleOpenMobileNavigation}
                >
                  <MenuIcon />
                </IconButton>
                <Menu
                  id="mobile-navigation-menu"
                  anchorEl={mobileNavAnchorEl}
                  keepMounted
                  open={Boolean(mobileNavAnchorEl)}
                  onClose={handleCloseMobileNavigation}
                  PaperProps={{ style: { minWidth: "20ch", maxWidth: "calc(100vw - 16px)" } }}
                >
                  {mobileNavigationLinks.map((link) => (
                    <MenuItem
                      component={RouterLink}
                      to={link.to}
                      key={link.to}
                      onClick={handleCloseMobileNavigation}
                    >
                      {link.translationKey ? t(link.translationKey) : link.name}
                    </MenuItem>
                  ))}
                </Menu>
              </Fragment>
            ) : (
              <nav>
                {navMenus.map((menu) => (
                  <Fragment key={menu.name}>
                    <Button onClick={handleOpenMenu(menu.name)}>
                      {menu.translationKey ? t(menu.translationKey) : menu.name}
                    </Button>
                    <Menu
                      id={`${menu.name}-menu`}
                      anchorEl={anchorEl}
                      keepMounted
                      open={openedMenu[menu.name]}
                      onClose={handleCloseMenu(menu.name)}
                      PaperProps={{
                        style: {
                          minWidth: '20ch',
                        },
                      }}
                    >
                      {menu.links.map((link) => (
                        <MenuItem component={RouterLink} to={link.to} key={link.to} onClick={handleCloseMenu(menu.name)}>
                          {link.translationKey ? t(link.translationKey) : link.name}
                        </MenuItem>
                      ))}
                    </Menu>
                  </Fragment>
                ))}
              </nav>
            )}
            <LoginBox component={RouterLink} />
          </Nav>
        </StyledToolbar>
      </AppBar>
    </Grid>
  );
};

export default Header;
