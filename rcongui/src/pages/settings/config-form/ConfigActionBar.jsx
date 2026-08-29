import {
  Box,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";

const renderAction = (action, fallbackVariant, fullWidth = false) => {
  if (!action) return null;
  if (action.node) return action.node;

  return (
    <Button
      key={action.id || action.label}
      data-testid={action.testId}
      type={action.type || "button"}
      form={action.form}
      variant={action.variant || fallbackVariant}
      color={action.color || "primary"}
      size={action.size || "medium"}
      startIcon={
        action.loading ? (
          <CircularProgress color="inherit" size={16} />
        ) : (
          action.startIcon
        )
      }
      onClick={action.onClick}
      disabled={action.disabled || action.loading}
      fullWidth={fullWidth}
      sx={{ textTransform: "none", whiteSpace: "nowrap", ...action.sx }}
    >
      {action.loading && action.loadingLabel
        ? action.loadingLabel
        : action.label}
    </Button>
  );
};

export default function ConfigActionBar({
  stateLabel,
  stateDescription,
  stateIcon,
  primaryAction,
  secondaryActions = [],
  leading,
  dirty = false,
  dirtyLabel,
  sticky = true,
}) {
  return (
    <Box
      component="footer"
      sx={{
        position: sticky ? "sticky" : "static",
        bottom: sticky
          ? {
              xs: "calc(var(--mobile-bottom-nav-height, 0px) + env(safe-area-inset-bottom))",
              sm: 0,
            }
          : "auto",
        zIndex: (theme) => theme.zIndex.appBar - 1,
        mt: 0,
        mx: { xs: -1, sm: 0 },
        px: { xs: 1.5, sm: 3 },
        py: { xs: 1.5, sm: 2 },
        border: "1px solid",
        borderTop: 0,
        borderColor: "divider",
        bgcolor: "background.paper",
        borderRadius: "0 0 8px 8px",
        boxShadow: sticky ? "0 -4px 12px rgba(0,0,0,0.06)" : 0,
        "& .MuiButton-root": {
          width: { xs: "100%", sm: "auto" },
          minHeight: { xs: 44, sm: 36 },
        },
      }}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", sm: "center" }}
        spacing={1.25}
      >
        <Stack
          direction="row"
          spacing={1}
          alignItems="center"
          sx={{ minWidth: 0 }}
        >
          {stateIcon && (
            <Box
              sx={{
                display: "grid",
                placeItems: "center",
                flex: "0 0 auto",
                width: 30,
                height: 30,
                bgcolor: dirty ? "rgba(214, 170, 77, 0.08)" : "action.hover",
                borderRadius: 0.75,
              }}
            >
              {stateIcon}
            </Box>
          )}
          <Box sx={{ minWidth: 0 }}>
            {dirty && dirtyLabel && (
              <Typography
                variant="overline"
                color="warning.main"
                data-testid="config-dirty-indicator"
                sx={{ display: "block", textTransform: "none" }}
              >
                {dirtyLabel}
              </Typography>
            )}
            {stateLabel && (
              <Typography variant="body2" fontWeight={800}>
                {stateLabel}
              </Typography>
            )}
            {stateDescription && (
              <Typography variant="caption" color="text.secondary">
                {stateDescription}
              </Typography>
            )}
            {leading}
          </Box>
        </Stack>

        <Stack
          direction={{ xs: "column-reverse", sm: "row" }}
          spacing={1}
          sx={{ flexShrink: 0 }}
        >
          {secondaryActions.map((action) =>
            renderAction(action, "outlined", false)
          )}
          {renderAction(
            primaryAction
              ? {
                  ...primaryAction,
                  testId: primaryAction.testId || "config-save-button",
                }
              : null,
            "contained",
            false
          )}
        </Stack>
      </Stack>
    </Box>
  );
}
