import {
  Box,
  Stack,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";

export default function ConfigModeSwitch({
  value,
  options = [],
  onChange,
  label,
  ariaLabel,
  description,
  disabled = false,
  fullWidth = false,
}) {
  const handleChange = (_, nextValue) => {
    if (nextValue !== null && nextValue !== value) onChange?.(nextValue);
  };

  return (
    <Stack spacing={0.75} data-testid="config-mode-toggle">
      {(label || description) && (
        <Box>
          {label && (
            <Typography variant="body2" fontWeight={800}>
              {label}
            </Typography>
          )}
          {description && (
            <Typography variant="caption" color="text.secondary">
              {description}
            </Typography>
          )}
        </Box>
      )}
      <ToggleButtonGroup
        exclusive
        value={value}
        onChange={handleChange}
        disabled={disabled}
        fullWidth={fullWidth}
        aria-label={ariaLabel || label}
        size="small"
        sx={{
          width: fullWidth ? "100%" : "fit-content",
          "& .MuiToggleButton-root": {
            minWidth: "auto",
            minHeight: 44,
            borderRadius: 0,
            px: 1.625,
            py: 0.45,
            fontSize: 10.5,
            fontWeight: 800,
            textTransform: "none",
          },
          "& .MuiToggleButton-root.Mui-selected": {
            bgcolor: "primary.main",
            color: "primary.contrastText",
            "&:hover": { bgcolor: "primary.dark" },
          },
        }}
      >
        {options.map((option) => (
          <ToggleButton
            key={option.value}
            value={option.value}
            disabled={option.disabled}
            aria-label={option.ariaLabel || option.label}
            sx={{ gap: 0.75 }}
          >
            {option.icon}
            {option.label}
          </ToggleButton>
        ))}
      </ToggleButtonGroup>
    </Stack>
  );
}
