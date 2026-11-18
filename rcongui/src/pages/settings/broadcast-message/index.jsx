import { Suspense, useEffect, useMemo, useState } from "react";
import {
  Await,
  defer,
  useActionData,
  useLoaderData,
  useNavigation,
  useSubmit,
} from "react-router-dom";
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  IconButton,
  MenuItem,
  Skeleton,
  Stack,
  Switch,
  TextField,
  Tooltip,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CampaignIcon from "@mui/icons-material/Campaign";
import ContentCopyIcon from "@mui/icons-material/ContentCopy";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import PlayArrowIcon from "@mui/icons-material/PlayArrow";
import { useTranslation } from "react-i18next";
import isEqual from "lodash/isEqual";

import { AsyncClientError } from "@/components/shared/AsyncClientError";
import { isFakeMode } from "@/mirage/demo-data";
import { playerTestErrorKey } from "./player-test-feedback.mjs";
import { TEMPLATE_CATEGORY, unpackBroadcastMessage } from "@/utils/lib";
import { cmd } from "@/utils/fetchUtils";
import BroadcastCampaignWorkbench from "./BroadcastCampaignWorkbench";
import VipLifecyclePanel from "./VipLifecyclePanel";

const createCampaign = (index = 0) => ({
  id: `campaign-${Date.now()}-${index}`,
  title: "",
  enabled: true,
  time_sec: 900,
  message: "",
  min_players: 0,
  max_players: 100,
  pause_during_seeding: false,
  delivery_mode: "broadcast",
  min_session_minutes: 5,
  recipient_group: "all",
});

const VIP_LIFECYCLE_DEFAULT_MESSAGES = {
  unverified:
    "Du kannst einmalig kostenlos VIP freischalten und erhältst damit bevorzugten Zugang bei voller Warteschlange. Weitere Informationen: fln.gg/vip",
  trial_active:
    "Dein kostenloser VIP-Zugang ist aktiv. Die verbleibende Laufzeit findest du in deinem Konto unter fln.gg/mein-konto",
  trial_expiring:
    "Dein kostenloser VIP-Zugang endet bald. Deine Laufzeit und Verlängerungsmöglichkeiten findest du unter fln.gg/mein-konto",
  trial_expired:
    "Dein kostenloser VIP-Zugang ist abgelaufen. Wenn du VIP weiter nutzen möchtest, findest du die verfügbaren Laufzeiten unter fln.gg/vip",
};

const createVipLifecycleCampaign = (message) => ({
  enabled: true,
  message,
  min_session_minutes: 5,
  min_players: 0,
  max_players: 100,
  pause_during_seeding: false,
});

const createVipLifecycleConfig = () => ({
  enabled: false,
  server_family: "hll_vietnam",
  expiry_window_hours: 48,
  status_cache_seconds: 60,
  test_mode: false,
  campaigns: Object.fromEntries(
    Object.entries(VIP_LIFECYCLE_DEFAULT_MESSAGES).map(([rule, message]) => [
      rule,
      createVipLifecycleCampaign(message),
    ])
  ),
});

const normalizeConfig = (config) => {
  const lifecycleDefaults = createVipLifecycleConfig();
  const lifecycleConfig = config?.vip_lifecycle ?? {};
  const lifecycleSettings = { ...lifecycleConfig };
  delete lifecycleSettings.messages;
  const lifecycleCampaigns = Object.fromEntries(
    Object.entries(lifecycleDefaults.campaigns).map(([rule, defaults]) => [
      rule,
      {
        ...defaults,
        ...(lifecycleConfig.campaigns?.[rule] ?? {}),
        message:
          lifecycleConfig.campaigns?.[rule]?.message ??
          lifecycleConfig.messages?.[rule] ??
          defaults.message,
      },
    ])
  );
  return {
    enabled: Boolean(config?.enabled),
    randomize: Boolean(config?.randomize),
    player_message_interval_sec: Number(
      config?.player_message_interval_sec ?? 10
    ),
    player_message_gap_sec: Number(config?.player_message_gap_sec ?? 300),
    vip_lifecycle: {
      ...lifecycleDefaults,
      ...lifecycleSettings,
      campaigns: lifecycleCampaigns,
    },
    messages: (config?.messages ?? []).map((campaign, index) => ({
      ...createCampaign(index),
      ...campaign,
      id: campaign.id || `legacy-campaign-${index}`,
    })),
  };
};

