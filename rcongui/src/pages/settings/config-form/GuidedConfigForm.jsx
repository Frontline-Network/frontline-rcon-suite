import { useMemo } from "react";
import {
  Alert,
  Autocomplete,
  Box,
  Chip,
  FormControlLabel,
  IconButton,
  InputAdornment,
  Stack,
  Switch,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import ExitToAppOutlinedIcon from "@mui/icons-material/ExitToAppOutlined";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import AddIcon from "@mui/icons-material/Add";
import RemoveIcon from "@mui/icons-material/Remove";
import { useTranslation } from "react-i18next";
import { getAllRoles } from "@/constants/roles";
import ConfigFormSection from "./ConfigFormSection";

const sectionIcons = {
  operation: <PowerSettingsNewIcon fontSize="small" />,
  exemptions: <ShieldOutlinedIcon fontSize="small" />,
  observation: <VisibilityOutlinedIcon fontSize="small" />,
  warnings: <CampaignOutlinedIcon fontSize="small" />,
  punishments: <GavelOutlinedIcon fontSize="small" />,
  kick: <ExitToAppOutlinedIcon fontSize="small" />,
};

const normalizeType = (property = {}) => {
  if (Array.isArray(property.type)) {
    return property.type.find((type) => type !== "null");
  }
  if (property.anyOf) {
    return property.anyOf.find((entry) => entry.type !== "null")?.type;
  }
  return property.type;
};

const specialChoice = (value) => {
  if (Number(value) === 0) return "skip";
  if (Number(value) === -1) return "unlimited";
  return "count";
};

const clampNumber = (value, minimum, maximum) =>
  Math.min(
    maximum ?? Number.MAX_SAFE_INTEGER,
    Math.max(minimum ?? Number.MIN_SAFE_INTEGER, Number(value) || 0)
  );

function NumberStepper({
  value,
  minimum,
  maximum,
  unit,
  disabled,
  onChange,
  ariaLabel,
}) {
  const update = (nextValue) =>
    onChange(clampNumber(nextValue, minimum, maximum));

  return (
    <Box>
      <Stack
        direction="row"
        alignItems="center"
        sx={{
          width: "100%",
          minHeight: 40,
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.default",
        }}
      >
        <IconButton
          size="small"
          disabled={disabled || Number(value) <= (minimum ?? 0)}
          onClick={() => update(Number(value) - 1)}
          aria-label={`${ariaLabel} -`}
          sx={{ borderRadius: 0, width: 40, alignSelf: "stretch" }}
        >
          <RemoveIcon fontSize="small" />
        </IconButton>
        <Typography
          component="output"
          aria-label={ariaLabel}
          variant="body1"
          fontWeight={900}
          sx={{ flex: 1, textAlign: "center" }}
        >
          {value}
        </Typography>
        <IconButton
          size="small"
          disabled={
            disabled || (maximum !== undefined && Number(value) >= maximum)
          }
          onClick={() => update(Number(value) + 1)}
          aria-label={`${ariaLabel} +`}
          sx={{ borderRadius: 0, width: 40, alignSelf: "stretch" }}
        >
          <AddIcon fontSize="small" />
        </IconButton>
        {unit && (
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "grid",
              placeItems: "center",
              alignSelf: "stretch",
              minWidth: 88,
              px: 1.25,
              borderLeft: "1px solid",
              borderColor: "divider",
            }}
          >
            {unit}
          </Typography>
        )}
      </Stack>
    </Box>
  );
}

