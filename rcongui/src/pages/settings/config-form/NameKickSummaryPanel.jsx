import { Box, Stack, Typography } from "@mui/material";
import ExitToAppOutlinedIcon from "@mui/icons-material/ExitToAppOutlined";
import NotificationsNoneOutlinedIcon from "@mui/icons-material/NotificationsNoneOutlined";
import RuleOutlinedIcon from "@mui/icons-material/RuleOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import { useTranslation } from "react-i18next";

const ROOT = "settings.configForms.nameKicks.workbench.summary";

function SummarySegment({ icon, eyebrow, value, detail, tone, last = false }) {
  return (
    <Box
      component="section"
      sx={{
        minWidth: 0,
        px: { xs: 1.75, md: 2.25 },
        py: { xs: 1.6, md: 1.9 },
        borderRight: { xs: 0, md: last ? 0 : "1px solid" },
        borderBottom: { xs: last ? 0 : "1px solid", md: 0 },
        borderColor: "divider",
      }}
    >
      <Stack direction="row" spacing={1.35} alignItems="flex-start">
        <Box
          aria-hidden="true"
          sx={{
            display: "grid",
            placeItems: "center",
            width: 32,
            height: 32,
            flex: "0 0 auto",
            color: tone || "primary.main",
            bgcolor: "action.selected",
            border: "1px solid",
            borderColor: "divider",
          }}
        >
          {icon}
        </Box>
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ display: "block", letterSpacing: "0.05em" }}
          >
            {eyebrow}
          </Typography>
          <Typography
            variant="subtitle1"
            component="p"
            sx={{ color: tone || "text.primary", mt: 0.15 }}
          >
            {value}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{
              display: "-webkit-box",
              mt: 0.35,
              overflow: "hidden",
              WebkitBoxOrient: "vertical",
              WebkitLineClamp: 2,
            }}
          >
            {detail}
          </Typography>
        </Box>
      </Stack>
    </Box>
  );
}

export default function NameKickSummaryPanel({ data = {} }) {
  const { t } = useTranslation();
  const ruleCount = Array.isArray(data.regular_expressions)
    ? data.regular_expressions.filter((item) => String(item || "").trim())
        .length
    : 0;
  const exemptionCount = Array.isArray(data.whitelist_flags)
    ? data.whitelist_flags.filter((item) => String(item || "").trim()).length
    : 0;
  const kickReason = String(data.kick_reason || "").trim();
  const webhookConfigured = /^https?:\/\//i.test(
    String(data.discord_webhook_url || "").trim()
  );

  return (
    <Box
      component="aside"
      aria-label={t(`${ROOT}.title`)}
      sx={{
        bgcolor: "background.paper",
        border: "1px solid",
        borderColor: "divider",
        overflow: "hidden",
      }}
    >
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            md: "0.8fr 1.25fr 0.8fr 0.9fr",
          },
        }}
      >
        <SummarySegment
          icon={<RuleOutlinedIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.filter`)}
          value={
            ruleCount
              ? t(`${ROOT}.rules`, { count: ruleCount })
              : t(`${ROOT}.noRules`)
          }
          detail={
            ruleCount ? t(`${ROOT}.filterActive`) : t(`${ROOT}.filterInactive`)
          }
          tone={ruleCount ? "success.main" : "warning.main"}
        />
        <SummarySegment
          icon={<ExitToAppOutlinedIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.effect`)}
          value={t(`${ROOT}.kickOnMatch`)}
          detail={kickReason || t(`${ROOT}.reasonMissing`)}
          tone={kickReason ? "primary.main" : "warning.main"}
        />
        <SummarySegment
          icon={<ShieldOutlinedIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.exemptions`)}
          value={
            exemptionCount
              ? t(`${ROOT}.flags`, { count: exemptionCount })
              : t(`${ROOT}.noFlags`)
          }
          detail={t(`${ROOT}.exemptionsHelp`)}
        />
        <SummarySegment
          icon={<NotificationsNoneOutlinedIcon fontSize="small" />}
          eyebrow={t(`${ROOT}.audit`)}
          value={
            webhookConfigured
              ? t(`${ROOT}.webhookActive`)
              : t(`${ROOT}.webhookInactive`)
          }
          detail={
            webhookConfigured
              ? t(`${ROOT}.webhookActiveHelp`)
              : t(`${ROOT}.webhookInactiveHelp`)
          }
          tone={webhookConfigured ? "success.main" : "text.secondary"}
          last
        />
      </Box>
    </Box>
  );
}
