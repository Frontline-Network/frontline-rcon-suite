import {
  Form,
  json,
  useActionData,
  useLoaderData,
  useRevalidator,
  useSubmit,
} from "react-router-dom";
import { lazy, Suspense, useCallback, useEffect, useState } from "react";
import { execute, get, handleHttpError } from "@/utils/fetchUtils";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SettingsIcon from "@mui/icons-material/Settings";
import { a11yDark, a11yLight, CopyBlock } from "react-code-blocks";
import { toast } from "react-toastify";
import { red } from "@mui/material/colors";
import { JsonForms } from "@jsonforms/react";
import {
  materialCells,
  materialRenderers,
} from "@jsonforms/material-renderers";
import { Generate } from "@jsonforms/core";
import ButtonGroup from "@mui/material/ButtonGroup";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { customRenderers } from "@/pages/settings/[configs]/renderer/renderer";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";
import i18n from "@/i18n";
import AutobalancerHelp from "@/pages/settings/[configs]/autobalancer-help";
import AutobalancerShadowOverview from "@/pages/settings/[configs]/autobalancer-shadow-overview";
import SystemDiagnosticsLayout from "../system-diagnostics/SystemDiagnosticsLayout";

const Editor = lazy(() => import("@monaco-editor/react"));

const systemDiagnosticsCommands = new Set([
  "rcon_connection_settings_config",
  "rcon_server_settings_config",
  "steam_config",
  "log_stream_config",
  "watch_killrate_config",
]);

const diagnosticColor = {
  valid: "success",
  invalid: "error",
  unreachable: "warning",
  unverified: "default",
};

