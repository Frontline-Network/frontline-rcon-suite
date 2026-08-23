import {
  Alert,
  AlertTitle,
  Button,
  List,
  ListItem,
  ListItemText,
  Stack,
  Typography,
} from "@mui/material";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";

export default function ConfigValidationSummary({
  errors = [],
  title,
  description,
  onNavigate,
  navigateLabel,
}) {
  if (!errors.length) return null;

  return (
    <Alert severity="error" data-testid="config-error-summary">
      {title && <AlertTitle>{title}</AlertTitle>}
      {description && (
        <Typography variant="body2" sx={{ mb: 0.5 }}>
          {description}
        </Typography>
      )}
      <List dense disablePadding>
        {errors.map((error, index) => {
          const normalizedError =
            typeof error === "string" ? { id: error, message: error } : error;

          return (
            <ListItem
              key={normalizedError.id || `${normalizedError.message}-${index}`}
              disableGutters
              secondaryAction={
                onNavigate && normalizedError.sectionId ? (
                  <Button
                    size="small"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() =>
                      onNavigate(normalizedError.sectionId, normalizedError)
                    }
                  >
                    {normalizedError.navigateLabel || navigateLabel}
                  </Button>
                ) : null
              }
              sx={{ pr: onNavigate && normalizedError.sectionId ? 12 : 0 }}
            >
              <ListItemText
                primary={normalizedError.label}
                secondary={normalizedError.message}
                primaryTypographyProps={{ fontWeight: 750 }}
              />
            </ListItem>
          );
        })}
      </List>
    </Alert>
  );
}
