import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  Grid2 as Grid,
  List,
  ListItem,
  ListItemText,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import {
  Cached as CacheIcon,
  Link as LinkIcon,
  PhoneAndroid as PhoneIcon,
  QrCode2 as QrCodeIcon,
} from "@mui/icons-material";
import { useMutation } from "@tanstack/react-query";
import { QRCodeSVG } from "qrcode.react";
import { cmd, mobileRequest } from "@/utils/fetchUtils";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

function CrconAppSettings() {
  const { t } = useTranslation();
  const [password, setPassword] = useState("");
  const [pairing, setPairing] = useState(null);
  const [devices, setDevices] = useState([]);
  const [bootstrap, setBootstrap] = useState(null);
  const [mobileError, setMobileError] = useState("");

  const loadDevices = useCallback(async () => {
    try {
      // Owners receive all installations; other roles transparently receive only their own.
      const [nextDevices, nextBootstrap] = await Promise.all([
        mobileRequest("devices?all=true"),
        mobileRequest("bootstrap"),
      ]);
      setDevices(nextDevices);
      setBootstrap(nextBootstrap);
      setMobileError("");
    } catch (error) {
      setMobileError(error.message);
    }
  }, []);

  useEffect(() => {
    loadDevices();
  }, [loadDevices]);

  useEffect(() => {
    if (
      !pairing?.id ||
      !["pending", "scanned", "approved"].includes(pairing.state)
    ) {
      return undefined;
    }
    const timer = window.setInterval(async () => {
      try {
        const next = await mobileRequest(`pairings/${pairing.id}`);
        setPairing((current) => ({ ...current, ...next }));
        if (["consumed", "denied"].includes(next.state)) {
          loadDevices();
        }
      } catch (error) {
        setMobileError(error.message);
      }
    }, 1000);
    return () => window.clearInterval(timer);
  }, [pairing?.id, pairing?.state, loadDevices]);

  const createPairingMutation = useMutation({
    mutationFn: () =>
      mobileRequest("pairings", { method: "POST", payload: { password } }),
    onSuccess: (result) => {
      setPairing(result);
      setPassword("");
      setMobileError("");
    },
    onError: (error) => setMobileError(error.message),
  });

  const approvePairingMutation = useMutation({
    mutationFn: (approve) =>
      mobileRequest(`pairings/${pairing.id}/approve`, {
        method: "POST",
        payload: { approve, verification_code: pairing.verification_code },
      }),
    onSuccess: (result) => setPairing((current) => ({ ...current, ...result })),
    onError: (error) => setMobileError(error.message),
  });

  const revokeDevice = async (deviceId) => {
    try {
      await mobileRequest(`devices/${deviceId}`, { method: "DELETE" });
      await loadDevices();
      toast.success(t("settings.mobile.deviceRevoked"));
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Flush Cache Mutation
  const flushCacheMutation = useMutation({
    mutationFn: () => cmd.CLEAR_APPLICATION_CACHE({ throwRouteError: false }),
    onSuccess: () => {
      toast.success(t("settings.mobile.cacheFlushed"));
    },
    onError: (error) => {
      toast.error(`${t("settings.mobile.cacheFlushFailed")}: ${error.message}`);
    },
  });

  // Reconnect Gameserver Mutation
  const reconnectMutation = useMutation({
    mutationFn: () => cmd.RECONNECT_GAME_SERVER({ throwRouteError: false }),
    onSuccess: () => {
      toast.success(t("settings.mobile.reconnected"));
    },
    onError: (error) => {
      toast.error(`${t("settings.mobile.reconnectFailed")}: ${error.message}`);
    },
  });

  const handleFlushCache = () => {
    flushCacheMutation.mutate();
  };

  const handleReconnect = () => {
    reconnectMutation.mutate();
  };

  return (
    <Grid container spacing={3}>
      <Grid size={12}>
        <Card elevation={2}>
          <CardHeader
            avatar={<QrCodeIcon color="primary" />}
            title={t("settings.mobile.title")}
            subheader={t("settings.mobile.subtitle")}
          />
          <Divider flexItem />
          <CardContent>
            <Stack spacing={2}>
              {mobileError && <Alert severity="info">{mobileError}</Alert>}
              <Alert severity="warning">
                {t("settings.mobile.pairingWarning")}
              </Alert>
              {!pairing || ["consumed", "denied"].includes(pairing.state) ? (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    label={t("settings.mobile.confirmPassword")}
                    type="password"
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    autoComplete="current-password"
                    fullWidth
                  />
                  <Button
                    variant="contained"
                    startIcon={<QrCodeIcon />}
                    disabled={!password || createPairingMutation.isPending}
                    onClick={() => createPairingMutation.mutate()}
                  >
                    {t("settings.mobile.createQr")}
                  </Button>
                </Stack>
              ) : (
                <Stack
                  direction={{ xs: "column", md: "row" }}
                  spacing={3}
                  alignItems="center"
                >
                  {pairing.qr_payload && pairing.state === "pending" && (
                    <Box sx={{ bgcolor: "white", p: 2, borderRadius: 1 }}>
                      <QRCodeSVG
                        value={pairing.qr_payload}
                        size={224}
                        level="Q"
                      />
                    </Box>
                  )}
                  <Stack spacing={1} sx={{ minWidth: 280 }}>
                    <Chip
                      label={`${t("settings.mobile.statusLabel")}: ${t(`settings.mobile.status.${pairing.state}`, { defaultValue: pairing.state })}`}
                      color="primary"
                      variant="outlined"
                    />
                    {pairing.state === "pending" && (
                      <Typography color="text.secondary">
                        {t("settings.mobile.scanCode")}
                      </Typography>
                    )}
                    {pairing.state === "scanned" && (
                      <>
                        <Typography variant="h3" sx={{ letterSpacing: 6 }}>
                          {pairing.verification_code}
                        </Typography>
                        <Typography>
                          {pairing.device_name} · {pairing.platform}
                        </Typography>
                        <Stack direction="row" spacing={1}>
                          <Button
                            variant="contained"
                            onClick={() => approvePairingMutation.mutate(true)}
                          >
                            {t("settings.mobile.approve")}
                          </Button>
                          <Button
                            color="error"
                            onClick={() => approvePairingMutation.mutate(false)}
                          >
                            {t("settings.mobile.deny")}
                          </Button>
                        </Stack>
                      </>
                    )}
                    {pairing.state === "approved" && (
                      <Typography>
                        {t("settings.mobile.approved")}
                      </Typography>
                    )}
                  </Stack>
                </Stack>
              )}

              <Divider />
              {bootstrap?.user?.permissions?.includes(
                "api.can_manage_all_mobile_devices"
              ) && (
                <>
                  <Typography variant="h6">
                    {t("settings.mobile.installationConfiguration")}
                  </Typography>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    <Chip
                      label={`${t("settings.mobile.url")}: ${bootstrap.mobile_configuration.public_base_url}`}
                    />
                    <Chip
                      label={`${t("settings.mobile.triggers")}: ${bootstrap.mobile_configuration.incident_triggers.join(
                        ", "
                      )}`}
                    />
                    <Chip
                      label={`${t("settings.mobile.retention")}: ${bootstrap.mobile_configuration.incident_retention_days} ${t("settings.mobile.days")}`}
                    />
                    <Chip
                      color={
                        bootstrap.mobile_configuration.push_relay_configured
                          ? "success"
                          : "default"
                      }
                      label={
                        bootstrap.mobile_configuration.push_relay_configured
                          ? t("settings.mobile.pushConfigured")
                          : t("settings.mobile.pushDisabled")
                      }
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    {t("settings.mobile.configurationHint")}
                  </Typography>
                  <Divider />
                </>
              )}
              <Typography variant="h6">
                {bootstrap?.user?.permissions?.includes(
                  "api.can_manage_all_mobile_devices"
                )
                  ? t("settings.mobile.allDevices")
                  : t("settings.mobile.myDevices")}
              </Typography>
              {devices.length === 0 ? (
                <Typography color="text.secondary">
                  {t("settings.mobile.noDevices")}
                </Typography>
              ) : (
                <List disablePadding>
                  {devices.map((device) => (
                    <ListItem
                      key={device.id}
                      divider
                      secondaryAction={
                        !device.revoked_at && (
                          <Button
                            color="error"
                            onClick={() => revokeDevice(device.id)}
                          >
                            {t("settings.mobile.revoke")}
                          </Button>
                        )
                      }
                    >
                      <PhoneIcon
                        sx={{ mr: 2 }}
                        color={device.revoked_at ? "disabled" : "action"}
                      />
                      <ListItemText
                        primary={`${device.name} · ${device.username}`}
                        secondary={`${device.platform} · ${
                          device.last_seen_at
                            ? `${t("settings.mobile.lastSeen")} ${new Date(
                                device.last_seen_at
                              ).toLocaleString()}`
                            : t("settings.mobile.neverUsed")
                        }${device.revoked_at ? ` · ${t("settings.mobile.revoked")}` : ""}`}
                      />
                    </ListItem>
                  ))}
                </List>
              )}
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Flush Cache Card */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card elevation={2}>
          <CardHeader
            avatar={<CacheIcon color="primary" />}
            title={t("settings.mobile.cacheTitle")}
            subheader={t("settings.mobile.cacheSubtitle")}
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="body2" color="text.secondary">
                {t("settings.mobile.cacheDescription")}
              </Typography>
              <Alert severity="warning">
                {t("settings.mobile.cacheWarning")}
              </Alert>
              <Button
                variant="contained"
                color="warning"
                onClick={handleFlushCache}
                disabled={flushCacheMutation.isPending}
                startIcon={<CacheIcon />}
              >
                {flushCacheMutation.isPending ? t("settings.mobile.flushing") : t("settings.mobile.flushCache")}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Grid>

      {/* Reconnect Gameserver Card */}
      <Grid size={{ xs: 12, md: 6 }}>
        <Card elevation={2}>
          <CardHeader
            avatar={<LinkIcon color="primary" />}
            title={t("settings.mobile.connectionTitle")}
            subheader={t("settings.mobile.connectionSubtitle")}
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="body2" color="text.secondary">
                {t("settings.mobile.connectionDescription")}
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={handleReconnect}
                disabled={reconnectMutation.isPending}
                startIcon={<LinkIcon />}
              >
                {reconnectMutation.isPending ? t("settings.mobile.reconnecting") : t("settings.mobile.reconnect")}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

export default CrconAppSettings;
