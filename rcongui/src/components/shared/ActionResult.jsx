import {
  Alert,
  AlertTitle,
  Box,
  Button,
  CircularProgress,
  Stack,
  Typography,
} from "@mui/material";
import OpenInNewOutlinedIcon from "@mui/icons-material/OpenInNewOutlined";
import ReplayOutlinedIcon from "@mui/icons-material/ReplayOutlined";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";

export const ACTION_RESULT_KINDS = Object.freeze([
  "running",
  "success",
  "partial",
  "error",
  "conflict",
  "forbidden",
  "destructive",
]);

const PRESENTATION = {
  running: { severity: "info", titleKey: "runningTitle" },
  success: { severity: "success", titleKey: "successTitle" },
  partial: { severity: "warning", titleKey: "partialTitle" },
  error: { severity: "error", titleKey: "errorTitle" },
  conflict: { severity: "warning", titleKey: "conflictTitle" },
  forbidden: { severity: "warning", titleKey: "forbiddenTitle" },
  destructive: { severity: "error", titleKey: "destructiveTitle" },
};

const Detail = ({ label, value }) => {
  if (!value) return null;
  return (
    <Box component="div" sx={{ minWidth: 0 }}>
      <Typography
        component="dt"
        variant="caption"
        color="text.secondary"
        sx={{ textTransform: "uppercase", letterSpacing: "0.08em" }}
      >
        {label}
      </Typography>
      <Typography component="dd" variant="body2" sx={{ m: 0 }}>
        {value}
      </Typography>
    </Box>
  );
};

export default function ActionResult({ result, compact = false }) {
  const { t } = useTranslation();
  if (!result) return null;

  const presentation = PRESENTATION[result.kind] ?? PRESENTATION.error;
  const isAssertive = ["error", "conflict", "forbidden", "destructive"].includes(
    result.kind
  );
  const details = [
    [t("common.actionResult.target"), result.target],
    [t("common.actionResult.time"), result.time],
    [t("common.actionResult.system"), result.system],
    [t("common.actionResult.cause"), result.cause],
    [t("common.actionResult.retained"), result.retainedConfiguration],
    [t("common.actionResult.nextStep"), result.nextAction],
  ].filter(([, value]) => Boolean(value));

  return (
    <Alert
      severity={presentation.severity}
      role={isAssertive ? "alert" : "status"}
      aria-live={isAssertive ? "assertive" : "polite"}
      icon={
        result.kind === "running" ? (
          <CircularProgress color="inherit" size={20} />
        ) : undefined
      }
      sx={{
        borderRadius: 0,
        alignItems: "flex-start",
        py: compact ? 0.75 : 1,
      }}
    >
      <AlertTitle sx={{ mb: result.description || details.length ? 0.5 : 0 }}>
        {result.title ||
          t(`common.actionResult.${presentation.titleKey}`)}
      </AlertTitle>
      {result.description ? (
        <Typography variant="body2">{result.description}</Typography>
      ) : null}
      {details.length ? (
        <Box
          component="dl"
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              lg: "repeat(3, minmax(0, 1fr))",
            },
            gap: 1,
            m: 0,
            mt: 1,
          }}
        >
          {details.map(([label, value]) => (
            <Detail key={label} label={label} value={value} />
          ))}
        </Box>
      ) : null}
      {result.onRetry || result.auditHref ? (
        <Stack direction={{ xs: "column", sm: "row" }} gap={1} sx={{ mt: 1 }}>
          {result.onRetry ? (
            <Button
              size="small"
              variant="outlined"
              color="inherit"
              startIcon={<ReplayOutlinedIcon />}
              onClick={result.onRetry}
            >
              {result.retryLabel || t("common.retry")}
            </Button>
          ) : null}
          {result.auditHref ? (
            <Button
              component={Link}
              to={result.auditHref}
              size="small"
              variant="outlined"
              color="inherit"
              startIcon={<OpenInNewOutlinedIcon />}
            >
              {result.auditLabel || t("common.actionResult.openAudit")}
            </Button>
          ) : null}
        </Stack>
      ) : null}
    </Alert>
  );
}
