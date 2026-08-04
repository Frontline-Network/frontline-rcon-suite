import { Paper } from "@mui/material";

export default function SectionSurface({ children, sx, ...props }) {
  return (
    <Paper
      variant="outlined"
      {...props}
      sx={{
        borderRadius: 0,
        borderColor: "divider",
        backgroundColor: "background.paper",
        backgroundImage: "none",
        overflow: "hidden",
        ...sx,
      }}
    >
      {children}
    </Paper>
  );
}
