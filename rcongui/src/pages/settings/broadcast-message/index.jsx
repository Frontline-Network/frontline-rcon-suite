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
  Divider,
  FormControlLabel,
  IconButton,
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
});

const normalizeConfig = (config) => ({
  enabled: Boolean(config?.enabled),
  randomize: Boolean(config?.randomize),
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
    return defer({ config: fakeCampaignConfig, templates: Promise.resolve([]) });
  }

  return defer({
    config: normalizeConfig(await cmd.GET_BROADCAST_CONFIG()),
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
}) => {
  const { t } = useTranslation();
  const update = (field, value) => onChange(index, { ...campaign, [field]: value });
  const intervalMinutes = Math.max(1, Math.round(Number(campaign.time_sec) / 60));

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
            <Stack direction="row" alignItems="center" justifyContent="flex-end">
              <FormControlLabel
                control={
                  <Switch
                    checked={campaign.enabled}
                    onChange={(event) => update("enabled", event.target.checked)}
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
            helperText={t("settings.campaigns.messageHelp")}
          />

          <Stack direction={{ xs: "column", md: "row" }} gap={1.5}>
            <TextField
              label={t("settings.campaigns.interval")}
              type="number"
              value={intervalMinutes}
              onChange={(event) => update("time_sec", Number(event.target.value) * 60)}
              slotProps={{ htmlInput: { min: 1, max: 1440 } }}
              helperText={t("settings.campaigns.intervalUnit")}
              sx={{ minWidth: 190 }}
            />
            <TextField
              label={t("settings.campaigns.minPlayers")}
              type="number"
              value={campaign.min_players}
              onChange={(event) => update("min_players", Number(event.target.value))}
              slotProps={{ htmlInput: { min: 0, max: 100 } }}
              sx={{ width: { xs: "100%", md: 150 } }}
            />
            <TextField
              label={t("settings.campaigns.maxPlayers")}
              type="number"
              value={campaign.max_players}
              onChange={(event) => update("max_players", Number(event.target.value))}
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

  useEffect(() => {
    setConfig(normalizeConfig(data.config));
  }, [data.config]);

  const activeCount = config.messages.filter((campaign) => campaign.enabled).length;
  const hasChanges = useMemo(
    () => !isEqual(config, normalizeConfig(data.config)),
    [config, data.config]
  );
  const isValid = config.messages.every(
    (campaign) =>
      campaign.message.trim() &&
      Number(campaign.time_sec) > 0 &&
      campaign.min_players >= 0 &&
      campaign.max_players <= 100 &&
      campaign.min_players <= campaign.max_players
  );
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
      messages: [...previous.messages, createCampaign(previous.messages.length)],
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
    setTestingId(campaign.id);
    setTestResult(null);
    try {
      if (!isFakeMode()) {
        await cmd.SET_BROADCAST_MESSAGE({ payload: { message: campaign.message } });
      }
      setTestResult({ severity: "success", text: t("settings.campaigns.testSent") });
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
          <Stack direction={{ xs: "column", sm: "row" }} gap={2} alignItems={{ sm: "center" }}>
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
              label={t("settings.campaigns.activeCount", { count: activeCount })}
            />
          </Stack>
          <Stack direction={{ xs: "column", sm: "row" }} gap={1}>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={handleAdd}>
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
      </Paper>

      {!isValid && (
        <Alert severity="warning">{t("settings.campaigns.invalidRange")}</Alert>
      )}
      {actionData?.saved && (
        <Alert severity="success">{t("settings.campaigns.saved")}</Alert>
      )}
      {testResult && <Alert severity={testResult.severity}>{testResult.text}</Alert>}

      <Suspense fallback={<TemplateSkeleton />}>
        <Await
          resolve={data.templates}
          errorElement={<AsyncClientError title={t("settings.broadcast.templates")} />}
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
          <Button variant="contained" startIcon={<AddIcon />} onClick={handleAdd}>
            {t("settings.campaigns.addFirst")}
          </Button>
        </Paper>
      )}

      <Divider />
      <Typography variant="body2" color="text.secondary">
        {t("settings.campaigns.priorityNote")}
      </Typography>
    </Stack>
  );
};

export default BroadcastCampaignPage;
