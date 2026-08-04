import {
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
} from "@mui/material";
import { useState } from "react";
import { useTranslation } from "react-i18next";

const ConfirmButton = ({
  onConfirm,
  title,
  description,
  buttonText,
  confirmText,
  cancelText,
  buttonProps = {},
  disabled = false,
}) => {
  const [open, setOpen] = useState(false);
  const { t } = useTranslation();

  const handleConfirm = () => {
    onConfirm();
    setOpen(false);
  };

  return (
    <>
      <Button
        {...buttonProps}
        disabled={disabled}
        onClick={() => setOpen(true)}
      >
        {buttonText}
      </Button>
      <Dialog
        open={open}
        onClose={() => setOpen(false)}
        aria-labelledby="confirm-dialog-title"
        aria-describedby="confirm-dialog-description"
      >
        <DialogTitle id="confirm-dialog-title">{title}</DialogTitle>
        <DialogContent>
          <DialogContentText id="confirm-dialog-description">
            {description}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setOpen(false)} color="warning">
            {cancelText ?? t("common.cancel")}
          </Button>
          <Button onClick={handleConfirm} color="primary" autoFocus>
            {confirmText ?? t("common.confirm")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default ConfirmButton; 
