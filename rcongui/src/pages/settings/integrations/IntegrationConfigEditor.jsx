import { useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Box,
  Button,
  IconButton,
  InputAdornment,
  MenuItem,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import DeleteOutlineIcon from "@mui/icons-material/DeleteOutline";
import VisibilityOffOutlinedIcon from "@mui/icons-material/VisibilityOffOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import { getIntegrationWorkbenchCopy } from "./workbench-copy";

const sectionOrder = [
  "operation",
  "destinations",
  "events",
  "mentions",
  "commands",
  "connection",
  "scoreboardHeader",
  "mapRotation",
  "playerStats",
  "appearance",
  "advanced",
];

const webhookCommands = new Set([
  "audit_discord_webhooks_config",
  "admin_pings_discord_webhooks_config",
  "watchlist_discord_webhooks_config",
  "camera_discord_webhooks_config",
  "chat_discord_webhooks_config",
  "kills_discord_webhooks_config",
  "log_line_webhook_config",
]);

const resolveSchema = (rootSchema, inputSchema = {}) => {
  if (inputSchema.$ref?.startsWith("#/")) {
    const referenced = inputSchema.$ref
      .slice(2)
      .split("/")
      .reduce((current, key) => current?.[key], rootSchema);
    return resolveSchema(rootSchema, referenced || {});
  }
  if (Array.isArray(inputSchema.allOf) && inputSchema.allOf.length) {
    return resolveSchema(rootSchema, inputSchema.allOf[0]);
  }
  if (Array.isArray(inputSchema.anyOf)) {
    const concrete = inputSchema.anyOf.find(
      (candidate) => candidate.type !== "null"
    );
    return resolveSchema(rootSchema, concrete || inputSchema.anyOf[0]);
  }
  return inputSchema;
};

const inferType = (schema, value) => {
  if (schema?.type)
    return Array.isArray(schema.type) ? schema.type[0] : schema.type;
  if (Array.isArray(value)) return "array";
  if (value !== null && typeof value === "object") return "object";
  return typeof value;
};

const setAtPath = (source, path, value) => {
  if (!path.length) return value;
  const [head, ...tail] = path;
  const clone = Array.isArray(source) ? [...source] : { ...(source || {}) };
  clone[head] = setAtPath(source?.[head], tail, value);
  return clone;
};

const defaultForSchema = (rootSchema, inputSchema = {}) => {
  const schema = resolveSchema(rootSchema, inputSchema);
  if (schema.default !== undefined) return schema.default;
  const type = inferType(schema);
  if (type === "boolean") return false;
  if (type === "integer" || type === "number") return schema.minimum || 0;
  if (type === "array") return [];
  if (type === "object") {
    return Object.fromEntries(
      Object.entries(schema.properties || {}).map(([key, childSchema]) => [
        key,
        defaultForSchema(rootSchema, childSchema),
      ])
    );
  }
  return "";
};

const humanize = (value) =>
  value
    .replace(/_/g, " ")
    .replace(/\b\w/g, (character) => character.toUpperCase());

const getFieldLabel = (t, key, schema) =>
  t(`settings.integrations.form.fields.${key}`, {
    defaultValue: schema.title || humanize(key),
  });

const getFieldHelp = (t, key, schema) =>
  t(`settings.integrations.form.help.${key}`, {
    defaultValue: schema.description || "",
  });

const isSensitiveField = (path) => {
  const key = String(path.at(-1) || "").toLowerCase();
  return key === "url" || key.includes("webhook_url");
};

function PrimitiveField({
  disabled,
  fieldKey,
  onChange,
  path,
  rootSchema,
  schema: inputSchema,
  value,
}) {
  const { t } = useTranslation();
  const [revealed, setRevealed] = useState(false);
  const schema = resolveSchema(rootSchema, inputSchema);
  const type = inferType(schema, value);
  const label = getFieldLabel(t, fieldKey, schema);
  const help = getFieldHelp(t, fieldKey, schema);
  const options =
    schema.enum ||
    schema.oneOf
      ?.map((entry) => entry.const)
      .filter((entry) => entry !== undefined);

  if (type === "boolean") {
    return (
      <Box>
        <Typography
          component="span"
          variant="overline"
          color="text.secondary"
          sx={{ display: "block", mb: 0.6, letterSpacing: "0.07em" }}
        >
          {label}
        </Typography>
        <Stack direction="row" role="group" aria-label={label}>
          {[false, true].map((option) => (
            <Button
              key={String(option)}
              fullWidth
              size="small"
              disabled={disabled}
              variant={Boolean(value) === option ? "contained" : "outlined"}
              aria-pressed={Boolean(value) === option}
              onClick={() => onChange(option)}
              sx={{ minHeight: 36 }}
            >
              {t(
                option
                  ? "settings.integrations.form.enabled"
                  : "settings.integrations.form.disabled"
              )}
            </Button>
          ))}
        </Stack>
        {help && (
          <Typography variant="caption" color="text.secondary" sx={{ mt: 0.6 }}>
            {help}
          </Typography>
        )}
      </Box>
    );
  }

  if (options?.length) {
    return (
      <TextField
        select
        fullWidth
        size="small"
        disabled={disabled}
        label={label}
        value={value ?? ""}
        helperText={help}
        onChange={(event) => onChange(event.target.value)}
      >
        {options.map((option) => (
          <MenuItem key={String(option)} value={option}>
            {String(option)}
          </MenuItem>
        ))}
      </TextField>
    );
  }

  const sensitive = isSensitiveField(path);
  const multiline = /message|description|format|legend/i.test(fieldKey);
  return (
    <TextField
      fullWidth
      size="small"
      disabled={disabled}
      type={
        sensitive && !revealed
          ? "password"
          : type === "integer" || type === "number"
          ? "number"
          : "text"
      }
      multiline={multiline}
      minRows={multiline ? 2 : undefined}
      label={label}
      value={value ?? ""}
      helperText={sensitive ? t("settings.integrations.form.secretHelp") : help}
      onChange={(event) => {
        const raw = event.target.value;
        onChange(
          type === "integer" || type === "number"
            ? raw === ""
              ? ""
              : Number(raw)
            : raw
        );
      }}
      inputProps={{
        min: schema.minimum,
        max: schema.maximum,
        step: type === "integer" ? 1 : undefined,
      }}
      InputProps={
        sensitive
          ? {
              endAdornment: (
                <InputAdornment position="end">
                  <IconButton
                    size="small"
                    edge="end"
                    aria-label={t(
                      revealed
                        ? "settings.integrations.form.hideSecret"
                        : "settings.integrations.form.showSecret"
                    )}
                    onClick={() => setRevealed((current) => !current)}
                  >
                    {revealed ? (
                      <VisibilityOffOutlinedIcon fontSize="small" />
                    ) : (
                      <VisibilityOutlinedIcon fontSize="small" />
                    )}
                  </IconButton>
                </InputAdornment>
              ),
            }
          : undefined
      }
    />
  );
}

function KeyValueObjectField({
  disabled,
  label,
  onChange,
  path,
  rootSchema,
  schema,
  value,
}) {
  const { t, i18n } = useTranslation();
  const workbenchCopy = getIntegrationWorkbenchCopy(i18n.resolvedLanguage);
  const [newKey, setNewKey] = useState("");
  const [newKeyError, setNewKeyError] = useState("");
  const entries = Object.entries(value || {});
  const itemSchema =
    schema.additionalProperties &&
    typeof schema.additionalProperties === "object"
      ? schema.additionalProperties
      : {};
  const sampleValue = entries[0]?.[1];
  const defaultDynamicValue = () => {
    if (Object.keys(itemSchema).length) {
      return defaultForSchema(rootSchema, itemSchema);
    }
    if (Array.isArray(sampleValue)) return [];
    if (sampleValue !== null && typeof sampleValue === "object") return {};
    if (typeof sampleValue === "boolean") return false;
    if (typeof sampleValue === "number") return 0;
    return "";
  };

  const updateEntry = (key, nextValue) => {
    onChange({ ...(value || {}), [key]: nextValue });
  };

  const removeEntry = (key) => {
    const nextValue = { ...(value || {}) };
    delete nextValue[key];
    onChange(nextValue);
  };

  const addEntry = () => {
    const key = newKey.trim();
    if (!key) {
      setNewKeyError(workbenchCopy.keyRequired);
      return;
    }
    if (Object.prototype.hasOwnProperty.call(value || {}, key)) {
      setNewKeyError(workbenchCopy.keyExists);
      return;
    }
    onChange({
      ...(value || {}),
      [key]: defaultDynamicValue(),
    });
    setNewKey("");
    setNewKeyError("");
  };

  return (
    <Box sx={{ gridColumn: "1 / -1", minWidth: 0 }}>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="baseline"
        gap={1}
        sx={{ mb: 1 }}
      >
        <Typography variant="subtitle2">{label}</Typography>
        <Typography variant="caption" color="text.secondary">
          {t("settings.integrations.form.entryCount", {
            count: entries.length,
          })}
        </Typography>
      </Stack>

      <Stack spacing={1}>
        {entries.map(([key, entryValue]) => {
          const complex =
            entryValue !== null && typeof entryValue === "object";
          return (
            <Box data-theme-surface="panel"
              key={key}
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "minmax(0, 1fr) auto",
                  sm: "minmax(150px, 0.42fr) minmax(0, 1fr) auto",
                },
                gap: 1,
                alignItems: "start",
                border: "1px solid",
                borderColor: "divider",
                p: 1.25,
                bgcolor: "background.default",
              }}
            >
              <TextField
                size="small"
                label={workbenchCopy.keyLabel}
                value={key}
                disabled
                sx={{ gridColumn: { xs: "1 / -1", sm: "auto" } }}
              />
              {complex ? (
                <Box data-theme-surface="panel"
                  sx={{
                    minWidth: 0,
                    p: 1,
                    border: "1px solid",
                    borderColor: "divider",
                  }}
                >
                  <ConfigField
                    disabled={disabled}
                    fieldKey="listItem"
                    rootSchema={rootSchema}
                    schema={
                      Array.isArray(entryValue)
                        ? { type: "array", items: {} }
                        : { type: "object", additionalProperties: true }
                    }
                    value={entryValue}
                    path={[...path, key]}
                    onChange={(nextValue) => updateEntry(key, nextValue)}
                  />
                </Box>
              ) : (
                <PrimitiveField
                  disabled={disabled}
                  fieldKey="listItem"
                  rootSchema={rootSchema}
                  schema={itemSchema}
                  value={entryValue}
                  path={[...path, key]}
                  onChange={(nextValue) => updateEntry(key, nextValue)}
                />
              )}
              <IconButton
                size="small"
                disabled={disabled}
                aria-label={workbenchCopy.removeNamedEntry(key)}
                onClick={() => removeEntry(key)}
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Box>
          );
        })}

        {entries.length === 0 && (
          <Box data-theme-surface="panel"
            sx={{
              border: "1px dashed",
              borderColor: "divider",
              px: 1.5,
              py: 1.25,
            }}
          >
            <Typography variant="body2" color="text.secondary">
              {t("settings.integrations.form.noEntries")}
            </Typography>
          </Box>
        )}

        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", sm: "minmax(0, 1fr) auto" },
            gap: 1,
            alignItems: "start",
          }}
        >
          <TextField
            size="small"
            disabled={disabled}
            label={workbenchCopy.newKeyLabel}
            value={newKey}
            error={Boolean(newKeyError)}
            helperText={
              newKeyError || workbenchCopy.newKeyHelp
            }
            onChange={(event) => {
              setNewKey(event.target.value);
              setNewKeyError("");
            }}
            onKeyDown={(event) => {
              if (event.key !== "Enter") return;
              event.preventDefault();
              addEntry();
            }}
          />
          <Button
            variant="outlined"
            startIcon={<AddIcon />}
            disabled={disabled || !newKey.trim()}
            onClick={addEntry}
            sx={{ minHeight: 40 }}
          >
            {workbenchCopy.addSetting}
          </Button>
        </Box>
      </Stack>
    </Box>
  );
}

