import { Link, Navigate, Outlet, useLocation } from "react-router-dom";
import {
  Avatar,
  Box,
  ButtonBase,
  ListItemAvatar,
  ListItemText,
  ListSubheader,
  MenuItem,
  Paper,
  Select,
  Stack,
  Typography,
  selectClasses,
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
              <ButtonBase
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
        <Paper variant="outlined" sx={{ mb: 1.5 }}>
          <Select
            labelId="messages-select"
            id="messages-simple-select"
            value={activeCategory.href}
            displayEmpty
            inputProps={{ "aria-label": t("settings.templates.select") }}
            fullWidth
            MenuProps={{
              PaperProps: {
                sx: {
                  "& .MuiMenuItem-root:not(:last-child)": {
                    mb: 1,
                  },
                },
              },
            }}
            sx={{
              maxHeight: 56,
              borderRadius: 0,
              "&.MuiList-root": { p: "8px" },
              [`& .${selectClasses.select}`]: {
                display: "flex",
                alignItems: "center",
                gap: "2px",
                pl: 1,
              },
            }}
          >
            <ListSubheader sx={{ pt: 0 }}>{t("settings.templates.categories")}</ListSubheader>
            {categories.map((type) => (
              <MenuItem
                key={type.href}
                value={type.href}
                component={Link}
                to={type.href}
              >
                <ListItemAvatar>
                  <Avatar alt={t(type.label)}>{type.icon}</Avatar>
                </ListItemAvatar>
                <ListItemText
                  sx={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                  primary={t(type.label)}
                />
              </MenuItem>
            ))}
          </Select>
        </Paper>
      )}
      <Outlet />
    </Box>
  );
};

export default MessagesRoot;
