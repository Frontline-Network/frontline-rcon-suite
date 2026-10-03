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
  embedded = false,
}) {
  const hasNavigation = sections.length > 0;
  const hasSummary = Boolean(summary);
  return (
    <Box
      data-testid={testId}
      className="wardogs-config-layout"
      data-embedded={embedded || undefined}
      sx={{
        width: "100%",
        maxWidth: embedded ? "none" : hasNavigation ? 1304 : undefined,
        mx: embedded ? 0 : hasNavigation ? { xs: 0, xl: 1.5 } : undefined,
        ...sx,
      }}
    >
      <Stack spacing={1.5} sx={{ mb: 1 }}>
        {!embedded && (
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
        )}
        {headerActions && <Box>{headerActions}</Box>}
      </Stack>

      <Box
        className="wardogs-config-grid"
        data-has-summary={hasSummary}
        sx={{
          display: "grid",
          gridTemplateColumns:
            hasNavigation && hasSummary
              ? {
                  xs: "minmax(0, 1fr)",
                  md: "minmax(190px, 0.8fr) minmax(0, 2.2fr)",
                  lg: "242px minmax(0, 802px) 260px",
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
          minHeight: hasNavigation && hasSummary ? { lg: 676 } : undefined,
          gap: 0,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          borderRadius: actionBar ? "8px 8px 0 0" : 1,
          overflow: "hidden",
        }}
      >
        {hasNavigation && (
          <Box
            className="wardogs-config-nav"
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
          className="wardogs-config-fields"
          sx={{
            gridArea: "content",
            minWidth: 0,
            pl: { xs: 2, md: 3 },
            pr: { xs: 2, md: 3, lg: 9 },
            pt: { xs: 2, md: 1, lg: 0.625 },
            pb: { xs: 2, md: 1.5 },
          }}
          spacing={2}
        >
          {children}
        </Stack>

        {hasSummary && (
          <Box
            className="wardogs-config-summary"
            sx={{
              gridArea: "summary",
              minWidth: 0,
              p: { xs: 2, md: 3, lg: 2.5 },
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
