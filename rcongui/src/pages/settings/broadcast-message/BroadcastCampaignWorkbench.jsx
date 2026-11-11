import {
  Alert,
  Box,
  Button,
  ButtonBase,
  Chip,
  Divider,
  Stack,
  TextField,
  ToggleButton,
  ToggleButtonGroup,
  Typography,
} from "@mui/material";
import AddIcon from "@mui/icons-material/Add";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import QueryStatsOutlinedIcon from "@mui/icons-material/QueryStatsOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import SendOutlinedIcon from "@mui/icons-material/SendOutlined";
import ViewListOutlinedIcon from "@mui/icons-material/ViewListOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import { useTranslation } from "react-i18next";

import ConfigActionBar from "../config-form/ConfigActionBar";
import ConfigFormSection from "../config-form/ConfigFormSection";
import SeedingWorkbenchLayout from "../config-form/SeedingWorkbenchLayout";

const ROOT = "settings.campaigns";

const campaignMode = (config) => {
  if (!config.enabled) return "off";
  return config.randomize ? "random" : "sequence";
};

const campaignChannelLabel = (campaign, t) =>
  t(
    campaign.delivery_mode === "player_message"
      ? `${ROOT}.deliveryPlayerMessage`
      : `${ROOT}.deliveryBroadcast`
  );

