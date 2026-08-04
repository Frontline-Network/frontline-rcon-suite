import { useClipboard } from "@/hooks/useClipboard";
import {
  Button,
  Dialog,
  DialogContent,
  Typography,
  Tooltip,
  IconButton,
} from "@mui/material";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DoneAllIcon from "@mui/icons-material/DoneAll";
import { useState } from "react";
import { useTranslation } from "react-i18next";

export default function CopyToClipboardButton({
  text,
  title,
  iconOnly = false,
  ...props
}) {
  const { t } = useTranslation();
  const { isClipboardAvailable, isCopied, copyToClipboard } = useClipboard();
  const [dialogOpen, setDialogOpen] = useState(false);

  const handleClick = () => {
    if (isClipboardAvailable) {
      copyToClipboard(text);
    } else {
      setDialogOpen(true);
    }
  };

  return (
    <>
      <Tooltip title={isCopied ? t("common.copied") : (title ?? t("common.copy"))}>
        {iconOnly ? (
          <IconButton
            variant="outlined"
            color="warning"
            onClick={handleClick}
            {...props}
          >
            {isCopied ? <DoneAllIcon /> : <ContentCopyIcon />}
          </IconButton>
        ) : (
          <Button
            variant="outlined"
            color="warning"
            onClick={handleClick}
            startIcon={isCopied ? <DoneAllIcon /> : <ContentCopyIcon />}
            {...props}
          >
            {isCopied ? t("common.copied") : t("common.copy")}
          </Button>
        )}
      </Tooltip>
      <Dialog open={dialogOpen} onClose={() => setDialogOpen(false)}>
        <DialogContent>
          <Typography>{t("common.clipboardHttps")}</Typography>
        </DialogContent>
        <DialogContent>
          <Typography>{text}</Typography>
        </DialogContent>
      </Dialog>
    </>
  );
}
