import React, { useState } from "react";
import { Alert, Box, Stack, TextField, Typography } from "@mui/material";
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

function ServerNameSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();
  const [active, setActive] = useState("name");
  const [errors, setErrors] = useState({});

  const { data: serverName } = useQuery({
    queryKey: [{ queryIdentifier: "get_server_name" }],
    queryFn: () => cmd.GET_SERVER_NAME({ throwRouteError: false }),
    initialData: loaderData.serverName,
  });
  const { data: serverNameConfig } = useQuery({
    queryKey: [{ queryIdentifier: "get_server_name_change_config" }],
    queryFn: () =>
      cmd.GET_SERVER_NAME_CHANGE_CONFIG({ throwRouteError: false }),
    initialData: loaderData.serverNameConfig,
  });

  const serverNameMutation = useMutation({
    mutationFn: (newName) =>
      cmd.SET_SERVER_NAME({
        payload: { name: newName },
        throwRouteError: false,
      }),
  });
  const configMutation = useMutation({
    mutationFn: (newConfig) =>
      cmd.SET_SERVER_NAME_CHANGE_CONFIG({
        payload: newConfig,
        throwRouteError: false,
      }),
  });

  const nameForm = useForm({ defaultValues: { serverName: serverName || "" } });
  const configForm = useForm({ defaultValues: serverNameConfig || {} });

  React.useEffect(() => {
    if (serverName !== undefined) nameForm.reset({ serverName });
  }, [serverName, nameForm]);
  React.useEffect(() => {
    if (serverNameConfig) configForm.reset(serverNameConfig);
  }, [serverNameConfig, configForm]);

  const dirtyCount =
    Number(nameForm.formState.isDirty) + Number(configForm.formState.isDirty);
  const saving = serverNameMutation.isPending || configMutation.isPending;

  const resetAll = () => {
    nameForm.reset({ serverName });
    configForm.reset(serverNameConfig || {});
    setErrors({});
  };

  const saveAll = async () => {
    const nextErrors = {};
    if (nameForm.formState.isDirty) {
      try {
        const value = nameForm.getValues("serverName");
        await serverNameMutation.mutateAsync(value);
        nameForm.reset({ serverName: value });
        queryClient.invalidateQueries({
          queryKey: [{ queryIdentifier: "get_server_name" }],
        });
      } catch (error) {
        nextErrors.name = error.message;
      }
    }
    if (configForm.formState.isDirty) {
      try {
        const value = configForm.getValues();
        await configMutation.mutateAsync(value);
        configForm.reset(value);
        queryClient.invalidateQueries({
          queryKey: [{ queryIdentifier: "get_server_name_change_config" }],
        });
      } catch (error) {
        nextErrors.connection = error.message;
      }
    }
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length) {
      toast.error(t("settings.serverName.updateFailed"));
    } else {
      toast.success(t("settings.serverName.updated"));
    }
  };

  const sections = [
    { key: "name", label: t("settings.serverName.title") },
    { key: "connection", label: t("settings.serverName.sftpTitle") },
    { key: "requirements", label: t("settings.serverName.requirements") },
  ];

  return (
    <>
      <ControlPageLayout
        sections={sections}
        active={active}
        onChange={setActive}
      >
        {active === "name" && (
          <>
            <ControlSectionHeader
              title={t("settings.serverName.title")}
              description={t("settings.serverName.subtitle")}
            />
            <ControlRow
              title={t("settings.serverName.title")}
              description={t("settings.serverName.helper")}
              value={
                <TextField
                  {...nameForm.register("serverName")}
                  placeholder={t("settings.serverName.placeholder")}
                  fullWidth
                  size="small"
                  inputProps={{ "aria-label": t("settings.serverName.title") }}
                  sx={{ "& .MuiOutlinedInput-root": { borderRadius: 0 } }}
                />
              }
              meta={serverName || "—"}
              status={
                <RowStatus
                  dirty={nameForm.formState.isDirty}
                  error={errors.name}
                />
              }
            />
          </>
        )}

        {active === "connection" && (
          <>
            <ControlSectionHeader
              title={t("settings.serverName.sftpTitle")}
              description={t("settings.serverName.sftpSubtitle")}
            />
            <ControlRow
              title={t("settings.serverName.sftpHost")}
              description={t("settings.serverName.sftpHostDescription")}
              value={
                <TextField
                  {...configForm.register("ip")}
                  placeholder="168.10.0.1"
                  fullWidth
                  size="small"
                  inputProps={{
                    "aria-label": t("settings.serverName.sftpHost"),
                  }}
                  sx={{ "& .MuiOutlinedInput-root": { borderRadius: 0 } }}
                />
              }
              meta={
                serverNameConfig?.ip || t("settings.serverName.notConfigured")
              }
              status={
                <RowStatus
                  dirty={configForm.formState.isDirty}
                  error={errors.connection}
                />
              }
            />
            <ControlRow
              title={t("settings.serverName.sftpPort")}
              description={t("settings.serverName.sftpPortDescription")}
              value={
                <TextField
                  {...configForm.register("port", { valueAsNumber: true })}
                  type="number"
                  placeholder="22"
                  fullWidth
                  size="small"
                  inputProps={{
                    min: 1,
                    max: 65535,
                    "aria-label": t("settings.serverName.sftpPort"),
                  }}
                  sx={{ "& .MuiOutlinedInput-root": { borderRadius: 0 } }}
                />
              }
              meta={serverNameConfig?.port || "—"}
              status={
                <RowStatus
                  dirty={configForm.formState.isDirty}
                  error={errors.connection}
                />
              }
            />
          </>
        )}

        {active === "requirements" && (
          <>
            <ControlSectionHeader
              title={t("settings.serverName.requirements")}
              description={t("settings.serverName.intro")}
            />
            <Box sx={{ p: 2 }}>
              <Alert severity="info" sx={{ borderRadius: 0 }}>
                <Stack spacing={1}>
                  <Typography variant="body2">
                    {t("settings.serverName.configureCredentials")}
                  </Typography>
                  <Typography component="code" variant="caption">
                    GTX_SERVER_NAME_CHANGE_USERNAME
                  </Typography>
                  <Typography component="code" variant="caption">
                    GTX_SERVER_NAME_CHANGE_PASSWORD
                  </Typography>
                  <Typography variant="body2">
                    {t("settings.serverName.provideHost")}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("settings.serverName.changeNote")}
                  </Typography>
                </Stack>
              </Alert>
            </Box>
          </>
        )}
      </ControlPageLayout>
      <ControlActionBar
        dirtyCount={dirtyCount}
        onReset={resetAll}
        onSave={saveAll}
        saving={saving}
      />
    </>
  );
}

export default ServerNameSettings;