function ConfigField({
  disabled,
  fieldKey,
  onChange,
  path,
  rootSchema,
  schema: inputSchema,
  value,
}) {
  const { t, i18n } = useTranslation();
  const workbenchCopy = getIntegrationWorkbenchCopy(i18n.resolvedLanguage);
  const schema = resolveSchema(rootSchema, inputSchema);
  const type = inferType(schema, value);
  const label = getFieldLabel(t, fieldKey, schema);

  if (type === "array") {
    const itemSchema = resolveSchema(rootSchema, schema.items || {});
    const items = Array.isArray(value) ? value : [];
    const itemType = inferType(itemSchema, items[0]);
    return (
      <Box sx={{ gridColumn: "1 / -1" }}>
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{ mb: 1 }}
        >
          <Typography variant="subtitle2">{label}</Typography>
          <Typography variant="caption" color="text.secondary">
            {t("settings.integrations.form.entryCount", {
              count: items.length,
            })}
          </Typography>
        </Stack>
        <Stack spacing={1}>
          {items.map((item, index) => (
            <Box data-theme-surface="panel"
              key={`${fieldKey}-${index}`}
              sx={{
                display: "grid",
                gridTemplateColumns: "minmax(0, 1fr) auto",
                gap: 1,
                alignItems: "start",
                border: "1px solid",
                borderColor: "divider",
                p: 1.25,
                bgcolor: "background.default",
              }}
            >
              {itemType === "object" ? (
                <Box
                  sx={{
                    display: "grid",
                    gridTemplateColumns: {
                      xs: "1fr",
                      md: "repeat(2, minmax(0, 1fr))",
                    },
                    gap: 1.25,
                  }}
                >
                  {Object.entries(itemSchema.properties || {}).map(
                    ([childKey, childSchema]) => (
                      <ConfigField
                        key={childKey}
                        disabled={disabled}
                        fieldKey={childKey}
                        rootSchema={rootSchema}
                        schema={childSchema}
                        value={item?.[childKey]}
                        path={[...path, index, childKey]}
                        onChange={(nextValue) => {
                          const nextItems = [...items];
                          nextItems[index] = {
                            ...(nextItems[index] || {}),
                            [childKey]: nextValue,
                          };
                          onChange(nextItems);
                        }}
                      />
                    )
                  )}
                  {!Object.keys(itemSchema.properties || {}).length && (
                    <KeyValueObjectField
                      disabled={disabled}
                      label={getFieldLabel(t, "listItem", itemSchema)}
                      rootSchema={rootSchema}
                      schema={{ type: "object", additionalProperties: true }}
                      value={item}
                      path={[...path, index]}
                      onChange={(nextValue) => {
                        const nextItems = [...items];
                        nextItems[index] = nextValue;
                        onChange(nextItems);
                      }}
                    />
                  )}
                </Box>
              ) : (
                <PrimitiveField
                  disabled={disabled}
                  fieldKey="listItem"
                  rootSchema={rootSchema}
                  schema={itemSchema}
                  value={item}
                  path={[...path, index]}
                  onChange={(nextValue) => {
                    const nextItems = [...items];
                    nextItems[index] = nextValue;
                    onChange(nextItems);
                  }}
                />
              )}
              <IconButton
                size="small"
                disabled={disabled}
                aria-label={t("settings.integrations.form.removeEntry", {
                  number: index + 1,
                })}
                onClick={() =>
                  onChange(items.filter((_, itemIndex) => itemIndex !== index))
                }
              >
                <DeleteOutlineIcon fontSize="small" />
              </IconButton>
            </Box>
          ))}
          {items.length === 0 && (
            <Box data-theme-surface="panel"
              sx={{
                border: "1px dashed",
                borderColor: "divider",
                px: 1.5,
                py: 1.25,
              }}
            >
              <Typography variant="body2" color="text.secondary">
                {t("settings.integrations.form.noEntries")}
              </Typography>
            </Box>
          )}
          <Button
            size="small"
            variant="outlined"
            startIcon={<AddIcon />}
            disabled={disabled}
            onClick={() =>
              onChange([...items, defaultForSchema(rootSchema, itemSchema)])
            }
            sx={{ alignSelf: "flex-start" }}
          >
            {t("settings.integrations.form.addEntry")}
          </Button>
        </Stack>
      </Box>
    );
  }

  if (type === "object") {
    const properties = schema.properties || {};
    const propertyKeys = Object.keys(properties);
    if (!propertyKeys.length) {
      return (
        <KeyValueObjectField
          disabled={disabled}
          label={label}
          value={value}
          onChange={onChange}
          path={path}
          rootSchema={rootSchema}
          schema={schema}
        />
      );
    }
    const additionalValue = Object.fromEntries(
      Object.entries(value || {}).filter(
        ([key]) => !Object.prototype.hasOwnProperty.call(properties, key)
      )
    );
    return (
      <Box data-theme-surface="panel"
        sx={{
          gridColumn: "1 / -1",
          border: "1px solid",
          borderColor: "divider",
          p: 1.25,
          bgcolor: "background.default",
        }}
      >
        <Typography variant="subtitle2" sx={{ mb: 1.25 }}>
          {label}
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
            gap: 1.25,
          }}
        >
          {Object.entries(properties).map(([childKey, childSchema]) => (
            <ConfigField
              key={childKey}
              disabled={disabled}
              fieldKey={childKey}
              rootSchema={rootSchema}
              schema={childSchema}
              value={value?.[childKey]}
              path={[...path, childKey]}
              onChange={(nextValue) =>
                onChange({ ...(value || {}), [childKey]: nextValue })
              }
            />
          ))}
          {schema.additionalProperties && (
            <KeyValueObjectField
              disabled={disabled}
              label={workbenchCopy.additionalSettingsLabel}
              rootSchema={rootSchema}
              schema={schema}
              value={additionalValue}
              path={path}
              onChange={(nextAdditionalValue) => {
                const fixedValue = Object.fromEntries(
                  Object.entries(value || {}).filter(([key]) =>
                    Object.prototype.hasOwnProperty.call(properties, key)
                  )
                );
                onChange({ ...fixedValue, ...nextAdditionalValue });
              }}
            />
          )}
        </Box>
      </Box>
    );
  }

  return (
    <PrimitiveField
      disabled={disabled}
      fieldKey={fieldKey}
      rootSchema={rootSchema}
      schema={schema}
      value={value}
      path={path}
      onChange={onChange}
    />
  );
}

