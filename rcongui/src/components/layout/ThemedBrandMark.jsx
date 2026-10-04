import { Box } from "@mui/material";
import { useTheme } from "@mui/material/styles";

export default function ThemedBrandMark({
  src = "/frontline-logo.png",
  alt = "",
  sx,
}) {
  const theme = useTheme();
  if (theme.frontline?.appearance?.preset !== "wardogs") {
    return <Box component="img" src={src} alt={alt} sx={sx} />;
  }
  return (
    <Box
      component="span"
      role={alt ? "img" : undefined}
      aria-label={alt || undefined}
      aria-hidden={alt ? undefined : true}
      sx={{
        ...sx,
        display: "inline-block",
        bgcolor: "primary.main",
        mask: `url("${src}") center / contain no-repeat`,
        WebkitMask: `url("${src}") center / contain no-repeat`,
      }}
    />
  );
}