function SummarySegment({ icon, label, value, detail, border = true }) {
  return (
    <Box
      component="section"
      sx={{
        minWidth: 0,
        px: { xs: 1.75, md: 2.25 },
        py: 1.75,
        borderRight: { xs: 0, md: border ? "1px solid" : 0 },
        borderBottom: { xs: border ? "1px solid" : 0, md: 0 },
        borderColor: "divider",
      }}
    >
      <Stack direction="row" spacing={1.25} alignItems="flex-start">
        <Box sx={{ color: "primary.main", display: "flex", mt: 0.15 }}>
          {icon}
        </Box>
        <Box sx={{ minWidth: 0 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", letterSpacing: "0.05em" }}
          >
            {label}
          </Typography>
          <Typography variant="subtitle1" fontWeight={800} sx={{ mt: 0.25 }}>
            {value}
          </Typography>
          {detail && (
            <Typography
              variant="caption"
              color="text.secondary"
              sx={{ display: "block", mt: 0.2 }}
            >
              {detail}
            </Typography>
          )}
        </Box>
      </Stack>
    </Box>
  );
}

function BroadcastSummary({ config, activeCount }) {
  const { t } = useTranslation();
  const channels = new Set(
    config.messages
      .filter((campaign) => campaign.enabled)
      .map((campaign) => campaign.delivery_mode)
  );
  const channelSummary = channels.size
    ? [...channels]
        .map((channel) =>
          t(
            channel === "player_message"
              ? `${ROOT}.deliveryPlayerMessage`
              : `${ROOT}.deliveryBroadcast`
          )
        )
        .join(" · ")
    : t(`${ROOT}.noActiveChannels`);

  return (
    <Box data-theme-surface="panel"
      component="aside"
      aria-label={t(`${ROOT}.summaryTitle`)}
      sx={{
        border: "1px solid",
        borderColor: "divider",
        bgcolor: "background.paper",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
        }}
      >
        <SummarySegment
          icon={<DashboardOutlinedIcon fontSize="small" />}
          label={t(`${ROOT}.operationLabel`)}
          value={t(
            config.enabled ? `${ROOT}.moduleActive` : `${ROOT}.modulePaused`
          )}
          detail={t(`${ROOT}.activeOfTotal`, {
            active: activeCount,
            total: config.messages.length,
          })}
        />
        <SummarySegment
          icon={<SendOutlinedIcon fontSize="small" />}
          label={t(`${ROOT}.deliveryLabel`)}
          value={t(
            config.randomize ? `${ROOT}.randomMode` : `${ROOT}.sequenceMode`
          )}
          detail={channelSummary}
        />
        <SummarySegment
          icon={<ScheduleOutlinedIcon fontSize="small" />}
          label={t(`${ROOT}.timingLabel`)}
          value={channels.has("player_message") ? t(`${ROOT}.globalTimingValue`, {
            seconds: config.player_message_interval_sec,
          }) : t(`${ROOT}.broadcastTiming`)}
          detail={channels.has("player_message") ? t(`${ROOT}.playerGapValue`, {
            minutes: Math.round(config.player_message_gap_sec / 60),
          }) : t(`${ROOT}.broadcastIntervalHelp`)}
          border={false}
        />
      </Box>
    </Box>
  );
}

function CampaignList({ campaigns, selectedCampaignId, onSelect, onAdd }) {
  const { t } = useTranslation();

  return (
    <Box
      component="nav"
      aria-label={t(`${ROOT}.campaignList`)}
      sx={{
        minWidth: 0,
        borderRight: { md: "1px solid" },
        borderBottom: { xs: "1px solid", md: 0 },
        borderColor: "divider",
      }}
    >
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        sx={{
          px: 1.5,
          py: 1.25,
          borderBottom: "1px solid",
          borderColor: "divider",
        }}
      >
        <Box>
          <Typography variant="overline" color="text.secondary">
            {t(`${ROOT}.campaignList`)}
          </Typography>
          <Typography variant="caption" color="text.secondary" display="block">
            {t(`${ROOT}.campaignCount`, { count: campaigns.length })}
          </Typography>
        </Box>
        <Button
          size="small"
          variant="outlined"
          startIcon={<AddIcon />}
          onClick={onAdd}
          aria-label={t(`${ROOT}.add`)}
        >
          {t(`${ROOT}.addShort`)}
        </Button>
      </Stack>

      <Stack
        sx={{
          maxHeight: { md: 640 },
          overflowY: { md: "auto" },
          overflowX: "hidden",
        }}
      >
        {campaigns.map((campaign, index) => {
          const selected = campaign.id === selectedCampaignId;
          return (
            <ButtonBase
              key={campaign.id || index}
              onClick={() => onSelect(campaign.id)}
              aria-current={selected ? "page" : undefined}
              sx={{
                position: "relative",
                width: "100%",
                justifyContent: "flex-start",
                textAlign: "left",
                px: 1.75,
                py: 1.4,
                borderBottom: "1px solid",
                borderColor: "divider",
                bgcolor: selected ? "action.selected" : "transparent",
                color: selected ? "text.primary" : "text.secondary",
                "&::before": {
                  content: '""',
                  position: "absolute",
                  inset: "0 auto 0 0",
                  width: 2,
                  bgcolor: selected ? "primary.main" : "transparent",
                },
                "&:hover": { bgcolor: "action.hover" },
                "&.Mui-focusVisible": {
                  outline: "2px solid",
                  outlineColor: "primary.main",
                  outlineOffset: -2,
                },
              }}
            >
              <Stack spacing={0.6} sx={{ width: "100%", minWidth: 0 }}>
                <Stack direction="row" spacing={0.75} alignItems="center">
                  <Box
                    aria-hidden="true"
                    sx={{
                      width: 7,
                      height: 7,
                      bgcolor: campaign.enabled
                        ? "success.main"
                        : "text.disabled",
                      flex: "0 0 auto",
                    }}
                  />
                  <Typography
                    variant="body2"
                    fontWeight={selected ? 850 : 700}
                    noWrap
                    sx={{ flex: 1 }}
                  >
                    {campaign.title ||
                      t(`${ROOT}.untitledCampaign`, { count: index + 1 })}
                  </Typography>
                  <Typography variant="caption" color="text.disabled">
                    {index + 1}
                  </Typography>
                </Stack>
                <Typography variant="caption" color="text.secondary" noWrap>
                  {campaignChannelLabel(campaign, t)}
                </Typography>
                <Stack
                  direction="row"
                  justifyContent="space-between"
                  spacing={1}
                >
                  <Typography variant="caption" color="text.secondary">
                    {campaign.delivery_mode === "player_message"
                      ? t(`${ROOT}.afterSessionMinutes`, {
                          minutes: campaign.min_session_minutes,
                        })
                      : t(`${ROOT}.broadcastSeconds`, { seconds: campaign.time_sec })}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {campaign.min_players}–{campaign.max_players}
                  </Typography>
                </Stack>
              </Stack>
            </ButtonBase>
          );
        })}
      </Stack>
    </Box>
  );
}

function DeliverySettings({ config, onChange }) {
  const { t } = useTranslation();
  return (
    <ConfigFormSection
      plain
      id="campaign-delivery-settings"
      eyebrow={t(`${ROOT}.deliveryLabel`)}
      title={t(`${ROOT}.deliverySettingsTitle`)}
      description={t(`${ROOT}.deliverySettingsDescription`)}
      icon={<ScheduleOutlinedIcon />}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(2, minmax(0, 1fr))" },
          gap: 2,
        }}
      >
        <TextField
          label={t(`${ROOT}.globalSendInterval`)}
          type="number"
          value={config.player_message_interval_sec}
          onChange={(event) =>
            onChange("player_message_interval_sec", Number(event.target.value))
          }
          slotProps={{ htmlInput: { min: 5, max: 300 } }}
          helperText={t(`${ROOT}.globalSendIntervalHelp`)}
          fullWidth
        />
        <TextField
          label={t(`${ROOT}.playerGap`)}
          type="number"
          value={Math.round(config.player_message_gap_sec / 60)}
          onChange={(event) =>
            onChange("player_message_gap_sec", Number(event.target.value) * 60)
          }
          slotProps={{ htmlInput: { min: 1, max: 60 } }}
          helperText={t(`${ROOT}.playerGapHelp`)}
          fullWidth
        />
      </Box>
      <Alert severity="info" sx={{ mt: 2 }}>
        {t(`${ROOT}.priorityNote`)}
      </Alert>
    </ConfigFormSection>
  );
}

