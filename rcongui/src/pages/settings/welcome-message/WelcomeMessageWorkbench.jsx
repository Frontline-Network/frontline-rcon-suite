import { Link } from "react-router-dom";
import {
  Alert,
  Box,
  Button,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import AddCommentOutlinedIcon from "@mui/icons-material/AddCommentOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import MessageOutlinedIcon from "@mui/icons-material/MessageOutlined";
import RestartAltOutlinedIcon from "@mui/icons-material/RestartAltOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { useTranslation } from "react-i18next";
import ConfigActionBar from "../config-form/ConfigActionBar";
import ConfigFormSection from "../config-form/ConfigFormSection";
import SeedingWorkbenchLayout from "../config-form/SeedingWorkbenchLayout";
import ConfirmButton from "@/components/shared/ConfirmButton";

const ROOT = "settings.welcome";

function SummaryItem({ icon, label, value, detail }) {
  return (
    <Stack
      direction="row"
      spacing={1.5}
      alignItems="flex-start"
      sx={{ minWidth: 0, p: { xs: 1.5, md: 2 } }}
    >
      <Box sx={{ color: "primary.main", display: "grid", mt: 0.1 }}>{icon}</Box>
      <Box sx={{ minWidth: 0 }}>
        <Typography variant="overline" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="body1" fontWeight={800} noWrap>
          {value}
        </Typography>
        {detail && (
          <Typography variant="caption" color="text.secondary">
            {detail}
          </Typography>
        )}
      </Box>
    </Stack>
  );
}

function WelcomeSummary({ message }) {
  const { t } = useTranslation();
  const active = Boolean(message.trim());
  const lines = message ? message.split(/\r?\n/).length : 0;

  return (
    <Box data-theme-surface="panel"
      component="aside"
      aria-label={t(`${ROOT}.summaryTitle`)}
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", sm: "repeat(3, minmax(0, 1fr))" },
        border: "1px solid",
        borderColor: "divider",
        "& > * + *": {
          borderTop: { xs: "1px solid", sm: 0 },
          borderLeft: { xs: 0, sm: "1px solid" },
          borderColor: "divider",
        },
      }}
    >
      <SummaryItem
        icon={<MessageOutlinedIcon fontSize="small" />}
        label={t(`${ROOT}.statusLabel`)}
        value={t(active ? `${ROOT}.active` : `${ROOT}.inactive`)}
        detail={t(active ? `${ROOT}.activeHint` : `${ROOT}.inactiveHint`)}
      />
      <SummaryItem
        icon={<VisibilityOutlinedIcon fontSize="small" />}
        label={t(`${ROOT}.sizeLabel`)}
        value={t(`${ROOT}.characterCount`, { count: message.length })}
        detail={t(`${ROOT}.lineCount`, { count: lines })}
      />
      <SummaryItem
        icon={<CheckCircleOutlineIcon fontSize="small" />}
        label={t(`${ROOT}.scopeLabel`)}
        value={t(`${ROOT}.currentServer`)}
        detail={t(`${ROOT}.scopeHint`)}
      />
    </Box>
  );
}

function MessageEditor({ message, onMessageChange }) {
  const { t } = useTranslation();

  return (
    <ConfigFormSection
      plain
      id="welcome-message-editor"
      eyebrow={t(`${ROOT}.messageEyebrow`)}
      title={t(`${ROOT}.editorTitle`)}
      description={t(`${ROOT}.editorDescription`)}
      icon={<MessageOutlinedIcon />}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            lg: "minmax(0, 1.65fr) minmax(260px, 0.7fr)",
          },
          gap: 2,
          alignItems: "stretch",
        }}
      >
        <TextField
          name="message"
          label={t(`${ROOT}.messageLabel`)}
          value={message}
          onChange={(event) => onMessageChange(event.target.value)}
          placeholder={t("settings.templates.messageContent")}
          multiline
          minRows={12}
          fullWidth
          helperText={t(`${ROOT}.editorHint`)}
          slotProps={{ htmlInput: { "data-testid": "welcome-message-input" } }}
        />

        <Stack data-theme-surface="panel"
          spacing={1.5}
          className="wardogs-writing-guide"
          sx={{
            p: 2,
            border: "1px solid",
            borderColor: "divider",
            bgcolor: "background.default",
          }}
        >
          <Typography variant="overline" color="primary.main">
            {t(`${ROOT}.writingGuideTitle`)}
          </Typography>
          {["short", "clear", "lineBreaks"].map((key) => (
            <Stack
              key={key}
              direction="row"
              spacing={1}
              alignItems="flex-start"
            >
              <CheckCircleOutlineIcon
                color="success"
                sx={{ fontSize: 18, mt: 0.15 }}
              />
              <Typography variant="body2" color="text.secondary">
                {t(`${ROOT}.writingGuide.${key}`)}
              </Typography>
            </Stack>
          ))}
          <Alert severity={message.trim() ? "info" : "warning"}>
            {t(message.trim() ? `${ROOT}.saveHint` : `${ROOT}.disableHint`)}
          </Alert>
        </Stack>
      </Box>
    </ConfigFormSection>
  );
}