const sectionForField = (command, field) => {
  if (field === "enabled") return "operation";
  if (field === "hooks" || field === "webhooks" || field.includes("_url")) {
    return "destinations";
  }
  if (field.includes("mention") || field === "trigger_words") return "mentions";
  if (
    field === "send_kills" ||
    field === "send_team_kills" ||
    field === "log_types"
  ) {
    return "events";
  }
  if (field === "command_words" || field === "describe_words")
    return "commands";
  if (command === "server_name_change_config") return "connection";
  if (command === "scoreboard_config") {
    if (
      field.startsWith("header_") ||
      field.startsWith("objective_") ||
      ["quick_connect_url", "battlemetrics_url", "show_map_image"].includes(
        field
      )
    ) {
      return "scoreboardHeader";
    }
    if (
      field.startsWith("map_") ||
      ["current_map_format", "next_map_format", "other_map_format"].includes(
        field
      )
    ) {
      return "mapRotation";
    }
    if (field.startsWith("player_")) return "playerStats";
    if (field.includes("footer")) return "appearance";
  }
  if (webhookCommands.has(command)) return "events";
  return "advanced";
};

export default function IntegrationConfigEditor({
  command,
  data,
  disabled,
  onChange,
  schema,
}) {
  const { t } = useTranslation();
  const properties = schema?.properties || {};
  const sections = useMemo(() => {
    const grouped = new Map();
    Object.keys(properties).forEach((field) => {
      const section = sectionForField(command, field);
      grouped.set(section, [...(grouped.get(section) || []), field]);
    });
    return sectionOrder
      .filter((section) => grouped.has(section))
      .map((section) => ({ id: section, fields: grouped.get(section) }));
  }, [command, properties]);

  return (
    <Box data-theme-surface="panel"
      data-testid="integration-config-editor"
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "repeat(12, minmax(0, 1fr))" },
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      {sections.map((section, index) => (
        <Box
          component="section"
          key={section.id}
          sx={{
            gridColumn: {
              xs: "1 / -1",
              lg:
                sections.length === 1
                  ? "1 / -1"
                  : sections.length > 2
                  ? section.fields.some((field) =>
                      ["hooks", "webhooks", "command_words"].includes(field)
                    )
                    ? "1 / -1"
                    : "span 6"
                  : section.fields.some((field) =>
                      ["hooks", "webhooks", "command_words"].includes(field)
                    )
                  ? "span 7"
                  : "span 5",
            },
            minWidth: 0,
            p: { xs: 1.5, md: 2 },
            borderTop: { xs: index === 0 ? 0 : "1px solid", lg: 0 },
            borderLeft: {
              xs: 0,
              lg: index === 0 ? 0 : "1px solid",
            },
            borderColor: "divider",
          }}
        >
          <Stack
            direction="row"
            spacing={1.25}
            alignItems="flex-start"
            sx={{ mb: 1.75 }}
          >
            <Box data-theme-surface="control"
              sx={{
                display: "grid",
                placeItems: "center",
                width: 26,
                height: 26,
                flex: "0 0 auto",
                border: "1px solid",
                borderColor: "primary.main",
                color: "primary.main",
                fontSize: 12,
                fontWeight: 800,
              }}
            >
              {index + 1}
            </Box>
            <Box>
              <Typography
                component="h3"
                variant="subtitle2"
                sx={{ textTransform: "uppercase", letterSpacing: "0.06em" }}
              >
                {t(`settings.integrations.form.sections.${section.id}.title`)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t(
                  `settings.integrations.form.sections.${section.id}.description`
                )}
              </Typography>
            </Box>
          </Stack>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md:
                  section.fields.length > 1
                    ? "repeat(2, minmax(0, 1fr))"
                    : "1fr",
              },
              gap: 1.5,
            }}
          >
            {section.fields.map((field) => (
              <ConfigField
                key={field}
                disabled={disabled}
                fieldKey={field}
                rootSchema={schema}
                schema={properties[field]}
                value={data?.[field]}
                path={[field]}
                onChange={(value) => onChange(setAtPath(data, [field], value))}
              />
            ))}
          </Box>
        </Box>
      ))}
    </Box>
  );
}
