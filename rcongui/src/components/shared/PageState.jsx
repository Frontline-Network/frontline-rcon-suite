import { Box, Button, Skeleton, Stack, Typography } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CloudOffOutlinedIcon from "@mui/icons-material/CloudOffOutlined";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import InboxOutlinedIcon from "@mui/icons-material/InboxOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import SyncProblemOutlinedIcon from "@mui/icons-material/SyncProblemOutlined";
import AutorenewOutlinedIcon from "@mui/icons-material/AutorenewOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";

const STATE_PRESENTATION = {
  empty: { icon: InboxOutlinedIcon, color: "text.secondary" },
  error: { icon: ErrorOutlineIcon, color: "error.main" },
  success: { icon: CheckCircleOutlineIcon, color: "success.main" },
  offline: { icon: CloudOffOutlinedIcon, color: "warning.main" },
  conflict: { icon: SyncProblemOutlinedIcon, color: "warning.main" },
  forbidden: { icon: LockOutlinedIcon, color: "text.secondary" },
  running: { icon: AutorenewOutlinedIcon, color: "info.main" },
  partial: { icon: WarningAmberOutlinedIcon, color: "warning.main" },
  destructive: { icon: ReportProblemOutlinedIcon, color: "error.main" },
};

const alertStates = new Set([
  "error",
  "offline",
  "conflict",
  "forbidden",
  "partial",
  "destructive",
]);

export function PageStateSkeleton({
  label,
  rows = 3,
  compact = false,
  titleComponent = "h2",
}) {
  return (
    <Stack
      component="section"
      aria-busy="true"
      aria-label={label}
      role="status"
      spacing={1}
      sx={{ minHeight: compact ? 120 : 220, p: compact ? 2 : 3 }}
    >
      <Typography
        component={titleComponent}
        variant={compact ? "subtitle1" : "h6"}
        color="text.secondary"
      >
        {label}
      </Typography>
      <Skeleton variant="text" width={compact ? "42%" : "28%"} height={28} />
      {Array.from({ length: rows }, (_, index) => (
        <Skeleton
          key={index}
          variant="rectangular"
          width="100%"
          height={compact ? 34 : 46}
        />
      ))}
    </Stack>
  );
}

export default function PageState({
  kind = "empty",
  title,
  description,
  action,
  actionLabel,
  onAction,
  icon,
  compact = false,
  titleComponent = "h2",
  skeletonRows = 3,
}) {
  if (kind === "loading") {
    return (
      <PageStateSkeleton
        compact={compact}
        label={title}
        rows={skeletonRows}
        titleComponent={titleComponent}
      />
    );
  }

  const presentation = STATE_PRESENTATION[kind] ?? STATE_PRESENTATION.empty;
  const StateIcon = icon ?? presentation.icon;
  const stateAction =
    action ??
    (actionLabel && onAction ? (
      <Button variant="outlined" onClick={onAction}>
        {actionLabel}
      </Button>
    ) : null);

  return (
    <Stack data-theme-surface="panel"
      component="section"
      role={alertStates.has(kind) ? "alert" : "status"}
      aria-live={alertStates.has(kind) ? "assertive" : "polite"}
      alignItems="center"
      justifyContent="center"
      spacing={1}
      sx={{
        minHeight: compact ? 120 : 220,
        border: "1px dashed",
        borderColor: "divider",
        bgcolor: "background.paper",
        px: compact ? 2 : 3,
        py: compact ? 2.5 : 4,
        textAlign: "center",
      }}
    >
      <Box
        sx={{
          color: presentation.color,
          display: "grid",
          placeItems: "center",
        }}
      >
        <StateIcon aria-hidden="true" sx={{ fontSize: compact ? 32 : 40 }} />
      </Box>
      <Typography
        component={titleComponent}
        variant={compact ? "subtitle1" : "h6"}
      >
        {title}
      </Typography>
      {description ? (
        <Typography
          color="text.secondary"
          variant="body2"
          sx={{ maxWidth: 620 }}
        >
          {description}
        </Typography>
      ) : null}
      {stateAction ? <Box sx={{ pt: 0.5 }}>{stateAction}</Box> : null}
    </Stack>
  );
}
