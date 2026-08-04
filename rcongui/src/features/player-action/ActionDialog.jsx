import {
  Alert,
  AlertTitle,
  AppBar,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  IconButton,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import { ActionForm } from "./ActionForm";
import { useActionDialog } from "@/hooks/useActionDialog";
import CloseIcon from "@mui/icons-material/Close";
import { ClientError } from "@/components/shared/ClientError";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";

export const ActionDialog = () => {
  const { t } = useTranslation();
  const { state, closeDialog } = useActionDialog();
  const submitRef = useRef();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("md"));
  const { open, action, recipients } = state;

  const handleLoading = (state) => {
    setLoading(state);
  };

  const handleClose = () => {
    setError(null);
    setSuccess(false);
    setLoading(false);
    closeDialog();
  };

  const handleConfirm = () => {
    submitRef.current.click();
  };

  useEffect(() => {
    return () => {
      setLoading(false);
    };
  }, []);

  const actionHandlers = {
    submitRef,
    setError,
    setSuccess,
    setLoading: handleLoading,
    closeDialog: handleClose,
  };

  if (!open) return null;

  return (
    <Dialog
      fullWidth
      fullScreen={fullScreen}
      open={open}
      onClose={handleClose}
      aria-labelledby="alert-dialog-title"
      aria-describedby="alert-dialog-description"
    >
      <AppBar sx={{ position: "relative" }}>
        <Toolbar>
          <IconButton
            edge="start"
            color="inherit"
            onClick={handleClose}
            aria-label={t("common.close")}
          >
            <CloseIcon />
          </IconButton>
          <Typography sx={{ ml: 2, flex: 1 }} variant="h6" component="div">
            {action.translationKey ? t(`${action.translationKey}.name`) : action.name}
          </Typography>
          <Button
            variant="outlined"
            color="primary"
            disabled={loading || !action || !recipients}
            onClick={handleConfirm}
            autoFocus
          >
            {loading ? t("common.processing") : t("common.confirm")}
          </Button>
        </Toolbar>
      </AppBar>
      <DialogContent dividers>
        {error && <ClientError error={error} />}
        {success && (
          <Alert severity="success" sx={{ mb: 1 }}>
            <AlertTitle>{t("common.success")}</AlertTitle>
            {t("actions.actionSucceeded")}
          </Alert>
        )}
        {action.deprecated && (
          <Alert severity="warning" sx={{ mb: 1 }}>
            <AlertTitle>{t("actions.deprecated")}</AlertTitle>
            {t("actions.deprecatedNote")}
          </Alert>
        )}
        <Typography variant="subtitle1" sx={{ mb: 1 }}>
          {action.translationKey ? t(`${action.translationKey}.description`) : action.description}
        </Typography>
        <ActionForm actionHandlers={actionHandlers} state={state} />
      </DialogContent>
      <DialogActions>
        <Button variant="outlined" color="secondary" onClick={handleClose}>
          {t("common.cancel")}
        </Button>
        <Button
          variant="outlined"
          color="primary"
          disabled={loading || !action || !recipients}
          onClick={handleConfirm}
          autoFocus
        >
          {loading ? t("common.processing") : t("common.confirm")}
        </Button>
      </DialogActions>
    </Dialog>
  );
};