export const validateProfiledConfig = (schema, data, profile, t) => {
  if (!schema || !data || !profile) return [];

  const required = new Set(schema.required || []);
  const sectionByField = new Map(
    profile.sections.flatMap((section) =>
      section.fields.map((fieldName) => [fieldName, section.id])
    )
  );

  return Object.entries(schema.properties || {}).flatMap(([name, property]) => {
    const value = data[name];
    const metadata = profile.fields[name];
    const label = metadata?.labelKey ? t(metadata.labelKey) : name;
    const sectionId = sectionByField.get(name);
    const errors = [];

    if (
      required.has(name) &&
      (value === undefined || value === null || value === "")
    ) {
      errors.push({
        id: `${name}-required`,
        label,
        message: t("settings.configForms.workbench.validation.required"),
        sectionId,
      });
      return errors;
    }

    if (value === undefined || value === null || value === "") return errors;

    const type = normalizeType(property);
    if (type === "integer" && !Number.isInteger(Number(value))) {
      errors.push({
        id: `${name}-integer`,
        label,
        message: t("settings.configForms.workbench.validation.integer"),
        sectionId,
      });
      return errors;
    }

    if (type === "integer" && property.minimum !== undefined) {
      if (Number(value) < property.minimum) {
        errors.push({
          id: `${name}-minimum`,
          label,
          message: t("settings.configForms.workbench.validation.minimum", {
            value: property.minimum,
          }),
          sectionId,
        });
      }
    }

    if (type === "integer" && property.maximum !== undefined) {
      if (Number(value) > property.maximum) {
        errors.push({
          id: `${name}-maximum`,
          label,
          message: t("settings.configForms.workbench.validation.maximum", {
            value: property.maximum,
          }),
          sectionId,
        });
      }
    }

    if (metadata?.kind === "url" && typeof value === "string") {
      try {
        const parsed = new URL(value);
        if (!["http:", "https:"].includes(parsed.protocol)) throw new Error();
      } catch {
        errors.push({
          id: `${name}-url`,
          label,
          message: t("settings.configForms.workbench.validation.url"),
          sectionId,
        });
      }
    }

    if (type === "array" && Array.isArray(value)) {
      const allowedValues =
        property.items?.enum instanceof Array
          ? new Set(property.items.enum)
          : null;
      if (allowedValues && value.some((item) => !allowedValues.has(item))) {
        errors.push({
          id: `${name}-enum`,
          label,
          message: t("settings.configForms.workbench.validation.enum"),
          sectionId,
        });
      }
      if (new Set(value).size !== value.length) {
        errors.push({
          id: `${name}-duplicate`,
          label,
          message: t("settings.configForms.workbench.validation.duplicate"),
          sectionId,
        });
      }
    }

    if (metadata?.placeholders && typeof value === "string") {
      const allowed = new Set(metadata.placeholders);
      const used = value.match(/\{[^{}]+\}/g) || [];
      const invalid = [...new Set(used.filter((token) => !allowed.has(token)))];
      if (invalid.length) {
        errors.push({
          id: `${name}-placeholder`,
          label,
          message: t("settings.configForms.workbench.validation.placeholder", {
            values: invalid.join(", "),
          }),
          sectionId,
        });
      }
    }

    return errors;
  });
};

function ToggleField({ name, value, metadata, disabled, onChange }) {
  const { t } = useTranslation();
  return (
    <Box
      sx={{
        p: 1.5,
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.default",
      }}
    >
      <FormControlLabel
        control={
          <Switch
            name={name}
            checked={Boolean(value)}
            disabled={disabled}
            onChange={(event) => onChange(event.target.checked)}
          />
        }
        label={
          <Box>
            <Typography variant="body2" fontWeight={800}>
              {t(metadata.labelKey)}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              {t(metadata.helpKey)}
            </Typography>
          </Box>
        }
        sx={{ m: 0, alignItems: "flex-start", gap: 0.75 }}
      />
    </Box>
  );
}

