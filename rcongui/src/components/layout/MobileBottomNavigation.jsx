import { useMemo } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { BottomNavigation, BottomNavigationAction, Paper } from "@mui/material";
import BoltRoundedIcon from "@mui/icons-material/BoltRounded";
import ReportProblemRoundedIcon from "@mui/icons-material/ReportProblemRounded";
import PeopleAltRoundedIcon from "@mui/icons-material/PeopleAltRounded";
import DashboardCustomizeRoundedIcon from "@mui/icons-material/DashboardCustomizeRounded";
import MoreHorizRoundedIcon from "@mui/icons-material/MoreHorizRounded";
import { useTranslation } from "react-i18next";
import { getContextNavigationSurface } from "./navigation/navigation-surfaces";
import { getMobileNavigationValue } from "./mobile-navigation.mjs";

const NAV_ITEMS = [
  { value: "operations", to: "/views/live", icon: BoltRoundedIcon },
  { value: "incidents", to: "/incidents", icon: ReportProblemRoundedIcon },
  { value: "players", to: "/records/players", icon: PeopleAltRoundedIcon },
  {
    value: "server-operations",
    to: "/",
    icon: DashboardCustomizeRoundedIcon,
  },
];

/**
 * Phone-only task navigation. The complete permission-aware navigation stays
 * available behind “More”; these five destinations cover the daily admin
 * workflow without mirroring the full desktop information architecture.
 */
export default function MobileBottomNavigation({
  onOpenMore,
  moreOpen = false,
}) {
  const { t } = useTranslation();
  const location = useLocation();
  const navigate = useNavigate();
  const value = useMemo(
    () => getMobileNavigationValue(location.pathname),
    [location.pathname]
  );

  return (
    <Paper
      component="nav"
      aria-label={t("mobileNav.ariaLabel")}
      elevation={8}
      square
      sx={(theme) => ({
        display: { xs: "block", md: "none" },
        position: "fixed",
        zIndex: theme.zIndex.appBar,
        right: 0,
        bottom: 0,
        left: 0,
        borderTop: `1px solid ${theme.palette.divider}`,
        ...getContextNavigationSurface(theme),
        pb: "env(safe-area-inset-bottom)",
      })}
    >
      <BottomNavigation
        showLabels
        value={value}
        onChange={(_event, nextValue) => {
          const item = NAV_ITEMS.find((entry) => entry.value === nextValue);
          if (item) navigate(item.to);
        }}
        sx={{
          height: "var(--mobile-bottom-nav-height)",
          bgcolor: "transparent",
          "& .MuiBottomNavigationAction-root": {
            minWidth: 0,
            minHeight: 56,
            px: 0.5,
            color: "text.secondary",
          },
          "& .MuiBottomNavigationAction-label": {
            fontSize: "0.68rem",
            fontWeight: 700,
            mt: 0.25,
          },
          "& .Mui-selected": { color: "primary.light" },
        }}
      >
        {NAV_ITEMS.map(({ value: itemValue, icon: Icon }) => (
          <BottomNavigationAction
            key={itemValue}
            value={itemValue}
            label={t(`mobileNav.${itemValue}`)}
            icon={<Icon fontSize="small" />}
            aria-current={value === itemValue ? "page" : undefined}
          />
        ))}
        <BottomNavigationAction
          value="more"
          label={t("mobileNav.more")}
          icon={<MoreHorizRoundedIcon fontSize="small" />}
          aria-controls="mobile-primary-navigation"
          aria-expanded={moreOpen}
          onClick={(event) => {
            event.preventDefault();
            onOpenMore();
          }}
        />
      </BottomNavigation>
    </Paper>
  );
}
