import { Box, ButtonBase, Chip, Stack, Typography } from "@mui/material";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import CampaignOutlinedIcon from "@mui/icons-material/CampaignOutlined";
import DashboardOutlinedIcon from "@mui/icons-material/DashboardOutlined";
import ExitToAppOutlinedIcon from "@mui/icons-material/ExitToAppOutlined";
import GavelOutlinedIcon from "@mui/icons-material/GavelOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import RedeemOutlinedIcon from "@mui/icons-material/RedeemOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import ScheduleOutlinedIcon from "@mui/icons-material/ScheduleOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import TuneOutlinedIcon from "@mui/icons-material/TuneOutlined";
import VisibilityOutlinedIcon from "@mui/icons-material/VisibilityOutlined";
import WarningAmberOutlinedIcon from "@mui/icons-material/WarningAmberOutlined";
import BadgeOutlinedIcon from "@mui/icons-material/BadgeOutlined";
import DnsOutlinedIcon from "@mui/icons-material/DnsOutlined";
import KeyOutlinedIcon from "@mui/icons-material/KeyOutlined";
import LockOutlinedIcon from "@mui/icons-material/LockOutlined";
import QueryStatsOutlinedIcon from "@mui/icons-material/QueryStatsOutlined";
import SpeedOutlinedIcon from "@mui/icons-material/SpeedOutlined";
import StorageOutlinedIcon from "@mui/icons-material/StorageOutlined";
import SyncOutlinedIcon from "@mui/icons-material/SyncOutlined";

const sectionIcons = {
  operation: DashboardOutlinedIcon,
  requirements: CheckCircleOutlineIcon,
  detection: VisibilityOutlinedIcon,
  rules: RuleOutlinedIcon,
  exemptions: ShieldOutlinedIcon,
  announcements: CampaignOutlinedIcon,
  warnings: CampaignOutlinedIcon,
  punishments: GavelOutlinedIcon,
  kick: ExitToAppOutlinedIcon,
  actions: GavelOutlinedIcon,
  reward: RedeemOutlinedIcon,
  messages: CampaignOutlinedIcon,
  schedule: ScheduleOutlinedIcon,
  notifications: NotificationsNoneOutlinedIcon,
  connections: DnsOutlinedIcon,
  telemetry: QueryStatsOutlinedIcon,
  identity: BadgeOutlinedIcon,
  access: LockOutlinedIcon,
  refresh: SyncOutlinedIcon,
  windowsStore: RuleOutlinedIcon,
  credentials: KeyOutlinedIcon,
  capacity: StorageOutlinedIcon,
  timing: ScheduleOutlinedIcon,
  thresholds: SpeedOutlinedIcon,
  exceptions: ShieldOutlinedIcon,
};

const getSectionLabel = (section) =>
  typeof section.label === "string" ? section.label : section.id;

function SeedingSectionNavigation({
  sections,
  activeSection,
  onSectionChange,
  label,
  mobileLabel,
}) {
  const selectedSection = sections.some(
    (section) => section.id === activeSection && !section.disabled
  )
    ? activeSection
    : sections.find((section) => !section.disabled)?.id;

  if (!sections.length) return null;

  return (
    <Box component="nav" aria-label={label} sx={{ minWidth: 0 }}>
      {mobileLabel && (
        <Typography
          variant="overline"
          color="text.secondary"
          sx={{ display: { xs: "block", sm: "none" }, px: 1.75, pt: 1.25 }}
        >
          {mobileLabel}
        </Typography>
      )}
      <Stack
        direction="row"
        sx={{
          minWidth: 0,
          overflowX: "auto",
          scrollbarWidth: "thin",
          borderBottom: "1px solid",
          borderColor: "divider",
          px: { xs: 0.75, sm: 1.25 },
          "&::-webkit-scrollbar": { height: 4 },
          "&::-webkit-scrollbar-thumb": {
            bgcolor: "divider",
            borderRadius: 0,
          },
        }}
      >
        {sections.map((section) => {
          const selected = section.id === selectedSection;
          const SectionIcon = sectionIcons[section.id] || TuneOutlinedIcon;
          const StatusIcon =
            section.status === "error"
              ? WarningAmberOutlinedIcon
              : section.status === "complete"
              ? CheckCircleOutlineIcon
              : SectionIcon;

          return (
            <ButtonBase
              key={section.id}
              component="button"
              disabled={section.disabled}
              onClick={() => {
                if (!selected) onSectionChange?.(section.id);
              }}
              aria-current={selected ? "step" : undefined}
              aria-label={
                section.description
                  ? `${getSectionLabel(section)}. ${section.description}`
                  : getSectionLabel(section)
              }
              sx={{
                position: "relative",
                flex: { xs: "0 0 auto", md: "1 1 0" },
                minWidth: { xs: 148, md: 0 },
                minHeight: 58,
                px: { xs: 1.25, md: 1.75 },
                py: 1.15,
                gap: 0.9,
                justifyContent: { xs: "flex-start", md: "center" },
                color:
                  section.status === "error"
                    ? "error.main"
                    : selected
                    ? "primary.main"
                    : "text.secondary",
                borderBottom: "2px solid",
                borderBottomColor: selected ? "primary.main" : "transparent",
                transition:
                  "color 140ms ease, background-color 140ms ease, border-color 140ms ease",
                "&:hover": { bgcolor: "action.hover", color: "text.primary" },
                "&.Mui-focusVisible": {
                  outline: "2px solid",
                  outlineColor: "primary.main",
                  outlineOffset: -2,
                },
              }}
            >
              <StatusIcon sx={{ fontSize: 18, flex: "0 0 auto" }} />
              <Box sx={{ minWidth: 0, textAlign: "left" }}>
                <Typography
                  variant="body2"
                  fontWeight={selected ? 850 : 700}
                  noWrap
                  sx={{ color: "inherit" }}
                >
                  {getSectionLabel(section)}
                </Typography>
                <Typography
                  variant="caption"
                  color="text.secondary"
                  noWrap
                  sx={{ display: { xs: "none", lg: "block" }, maxWidth: 180 }}
                >
                  {section.description}
                </Typography>
              </Box>
            </ButtonBase>
          );
        })}
      </Stack>
    </Box>
  );
}