let fakeCampaignConfig = normalizeConfig({
  enabled: true,
  randomize: false,
  messages: [
    {
      id: "vip-access",
      title: "VIP-Zugang",
      enabled: true,
      time_sec: 1200,
      message:
        "★ Unterstütze Frontline Network und erhalte bevorzugten Serverzugang mit VIP: fln.gg/vip",
      min_players: 35,
      max_players: 100,
      pause_during_seeding: true,
    },
    {
      id: "discord-community",
      title: "Discord-Community",
      enabled: true,
      time_sec: 1800,
      message:
        "Tritt der Frontline-Community bei, finde Mitspieler und erhalte Event-News: discord.gg/flnetwork",
      min_players: 10,
      max_players: 100,
      pause_during_seeding: false,
    },
  ],
});

export const loader = async () => {
  if (isFakeMode()) {
    return defer({
      config: fakeCampaignConfig,
      templates: Promise.resolve([]),
      deliveryStatus: { campaigns: [] },
      vipLifecycleStatus: { available: true, deliveries: [] },
    });
  }

  return defer({
    config: normalizeConfig(await cmd.GET_BROADCAST_CONFIG()),
    deliveryStatus: await cmd.GET_CAMPAIGN_DELIVERY_STATUS(),
    vipLifecycleStatus: await cmd.GET_VIP_LIFECYCLE_STATUS(),
    templates: cmd.GET_MESSAGE_TEMPLATES({
      params: { category: TEMPLATE_CATEGORY.BROADCAST },
    }),
  });
};

export const action = async ({ request }) => {
  const payload = normalizeConfig(await request.json());
  if (isFakeMode()) {
    fakeCampaignConfig = payload;
    return { saved: true };
  }

  await cmd.SET_BROADCAST_CONFIG({ payload });
  return { saved: true };
};

const TemplateSkeleton = () => <Skeleton height={56} />;

