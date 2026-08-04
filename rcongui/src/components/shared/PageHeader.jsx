import { Box, Stack, Typography } from "@mui/material";

export default function PageHeader({ eyebrow, title, subtitle, actions }) {
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      justifyContent="space-between"
      alignItems={{ xs: "stretch", sm: "flex-end" }}
      gap={2}
      sx={{
        mb: 2,
        pb: 1.5,
        borderBottom: "1px solid",
        borderColor: "divider",
      }}
    >
      <Box>
        {eyebrow && (
          <Typography
            variant="overline"
            color="primary.main"
            sx={{ fontWeight: 800, letterSpacing: "0.14em" }}
          >
            {eyebrow}
          </Typography>
        )}
        <Typography
          component="h1"
          variant="h4"
          sx={{
            fontFamily: '"Bahnschrift Condensed", "Arial Narrow", sans-serif',
            fontWeight: 800,
            letterSpacing: "0.045em",
            textTransform: "uppercase",
            lineHeight: 1,
          }}
        >
          {title}
        </Typography>
        {subtitle && (
          <Typography color="text.secondary" sx={{ mt: 0.75, maxWidth: 760 }}>
            {subtitle}
          </Typography>
        )}
      </Box>
      {actions && <Box sx={{ flexShrink: 0 }}>{actions}</Box>}
    </Stack>
  );
}
