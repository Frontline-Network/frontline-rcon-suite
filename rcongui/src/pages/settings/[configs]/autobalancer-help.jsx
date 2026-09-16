import i18n from "@/i18n";
import { useTranslation } from "react-i18next";
import { Alert, Box, Chip, Stack, Typography } from "@mui/material";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";

const MODE_INFO = () => ({
  disabled: {
    label: i18n.t("settingsPanels.autobalancer.off"),
    severity: "info",
    text: i18n.t("settingsPanels.autobalancer.offHelp"),
  },
  shadow: {
    label: i18n.t("settingsPanels.autobalancer.observe"),
    severity: "info",
    text: i18n.t("settingsPanels.autobalancer.observeHelp"),
  },
  manual: {
    label: i18n.t("settingsPanels.autobalancer.manual"),
    severity: "warning",
    text: i18n.t("settingsPanels.autobalancer.manualHelp"),
  },
  auto: {
    label: i18n.t("settingsPanels.autobalancer.automatic"),
    severity: "warning",
    text: i18n.t("settingsPanels.autobalancer.automaticHelp"),
  },
});

const SummaryItem = ({ icon, label, value, detail }) => (
  <Box sx={{ p: 1.5, minWidth: 0 }}>
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 0.5 }}>
      {icon}
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
    </Stack>
    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
      {value}
    </Typography>
    <Typography variant="caption" color="text.secondary">
      {detail}
    </Typography>
  </Box>
);

const AutobalancerHelp = ({ config = {} }) => {
  useTranslation();
  const mode = MODE_INFO()[config.mode] || MODE_INFO().disabled;
  const targetDifference = config.target_difference ?? 2;
  const stableSeconds = config.stable_difference_seconds ?? 45;
  const squadSwitches = config.coordinated_squad_switches_enabled === true;
  const individualFallback = config.allow_individual_squad_fallback !== false;

  return (
    <Stack spacing={1.5} sx={{ mt: 2, mb: 2 }}>
      <Alert severity={mode.severity} variant="outlined">
        <strong>
          {i18n.t("settingsPanels.autobalancer.operatingMode")} {mode.label}.
        </strong>{" "}
        {mode.text}
      </Alert>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          "& > div + div": {
            borderLeft: { md: "1px solid" },
            borderTop: { xs: "1px solid", md: 0 },
            borderColor: "divider",
          },
        }}
      >
        <SummaryItem
          icon={<BalanceOutlinedIcon fontSize="small" color="primary" />}
          label={i18n.t("settingsPanels.autobalancer.intervention")}
          value={i18n.t("settingsPanels.autobalancer.playerThreshold", {
            v0: targetDifference,
          })}
          detail={i18n.t("settingsPanels.autobalancer.stabilityThreshold", {
            v0: stableSeconds,
          })}
        />
        <SummaryItem
          icon={<GroupsOutlinedIcon fontSize="small" color="primary" />}
          label="Squads"
          value={
            squadSwitches
              ? i18n.t("settingsPanels.autobalancer.squadSwitchAllowed")
              : i18n.t("settingsPanels.autobalancer.proposalOnly")
          }
          detail={
            squadSwitches
              ? i18n.t("settingsPanels.autobalancer.squadSwitchHelp")
              : i18n.t("settingsPanels.autobalancer.squadProposalHelp")
          }
        />
        <SummaryItem
          icon={<ShieldOutlinedIcon fontSize="small" color="primary" />}
          label="Fallback"
          value={
            individualFallback
              ? i18n.t("settingsPanels.autobalancer.individualsAllowed")
              : i18n.t("settingsPanels.autobalancer.squadsTogether")
          }
          detail={i18n.t("settingsPanels.autobalancer.protectedSquads")}
        />
      </Box>

      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
        <Chip
          label={i18n.t("settingsPanels.autobalancer.liveData")}
          size="small"
          color="info"
        />
        <Chip
          label={i18n.t("settingsPanels.autobalancer.currentServer")}
          size="small"
          variant="outlined"
        />
        <Chip
          label={i18n.t("settingsPanels.autobalancer.squadNotice")}
          size="small"
          variant="outlined"
        />
      </Stack>

      {squadSwitches && (
        <Alert severity="warning" variant="outlined">
          {i18n.t("settingsPanels.autobalancer.squadRecreation")}
        </Alert>
      )}
    </Stack>
  );
};

export default AutobalancerHelp;
import "@/i18n/register-settings-panels";
