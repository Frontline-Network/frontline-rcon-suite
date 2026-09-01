import IconButton from "@mui/material/IconButton";
import Menu from "@mui/material/Menu";
import MenuItem from "@mui/material/MenuItem";
import MoreVertIcon from "@mui/icons-material/MoreVert";
import MoreHorizIcon from "@mui/icons-material/MoreHoriz";
import MilitaryTechIcon from "@mui/icons-material/MilitaryTech";
import AssignmentIndIcon from "@mui/icons-material/AssignmentInd";
import {
  Badge,
  Box,
  Divider,
  ListItemIcon,
  Typography,
  Card,
  Tooltip,
  Button,
} from "@mui/material";
import { useAuth } from "@/hooks/useAuth";
import { useActionDialog } from "@/hooks/useActionDialog";
import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import PersonIcon from "@mui/icons-material/Person";
import { useId, useMemo, useState } from "react";
import { useEditAccountModal } from "@/hooks/useEditAccountModal";
import { useEditSoldierModal } from "@/hooks/useEditSoldierModal";
import { useTranslation } from "react-i18next";

/**
 * Displays a menu of actions that the user can perform on a player.
 * The provided actions are filtered based on the user's permissions.
 */
export function ActionMenu({
  actions,
  recipients,
  anchorEl,
  setAnchorEl,
  withProfile = false,
  menuId,
}) {
  const { t } = useTranslation();
  const { permissions: user } = useAuth();
  const { openDialog } = useActionDialog();
  const { openWithId } = usePlayerSidebar();
  const open = Boolean(anchorEl);
  const { openModal: openAccountModal, modal: accountModal } =
    useEditAccountModal(recipients.player_id, recipients.account);
  const { openModal: openSoldierModal, modal: soldierModal } =
    useEditSoldierModal(recipients.player_id, recipients.soldier);
  const handleClose = () => {
    setAnchorEl(null);
  };

  const handleActionClick = (action) => {
    openDialog(action, recipients);
    setAnchorEl(null);
  };

  const handleProfileClick = () => {
    handleClose();
    openWithId(recipients.player_id);
  };

  const filteredActionList = useMemo(
    () => actions.filter(hasPermission(user)),
    [actions, user]
  );

  return (
    <Menu
      id={menuId}
      anchorEl={anchorEl}
      open={open}
      onClose={handleClose}
      sx={{ maxHeight: (theme) => theme.typography.pxToRem(500) }}
    >
      {withProfile && !Array.isArray(recipients) && (
        <>
          <MenuItem onClick={handleProfileClick} dense>
            <ListItemIcon>
              <PersonIcon />
            </ListItemIcon>
            {t("actions.viewProfile")}
          </MenuItem>
          <MenuItem onClick={openSoldierModal} dense>
            <ListItemIcon>
              <MilitaryTechIcon />
            </ListItemIcon>
            {t("actions.editSoldier")}
          </MenuItem>
          <MenuItem onClick={openAccountModal} dense>
            <ListItemIcon>
              <AssignmentIndIcon />
            </ListItemIcon>
            {t("actions.editAccount")}
          </MenuItem>
        </>
      )}
      {withProfile && !Array.isArray(recipients) && <Divider />}
      {filteredActionList.map((action) => (
        <MenuItem
          key={action.name}
          onClick={(event) => handleActionClick(action, event)}
          dense
        >
          <ListItemIcon>
            <action.icon />
          </ListItemIcon>
          <Typography
            variant="inherit"
            sx={{ textDecoration: action.deprecated ? "line-through" : "" }}
          >
            {action.translationKey
              ? t(`${action.translationKey}.name`)
              : action.name}
          </Typography>
        </MenuItem>
      ))}
      {filteredActionList.length === 0 && (
        <MenuItem disabled>
          {actions.length > 0
            ? t("actions.missingPermission")
            : t("actions.none")}
        </MenuItem>
      )}
      {accountModal}
      {soldierModal}
    </Menu>
  );
}

/**
 * @typedef {Object} Player
 * @property {string} player_id - The unique identifier for the player
 * @property {string} name - The name of the player
 */

/**
 * @param {Player|Player[]} recipients - The player or players to perform actions on.
 * @param {ReactNode} renderButton - A custom button to render instead of the default one.
 * @param {boolean} withProfile - Whether to include a profile button in the menu.
 * @param {string} orientation - The orientation of the menu. Can be "vertical" or "horizontal".
 * @param {object} props - Additional props to pass to the menu button.
 */

/**
 * Displays a menu of actions that the user can perform on a player.
 * The provided actions are filtered based on the user's permissions.
 * If the withProfile prop is true, a profile button will be added to the menu.
 * The profile button will open the player sidebar with the player's id.
 */
