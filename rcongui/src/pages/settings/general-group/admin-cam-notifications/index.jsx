import React, { useState } from "react";
import { Alert, Button, ButtonGroup, Stack, Typography } from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useForm } from "react-hook-form";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";
import { cmd } from "@/utils/fetchUtils";
import {
  ControlActionBar,
  ControlPageLayout,
  ControlRow,
  ControlSectionHeader,
  RowStatus,
} from "../ControlPageLayout";

const ADMIN_CAM_KEY = {
  broadcast: "broadcast",
  welcome: "welcome",
};

function ToggleButtons({ value, onChange, disabled, label }) {
  const { t } = useTranslation();
  return (
    <ButtonGroup
      size="small"
      disabled={disabled}
      aria-label={label}
      sx={{ "& .MuiButton-root": { minWidth: 104, borderRadius: 0 } }}
    >
      <Button
        variant={!value ? "contained" : "outlined"}
        color={!value ? "inherit" : "primary"}
        onClick={() => onChange(false)}
      >
        {t("settingsPanels.camera.inactive")}
      </Button>
      <Button
        variant={value ? "contained" : "outlined"}
        onClick={() => onChange(true)}
      >
        {t("settingsPanels.camera.active")}
      </Button>
    </ButtonGroup>
  );
}

function AdminCamSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();
  const [active, setActive] = useState("notifications");
  const [error, setError] = useState("");

  const { data: cameraConfig } = useQuery({
    queryKey: [{ queryIdentifier: "get_camera_notification_config" }],
    queryFn: () =>
      cmd.GET_CAMERA_NOTIFICATION_CONFIG({ throwRouteError: false }),
    initialData: loaderData.cameraConfig,
  });
  const mutation = useMutation({
    mutationFn: (values) =>
      cmd.SET_CAMERA_NOTIFICATION_CONFIG({
        payload: values,
        throwRouteError: false,
      }),
  });

  const form = useForm({
    defaultValues: {
      [ADMIN_CAM_KEY.broadcast]: Boolean(
        cameraConfig?.[ADMIN_CAM_KEY.broadcast]
      ),
      [ADMIN_CAM_KEY.welcome]: Boolean(cameraConfig?.[ADMIN_CAM_KEY.welcome]),
    },
  });

  React.useEffect(() => {
    if (cameraConfig) {
      form.reset({
        [ADMIN_CAM_KEY.broadcast]: Boolean(
          cameraConfig[ADMIN_CAM_KEY.broadcast]
        ),
        [ADMIN_CAM_KEY.welcome]: Boolean(cameraConfig[ADMIN_CAM_KEY.welcome]),
      });
    }
  }, [cameraConfig, form]);

  const setValue = (key, value) => {
    form.setValue(key, value, { shouldDirty: true });
    setError("");
  };

  const save = async () => {
    try {
      const values = form.getValues();
      await mutation.mutateAsync(values);
      form.reset(values);
      queryClient.invalidateQueries({
        queryKey: [{ queryIdentifier: "get_camera_notification_config" }],
      });
      toast.success(t("settings.adminCam.updated"));
    } catch (nextError) {
      setError(nextError.message);
      toast.error(
        t("settings.adminCam.updateFailed", { message: nextError.message })
      );
    }
  };

  const sections = [
    { key: "notifications", label: t("settingsPanels.camera.notifications") },
    { key: "behavior", label: t("settingsPanels.camera.behavior") },
  ];

  return (
    <>
      <ControlPageLayout
        sections={sections}
        active={active}
        onChange={setActive}
      >
        {active === "notifications" ? (
          <>
            <ControlSectionHeader
              title={t("settings.adminCam.title")}
              description={t("settings.adminCam.description")}
            />
            <ControlRow
              title={t("settings.adminCam.broadcast")}
              description={t("settingsPanels.camera.broadcastHelp")}
              value={
                <ToggleButtons
                  label={t("settings.adminCam.broadcast")}
                  value={form.watch(ADMIN_CAM_KEY.broadcast)}
                  onChange={(value) => setValue(ADMIN_CAM_KEY.broadcast, value)}
                  disabled={mutation.isPending}
                />
              }
              meta={
                form.watch(ADMIN_CAM_KEY.broadcast)
                  ? t("settingsPanels.camera.broadcastActive")
                  : t("settingsPanels.camera.broadcastInactive")
              }
              status={
                <RowStatus dirty={form.formState.isDirty} error={error} />
              }
            />
            <ControlRow
              title={t("settings.adminCam.welcome")}
              description={t("settingsPanels.camera.welcomeHelp")}
              value={
                <ToggleButtons
                  label={t("settings.adminCam.welcome")}
                  value={form.watch(ADMIN_CAM_KEY.welcome)}
                  onChange={(value) => setValue(ADMIN_CAM_KEY.welcome, value)}
                  disabled={mutation.isPending}
                />
              }
              meta={
                form.watch(ADMIN_CAM_KEY.welcome)
                  ? t("settingsPanels.camera.welcomeActive")
                  : t("settingsPanels.camera.welcomeInactive")
              }
              status={
                <RowStatus dirty={form.formState.isDirty} error={error} />
              }
            />
          </>
        ) : (
          <>
            <ControlSectionHeader
              title={t("settingsPanels.camera.behavior")}
              description={t("settingsPanels.camera.behaviorHelp")}
            />
            <Stack spacing={1.25} sx={{ p: 2 }}>
              <Alert severity="info" sx={{ borderRadius: 0 }}>
                {t("settingsPanels.camera.cameraOnly")}
              </Alert>
              <Typography variant="body2" color="text.secondary">
                {t("settingsPanels.camera.independent")}
              </Typography>
            </Stack>
          </>
        )}
      </ControlPageLayout>
      <ControlActionBar
        dirtyCount={form.formState.isDirty ? 1 : 0}
        onReset={() => {
          form.reset({
            [ADMIN_CAM_KEY.broadcast]: Boolean(
              cameraConfig?.[ADMIN_CAM_KEY.broadcast]
            ),
            [ADMIN_CAM_KEY.welcome]: Boolean(
              cameraConfig?.[ADMIN_CAM_KEY.welcome]
            ),
          });
          setError("");
        }}
        onSave={save}
        saving={mutation.isPending}
      />
    </>
  );
}

export default AdminCamSettings;
import "@/i18n/register-settings-panels";
