import { Alert, AlertTitle, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";

/**
 * Display an error message to the user
 * @param {Error} error
 */
export function ClientError({ error }) {
  const { t } = useTranslation();
  return (
    <Alert severity="error">
      <AlertTitle>{error.name ?? t("errors.unknown")}</AlertTitle>
      <Typography variant="body2">
        {error.command && `${t("errors.command")}: ${error.command}`}
      </Typography>
      <Typography variant="body2">
        {error?.text ?? error?.message ?? t("errors.requestFailed")}
      </Typography>
    </Alert>
  );
}
