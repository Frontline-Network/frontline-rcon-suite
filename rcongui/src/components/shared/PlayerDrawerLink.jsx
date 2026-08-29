import { usePlayerSidebar } from "@/hooks/usePlayerSidebar";
import { Box } from "@mui/material";

export const PlayerDrawerLink = ({ playerId, children, ...props }) => {
  const { openWithId } = usePlayerSidebar();
  const handleClick = () => {
    openWithId(playerId);
  };

  return (
    <Box
      component="button"
      type="button"
      onClick={handleClick}
      {...props}
      sx={{
        appearance: "none",
        bgcolor: "transparent",
        border: 0,
        color: "inherit",
        cursor: "pointer",
        display: "inline",
        font: "inherit",
        fontStyle: "italic",
        fontWeight: "bolder",
        m: 0,
        p: 0,
        textAlign: "inherit",
        "&:hover": {
          textDecoration: "underline",
        },
        "&:focus-visible": {
          borderRadius: 0.25,
          outline: "2px solid",
          outlineColor: "primary.main",
          outlineOffset: 2,
        },
        ...props.sx,
      }}
    >
      {children}
    </Box>
  );
};
