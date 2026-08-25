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
import MenuButton from './MenuButton';
import {useSubmit} from 'react-router-dom';
import {Fragment, lazy, Suspense, useState} from "react";
import { useTranslation } from "react-i18next";

const AppearanceSettingsDialog = lazy(() =>
  import("./AppearanceSettingsDialog")
);

const MenuItem = styled(MuiMenuItem)({
  margin: '2px 0',
});

export default function OptionsMenu() {
  const { t } = useTranslation();
  const [anchorEl, setAnchorEl] = useState(null);
  const [appearanceOpen, setAppearanceOpen] = useState(false);
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
  const handleChangePassword = () => {
    location.href = '/accounts/password_change';
  }
  return (
    <Fragment>
      <MenuButton
        aria-label={t("common.actions")}
        data-testid="user-options-menu"
        onClick={handleClick}
        sx={{ borderColor: 'transparent' }}
      >
        <MoreVertRoundedIcon />
      </MenuButton>
      <Menu
        anchorEl={anchorEl}
        id="menu"
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
        <MenuItem
          onClick={handleChangePassword}
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
      {appearanceOpen ? (
        <Suspense fallback={null}>
          <AppearanceSettingsDialog
            open
            onClose={() => setAppearanceOpen(false)}
          />
        </Suspense>
      ) : null}
    </Fragment>
  );
}
