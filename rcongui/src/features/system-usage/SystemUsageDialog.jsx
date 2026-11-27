import { lazy, Suspense } from "react";
import {
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Typography,
} from "@mui/material";
import CloseIcon from "@mui/icons-material/Close";
import { useTranslation } from "react-i18next";

const ResourceTelemetryCard = lazy(() =>
  import("@/components/cards/ResourceTelemetryCard")
);

export default function SystemUsageDialog({ onClose }) {
  const { t } = useTranslation();
  return (
    <Dialog
      open
      onClose={onClose}
      fullWidth
      maxWidth="md"
      aria-labelledby="system-usage-dialog-title"
    >
      <DialogTitle id="system-usage-dialog-title" sx={{ pr: 6 }}>
        {t("dashboard.resources.title")}
        <IconButton
          aria-label={t("common.close")}
          onClick={onClose}
          sx={{ position: "absolute", top: 8, right: 8 }}
        >
          <CloseIcon />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ px: { xs: 1, sm: 2 }, pb: 2 }}>
        <Suspense fallback={<Typography>{t("common.loading")}</Typography>}>
          <ResourceTelemetryCard embedded />
        </Suspense>
      </DialogContent>
    </Dialog>
  );
}
