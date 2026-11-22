import { useState, useEffect } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";
import {
  Alert,
  Button,
  Stack,
  CircularProgress,
  Typography,
} from "@mui/material";
import { CloudUpload } from "@mui/icons-material";
import { InputFileUpload } from "@/components/shared/InputFileUpload";
import { vipQueryKeys } from "@/queries/vip-query";
import { useTranslation } from "react-i18next";

const POLL_INTERVAL = 2000; // 2 seconds

const VipUpload = () => {
  const { t } = useTranslation();
  const [showWarning, setShowWarning] = useState(false);
  const [uploadId, setUploadId] = useState(null);
  const [status, setStatus] = useState(null);
  const [result, setResult] = useState(null);
  const queryClient = useQueryClient();

  const { mutate: uploadVips } = useMutation({
    mutationFn: async (file) => {
      const formData = new FormData();
      formData.append("File", file);

      formData.append("track_job", "1");

      return cmd.UPLOAD_VIP_FILE({ payload: formData, headers: {} });
    },
    onSuccess: (data) => {
      if (data?.failed || data?.result?.failed) {
        setUploadId(null);
        setResult(data?.error?.split("\n"));
        setStatus("error");
        return;
      }
      setUploadId(data?.result?.upload_id || true);
      setStatus("started");
    },
    onError: () => {
      setUploadId(null);
      setStatus("error");
    },
  });

  // Poll for upload status
  const { data: uploadStatus } = useQuery({
    queryKey: [{ queryIdentifier: "vip_upload_status", uploadId }],
    queryFn: () => cmd.GET_UPLOAD_VIP_FILE_RESPONSE({ params: typeof uploadId === "string" ? { upload_id: uploadId } : {} }),
    enabled: !!uploadId,
    refetchInterval: POLL_INTERVAL,
  });

  // Handle status changes with an effect
  useEffect(() => {
    if (!uploadId || !uploadStatus) return;

    switch (uploadStatus.status) {
      case "started":
        setStatus("started");
        break;
      case "finished":
        setResult(uploadStatus.result);
        setStatus(uploadStatus.result?.length === 1 && uploadStatus.result[0] === "ALL OK"
          ? "finished" : "error");
        setUploadId(null);
        queryClient.invalidateQueries({ queryKey: vipQueryKeys.list });
        break;
      case "failed":
      case "stopped":
      case "canceled":
        setStatus("error");
        setUploadId(null);
        break;
      default:
        break;
    }
  }, [uploadId, uploadStatus, queryClient]);

  const handleInitialUpload = () => {
    setShowWarning(true);
  };

  const reset = () => {
    setShowWarning(false);
    setStatus(null);
    setUploadId(null);
    setResult(null);
  };

  const handleFileUpload = (event) => {
    const file = event.target.files[0];
    if (file) {
      uploadVips(file);
    }
  };

  if (status === "started") {
    return (
      <Stack spacing={2} alignItems="center">
        <CircularProgress size={24} />
        <Alert severity="info">{t("records.vips.uploadProcessing")}</Alert>
      </Stack>
    );
  }

  if (status === "finished") {
    return (
      <Stack spacing={2}>
        <Alert severity="success">{t("records.vips.uploadFinished")}</Alert>
        {result?.map((message) => (
          <Typography key={message}>{message}</Typography>
        ))}
        <Button variant="contained" onClick={reset}>
          {t("common.confirm")}
        </Button>
      </Stack>
    );
  }

  if (status === "error") {
    return (
      <Stack spacing={2}>
        <Alert severity="error">{t("records.vips.uploadError")}</Alert>
        {result?.map((message) => <Typography key={message}>{message}</Typography>)}
        <Button variant="outlined" onClick={reset}>
          {t("common.retry")}
        </Button>
      </Stack>
    );
  }

  if (showWarning) {
    return (
      <Stack spacing={2}>
        <Alert severity="warning">{t("records.vips.uploadWarning")}</Alert>
        <Stack direction="row" spacing={1}>
          <Button fullWidth variant="outlined" color="error" onClick={reset}>
            {t("common.cancel")}
          </Button>
          <InputFileUpload
            text={t("records.vips.uploadFile")}
            color="primary"
            variant="contained"
            onChange={handleFileUpload}
            accept=".txt"
            fullWidth
            sx={{ whiteSpace: "nowrap" }}
          />
        </Stack>
      </Stack>
    );
  }

  return (
    <Button
      variant="contained"
      startIcon={<CloudUpload />}
      onClick={handleInitialUpload}
      fullWidth
    >
      {t("records.vips.uploadFromFile")}
    </Button>
  );
};

export default VipUpload;
