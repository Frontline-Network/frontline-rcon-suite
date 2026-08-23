import {
  Box,
  List,
  ListItemButton,
  ListItemText,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";

const getSectionLabel = (section) =>
  typeof section.label === "string" ? section.label : section.id;

export default function ConfigSectionNavigation({
  sections = [],
  activeSection,
  onSectionChange,
  label,
  mobileLabel,
}) {
  const selectedSection = sections.some(
    (section) => section.id === activeSection && !section.disabled
  )
    ? activeSection
    : sections.find((section) => !section.disabled)?.id || false;

  const handleChange = (sectionId) => {
    if (sectionId !== selectedSection) onSectionChange?.(sectionId);
  };

  if (!sections.length) return null;

  return (
    <Box component="nav" aria-label={label}>
      <Box sx={{ display: { xs: "block", md: "none" } }}>
        {mobileLabel && (
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ display: "block", mb: 0.75 }}
          >
            {mobileLabel}
          </Typography>
        )}
        <Tabs
          value={selectedSection}
          onChange={(_, value) => handleChange(value)}
          variant="scrollable"
          scrollButtons="auto"
          allowScrollButtonsMobile
          aria-label={label}
          sx={{
            minHeight: 44,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.paper",
            "& .MuiTab-root": {
              minHeight: 44,
              minWidth: "max-content",
              px: 2,
            },
          }}
        >
          {sections.map((section) => (
            <Tab
              key={section.id}
              value={section.id}
              label={getSectionLabel(section)}
              disabled={section.disabled}
            />
          ))}
        </Tabs>
      </Box>

      <Box
        sx={{
          display: { xs: "none", md: "block" },
          p: 3,
        }}
      >
        {label && (
          <Typography
            variant="overline"
            color="text.secondary"
            sx={{ display: "block", mb: 2 }}
          >
            {label}
          </Typography>
        )}
        <List
          disablePadding
          sx={{
            bgcolor: "transparent",
            "& .MuiListItemButton-root, & .MuiListItemText-root": {
              bgcolor: "transparent !important",
            },
          }}
        >
          {sections.map((section, index) => {
            const selected = section.id === selectedSection;

            return (
              <ListItemButton
                key={section.id}
                selected={selected}
                disabled={section.disabled}
                onClick={() => handleChange(section.id)}
                aria-current={selected ? "step" : undefined}
                sx={{
                  position: "relative",
                  minHeight: 60,
                  p: 0,
                  pl: 5.25,
                  alignItems: "flex-start",
                  bgcolor: "transparent",
                  "&:hover, &.Mui-selected, &.Mui-selected:hover": {
                    bgcolor: "transparent",
                  },
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    left: 15,
                    top: index === 0 ? 21 : 0,
                    bottom: index === sections.length - 1 ? 39 : 0,
                    width: 1,
                    bgcolor: "divider",
                  },
                }}
              >
                <Box
                  aria-hidden="true"
                  sx={{
                    position: "absolute",
                    left: 0,
                    top: 6,
                    zIndex: 1,
                    display: "grid",
                    placeItems: "center",
                    width: 32,
                    height: 32,
                    border: "1px solid",
                    borderColor: selected ? "primary.main" : "divider",
                    borderRadius: "50%",
                    bgcolor: selected ? "primary.main" : "background.paper",
                    color: selected ? "primary.contrastText" : "text.secondary",
                    fontSize: 13,
                    fontWeight: 900,
                  }}
                >
                  {index + 1}
                </Box>
                <ListItemText
                  primary={section.label}
                  secondary={section.description}
                  primaryTypographyProps={{
                    fontWeight: selected ? 850 : 700,
                    color: selected ? "primary.main" : "text.primary",
                  }}
                  secondaryTypographyProps={{
                    variant: "caption",
                    sx: { mt: 0.25, lineHeight: 1.35 },
                  }}
                />
              </ListItemButton>
            );
          })}
        </List>
      </Box>
    </Box>
  );
}
