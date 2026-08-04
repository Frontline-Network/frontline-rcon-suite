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
        <IconButton onClick={handleClose}>
          <CloseIcon />
        </IconButton>
      }
    >
      <AlertTitle>{t("errors.sectionUnavailable")}</AlertTitle>
      <Typography>
        {error?.message ?? error?.statusText ?? t("errors.requestFailed")}
      </Typography>
    </Alert>
  );
}