function BroadcastActivity({ status }) {
  const { t } = useTranslation();
  const formatDate = (value) => value ? new Date(value).toLocaleString() : "—";
  const state = status?.state;
  return <ConfigFormSection plain title={t(`${ROOT}.broadcastActivity`)} description={t(`${ROOT}.broadcastDisclaimer`)} icon={<CampaignOutlinedIcon />}>
    <Alert severity={status?.available === false ? "warning" : "info"}>
      {t(`${ROOT}.broadcastPhases.${state?.phase || "unknown"}`)}
      {state?.next_at && <> · {t(`${ROOT}.broadcastNext`)}: {formatDate(state.next_at)}</>}
      {state?.updated_at && <> · {t(`${ROOT}.broadcastChecked`)}: {formatDate(state.updated_at)}</>}
    </Alert>
    {(status?.recent ?? []).length === 0 && <Typography sx={{ mt: 2 }}>{t(`${ROOT}.broadcastEmpty`)}</Typography>}
    {(status?.recent ?? []).map((row, index) => <Box key={`${row.at}-${index}`} sx={{ p: 2, borderBottom: "1px solid", borderColor: "divider" }}>
      <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
        <Typography variant="body2">{formatDate(row.at)}</Typography>
        <Chip size="small" color={row.status === "accepted" ? "success" : "warning"} label={t(`${ROOT}.broadcastResult.${row.status}`)} />
        {row.error && <Typography variant="caption">{row.error}</Typography>}
      </Stack>
      <Typography sx={{ mt: 1, overflowWrap: "anywhere" }}>{row.message}</Typography>
    </Box>)}
  </ConfigFormSection>;
}