function CountChoiceField({
  name,
  value,
  metadata,
  property,
  disabled,
  onChange,
}) {
  const { t } = useTranslation();
  const choice = specialChoice(value);
  const unit = metadata.unitKey ? t(metadata.unitKey) : undefined;

  return (
    <Stack spacing={1.25}>
      <Box>
        <Typography variant="body2" fontWeight={800}>
          {t(metadata.labelKey)}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {t(metadata.helpKey)}
        </Typography>
      </Box>
      <ToggleButtonGroup
        exclusive
        fullWidth
        size="small"
        value={choice}
        disabled={disabled}
        onChange={(_, nextChoice) => {
          if (!nextChoice) return;
          if (nextChoice === "skip") onChange(0);
          if (nextChoice === "unlimited") onChange(-1);
          if (nextChoice === "count") onChange(Number(value) > 0 ? value : 1);
        }}
        aria-label={t(metadata.labelKey)}
      >
        <ToggleButton value="skip">
          {t("settings.configForms.workbench.choices.skip")}
        </ToggleButton>
        <ToggleButton value="count">
          {t("settings.configForms.workbench.choices.count")}
        </ToggleButton>
        <ToggleButton value="unlimited">
          {t("settings.configForms.workbench.choices.unlimited")}
        </ToggleButton>
      </ToggleButtonGroup>
      {choice === "count" && (
        <TextField
          name={name}
          type="number"
          size="small"
          disabled={disabled}
          value={value}
          onChange={(event) => onChange(Number(event.target.value))}
          inputProps={{
            min: Math.max(1, property.minimum || 1),
            max: property.maximum,
          }}
          InputProps={{
            endAdornment: unit ? (
              <InputAdornment position="end">{unit}</InputAdornment>
            ) : undefined,
          }}
        />
      )}
    </Stack>
  );
}

function MessageField({ name, value, metadata, disabled, onChange, data }) {
  const { t } = useTranslation();
  const placeholders = metadata.placeholders || [];
  const localizedPlaceholder = (placeholder) =>
    `{${t(
      `settings.configForms.workbench.placeholders.${placeholder.replace(
        /[{}]/g,
        ""
      )}`,
      { defaultValue: placeholder.replace(/[{}]/g, "") }
    )}}`;
  const displayValue = placeholders.reduce(
    (message, placeholder) =>
      message.replaceAll(placeholder, localizedPlaceholder(placeholder)),
    value || ""
  );
  const toStoredValue = (message) =>
    placeholders.reduce(
      (storedMessage, placeholder) =>
        storedMessage.replaceAll(
          localizedPlaceholder(placeholder),
          placeholder
        ),
      message
    );
  const nextCheckSeconds =
    name === "punish_message"
      ? data?.punish_interval_seconds
      : data?.warning_interval_seconds;
  const warningTotal =
    Number(data?.number_of_warnings) === -1
      ? "∞"
      : data?.number_of_warnings ?? 2;

  const insertPlaceholder = (placeholder) => {
    const current = value || "";
    const separator = current && !current.endsWith(" ") ? " " : "";
    onChange(`${current}${separator}${placeholder}`);
  };

  const preview = (value || "")
    .replaceAll("{player_name}", "Bumse")
    .replaceAll("{squad_name}", "Able")
    .replaceAll("{max_warnings}", String(data?.number_of_warnings ?? 2))
    .replaceAll("{received_warnings}", "1")
    .replaceAll("{max_punishes}", String(data?.number_of_punishments ?? 2))
    .replaceAll("{received_punishes}", "1")
    .replaceAll("{next_check_seconds}", String(nextCheckSeconds ?? 60))
    .replaceAll(
      "{kick_grace_period}",
      String(data?.kick_grace_period_seconds ?? 60)
    );

  return (
    <Stack spacing={1.25}>
      <Box>
        <Typography
          variant="overline"
          fontWeight={800}
          sx={{ display: "block", lineHeight: 1.25 }}
        >
          {t(metadata.labelKey)}
        </Typography>
        <Typography
          variant="caption"
          color="text.secondary"
          sx={{ display: "block", lineHeight: 1.35, mt: 0.4 }}
        >
          {t(metadata.helpKey)}
        </Typography>
      </Box>
      <TextField
        name={name}
        aria-label={t(metadata.labelKey)}
        value={displayValue}
        disabled={disabled}
        onChange={(event) => onChange(toStoredValue(event.target.value))}
        multiline
        minRows={name === "warning_message" ? 2 : 3}
        fullWidth
        sx={
          name === "warning_message"
            ? {
                mt: "4px !important",
                "& .MuiInputBase-root": { minHeight: 82 },
              }
            : undefined
        }
      />
      <Typography variant="caption" color="text.secondary">
        {t("settings.configForms.workbench.availablePlaceholders")}
      </Typography>
      <Stack
        direction="row"
        spacing={0.75}
        useFlexGap
        flexWrap="wrap"
        sx={{ mt: "2px !important" }}
      >
        {placeholders.map((placeholder) => (
          <Chip
            key={placeholder}
            label={t(
              `settings.configForms.workbench.placeholders.${placeholder.replace(
                /[{}]/g,
                ""
              )}`,
              { defaultValue: placeholder }
            )}
            size="small"
            variant="outlined"
            disabled={disabled}
            onClick={() => insertPlaceholder(placeholder)}
            sx={{ height: 24, "& .MuiChip-label": { px: 1 } }}
          />
        ))}
      </Stack>
      <Box sx={{ pt: 4.625 }}>
        <Typography
          variant="overline"
          color="text.primary"
          sx={{ display: "block", lineHeight: 1.25, mb: 0.75 }}
        >
          {t("settings.configForms.workbench.messagePreview")}
        </Typography>
        <Box
          sx={{
            p: 1.5,
            minHeight: name === "warning_message" ? 93 : undefined,
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "action.hover",
            borderRadius: 0.75,
          }}
        >
          <Typography
            variant="body2"
            sx={{ overflowWrap: "anywhere", whiteSpace: "pre-line" }}
          >
            {preview || t("settings.configForms.workbench.messagePreviewEmpty")}
          </Typography>
          {name === "warning_message" && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.75 }}
            >
              {t("settings.configForms.workbench.warningPreviewMeta", {
                current: 1,
                total: warningTotal,
                seconds: data?.warning_interval_seconds ?? 60,
              })}
            </Typography>
          )}
        </Box>
      </Box>
    </Stack>
  );
}

