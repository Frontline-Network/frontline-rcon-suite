import Badge, { badgeClasses } from '@mui/material/Badge';
import IconButton from '@mui/material/IconButton';

function MenuButton({ showBadge = false, sx, ...props }) {
  return (
    <Badge
      color="error"
      variant="dot"
      invisible={!showBadge}
      sx={{ [`& .${badgeClasses.badge}`]: { right: 2, top: 2 } }}
    >
      <IconButton
        size="small"
        sx={{ minWidth: 44, minHeight: 44, ...sx }}
        {...props}
      />
    </Badge>
  );
}


export default MenuButton;
