import React, { useCallback, useEffect, useState } from "react";
import {
  Alert,
  Button,
  Card,
  CardContent,
  CardHeader,
  Chip,
  Divider,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
} from "@mui/material";
import { SmartToy as BotIcon } from "@mui/icons-material";
import { discordRequest } from "@/utils/fetchUtils";
import { toast } from "react-toastify";
import { useTranslation } from "react-i18next";

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

export default function DiscordReportBotCard() {
  const { t } = useTranslation();
  const [config, setConfig] = useState(null);
  const [error, setError] = useState("");
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
  const [usage, setUsage] = useState(null);
  const [editingConnection, setEditingConnection] = useState(false);

  const apply = useCallback((next) => {
    setConfig(next);
    setChannelId(next.channel_id || "");
    setRoles(next.moderator_role_ids || []);
    setTerms((next.policy?.custom_terms || []).join("\n"));
    setExceptions((next.policy?.exceptions || []).join("\n"));
    setRegexes((next.policy?.custom_regexes || []).join("\n"));
    setError("");
  }, []);

  const loadDiscordOptions = useCallback(async () => {
    const options = await discordRequest("options");
    setDiscordOptions({
      guild: options.guild || null,
      channels: options.channels || [],
      roles: options.roles || [],
    });
    setError("");
    return options;
  }, []);

  useEffect(() => {
    discordRequest("integration")
      .then((next) => {
        apply(next);
        if (next.connected) {
          discordRequest("usage").then(setUsage).catch(() => setUsage(null));
        }
        loadDiscordOptions().catch((requestError) =>
          setError(requestError.message)
        );
      })
      .catch((requestError) => setError(requestError.message));
  }, [apply, loadDiscordOptions]);

  const connect = async () => {
    try {
      apply(
        await discordRequest("connect", {
          method: "POST",
          payload: {
            channel_id: channelId,
            channel_name:
              discordOptions.channels.find((item) => item.id === channelId)
                ?.name || "",
            moderator_role_ids: roles,
          },
        })
      );
      await loadDiscordOptions();
      setEditingConnection(false);
      toast.success(t("settings.discordReports.connected"));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  const cancelConnectionEdit = () => {
    setChannelId(config.channel_id || "");
    setRoles(config.moderator_role_ids || []);
    setEditingConnection(false);
    setError("");
  };

  const save = async () => {
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
      apply(
        await discordRequest("integration", {
          method: "PUT",
          payload: {
            enabled: config.enabled,
            moderator_role_ids: roles,
            allowed_actions: config.allowed_actions || [],
            language: config.language,
            ai_config: config.ai_config || {},
            policy,
            reporter_templates: config.reporter_templates || {},
          },
        })
      );
      toast.success(t("settings.discordReports.saved"));
    } catch (requestError) {
      setError(requestError.message);
    }
  };

  if (!config && !error) return null;
  return (
    <Card elevation={2}>
      <CardHeader
        avatar={<BotIcon color="primary" />}
        title={t("settings.discordReports.title")}
        subheader={t("settings.discordReports.subtitle")}
        action={
          config && (
            <Chip
              color={config.connected ? "success" : "default"}
              label={
                config.connected
                  ? t("settings.discordReports.statusConnected")
                  : t("settings.discordReports.statusDisconnected")
              }
            />
          )
        }
      />
      <Divider />
      <CardContent>
        <Stack spacing={2}>
          {error && <Alert severity="warning">{error}</Alert>}
          {config && !config.connected && (
            <>
              <Alert severity="info">
                {t("settings.discordReports.installHint")}
              </Alert>
              <Stack spacing={2}>
                <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                  <Button
                    variant="outlined"
                    onClick={() =>
                      window.open(
                        `${config.service_url.replace(/\/$/, "")}/oauth/install`,
                        "_blank",
                        "noopener,noreferrer"
                      )
                    }
                  >
                    {t("settings.discordReports.install")}
                  </Button>
                  <Button variant="outlined" onClick={loadDiscordOptions}>
                    {t("settings.discordReports.detectServer")}
                  </Button>
                  <TextField
                    label={t("settings.discordReports.discordServer")}
                    value={discordOptions.guild?.name || ""}
                    helperText={t("settings.discordReports.guildDetectedHelp")}
                    InputProps={{ readOnly: true }}
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
                  <Button
                    variant="contained"
                    disabled={!discordOptions.guild || !channelId}
                    onClick={connect}
                  >
                    {t("settings.discordReports.connect")}
                  </Button>
                </Stack>
                <TextField
                  select
                  label={t("settings.discordReports.roles")}
                  value={roles}
                  onChange={(event) => {
                    const value = event.target.value;
                    setRoles(
                      typeof value === "string" ? value.split(",") : value
                    );
                  }}
                  helperText={t("settings.discordReports.rolesHelp")}
                  SelectProps={{
                    multiple: true,
                    renderValue: (selected) =>
                      selected
                        .map(
                          (id) =>
                            discordOptions.roles.find((role) => role.id === id)
                              ?.name || id
                        )
                        .join(", "),
                  }}
                >
                  {discordOptions.roles.map((role) => (
                    <MenuItem key={role.id} value={role.id}>
                      {role.name}
                    </MenuItem>
                  ))}
                </TextField>
              </Stack>
            </>
          )}
          {config?.connected && (
            <>
              {usage && (
                <Alert severity="info">
                  {t("settings.discordReports.usage", {
                    used: usage.used_tokens.toLocaleString(),
                    quota: usage.quota_tokens
                      ? usage.quota_tokens.toLocaleString()
                      : t("settings.discordReports.unlimited"),
                  })}
                </Alert>
              )}
              {!editingConnection ? (
                <Stack spacing={2}>
                  <Alert severity="success">
                    {t("settings.discordReports.connectedTo", {
                      guild: config.guild_name || config.guild_id,
                      channel: config.channel_name
                        ? `#${config.channel_name}`
                        : config.channel_id,
                    })}
                  </Alert>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <TextField
                      label={t("settings.discordReports.discordServer")}
                      value={config.guild_name || config.guild_id || ""}
                      InputProps={{ readOnly: true }}
                      fullWidth
                    />
                    <TextField
                      label={t("settings.discordReports.reportChannel")}
                      value={
                        config.channel_name
                          ? `#${config.channel_name}`
                          : config.channel_id || ""
                      }
                      InputProps={{ readOnly: true }}
                      fullWidth
                    />
                    <Button
                      variant="outlined"
                      onClick={() => setEditingConnection(true)}
                    >
                      {t("settings.discordReports.changeConnection")}
                    </Button>
                  </Stack>
                </Stack>
              ) : (
                <Stack spacing={2}>
                  <Alert severity="warning">
                    {t("settings.discordReports.changeConnectionHint")}
                  </Alert>
                  <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                    <Button
                      variant="outlined"
                      onClick={() =>
                        window.open(
                          `${config.service_url.replace(/\/$/, "")}/oauth/install`,
                          "_blank",
                          "noopener,noreferrer"
                        )
                      }
                    >
                      {t("settings.discordReports.install")}
                    </Button>
                    <TextField
                      label={t("settings.discordReports.discordServer")}
                      value={
                        discordOptions.guild?.name ||
                        config.guild_name ||
                        config.guild_id ||
                        ""
                      }
                      helperText={t("settings.discordReports.guildDetectedHelp")}
                      InputProps={{ readOnly: true }}
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
                  <Stack direction="row" spacing={1}>
                    <Button
                      variant="contained"
                      disabled={!discordOptions.guild || !channelId}
                      onClick={connect}
                    >
                      {t("settings.discordReports.saveConnection")}
                    </Button>
                    <Button onClick={cancelConnectionEdit}>
                      {t("settings.discordReports.cancel")}
                    </Button>
                  </Stack>
                </Stack>
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
                SelectProps={{
                  multiple: true,
                  renderValue: (selected) =>
                    selected
                      .map(
                        (id) =>
                          discordOptions.roles.find((role) => role.id === id)
                            ?.name || id
                      )
                      .join(", "),
                }}
              >
                {discordOptions.roles.map((role) => (
                  <MenuItem key={role.id} value={role.id}>
                    {role.name}
                  </MenuItem>
                ))}
              </TextField>
              <TextField
                select
                label={t("settings.discordReports.language")}
                value={config.language || "de"}
                onChange={(event) =>
                  setConfig({ ...config, language: event.target.value })
                }
              >
                <MenuItem value="de">Deutsch</MenuItem>
                <MenuItem value="en">English</MenuItem>
              </TextField>
              <Stack direction="row" spacing={2} useFlexGap flexWrap="wrap">
                <FormControlLabel
                  control={
                    <Switch
                      checked={config.enabled}
                      onChange={(event) =>
                        setConfig({ ...config, enabled: event.target.checked })
                      }
                    />
                  }
                  label={t("settings.discordReports.enabled")}
                />
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
              <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap">
                {ACTIONS.map((action) => {
                  const active = (config.allowed_actions || []).includes(
                    action
                  );
                  return (
                    <Chip
                      key={action}
                      clickable
                      color={active ? "primary" : "default"}
                      label={action}
                      onClick={() =>
                        setConfig({
                          ...config,
                          allowed_actions: active
                            ? config.allowed_actions.filter(
                                (item) => item !== action
                              )
                            : [...(config.allowed_actions || []), action],
                        })
                      }
                    />
                  );
                })}
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                <TextField
                  multiline
                  minRows={3}
                  label={t("settings.discordReports.customTerms")}
                  value={terms}
                  onChange={(event) => setTerms(event.target.value)}
                  fullWidth
                />
                <TextField
                  multiline
                  minRows={3}
                  label={t("settings.discordReports.exceptions")}
                  value={exceptions}
                  onChange={(event) => setExceptions(event.target.value)}
                  fullWidth
                />
                <TextField
                  multiline
                  minRows={3}
                  label={t("settings.discordReports.regexes")}
                  value={regexes}
                  onChange={(event) => setRegexes(event.target.value)}
                  fullWidth
                />
              </Stack>
              <Stack direction={{ xs: "column", md: "row" }} spacing={2}>
                {["received", "claimed", "resolved", "dismissed"].map(
                  (templateKey) => (
                    <TextField
                      key={templateKey}
                      label={t(
                        `settings.discordReports.template_${templateKey}`
                      )}
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
                  )
                )}
              </Stack>
              <Alert severity="info">
                {t("settings.discordReports.aiSafety")}
              </Alert>
              <Stack direction="row" spacing={1}>
                <Button variant="contained" onClick={save}>
                  {t("settings.discordReports.save")}
                </Button>
                <Button
                  variant="outlined"
                  onClick={() =>
                    discordRequest("test-message", { method: "POST" })
                      .then(() =>
                        toast.success(t("settings.discordReports.testSent"))
                      )
                      .catch((requestError) => setError(requestError.message))
                  }
                >
                  {t("settings.discordReports.test")}
                </Button>
                <Button
                  color="error"
                  onClick={() =>
                    discordRequest("integration", { method: "DELETE" })
                      .then(apply)
                      .catch((requestError) => setError(requestError.message))
                  }
                >
                  {t("settings.discordReports.disconnect")}
                </Button>
              </Stack>
            </>
          )}
        </Stack>
      </CardContent>
    </Card>
  );
}