function ActivityPanel({ deliveryStatus }) {
  const { t } = useTranslation();
  const campaigns = deliveryStatus?.campaigns ?? [];
  const aggregate = campaigns.reduce(
    (result, campaign) => ({
      pending: result.pending + Number(campaign.pending || 0),
      sent: result.sent + Number(campaign.sent_24h || 0),
      failed: result.failed + Number(campaign.failed_24h || 0),
    }),
    { pending: 0, sent: 0, failed: 0 }
  );
  const recent = campaigns
    .flatMap((campaign) =>
      (campaign.recent ?? []).map((delivery) => ({
        ...delivery,
        campaignTitle: campaign.title,
      }))
    )
    .sort((left, right) =>
      String(right.updated_at).localeCompare(String(left.updated_at))
    )
    .slice(0, 12);

  return (
    <ConfigFormSection
      plain
      id="campaign-activity"
      eyebrow={t(`${ROOT}.activity`)}
      title={t(`${ROOT}.activityTitle`)}
      description={t(`${ROOT}.activityDescription`)}
      icon={<QueryStatsOutlinedIcon />}
    >
      <Box data-theme-surface="panel"
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
          border: "1px solid",
          borderColor: "divider",
        }}
      >
        {[
          [
            t(`${ROOT}.pending`, { count: aggregate.pending }),
            aggregate.pending,
          ],
          [t(`${ROOT}.sent24h`, { count: aggregate.sent }), aggregate.sent],
          [
            t(`${ROOT}.failed24h`, { count: aggregate.failed }),
            aggregate.failed,
          ],
        ].map(([label, value], index) => (
          <Box
            key={label}
            sx={{
              px: 2,
              py: 1.75,
              borderRight: { sm: index < 2 ? "1px solid" : 0 },
              borderBottom: { xs: index < 2 ? "1px solid" : 0, sm: 0 },
              borderColor: "divider",
            }}
          >
            <Typography variant="h5">{value}</Typography>
            <Typography variant="caption" color="text.secondary">
              {label}
            </Typography>
          </Box>
        ))}
      </Box>

      <Box data-theme-surface="panel" sx={{ mt: 2, border: "1px solid", borderColor: "divider" }}>
        <Box
          sx={{
            px: 2,
            py: 1.25,
            borderBottom: "1px solid",
            borderColor: "divider",
          }}
        >
          <Typography variant="subtitle2">
            {t(`${ROOT}.recentDeliveries`)}
          </Typography>
        </Box>
        {recent.length ? (
          recent.map((delivery) => (
            <Box
              key={delivery.id}
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "1.4fr 1fr auto" },
                gap: 1,
                px: 2,
                py: 1.1,
                borderBottom: "1px solid",
                borderColor: "divider",
                "&:last-child": { borderBottom: 0 },
              }}
            >
              <Typography variant="body2">{delivery.player_name}</Typography>
              <Typography variant="caption" color="text.secondary">
                {delivery.campaignTitle || "—"}
              </Typography>
              <Typography
                variant="caption"
                color={
                  delivery.status === "failed" ? "error.main" : "text.secondary"
                }
              >
                {t(`${ROOT}.deliveryStatus.${delivery.status}`)}
              </Typography>
            </Box>
          ))
        ) : (
          <Typography variant="body2" color="text.secondary" sx={{ p: 2 }}>
            {t(`${ROOT}.noRecentDeliveries`)}
          </Typography>
        )}
      </Box>
    </ConfigFormSection>
  );
}

