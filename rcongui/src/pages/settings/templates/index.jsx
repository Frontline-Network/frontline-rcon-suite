import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import {
  Box,
  ButtonBase,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import ChatIcon from '@mui/icons-material/Chat';
import WavingHandIcon from '@mui/icons-material/WavingHand';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import PodcastsIcon from '@mui/icons-material/Podcasts';
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest';
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";

const categories = [
  {
    label: "settings.templates.message",
    href: "/settings/templates/message",
    icon: <ChatIcon />,
  },
  {
    label: "settings.templates.reason",
    href: "/settings/templates/reason",
    icon: <AnnouncementIcon />,
  },
  {
    label: "settings.templates.welcome",
    href: "/settings/templates/welcome",
    icon: <WavingHandIcon />,
  },
  {
    label: "settings.templates.broadcast",
    href: "/settings/templates/broadcast",
    icon: <PodcastsIcon />,
  },
  {
    label: "settings.templates.autosettings",
    href: "/settings/templates/auto_settings",
    icon: <SettingsSuggestIcon />,
  },
];

const MessagesRoot = () => {
  const location = useLocation();
  const { t } = useTranslation();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));

  if (location.pathname.replace(/\/$/, "") === "/settings/templates") {
    return <Navigate replace to="/settings/templates/message" />;
  }

  const activeCategory =
    categories.find((category) => category.href === location.pathname) ??
    categories[0];

  return (
    <Box sx={{ minWidth: 0, pb: { xs: 10, md: 0 } }}>
      <PageHeader
        eyebrow={t("settings.templates.eyebrow")}
        title={t("settings.templates.title")}
        subtitle={t("settings.templates.subtitle")}
      />

      {compact ? (
        <Stack
          component="nav"
          className="wardogs-page-tabs"
          aria-label={t("settings.templates.categories")}
          direction="row"
          gap={1}
          sx={{
            mx: -1,
            px: 1,
            mb: 1.5,
            overflowX: "auto",
            scrollbarWidth: "none",
            "&::-webkit-scrollbar": { display: "none" },
          }}
        >
          {categories.map((category) => {
            const selected = category.href === activeCategory.href;
            return (
              <ButtonBase data-theme-surface="control"
                key={category.href}
                component={Link}
                to={category.href}
                aria-current={selected ? "page" : undefined}
                sx={{
                  flex: "0 0 auto",
                  minHeight: 44,
                  px: 1.5,
                  gap: 1,
                  border: "1px solid",
                  borderColor: selected ? "primary.main" : "divider",
                  color: selected ? "primary.main" : "text.secondary",
                  bgcolor: selected ? "action.selected" : "background.paper",
                  fontWeight: 800,
                }}
              >
                {category.icon}
                <Typography variant="button" color="inherit">
                  {t(category.label)}
                </Typography>
              </ButtonBase>
            );
          })}
        </Stack>
      ) : (
        <Box data-theme-surface="panel"
          component="nav"
          className="wardogs-page-tabs"
          aria-label={t("settings.templates.categories")}
          sx={{
            display: "grid",
            gridTemplateColumns: "repeat(5, minmax(0, 1fr))",
            mb: 1.5,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
          }}
        >
          {categories.map((category, index) => {
            const selected = category.href === activeCategory.href;
            return (
              <ButtonBase
                key={category.href}
                component={Link}
                to={category.href}
                aria-current={selected ? "page" : undefined}
                sx={{
                  position: "relative",
                  minWidth: 0,
                  minHeight: 64,
                  px: 1.5,
                  gap: 1,
                  justifyContent: "flex-start",
                  borderRight: index < categories.length - 1 ? "1px solid" : 0,
                  borderColor: "divider",
                  color: selected ? "primary.main" : "text.secondary",
                  bgcolor: selected ? "action.selected" : "transparent",
                  "&::after": {
                    content: '""',
                    position: "absolute",
                    left: 0,
                    right: 0,
                    bottom: 0,
                    height: 2,
                    bgcolor: selected ? "primary.main" : "transparent",
                  },
                  "&:hover": {
                    bgcolor: selected ? "action.selected" : "action.hover",
                    color: selected ? "primary.main" : "text.primary",
                  },
                }}
              >
                <Box sx={{ display: "grid", placeItems: "center", flex: "0 0 auto" }}>
                  {category.icon}
                </Box>
                <Typography
                  variant="button"
                  color="inherit"
                  sx={{ overflow: "hidden", textOverflow: "ellipsis" }}
                >
                  {t(category.label)}
                </Typography>
              </ButtonBase>
            );
          })}
        </Box>
      )}
      <Outlet />
    </Box>
  );
};

export default MessagesRoot;
