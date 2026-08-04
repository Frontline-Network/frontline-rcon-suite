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

function CrconAppSettings() {
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
      toast.success("Mobile device revoked");
    } catch (error) {
      toast.error(error.message);
    }
  };

  // Flush Cache Mutation
  const flushCacheMutation = useMutation({
    mutationFn: () => cmd.CLEAR_APPLICATION_CACHE({ throwRouteError: false }),
    onSuccess: () => {
      toast.success("Cache flushed successfully!");
    },
    onError: (error) => {
      toast.error(`Failed to flush cache: ${error.message}`);
    },
  });

  // Reconnect Gameserver Mutation
  const reconnectMutation = useMutation({
    mutationFn: () => cmd.RECONNECT_GAME_SERVER({ throwRouteError: false }),
    onSuccess: () => {
      toast.success("Reconnected to gameserver successfully!");
    },
    onError: (error) => {
      toast.error(`Failed to reconnect to gameserver: ${error.message}`);
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
            title="Mobile Admin App"
            subheader="Pair your own CRCON account with a trusted phone"
          />
          <Divider flexItem />
          <CardContent>
            <Stack spacing={2}>
              {mobileError && <Alert severity="info">{mobileError}</Alert>}
              <Alert severity="warning">
                Only approve the phone if its six-digit code matches this page.
                The QR code expires after two minutes and can be used only once.
              </Alert>
              {!pairing || ["consumed", "denied"].includes(pairing.state) ? (
                <Stack direction={{ xs: "column", sm: "row" }} spacing={2}>
                  <TextField
                    label="Confirm your CRCON password"
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
                    Create QR code
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
                      label={`Status: ${pairing.state}`}
                      color="primary"
                      variant="outlined"
                    />
                    {pairing.state === "pending" && (
                      <Typography color="text.secondary">
                        Scan this code in the CRCON Admin app.
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
                            Codes match — approve
                          </Button>
                          <Button
                            color="error"
                            onClick={() => approvePairingMutation.mutate(false)}
                          >
                            Deny
                          </Button>
                        </Stack>
                      </>
                    )}
                    {pairing.state === "approved" && (
                      <Typography>
                        Approved. Finish the connection on the phone.
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
                    Installation configuration
                  </Typography>
                  <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                    <Chip
                      label={`URL: ${bootstrap.mobile_configuration.public_base_url}`}
                    />
                    <Chip
                      label={`Triggers: ${bootstrap.mobile_configuration.incident_triggers.join(
                        ", "
                      )}`}
                    />
                    <Chip
                      label={`Retention: ${bootstrap.mobile_configuration.incident_retention_days} days`}
                    />
                    <Chip
                      color={
                        bootstrap.mobile_configuration.push_relay_configured
                          ? "success"
                          : "default"
                      }
                      label={
                        bootstrap.mobile_configuration.push_relay_configured
                          ? "Push configured"
                          : "Push disabled"
                      }
                    />
                  </Stack>
                  <Typography variant="body2" color="text.secondary">
                    These security-sensitive deployment values are changed
                    through the CRCON environment file.
                  </Typography>
                  <Divider />
                </>
              )}
              <Typography variant="h6">
                {bootstrap?.user?.permissions?.includes(
                  "api.can_manage_all_mobile_devices"
                )
                  ? "All mobile devices"
                  : "My devices"}
              </Typography>
              {devices.length === 0 ? (
                <Typography color="text.secondary">
                  No mobile devices paired.
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
                            Revoke
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
                            ? `last seen ${new Date(
                                device.last_seen_at
                              ).toLocaleString()}`
                            : "never used"
                        }${device.revoked_at ? " · revoked" : ""}`}
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
            title="Cache Management"
            subheader="Clear application cache"
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="body2" color="text.secondary">
                Clicking this will flush the internal cache used by different
                CRCON components. Avoid using it unnecessarily, as it forces a
                lot of data to be recalculated and reloaded.
              </Typography>
              <Alert severity="warning">
                Do not use this until instructed to do so by the CRCON
                maintainers or you know what you are doing.
              </Alert>
              <Button
                variant="contained"
                color="warning"
                onClick={handleFlushCache}
                disabled={flushCacheMutation.isPending}
                startIcon={<CacheIcon />}
              >
                {flushCacheMutation.isPending ? "Flushing..." : "Flush Cache"}
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
            title="Gameserver Connection"
            subheader="Reconnect to gameserver"
          />
          <Divider flexItem sx={{ mt: 1, mb: 2 }} />
          <CardContent>
            <Stack spacing={2}>
              <Typography variant="body2" color="text.secondary">
                Force a reconnection to the gameserver. Use this if the
                connection appears to be unstable.
              </Typography>
              <Button
                variant="contained"
                color="primary"
                onClick={handleReconnect}
                disabled={reconnectMutation.isPending}
                startIcon={<LinkIcon />}
              >
                {reconnectMutation.isPending ? "Reconnecting..." : "Reconnect"}
              </Button>
            </Stack>
          </CardContent>
        </Card>
      </Grid>
    </Grid>
  );
}

export default CrconAppSettings;
