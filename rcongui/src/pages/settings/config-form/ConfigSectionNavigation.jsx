import {
  Box,
  List,
  ListItemButton,
  ListItemText,
  Tab,
  Tabs,
  Typography,
} from "@mui/material";
import CheckIcon from "@mui/icons-material/Check";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import CheckBoxOutlinedIcon from "@mui/icons-material/CheckBoxOutlined";

const completedSectionIcons = {
  operation: <ShieldOutlinedIcon sx={{ fontSize: 15 }} />,
  exemptions: <WarningAmberOutlinedIcon sx={{ fontSize: 15 }} />,
  observation: <CheckBoxOutlinedIcon sx={{ fontSize: 15 }} />,
};

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
          px: 1.5,
          py: 2.125,
        }}
      >
        <List
          disablePadding
          sx={{
            bgcolor: "transparent",
            px: "0 !important",
            ml: 0.25,
            "& .MuiListItemButton-root, & .MuiListItemText-root": {
              bgcolor: "transparent !important",
            },
          }}
        >
          {sections.map((section, index) => {
            const selected = section.id === selectedSection;
            const complete = section.status === "complete" && !selected;

            return (
              <ListItemButton
                key={section.id}
                selected={selected}
                disabled={section.disabled}
                onClick={() => handleChange(section.id)}
                aria-current={selected ? "step" : undefined}
                sx={{
                  position: "relative",
                  minHeight: 72,
                  p: 0,
                  pl: 5.25,
                  alignItems: "flex-start",
                  bgcolor: "transparent",
                  "&:hover, &.Mui-selected, &.Mui-selected:hover": {
                    bgcolor: "transparent",
                  },
                  "&.Mui-focusVisible": {
                    bgcolor: "transparent",
                    boxShadow: "none",
                  },
                  "&::before": {
                    content: '""',
                    position: "absolute",
                    left: 15,
                    top: index === 0 ? 21 : 0,
                    bottom: index === sections.length - 1 ? 51 : 0,
                    width: "1px",
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
                  {complete
                    ? completedSectionIcons[section.id] || (
                        <CheckIcon sx={{ fontSize: 17 }} />
                      )
                    : index + 1}
                </Box>
                <ListItemText
                  sx={{
                    m: 0,
                    mt: 0.5,
                    bgcolor: "transparent !important",
                    "& .MuiTypography-root": {
                      bgcolor: "transparent !important",
                    },
                  }}
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
