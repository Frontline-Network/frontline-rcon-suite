import React, {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  AlertTitle,
  Box,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  CircularProgress,
  Divider,
  FormControlLabel,
  MenuItem,
  Stack,
  Step,
  StepButton,
  Stepper,
  Switch,
  TextField,
  Typography,
  useMediaQuery,
  useTheme,
} from "@mui/material";
import {
  AutoAwesome as AiIcon,
  CheckCircle as HealthyIcon,
  CloudSync as DiagnosticsIcon,
  ExpandMore as ExpandMoreIcon,
  Forum as ReplyIcon,
  Key as ApiKeyIcon,
  Link as ConnectionIcon,
  Login as LoginIcon,
  Refresh as RefreshIcon,
  Security as PermissionsIcon,
  Send as TestIcon,
  SettingsEthernet as BrokerIcon,
  SmartToy as DiscordBotIcon,
  WarningAmber as WarningIcon,
} from "@mui/icons-material";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { useGlobalStore } from "@/stores/global-state";
import { discordRequest } from "@/utils/fetchUtils";
import ReportAdmin from "@/pages/settings/report-admin";

const ACTIONS = [
  "message",
  "punish",
  "kick",
  "temp_ban",
  "perma_ban",
  "blacklist",
  "remove_from_squad",
  "disband_squad",
];

const splitValues = (value) =>
  value
    .split(/[\n,]/)
    .map((item) => item.trim())
    .filter(Boolean);

const formatTimestamp = (value, language) => {
  if (!value) return null;
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return null;
  const code = String(language || "en").split("-")[0];
  const locale = { de: "de-DE", en: "en-GB", fr: "fr-FR" }[code] || "en-GB";
  return new Intl.DateTimeFormat(locale, {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
};

const SectionTitle = ({ icon, title, help }) => (
  <Stack direction="row" spacing={1.5} alignItems="flex-start">
    <Box
      sx={{
        display: "grid",
        placeItems: "center",
        width: 38,
        height: 38,
        flex: "0 0 auto",
        borderRadius: 1.5,
        bgcolor: "action.selected",
        color: "primary.main",
      }}
    >
      {icon}
    </Box>
    <Box>
      <Typography variant="h6" sx={{ fontWeight: 750, lineHeight: 1.25 }}>
        {title}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.35 }}>
        {help}
      </Typography>
    </Box>
  </Stack>
);

const StateChip = ({ state, t }) => {
  const normalized = state || "unknown";
  const color = [
    "active",
    "healthy",
    "online",
    "succeeded",
    "delivered",
  ].includes(normalized)
    ? "success"
    : ["degraded", "failed", "offline", "retrying"].includes(normalized)
    ? "warning"
    : "default";
  return (
    <Chip
      size="small"
      color={color}
      variant={color === "default" ? "outlined" : "filled"}
      label={t(`settings.discordReports.state_${normalized}`, {
        defaultValue: normalized,
      })}
    />
  );
};

const StatusTile = ({ icon, label, state, detail, t }) => (
  <Box
    sx={{
      minWidth: 0,
      p: 1.5,
      border: "1px solid",
      borderColor: "divider",
      borderRadius: 2,
      bgcolor: "background.default",
    }}
  >
    <Stack direction="row" spacing={1} alignItems="center">
      <Box sx={{ color: "text.secondary", display: "flex" }}>{icon}</Box>
      <Typography variant="caption" color="text.secondary" sx={{ flexGrow: 1 }}>
        {label}
      </Typography>
      <StateChip state={state} t={t} />
    </Stack>
    {detail && (
      <Typography variant="body2" sx={{ mt: 1, overflowWrap: "anywhere" }}>
        {detail}
      </Typography>
    )}
  </Box>
);

const TechnicalDetails = ({ error, status, t }) => {
  if (!error && !status?.last_diagnostic?.result) return null;
  return (
    <Accordion
      disableGutters
      elevation={0}
      sx={{ border: "1px solid", borderColor: "divider" }}
    >
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Typography variant="body2" sx={{ fontWeight: 700 }}>
          {t("settings.discordReports.technicalDetails")}
        </Typography>
      </AccordionSummary>
      <AccordionDetails>
        <Stack spacing={1}>
          {error && (
            <Typography
              component="code"
              variant="caption"
              sx={{ overflowWrap: "anywhere" }}
            >
              {error}
            </Typography>
          )}
          {status?.last_diagnostic?.result && (
            <Typography
              component="pre"
              variant="caption"
              sx={{ m: 0, whiteSpace: "pre-wrap", overflowWrap: "anywhere" }}
            >
              {JSON.stringify(status.last_diagnostic.result, null, 2)}
            </Typography>
          )}
        </Stack>
      </AccordionDetails>
    </Accordion>
  );
};