function FieldControl({
  name,
  value,
  metadata,
  property,
  disabled,
  onChange,
  data,
}) {
  const { t, i18n } = useTranslation();
  const type = normalizeType(property);

  if (metadata.kind === "toggle" || type === "boolean") {
    return (
      <ToggleField
        name={name}
        value={value}
        metadata={metadata}
        disabled={disabled}
        onChange={onChange}
        data={data}
      />
    );
  }

  if (
    metadata.kind === "number" &&
    Object.prototype.hasOwnProperty.call(metadata.specialValues || {}, "-1")
  ) {
    return (
      <CountChoiceField
        name={name}
        value={value}
        metadata={metadata}
        property={property}
        disabled={disabled}
        onChange={onChange}
      />
    );
  }

  if (metadata.kind === "textarea") {
    return (
      <MessageField
        name={name}
        value={value}
        metadata={metadata}
        disabled={disabled}
        onChange={onChange}
        data={data}
      />
    );
  }

  if (metadata.kind === "roles") {
    const roleOptions = getAllRoles().map((role) => ({
      ...role,
      label: t(`settings.configForms.roles.${role.value}`, {
        defaultValue: role.label,
      }),
    }));
    const selected = (value || []).map(
      (roleValue) =>
        roleOptions.find((option) => option.value === roleValue) || {
          value: roleValue,
          label: roleValue,
        }
    );

    return (
      <Autocomplete
        multiple
        options={roleOptions}
        value={selected}
        disabled={disabled}
        isOptionEqualToValue={(option, selectedOption) =>
          option.value === selectedOption.value
        }
        onChange={(_, nextValue) =>
          onChange(nextValue.map((item) => item.value))
        }
        renderInput={(params) => (
          <TextField
            {...params}
            label={t(metadata.labelKey)}
            helperText={t(metadata.helpKey)}
          />
        )}
      />
    );
  }

  if (metadata.kind === "tags") {
    return (
      <Autocomplete
        multiple
        freeSolo
        options={[]}
        value={value || []}
        disabled={disabled}
        onChange={(_, nextValue) => onChange(nextValue)}
        renderInput={(params) => (
          <TextField
            {...params}
            label={t(metadata.labelKey)}
            helperText={t(metadata.helpKey)}
          />
        )}
      />
    );
  }

  const unit = metadata.unitKey ? t(metadata.unitKey) : undefined;
  const specialValue = metadata.specialValues?.[value];
  const helper = specialValue
    ? `${t(metadata.helpKey)} ${t(
        `settings.configForms.specialValues.${specialValue}`
      )}`
    : t(metadata.helpKey);

  return (
    <TextField
      name={name}
      type={
        type === "integer" ? "number" : metadata.kind === "url" ? "url" : "text"
      }
      label={t(metadata.labelKey)}
      helperText={helper}
      placeholder={
        metadata.placeholderKey ? t(metadata.placeholderKey) : undefined
      }
      value={value ?? ""}
      disabled={disabled}
      onChange={(event) =>
        onChange(
          type === "integer"
            ? Number(event.target.value)
            : metadata.kind === "url" && event.target.value === ""
            ? null
            : event.target.value
        )
      }
      fullWidth
      inputProps={
        type === "integer"
          ? {
              min: property.minimum,
              max: property.maximum,
              lang: i18n.language,
            }
          : undefined
      }
      InputProps={{
        endAdornment: unit ? (
          <InputAdornment position="end">{unit}</InputAdornment>
        ) : undefined,
      }}
    />
  );
}