export default function BroadcastCampaignWorkbench({
  config,
  activeCount,
  activeSection,
  onSectionChange,
  selectedCampaignId,
  onSelectCampaign,
  onAdd,
  onModeChange,
  onGlobalChange,
  onReset,
  onSave,
  hasChanges,
  isValid,
  saving,
  actionSaved,
  templatePicker,
  campaignEditor,
  deliveryStatus,
  lifecycleAvailable,
  lifecyclePanel,
}) {
  const { t } = useTranslation();
  const sections = [
    {
      id: "overview",
      label: t(`${ROOT}.overview`),
      description: t(`${ROOT}.overviewDescription`),
      status: "complete",
    },
    {
      id: "campaigns",
      label: t(`${ROOT}.campaignsSection`),
      description: t(`${ROOT}.campaignsDescription`),
      status: isValid ? "complete" : "error",
    },
    {
      id: "delivery",
      label: t(`${ROOT}.deliverySection`),
      description: t(`${ROOT}.deliveryDescription`),
      status: "complete",
    },
    ...(lifecycleAvailable
      ? [
          {
            id: "vip-lifecycle",
            label: t(`${ROOT}.vipLifecycle.title`),
            description: t(`${ROOT}.vipLifecycle.subtitle`),
            status: config.vip_lifecycle?.enabled ? "complete" : "pending",
          },
        ]
      : []),
    {
      id: "activity",
      label: t(`${ROOT}.activity`),
      description: t(`${ROOT}.activityDescriptionShort`),
      status: "complete",
    },
  ];

  const mode = campaignMode(config);
  const modeControl = (
    <ToggleButtonGroup
      data-testid="campaign-mode-toggle"
      value={mode}
      exclusive
      onChange={(_, value) => value && onModeChange(value)}
      aria-label={t(`${ROOT}.operationMode`)}
      size="small"
      sx={{
        width: { xs: "100%", md: 420 },
        maxWidth: "100%",
        "& .MuiToggleButton-root": {
          flex: "1 1 0",
          minWidth: 0,
          minHeight: 44,
          px: { xs: 1, sm: 2 },
        },
      }}
    >
      <ToggleButton value="off">{t(`${ROOT}.modeOff`)}</ToggleButton>
      <ToggleButton value="sequence">{t(`${ROOT}.modeSequence`)}</ToggleButton>
      <ToggleButton value="random">{t(`${ROOT}.modeRandom`)}</ToggleButton>
    </ToggleButtonGroup>
  );

  return (
    <SeedingWorkbenchLayout
      testId="campaign-workbench"
      eyebrow={t(`${ROOT}.eyebrowExtended`)}
      title={t(`${ROOT}.title`)}
      description={t(`${ROOT}.subtitle`)}
      status={t(config.enabled ? `${ROOT}.active` : `${ROOT}.paused`)}
      statusColor={config.enabled ? "success" : "default"}
      headerActions={modeControl}
      sections={sections}
      activeSection={activeSection}
      onSectionChange={onSectionChange}
      navigationLabel={t(`${ROOT}.sectionNavigation`)}
      mobileNavigationLabel={t(`${ROOT}.sectionNavigation`)}
      summary={<BroadcastSummary config={config} activeCount={activeCount} />}
      actionBar={
        <ConfigActionBar
          dirty={hasChanges}
          dirtyLabel={t(`${ROOT}.unsavedChanges`)}
          result={
            actionSaved ? { kind: "success", title: t(`${ROOT}.saved`) } : null
          }
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
              id: "reset-campaigns",
              label: t(`${ROOT}.reset`),
              onClick: onReset,
              disabled: !hasChanges || saving,
            },
          ]}
          primaryAction={{
            label: saving ? t("common.loading") : t("common.save"),
            onClick: onSave,
            disabled: !hasChanges || !isValid || saving,
            loading: saving,
            startIcon: <CampaignOutlinedIcon fontSize="small" />,
          }}
        />
      }
    >
      {!isValid && (
        <Alert severity="warning">{t(`${ROOT}.invalidRange`)}</Alert>
      )}

      {activeSection === "overview" && (
        <ConfigFormSection
          plain
          id="campaign-overview"
          eyebrow={t(`${ROOT}.overview`)}
          title={t(`${ROOT}.overviewTitle`)}
          description={t(`${ROOT}.overviewDescriptionLong`)}
          icon={<DashboardOutlinedIcon />}
        >
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: { xs: "1fr", lg: "minmax(0, 1fr) auto" },
              gap: 2,
              alignItems: "end",
            }}
          >
            <Alert severity={config.enabled ? "success" : "info"}>
              {t(
                config.enabled
                  ? `${ROOT}.activeModeDescription`
                  : `${ROOT}.pausedModeDescription`
              )}
            </Alert>
            <Button variant="outlined" startIcon={<AddIcon />} onClick={onAdd}>
              {t(`${ROOT}.add`)}
            </Button>
          </Box>
          {templatePicker && <Box sx={{ mt: 2 }}>{templatePicker}</Box>}
          <Alert severity="info" sx={{ mt: 2 }}>
            {t(`${ROOT}.priorityNote`)}
          </Alert>
        </ConfigFormSection>
      )}

      {activeSection === "campaigns" && (
        <Box data-theme-surface="panel"
          className="wardogs-campaign-workspace"
          sx={{
            display: "grid",
            gridTemplateColumns: {
              xs: "minmax(0, 1fr)",
              md: "280px minmax(0, 1fr)",
            },
            border: "1px solid",
            borderColor: "divider",
            minHeight: { md: 540 },
          }}
        >
          <CampaignList
            campaigns={config.messages}
            selectedCampaignId={selectedCampaignId}
            onSelect={onSelectCampaign}
            onAdd={onAdd}
          />
          <Box sx={{ minWidth: 0 }}>{campaignEditor}</Box>
        </Box>
      )}

      {activeSection === "delivery" && (
        <DeliverySettings config={config} onChange={onGlobalChange} />
      )}

      {activeSection === "vip-lifecycle" && lifecyclePanel}

      {activeSection === "activity" && (
        <Stack spacing={3}>
          <BroadcastActivity status={deliveryStatus?.broadcast} />
          {config.messages.some((item) => item.delivery_mode === "player_message") && <ActivityPanel deliveryStatus={deliveryStatus} />}
        </Stack>
      )}
    </SeedingWorkbenchLayout>
  );
}