export default function DiscordReportBotCard() {
  const { t, i18n } = useTranslation();
  const theme = useTheme();
  const compact = useMediaQuery(theme.breakpoints.down("sm"));
  const serverState = useGlobalStore((state) => state.serverState);
  const [config, setConfig] = useState(null);
  const [status, setStatus] = useState(null);
  const [error, setError] = useState("");
  const [installError, setInstallError] = useState("");
  const [channelId, setChannelId] = useState("");
  const [roles, setRoles] = useState([]);
  const [discordOptions, setDiscordOptions] = useState({
    guild: null,
    channels: [],
    roles: [],
  });
  const [terms, setTerms] = useState("");
  const [exceptions, setExceptions] = useState("");
  const [regexes, setRegexes] = useState("");
  const [aiStatus, setAiStatus] = useState(null);
  const [apiKey, setApiKey] = useState("");
  const [editingConnection, setEditingConnection] = useState(false);
  const [activeStep, setActiveStep] = useState(0);
  const stepInitialized = useRef(false);
  const [busyAction, setBusyAction] = useState("");

  const steps = useMemo(
    () => [
      "install",
      "guild",
      "channelRoles",
      "actions",
      "ai",
      "test",
      "activate",
    ],
    []
  );

  const apply = useCallback((next) => {
    setConfig(next);
    setChannelId(next.channel_id || "");
    setRoles(next.moderator_role_ids || []);
    setTerms((next.policy?.custom_terms || []).join("\n"));
    setExceptions((next.policy?.exceptions || []).join("\n"));
    setRegexes((next.policy?.custom_regexes || []).join("\n"));
  }, []);

  const captureError = useCallback((requestError) => {
    setError(requestError?.message || String(requestError));
  }, []);

  const loadStatus = useCallback(async () => {
    const next = await discordRequest("status");
    setStatus(next);
    return next;
  }, []);

  const loadDiscordOptions = useCallback(async () => {
    const options = await discordRequest("options");
    setDiscordOptions({
      guild: options.guild || null,
      channels: options.channels || [],
      roles: options.roles || [],
    });
    return options;
  }, []);

  const detectServer = async () => {
    setBusyAction("detect");
    try {
      await loadDiscordOptions();
      setError("");
    } catch (requestError) {
      captureError(requestError);
    } finally {
      setBusyAction("");
    }
  };

  const loadAiStatus = useCallback(async () => {
    const next = await discordRequest("ai/status");
    setAiStatus((previous) => ({ ...(previous || {}), ...next }));
    return next;
  }, []);

  useEffect(() => {
    discordRequest("integration")
      .then(async (next) => {
        apply(next);
        const operationalResults = await Promise.allSettled([
          loadDiscordOptions(),
          loadStatus(),
        ]);
        const failedOperation = operationalResults.find(
          (result) => result.status === "rejected"
        );
        if (failedOperation) captureError(failedOperation.reason);
        else setError("");
        if (next.connected) {
          await loadAiStatus().catch(() => setAiStatus(null));
        }
        if (!stepInitialized.current) {
          setActiveStep(next.connected ? 5 : 0);
          stepInitialized.current = true;
        }
      })
      .catch(captureError);
  }, [apply, captureError, loadAiStatus, loadDiscordOptions, loadStatus]);

  useEffect(() => {
    if (aiStatus?.state !== "pending") return undefined;
    const timer = window.setInterval(
      () => loadAiStatus().catch(() => null),
      3000
    );
    return () => window.clearInterval(timer);
  }, [aiStatus?.state, loadAiStatus]);

  const installDiscordApp = async () => {
    let popup;
    setInstallError("");
    setBusyAction("install");
    try {
      popup = window.open("about:blank", "_blank");
      const pairing = await discordRequest("pairings", { method: "POST" });
      if (popup) {
        popup.opener = null;
        popup.location = pairing.install_url;
      } else {
        window.location.assign(pairing.install_url);
      }
      setError("");
      setActiveStep(1);
    } catch (requestError) {
      setInstallError(requestError?.message || String(requestError));
      captureError(requestError);
      // Closing a blocked or user-closed popup must not hide the API error.
      try {
        if (popup && !popup.closed) popup.close();
      } catch {
        // The persistent inline alert below remains available.
      }
    } finally {
      setBusyAction("");
    }
  };

  const connect = async () => {
    setBusyAction("connect");
    try {
      const next = await discordRequest("connect", {
        method: "POST",
        payload: {
          channel_id: channelId,
          channel_name:
            discordOptions.channels.find((item) => item.id === channelId)
              ?.name || "",
          moderator_role_ids: roles,
        },
      });
      apply(next);
      await Promise.all([loadDiscordOptions(), loadStatus()]);
      setEditingConnection(false);
      setError("");
      setActiveStep(3);
      toast.success(t("settings.discordReports.connected"));
    } catch (requestError) {
      captureError(requestError);
    } finally {
      setBusyAction("");
    }
  };

  const save = async (activate = config?.enabled) => {
    setBusyAction("save");
    try {
      const policy = {
        profile_id: "frontline-default",
        version: "1",
        language: config.language,
        enabled_sources: ["report", "ai_chat", "ai_player_name"],
        alert_threshold: 0.9,
        shadow_threshold: 0.7,
        hard_rule_ids: config.policy?.hard_rule_ids || [],
        custom_terms: splitValues(terms),
        exceptions: splitValues(exceptions),
        custom_regexes: splitValues(regexes),
      };
      const next = await discordRequest("integration", {
        method: "PUT",
        payload: {
          enabled: activate,
          moderator_role_ids: roles,
          allowed_actions: config.allowed_actions || [],
          language: config.language,
          ai_config: config.ai_config || {},
          ...(apiKey ? { api_key: apiKey } : {}),
          policy,
          reporter_templates: config.reporter_templates || {},
        },
      });
      apply(next);
      setApiKey("");
      setError("");
      await loadStatus();
      toast.success(t("settings.discordReports.saved"));
      return next;
    } catch (requestError) {
      captureError(requestError);
      return null;
    } finally {
      setBusyAction("");
    }
  };

  const runDiagnostics = async () => {
    setBusyAction("diagnostics");
    try {
      await discordRequest("diagnostics", { method: "POST" });
      await loadStatus();
      setError("");
      toast.success(t("settings.discordReports.diagnosticsComplete"));
    } catch (requestError) {
      captureError(requestError);
      await loadStatus().catch(() => null);
    } finally {
      setBusyAction("");
    }
  };

  const sendTest = async () => {
    setBusyAction("test");
    try {
      await discordRequest("test-message", { method: "POST" });
      await loadStatus();
      setError("");
      toast.success(t("settings.discordReports.testSent"));
    } catch (requestError) {
      captureError(requestError);
      await loadStatus().catch(() => null);
    } finally {
      setBusyAction("");
    }
  };

  const disconnect = async () => {
    setBusyAction("disconnect");
    try {
      const next = await discordRequest("integration", { method: "DELETE" });
      apply(next);
      setStatus(null);
      setDiscordOptions({ guild: null, channels: [], roles: [] });
      setActiveStep(0);
      setError("");
    } catch (requestError) {
      captureError(requestError);
    } finally {
      setBusyAction("");
    }
  };

  const repair = async () => {
    setBusyAction("repair");
    try {
      await Promise.all([loadDiscordOptions(), loadStatus()]);
      setError("");
      toast.success(t("settings.discordReports.repairComplete"));
    } catch (requestError) {
      captureError(requestError);
    } finally {
      setBusyAction("");
    }
  };

  if (!config) {
    if (!error) return <CircularProgress size={28} />;
    return (
      <Stack spacing={1.5}>
        <Alert severity="warning" icon={<WarningIcon />}>
          {t("settings.discordReports.actionFailed")}
        </Alert>
        <TechnicalDetails error={error} status={status} t={t} />
      </Stack>
    );
  }

  const completed = [
    Boolean(discordOptions.guild || config?.connected),
    Boolean(discordOptions.guild || config?.guild_id),
    Boolean(config?.connected),
    Boolean(
      config?.connected && roles.length && config.allowed_actions?.length
    ),
    true,
    status?.last_test?.state === "succeeded",
    Boolean(config?.enabled),
  ];
  const canOpenStep = (index) => index <= 2 || Boolean(config?.connected);
  const canContinue =
    activeStep === 1
      ? Boolean(discordOptions.guild || config?.guild_id)
      : activeStep === 2
      ? Boolean(config?.connected)
      : true;
  const diagnostic = status?.last_diagnostic?.result;
  const gameLabel =
    serverState?.game === "hll_vietnam"
      ? "Hell Let Loose: Vietnam"
      : serverState?.game === "hll"
      ? "Hell Let Loose"
      : t("settings.discordReports.gameUnknown");
  const serverLabel = serverState
    ? `${
        serverState.short_name ||
        serverState.name ||
        t("settings.discordReports.serverFallback")
      } · #${serverState.server_number ?? "–"} · ${gameLabel}`
    : t("settings.discordReports.serverContextUnavailable");

  const renderChannelAndRoles = () => (
    <Stack spacing={2.5}>
      <SectionTitle
        icon={<PermissionsIcon />}
        title={t("settings.discordReports.step_channelRoles")}
        help={t("settings.discordReports.channelRolesHelp")}
      />
      {config?.connected && !editingConnection ? (
        <>
          <Alert severity="success">
            {t("settings.discordReports.connectedTo", {
              guild:
                config.guild_name ||
                t("settings.discordReports.guildNotDetected"),
              channel: config.channel_name ? `#${config.channel_name}` : "–",
            })}
          </Alert>
          <Button
            variant="outlined"
            onClick={() => setEditingConnection(true)}
            sx={{ alignSelf: "flex-start" }}
          >
            {t("settings.discordReports.changeConnection")}
          </Button>
        </>
      ) : (
        <>
          {config?.connected && (
            <Alert severity="warning">
              {t("settings.discordReports.changeConnectionHint")}
            </Alert>
          )}
          <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
            <TextField
              label={t("settings.discordReports.discordServer")}
              value={discordOptions.guild?.name || config?.guild_name || ""}
              helperText={t("settings.discordReports.guildDetectedHelp")}
              slotProps={{ input: { readOnly: true } }}
              fullWidth
            />
            <TextField
              select
              label={t("settings.discordReports.reportChannel")}
              value={channelId}
              onChange={(event) => setChannelId(event.target.value)}
              fullWidth
            >
              {discordOptions.channels.map((channel) => (
                <MenuItem key={channel.id} value={channel.id}>
                  #{channel.name}
                </MenuItem>
              ))}
            </TextField>
          </Stack>
        </>
      )}
      <TextField
        select
        label={t("settings.discordReports.roles")}
        value={roles}
        onChange={(event) => {
          const value = event.target.value;
          setRoles(typeof value === "string" ? value.split(",") : value);
        }}
        helperText={t("settings.discordReports.rolesHelp")}
        slotProps={{
          select: {
            multiple: true,
            renderValue: (selected) =>
              selected
                .map(
                  (id) =>
                    discordOptions.roles.find((role) => role.id === id)?.name ||
                    "–"
                )
                .join(", "),
          },
        }}
      >
        {discordOptions.roles.map((role) => (
          <MenuItem key={role.id} value={role.id}>
            {role.name}
          </MenuItem>
        ))}
      </TextField>
      {(!config?.connected || editingConnection) && (
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button
            variant="contained"
            disabled={
              !discordOptions.guild ||
              !channelId ||
              !roles.length ||
              busyAction === "connect"
            }
            onClick={connect}
          >
            {busyAction === "connect"
              ? t("settings.discordReports.connecting")
              : t("settings.discordReports.saveConnection")}
          </Button>
          {config?.connected && (
            <Button onClick={() => setEditingConnection(false)}>
              {t("settings.discordReports.cancel")}
            </Button>
          )}
        </Stack>
      )}
    </Stack>
  );

  const renderActions = () => (
    <Stack spacing={2.5}>
      <SectionTitle
        icon={<PermissionsIcon />}
        title={t("settings.discordReports.step_actions")}
        help={t("settings.discordReports.sectionPermissionsHelp")}
      />
      <TextField
        select
        label={t("settings.discordReports.language")}
        value={config.language || "de"}
        onChange={(event) =>
          setConfig({ ...config, language: event.target.value })
        }
        sx={{ maxWidth: 360 }}
      >
        <MenuItem value="de">
          {t("settings.discordReports.languageGerman")}
        </MenuItem>
        <MenuItem value="en">
          {t("settings.discordReports.languageEnglish")}
        </MenuItem>
        <MenuItem value="fr">{t("language.fr")}</MenuItem>
      </TextField>
      <Typography variant="subtitle2" color="text.secondary">
        {t("settings.discordReports.allowedActions")}
      </Typography>
      <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
        {ACTIONS.map((action) => {
          const active = (config.allowed_actions || []).includes(action);
          return (
            <Chip
              key={action}
              clickable
              variant={active ? "filled" : "outlined"}
              color={active ? "primary" : "default"}
              label={t(`settings.discordReports.action_${action}`)}
              onClick={() =>
                setConfig({
                  ...config,
                  allowed_actions: active
                    ? config.allowed_actions.filter((item) => item !== action)
                    : [...(config.allowed_actions || []), action],
                })
              }
            />
          );
        })}
      </Stack>
      <Alert severity="info">{t("settings.discordReports.actionSafety")}</Alert>
      <Divider />
      <SectionTitle
        icon={<ReplyIcon />}
        title={t("settings.discordReports.sectionTemplates")}
        help={t("settings.discordReports.sectionTemplatesHelp")}
      />
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          gap: 2,
        }}
      >
        {["received", "claimed", "resolved", "dismissed"].map((templateKey) => (
          <TextField
            key={templateKey}
            label={t(`settings.discordReports.template_${templateKey}`)}
            value={config.reporter_templates?.[templateKey] || ""}
            onChange={(event) =>
              setConfig({
                ...config,
                reporter_templates: {
                  ...(config.reporter_templates || {}),
                  [templateKey]: event.target.value,
                },
              })
            }
            fullWidth
          />
        ))}
      </Box>
    </Stack>
  );

  const renderAi = () => {
    const provider = config.ai_config?.provider || "api_key";
    return (
      <Stack spacing={2.5}>
        <ReportAdmin embedded />
        <Divider />
        <SectionTitle
          icon={<AiIcon />}
          title={t("settings.discordReports.step_ai")}
          help={t("settings.discordReports.sectionAiHelp")}
        />
        <Alert severity="info">
          {t("settings.discordReports.externalBilling")}
        </Alert>
        <TextField
          select
          label={t("settings.discordReports.aiProvider")}
          value={provider}
          onChange={(event) =>
            setConfig({
              ...config,
              ai_config: {
                ...(config.ai_config || {}),
                provider: event.target.value,
              },
            })
          }
          helperText={t(`settings.discordReports.provider_${provider}_help`)}
          fullWidth
        >
          <MenuItem value="api_key">
            {t("settings.discordReports.provider_api_key")}
          </MenuItem>
          <MenuItem value="codex">
            {t("settings.discordReports.provider_codex")}
          </MenuItem>
        </TextField>
        {provider === "api_key" && (
          <TextField
            type="password"
            label={t("settings.discordReports.apiKey")}
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder={config.has_api_key ? "sk-••••••••••••" : "sk-…"}
            helperText={
              config.has_api_key
                ? t("settings.discordReports.apiKeyStored")
                : t("settings.discordReports.apiKeyHelp")
            }
            slotProps={{
              input: { startAdornment: <ApiKeyIcon sx={{ mr: 1 }} /> },
            }}
            fullWidth
          />
        )}
        {provider === "codex" && (
          <Stack spacing={1.25}>
            {aiStatus?.connected ? (
              <Alert
                severity="success"
                action={
                  <Button
                    color="inherit"
                    size="small"
                    onClick={() =>
                      discordRequest("ai/logout", { method: "POST" })
                        .then(loadAiStatus)
                        .catch(captureError)
                    }
                  >
                    {t("settings.discordReports.codexLogout")}
                  </Button>
                }
              >
                {t("settings.discordReports.codexConnected", {
                  email: aiStatus.email || "ChatGPT",
                  plan: aiStatus.plan_type || "Codex",
                })}
              </Alert>
            ) : aiStatus?.state === "pending" ? (
              <Alert severity="info">
                {t("settings.discordReports.codexPending", {
                  code: aiStatus.user_code || "",
                })}
              </Alert>
            ) : (
              <Alert
                severity={aiStatus?.available === false ? "warning" : "info"}
                action={
                  <Button
                    color="inherit"
                    size="small"
                    startIcon={<LoginIcon />}
                    disabled={aiStatus?.available === false}
                    onClick={() =>
                      discordRequest("ai/login", { method: "POST" })
                        .then((next) => {
                          setAiStatus(next);
                          window.open(
                            next.verification_url,
                            "_blank",
                            "noopener,noreferrer"
                          );
                        })
                        .catch(captureError)
                    }
                  >
                    {t("settings.discordReports.codexLogin")}
                  </Button>
                }
              >
                {aiStatus?.available === false
                  ? t("settings.discordReports.codexUnavailable")
                  : t("settings.discordReports.codexDisconnected")}
              </Alert>
            )}
            {aiStatus?.state === "pending" && aiStatus.verification_url && (
              <Button
                variant="outlined"
                onClick={() =>
                  window.open(
                    aiStatus.verification_url,
                    "_blank",
                    "noopener,noreferrer"
                  )
                }
              >
                {t("settings.discordReports.codexOpenLogin", {
                  code: aiStatus.user_code,
                })}
              </Button>
            )}
          </Stack>
        )}
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gap: 2,
          }}
        >
          {["ai_model", "player_name_model"].map((key) => {
            const options =
              provider === "codex"
                ? aiStatus?.models || []
                : config.api_model_options || [];
            const selected =
              config.ai_config?.[key] ||
              (key === "ai_model" ? "gpt-5.6-luna" : "gpt-5.4-nano");
            const visibleOptions = options.some(
              (option) => option.id === selected
            )
              ? options
              : [{ id: selected, name: selected }, ...options];
            return (
              <TextField
                key={key}
                select
                label={t(`settings.discordReports.${key}`)}
                value={selected}
                onChange={(event) =>
                  setConfig({
                    ...config,
                    ai_config: {
                      ...(config.ai_config || {}),
                      [key]: event.target.value,
                    },
                  })
                }
                disabled={provider === "codex" && !aiStatus?.connected}
                helperText={t(`settings.discordReports.${key}Help`)}
                fullWidth
              >
                {visibleOptions.map((option) => (
                  <MenuItem key={option.id} value={option.id}>
                    {option.name || option.id}
                  </MenuItem>
                ))}
              </TextField>
            );
          })}
        </Box>
        <Stack direction="row" spacing={2} useFlexGap flexWrap="wrap">
          {[
            "chat_enabled",
            "names_enabled",
            "shadow_mode",
            "quality_opt_in",
          ].map((key) => (
            <FormControlLabel
              key={key}
              control={
                <Switch
                  checked={Boolean(config.ai_config?.[key])}
                  onChange={(event) =>
                    setConfig({
                      ...config,
                      ai_config: {
                        ...(config.ai_config || {}),
                        [key]: event.target.checked,
                      },
                    })
                  }
                />
              }
              label={t(`settings.discordReports.${key}`)}
            />
          ))}
        </Stack>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", lg: "repeat(3, minmax(0, 1fr))" },
            gap: 2,
          }}
        >
          <TextField
            multiline
            minRows={3}
            label={t("settings.discordReports.customTerms")}
            value={terms}
            onChange={(event) => setTerms(event.target.value)}
          />
          <TextField
            multiline
            minRows={3}
            label={t("settings.discordReports.exceptions")}
            value={exceptions}
            onChange={(event) => setExceptions(event.target.value)}
          />
          <TextField
            multiline
            minRows={3}
            label={t("settings.discordReports.regexes")}
            value={regexes}
            onChange={(event) => setRegexes(event.target.value)}
          />
        </Box>
        <Alert severity="info">{t("settings.discordReports.aiSafety")}</Alert>
      </Stack>
    );
  };

  const stepContent = [
    <Stack spacing={2.5} key="install">
      <SectionTitle
        icon={<DiscordBotIcon />}
        title={t("settings.discordReports.step_install")}
        help={t("settings.discordReports.installHint")}
      />
      {config?.connected ? (
        <Alert severity="success">
          {t("settings.discordReports.appInstalled")}
        </Alert>
      ) : (
        <Alert severity="info">
          {t("settings.discordReports.installPrivacy")}
        </Alert>
      )}
      <Button
        variant="contained"
        onClick={installDiscordApp}
        disabled={busyAction === "install"}
        sx={{ alignSelf: "flex-start" }}
      >
        {t("settings.discordReports.install")}
      </Button>
      {installError && (
        <Alert severity="error" data-testid="discord-install-error">
          <AlertTitle>{t("settings.discordReports.installFailed")}</AlertTitle>
          <Typography variant="body2">
            {t("settings.discordReports.installFailedHelp")}
          </Typography>
          <Typography variant="body2" sx={{ mt: 1, overflowWrap: "anywhere" }}>
            {installError}
          </Typography>
        </Alert>
      )}
    </Stack>,
    <Stack spacing={2.5} key="guild">
      <SectionTitle
        icon={<ConnectionIcon />}
        title={t("settings.discordReports.step_guild")}
        help={t("settings.discordReports.guildDetectedHelp")}
      />
      <TextField
        label={t("settings.discordReports.discordServer")}
        value={discordOptions.guild?.name || config?.guild_name || ""}
        placeholder={t("settings.discordReports.guildNotDetected")}
        slotProps={{ input: { readOnly: true } }}
        fullWidth
      />
      <Button
        variant="outlined"
        startIcon={<RefreshIcon />}
        onClick={detectServer}
        disabled={busyAction === "detect"}
        sx={{ alignSelf: "flex-start" }}
      >
        {t("settings.discordReports.detectServer")}
      </Button>
    </Stack>,
    renderChannelAndRoles(),
    renderActions(),
    renderAi(),
    <Stack spacing={2.5} key="test">
      <SectionTitle
        icon={<DiagnosticsIcon />}
        title={t("settings.discordReports.step_test")}
        help={t("settings.discordReports.testHelp")}
      />
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          gap: 1.5,
        }}
      >
        <StatusTile
          icon={<DiscordBotIcon fontSize="small" />}
          label={t("settings.discordReports.serviceStatus")}
          state={
            diagnostic?.service?.state ||
            (status?.service_configured ? "unknown" : "offline")
          }
          detail={
            diagnostic?.service?.latency_ms != null
              ? `${diagnostic.service.latency_ms} ms`
              : null
          }
          t={t}
        />
        <StatusTile
          icon={<ConnectionIcon fontSize="small" />}
          label={t("settings.discordReports.bindingStatus")}
          state={
            diagnostic?.discord_binding?.state ||
            (config?.connected ? "unknown" : "offline")
          }
          detail={
            diagnostic?.discord_binding?.guild_name
              ? `${diagnostic.discord_binding.guild_name} · #${
                  diagnostic.discord_binding.channel_name || "–"
                }`
              : null
          }
          t={t}
        />
        <StatusTile
          icon={<BrokerIcon fontSize="small" />}
          label={t("settings.discordReports.callbackStatus")}
          state={diagnostic?.callback?.state || "unknown"}
          detail={
            status?.callback_mode === "broker"
              ? t("settings.discordReports.brokerMode")
              : t("settings.discordReports.directMode")
          }
          t={t}
        />
        <StatusTile
          icon={<ReplyIcon fontSize="small" />}
          label={t("settings.discordReports.lastDelivery")}
          state={status?.delivery?.state || "unknown"}
          detail={
            formatTimestamp(
              status?.delivery?.last_delivered_at,
              i18n.resolvedLanguage
            ) ||
            (status?.delivery?.pending_count
              ? t("settings.discordReports.pendingDeliveries", {
                  count: status.delivery.pending_count,
                })
              : null)
          }
          t={t}
        />
        <StatusTile
          icon={<TestIcon fontSize="small" />}
          label={t("settings.discordReports.lastTest")}
          state={status?.last_test?.state || "unknown"}
          detail={formatTimestamp(
            status?.last_test?.checked_at,
            i18n.resolvedLanguage
          )}
          t={t}
        />
      </Box>
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <Button
          variant="contained"
          startIcon={<TestIcon />}
          onClick={sendTest}
          disabled={busyAction === "test"}
        >
          {t("settings.discordReports.test")}
        </Button>
        <Button
          variant="outlined"
          startIcon={<DiagnosticsIcon />}
          onClick={runDiagnostics}
          disabled={busyAction === "diagnostics"}
        >
          {t("settings.discordReports.runDiagnostics")}
        </Button>
        <Button
          variant="text"
          startIcon={<RefreshIcon />}
          onClick={repair}
          disabled={busyAction === "repair"}
        >
          {t("settings.discordReports.repair")}
        </Button>
      </Stack>
      <TechnicalDetails error={error} status={status} t={t} />
    </Stack>,
    <Stack spacing={2.5} key="activate">
      <SectionTitle
        icon={<HealthyIcon />}
        title={t("settings.discordReports.step_activate")}
        help={t("settings.discordReports.activateHelp")}
      />
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          gap: 1.5,
        }}
      >
        <StatusTile
          icon={<ConnectionIcon fontSize="small" />}
          label={t("settings.discordReports.discordServer")}
          state={config?.connected ? "online" : "offline"}
          detail={`${config?.guild_name || "–"} · ${
            config?.channel_name ? `#${config.channel_name}` : "–"
          }`}
          t={t}
        />
        <StatusTile
          icon={<PermissionsIcon fontSize="small" />}
          label={t("settings.discordReports.roles")}
          state={roles.length ? "healthy" : "degraded"}
          detail={
            roles
              .map(
                (id) =>
                  discordOptions.roles.find((role) => role.id === id)?.name ||
                  "–"
              )
              .join(", ") || "–"
          }
          t={t}
        />
        <StatusTile
          icon={<AiIcon fontSize="small" />}
          label={t("settings.discordReports.sectionAi")}
          state={
            config?.ai_config?.chat_enabled || config?.ai_config?.names_enabled
              ? "active"
              : "disabled"
          }
          detail={
            config?.ai_config?.provider === "codex"
              ? t("settings.discordReports.provider_codex")
              : t("settings.discordReports.provider_api_key")
          }
          t={t}
        />
        <StatusTile
          icon={<TestIcon fontSize="small" />}
          label={t("settings.discordReports.lastTest")}
          state={status?.last_test?.state || "unknown"}
          detail={formatTimestamp(
            status?.last_test?.checked_at,
            i18n.resolvedLanguage
          )}
          t={t}
        />
      </Box>
      <FormControlLabel
        control={
          <Switch
            checked={Boolean(config?.enabled)}
            onChange={(event) =>
              setConfig({ ...config, enabled: event.target.checked })
            }
          />
        }
        label={t("settings.discordReports.enabled")}
      />
      {status?.last_test?.state !== "succeeded" && (
        <Alert severity="warning">
          {t("settings.discordReports.activateWithoutTest")}
        </Alert>
      )}
      <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
        <Button
          variant="contained"
          onClick={() => save(config.enabled)}
          disabled={
            !roles.length ||
            !config.allowed_actions?.length ||
            busyAction === "save"
          }
        >
          {config.enabled
            ? t("settings.discordReports.saveAndActivate")
            : t("settings.discordReports.savePaused")}
        </Button>
        <Button
          color="error"
          onClick={disconnect}
          disabled={busyAction === "disconnect"}
        >
          {t("settings.discordReports.disconnect")}
        </Button>
      </Stack>
    </Stack>,
  ];

  return (
    <Card
      elevation={0}
      sx={{
        overflow: "hidden",
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 3,
      }}
    >
      <CardHeader
        avatar={
          <Box
            sx={{
              display: "grid",
              placeItems: "center",
              width: 48,
              height: 48,
              borderRadius: 2,
              bgcolor: "#5865F2",
              color: "white",
            }}
          >
            <DiscordBotIcon />
          </Box>
        }
        title={t("settings.discordReports.title")}
        subheader={serverLabel}
        action={
          config && (
            <Chip
              color={config.enabled && config.connected ? "success" : "default"}
              label={
                config.enabled && config.connected
                  ? t("settings.discordReports.statusActive")
                  : config.connected
                  ? t("settings.discordReports.statusPaused")
                  : t("settings.discordReports.statusDisconnected")
              }
            />
          )
        }
        sx={{
          alignItems: "flex-start",
          "& .MuiCardHeader-action": { mt: 0.5, mr: 0.5 },
        }}
      />
      <Divider />
      <CardContent sx={{ p: { xs: 2, md: 3 } }}>
        <Stack spacing={3}>
          {error && activeStep !== 5 && (
            <>
              <Alert severity="warning" icon={<WarningIcon />}>
                {t("settings.discordReports.actionFailed")}
              </Alert>
              <TechnicalDetails error={error} status={status} t={t} />
            </>
          )}
          <Box
            component="nav"
            aria-label={t("settings.discordReports.wizardProgress")}
          >
            {compact ? (
              <Stack spacing={1}>
                <Typography variant="caption" color="text.secondary">
                  {t("settings.discordReports.stepCount", {
                    current: activeStep + 1,
                    total: steps.length,
                  })}
                </Typography>
                <TextField
                  select
                  size="small"
                  label={t("settings.discordReports.currentStep")}
                  value={activeStep}
                  onChange={(event) =>
                    setActiveStep(Number(event.target.value))
                  }
                  fullWidth
                >
                  {steps.map((step, index) => (
                    <MenuItem
                      key={step}
                      value={index}
                      disabled={!canOpenStep(index)}
                    >
                      {index + 1}. {t(`settings.discordReports.step_${step}`)}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
            ) : (
              <Stepper activeStep={activeStep} nonLinear>
                {steps.map((step, index) => (
                  <Step
                    key={step}
                    completed={completed[index]}
                    disabled={!canOpenStep(index)}
                  >
                    <StepButton
                      onClick={() => canOpenStep(index) && setActiveStep(index)}
                    >
                      {t(`settings.discordReports.step_${step}`)}
                    </StepButton>
                  </Step>
                ))}
              </Stepper>
            )}
          </Box>
          <Box
            data-testid={`discord-wizard-step-${steps[activeStep]}`}
            sx={{
              p: { xs: 2, md: 3 },
              border: "1px solid",
              borderColor: "divider",
              borderRadius: 2.5,
              bgcolor: "background.paper",
            }}
          >
            {stepContent[activeStep]}
          </Box>
          <Stack direction="row" justifyContent="space-between" spacing={1}>
            <Button
              disabled={activeStep === 0}
              onClick={() =>
                setActiveStep((current) => Math.max(0, current - 1))
              }
            >
              {t("settings.discordReports.back")}
            </Button>
            {activeStep < steps.length - 1 && (
              <Button
                variant="outlined"
                disabled={!canContinue}
                onClick={() =>
                  setActiveStep((current) =>
                    Math.min(steps.length - 1, current + 1)
                  )
                }
              >
                {t("settings.discordReports.next")}
              </Button>
            )}
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
}
