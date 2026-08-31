import {
  Form,
  json,
  useActionData,
  useLoaderData,
  useNavigation,
  useRevalidator,
  useSubmit,
} from "react-router-dom";
import { lazy, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { execute, get, handleHttpError } from "@/utils/fetchUtils";
import {
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Collapse,
  Alert,
  Stack,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import SettingsIcon from "@mui/icons-material/Settings";
import RestartAltIcon from "@mui/icons-material/RestartAlt";
import SaveOutlinedIcon from "@mui/icons-material/SaveOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import ScienceOutlinedIcon from "@mui/icons-material/ScienceOutlined";
import { toast } from "react-toastify";
import { JsonForms } from "@jsonforms/react";
import {
  materialCells,
  materialRenderers,
} from "@jsonforms/material-renderers";
import { Generate } from "@jsonforms/core";
import { createTheme, ThemeProvider } from "@mui/material/styles";
import { customRenderers } from "@/pages/settings/[configs]/renderer/renderer";
import { isFakeMode } from "@/mirage/demo-data";
import { useTranslation } from "react-i18next";
import i18n from "@/i18n";
import AutobalancerHelp from "@/pages/settings/[configs]/autobalancer-help";
import AutobalancerShadowOverview from "@/pages/settings/[configs]/autobalancer-shadow-overview";
import SystemDiagnosticsLayout from "../system-diagnostics/SystemDiagnosticsLayout";
import { useAuth } from "@/hooks/useAuth";
import {
  ConfigActionBar,
  ConfigFormLayout,
  ConfigProfileSummaryPanel,
  ConfigValidationSummary,
  GuidedConfigForm,
  NameKickSummaryPanel,
  NoLeaderOperationModeControl,
  NoLeaderSummaryPanel,
  SchemaConfigForm,
  SeedVipConfigForm,
  SeedingConfigForm,
  SeedingOperationModeControl,
  SeedingSummaryPanel,
  SeedingWorkbenchLayout,
  validateProfiledConfig,
} from "@/pages/settings/config-form";
import {
  inspectConfigCompatibility,
  mergeConfigWithSchema,
} from "@/pages/settings/config-form/configCompatibility.mjs";
import { getConfigFormProfile } from "@/pages/settings/config-form/schema";
import IntegrationsHub from "@/pages/settings/integrations/IntegrationsHub";
import IntegrationConfigEditor from "@/pages/settings/integrations/IntegrationConfigEditor";
import {
  getIntegrationByCommand,
  getIntegrationBySlug,
} from "@/pages/settings/integrations/registry";

const LevelRuleTestDrawer = lazy(() =>
  import("@/pages/settings/config-form/LevelRuleTestDrawer")
);
const EscalationRuleTestDrawer = lazy(() =>
  import("@/pages/settings/config-form/EscalationRuleTestDrawer")
);

// Fake-preview saves stay process-local so repeated form interactions are
// deterministic without changing the production request path.
const fakeConfigOverrides = new Map();

const systemDiagnosticsCommands = new Set([
  "rcon_connection_settings_config",
  "rcon_server_settings_config",
  "steam_config",
  "log_stream_config",
  "watch_killrate_config",
]);

const guidedRendererSections = new Set([
  "operation",
  "detection",
  "exemptions",
  "actions",
  "notifications",
]);
const seedingRendererSections = new Set([
  "operation",
  "rules",
  "exemptions",
  "actions",
  "notifications",
]);
const seedVipRendererSections = new Set([
  "operation",
  "requirements",
  "reward",
  "messages",
  "notifications",
]);

const diagnosticColor = {
  valid: "success",
  invalid: "error",
  unreachable: "warning",
  unverified: "default",
};

const ChatWebhookDiagnostics = ({ canChange }) => {
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
              disabled={loading || !canChange}
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
              disabled={loading || !canChange || diagnostics.length === 0}
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

const ConfigCompatibilityAlert = ({ issues }) => {
  const { t } = useTranslation();
  if (!issues.length) return null;

  return (
    <Alert severity="warning" data-testid="config-compatibility-warning">
      <Typography variant="body2" fontWeight={800}>
        {t("settings.configForms.workbench.compatibilityTitle")}
      </Typography>
      <Typography variant="body2" sx={{ mb: 1 }}>
        {t("settings.configForms.workbench.compatibilityDescription")}
      </Typography>
      <Stack component="ul" spacing={0.35} sx={{ m: 0, pl: 2.5 }}>
        {issues.map((issue) => (
          <Typography component="li" variant="caption" key={issue.path}>
            {t("settings.configForms.workbench.compatibilityIssue", {
              path: issue.path,
              expected: t(
                `settings.configForms.workbench.types.${issue.expectedType}`,
                { defaultValue: issue.expectedType }
              ),
              actual: t(
                `settings.configForms.workbench.types.${issue.actualType}`,
                { defaultValue: issue.actualType }
              ),
            })}
          </Typography>
        ))}
      </Stack>
    </Alert>
  );
};

export const loader = async ({ params }) => {
  let { category, type } = params;
  let note, data, details, configTypes, schema;

  try {
    if (params.section !== undefined || (!params.category && !params.type)) {
      details = getIntegrationBySlug(params.section || "audit");
      if (!details) throw new Error();
      category = details.category;
      type = details.type;
    } else {
      const configMappingModule = await import("../_data/mappings");

      if (!configMappingModule[category]) throw new Error();

      configTypes = configMappingModule[category];
      details = configTypes.find(
        (configType) => type === configType.path.split("/").slice(-1)[0]
      );

      if (!details) throw new Error();
      const integration = getIntegrationByCommand(details.command);
      if (integration) details = { ...details, ...integration };
    }
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
    if (details.command === "auto_mod_no_leader_config") {
      const { noLeaderConfig, noLeaderSchema } = await import(
        "@/mirage/data/noLeaderConfig"
      );
      return {
        note: note.default,
        data: fakeConfigOverrides.get(details.command) || noLeaderConfig,
        schema: noLeaderSchema,
        ...details,
      };
    }
    const { getConfigFormExample } = await import(
      "@/mirage/data/configFormExamples"
    );
    const example = getConfigFormExample(details.command);
    if (example) {
      return {
        note: note.default,
        data: fakeConfigOverrides.get(details.command) || example.data,
        schema: example.schema,
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

  try {
    config = JSON.parse(config);
  } catch (parseError) {
    return {
      ok: false,
      error: {
        _root: i18n.t("settings.config.invalidJson", {
          error: parseError.message,
        }),
      },
    };
  }

  if (isFakeMode()) {
    fakeConfigOverrides.set(name, config);
    return { ok: true };
  }

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

  try {
    response = await execute(`set_${name}`, config);
  } catch (error) {
    handleHttpError(error);
  }

  const rawSaved = await response.text();
  let saved = { result: true };
  if (rawSaved) {
    try {
      saved = JSON.parse(rawSaved);
    } catch (parseError) {
      throw json(
        {
          message: i18n.t("errors.configSaveFailed"),
          error: parseError.message,
        },
        { status: 502 }
      );
    }
  }

  if (!response.ok || !saved || saved.failed) {
    throw json(
      {
        message: i18n.t("errors.configSaveFailed"),
        error: saved?.error,
        command: saved?.command,
      },
      { status: 400 }
    );
  }

  return { ok: true };
};

const normalizeValidationErrors = (errors, profile, t) => {
  if (!errors) return [];
  if (Array.isArray(errors)) {
    return errors.flatMap((error, index) =>
      typeof error === "string"
        ? [{ id: `server-${index}`, message: error }]
        : [error]
    );
  }
  if (typeof errors === "string") {
    return [{ id: "server-root", message: errors }];
  }

  const sectionByField = new Map(
    (profile?.sections || []).flatMap((section) =>
      section.fields.map((fieldName) => [fieldName, section.id])
    )
  );

  return Object.entries(errors).flatMap(([fieldName, message]) => {
    const messages = Array.isArray(message) ? message : [message];
    const metadata = profile?.fields?.[fieldName];
    return messages.map((entry, index) => ({
      id: `${fieldName}-${index}`,
      label:
        fieldName === "_root"
          ? undefined
          : metadata?.labelKey
          ? t(metadata.labelKey)
          : fieldName,
      message:
        typeof entry === "string" ? entry : JSON.stringify(entry, null, 2),
      sectionId: sectionByField.get(fieldName),
    }));
  });
};

const ConfigPage = () => {
  const { t } = useTranslation();
  const {
    command,
    name,
    nameKey,
    data,
    schema,
    slug: integrationSlug,
    changePermission: explicitChangePermission,
  } = useLoaderData();
  const displayName = nameKey ? t(nameKey) : name;
  const [validationErrors, setValidationErrors] = useState(null);
  const [jsonData, setJsonData] = useState(data);
  const [editorContent, setEditorContent] = useState("");
  const [activeSection, setActiveSection] = useState("operation");
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [testOpen, setTestOpen] = useState(false);
  const revalidator = useRevalidator();
  const actionData = useActionData();
  const submit = useSubmit();
  const navigation = useNavigation();
  const { permissions } = useAuth();
  const isAutobalancer = command === "autobalancer_config";
  const isChatWebhookConfig = command === "chat_discord_webhooks_config";
  const isSystemDiagnostics = systemDiagnosticsCommands.has(command);
  const isIntegrationHub = Boolean(integrationSlug);
  const formProfile = useMemo(
    () => getConfigFormProfile(command, schema),
    [command, schema]
  );
  const hasGuidedProfile = Boolean(formProfile?.sections?.length);
  const usesGuidedRenderer = formProfile?.renderer === "guided";
  const usesSeedingRenderer = formProfile?.renderer === "seeding";
  const usesSeedVipRenderer = formProfile?.renderer === "seedVip";
  const usesNameKickRenderer = formProfile?.renderer === "nameKick";
  const usesSchemaWorkbench = formProfile?.layout === "workbench";
  const testKind = formProfile?.testKind || null;
  const supportsImpactTest = ["level", "noLeader", "noSoloTank"].includes(
    testKind
  );
  const WorkbenchLayout =
    usesSeedingRenderer ||
    usesSeedVipRenderer ||
    usesGuidedRenderer ||
    usesNameKickRenderer ||
    usesSchemaWorkbench
      ? SeedingWorkbenchLayout
      : ConfigFormLayout;
  const changePermission = explicitChangePermission || `can_change_${command}`;
  const canChange = Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some(
        (item) => item.permission === changePermission
      )
  );
  const savedEditorContent = useMemo(
    () => JSON.stringify(data, null, 2),
    [data]
  );
  const compatibilityIssues = useMemo(
    () => inspectConfigCompatibility(data, schema),
    [data, schema]
  );
  const hasCompatibilityIssues = compatibilityIssues.length > 0;
  const isDirty = editorContent !== savedEditorContent;
  const isSubmitting = navigation.state === "submitting";
  const clientValidationErrors = useMemo(
    () =>
      hasGuidedProfile
        ? validateProfiledConfig(schema, jsonData, formProfile, t)
        : [],
    [formProfile, hasGuidedProfile, jsonData, schema, t]
  );
  const normalizedServerErrors = useMemo(
    () => normalizeValidationErrors(validationErrors, formProfile, t),
    [formProfile, t, validationErrors]
  );
  const allValidationErrors = [
    ...clientValidationErrors,
    ...normalizedServerErrors,
  ];
  const hasBlockingErrors = allValidationErrors.length > 0;

  useEffect(() => {
    setEditorContent(savedEditorContent);
    setJsonData(data);
  }, [data, savedEditorContent]);

  useEffect(() => {
    if (actionData && actionData.ok === false) {
      setValidationErrors(actionData.error);
      toast.error(t("settings.config.saveFailed", { name: displayName }));
    } else if (actionData && actionData.ok) {
      setValidationErrors(null);
      toast.success(t("settings.config.saved", { name: displayName }));
      revalidator.revalidate();
    }
  }, [actionData, displayName, revalidator, t]);

  useEffect(() => {
    const warnBeforeUnload = (event) => {
      if (!isDirty) return;
      event.preventDefault();
      event.returnValue = "";
    };

    window.addEventListener("beforeunload", warnBeforeUnload);
    return () => window.removeEventListener("beforeunload", warnBeforeUnload);
  }, [isDirty]);

  useEffect(() => {
    setValidationErrors(null);
    setActiveSection(formProfile?.sections?.[0]?.id || "operation");
    setTestOpen(false);
  }, [command, formProfile]);

  const handleSubmit = (e) => {
    if (
      !canChange ||
      isSubmitting ||
      !isDirty ||
      hasBlockingErrors ||
      hasCompatibilityIssues
    ) {
      e.preventDefault();
      return;
    }
    const formData = new FormData();
    formData.append("config", editorContent);
    formData.append("name", command);
    submit(formData, { method: "post" });
    e.preventDefault();
  };

  const handleDiscard = () => {
    setEditorContent(savedEditorContent);
    setJsonData(data);
    setValidationErrors(null);
  };

  const handleGuidedChange = (fieldName, value) => {
    const nextData = mergeConfigWithSchema(
      jsonData,
      { [fieldName]: value },
      schema
    );
    setJsonData(nextData);
    setEditorContent(JSON.stringify(nextData, null, 2));
    setValidationErrors(null);
  };

  const handleSchemaSectionChange = (sectionData) => {
    const nextData = mergeConfigWithSchema(jsonData, sectionData, schema);
    setJsonData(nextData);
    setEditorContent(JSON.stringify(nextData, null, 2));
    setValidationErrors(null);
  };

  const handleOpenAutobalancerSettings = () => {
    setSettingsOpen(true);
    window.requestAnimationFrame(() => {
      document
        .getElementById("autobalancer-settings")
        ?.scrollIntoView({ behavior: "smooth", block: "start" });
    });
  };

  const pageEyebrow = formProfile?.eyebrowKey
    ? t(formProfile.eyebrowKey)
    : t("settings.configForms.workbench.defaultEyebrow");
  const pageTitle = formProfile?.titleKey
    ? t(formProfile.titleKey)
    : displayName;
  const pageDescription = formProfile?.introKey
    ? t(formProfile.introKey)
    : t("settings.configForms.workbench.defaultIntro");
  const hasEnabledSetting = Boolean(schema?.properties?.enabled);
  const ruleStatus = hasEnabledSetting
    ? jsonData?.enabled
      ? jsonData?.dry_run
        ? t("settings.configForms.workbench.statusTest")
        : t("settings.configForms.workbench.statusActive")
      : t("settings.configForms.workbench.statusInactive")
    : t("settings.configForms.workbench.statusConfigured");
  const ruleStatusColor =
    hasEnabledSetting && jsonData?.enabled ? "success" : "default";
  const localWorkbenchCopy = i18n.language?.startsWith("de")
    ? {
        test: "Auswirkung testen",
        scope: "Geltungsbereich",
        scopeValue: "Dieser Server",
        validation: "Validierung",
        valid: "Bereit zum Speichern",
        errors: `${allValidationErrors.length} Angaben prüfen`,
      }
    : {
        test: "Test impact",
        scope: "Scope",
        scopeValue: "This server",
        validation: "Validation",
        valid: "Ready to save",
        errors: `${allValidationErrors.length} entries need attention`,
      };
  const changeMetaItems = [
    {
      id: "scope",
      label: localWorkbenchCopy.scope,
      value: localWorkbenchCopy.scopeValue,
    },
    {
      id: "validation",
      label: localWorkbenchCopy.validation,
      value: hasBlockingErrors
        ? localWorkbenchCopy.errors
        : localWorkbenchCopy.valid,
      color: hasBlockingErrors ? "error.main" : "success.main",
    },
  ];
  const activeSectionIndex = (formProfile?.sections || []).findIndex(
    (section) => section.id === activeSection
  );
  const sectionNavigation = (formProfile?.sections || []).map(
    (section, index) => ({
      id: section.id,
      label: t(section.titleKey),
      description: t(section.descriptionKey),
      status: allValidationErrors.some(
        (error) => error.sectionId === section.id
      )
        ? "error"
        : index < activeSectionIndex
        ? "complete"
        : index === activeSectionIndex
        ? "current"
        : "upcoming",
    })
  );

  if (isIntegrationHub) {
    const integrationForm = (
      <Form id="config-settings-form" method="post" onSubmit={handleSubmit}>
        <Stack spacing={1.5}>
          <Box
            sx={{
              border: "1px solid",
              borderColor: "divider",
              px: { xs: 1.5, md: 2 },
              py: 1.25,
              bgcolor: "background.paper",
            }}
          >
            <Box>
              <Typography
                variant="overline"
                color="primary.main"
                sx={{ display: "block", letterSpacing: "0.08em" }}
              >
                {t("settings.integrations.form.moduleConfiguration")}
              </Typography>
              <Stack
                direction="row"
                spacing={1}
                alignItems="baseline"
                flexWrap="wrap"
              >
                <Typography component="h2" variant="h6">
                  {displayName}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {ruleStatus}
                </Typography>
              </Stack>
            </Box>
          </Box>

          {!canChange && (
            <Alert severity="warning">
              <Typography variant="body2" fontWeight={800}>
                {t("settings.configForms.workbench.readOnly")}
              </Typography>
              <Typography variant="body2">
                {t("settings.configForms.workbench.readOnlyDescription", {
                  permission: changePermission,
                })}
              </Typography>
            </Alert>
          )}

          <ConfigCompatibilityAlert issues={compatibilityIssues} />

          <ConfigValidationSummary
            errors={allValidationErrors}
            title={t("settings.configForms.workbench.validationTitle")}
            description={t(
              "settings.configForms.workbench.validationDescription"
            )}
            navigateLabel={t("settings.configForms.workbench.navigateToError")}
          />

          {!hasCompatibilityIssues && (
            <IntegrationConfigEditor
              command={command}
              data={jsonData}
              disabled={!canChange}
              schema={schema}
              onChange={(nextData) => handleSchemaSectionChange(nextData)}
            />
          )}

          {isChatWebhookConfig && (
            <ChatWebhookDiagnostics canChange={canChange} />
          )}

          <ConfigActionBar
            sticky={false}
            dirty={isDirty}
            dirtyLabel={t("settings.configForms.workbench.dirty")}
            stateLabel={
              isDirty ? undefined : t("settings.configForms.workbench.saved")
            }
            stateDescription={
              isDirty
                ? undefined
                : t("settings.configForms.workbench.savedDescription")
            }
            stateIcon={
              isDirty ? (
                <WarningAmberOutlinedIcon color="warning" />
              ) : (
                <CheckCircleOutlineIcon color="success" />
              )
            }
            metaItems={changeMetaItems}
            secondaryActions={[
              {
                id: "reset",
                label: t("settings.configForms.workbench.reset"),
                startIcon: <RestartAltIcon />,
                variant: "text",
                onClick: handleDiscard,
                disabled: !isDirty || isSubmitting,
                testId: "config-reset-button",
              },
            ]}
            primaryAction={{
              id: "save",
              type: "submit",
              form: "config-settings-form",
              label: t("settings.configForms.workbench.save"),
              loadingLabel: t("settings.configForms.workbench.saving"),
              loading: isSubmitting,
              startIcon: <SaveOutlinedIcon />,
              sx: { width: 200, height: 40 },
              disabled:
                !canChange ||
                !isDirty ||
                hasBlockingErrors ||
                hasCompatibilityIssues ||
                isSubmitting,
            }}
          />
        </Stack>
      </Form>
    );

    return (
      <IntegrationsHub
        activeCommand={command}
        activeData={jsonData}
        isDirty={isDirty}
      >
        {integrationForm}
      </IntegrationsHub>
    );
  }

  const content = (
    <Stack
      direction="column"
      spacing={isSystemDiagnostics ? 2 : 4}
      sx={
        isSystemDiagnostics
          ? {
              p: { xs: 1.5, md: 2 },
              "& .MuiButton-root, & .MuiButtonGroup-root, & .MuiPaper-root, & .MuiOutlinedInput-root":
                {
                  borderRadius: 0,
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
      {isChatWebhookConfig && <ChatWebhookDiagnostics canChange={canChange} />}
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
        <Form id="config-settings-form" method="post" onSubmit={handleSubmit}>
          <WorkbenchLayout
            embedded={isIntegrationHub || isSystemDiagnostics}
            eyebrow={pageEyebrow}
            title={pageTitle}
            description={pageDescription}
            status={
              usesSeedingRenderer ||
              usesSeedVipRenderer ||
              usesGuidedRenderer ||
              usesNameKickRenderer ||
              (usesSchemaWorkbench && hasEnabledSetting)
                ? undefined
                : ruleStatus
            }
            statusColor={ruleStatusColor}
            sections={sectionNavigation}
            activeSection={activeSection}
            onSectionChange={setActiveSection}
            navigationLabel={t("settings.configForms.workbench.navigation")}
            mobileNavigationLabel={t(
              "settings.configForms.workbench.mobileNavigation"
            )}
            headerActions={
              <Stack
                direction={{ xs: "column", lg: "row" }}
                spacing={1}
                alignItems={{ xs: "stretch", lg: "center" }}
              >
                {usesSeedingRenderer && (
                  <SeedingOperationModeControl
                    data={jsonData}
                    disabled={!canChange || hasCompatibilityIssues}
                    onChange={handleSchemaSectionChange}
                  />
                )}
                {usesGuidedRenderer && (
                  <NoLeaderOperationModeControl
                    data={jsonData}
                    disabled={!canChange || hasCompatibilityIssues}
                    onChange={handleSchemaSectionChange}
                    translationRoot={formProfile.translationRoot}
                  />
                )}
                {usesSchemaWorkbench && formProfile.operationMode && (
                  <NoLeaderOperationModeControl
                    data={jsonData}
                    disabled={!canChange || hasCompatibilityIssues}
                    onChange={handleSchemaSectionChange}
                    translationRoot="settings.configForms"
                    supportsDryRun={formProfile.operationMode === "threeState"}
                  />
                )}
                {supportsImpactTest && (
                  <Button
                    variant="outlined"
                    startIcon={<ScienceOutlinedIcon />}
                    onClick={() => setTestOpen(true)}
                    disabled={hasCompatibilityIssues}
                    sx={{ minHeight: 44, minWidth: { lg: 196 } }}
                  >
                    {localWorkbenchCopy.test}
                  </Button>
                )}
              </Stack>
            }
            summary={
              hasGuidedProfile && !hasCompatibilityIssues ? (
                usesNameKickRenderer ? (
                  <NameKickSummaryPanel data={jsonData} />
                ) : usesGuidedRenderer ? (
                  <NoLeaderSummaryPanel
                    data={jsonData}
                    translationRoot={formProfile.translationRoot}
                  />
                ) : usesSeedingRenderer ? (
                  <SeedingSummaryPanel data={jsonData} />
                ) : (
                  <ConfigProfileSummaryPanel
                    profile={formProfile}
                    data={jsonData}
                  />
                )
              ) : null
            }
            actionBar={
              <ConfigActionBar
                sticky={!isIntegrationHub}
                dirty={isDirty}
                dirtyLabel={t("settings.configForms.workbench.dirty")}
                stateLabel={
                  isDirty
                    ? undefined
                    : t("settings.configForms.workbench.saved")
                }
                stateDescription={
                  isDirty
                    ? undefined
                    : t("settings.configForms.workbench.savedDescription")
                }
                stateIcon={
                  isDirty ? (
                    <WarningAmberOutlinedIcon color="warning" />
                  ) : (
                    <CheckCircleOutlineIcon color="success" />
                  )
                }
                metaItems={changeMetaItems}
                secondaryActions={[
                  ...(supportsImpactTest
                    ? [
                        {
                          id: "test-impact",
                          label: localWorkbenchCopy.test,
                          startIcon: <ScienceOutlinedIcon />,
                          variant: "outlined",
                          onClick: () => setTestOpen(true),
                          disabled: hasCompatibilityIssues,
                          testId: "config-test-impact-button",
                        },
                      ]
                    : []),
                  {
                    id: "reset",
                    label: t("settings.configForms.workbench.reset"),
                    startIcon: <RestartAltIcon />,
                    variant: "text",
                    onClick: handleDiscard,
                    disabled: !isDirty || isSubmitting,
                    testId: "config-reset-button",
                  },
                ]}
                primaryAction={{
                  id: "save",
                  type: "submit",
                  form: "config-settings-form",
                  label: isAutobalancer
                    ? t("settings.config.saveSettings")
                    : t("settings.configForms.workbench.save"),
                  loadingLabel: t("settings.configForms.workbench.saving"),
                  loading: isSubmitting,
                  startIcon: <SaveOutlinedIcon />,
                  sx: { width: 200, height: 40 },
                  disabled:
                    !canChange ||
                    !isDirty ||
                    hasBlockingErrors ||
                    hasCompatibilityIssues ||
                    isSubmitting,
                }}
              />
            }
          >
            {!canChange && (
              <Alert severity="warning">
                <Typography variant="body2" fontWeight={800}>
                  {t("settings.configForms.workbench.readOnly")}
                </Typography>
                <Typography variant="body2">
                  {t("settings.configForms.workbench.readOnlyDescription", {
                    permission: changePermission,
                  })}
                </Typography>
              </Alert>
            )}

            <ConfigCompatibilityAlert issues={compatibilityIssues} />

            <ConfigValidationSummary
              errors={allValidationErrors}
              title={t("settings.configForms.workbench.validationTitle")}
              description={t(
                "settings.configForms.workbench.validationDescription"
              )}
              onNavigate={(sectionId) => {
                setActiveSection(sectionId);
              }}
              navigateLabel={t(
                "settings.configForms.workbench.navigateToError"
              )}
            />

            {isAutobalancer && !hasCompatibilityIssues && (
              <AutobalancerHelp config={jsonData} />
            )}

            {!hasCompatibilityIssues &&
              (hasGuidedProfile ? (
                usesGuidedRenderer &&
                guidedRendererSections.has(activeSection) ? (
                  <GuidedConfigForm
                    profile={formProfile}
                    schema={schema}
                    data={jsonData}
                    activeSection={activeSection}
                    disabled={!canChange}
                    onChange={handleGuidedChange}
                  />
                ) : usesSeedingRenderer &&
                  seedingRendererSections.has(activeSection) ? (
                  <SeedingConfigForm
                    profile={formProfile}
                    schema={schema}
                    data={jsonData}
                    activeSection={activeSection}
                    disabled={!canChange}
                    onChange={handleSchemaSectionChange}
                  />
                ) : usesSeedVipRenderer &&
                  seedVipRendererSections.has(activeSection) ? (
                  <SeedVipConfigForm
                    data={jsonData}
                    activeSection={activeSection}
                    disabled={!canChange}
                    onChange={handleSchemaSectionChange}
                  />
                ) : (
                  <SchemaConfigForm
                    profile={formProfile}
                    schema={schema}
                    data={jsonData}
                    activeSection={activeSection}
                    disabled={!canChange}
                    onChange={handleSchemaSectionChange}
                  />
                )
              ) : (
                <Box
                  sx={{
                    p: { xs: 1.25, sm: 2 },
                    border: "1px solid",
                    borderColor: "divider",
                    bgcolor: "background.paper",
                    "& .MuiFormControl-root": { mt: 1.75 },
                  }}
                >
                  <JsonForms
                    data={jsonData}
                    readonly={!canChange}
                    onChange={({ data: nextData }) => {
                      const mergedData = mergeConfigWithSchema(
                        jsonData,
                        nextData,
                        schema
                      );
                      setEditorContent(JSON.stringify(mergedData, null, 2));
                      setJsonData(mergedData);
                      setValidationErrors(null);
                    }}
                    sx={{ "& .jfa-label": { fontSize: "14px" } }}
                    schema={schema}
                    uischema={Generate.uiSchema(schema)}
                    renderers={[...customRenderers, ...materialRenderers]}
                    cells={materialCells}
                  />
                </Box>
              ))}
          </WorkbenchLayout>
        </Form>
      </Collapse>
      {supportsImpactTest && (
        <Suspense fallback={null}>
          {testKind === "level" ? (
            <LevelRuleTestDrawer
              open={testOpen}
              onClose={() => setTestOpen(false)}
              data={jsonData}
            />
          ) : (
            <EscalationRuleTestDrawer
              open={testOpen}
              onClose={() => setTestOpen(false)}
              data={jsonData}
              kind={testKind}
            />
          )}
        </Suspense>
      )}
    </Stack>
  );

  return isSystemDiagnostics ? (
    <SystemDiagnosticsLayout>{content}</SystemDiagnosticsLayout>
  ) : (
    content
  );
};

export default ConfigPage;
