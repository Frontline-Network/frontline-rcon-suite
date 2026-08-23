import { Box, Chip, Stack, Typography } from "@mui/material";
import ConfigSectionNavigation from "./ConfigSectionNavigation";

export default function ConfigFormLayout({
  eyebrow,
  title,
  description,
  status,
  statusColor = "default",
  headerActions,
  sections = [],
  activeSection,
  onSectionChange,
  navigationLabel,
  mobileNavigationLabel,
  children,
  summary,
  actionBar,
  testId = "config-page-shell",
  sx,
}) {
  const hasNavigation = sections.length > 0;
  const hasSummary = Boolean(summary);
  return (
    <Box
      data-testid={testId}
      sx={{ maxWidth: hasNavigation ? 1310 : undefined, ...sx }}
    >
      <Stack spacing={1.5} sx={{ mb: 2 }}>
        <Box>
          {eyebrow && (
            <Typography
              variant="overline"
              color="primary.main"
              sx={{ display: "block", mb: 0.35 }}
            >
              {eyebrow}
            </Typography>
          )}
          <Stack
            direction="row"
            spacing={1.25}
            alignItems="center"
            useFlexGap
            flexWrap="wrap"
          >
            <Typography component="h1" variant="h4" fontWeight={800}>
              {title}
            </Typography>
            {status && (
              <Chip
                label={status}
                color={statusColor}
                size="small"
                sx={{ borderRadius: 0.75, fontWeight: 800 }}
              />
            )}
          </Stack>
          {description && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.75, maxWidth: 820 }}
            >
              {description}
            </Typography>
          )}
        </Box>
        {headerActions && <Box>{headerActions}</Box>}
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns:
            hasNavigation && hasSummary
              ? {
                  xs: "minmax(0, 1fr)",
                  md: "minmax(190px, 0.8fr) minmax(0, 2.2fr)",
                  lg: "minmax(230px, 0.9fr) minmax(0, 3fr) minmax(240px, 1fr)",
                }
              : hasNavigation
              ? {
                  xs: "minmax(0, 1fr)",
                  md: "minmax(190px, 0.8fr) minmax(0, 3fr)",
                }
              : "minmax(0, 1fr)",
          gridTemplateAreas:
            hasNavigation && hasSummary
              ? {
                  xs: '"navigation" "content" "summary"',
                  md: '"navigation content" "summary summary"',
                  lg: '"navigation content summary"',
                }
              : hasNavigation
              ? {
                  xs: '"navigation" "content"',
                  md: '"navigation content"',
                }
              : '"content"',
          alignItems: "stretch",
          gap: 0,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
        }}
      >
        {hasNavigation && (
          <Box
            sx={{
              gridArea: "navigation",
              minWidth: 0,
              borderRight: { md: "1px solid" },
              borderBottom: { xs: "1px solid", md: 0 },
              borderColor: { xs: "divider", md: "divider" },
            }}
          >
            <ConfigSectionNavigation
              sections={sections}
              activeSection={activeSection}
              onSectionChange={onSectionChange}
              label={navigationLabel}
              mobileLabel={mobileNavigationLabel}
            />
          </Box>
        )}

        <Stack
          sx={{
            gridArea: "content",
            minWidth: 0,
            px: { xs: 2, md: 3 },
            pt: { xs: 2, md: 3 },
            pb: { xs: 2, md: 1.5 },
          }}
          spacing={2}
        >
          {children}
        </Stack>

        {hasSummary && (
          <Box
            sx={{
              gridArea: "summary",
              minWidth: 0,
              p: { xs: 2, md: 3 },
              borderTop: { xs: "1px solid", lg: 0 },
              borderLeft: { lg: "1px solid" },
              borderColor: { xs: "divider", lg: "divider" },
            }}
          >
            {summary}
          </Box>
        )}
      </Box>

      <Box sx={{ mt: actionBar ? 0 : undefined }}>{actionBar}</Box>
    </Box>
  );
}
