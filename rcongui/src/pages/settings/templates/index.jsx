import { Link, Outlet, useLocation } from "react-router-dom";
import {
  Avatar,
  Box,
  ListItemAvatar,
  ListItemText,
  ListSubheader,
  MenuItem,
  Select,
  selectClasses,
} from "@mui/material";
import ChatIcon from '@mui/icons-material/Chat';
import WavingHandIcon from '@mui/icons-material/WavingHand';
import AnnouncementIcon from '@mui/icons-material/Announcement';
import PodcastsIcon from '@mui/icons-material/Podcasts';
import SettingsSuggestIcon from '@mui/icons-material/SettingsSuggest';
import { useTranslation } from "react-i18next";

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

  return (
    <Box>
      <Select
        labelId="messages-select"
        id="messages-simple-select"
        value={location.pathname}
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
          borderBottomLeftRadius: 0,
          borderBottomRightRadius: 0,
          "&.MuiList-root": {
            p: "8px",
          },
          [`& .${selectClasses.select}`]: {
            display: "flex",
            alignItems: "center",
            gap: "2px",
            pl: 1,
          },
        }}
      >
        <ListSubheader sx={{ pt: 0 }}>{t("settings.templates.categories")}</ListSubheader>
        {categories?.map((type) => (
          <MenuItem
            key={type.href}
            value={type.href}
            component={Link}
            href={type.href}
            to={type.href}
          >
            <ListItemAvatar>
              <Avatar alt={t(type.label)}>
                {type.icon}
              </Avatar>
            </ListItemAvatar>
            <ListItemText
              sx={{
                overflow: "hidden",
                textOverflow: "ellipsis",
                whiteSpace: "nowrap",
              }}
              primary={t(type.label)}
            />
          </MenuItem>
        ))}
      </Select>
      <Outlet />
    </Box>
  );
};

export default MessagesRoot;