export function ActionMenuButton({
  actions,
  recipients,
  renderButton,
  orientation = "vertical",
  withProfile = false,
  size = "regular",
  ...props
}) {
  const { t } = useTranslation();
  const generatedId = useId();
  const [anchorEl, setAnchorEl] = useState(null);
  const open = Boolean(anchorEl);
  const buttonId = `player-action-button-${generatedId}`;
  const menuId = `player-action-menu-${generatedId}`;

  const handleClick = (event) => {
    setAnchorEl(event.currentTarget);
  };

  const buttonProps = {
    "aria-label": t("actions.menu"),
    id: buttonId,
    "aria-controls": open ? menuId : undefined,
    "aria-expanded": open ? "true" : undefined,
    "aria-haspopup": "true",
    onClick: handleClick,
  };

  return (
    <Box>
      {renderButton ? (
        renderButton({ ...buttonProps })
      ) : (
        <IconButton {...buttonProps} {...props}>
          <Badge
            badgeContent={Array.isArray(recipients) ? recipients.length : 0}
            color="primary"
          >
            {orientation === "vertical" ? <MoreVertIcon /> : <MoreHorizIcon />}
          </Badge>
        </IconButton>
      )}
      <ActionMenu
        actions={actions}
        recipients={recipients}
        withProfile={withProfile}
        anchorEl={anchorEl}
        setAnchorEl={setAnchorEl}
        menuId={menuId}
      />
    </Box>
  );
}

export function ActionBar({ actions, recipients = [] }) {
  return (
    <Card
      sx={{
        display: "flex",
        color: "text.secondary",
        p: 0,
        gap: 0,
        [`& .MuiIconButton-root`]: {
          borderRadius: 0,
          width: 40,
          height: 40,
        },
        [`& .MuiIconButton-root + .MuiIconButton-root`]: {
          borderLeft: (theme) => `1px solid ${theme.palette.divider}`,
        },
      }}
    >
      {actions.map((action) => (
        <ActionIconButton
          key={action.name}
          action={action}
          recipients={recipients}
        />
      ))}
    </Card>
  );
}

export function ActionIconButton({
  action,
  recipients,
  params,
  icon,
  label,
  sx,
  ...props
}) {
  const { t } = useTranslation();
  const { permissions: user } = useAuth();
  const { openDialog } = useActionDialog();
  const actionLabel =
    label ||
    (action.translationKey ? t(`${action.translationKey}.name`) : action.name);
  const allowed = hasPermission(user)(action);

  const handleActionClick = (action) => () => {
    openDialog(action, recipients, params);
  };

  return (
    <Tooltip
      title={allowed ? actionLabel : t("actions.missingPermission")}
      key={action.name}
    >
      <span>
        <IconButton
          key={action.name}
          aria-label={actionLabel}
          disabled={!allowed}
          size="small"
          onClick={handleActionClick(action)}
          sx={{ opacity: action.deprecated ? 0.5 : 1 }}
          {...props}
        >
          {icon ? icon : <action.icon sx={sx} />}
        </IconButton>
      </span>
    </Tooltip>
  );
}

export function ActionButton({
  action,
  recipients,
  params,
  sx,
  label,
  tooltipLabel,
  icon: Icon,
  onBeforeAction,
  ...props
}) {
  const { t } = useTranslation();
  const { permissions: user } = useAuth();
  const { openDialog } = useActionDialog();
  const allowed = hasPermission(user)(action);
  const actionLabel =
    label ||
    (action.translationKey ? t(`${action.translationKey}.name`) : action.name);
  const accessibleActionLabel = tooltipLabel || actionLabel;

  return (
    <Tooltip
      title={allowed ? accessibleActionLabel : t("actions.missingPermission")}
    >
      <span>
        <Button
          size="small"
          variant="outlined"
          startIcon={Icon ? <Icon /> : <action.icon />}
          aria-label={accessibleActionLabel}
          disabled={!allowed}
          onClick={() => {
            onBeforeAction?.();
            openDialog(action, recipients, params);
          }}
          sx={[{ opacity: action.deprecated ? 0.5 : 1 }, sx]}
          {...props}
        >
          {actionLabel}
        </Button>
      </span>
    </Tooltip>
  );
}

function hasPermission(user) {
  return (action) => {
    if (!user.is_superuser && action.permission) {
      // example ["can_blacklist", "can_watch", "can_ban", "can_message", "can_comment"]
      // user needs to have all permissions in the array
      return action.permission.every((perm) =>
        user.permissions.some((userPerm) => userPerm.permission === perm)
      );
    }

    return true;
  };
}