const ChatWebhookDiagnostics = () => {
  const { t } = useTranslation();
  const [diagnostics, setDiagnostics] = useState([]);
  const [loading, setLoading] = useState(false);

  const load = useCallback(async () => {
    try {
      const response = await get("get_chat_webhook_diagnostics");
      const payload = await response.json();
      setDiagnostics(payload?.result || []);
    } catch (error) {
      handleHttpError(error);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const run = async (command, successMessage) => {
    setLoading(true);
    try {
      const response = await execute(command);
      const payload = await response.json();
      if (payload?.failed) throw new Error(payload.error);
      setDiagnostics(payload?.result || []);
      toast.success(t(successMessage));
    } catch (error) {
      handleHttpError(error);
    } finally {
      setLoading(false);
    }
  };

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack spacing={1.5}>
          <Box>
            <Typography variant="h6">
              {t("settings.config.webhookDiagnostics.title")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {t("settings.config.webhookDiagnostics.help")}
            </Typography>
          </Box>
          {diagnostics.length === 0 ? (
            <Typography variant="body2" color="text.secondary">
              {t("settings.config.webhookDiagnostics.empty")}
            </Typography>
          ) : (
            diagnostics.map((diagnostic) => (
              <Stack
                direction="row"
                spacing={1}
                alignItems="center"
                key={diagnostic.index}
              >
                <Typography variant="body2" sx={{ minWidth: 100 }}>
                  {t("settings.config.webhookDiagnostics.webhook", {
                    number: diagnostic.index + 1,
                  })}
                </Typography>
                <Chip
                  size="small"
                  color={diagnosticColor[diagnostic.status] || "default"}
                  label={t(
                    `settings.config.webhookDiagnostics.status_${
                      diagnostic.status || "unverified"
                    }`
                  )}
                />
                {diagnostic.last_error && (
                  <Typography variant="body2" color="text.secondary">
                    {diagnostic.last_error}
                  </Typography>
                )}
              </Stack>
            ))
          )}
          <Stack direction="row" spacing={1} flexWrap="wrap">
            <Button
              variant="outlined"
              disabled={loading}
              onClick={() =>
                run(
                  "diagnose_chat_webhooks",
                  "settings.config.webhookDiagnostics.checked"
                )
              }
            >
              {t("settings.config.webhookDiagnostics.check")}
            </Button>
            <Button
              variant="contained"
              disabled={loading || diagnostics.length === 0}
              onClick={() =>
                run(
                  "test_chat_webhooks",
                  "settings.config.webhookDiagnostics.testSent"
                )
              }
            >
              {t("settings.config.webhookDiagnostics.test")}
            </Button>
          </Stack>
        </Stack>
      </CardContent>
    </Card>
  );
};

export const loader = async ({ params }) => {
  const { category, type } = params;
  let note, data, details, configTypes, schema;

  // Dynamically load JSON based on route parameters
  try {
    const configMappingModule = await import("../_data/mappings");

    if (!configMappingModule[category]) throw new Error();

    configTypes = configMappingModule[category];

    details = configTypes.find(
      (configType) => type === configType.path.split("/").slice(-1)[0]
    );

    if (!details) throw new Error();
  } catch (error) {
    throw json(
      {
        message: i18n.t("errors.configUnknown"),
        error: error?.message,
        command: error?.command,
      },
      { status: 404 }
    );
  }

  try {
    note = await import(`../_data/${category}/${type}.js`);
  } catch (error) {
    throw json(
      {
        message: i18n.t("errors.configDocumentationUnavailable"),
        error: error?.message,
        command: error?.command,
      },
      { status: 404 }
    );
  }

  if (isFakeMode()) {
    if (details.command === "autobalancer_config") {
      const { autobalancerConfig, autobalancerSchema } = await import(
        "@/mirage/data/autobalancer"
      );
      return {
        note: note.default,
        data: autobalancerConfig,
        schema: autobalancerSchema,
        ...details,
      };
    }
    return {
      note: note.default,
      data: {
        enabled: true,
        discord_webhook_url: "https://discord.example/frontline",
      },
      schema: {
        type: "object",
        properties: {
          enabled: { type: "boolean", title: "Aktiviert" },
          discord_webhook_url: { type: "string", title: "Discord-Webhook-URL" },
        },
      },
      ...details,
    };
  }

  let response;
  try {
    response = await get(`get_${details.command}`);
  } catch (error) {
    handleHttpError(error);
  }

  data = await response.json();
  if (!data || data.failed)
    throw new Response(i18n.t("errors.configLoadFailed"), { status: 400 });

  try {
    response = await get(`describe_${details.command}`);
    schema = await response.json();
    if (!schema || schema.failed) throw new Error();
  } catch (error) {
    throw new Response(i18n.t("errors.configSchemaFailed"), { status: 400 });
  }

  return {
    note: note.default, // .default is needed because dynamic imports return an ES module object
    data: data.result,
    schema: schema.result,
    ...details,
  };
};

export const action = async ({ request }) => {
  let formData = await request.formData();
  let name = formData.get("name");
  let config = formData.get("config");
  let error = null;
  let response;

  if (!(name && config))
    return { ok: false, error: i18n.t("errors.missingParameters") };

  config = JSON.parse(config);

  try {
    response = await execute(`validate_${name}`, {
      errors_as_json: true,
      ...config,
    });
  } catch (error) {
    handleHttpError(error);
  }

  const data = await response.json();

  if (!data || data.failed) {
    throw json(
      {
        message: i18n.t("errors.configValidationFailed"),
        error: data?.error,
        command: data?.command,
      },
      { status: 400 }
    );
  }

  error = data.error;

  if (error) {
    return { ok: false, error };
  }

  response = await execute(`set_${name}`, config);

  return { ok: true };
};

const ConfigPage = () => {
  const { t } = useTranslation();
  const { note, command, name, nameKey, data, schema } = useLoaderData();
  const displayName = nameKey ? t(nameKey) : name;
  const [validationErrors, setValidationErrors] = useState(null);
  const [jsonData, setJsonData] = useState(data);
  const [editorContent, setEditorContent] = useState("");
  const [mode, setMode] = useState("visual");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const revalidator = useRevalidator();
  const actionData = useActionData();
  const submit = useSubmit();
  const theme = useTheme();
  const isAutobalancer = command === "autobalancer_config";
  const isChatWebhookConfig = command === "chat_discord_webhooks_config";
  const isSystemDiagnostics = systemDiagnosticsCommands.has(command);

  useEffect(() => {
    setEditorContent(JSON.stringify(data, null, 2));
    setJsonData(data);
  }, [data]);

  useEffect(() => {
    if (actionData && actionData.ok === false) {
      setValidationErrors(actionData.error);
      toast.error(t("settings.config.saveFailed", { name: displayName }));
    } else if (actionData && actionData.ok) {
      setValidationErrors(null);
      toast.success(t("settings.config.saved", { name: displayName }));
    }
  }, [actionData, displayName, t]);

  useEffect(() => {
    setValidationErrors(null);
  }, [command]);

  const handleSubmit = (e) => {
    const formData = new FormData();
    formData.append("config", editorContent);
    formData.append("name", command);
    submit(formData, { method: "post" });
    e.preventDefault();
  };

  const handleRefresh = () => {
    revalidator.revalidate();
    setValidationErrors(null);
  };

  function updateMode(mode) {
    if (mode === "visual") {
      try {
        setJsonData(JSON.parse(editorContent));
      } catch (e) {
        setValidationErrors(t("settings.config.invalidJson", { error: e }));
      }
    } else if (jsonData) {
      setEditorContent(JSON.stringify(jsonData, null, 2));
    }
    setMode(mode);
  }

  const handleOpenAutobalancerSettings = () => {
    setSettingsOpen(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("autobalancer-settings")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const content = (
    <Stack
      direction={"column"}
      spacing={isSystemDiagnostics ? 2 : 4}
      sx={
        isSystemDiagnostics
          ? {
              p: { xs: 1.5, md: 2 },
              "& .MuiButton-root, & .MuiButtonGroup-root, & .MuiPaper-root, & .MuiOutlinedInput-root":
                { borderRadius: 0 },
              "& form": {
                p: { xs: 1.25, md: 2 },
                border: "1px solid",
                borderColor: "divider",
                bgcolor: "background.default",
              },
            }
          : undefined
      }
    >
      {isAutobalancer && (
        <AutobalancerShadowOverview
          config={jsonData}
          onOpenSettings={handleOpenAutobalancerSettings}
        />
      )}
      {isChatWebhookConfig && <ChatWebhookDiagnostics />}
      {isAutobalancer && (
        <Button
          id="autobalancer-settings"
          fullWidth
          size="large"
          variant="outlined"
          startIcon={<SettingsIcon />}
          endIcon={<ExpandMoreIcon />}
          onClick={() => setSettingsOpen((open) => !open)}
          sx={{
            justifyContent: "flex-start",
            py: 1.5,
            "& .MuiButton-endIcon": {
              ml: "auto",
              transform: settingsOpen ? "rotate(180deg)" : "rotate(0deg)",
              transition: "transform 160ms ease",
            },
          }}
        >
          {settingsOpen
            ? t("settings.config.closeAutobalancerSettings")
            : t("settings.config.openAutobalancerSettings", {
                mode: jsonData?.mode || t("common.unknown"),
              })}
        </Button>
      )}
      <Collapse
        in={!isAutobalancer || settingsOpen}
        timeout="auto"
        unmountOnExit={isAutobalancer}
      >
        <Stack spacing={4}>
          <Form method="post" onSubmit={handleSubmit}>
            <Stack direction={"row"} justifyContent={"space-between"}>
              <Typography variant="h3">{displayName}</Typography>
              <ButtonGroup variant="outlined">
                <Button
                  variant={mode === "visual" ? "contained" : "outlined"}
                  onClick={() => updateMode("visual")}
                >
                  {isAutobalancer
                    ? t("settings.config.basicMode")
                    : t("settings.config.visual")}
                </Button>
                <Button
                  variant={mode === "code" ? "contained" : "outlined"}
                  onClick={() => updateMode("code")}
                >
                  {isAutobalancer
                    ? t("settings.config.advancedJsonMode")
                    : isSystemDiagnostics
                    ? t("settings.config.advancedJsonMode")
                    : t("settings.config.code")}
                </Button>
              </ButtonGroup>
            </Stack>
            <Stack spacing={2} direction={"column"}>
              {validationErrors && (
                <Box sx={{ mb: 2 }}>
                  <CopyBlock
                    wrapLongLines
                    text={JSON.stringify(validationErrors, null, 2)}
                    language="json"
                    theme={theme.palette.mode === "dark" ? a11yDark : a11yLight}
                    customStyle={{ border: `2px solid ${red["600"]}` }}
                  />
                </Box>
              )}
              {isAutobalancer && <AutobalancerHelp config={jsonData} />}
              {mode === "visual" ? (
                <Box
                  sx={{
                    "& .MuiFormControl-root": {
                      marginTop: "14px",
                    },
                  }}
                >
                  <JsonForms
                    data={jsonData}
                    onChange={({ data }) => {
                      setEditorContent(JSON.stringify(data, null, 2));
                      setJsonData(data);
                    }}
                    sx={{
                      "& .jfa-label": {
                        fontSize: "14px",
                      },
                    }}
                    schema={schema}
                    uischema={Generate.uiSchema(schema)}
                    renderers={[...customRenderers, ...materialRenderers]}
                    cells={materialCells}
                  />
                </Box>
              ) : (
                <Suspense>
                  <Editor
                    height="70vh"
                    defaultLanguage="json"
                    value={editorContent}
                    defaultValue=""
                    theme={
                      theme.palette.mode === "dark" ? "vs-dark" : "vs-light"
                    }
                    onChange={(value) => setEditorContent(value)}
                  />
                </Suspense>
              )}
              <Stack direction={"row"} spacing={1}>
                <Button variant={"outlined"} onClick={handleRefresh}>
                  {isAutobalancer || isSystemDiagnostics
                    ? t("settings.config.reload")
                    : t("common.refresh")}
                </Button>
                <Button variant={"contained"} type="submit">
                  {isAutobalancer || isSystemDiagnostics
                    ? t("settings.config.saveSettings")
                    : t("settings.config.submit")}
                </Button>
              </Stack>
            </Stack>
          </Form>
          {mode === "code" ? (
            <>
              <Typography variant="h4">
                {isAutobalancer
                  ? t("settings.config.explanation")
                  : t("settings.config.documentation")}
              </Typography>
              <CopyBlock
                wrapLongLines
                text={note}
                language="json"
                wrapLines
                theme={theme.palette.mode === "dark" ? a11yDark : a11yLight}
              />
              <Typography variant="h4">
                {isAutobalancer
                  ? t("settings.config.technicalSchema")
                  : t("settings.config.modelSchema")}
              </Typography>
              <CopyBlock
                wrapLongLines
                text={JSON.stringify(schema, null, 2)}
                language="json"
                wrapLines
                theme={theme.palette.mode === "dark" ? a11yDark : a11yLight}
              />
            </>
          ) : (
            <></>
          )}
        </Stack>
      </Collapse>
    </Stack>
  );

  return isSystemDiagnostics ? (
    <SystemDiagnosticsLayout>{content}</SystemDiagnosticsLayout>
  ) : (
    content
  );
};

export default ConfigPage;
