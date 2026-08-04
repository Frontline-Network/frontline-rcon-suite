import { cmd } from "@/utils/fetchUtils";
import {
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Divider,
  Grid2 as Grid,
  TextField,
  Typography,
} from "@mui/material";
import {
  CloudUpload as CloudIcon,
  Dns as ServerIcon,
  Save as SaveIcon,
  Settings as SettingsIcon,
} from "@mui/icons-material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import React from "react";
import { useForm } from "react-hook-form";
import { useLoaderData } from "react-router-dom";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

function ServerNameSettings() {
  const { t } = useTranslation();
  const loaderData = useLoaderData();
  const queryClient = useQueryClient();

  // Server Name Query
  const { data: serverName } = useQuery({
    queryKey: [{ queryIdentifier: "get_server_name" }],
    queryFn: () => cmd.GET_SERVER_NAME({ throwRouteError: false }),
    initialData: loaderData.serverName,
  });

  // Server Name Change Config Query
  const { data: serverNameConfig } = useQuery({
    queryKey: [{ queryIdentifier: "get_server_name_change_config" }],
    queryFn: () => cmd.GET_SERVER_NAME_CHANGE_CONFIG({ throwRouteError: false }),
    initialData: loaderData.serverNameConfig,
  });

  // Server Name Mutation
  const serverNameMutation = useMutation({
    mutationFn: (newName) =>
      cmd.SET_SERVER_NAME({ payload: { name: newName }, throwRouteError: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [{ queryIdentifier: "get_server_name" }],
      });
      toast.success(t("settings.serverName.updated"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <strong>{t("settings.serverName.updateFailed")}</strong>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  // Server Name Config Mutation
  const configMutation = useMutation({
    mutationFn: (newConfig) =>
      cmd.SET_SERVER_NAME_CHANGE_CONFIG({ payload: newConfig, throwRouteError: false }),
    onSuccess: () => {
      queryClient.invalidateQueries({
        queryKey: [{ queryIdentifier: "get_server_name_change_config" }],
      });
      toast.success(t("settings.serverName.configUpdated"));
    },
    onError: (error) => {
      toast.error(
        <div>
          <strong>{t("settings.serverName.configFailed")}</strong>
          <p>{error.message}</p>
        </div>
      );
    },
  });

  // Server Name Form
  const {
    register: registerName,
    handleSubmit: handleSubmitName,
    reset: resetName,
    formState: { isDirty: isNameDirty, isSubmitting: isNameSubmitting },
  } = useForm({
    defaultValues: { serverName: serverName || "" },
  });

  // Server Name Config Form
  const {
    register: registerConfig,
    handleSubmit: handleSubmitConfig,
    reset: resetConfig,
    formState: { isDirty: isConfigDirty, isSubmitting: isConfigSubmitting },
  } = useForm({
    defaultValues: serverNameConfig || {},
  });

  // Sync forms when data changes
  React.useEffect(() => {
    if (serverName) {
      resetName({ serverName });
    }
  }, [serverName, resetName]);

  React.useEffect(() => {
    if (serverNameConfig) {
      resetConfig(serverNameConfig);
    }
  }, [serverNameConfig, resetConfig]);

  const onSubmitName = (data) => {
    serverNameMutation.mutate(data.serverName);
  };

  const onSubmitConfig = (data) => {
    configMutation.mutate(data);
  };

  return (
    <Grid container spacing={3}>
      {/* Header Information */}
      <Grid size={12}>

        <Typography color="text.secondary">
          {t("settings.serverName.intro")}
        </Typography>

        <Typography variant="body2" color="text.secondary" component="div">
          <strong>{t("settings.serverName.requirements")}</strong>
          <ul style={{ margin: '8px 0', paddingLeft: '20px' }}>
            <li>{t("settings.serverName.configureCredentials")}
              <ul>
                <li>GTX_SERVER_NAME_CHANGE_USERNAME</li>
                <li>GTX_SERVER_NAME_CHANGE_PASSWORD</li>
              </ul>
            </li>
            <li>{t("settings.serverName.provideHost")}</li>
          </ul>
          <em>{t("settings.serverName.changeNote")}</em>
        </Typography>
      </Grid>

      {/* Server Name Section */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card elevation={2} component={"fieldset"} form="server-name-form">
          <CardHeader
            avatar={<ServerIcon color="primary" />}
            title={t("settings.serverName.title")}
            subheader={t("settings.serverName.subtitle")}
            action={
              <Button
                type="submit"
                form="server-name-form"
                variant="contained"
                size="small"
                startIcon={<SaveIcon />}
                disabled={isNameSubmitting || serverNameMutation.isPending}
                sx={{ mr: 1 }}
              >
                {serverNameMutation.isPending ? t("playerEditor.updating") : t("common.save")}
              </Button>
            }
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Box component="form" id="server-name-form" onSubmit={handleSubmitName(onSubmitName)}>
              <TextField
                {...registerName("serverName")}
                label={t("settings.serverName.title")}
                placeholder={t("settings.serverName.placeholder")}
                fullWidth
                size="small"
                variant="outlined"
                helperText={t("settings.serverName.helper")}
              />
            </Box>
          </CardContent>
        </Card>
      </Grid>

      {/* Configuration Section */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card elevation={2} component={"fieldset"} form="config-form">
          <CardHeader
            avatar={<SettingsIcon color="primary" />}
            title={t("settings.serverName.sftpTitle")}
            subheader={t("settings.serverName.sftpSubtitle")}
            action={
              <Button
                type="submit"
                form="config-form"
                variant="contained"
                size="small"
                startIcon={<CloudIcon />}
                disabled={isConfigSubmitting || configMutation.isPending}
              >
                {configMutation.isPending ? t("playerEditor.updating") : t("settings.serverName.saveConfig")}
              </Button>
            }
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Box component="form" id="config-form" onSubmit={handleSubmitConfig(onSubmitConfig)}>
                <Grid container spacing={2}>
                  <Grid size={8}>
                    <TextField
                      {...registerConfig("ip")}
                      label={t("settings.serverName.sftpHost")}
                      placeholder="168.10.0.1"
                      fullWidth
                      size="small"
                      variant="outlined"
                    />
                  </Grid>
                  <Grid size={4}>
                    <TextField
                      {...registerConfig("port")}
                      label="Port"
                      type="number"
                      placeholder="1234"
                      fullWidth
                      size="small"
                      variant="outlined"
                      slotProps={{ input: { min: 1, max: 65535 } }}
                    />
                  </Grid>
                </Grid>
            </Box>
          </CardContent>
        </Card>
      </Grid>

    </Grid>
  );
}

export default ServerNameSettings;
