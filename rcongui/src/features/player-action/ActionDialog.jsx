import {
  Alert,
  AlertTitle,
  AppBar,
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  Drawer,
  IconButton,
  Stack,
  Toolbar,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useEffect, useRef, useState } from "react";
import { useTranslation } from "react-i18next";
import { ActionForm } from "./ActionForm";
import { useActionDialog } from "@/hooks/useActionDialog";
import { ClientError } from "@/components/shared/ClientError";
import {
  ADMIN_ACTION_RISK,
  requiresSecondConfirmation,
} from "./action-contracts.mjs";

const ActionHeader = ({ title, onClose }) => {
  const { t } = useTranslation();
  return (
    <AppBar color="transparent" elevation={0} position="relative">
      <Toolbar sx={{ minHeight: 56 }}>
        <IconButton
          edge="start"
          color="inherit"
          onClick={onClose}
          aria-label={t("common.close")}
          sx={{ minHeight: 44, minWidth: 44 }}
        >
          <CloseIcon />
        </IconButton>
        <Typography
          id="player-action-dialog-title"
          sx={{ ml: 1, flex: 1 }}
          variant="h6"
          component="h2"
        >
          {title}
        </Typography>
      </Toolbar>
    </AppBar>
  );
};

export const ActionDialog = () => {
  const { t } = useTranslation();
  const { state, closeDialog } = useActionDialog();
  const submitRef = useRef();
  const cancelRef = useRef();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [success, setSuccess] = useState(false);
  const [confirmationStep, setConfirmationStep] = useState(false);
  const [recipientCount, setRecipientCount] = useState(0);
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("md"));
  const { open, action, recipients } = state;

  const title = action
    ? action.translationKey
      ? t(`${action.translationKey}.name`)
      : action.name
    : "";
  const needsSecondConfirmation = requiresSecondConfirmation(
    action?.safety,
    recipientCount
  );
  const isCritical = action?.safety?.risk === ADMIN_ACTION_RISK.CRITICAL;

  const handleClose = () => {
    setError(null);
    setSuccess(false);
    setLoading(false);
    setConfirmationStep(false);
    setRecipientCount(0);
    closeDialog();
  };

  const handleConfirm = () => {
    if (needsSecondConfirmation && !confirmationStep) {
      setConfirmationStep(true);
      window.requestAnimationFrame(() => cancelRef.current?.focus());
      return;
    }
    submitRef.current?.click();
  };

  useEffect(() => {
    setConfirmationStep(false);
    setRecipientCount(recipients?.length ?? 0);
    setError(null);
    setSuccess(false);
  }, [action, open, recipients]);

  useEffect(() => () => setLoading(false), []);

  const actionHandlers = {
    submitRef,
    setError,
    setSuccess,
    setLoading,
    closeDialog: handleClose,
  };

  if (!open || !action) return null;

  const content = (
    <>
      {error ? <ClientError error={error} /> : null}
      {success ? (
        <Alert severity="success" sx={{ mb: 1 }}>
          <AlertTitle>{t("common.success")}</AlertTitle>
          {t("actions.actionSucceeded")}
        </Alert>
      ) : null}
      {action.deprecated ? (
        <Alert severity="warning" sx={{ mb: 1 }}>
          <AlertTitle>{t("actions.deprecated")}</AlertTitle>
          {t("actions.deprecatedNote")}
        </Alert>
      ) : null}
      {confirmationStep ? (
        <Alert severity={isCritical ? "error" : "warning"} sx={{ mb: 1.5 }}>
          <AlertTitle>
            {t("actions.secondConfirmationTitle", {
              defaultValue: "Aktion nochmals prüfen",
            })}
          </AlertTitle>
          {t("actions.secondConfirmationBody", {
            count: recipientCount,
            defaultValue:
              "Diese Aktion wirkt unmittelbar. Prüfe Ziel und Angaben, bevor du sie endgültig ausführst.",
          })}
        </Alert>
      ) : null}
      <Typography
        id="player-action-dialog-description"
        variant="subtitle1"
        sx={{ mb: 1 }}
      >
        {action.translationKey
          ? t(`${action.translationKey}.description`)
          : action.description}
      </Typography>
      <ActionForm
        actionHandlers={actionHandlers}
        locked={confirmationStep}
        onRecipientCountChange={setRecipientCount}
        state={state}
      />
    </>
  );

  const actions = (
    <Stack
      direction="row"
      spacing={1}
      sx={{
        bgcolor: "background.paper",
        borderTop: "1px solid",
        borderColor: "divider",
        flexWrap: "wrap",
        justifyContent: "flex-end",
        p: 1.25,
        pb: compact
          ? "calc(10px + env(safe-area-inset-bottom))"
          : 1.25,
        position: compact ? "sticky" : "static",
        bottom: 0,
        zIndex: 1,
      }}
    >
      <Button
        ref={cancelRef}
        variant="outlined"
        color="secondary"
        onClick={() => {
          if (confirmationStep) {
            setConfirmationStep(false);
            return;
          }
          handleClose();
        }}
        sx={{ flex: { xs: "1 1 100%", sm: "0 0 auto" }, minHeight: 44 }}
      >
        {confirmationStep
          ? t("common.back", { defaultValue: "Zurück" })
          : t("common.cancel")}
      </Button>
      <Button
        variant={confirmationStep ? "contained" : "outlined"}
        color={isCritical ? "error" : "primary"}
        disabled={loading || success || !recipients}
        onClick={handleConfirm}
        sx={{ flex: { xs: "1 1 100%", sm: "0 0 auto" }, minHeight: 44 }}
      >
        {loading
          ? t("common.processing")
          : confirmationStep
            ? t("actions.executeFinally", {
                defaultValue: "Endgültig ausführen",
              })
            : needsSecondConfirmation
              ? t("common.continue", { defaultValue: "Weiter" })
              : t("common.confirm")}
      </Button>
    </Stack>
  );

  if (compact) {
    return (
      <Drawer
        anchor="bottom"
        open={open}
        onClose={handleClose}
        SlideProps={{ onEntered: () => cancelRef.current?.focus() }}
        PaperProps={{
          role: "dialog",
          "aria-modal": "true",
          "aria-labelledby": "player-action-dialog-title",
          "aria-describedby": "player-action-dialog-description",
        }}
        sx={(theme) => ({
          zIndex: theme.zIndex.modal + 1,
          "& .MuiDrawer-paper": {
            backgroundImage: "none",
            bgcolor: "background.paper",
            borderTop: `1px solid ${theme.palette.primary.dark}`,
            maxHeight: "94dvh",
            pl: "env(safe-area-inset-left)",
            pr: "env(safe-area-inset-right)",
          },
        })}
      >
        <ActionHeader title={title} onClose={handleClose} />
        <Box sx={{ flex: "1 1 auto", overflowY: "auto", p: 1.5 }}>
          {content}
        </Box>
        {actions}
      </Drawer>
    );
  }

  return (
    <Dialog
      fullWidth
      maxWidth="sm"
      open={open}
      onClose={handleClose}
      TransitionProps={{ onEntered: () => cancelRef.current?.focus() }}
      aria-labelledby="player-action-dialog-title"
      aria-describedby="player-action-dialog-description"
    >
      <ActionHeader title={title} onClose={handleClose} />
      <DialogContent dividers>{content}</DialogContent>
      <DialogActions sx={{ p: 0 }}>{actions}</DialogActions>
    </Dialog>
  );
};
