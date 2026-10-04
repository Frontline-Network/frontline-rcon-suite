import NewReleasesOutlinedIcon from "@mui/icons-material/NewReleasesOutlined";
import { styled } from '@mui/material/styles';
import { dividerClasses } from '@mui/material/Divider';
import Menu from '@mui/material/Menu';
import MuiMenuItem from '@mui/material/MenuItem';
import { paperClasses } from '@mui/material/Paper';
import { listClasses } from '@mui/material/List';
import ListItemText from '@mui/material/ListItemText';
import ListItemIcon, { listItemIconClasses } from '@mui/material/ListItemIcon';
import LogoutRoundedIcon from '@mui/icons-material/LogoutRounded';
import MoreVertRoundedIcon from '@mui/icons-material/MoreVertRounded';
import PaletteOutlinedIcon from '@mui/icons-material/PaletteOutlined';
import MenuBookOutlinedIcon from '@mui/icons-material/MenuBookOutlined';
import MenuButton from './MenuButton';
import {Link, useSubmit} from 'react-router-dom';
import {Fragment, useState} from "react";
import { useTranslation } from "react-i18next";
import { useAppStore } from "@/stores/app-state";
import Badge from "@mui/material/Badge";
import { useUpdateChannel } from "@/hooks/useUpdateChannel";

const MenuItem = styled(MuiMenuItem)({
  margin: '2px 0',
});

export default function OptionsMenu({ renderTrigger }) {
  const { t } = useTranslation();
  const { unreadCount } = useUpdateChannel({ poll: true });
  const [anchorEl, setAnchorEl] = useState(null);
  const setAppearanceOpen = useAppStore((state) => state.setAppearanceDialogOpen);
  const submit = useSubmit();
  const open = Boolean(anchorEl);
  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };
  const handleClose = () => {
    setAnchorEl(null);
  };
  const handleLogout = () => {
    setAnchorEl(null);
    const formData = new FormData();
    formData.append('intent', 'logout');
    submit(formData, { action: '/', method: 'POST' })
  }
  const triggerProps = {
    "aria-label": t("common.actions"),
    "aria-controls": open ? "user-options-menu-popover" : undefined,
    "aria-expanded": open || undefined,
    "aria-haspopup": "menu",
    "data-testid": "user-options-menu",
    onClick: handleClick,
  };
  return (
    <Fragment>
      {renderTrigger ? (
        renderTrigger(triggerProps)
      ) : (
        <MenuButton {...triggerProps} sx={{ borderColor: 'transparent' }}>
          <MoreVertRoundedIcon />
        </MenuButton>
      )}
      <Menu
        anchorEl={anchorEl}
        id="user-options-menu-popover"
        open={open}
        onClose={handleClose}
        onClick={handleClose}
        transformOrigin={{ horizontal: 'right', vertical: 'top' }}
        anchorOrigin={{ horizontal: 'right', vertical: 'bottom' }}
        sx={{
          [`& .${listClasses.root}`]: {
            padding: '4px',
          },
          [`& .${paperClasses.root}`]: {
            padding: 0,
          },
          [`& .${dividerClasses.root}`]: {
            margin: '4px -4px',
          },
        }}
      >
        <MenuItem onClick={() => setAppearanceOpen(true)}>
          <ListItemText>{t("appearance.menuLabel")}</ListItemText>
          <ListItemIcon sx={{ ml: 'auto', minWidth: 0 }}>
            <PaletteOutlinedIcon fontSize="small" />
          </ListItemIcon>
        </MenuItem>
        <MenuItem component={Link} to="/updates">
          <ListItemText>{t("updates.title")}</ListItemText>
          <ListItemIcon sx={{ ml: "auto", minWidth: 0 }}><Badge color="primary" variant="dot" invisible={!unreadCount}><NewReleasesOutlinedIcon fontSize="small" /></Badge></ListItemIcon>
        </MenuItem>
        <MenuItem component={Link} to="/documentation">
          <ListItemText>{t("documentation.title")}</ListItemText>
          <ListItemIcon sx={{ ml: 'auto', minWidth: 0 }}>
            <MenuBookOutlinedIcon fontSize="small" />
          </ListItemIcon>
        </MenuItem>
        <MenuItem
          component={Link}
          to="/account/password"
          sx={{
            [`& .${listItemIconClasses.root}`]: {
              ml: 'auto',
              minWidth: 0,
            },
          }}
        >
          <ListItemText>{t("sidebar.changePassword")}</ListItemText>
        </MenuItem>
        <MenuItem
          onClick={handleLogout}
          sx={{
            [`& .${listItemIconClasses.root}`]: {
              ml: 'auto',
              minWidth: 0,
            },
          }}
        >
          <ListItemText>{t("sidebar.logout")}</ListItemText>
          <ListItemIcon>
            <LogoutRoundedIcon fontSize="small" />
          </ListItemIcon>
        </MenuItem>
      </Menu>
    </Fragment>
  );
}
