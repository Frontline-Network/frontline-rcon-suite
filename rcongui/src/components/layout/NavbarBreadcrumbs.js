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
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import Tooltip from "@mui/material/Tooltip";
import { canAccessNavLink, navMenus } from "@/components/Header/nav-data";
import { useAuth } from "@/hooks/useAuth";

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

function GroupBreadcrumb({ menu, permissions }) {
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
      <StyledPopper
        open={Boolean(anchorEl)}
        anchorEl={anchorEl}
        placement="bottom-start"
      >
        <ClickAwayListener onClickAway={() => setAnchorEl(null)}>
          <Box>
            <Typography
              variant="caption"
              color="primary.light"
              sx={{ display: "block", px: 1.5, py: 1 }}
            >
              {t("navigation.navigateTo")}
            </Typography>
            <List dense disablePadding sx={{ pb: 0.75 }}>
              {menu.links.map((item) => {
                const canAccess = canAccessNavLink(item, permissions);
                const content = (
                  <ListItem key={item.to} disablePadding>
                    <ListItemButton
                      {...(canAccess && { component: Link, to: item.to })}
                      aria-disabled={!canAccess || undefined}
                      onClick={() => canAccess && setAnchorEl(null)}
                      sx={
                        !canAccess
                          ? { color: "text.disabled", cursor: "not-allowed" }
                          : undefined
                      }
                    >
                      <ListItemIcon>{item.icon}</ListItemIcon>
                      <ListItemText primary={translatedLabel(item, t)} />
                      {!canAccess && (
                        <LockOutlinedIcon aria-hidden fontSize="small" />
                      )}
                    </ListItemButton>
                  </ListItem>
                );

                return canAccess ? (
                  content
                ) : (
                  <Tooltip
                    key={item.to}
                    title={t("navigation.permissionMissing")}
                    placement="right"
                    arrow
                  >
                    {content}
                  </Tooltip>
                );
              })}
            </List>
          </Box>
        </ClickAwayListener>
      </StyledPopper>
    </Fragment>
  );
}

export default function NavbarBreadcrumbs({ mobileCompact = false }) {
  const { t } = useTranslation();
  const { permissions } = useAuth();
  const location = useLocation();

  const current = useMemo(() => {
    if (location.pathname === "/") return {};
    const links = navMenus.flatMap((menu) =>
      menu.links.map((link) => ({
        menu,
        link,
        path: link.to.startsWith("/") ? link.to : `/${link.to}`,
      }))
    );
    return (
      links
        .filter(
          ({ path }) =>
            location.pathname === path ||
            location.pathname.startsWith(`${path}/`)
        )
        .sort((a, b) => b.path.length - a.path.length)[0] || {}
    );
  }, [location.pathname]);

  const currentLabel = current.link
    ? translatedLabel(current.link, t)
    : t("navigation.links.home");

  return (
    <Box sx={{ minWidth: 0, maxWidth: "100%" }}>
      {mobileCompact && (
        <Typography
          data-testid="mobile-current-route"
          aria-current="page"
          color="text.primary"
          sx={{
            display: { xs: "block", sm: "none" },
            maxWidth: "100%",
            overflow: "hidden",
            textOverflow: "ellipsis",
            whiteSpace: "nowrap",
            fontWeight: 700,
          }}
        >
          {currentLabel}
        </Typography>
      )}
      <StyledBreadcrumbs
        aria-label="breadcrumb"
        separator={<NavigateNextRoundedIcon fontSize="small" />}
        sx={{ display: mobileCompact ? { xs: "none", sm: "flex" } : "flex" }}
      >
        <Typography
          component={Link}
          to="/"
          color={location.pathname === "/" ? "primary.light" : "text.secondary"}
          sx={{ textDecoration: "none" }}
        >
          {t("navigation.links.home")}
        </Typography>
        {current.menu?.name && (
          <GroupBreadcrumb menu={current.menu} permissions={permissions} />
        )}
        {current.link && (
          <Typography color="text.primary" sx={{ fontWeight: 700 }}>
            {translatedLabel(current.link, t)}
          </Typography>
        )}
      </StyledBreadcrumbs>
    </Box>
  );
}
