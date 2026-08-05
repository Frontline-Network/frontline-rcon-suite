import {
  Form,
  json,
  useActionData,
  useLoaderData,
  useRevalidator,
  useSubmit,
} from "react-router-dom";
import { lazy, Suspense, useEffect, useMemo, useState } from "react";
import { execute, get, handleHttpError } from "@/utils/fetchUtils";
import {
  Box,
  Button,
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

const Editor = lazy(() => import("@monaco-editor/react"));

const OTHER_CONFIG_COMMANDS = new Set([
  "autobalancer_config",
  "seed_vip_config",
  "rcon_connection_settings_config",
  "rcon_server_settings_config",
  "chat_commands_config",
  "rcon_chat_commands_config",
  "scoreboard_config",
  "steam_config",
  "vac_game_bans_config",
  "tk_ban_on_connect_config",
  "name_kick_config",
  "expired_vip_config",
  "server_name_change_config",
  "log_stream_config",
  "watch_killrate_config",
]);

const localizeOtherSchema = (schema, t) => {
  const localizeNode = (node, propertyName) => {
    if (Array.isArray(node)) {
      return node.map((item) => localizeNode(item));
    }

    if (!node || typeof node !== "object") return node;

    const localized = { ...node };
    if (propertyName) {
      const key = `settings.others.fields.${propertyName}`;
      if (i18n.exists(`${key}.title`)) localized.title = t(`${key}.title`);
      if (i18n.exists(`${key}.description`)) {
        localized.description = t(`${key}.description`);
      }
    }

    if (node.properties) {
      localized.properties = Object.fromEntries(
        Object.entries(node.properties).map(([name, value]) => [
          name,
          localizeNode(value, name),
        ])
      );
    }
    if (node.$defs) {
      localized.$defs = Object.fromEntries(
        Object.entries(node.$defs).map(([name, value]) => [
          name,
          localizeNode(value),
        ])
      );
    }
    ["items", "anyOf", "oneOf", "allOf"].forEach((key) => {
      if (node[key]) localized[key] = localizeNode(node[key]);
    });

    return localized;
  };

  return localizeNode(schema);
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
    return {
      note: note.default,
      data: { enabled: true, discord_webhook_url: "https://discord.example/frontline" },
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

  if (!(name && config)) return { ok: false, error: i18n.t("errors.missingParameters") };

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
  const localizedSchema = useMemo(
    () =>
      OTHER_CONFIG_COMMANDS.has(command)
        ? localizeOtherSchema(schema, t)
        : schema,
    [command, schema, t]
  );

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

  return (
    <Stack direction={"column"} spacing={4}>
      {isAutobalancer && <AutobalancerShadowOverview config={jsonData} />}
      {isAutobalancer && (
        <Button
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
            ? "Einstellungen schließen"
            : `Einstellungen öffnen · Modus ${jsonData?.mode || "unbekannt"}`}
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
                  {isAutobalancer ? "Einfache Ansicht" : t("settings.config.visual")}
                </Button>
                <Button
                  variant={mode === "code" ? "contained" : "outlined"}
                  onClick={() => updateMode("code")}
                >
                  {isAutobalancer ? "Erweitert (JSON)" : t("settings.config.code")}
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
                    schema={localizedSchema}
                    uischema={Generate.uiSchema(localizedSchema)}
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
                  {isAutobalancer ? "Neu laden" : t("common.refresh")}
                </Button>
                <Button variant={"contained"} type="submit">
                  {isAutobalancer
                    ? "Einstellungen speichern"
                    : t("settings.config.submit")}
                </Button>
              </Stack>
            </Stack>
          </Form>
          {mode === "code" ? (
            <>
              <Typography variant="h4">
                {isAutobalancer
                  ? "Erklärung"
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
                  ? "Technisches Schema"
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
};

export default ConfigPage;