function WarningFields({ profile, schema, data, disabled, onChange }) {
  const { t } = useTranslation();
  const countMetadata = profile.fields.number_of_warnings;
  const countProperty = schema.properties?.number_of_warnings || {};
  const countChoice = specialChoice(data.number_of_warnings);

  return (
    <Stack spacing={2.5}>
      <Stack spacing={0}>
        <Typography
          variant="overline"
          fontWeight={800}
          sx={{ display: "block" }}
        >
          {t("settings.configForms.workbench.warningMode")}
        </Typography>
        <ToggleButtonGroup
          exclusive
          fullWidth
          size="small"
          value={countChoice}
          disabled={disabled}
          onChange={(_, nextChoice) => {
            if (!nextChoice) return;
            if (nextChoice === "skip") onChange("number_of_warnings", 0);
            if (nextChoice === "unlimited") onChange("number_of_warnings", -1);
            if (nextChoice === "count") {
              onChange(
                "number_of_warnings",
                Number(data.number_of_warnings) > 0
                  ? data.number_of_warnings
                  : 1
              );
            }
          }}
          aria-label={t(countMetadata.labelKey)}
          sx={{
            borderRadius: 0.75,
            overflow: "hidden",
            "& .MuiToggleButton-root": {
              borderRadius: 0,
              py: 0.9,
              textTransform: "none",
            },
            "& .Mui-selected": {
              bgcolor: "rgba(214, 170, 77, 0.08) !important",
              color: "primary.main !important",
              borderColor: "primary.main !important",
              borderRadius: "6px !important",
            },
          }}
        >
          {["skip", "count", "unlimited"].map((choice) => (
            <ToggleButton key={choice} value={choice}>
              <Box>
                <Typography variant="body2" fontWeight={850}>
                  {t(`settings.configForms.workbench.choices.${choice}`)}
                </Typography>
                <Typography
                  component="span"
                  variant="caption"
                  color="text.secondary"
                >
                  {t(`settings.configForms.workbench.choiceHelp.${choice}`)}
                </Typography>
              </Box>
            </ToggleButton>
          ))}
        </ToggleButtonGroup>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "minmax(0, 323px) minmax(0, 280px)",
          },
          gap: { xs: 2, sm: 3.25 },
          maxWidth: { sm: 629 },
        }}
      >
        {countChoice === "count" && (
          <Box>
            <Typography variant="overline" fontWeight={800} sx={{ mb: 0.75 }}>
              {t("settings.configForms.workbench.warningsBeforePunish")}
            </Typography>
            <NumberStepper
              value={data.number_of_warnings}
              minimum={Math.max(1, countProperty.minimum || 1)}
              maximum={countProperty.maximum}
              disabled={disabled}
              onChange={(value) => onChange("number_of_warnings", value)}
              ariaLabel={t(countMetadata.labelKey)}
            />
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.75 }}
            >
              {t("settings.configForms.workbench.warningsBeforePunishHelp")}
            </Typography>
          </Box>
        )}
        <Box>
          <Typography variant="overline" fontWeight={800} sx={{ mb: 0.75 }}>
            {t(profile.fields.warning_interval_seconds.labelKey)}
          </Typography>
          <NumberStepper
            value={data.warning_interval_seconds}
            minimum={schema.properties?.warning_interval_seconds?.minimum ?? 1}
            maximum={schema.properties?.warning_interval_seconds?.maximum}
            unit={t(profile.fields.warning_interval_seconds.unitKey)}
            disabled={disabled}
            onChange={(value) => onChange("warning_interval_seconds", value)}
            ariaLabel={t(profile.fields.warning_interval_seconds.labelKey)}
          />
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", mt: 0.75 }}
          >
            {t("settings.configForms.workbench.warningIntervalHelp")}
          </Typography>
        </Box>
      </Box>

      <MessageField
        name="warning_message"
        value={data.warning_message}
        metadata={profile.fields.warning_message}
        disabled={disabled}
        onChange={(value) => onChange("warning_message", value)}
        data={data}
      />
    </Stack>
  );
}