export default function SeedingWorkbenchLayout({
  eyebrow,
  title,
  description,
  status,
  statusColor = "default",
  headerActions,
  sections = [],
  activeSection,
  onSectionChange,
  navigationLabel,
  mobileNavigationLabel,
  children,
  summary,
  actionBar,
  testId = "config-page-shell",
  sx,
  embedded = false,
}) {
  const hasNavigation = sections.length > 0;
  const hasSummary = Boolean(summary);

  return (
    <Box
      data-testid={testId}
      sx={{
        width: "100%",
        maxWidth: embedded ? "none" : 1460,
        mx: "auto",
        "& .MuiButton-root, & .MuiToggleButton-root, & .MuiOutlinedInput-root, & .MuiOutlinedInput-notchedOutline, & .MuiAlert-root, & .MuiChip-root":
          {
            borderRadius: 0,
          },
        ...sx,
      }}
    >
      <Box
        component="header"
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "minmax(0, 1fr)",
            md: "minmax(0, 1fr) auto",
          },
          gap: { xs: 1.5, md: 3 },
          alignItems: "end",
          mb: embedded ? 1 : 1.5,
        }}
      >
        {!embedded && (
          <Box sx={{ minWidth: 0 }}>
          {eyebrow && (
            <Typography
              variant="overline"
              color="primary.main"
              sx={{ display: "block", mb: 0.25, letterSpacing: "0.08em" }}
            >
              {eyebrow}
            </Typography>
          )}
          <Stack
            direction="row"
            spacing={1.25}
            alignItems="center"
            useFlexGap
            flexWrap="wrap"
          >
            <Typography
              component="h1"
              variant="h4"
              fontWeight={850}
              sx={{ letterSpacing: "-0.02em" }}
            >
              {title}
            </Typography>
            {status && (
              <Chip
                label={status}
                color={statusColor}
                size="small"
                sx={{ borderRadius: 0, fontWeight: 800 }}
              />
            )}
          </Stack>
          {description && (
            <Typography
              variant="body2"
              color="text.secondary"
              sx={{ mt: 0.65, maxWidth: 880, lineHeight: 1.55 }}
            >
              {description}
            </Typography>
          )}
          </Box>
        )}

        {headerActions && (
          <Box
            sx={{
              gridColumn: embedded ? "1 / -1" : undefined,
              justifySelf: { xs: "stretch", md: "end" },
              minWidth: { md: 300 },
              "& [data-testid='config-mode-toggle']": {
                alignItems: { xs: "stretch", md: "flex-end" },
              },
              "& .MuiToggleButtonGroup-root": {
                width: { xs: "100%", md: "auto" },
              },
              "& .MuiToggleButton-root": {
                flex: { xs: "1 1 0", md: "0 0 auto" },
              },
            }}
          >
            {headerActions}
          </Box>
        )}
      </Box>

      <Box
        sx={{
          border: "1px solid",
          borderTopColor: embedded ? "divider" : undefined,
          borderColor: "divider",
          borderRadius: 0,
          bgcolor: "background.paper",
          overflow: "hidden",
        }}
      >
        {hasNavigation && (
          <SeedingSectionNavigation
            sections={sections}
            activeSection={activeSection}
            onSectionChange={onSectionChange}
            label={navigationLabel}
            mobileLabel={mobileNavigationLabel}
          />
        )}

        {hasSummary && (
          <Box
            sx={{
              mx: { xs: 1.5, md: 2.5 },
              mt: { xs: 1.5, md: 2.25 },
              "& > aside": {
                width: "100%",
              },
            }}
          >
            {summary}
          </Box>
        )}

        <Stack
          component="section"
          sx={{
            minWidth: 0,
            px: { xs: 1.5, sm: 2, md: 2.5, lg: 3 },
            pt: { xs: 1.5, md: 2.25 },
            pb: { xs: 2, md: 3 },
          }}
          spacing={2}
        >
          {children}
        </Stack>
      </Box>

      {actionBar && (
        <Box
          sx={{
            mt: 1.25,
            "& > footer": {
              mx: "0 !important",
              borderTop: "1px solid !important",
              borderRadius: "0 !important",
              px: { xs: "12px !important", sm: "20px !important" },
              py: { xs: "10px !important", sm: "12px !important" },
              boxShadow: "0 -6px 24px rgba(0, 0, 0, 0.14)",
            },
          }}
        >
          {actionBar}
        </Box>
      )}
    </Box>
  );
}
