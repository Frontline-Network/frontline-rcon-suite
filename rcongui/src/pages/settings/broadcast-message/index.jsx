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
  Divider,
  FormControlLabel,
  IconButton,
  MenuItem,
  Paper,
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
import SaveIcon from "@mui/icons-material/Save";
import ShuffleIcon from "@mui/icons-material/Shuffle";
import { useTranslation } from "react-i18next";
import isEqual from "lodash/isEqual";

import { AsyncClientError } from "@/components/shared/AsyncClientError";
import Padlock from "@/components/shared/Padlock";
import { isFakeMode } from "@/mirage/demo-data";
import { TEMPLATE_CATEGORY, unpackBroadcastMessage } from "@/utils/lib";
import { cmd } from "@/utils/fetchUtils";

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

const normalizeConfig = (config) => ({
  enabled: Boolean(config?.enabled),
  randomize: Boolean(config?.randomize),
  player_message_interval_sec: Number(
    config?.player_message_interval_sec ?? 10
  ),
  player_message_gap_sec: Number(config?.player_message_gap_sec ?? 300),
  messages: (config?.messages ?? []).map((campaign, index) => ({
    ...createCampaign(index),
    ...campaign,
    id: campaign.id || `legacy-campaign-${index}`,
  })),
});

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
    });
  }

  return defer({
    config: normalizeConfig(await cmd.GET_BROADCAST_CONFIG()),
    deliveryStatus: await cmd.GET_CAMPAIGN_DELIVERY_STATUS(),
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
}) => {
  const { t } = useTranslation();
  const update = (field, value) =>
    onChange(index, { ...campaign, [field]: value });
  const intervalMinutes = Math.max(
    1,
    Math.round(Number(campaign.time_sec) / 60)
  );
  const isPlayerMessage = campaign.delivery_mode === "player_message";

  return (
    <Card
      variant="outlined"
      sx={{
        borderColor: campaign.enabled ? "divider" : "rgba(255,255,255,0.1)",
        opacity: campaign.enabled ? 1 : 0.72,
      }}
    >
      <CardContent sx={{ p: { xs: 2, md: 2.5 }, "&:last-child": { pb: 2.5 } }}>
        <Stack spacing={2}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ xs: "stretch", sm: "center" }}
            gap={1}
          >
            <Stack direction="row" alignItems="center" gap={1} minWidth={0}>
              <CampaignIcon color={campaign.enabled ? "primary" : "disabled"} />
              <TextField
                value={campaign.title}
                onChange={(event) => update("title", event.target.value)}
                placeholder={t("settings.campaigns.namePlaceholder")}
                variant="standard"
                fullWidth
                slotProps={{ htmlInput: { maxLength: 80 } }}
                sx={{ maxWidth: 360 }}
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
                <IconButton onClick={() => onDuplicate(index)}>
                  <ContentCopyIcon />
                </IconButton>
              </Tooltip>
              <Tooltip title={t("common.delete")}>
                <IconButton color="error" onClick={() => onDelete(index)}>
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
            helperText={t(
              isPlayerMessage
                ? "settings.campaigns.playerMessageHelp"
                : "settings.campaigns.messageHelp"
            )}
          />

          <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
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
                label={t("settings.campaigns.interval")}
                type="number"
                value={intervalMinutes}
                onChange={(event) =>
                  update("time_sec", Number(event.target.value) * 60)
                }
                slotProps={{ htmlInput: { min: 1, max: 1440 } }}
                helperText={t("settings.campaigns.intervalUnit")}
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

          <Box>
            <Button
              size="small"
              variant="outlined"
              startIcon={<PlayArrowIcon />}
              onClick={() => onTest(campaign)}
              disabled={testing || !campaign.message.trim()}
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

  useEffect(() => {
    setConfig(normalizeConfig(data.config));
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
        Number(campaign.time_sec) > 0 &&
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
    config.player_message_gap_sec <= 3600;
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
    setConfig((previous) => ({
      ...previous,
      messages: [
        ...previous.messages,
        createCampaign(previous.messages.length),
      ],
    }));
  };

  const handleDuplicate = (index) => {
    setConfig((previous) => {
      const source = previous.messages[index];
      const duplicate = {
        ...source,
        id: `campaign-${Date.now()}-${index}`,
        title: source.title
          ? t("settings.campaigns.copyName", { name: source.title })
          : "",
      };
      return {
        ...previous,
        messages: [
          ...previous.messages.slice(0, index + 1),
          duplicate,
          ...previous.messages.slice(index + 1),
        ],
      };
    });
  };

  const handleDelete = (index) => {
    setConfig((previous) => ({
      ...previous,
      messages: previous.messages.filter((_, itemIndex) => itemIndex !== index),
    }));
  };

  const handleTemplateChange = (_, template) => {
    if (!template) return;
    const templateMessages = unpackBroadcastMessage(template.content);
    setConfig((previous) => ({
      ...previous,
      messages: [
        ...previous.messages,
        ...templateMessages.map((message, index) => ({
          ...createCampaign(previous.messages.length + index),
          title: template.title,
          ...message,
        })),
      ],
    }));
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
        text: t("settings.campaigns.testFailed", {
          message: error?.message || t("errors.unknown"),
        }),
      });
    } finally {
      setTestingId(null);
    }
  };

  const handleSave = () => {
    submit(config, { method: "post", encType: "application/json" });
  };

  return (
    <Stack spacing={2.5} sx={{ maxWidth: 1180, mx: "auto" }}>
      <Box>
        <Typography variant="overline" color="primary">
          {t("settings.campaigns.eyebrow")}
        </Typography>
        <Typography variant="h4" component="h1">
          {t("settings.campaigns.title")}
        </Typography>
        <Typography color="text.secondary" sx={{ mt: 0.5, maxWidth: 760 }}>
          {t("settings.campaigns.subtitle")}
        </Typography>
      </Box>

      <Paper variant="outlined" sx={{ p: { xs: 2, md: 2.5 } }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ xs: "stretch", md: "center" }}
          gap={2}
        >
          <Stack
            direction={{ xs: "column", sm: "row" }}
            gap={2}
            alignItems={{ sm: "center" }}
          >
            <Padlock
              label={t(
                config.enabled
                  ? "settings.campaigns.moduleActive"
                  : "settings.campaigns.modulePaused"
              )}
              checked={config.enabled}
              handleChange={(checked) =>
                setConfig((previous) => ({ ...previous, enabled: checked }))
              }
            />
            <FormControlLabel
              control={
                <Switch
                  checked={config.randomize}
                  onChange={(event) =>
                    setConfig((previous) => ({
                      ...previous,
                      randomize: event.target.checked,
                    }))
                  }
                />
              }
              label={
                <Stack direction="row" gap={0.75} alignItems="center">
                  <ShuffleIcon fontSize="small" />
                  <span>{t("settings.campaigns.randomOrder")}</span>
                </Stack>
              }
            />
            <Chip
              color={activeCount ? "success" : "default"}
              label={t("settings.campaigns.activeCount", {
                count: activeCount,
              })}
            />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
            <Button
              variant="outlined"
              startIcon={<AddIcon />}
              onClick={handleAdd}
            >
              {t("settings.campaigns.add")}
            </Button>
            <Button
              variant="contained"
              startIcon={<SaveIcon />}
              disabled={!hasChanges || !isValid || saving}
              onClick={handleSave}
            >
              {saving ? t("common.loading") : t("common.save")}
            </Button>
          </Stack>
        </Stack>
        <Divider sx={{ my: 2 }} />
        <Stack direction={{ xs: "column", sm: "row" }} gap={2}>
          <TextField
            label={t("settings.campaigns.globalSendInterval")}
            type="number"
            value={config.player_message_interval_sec}
            onChange={(event) =>
              setConfig((previous) => ({
                ...previous,
                player_message_interval_sec: Number(event.target.value),
              }))
            }
            slotProps={{ htmlInput: { min: 5, max: 300 } }}
            helperText={t("settings.campaigns.seconds")}
            sx={{ minWidth: 230 }}
          />
          <TextField
            label={t("settings.campaigns.playerGap")}
            type="number"
            value={Math.round(config.player_message_gap_sec / 60)}
            onChange={(event) =>
              setConfig((previous) => ({
                ...previous,
                player_message_gap_sec: Number(event.target.value) * 60,
              }))
            }
            slotProps={{ htmlInput: { min: 1, max: 60 } }}
            helperText={t("settings.campaigns.minutes")}
            sx={{ minWidth: 230 }}
          />
        </Stack>
      </Paper>

      {!isValid && (
        <Alert severity="warning">{t("settings.campaigns.invalidRange")}</Alert>
      )}
      {actionData?.saved && (
        <Alert severity="success">{t("settings.campaigns.saved")}</Alert>
      )}
      {testResult && (
        <Alert severity={testResult.severity}>{testResult.text}</Alert>
      )}

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

      <Stack spacing={1.5}>
        {config.messages.map((campaign, index) => (
          <CampaignCard
            key={campaign.id || index}
            campaign={campaign}
            index={index}
            onChange={handleCampaignChange}
            onDuplicate={handleDuplicate}
            onDelete={handleDelete}
            onTest={handleTest}
            testing={testingId === campaign.id}
            deliveryStatus={deliveryStatus?.campaigns?.find(
              (status) => status.campaign_id === campaign.id
            )}
          />
        ))}
      </Stack>

      {config.messages.length === 0 && (
        <Paper variant="outlined" sx={{ p: 5, textAlign: "center" }}>
          <CampaignIcon sx={{ fontSize: 48, color: "text.disabled" }} />
          <Typography variant="h6" sx={{ mt: 1 }}>
            {t("settings.campaigns.emptyTitle")}
          </Typography>
          <Typography color="text.secondary" sx={{ mb: 2 }}>
            {t("settings.campaigns.emptyText")}
          </Typography>
          <Button
            variant="contained"
            startIcon={<AddIcon />}
            onClick={handleAdd}
          >
            {t("settings.campaigns.addFirst")}
          </Button>
        </Paper>
      )}

      <Divider />
      <Typography variant="body2" color="text.secondary">
        {t("settings.campaigns.priorityNote")}
      </Typography>

      <Dialog
        open={Boolean(testCampaign)}
        onClose={() => !testingId && setTestCampaign(null)}
        fullWidth
        maxWidth="sm"
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
    </Stack>
  );
};

export default BroadcastCampaignPage;