function Preview({ message }) {
  const { t } = useTranslation();
  const active = Boolean(message.trim());

  return (
    <ConfigFormSection
      plain
      id="welcome-message-preview"
      eyebrow={t(`${ROOT}.previewEyebrow`)}
      title={t(`${ROOT}.previewTitle`)}
      description={t(`${ROOT}.previewDescription`)}
      icon={<VisibilityOutlinedIcon />}
    >
      <Box data-theme-surface="panel"
        sx={{
          border: "1px solid",
          borderColor: active ? "primary.dark" : "divider",
          bgcolor: "background.default",
        }}
      >
        <Stack
          direction="row"
          justifyContent="space-between"
          alignItems="center"
          sx={{
            px: 2,
            py: 1.25,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="overline" color="primary.main">
            {t(`${ROOT}.playerJoinLabel`)}
          </Typography>
          <Typography
            variant="caption"
            color={active ? "success.main" : "text.disabled"}
          >
            {t(active ? `${ROOT}.active` : `${ROOT}.inactive`)}
          </Typography>
        </Stack>
        <Typography
          component="div"
          variant="body1"
          sx={{
            minHeight: 180,
            p: { xs: 2, md: 3 },
            whiteSpace: "pre-wrap",
            overflowWrap: "anywhere",
            color: active ? "text.primary" : "text.secondary",
            fontWeight: 600,
            lineHeight: 1.6,
          }}
        >
          {active ? message : t(`${ROOT}.previewEmpty`)}
        </Typography>
      </Box>
    </ConfigFormSection>
  );
}

export default function WelcomeMessageWorkbench({
  message,
  activeSection,
  onSectionChange,
  onMessageChange,
  onReset,
  onApply,
  onApplyAll,
  hasChanges,
  saving,
  templatePicker,
}) {
  const { t } = useTranslation();
  const active = Boolean(message.trim());
  const sections = [
    {
      id: "messages",
      label: t(`${ROOT}.messageSection`),
      description: t(`${ROOT}.messageSectionDescription`),
      status: "complete",
    },
    {
      id: "templates",
      label: t(`${ROOT}.templateSection`),
      description: t(`${ROOT}.templateSectionDescription`),
      status: "complete",
    },
    {
      id: "preview",
      label: t(`${ROOT}.previewSection`),
      description: t(`${ROOT}.previewSectionDescription`),
      status: "complete",
    },
  ];

  return (
    <SeedingWorkbenchLayout
      testId="welcome-message-workbench"
      eyebrow={t(`${ROOT}.eyebrow`)}
      title={t(`${ROOT}.title`)}
      description={t(`${ROOT}.subtitle`)}
      status={t(active ? `${ROOT}.active` : `${ROOT}.inactive`)}
      statusColor={active ? "success" : "default"}
      sections={sections}
      activeSection={activeSection}
      onSectionChange={onSectionChange}
      navigationLabel={t(`${ROOT}.sectionNavigation`)}
      mobileNavigationLabel={t(`${ROOT}.sectionNavigation`)}
      summary={<WelcomeSummary message={message} />}
      actionBar={
        <ConfigActionBar
          dirty={hasChanges}
          dirtyLabel={t(`${ROOT}.unsavedChanges`)}
          stateIcon={
            hasChanges ? (
              <WarningAmberOutlinedIcon color="warning" fontSize="small" />
            ) : (
              <CheckCircleOutlineIcon color="success" fontSize="small" />
            )
          }
          stateLabel={t(
            hasChanges ? `${ROOT}.changesPending` : `${ROOT}.allSaved`
          )}
          stateDescription={t(
            hasChanges
              ? `${ROOT}.changesPendingDescription`
              : `${ROOT}.allSavedDescription`
          )}
          secondaryActions={[
            {
              id: "reset-welcome-message",
              label: t(`${ROOT}.reset`),
              onClick: onReset,
              disabled: !hasChanges || saving,
              startIcon: <RestartAltOutlinedIcon fontSize="small" />,
            },
            {
              id: "apply-welcome-message-all",
              node: (
                <ConfirmButton
                  key="apply-welcome-message-all"
                  disabled={!hasChanges || saving}
                  onConfirm={onApplyAll}
                  title={t(`${ROOT}.applyAllTitle`)}
                  description={t(`${ROOT}.applyAllDescription`)}
                  buttonText={t(`${ROOT}.allServers`)}
                  buttonProps={{
                    variant: "outlined",
                    startIcon: <CheckCircleOutlineIcon />,
                  }}
                />
              ),
            },
          ]}
          primaryAction={{
            label: saving ? t("common.loading") : t(`${ROOT}.apply`),
            onClick: onApply,
            disabled: !hasChanges || saving,
            loading: saving,
            startIcon: <MessageOutlinedIcon fontSize="small" />,
          }}
        />
      }
    >
      {activeSection === "messages" && (
        <MessageEditor message={message} onMessageChange={onMessageChange} />
      )}

      {activeSection === "templates" && (
        <ConfigFormSection
          plain
          id="welcome-message-templates"
          eyebrow={t(`${ROOT}.templateEyebrow`)}
          title={t(`${ROOT}.templateTitle`)}
          description={t(`${ROOT}.templateDescription`)}
          icon={<AddCommentOutlinedIcon />}
        >
          <Stack spacing={2}>
            {templatePicker}
            <Button
              component={Link}
              startIcon={<AddCommentOutlinedIcon />}
              variant="outlined"
              to="/settings/templates/welcome"
              sx={{
                alignSelf: { xs: "stretch", sm: "flex-start" },
                minHeight: 44,
              }}
            >
              {t("settings.broadcast.createTemplate")}
            </Button>
          </Stack>
        </ConfigFormSection>
      )}

      {activeSection === "preview" && <Preview message={message} />}
    </SeedingWorkbenchLayout>
  );
}
