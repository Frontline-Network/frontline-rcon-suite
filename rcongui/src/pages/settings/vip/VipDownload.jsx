import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import {
  Alert,
  Button,
  Stack,
  TextField,
  CircularProgress,
  InputAdornment,
} from "@mui/material";
import { FileDownload } from "@mui/icons-material";
import { useTranslation } from "react-i18next";

const VipDownload = () => {
  const { t } = useTranslation();
  const [downloadEnabled, setDownloadEnabled] = useState(false);
  const [downloadCompleted, setDownloadCompleted] = useState(false);
  const [filename, setFilename] = useState("hll_vips");
  const [numLines, setNumLines] = useState(0);
  const fullFilename = `${filename}.txt`;

  const {
    data: fileURL,
    isFetching: isDownloadingVipFile,
    isSuccess: isDownloadingVipFileSuccess,
    isError: isDownloadingVipFileError,
  } = useQuery({
    queryKey: [{ queryIdentifier: "download_vip_file" }],
    queryFn: async () => {
      const text = await cmd.DOWNLOAD_VIP_FILE();

      // get number of lines - vip records
      const numLines = text.split("\n").length;
      setNumLines(numLines);

      const file = new Blob([text], { type: "text/plain" });
      const url = URL.createObjectURL(file);

      setDownloadEnabled(false);
      setDownloadCompleted(true);

      return url;
    },
    enabled: downloadEnabled,
  });

  const handleClear = () => {
    setDownloadCompleted(false);
    setDownloadEnabled(false);
    setNumLines(0);
    setFilename("hll_vips");
    URL.revokeObjectURL(fileURL);
  }

  const handleSave = () => {
    if (fileURL) {
      setTimeout(() => {
        handleClear();
      }, 1000);
    }
  };

  return (
    <Stack spacing={2}>
      {!downloadCompleted && (
        <Button
          variant="contained"
          startIcon={
            isDownloadingVipFile ? (
              <CircularProgress size={16} />
            ) : (
              <FileDownload />
            )
          }
          disabled={isDownloadingVipFile}
          onClick={() => setDownloadEnabled(true)}
        >
          {t("records.vips.getFile")}
        </Button>
      )}
      {isDownloadingVipFileError && (
        <Alert severity="error">{t("records.vips.downloadError")}</Alert>
      )}
      {isDownloadingVipFileSuccess && downloadCompleted && (
          <>
          <TextField
            value={filename}
            onChange={(e) => setFilename(e.target.value)}
            helperText={t("records.vips.recordsFound", { count: numLines })}
            slotProps={{
              input: {
                endAdornment: (
                  <InputAdornment position="end">.txt</InputAdornment>
                ),
              },
            }}
          />
          <Stack direction="row" spacing={1}>
            <Button fullWidth variant="outlined" color="error" onClick={handleClear}>{t("common.cancel")}</Button>
            <Button
            fullWidth
            LinkComponent={"a"}
            onClick={handleSave}
            href={fileURL}
            download={fullFilename}
            variant="contained"
          >
            {t("common.save")}
            </Button>
          </Stack>
        </>
      )}
    </Stack>
  );
};

export default VipDownload;
