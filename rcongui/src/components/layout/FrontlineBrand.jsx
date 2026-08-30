import { Box, Stack, Typography } from "@mui/material";

export default function FrontlineBrand({ compact = false, textOnly = false }) {
  return (
    <Stack
      data-testid={compact ? "compact-frontline-brand" : "frontline-brand"}
      direction="row"
      alignItems="center"
      spacing={textOnly ? 0 : 1.1}
      sx={{
        minWidth: 0,
        flexShrink: 0,
        px: compact ? 0 : 1.75,
        py: compact ? 0 : 1.5,
      }}
    >
      {!textOnly && (
        <Box
          component="img"
          src="/frontline-logo.png"
          alt=""
          sx={{
            width: compact ? 38 : 48,
            height: compact ? 32 : 40,
            objectFit: "contain",
          }}
        />
      )}
      <Box sx={{ minWidth: 0 }}>
        <Typography
          component="div"
          sx={{
            color: "text.primary",
            fontFamily: '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
            fontSize: compact ? 14 : 17,
            fontWeight: 800,
            lineHeight: 0.9,
            letterSpacing: "0.04em",
            textTransform: "uppercase",
          }}
        >
          Frontline
        </Typography>
        <Typography
          component="div"
          sx={{
            color: "primary.light",
            fontSize: compact ? 9 : 10,
            fontWeight: 900,
            lineHeight: 1.2,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
          }}
        >
          Network
        </Typography>
      </Box>
    </Stack>
  );
}