export default function GuidedConfigForm({
  profile,
  schema,
  data,
  activeSection,
  disabled = false,
  onChange,
}) {
  const { t } = useTranslation();

  const fieldToSection = useMemo(
    () =>
      new Map(
        profile.sections.flatMap((section) =>
          section.fields.map((fieldName) => [fieldName, section.id])
        )
      ),
    [profile]
  );

  const isFieldDisabled = (fieldName) => {
    if (disabled) return true;
    if (fieldName === "dry_run" && !data.enabled) return true;
    if (
      fieldToSection.get(fieldName) === "kick" &&
      fieldName !== "kick_after_max_punish" &&
      !data.kick_after_max_punish
    ) {
      return true;
    }
    return false;
  };

  return (
    <Stack spacing={2} data-testid="config-guided-form">
      {!data.enabled && (
        <Alert severity="info" icon={<InfoOutlinedIcon />}>
          {t("settings.configForms.workbench.ruleDisabledNotice")}
        </Alert>
      )}
      {profile.sections.map((section) => (
        <Box
          key={section.id}
          sx={{ display: section.id === activeSection ? "block" : "none" }}
        >
          <ConfigFormSection
            id={`config-form-${section.id}`}
            testId={`config-section-${section.id}`}
            icon={sectionIcons[section.id]}
            title={t(section.titleKey)}
            description={t(section.descriptionKey)}
            disabled={disabled}
            plain
          >
            {section.id === "warnings" ? (
              <WarningFields
                profile={profile}
                schema={schema}
                data={data}
                disabled={disabled}
                onChange={onChange}
              />
            ) : (
              <Stack spacing={2.25}>
                {section.fields.map((fieldName) => {
                  const metadata = profile.fields[fieldName];
                  const property = schema.properties?.[fieldName] || {};
                  if (!metadata) return null;

                  return (
                    <FieldControl
                      key={fieldName}
                      name={fieldName}
                      value={data[fieldName]}
                      metadata={metadata}
                      property={property}
                      disabled={isFieldDisabled(fieldName)}
                      onChange={(value) => onChange(fieldName, value)}
                      data={data}
                    />
                  );
                })}
              </Stack>
            )}
          </ConfigFormSection>
        </Box>
      ))}
    </Stack>
  );
}
