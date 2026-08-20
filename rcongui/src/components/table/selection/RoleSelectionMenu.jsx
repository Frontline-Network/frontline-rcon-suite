import { List, ListItem, ListItemButton, Box } from "@mui/material";
import { PopoverMenu } from "@/components/shared/PopoverMenu";
import WorkIcon from '@mui/icons-material/Work';
import { Tooltip, Button } from "@mui/material";
import { RoleIcon } from "@/components/shared/RoleIcon";
import { useTranslation } from "react-i18next";
    
/**
 * @typedef {Object} RoleOption
 * @property {string} role
 * @property {number} [count]
 */

/**
 * @param {Object} props
 * @param {Array<RoleOption>} props.roleOptions
 * @param {Function} props.onRoleSelect
 * @returns {JSX.Element}
 */
export const RoleSelectionMenu = ({ roleOptions, onRoleSelect }) => {
  const { t } = useTranslation();
  return <PopoverMenu
    id="role-picker"
    description={t("selection.roleDescription")}
    renderButton={(props) => (
      <Button {...props} aria-label={t("selection.role")}>
        <Tooltip title={t("selection.role")}>
          <WorkIcon />
        </Tooltip>
      </Button>
    )}
  >
    <List
      sx={{
        width: "100%",
        bgcolor: "background.paper",
        position: "relative",
        overflowY: "auto",
        overflowX: "hidden",
        maxHeight: 300,
        "& ul": { padding: 0 },
      }}
    >
      {roleOptions.map((option) => (
        <ListItem
          key={option.role}
          dense
          disableGutters
          sx={{ "& .MuiButtonBase-root": { opacity: 1 } }}
        >
          <ListItemButton onClick={() => onRoleSelect(option)}>
            <Box sx={{ display: "flex", alignItems: "center", overflow: "hidden", px: 0, py: 0.25, gap: 1 }}>
              <RoleIcon role={option.role} />
              <Box sx={{ overflow: "hidden", whiteSpace: "nowrap", textOverflow: "ellipsis" }}>
                <Box component="span" fontWeight="bold" textTransform="uppercase">
                  {option.role}{option.count ? ` (${option.count})` : ""}
                </Box>
              </Box>
            </Box>
          </ListItemButton>
        </ListItem>
      ))}
    </List>
  </PopoverMenu>;
};
