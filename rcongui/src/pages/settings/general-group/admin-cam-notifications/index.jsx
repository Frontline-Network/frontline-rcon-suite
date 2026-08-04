import React from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid2 as Grid,
  Stack,
  Typography,
} from "@mui/material";
import SaveIcon from "@mui/icons-material/Save";
import VideoCamIcon from "@mui/icons-material/Videocam";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useLoaderData } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import { toast } from "react-toastify";
import { ToggleInput } from "../components";
import { useTranslation } from "react-i18next";

const ADMIN_CAM_KEY = {
  broadcast: "broadcast",
  welcome: "welcome",
};

function AdminCamSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();

  const { data: cameraConfig } = useQuery({
    queryKey: [{ queryIdentifier: "get_camera_notification_config" }],
    queryFn: () => cmd.GET_CAMERA_NOTIFICATION_CONFIG({ throwRouteError: false }),
    initialData: loaderData.cameraConfig,
  });

  const { mutate, isPending } = useMutation({
    mutationFn: (values) =>
      cmd.SET_CAMERA_NOTIFICATION_CONFIG({ payload: values, throwRouteError: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [{ queryIdentifier: "get_camera_notification_config" }],
      });
      toast.success(t("settings.adminCam.updated"));
    },
    onError: (error) => {
      toast.error(t("settings.adminCam.updateFailed", { message: error.message }));
    },
  });

  const form = useForm({
    defaultValues: {
      [ADMIN_CAM_KEY.broadcast]: cameraConfig?.[ADMIN_CAM_KEY.broadcast] || false,
      [ADMIN_CAM_KEY.welcome]: cameraConfig?.[ADMIN_CAM_KEY.welcome] || false,
    },
  });

  React.useEffect(() => {
    if (cameraConfig) {
      form.reset({
        [ADMIN_CAM_KEY.broadcast]: cameraConfig[ADMIN_CAM_KEY.broadcast],
        [ADMIN_CAM_KEY.welcome]: cameraConfig[ADMIN_CAM_KEY.welcome],
      });
    }
  }, [cameraConfig, form]);

  const onSubmit = form.handleSubmit((values) => mutate(values));

  return (
    <Grid container spacing={3}>
      <Grid size={{ xs: 12, md: 6 }}>
        <Card elevation={2}>
          <CardHeader
            avatar={<VideoCamIcon color="primary" />}
            title={t("settings.adminCam.title")}
            subheader={t("settings.adminCam.subtitle")}
            action={
              <Button
                type="submit"
                form="admin-cam-form"
                variant="contained"
                size="small"
                startIcon={<SaveIcon />}
                disabled={form.formState.isSubmitting || isPending}
              >
                {isPending ? t("common.processing") : t("common.save")}
              </Button>
            }
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Box component="form" id="admin-cam-form" onSubmit={onSubmit}>
              <Stack gap={2}>
                <Typography variant="body1" color="text.secondary">
                  {t("settings.adminCam.description")}
                </Typography>

                <ToggleInput
                  keyName={ADMIN_CAM_KEY.broadcast}
                  title={t("settings.adminCam.broadcast")}
                  value={form.watch(ADMIN_CAM_KEY.broadcast)}
                  onChange={(checked) =>
                    form.setValue(ADMIN_CAM_KEY.broadcast, checked)
                  }
                />

                <ToggleInput
                  keyName={ADMIN_CAM_KEY.welcome}
                  title={t("settings.adminCam.welcome")}
                  value={form.watch(ADMIN_CAM_KEY.welcome)}
                  onChange={(checked) =>
                    form.setValue(ADMIN_CAM_KEY.welcome, checked)
                  }
                />
              </Stack>
            </Box>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

export default AdminCamSettings;