const CampaignCard = ({
  campaign,
  index,
  onChange,
  onDuplicate,
  onDelete,
  onTest,
  testing,
  deliveryStatus,
  testResult,
}) => {
  const { t } = useTranslation();
  const update = (field, value) =>
    onChange(index, { ...campaign, [field]: value });
  const rawIntervalSeconds = Number(campaign.time_sec);
  const isPlayerMessage = campaign.delivery_mode === "player_message";
  const messageInvalid = !campaign.message.trim();
  const intervalInvalid = !Number.isInteger(rawIntervalSeconds) || rawIntervalSeconds < 1 || rawIntervalSeconds > 86400;
  const sessionInvalid =
    !Number.isFinite(Number(campaign.min_session_minutes)) ||
    campaign.min_session_minutes < 1 ||
    campaign.min_session_minutes > 1440;
  const minPlayersInvalid =
    !Number.isFinite(Number(campaign.min_players)) ||
    campaign.min_players < 0 ||
    campaign.min_players > 100 ||
    campaign.min_players > campaign.max_players;
  const maxPlayersInvalid =
    !Number.isFinite(Number(campaign.max_players)) ||
    campaign.max_players < 0 ||
    campaign.max_players > 100 ||
    campaign.max_players < campaign.min_players;

  return (
    <Card
      variant="outlined"
      sx={{
        borderColor: campaign.enabled ? "divider" : "rgba(255,255,255,0.1)",
        border: 0,
        borderRadius: 0,
        bgcolor: "transparent",
        boxShadow: "none",
      }}
    >
      <CardContent
        className="wardogs-campaign-editor"
        sx={{ p: { xs: 2, md: 2.5 }, "&:last-child": { pb: 2.5 } }}
      >
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            className="wardogs-campaign-header"
            justifyContent="space-between"
            alignItems={{ xs: "stretch", sm: "center" }}
            gap={1}
          >
            <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
              <CampaignIcon color={campaign.enabled ? "primary" : "disabled"} />
              <TextField
                label={t("settings.campaigns.campaignName")}
                value={campaign.title}
                onChange={(event) => update("title", event.target.value)}
                placeholder={t("settings.campaigns.namePlaceholder")}
                size="small"
                fullWidth
                slotProps={{ htmlInput: { maxLength: 80 } }}
                sx={{ maxWidth: 420 }}
              />
              <Chip
                size="small"
                color={campaign.enabled ? "success" : "default"}
                label={t(
                  campaign.enabled
                    ? "settings.campaigns.active"
                    : "settings.campaigns.paused"
                )}
              />
            </Stack>
            <Stack
              direction="row"
              alignItems="center"
              justifyContent="flex-end"
            >
              <FormControlLabel
                control={
                  <Switch
                    checked={campaign.enabled}
                    onChange={(event) =>
                      update("enabled", event.target.checked)
                    }
                  />
                }
                label={t("common.enabled")}
              />
              <Tooltip title={t("settings.campaigns.duplicate")}>
                <IconButton
                  onClick={() => onDuplicate(index)}
                  aria-label={t("settings.campaigns.duplicate")}
                  sx={{ minWidth: 44, minHeight: 44 }}
                >
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title={t("common.delete")}>
                <IconButton
                  color="error"
                  onClick={() => onDelete(index)}
                  aria-label={t("common.delete")}
                  sx={{ minWidth: 44, minHeight: 44 }}
                >
                  <DeleteOutlineIcon />
                </IconButton>
              </Tooltip>
            </Stack>
          </Stack>

          <TextField
            label={t("settings.campaigns.message")}
            value={campaign.message}
            onChange={(event) => update("message", event.target.value)}
            multiline
            minRows={3}
            fullWidth
            required
            error={messageInvalid}
            helperText={
              messageInvalid
                ? t("settings.campaigns.messageRequired")
                : t(
                    isPlayerMessage
                      ? "settings.campaigns.playerMessageHelp"
                      : "settings.campaigns.messageHelp"
                  )
            }
          />

          <Stack
            className="wardogs-campaign-fields"
            data-delivery-mode={campaign.delivery_mode}
            direction={{ xs: "column", md: "row" }}
            gap={1.5}
          >
            <TextField
              select
              label={t("settings.campaigns.deliveryMode")}
              value={campaign.delivery_mode}
              onChange={(event) => update("delivery_mode", event.target.value)}
              sx={{ minWidth: 210 }}
            >
              <MenuItem value="broadcast">
                {t("settings.campaigns.deliveryBroadcast")}
              </MenuItem>
              <MenuItem value="player_message">
                {t("settings.campaigns.deliveryPlayerMessage")}
              </MenuItem>
            </TextField>
            {isPlayerMessage ? (
              <>
                <TextField
                  label={t("settings.campaigns.minSessionMinutes")}
                  type="number"
                  value={campaign.min_session_minutes}
                  onChange={(event) =>
                    update("min_session_minutes", Number(event.target.value))
                  }
                  slotProps={{ htmlInput: { min: 1, max: 1440 } }}
                  error={sessionInvalid}
                  helperText={
                    sessionInvalid
                      ? t("settings.campaigns.sessionRangeError")
                      : undefined
                  }
                  sx={{ minWidth: 190 }}
                />
                <TextField
                  select
                  label={t("settings.campaigns.recipientGroup")}
                  value={campaign.recipient_group}
                  onChange={(event) =>
                    update("recipient_group", event.target.value)
                  }
                  sx={{ minWidth: 170 }}
                >
                  <MenuItem value="all">
                    {t("settings.campaigns.allPlayers")}
                  </MenuItem>
                  <MenuItem value="vip">
                    {t("settings.campaigns.vipPlayers")}
                  </MenuItem>
                  <MenuItem value="non_vip">
                    {t("settings.campaigns.nonVipPlayers")}
                  </MenuItem>
                </TextField>
              </>
            ) : (
              <TextField
                label={t("settings.campaigns.broadcastInterval")}
                type="number"
                value={rawIntervalSeconds}
                onChange={(event) =>
                  update("time_sec", Number(event.target.value))
                }
                slotProps={{ htmlInput: { min: 1, max: 86400, step: 1 } }}
                error={intervalInvalid}
                helperText={
                  intervalInvalid
                    ? t("settings.campaigns.broadcastIntervalError")
                    : t("settings.campaigns.broadcastIntervalHelp")
                }
                sx={{ minWidth: 190 }}
              />
            )}
            <TextField
              label={t("settings.campaigns.minPlayers")}
              type="number"
              value={campaign.min_players}
              onChange={(event) =>
                update("min_players", Number(event.target.value))
              }
              slotProps={{ htmlInput: { min: 0, max: 100 } }}
              error={minPlayersInvalid}
              helperText={
                minPlayersInvalid
                  ? t("settings.campaigns.playerRangeError")
                  : undefined
              }
              sx={{ width: { xs: "100%", md: 150 } }}
            />
            <TextField
              label={t("settings.campaigns.maxPlayers")}
              type="number"
              value={campaign.max_players}
              onChange={(event) =>
                update("max_players", Number(event.target.value))
              }
              slotProps={{ htmlInput: { min: 0, max: 100 } }}
              error={maxPlayersInvalid}
              helperText={
                maxPlayersInvalid
                  ? t("settings.campaigns.playerRangeError")
                  : undefined
              }
              sx={{ width: { xs: "100%", md: 150 } }}
            />
            <FormControlLabel
              sx={{ ml: { md: 1 } }}
              control={
                <Switch
                  checked={campaign.pause_during_seeding}
                  onChange={(event) =>
                    update("pause_during_seeding", event.target.checked)
                  }
                />
              }
              label={t("settings.campaigns.pauseDuringSeeding")}
            />
          </Stack>

          {isPlayerMessage && deliveryStatus && (
            <Stack gap={1}>
              <Stack direction="row" gap={1} flexWrap="wrap">
                <Chip
                  size="small"
                  label={t("settings.campaigns.pending", {
                    count: deliveryStatus.pending,
                  })}
                />
                <Chip
                  size="small"
                  color="success"
                  variant="outlined"
                  label={t("settings.campaigns.sent24h", {
                    count: deliveryStatus.sent_24h,
                  })}
                />
                <Chip
                  size="small"
                  color={deliveryStatus.failed_24h ? "error" : "default"}
                  variant="outlined"
                  label={t("settings.campaigns.failed24h", {
                    count: deliveryStatus.failed_24h,
                  })}
                />
                {deliveryStatus.last_sent_at && (
                  <Chip
                    size="small"
                    variant="outlined"
                    label={t("settings.campaigns.lastSent", {
                      time: new Date(
                        deliveryStatus.last_sent_at
                      ).toLocaleString(),
                    })}
                  />
                )}
              </Stack>
              {deliveryStatus.recent?.length > 0 && (
                <Box component="details">
                  <Typography
                    component="summary"
                    variant="body2"
                    color="text.secondary"
                    sx={{ cursor: "pointer" }}
                  >
                    {t("settings.campaigns.recentDeliveries")}
                  </Typography>
                  <Stack spacing={0.5} sx={{ mt: 1 }}>
                    {deliveryStatus.recent.map((delivery) => (
                      <Typography
                        key={delivery.id}
                        variant="caption"
                        color={
                          delivery.status === "failed"
                            ? "error"
                            : "text.secondary"
                        }
                      >
                        {delivery.player_name} ·{" "}
                        {t(
                          `settings.campaigns.deliveryStatus.${delivery.status}`
                        )}{" "}
                        · {new Date(delivery.updated_at).toLocaleString()}
                      </Typography>
                    ))}
                  </Stack>
                </Box>
              )}
            </Stack>
          )}

          {testResult && (
            <Alert severity={testResult.severity}>{testResult.text}</Alert>
          )}

          <Box>
            <Button
              size="small"
              variant="outlined"
              startIcon={<PlayArrowIcon />}
              onClick={() => onTest(campaign)}
              disabled={testing || !campaign.message.trim()}
              sx={{ minHeight: 44 }}
            >
              {testing
                ? t("settings.campaigns.testing")
                : t("settings.campaigns.testNow")}
            </Button>
          </Box>
        </Stack>
      </CardContent>
    </Card>
  );
};

