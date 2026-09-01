import { ToggleButton, ToggleButtonGroup } from "@mui/material";

export const getOperationMode = (data = {}, supportsDryRun = true) =>
  !data.enabled
    ? "off"
    : supportsDryRun && data.dry_run
    ? "observe"
    : "active";

export default function ConfigOperationModeControl({
  data,
  disabled = false,
  onChange,
  supportsDryRun = true,
  ariaLabel,
  labels,
}) {
  const mode = getOperationMode(data, supportsDryRun);

  return (
    <ToggleButtonGroup
      value={mode}
      exclusive
      disabled={disabled}
      onChange={(_, nextMode) => {
        if (!nextMode) return;
        onChange?.(
          supportsDryRun
            ? {
                enabled: nextMode !== "off",
                dry_run: nextMode === "observe",
              }
            : { enabled: nextMode === "active" }
        );
      }}
      aria-label={ariaLabel}
      size="small"
      sx={{
        width: { xs: "100%", sm: "auto" },
        "& .MuiToggleButton-root": {
          flex: { xs: 1, sm: "0 0 auto" },
          minHeight: 44,
          minWidth: { xs: 0, sm: 112 },
          px: { xs: 1.25, sm: 2 },
          borderRadius: 0,
          textTransform: "none",
          fontWeight: 800,
        },
        "& .MuiToggleButton-root.Mui-selected": {
          bgcolor: mode === "active" ? "success.dark" : "action.selected",
          color: mode === "active" ? "success.contrastText" : "text.primary",
        },
      }}
    >
      <ToggleButton value="off">{labels.off}</ToggleButton>
      {supportsDryRun && (
        <ToggleButton value="observe">{labels.observe}</ToggleButton>
      )}
      <ToggleButton value="active">{labels.active}</ToggleButton>
    </ToggleButtonGroup>
  );
}
