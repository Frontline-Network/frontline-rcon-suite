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
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import KeyOutlinedIcon from "@mui/icons-material/KeyOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import QueryStatsOutlinedIcon from "@mui/icons-material/QueryStatsOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import SyncOutlinedIcon from "@mui/icons-material/SyncOutlined";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import { JsonForms } from "@jsonforms/react";
import { Generate } from "@jsonforms/core";
import {
  materialCells,
  materialRenderers,
} from "@jsonforms/material-renderers";
import { useTranslation } from "react-i18next";
import { schemaFormCustomRenderers } from "@/pages/settings/[configs]/renderer/renderer";
import ConfigFormSection from "./ConfigFormSection";
import NameKickFlagsField from "./NameKickFlagsField";
import NameKickRulesField from "./NameKickRulesField";

const sectionIcons = {
  operation: <PowerSettingsNewIcon fontSize="small" />,
  intervention: <BalanceOutlinedIcon fontSize="small" />,
  squads: <GroupsOutlinedIcon fontSize="small" />,
  safety: <ShieldOutlinedIcon fontSize="small" />,
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
  connections: <DnsOutlinedIcon fontSize="small" />,
  telemetry: <QueryStatsOutlinedIcon fontSize="small" />,
  identity: <BadgeOutlinedIcon fontSize="small" />,
  access: <LockOutlinedIcon fontSize="small" />,
  refresh: <SyncOutlinedIcon fontSize="small" />,
  windowsStore: <RuleOutlinedIcon fontSize="small" />,
  credentials: <KeyOutlinedIcon fontSize="small" />,
  capacity: <StorageOutlinedIcon fontSize="small" />,
  timing: <ScheduleOutlinedIcon fontSize="small" />,
  thresholds: <SpeedOutlinedIcon fontSize="small" />,
  exceptions: <ShieldOutlinedIcon fontSize="small" />,
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

const localizeProperty = (name, propertySchema, t, i18n, translationRoot) => {
  const labelKeys = [
    translationRoot && `${translationRoot}.fields.${name}.label`,
    `settings.others.fields.${name}.title`,
  ].filter(Boolean);
  const helpKeys = [
    translationRoot && `${translationRoot}.fields.${name}.help`,
    `settings.others.fields.${name}.description`,
  ].filter(Boolean);
  const labelKey = labelKeys.find((key) => i18n.exists(key));
  const helpKey = helpKeys.find((key) => i18n.exists(key));
  const properties = propertySchema?.properties
    ? Object.fromEntries(
        Object.entries(propertySchema.properties).map(
          ([childName, childSchema]) => [
            childName,
            localizeProperty(childName, childSchema, t, i18n, translationRoot),
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

const localizeSchema = (activeSchema, t, i18n, translationRoot) => ({
  ...activeSchema,
  ...(activeSchema.$defs
    ? {
        $defs: Object.fromEntries(
          Object.entries(activeSchema.$defs).map(([name, definition]) => [
            name,
            localizeProperty(name, definition, t, i18n, translationRoot),
          ])
        ),
      }
    : {}),
  properties: Object.fromEntries(
    Object.entries(activeSchema?.properties || {}).map(
      ([name, propertySchema]) => [
        name,
        localizeProperty(name, propertySchema, t, i18n, translationRoot),
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
    () => localizeSchema(activeSchema, t, i18n, profile.translationRoot),
    [activeSchema, i18n, profile.translationRoot, t]
  );
  // A newly generated UI schema reinitializes JsonForms while its debounced
  // change event is still pending, potentially restoring an old selection.
  const uiSchema = useMemo(() => {
    const generated = Generate.uiSchema(localizedActiveSchema);
    // Resolving a $ref discards the field-specific title (e.g. two
    // language packs using one definition). Keep it on the UI control.
    return {
      ...generated,
      elements: generated.elements.map((element) => {
        const field = element.scope
          ?.replace("#/properties/", "")
          .replace(/~1/g, "/")
          .replace(/~0/g, "~");
        const title = localizedActiveSchema.properties[field]?.title;
        return title ? { ...element, label: title } : element;
      }),
    };
  }, [localizedActiveSchema]);

  if (!section) return null;

  const isNameKickRules =
    profile?.titleKey === "settings.configForms.nameKicks.title" &&
    section.id === "rules";
  const isNameKickExemptions =
    profile?.titleKey === "settings.configForms.nameKicks.title" &&
    section.id === "exemptions";

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
        {isNameKickRules ? (
          <NameKickRulesField
            value={activeData.regular_expressions}
            disabled={disabled}
            onChange={(regularExpressions) =>
              onChange?.({ regular_expressions: regularExpressions })
            }
          />
        ) : isNameKickExemptions ? (
          <NameKickFlagsField
            value={activeData.whitelist_flags}
            disabled={disabled}
            onChange={(whitelistFlags) =>
              onChange?.({ whitelist_flags: whitelistFlags })
            }
          />
        ) : (
          <Box
            sx={{
              border: "1px solid",
              borderColor: "divider",
              bgcolor: "background.default",
              px: { xs: 1.25, sm: 1.75 },
              py: { xs: 1, sm: 1.5 },
              "& .MuiFormControl-root": { mt: 0.5 },
              "& .MuiGrid-container": { rowGap: 0.5 },
              "& .MuiInputBase-root": {
                bgcolor: "background.paper",
                borderRadius: 0,
              },
              "& .MuiButton-root, & .MuiChip-root, & .MuiAlert-root": {
                borderRadius: 0,
              },
              "& .MuiCard-root": {
                borderRadius: 0,
                boxShadow: "none",
                bgcolor: "background.paper",
                border: "1px solid",
                borderColor: "divider",
              },
              "& .MuiCardContent-root": {
                px: { xs: 1.25, sm: 1.75 },
                py: { xs: 1, sm: 1.5 },
                "&:last-child": { pb: { xs: 1, sm: 1.5 } },
              },
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
              uischema={uiSchema}
              renderers={[...schemaFormCustomRenderers, ...materialRenderers]}
              cells={materialCells}
            />
          </Box>
        )}
      </ConfigFormSection>
    </Box>
  );
}
