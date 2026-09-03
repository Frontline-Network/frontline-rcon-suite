import { useEffect, useMemo, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Divider,
  FormControlLabel,
  MenuItem,
  Paper,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import AutorenewIcon from "@mui/icons-material/Autorenew";
import PersonSearchIcon from "@mui/icons-material/PersonSearch";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import RefreshIcon from "@mui/icons-material/Refresh";
import { useTranslation } from "react-i18next";

import { isFakeMode } from "@/mirage/demo-data";
import { cmd } from "@/utils/fetchUtils";

const RULES = ["unverified", "trial_active", "trial_expiring", "trial_expired"];

const fakePreview = {
  available: true,
  family_matches: true,
  server_family: "hll_vietnam",
  players: [
    {
      player_id: "76561198000000001",
      player_name: "FLN_Raven",
      blocked: false,
      status_known: true,
      rule: "trial_expiring",
      verified: true,
      vip_active: true,
      grant_source: "trial",
      expires_at: new Date(Date.now() + 36 * 3600000).toISOString(),
      has_purchased_vip: false,
    },
  ],
};

const formatDate = (value) => (value ? new Date(value).toLocaleString() : "–");

const VipLifecyclePanel = ({ value, onChange, initialStatus }) => {
  const { t } = useTranslation();
  const [preview, setPreview] = useState(null);
  const [deliveryStatus, setDeliveryStatus] = useState(initialStatus);
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [selectedPlayer, setSelectedPlayer] = useState("");
  const [selectedRule, setSelectedRule] = useState(RULES[0]);
  const [busy, setBusy] = useState("");
  const [feedback, setFeedback] = useState(null);

  useEffect(() => setDeliveryStatus(initialStatus), [initialStatus]);

  const update = (field, nextValue) =>
    onChange({ ...value, [field]: nextValue });
  const updateMessage = (rule, message) =>
    onChange({
      ...value,
      messages: { ...value.messages, [rule]: message },
    });

  const targets = useMemo(
    () =>
      preview?.players?.filter((player) => player.rule && !player.blocked) ??
      [],
    [preview]
  );

  const loadPreview = async () => {
    setBusy("preview");
    setFeedback(null);
    try {
      const result = isFakeMode()
        ? fakePreview
        : await cmd.PREVIEW_VIP_LIFECYCLE();
      setPreview(result);
      if (!result.family_matches) {
        setFeedback({ severity: "warning", key: "familyMismatch" });
      } else if (!result.available) {
        setFeedback({ severity: "error", key: "statusUnavailable" });
      }
    } catch (error) {
      setFeedback({
        severity: "error",
        text: t("settings.campaigns.vipLifecycle.previewFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
    } finally {
      setBusy("");
    }
  };

  const refreshLog = async () => {
    setBusy("log");
    try {
      setDeliveryStatus(
        isFakeMode()
          ? { generated_at: new Date().toISOString(), deliveries: [] }
          : await cmd.GET_VIP_LIFECYCLE_STATUS()
      );
    } catch (error) {
      setFeedback({
        severity: "error",
        text: t("settings.campaigns.vipLifecycle.logFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
    } finally {
      setBusy("");
    }
  };

  const loadPlayers = async () => {
    setBusy("players");
    try {
      const players = isFakeMode()
        ? [{ player_id: "76561198000000001", name: "FLN_Raven" }]
        : await cmd.GET_ONLINE_PLAYERS();
      setOnlinePlayers(players ?? []);
      if ((players ?? []).length && !selectedPlayer) {
        setSelectedPlayer(players[0].player_id);
      }
    } catch (error) {
      setFeedback({
        severity: "error",
        text: t("settings.campaigns.vipLifecycle.playersFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
    } finally {
      setBusy("");
    }
  };

  const sendTest = async () => {
    if (!selectedPlayer) return;
    setBusy("test");
    setFeedback(null);
    try {
      if (!isFakeMode()) {
        await cmd.TEST_VIP_LIFECYCLE_MESSAGE({
          payload: { player_id: selectedPlayer, rule: selectedRule },
        });
      }
      setFeedback({ severity: "success", key: "testSent" });
      await refreshLog();
    } catch (error) {
      setFeedback({
        severity: "error",
        text: t("settings.campaigns.vipLifecycle.testFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
      setBusy("");
    }
  };

  return (
    <Paper
      variant="outlined"
      sx={{
        overflow: "hidden",
        borderColor: value.enabled ? "primary.main" : "divider",
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ xs: "stretch", md: "center" }}
        gap={2}
        sx={{ p: { xs: 2, md: 2.5 }, bgcolor: "action.hover" }}
      >
        <Stack direction="row" gap={1.25} alignItems="center">
          <AutorenewIcon color={value.enabled ? "primary" : "disabled"} />
          <Box>
            <Typography variant="h6">
              {t("settings.campaigns.vipLifecycle.title")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("settings.campaigns.vipLifecycle.subtitle")}
            </Typography>
          </Box>
        </Stack>
        <Stack direction="row" gap={2} alignItems="center" flexWrap="wrap">
          <FormControlLabel
            control={
              <Switch
                checked={value.test_mode}
                onChange={(event) => update("test_mode", event.target.checked)}
              />
            }
            label={t("settings.campaigns.vipLifecycle.testMode")}
          />
          <FormControlLabel
            control={
              <Switch
                checked={value.enabled}
                onChange={(event) => update("enabled", event.target.checked)}
              />
            }
            label={t("common.enabled")}
          />
        </Stack>
      </Stack>

      <Divider />
      <Stack spacing={2.5} sx={{ p: { xs: 2, md: 2.5 } }}>
        {value.test_mode && (
          <Alert severity="info">
            {t("settings.campaigns.vipLifecycle.testModeHelp")}
          </Alert>
        )}
        {feedback && (
          <Alert severity={feedback.severity}>
            {feedback.text ||
              t(`settings.campaigns.vipLifecycle.${feedback.key}`)}
          </Alert>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "1fr",
              sm: "repeat(2, minmax(0, 1fr))",
              lg: "repeat(4, minmax(0, 1fr))",
            },
            gap: 1.5,
          }}
        >
          <TextField
            select
            label={t("settings.campaigns.vipLifecycle.serverFamily")}
            value={value.server_family}
            onChange={(event) => update("server_family", event.target.value)}
          >
            <MenuItem value="hll_vietnam">Hell Let Loose: Vietnam</MenuItem>
            <MenuItem value="hll">Hell Let Loose</MenuItem>
          </TextField>
          <TextField
            type="number"
            label={t("settings.campaigns.vipLifecycle.expiryWindow")}
            value={value.expiry_window_hours}
            onChange={(event) =>
              update("expiry_window_hours", Number(event.target.value))
            }
            slotProps={{ htmlInput: { min: 1, max: 168 } }}
          />
          <TextField
            type="number"
            label={t("settings.campaigns.vipLifecycle.unverifiedCooldown")}
            value={value.unverified_cooldown_days}
            onChange={(event) =>
              update("unverified_cooldown_days", Number(event.target.value))
            }
            slotProps={{ htmlInput: { min: 1, max: 90 } }}
          />
          <TextField
            type="number"
            label={t("settings.campaigns.vipLifecycle.cacheSeconds")}
            value={value.status_cache_seconds}
            onChange={(event) =>
              update("status_cache_seconds", Number(event.target.value))
            }
            slotProps={{ htmlInput: { min: 30, max: 900 } }}
          />
        </Box>

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "repeat(2, minmax(0, 1fr))" },
            gap: 1.5,
          }}
        >
          {RULES.map((rule) => (
            <Paper key={rule} variant="outlined" sx={{ p: 2 }}>
              <Stack spacing={1.25}>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="subtitle2">
                    {t(`settings.campaigns.vipLifecycle.rules.${rule}.title`)}
                  </Typography>
                  <Chip
                    size="small"
                    variant="outlined"
                    label={t(
                      `settings.campaigns.vipLifecycle.rules.${rule}.limit`
                    )}
                  />
                </Stack>
                <Typography variant="caption" color="text.secondary">
                  {t(
                    `settings.campaigns.vipLifecycle.rules.${rule}.description`
                  )}
                </Typography>
                <TextField
                  multiline
                  minRows={3}
                  value={value.messages[rule]}
                  onChange={(event) => updateMessage(rule, event.target.value)}
                  label={t("settings.campaigns.vipLifecycle.message")}
                  fullWidth
                />
              </Stack>
            </Paper>
          ))}
        </Box>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Stack
              direction={{ xs: "column", md: "row" }}
              justifyContent="space-between"
              gap={1}
            >
              <Box>
                <Typography variant="subtitle1">
                  {t("settings.campaigns.vipLifecycle.previewTitle")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("settings.campaigns.vipLifecycle.previewHelp")}
                </Typography>
              </Box>
              <Button
                variant="outlined"
                startIcon={<PersonSearchIcon />}
                onClick={loadPreview}
                disabled={Boolean(busy)}
              >
                {t("settings.campaigns.vipLifecycle.previewAction")}
              </Button>
            </Stack>
            {preview && preview.family_matches && (
              <Stack spacing={0.75}>
                <Typography variant="body2">
                  {t("settings.campaigns.vipLifecycle.targetCount", {
                    count: targets.length,
                  })}
                </Typography>
                {preview.players.map((player) => (
                  <Stack
                    key={player.player_id}
                    direction={{ xs: "column", sm: "row" }}
                    justifyContent="space-between"
                    gap={1}
                    sx={{ py: 1, borderTop: 1, borderColor: "divider" }}
                  >
                    <Box>
                      <Typography variant="body2">
                        {player.player_name} · {player.player_id}
                      </Typography>
                      <Typography variant="caption" color="text.secondary">
                        {player.status_known
                          ? `${player.grant_source} · ${formatDate(
                              player.expires_at
                            )}`
                          : t("settings.campaigns.vipLifecycle.unknownStatus")}
                      </Typography>
                    </Box>
                    <Chip
                      size="small"
                      color={
                        player.rule && !player.blocked ? "primary" : "default"
                      }
                      label={
                        player.blocked
                          ? t("settings.campaigns.vipLifecycle.blocked")
                          : player.rule
                          ? t(
                              `settings.campaigns.vipLifecycle.rules.${player.rule}.title`
                            )
                          : t("settings.campaigns.vipLifecycle.noMessage")
                      }
                    />
                  </Stack>
                ))}
              </Stack>
            )}
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Box>
              <Typography variant="subtitle1">
                {t("settings.campaigns.vipLifecycle.testTitle")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {t("settings.campaigns.vipLifecycle.testHelp")}
              </Typography>
            </Box>
            <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
              <TextField
                select
                label={t("settings.campaigns.vipLifecycle.testPlayer")}
                value={selectedPlayer}
                onChange={(event) => setSelectedPlayer(event.target.value)}
                sx={{ flex: 1 }}
              >
                {onlinePlayers.map((player) => (
                  <MenuItem key={player.player_id} value={player.player_id}>
                    {player.name} · {player.player_id}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label={t("settings.campaigns.vipLifecycle.testRule")}
                value={selectedRule}
                onChange={(event) => setSelectedRule(event.target.value)}
                sx={{ flex: 1 }}
              >
                {RULES.map((rule) => (
                  <MenuItem key={rule} value={rule}>
                    {t(`settings.campaigns.vipLifecycle.rules.${rule}.title`)}
                  </MenuItem>
                ))}
              </TextField>
              <Button
                variant="outlined"
                startIcon={<RefreshIcon />}
                onClick={loadPlayers}
                disabled={Boolean(busy)}
              >
                {t("settings.campaigns.vipLifecycle.loadPlayers")}
              </Button>
              <Button
                variant="contained"
                startIcon={<PlayArrowIcon />}
                onClick={sendTest}
                disabled={!selectedPlayer || Boolean(busy)}
              >
                {t("settings.campaigns.vipLifecycle.sendTest")}
              </Button>
            </Stack>
          </Stack>
        </Paper>

        <Paper variant="outlined" sx={{ p: 2 }}>
          <Stack spacing={1.5}>
            <Stack direction="row" justifyContent="space-between" gap={1}>
              <Box>
                <Typography variant="subtitle1">
                  {t("settings.campaigns.vipLifecycle.logTitle")}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {t("settings.campaigns.vipLifecycle.logHelp")}
                </Typography>
              </Box>
              <Button
                startIcon={<RefreshIcon />}
                onClick={refreshLog}
                disabled={Boolean(busy)}
              >
                {t("common.refresh")}
              </Button>
            </Stack>
            {(deliveryStatus?.deliveries ?? []).length === 0 ? (
              <Typography variant="body2" color="text.secondary">
                {t("settings.campaigns.vipLifecycle.noLog")}
              </Typography>
            ) : (
              deliveryStatus.deliveries.map((delivery) => (
                <Stack
                  key={delivery.id}
                  direction={{ xs: "column", md: "row" }}
                  justifyContent="space-between"
                  gap={1}
                  sx={{ py: 1, borderTop: 1, borderColor: "divider" }}
                >
                  <Box>
                    <Typography variant="body2">
                      {delivery.player_name} · {delivery.player_id}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t(
                        `settings.campaigns.vipLifecycle.rules.${delivery.rule}.title`
                      )}{" "}
                      · {formatDate(delivery.updated_at)}
                    </Typography>
                  </Box>
                  <Chip
                    size="small"
                    color={delivery.status === "failed" ? "error" : "success"}
                    variant="outlined"
                    label={t(
                      `settings.campaigns.vipLifecycle.deliveryStatus.${delivery.status}`
                    )}
                  />
                </Stack>
              ))
            )}
          </Stack>
        </Paper>
      </Stack>
    </Paper>
  );
};

export default VipLifecyclePanel;
