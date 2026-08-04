import { Fragment, useMemo, useState } from "react";
import { Link, useLocation } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { styled } from "@mui/material/styles";
import Box from "@mui/material/Box";
import Breadcrumbs, { breadcrumbsClasses } from "@mui/material/Breadcrumbs";
import ClickAwayListener from "@mui/material/ClickAwayListener";
import List from "@mui/material/List";
import ListItem from "@mui/material/ListItem";
import ListItemButton from "@mui/material/ListItemButton";
import ListItemIcon from "@mui/material/ListItemIcon";
import ListItemText from "@mui/material/ListItemText";
import Popper from "@mui/material/Popper";
import Typography from "@mui/material/Typography";
import NavigateNextRoundedIcon from "@mui/icons-material/NavigateNextRounded";
import { navMenus } from "@/components/Header/nav-data";

const StyledBreadcrumbs = styled(Breadcrumbs)(({ theme }) => ({
  margin: theme.spacing(1, 0),
  [`& .${breadcrumbsClasses.separator}`]: {
    color: theme.palette.divider,
    margin: 2,
  },
}));

const StyledPopper = styled(Popper)(({ theme }) => ({
  border: `1px solid ${theme.palette.divider}`,
  backgroundColor: theme.palette.background.paper,
  borderRadius: theme.shape.borderRadius,
  minWidth: 220,
  zIndex: theme.zIndex.modal,
}));

const translatedLabel = (item, t) =>
  item?.translationKey ? t(item.translationKey) : item?.name || "";

function GroupBreadcrumb({ menu }) {
  const { t } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const label = translatedLabel(menu, t);

  return (
    <Fragment>
      <Typography
        component="button"
        type="button"
        onClick={(event) => setAnchorEl(event.currentTarget)}
        sx={{
          border: 0,
          p: 0,
          color: "text.secondary",
          bgcolor: "transparent",
          cursor: "pointer",
          font: "inherit",
          "&:hover": { color: "primary.light" },
        }}
      >
        {label}
      </Typography>
      <StyledPopper open={Boolean(anchorEl)} anchorEl={anchorEl} placement="bottom-start">
        <ClickAwayListener onClickAway={() => setAnchorEl(null)}>
          <Box>
            <Typography variant="caption" color="primary.light" sx={{ display: "block", px: 1.5, py: 1 }}>
              {t("navigation.navigateTo")}
            </Typography>
            <List dense disablePadding sx={{ pb: 0.75 }}>
              {menu.links.map((item) => (
                <ListItem key={item.to} disablePadding>
                  <ListItemButton component={Link} to={item.to} onClick={() => setAnchorEl(null)}>
                    <ListItemIcon>{item.icon}</ListItemIcon>
                    <ListItemText primary={translatedLabel(item, t)} />
                  </ListItemButton>
                </ListItem>
              ))}
            </List>
          </Box>
        </ClickAwayListener>
      </StyledPopper>
    </Fragment>
  );
}

export default function NavbarBreadcrumbs() {
  const { t } = useTranslation();
  const location = useLocation();

  const current = useMemo(() => {
    if (location.pathname === "/") return {};
    const links = navMenus.flatMap((menu) =>
      menu.links.map((link) => ({ menu, link, path: link.to.startsWith("/") ? link.to : `/${link.to}` }))
    );
    return links
      .filter(({ path }) => location.pathname === path || location.pathname.startsWith(`${path}/`))
      .sort((a, b) => b.path.length - a.path.length)[0] || {};
  }, [location.pathname]);

  return (
    <StyledBreadcrumbs aria-label="breadcrumb" separator={<NavigateNextRoundedIcon fontSize="small" />}>
      <Typography component={Link} to="/" color={location.pathname === "/" ? "primary.light" : "text.secondary"} sx={{ textDecoration: "none" }}>
        {t("navigation.links.home")}
      </Typography>
      {current.menu?.name && <GroupBreadcrumb menu={current.menu} />}
      {current.link && (
        <Typography color="text.primary" sx={{ fontWeight: 700 }}>
          {translatedLabel(current.link, t)}
        </Typography>
      )}
    </StyledBreadcrumbs>
  );
}
