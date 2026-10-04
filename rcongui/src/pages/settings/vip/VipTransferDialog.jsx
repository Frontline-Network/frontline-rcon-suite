import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Stack,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import FileDownloadOutlinedIcon from "@mui/icons-material/FileDownloadOutlined";
import FileUploadOutlinedIcon from "@mui/icons-material/FileUploadOutlined";
import { useTranslation } from "react-i18next";
import VipDownload from "./VipDownload";
import VipUpload from "./VipUpload";

const TransferSection = ({ icon, title, description, children }) => (
  <Stack data-theme-surface="panel"
    gap={1.5}
    sx={{
      border: "1px solid",
      borderColor: "divider",
      p: 2,
      minWidth: 0,
    }}
  >
    <Stack direction="row" gap={1} alignItems="center">
      {icon}
      <Typography variant="subtitle1" fontWeight={700}>
        {title}
      </Typography>
    </Stack>
    <Typography variant="body2" color="text.secondary">
      {description}
    </Typography>
    <Box sx={{ mt: "auto" }}>{children}</Box>
  </Stack>
);

export default function VipTransferDialog({ open, onClose }) {
  const { t } = useTranslation();
  const theme = useTheme();
  const fullScreen = useMediaQuery(theme.breakpoints.down("sm"));

  return (
    <Dialog
      open={open}
      onClose={onClose}
      fullWidth
      maxWidth="md"
      fullScreen={fullScreen}
      PaperProps={{ sx: { borderRadius: 0 } }}
    >
      <DialogTitle>
        <Typography
          component="span"
          variant="overline"
          color="primary.main"
          sx={{ display: "block", letterSpacing: "0.14em" }}
        >
          {t("records.vips.maintenance")}
        </Typography>
        {t("records.vips.importExport")}
      </DialogTitle>
      <DialogContent dividers sx={{ p: { xs: 2, sm: 2.5 } }}>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 1.5,
          }}
        >
          <TransferSection
            icon={<FileDownloadOutlinedIcon color="primary" />}
            title={t("records.vips.downloadTitle")}
            description={t("records.vips.downloadDescription")}
          >
            <VipDownload />
          </TransferSection>
          <TransferSection
            icon={<FileUploadOutlinedIcon color="warning" />}
            title={t("records.vips.uploadTitle")}
            description={t("records.vips.uploadDescription")}
          >
            <VipUpload />
          </TransferSection>
        </Box>
      </DialogContent>
      <DialogActions sx={{ p: 1.5 }}>
        <Button onClick={onClose}>{t("common.close")}</Button>
      </DialogActions>
    </Dialog>
  );
}
