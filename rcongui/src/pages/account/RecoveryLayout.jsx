import { useEffect } from "react";
import { Box, Container, Stack, Typography } from "@mui/material";
import FrontlineBrand from "@/components/layout/FrontlineBrand";
import LanguageSelector from "@/components/layout/LanguageSelector";

export default function RecoveryLayout({
  title,
  subtitle,
  children,
  wide = false,
}) {
  useEffect(() => {
    document.title = "Frontline Network · " + title;
  }, [title]);
  return (
    <Box
      component="main"
      id="main-content"
      sx={{
        minHeight: "100dvh",
        bgcolor: "background.default",
        py: { xs: 2, md: 5 },
      }}
    >
      <Container maxWidth={wide ? "lg" : "sm"}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: { xs: 4, md: 6 } }}
        >
          <FrontlineBrand compact />
          <LanguageSelector />
        </Stack>
        <Typography component="h1" variant="h4" sx={{ mb: 1 }}>
          {title}
        </Typography>
        <Typography color="text.secondary" sx={{ mb: 3, maxWidth: 700 }}>
          {subtitle}
        </Typography>
        {children}
        <Typography
          variant="caption"
          color="text.secondary"
          component="footer"
          sx={{ mt: 4 }}
        >
          Frontline Network · CRCON
        </Typography>
      </Container>
    </Box>
  );
}
