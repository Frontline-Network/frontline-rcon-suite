import { useMemo } from "react";
import { Alert, Box } from "@mui/material";
import PowerSettingsNewIcon from "@mui/icons-material/PowerSettingsNew";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import ExitToAppOutlinedIcon from "@mui/icons-material/ExitToAppOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import RedeemOutlinedIcon from "@mui/icons-material/RedeemOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import { JsonForms } from "@jsonforms/react";
import { Generate } from "@jsonforms/core";
import {
  materialCells,
  materialRenderers,
} from "@jsonforms/material-renderers";
import { useTranslation } from "react-i18next";
import { schemaFormCustomRenderers } from "@/pages/settings/[configs]/renderer/renderer";
import ConfigFormSection from "./ConfigFormSection";

const sectionIcons = {
  operation: <PowerSettingsNewIcon fontSize="small" />,
  scope: <TuneOutlinedIcon fontSize="small" />,
  requirements: <RuleOutlinedIcon fontSize="small" />,
  detection: <VisibilityOutlinedIcon fontSize="small" />,
  rules: <RuleOutlinedIcon fontSize="small" />,
  exemptions: <ShieldOutlinedIcon fontSize="small" />,
  schedule: <ScheduleOutlinedIcon fontSize="small" />,
  announcements: <CampaignOutlinedIcon fontSize="small" />,
  warnings: <CampaignOutlinedIcon fontSize="small" />,
  punishments: <GavelOutlinedIcon fontSize="small" />,
  kick: <ExitToAppOutlinedIcon fontSize="small" />,
  actions: <GavelOutlinedIcon fontSize="small" />,
  reward: <RedeemOutlinedIcon fontSize="small" />,
  messages: <CampaignOutlinedIcon fontSize="small" />,
  notifications: <NotificationsNoneOutlinedIcon fontSize="small" />,
  advanced: <TuneOutlinedIcon fontSize="small" />,
};

const sectionSchema = (schema, fields) => {
  const properties = Object.fromEntries(
    fields
      .filter((name) => schema?.properties?.[name])
      .map((name) => [name, schema.properties[name]])
  );
  return {
    ...schema,
    properties,
    required: (schema?.required || []).filter((name) => fields.includes(name)),
  };
};

const localizeProperty = (name, propertySchema, t, i18n) => {
  const labelKeys = [
    `settings.configForms.noLeader.fields.${name}.label`,
    `settings.others.fields.${name}.title`,
  ];
  const helpKeys = [
    `settings.configForms.noLeader.fields.${name}.help`,
    `settings.others.fields.${name}.description`,
  ];
  const labelKey = labelKeys.find((key) => i18n.exists(key));
  const helpKey = helpKeys.find((key) => i18n.exists(key));
  const properties = propertySchema?.properties
    ? Object.fromEntries(
        Object.entries(propertySchema.properties).map(
          ([childName, childSchema]) => [
            childName,
            localizeProperty(childName, childSchema, t, i18n),
          ]
        )
      )
    : undefined;

  return {
    ...propertySchema,
    ...(labelKey ? { title: t(labelKey) } : {}),
    ...(helpKey ? { description: t(helpKey) } : {}),
    ...(properties ? { properties } : {}),
  };
};

const localizeSchema = (activeSchema, t, i18n) => ({
  ...activeSchema,
  properties: Object.fromEntries(
    Object.entries(activeSchema?.properties || {}).map(
      ([name, propertySchema]) => [
        name,
        localizeProperty(name, propertySchema, t, i18n),
      ]
    )
  ),
});

export default function SchemaConfigForm({
  profile,
  schema,
  data,
  activeSection,
  disabled = false,
  onChange,
}) {
  const { t, i18n } = useTranslation();
  const section = profile.sections.find(({ id }) => id === activeSection);
  const activeSchema = useMemo(
    () => sectionSchema(schema, section?.fields || []),
    [schema, section]
  );
  const activeData = useMemo(
    () =>
      Object.fromEntries(
        (section?.fields || []).map((name) => [name, data?.[name]])
      ),
    [data, section]
  );
  const localizedActiveSchema = useMemo(
    () => localizeSchema(activeSchema, t, i18n),
    [activeSchema, i18n, t]
  );

  if (!section) return null;

  return (
    <Box data-testid="config-schema-form">
      {schema?.properties?.enabled && data?.enabled === false && (
        <Alert severity="info" sx={{ mb: 2 }}>
          {t("settings.configForms.workbench.ruleDisabledNotice")}
        </Alert>
      )}
      <ConfigFormSection
        id={`config-form-${section.id}`}
        testId={`config-section-${section.id}`}
        icon={sectionIcons[section.id]}
        title={t(section.titleKey)}
        description={t(section.descriptionKey)}
        disabled={disabled}
        plain
      >
        <Box
          sx={{
            "& .MuiFormControl-root": { mt: 0.5 },
            "& .MuiGrid-container": { rowGap: 0.5 },
            "& .MuiInputBase-root": { bgcolor: "background.default" },
            "& .MuiFormHelperText-root": { lineHeight: 1.45 },
          }}
        >
          <JsonForms
            data={activeData}
            readonly={disabled}
            onChange={({ data: nextSectionData }) =>
              onChange?.(nextSectionData || {})
            }
            schema={localizedActiveSchema}
            uischema={Generate.uiSchema(localizedActiveSchema)}
            renderers={[...schemaFormCustomRenderers, ...materialRenderers]}
            cells={materialCells}
          />
        </Box>
      </ConfigFormSection>
    </Box>
  );
}
