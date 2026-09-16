import {
  Alert,
  AlertTitle,
  IconButton,
  Typography,
} from "@mui/material";
import { useAsyncError } from "react-router-dom";
import VisibilityOffIcon from "@mui/icons-material/VisibilityOff";
import CloseIcon from "@mui/icons-material/Close";
import { useState } from "react";
import { useTranslation } from "react-i18next";
import { translateOperatorMessage } from "@/i18n/operator-messages";

export function AsyncClientError() {
  const { t } = useTranslation();
  const error = useAsyncError();
  const [open, setOpen] = useState(true);

  const handleClose = () => {
    setOpen(false);
  };

  if (!open) return null;

  return (
    <Alert
      component={"section"}
      severity={"info"}
      icon={<VisibilityOffIcon fontSize="inherit" />}
      action={
        <IconButton onClick={handleClose} aria-label={t("common.close")}>
          <CloseIcon />
        </IconButton>
      }
    >
      <AlertTitle>{t("errors.sectionUnavailable")}</AlertTitle>
      <Typography>
        {translateOperatorMessage(error?.message ?? error?.statusText, t) ?? t("errors.requestFailed")}
      </Typography>
    </Alert>
  );
}