const BroadcastCampaignPage = () => {
  const { t } = useTranslation();
  const data = useLoaderData();
  const actionData = useActionData();
  const navigation = useNavigation();
  const submit = useSubmit();
  const [config, setConfig] = useState(() => normalizeConfig(data.config));
  const [testingId, setTestingId] = useState(null);
  const [testResult, setTestResult] = useState(null);
  const [testCampaign, setTestCampaign] = useState(null);
  const [onlinePlayers, setOnlinePlayers] = useState([]);
  const [selectedPlayerId, setSelectedPlayerId] = useState("");
  const [loadingPlayers, setLoadingPlayers] = useState(false);
  const [deliveryStatus, setDeliveryStatus] = useState(data.deliveryStatus);
  const lifecycleAvailable = data.vipLifecycleStatus?.available === true;
  const [activeSection, setActiveSection] = useState("campaigns");
  const [selectedCampaignId, setSelectedCampaignId] = useState(
    () => normalizeConfig(data.config).messages[0]?.id ?? null
  );
  const [pendingDeleteIndex, setPendingDeleteIndex] = useState(null);

  useEffect(() => {
    const nextConfig = normalizeConfig(data.config);
    setConfig(nextConfig);
    setSelectedCampaignId((current) =>
      nextConfig.messages.some((campaign) => campaign.id === current)
        ? current
        : nextConfig.messages[0]?.id ?? null
    );
  }, [data.config]);

  useEffect(() => {
    setDeliveryStatus(data.deliveryStatus);
    if (isFakeMode()) return undefined;
    const interval = window.setInterval(async () => {
      try {
        setDeliveryStatus(await cmd.GET_CAMPAIGN_DELIVERY_STATUS());
      } catch {
        // Keep the last good snapshot; route-level errors would disrupt editing.
      }
    }, 30000);
    return () => window.clearInterval(interval);
  }, [data.deliveryStatus]);

  const activeCount = config.messages.filter(
    (campaign) => campaign.enabled
  ).length;
  const hasChanges = useMemo(
    () => !isEqual(config, normalizeConfig(data.config)),
    [config, data.config]
  );
  const isValid =
    config.messages.every(
      (campaign) =>
        campaign.message.trim() &&
        Number.isInteger(Number(campaign.time_sec)) &&
        Number(campaign.time_sec) > 0 && Number(campaign.time_sec) <= 86400 &&
        campaign.min_players >= 0 &&
        campaign.max_players <= 100 &&
        campaign.min_players <= campaign.max_players &&
        (campaign.delivery_mode !== "player_message" ||
          (campaign.min_session_minutes >= 1 &&
            campaign.min_session_minutes <= 1440))
    ) &&
    config.player_message_interval_sec >= 5 &&
    config.player_message_interval_sec <= 300 &&
    config.player_message_gap_sec >= 60 &&
    config.player_message_gap_sec <= 3600 &&
    (!lifecycleAvailable ||
      (config.vip_lifecycle.expiry_window_hours >= 1 &&
        config.vip_lifecycle.expiry_window_hours <= 168 &&
        config.vip_lifecycle.status_cache_seconds >= 30 &&
        config.vip_lifecycle.status_cache_seconds <= 900 &&
        Object.values(config.vip_lifecycle.campaigns).every(
          (campaign) =>
            (!campaign.enabled || campaign.message.trim()) &&
            campaign.min_session_minutes >= 1 &&
            campaign.min_session_minutes <= 1440 &&
            campaign.min_players >= 0 &&
            campaign.max_players <= 100 &&
            campaign.min_players <= campaign.max_players
        )));
  const saving = navigation.state === "submitting";

  const handleCampaignChange = (index, campaign) => {
    setConfig((previous) => ({
      ...previous,
      messages: previous.messages.map((item, itemIndex) =>
        itemIndex === index ? campaign : item
      ),
    }));
  };

  const handleAdd = () => {
    const campaign = createCampaign(config.messages.length);
    setConfig((previous) => ({
      ...previous,
      messages: [...previous.messages, campaign],
    }));
    setSelectedCampaignId(campaign.id);
    setActiveSection("campaigns");
  };

  const handleDuplicate = (index) => {
    const source = config.messages[index];
    const duplicate = {
      ...source,
      id: `campaign-${Date.now()}-${index}`,
      title: source.title
        ? t("settings.campaigns.copyName", { name: source.title })
        : "",
    };
    setConfig((previous) => ({
      ...previous,
      messages: [
        ...previous.messages.slice(0, index + 1),
        duplicate,
        ...previous.messages.slice(index + 1),
      ],
    }));
    setSelectedCampaignId(duplicate.id);
  };

  const handleDelete = (index) => {
    setPendingDeleteIndex(index);
  };

  const confirmDelete = () => {
    if (pendingDeleteIndex === null) return;
    const remaining = config.messages.filter(
      (_, itemIndex) => itemIndex !== pendingDeleteIndex
    );
    setConfig((previous) => ({ ...previous, messages: remaining }));
    setSelectedCampaignId(
      remaining[Math.min(pendingDeleteIndex, remaining.length - 1)]?.id ?? null
    );
    setPendingDeleteIndex(null);
  };

  const handleTemplateChange = (_, template) => {
    if (!template) return;
    const templateMessages = unpackBroadcastMessage(template.content);
    const importedCampaigns = templateMessages.map((message, index) => ({
      ...createCampaign(config.messages.length + index),
      title: template.title,
      ...message,
    }));
    setConfig((previous) => ({
      ...previous,
      messages: [...previous.messages, ...importedCampaigns],
    }));
    setSelectedCampaignId(importedCampaigns[0]?.id ?? selectedCampaignId);
    setActiveSection("campaigns");
  };

  const handleTest = async (campaign) => {
    if (campaign.delivery_mode === "player_message") {
      setTestCampaign(campaign);
      setSelectedPlayerId("");
      setLoadingPlayers(true);
      try {
        const players = isFakeMode()
          ? [
              { player_id: "76561198000000001", name: "FLN_Raven" },
              { player_id: "76561198000000002", name: "FrontlinePlayer" },
            ]
          : await cmd.GET_ONLINE_PLAYERS();
        setOnlinePlayers(players ?? []);
      } catch (error) {
        setTestCampaign(null);
        setTestResult({
          severity: "error",
          text: t("settings.campaigns.testFailed", {
            message: error?.message || t("errors.unknown"),
          }),
        });
      } finally {
        setLoadingPlayers(false);
      }
      return;
    }

    setTestingId(campaign.id);
    setTestResult(null);
    try {
      if (!isFakeMode()) {
        await cmd.SET_BROADCAST_MESSAGE({
          payload: { message: campaign.message },
        });
      }
      setTestResult({
        severity: "success",
        text: t("settings.campaigns.testSent"),
      });
    } catch (error) {
      setTestResult({
        severity: "error",
        text: t("settings.campaigns.testFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
    } finally {
      setTestingId(null);
    }
  };

  const handlePlayerTest = async () => {
    if (!testCampaign || !selectedPlayerId) return;
    setTestingId(testCampaign.id);
    setTestResult(null);
    try {
      if (!isFakeMode()) {
        await cmd.TEST_PLAYER_CAMPAIGN({
          payload: { campaign: testCampaign, player_id: selectedPlayerId },
          throwRouteError: false,
        });
      }
      setTestResult({
        severity: "success",
        text: t("settings.campaigns.playerTestSent"),
      });
      setTestCampaign(null);
    } catch (error) {
      setTestResult({
        severity: "error",
        text: playerTestErrorKey(error?.message)
          ? t(playerTestErrorKey(error.message))
          : t("settings.campaigns.testFailed", { message: error?.message || t("errors.unknown") }),
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleSave = () => {
    submit(config, { method: "post", encType: "application/json" });
  };

  const handleModeChange = (mode) => {
    setConfig((previous) => ({
      ...previous,
      enabled: mode !== "off",
      randomize: mode === "random",
    }));
  };

  const handleGlobalChange = (field, value) => {
    setConfig((previous) => ({ ...previous, [field]: value }));
  };

  const handleReset = () => {
    const savedConfig = normalizeConfig(data.config);
    setConfig(savedConfig);
    setSelectedCampaignId(savedConfig.messages[0]?.id ?? null);
    setTestResult(null);
  };

  const selectedCampaignIndex = config.messages.findIndex(
    (campaign) => campaign.id === selectedCampaignId
  );
  const selectedCampaign = config.messages[selectedCampaignIndex] ?? null;
  const selectedDeliveryStatus = selectedCampaign
    ? deliveryStatus?.campaigns?.find(
        (status) => status.campaign_id === selectedCampaign.id
      )
    : null;

  const templatePicker = (
    <Suspense fallback={<TemplateSkeleton />}>
      <Await
        resolve={data.templates}
        errorElement={
          <AsyncClientError title={t("settings.broadcast.templates")} />
        }
      >
        {(templates) =>
          templates.length > 0 ? (
            <Autocomplete
              options={templates}
              onChange={handleTemplateChange}
              getOptionLabel={(option) => option.title}
              renderInput={(params) => (
                <TextField
                  {...params}
                  label={t("settings.campaigns.importTemplate")}
                />
              )}
            />
          ) : null
        }
      </Await>
    </Suspense>
  );

  const campaignEditor = selectedCampaign ? (
    <CampaignCard
      key={selectedCampaign.id}
      campaign={selectedCampaign}
      index={selectedCampaignIndex}
      onChange={handleCampaignChange}
      onDuplicate={handleDuplicate}
      onDelete={handleDelete}
      onTest={handleTest}
      testing={testingId === selectedCampaign.id}
      deliveryStatus={selectedDeliveryStatus}
      testResult={testResult}
    />
  ) : (
    <Stack alignItems="center" spacing={1.5} sx={{ p: { xs: 3, md: 6 } }}>
      <CampaignIcon sx={{ fontSize: 44, color: "text.disabled" }} />
      <Typography variant="h6">{t("settings.campaigns.emptyTitle")}</Typography>
      <Typography color="text.secondary" textAlign="center">
        {t("settings.campaigns.emptyText")}
      </Typography>
      <Button variant="contained" startIcon={<AddIcon />} onClick={handleAdd}>
        {t("settings.campaigns.addFirst")}
      </Button>
    </Stack>
  );

  const vipLifecyclePanel = lifecycleAvailable ? (
    <VipLifecyclePanel
      value={config.vip_lifecycle}
      onChange={(vipLifecycle) =>
        setConfig((previous) => ({
          ...previous,
          vip_lifecycle: vipLifecycle,
        }))
      }
      initialStatus={data.vipLifecycleStatus}
    />
  ) : null;

  return (
    <>
      <BroadcastCampaignWorkbench
        config={config}
        activeCount={activeCount}
        activeSection={activeSection}
        onSectionChange={setActiveSection}
        selectedCampaignId={selectedCampaignId}
        onSelectCampaign={setSelectedCampaignId}
        onAdd={handleAdd}
        onModeChange={handleModeChange}
        onGlobalChange={handleGlobalChange}
        onReset={handleReset}
        onSave={handleSave}
        hasChanges={hasChanges}
        isValid={isValid}
        saving={saving}
        actionSaved={actionData?.saved}
        templatePicker={templatePicker}
        campaignEditor={campaignEditor}
        deliveryStatus={deliveryStatus}
        lifecycleAvailable={lifecycleAvailable}
        lifecyclePanel={vipLifecyclePanel}
      />

      <Dialog
        open={Boolean(testCampaign)}
        onClose={() => !testingId && setTestCampaign(null)}
        fullWidth
        maxWidth="sm"
        slotProps={{ paper: { sx: { borderRadius: 0 } } }}
      >
        <DialogTitle>{t("settings.campaigns.selectTestPlayer")}</DialogTitle>
        <DialogContent>
          <TextField
            select
            fullWidth
            sx={{ mt: 1 }}
            label={t("settings.campaigns.onlinePlayer")}
            value={selectedPlayerId}
            onChange={(event) => setSelectedPlayerId(event.target.value)}
            disabled={loadingPlayers}
            helperText={
              loadingPlayers
                ? t("common.loading")
                : onlinePlayers.length === 0
                ? t("settings.campaigns.noOnlinePlayers")
                : t("settings.campaigns.testDoesNotCount")
            }
          >
            {onlinePlayers.map((player) => (
              <MenuItem key={player.player_id} value={player.player_id}>
                {player.name} · {player.player_id}
              </MenuItem>
            ))}
          </TextField>
        </DialogContent>
        <DialogActions>
          <Button
            onClick={() => setTestCampaign(null)}
            disabled={Boolean(testingId)}
          >
            {t("common.cancel")}
          </Button>
          <Button
            variant="contained"
            onClick={handlePlayerTest}
            disabled={!selectedPlayerId || Boolean(testingId)}
          >
            {testingId
              ? t("settings.campaigns.testing")
              : t("settings.campaigns.testNow")}
          </Button>
        </DialogActions>
      </Dialog>

      <Dialog
        open={pendingDeleteIndex !== null}
        onClose={() => setPendingDeleteIndex(null)}
        fullWidth
        maxWidth="xs"
        slotProps={{ paper: { sx: { borderRadius: 0 } } }}
      >
        <DialogTitle>{t("settings.campaigns.deleteTitle")}</DialogTitle>
        <DialogContent>
          <Typography color="text.secondary">
            {t("settings.campaigns.deleteDescription", {
              name:
                config.messages[pendingDeleteIndex]?.title ||
                t("settings.campaigns.untitledCampaign", {
                  count: Number(pendingDeleteIndex) + 1,
                }),
            })}
          </Typography>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setPendingDeleteIndex(null)}>
            {t("common.cancel")}
          </Button>
          <Button color="error" variant="contained" onClick={confirmDelete}>
            {t("common.delete")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default BroadcastCampaignPage;
