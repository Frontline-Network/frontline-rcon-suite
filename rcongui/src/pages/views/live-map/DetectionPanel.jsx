import { Box, Button, Chip, Stack, Typography } from "@mui/material";
import { useTranslation } from "react-i18next";
import { translateOperatorMessage } from "@/i18n/operator-messages";

const signalText = (signal, t) => {
  if (signal.kind === "kill_rate")
    return `${t(signal.category)}: ${signal.kills} · ${signal.kpm} KPM (≥ ${
      signal.threshold
    })`;
  if (signal.kind === "kill_burst")
    return `${t("killBurst")}: ${signal.kills} / ${signal.seconds} s · ${
      signal.unique_victims
    } ${t("uniqueVictims")}`;
  if (signal.kind === "repeated_target")
    return `${t("repeatedTarget")}: ${signal.kills}× ${
      signal.victim_name || signal.victim
    }`;
  return `${t("movementAnomaly")}: ${signal.count}× · ${
    signal.maximum_mps
  } m/s`;
};

export default function DetectionPanel({
  detections,
  detail,
  detailLoading,
  selected,
  canCases,
  canArchive,
  permissions,
  canUse,
  mutation,
  onReview,
  onReplay,
  onDetails,
  onArchive,
  t,
}) {
  const { t: operatorT, i18n } = useTranslation();
  const visible = (detections || []).filter(
    (item) => !selected || item.player_id === selected
  );
  return (
    <Box data-theme-surface="panel"
      sx={{
        border: 1,
        borderColor: "divider",
        bgcolor: "background.paper",
        p: 1.5,
      }}
    >
      <Typography fontWeight={800}>{t("playerReview")}</Typography>
      <Typography variant="caption" color="text.secondary">
        {t("detectionDisclaimer")}
      </Typography>
      {!visible.length && (
        <Typography sx={{ mt: 1 }} variant="body2">
          {t("noDetections")}
        </Typography>
      )}
      {visible.map((item) => {
        const evidence = item.evidence || item;
        const expanded = detail?.id === item.id;
        const metrics = detail?.evidence?.metrics;
        const profile = detail?.profile_context;
        const bans = profile?.steam_bans || {};
        return (
          <Box
            key={item.id}
            sx={{
              borderTop: 2,
              borderColor:
                item.severity === "high"
                  ? "error.main"
                  : item.severity === "review"
                  ? "warning.main"
                  : "divider",
              mt: 1.5,
              pt: 1.5,
            }}
          >
            <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
              <Typography fontWeight={800}>
                {item.player_name || item.player_id}
              </Typography>
              <Chip
                size="small"
                variant="outlined"
                color={
                  item.severity === "high"
                    ? "error"
                    : item.severity === "review"
                    ? "warning"
                    : "default"
                }
                label={t(item.severity)}
              />
            </Stack>
            {(evidence.signals || []).map((signal, index) => (
              <Typography
                key={`${signal.kind}-${index}`}
                variant="caption"
                display="block"
              >
                {signalText(signal, t)}
              </Typography>
            ))}
            <Typography
              variant="caption"
              color="text.secondary"
              display="block"
              sx={{ mt: 0.5 }}
            >
              {t("humanReviewOnly")}
            </Typography>
            <Stack direction="row" flexWrap="wrap" gap={0.5} sx={{ mt: 1 }}>
              <Button
                size="small"
                aria-pressed={expanded}
                onClick={() => onDetails(item)}
              >
                {t(expanded ? "hideDetails" : "showDetails")}
              </Button>
              <Button size="small" onClick={() => onReplay(item)}>
                {t("inspectReplay")}
              </Button>
              {canCases && canUse(permissions, "can_claim_admin_incidents") && (
                <Button
                  size="small"
                  disabled={mutation.isPending}
                  onClick={() => onReview(item, "claim")}
                >
                  {t("claim")}
                </Button>
              )}
              {canCases &&
                canUse(permissions, "can_resolve_admin_incidents") && (
                  <Button
                    size="small"
                    disabled={mutation.isPending}
                    onClick={() => onReview(item, "dismiss")}
                  >
                    {t("dismiss")}
                  </Button>
                )}
              {canArchive && (
                <Button size="small" onClick={() => onArchive(item)}>
                  {t("saveInvestigation")}
                </Button>
              )}
            </Stack>
            {detailLoading && !detail && (
              <Typography variant="caption">{t("loadingDetails")}</Typography>
            )}
            {expanded && (
              <Box data-theme-surface="panel" sx={{ mt: 1, p: 1, border: 1, borderColor: "divider" }}>
                {metrics && (
                  <Typography variant="caption" display="block">
                    {t("detectionMetrics")
                      .replace("{kills}", metrics.kills ?? 0)
                      .replace(
                        "{minutes}",
                        Math.max(
                          1,
                          Math.round((metrics.observed_seconds || 0) / 60)
                        )
                      )
                      .replace("{victims}", metrics.unique_victims ?? 0)}
                  </Typography>
                )}
                <Typography variant="caption" display="block">
                  {t(
                    detail.evidence?.data_quality?.metric_positions
                      ? "metricPositionsAvailable"
                      : "metricPositionsUnavailable"
                  )}
                </Typography>
                {(detail.evidence?.context || []).map((line) => (
                  <Typography
                    key={line}
                    variant="caption"
                    color="text.secondary"
                    display="block"
                  >
                    {translateOperatorMessage(line, operatorT)}
                  </Typography>
                ))}
                <Typography
                  fontWeight={800}
                  variant="caption"
                  display="block"
                  sx={{ mt: 1 }}
                >
                  {t("previousRoundContext")}
                </Typography>
                {(detail.previous_24h || []).length ? (
                  (detail.previous_24h || []).map((previous) => (
                    <Typography
                      key={previous.id}
                      variant="caption"
                      display="block"
                    >
                      {new Date(previous.last_at * 1000).toLocaleString(i18n.resolvedLanguage)} ·{" "}
                      {t(previous.severity)}
                    </Typography>
                  ))
                ) : (
                  <Typography variant="caption" color="text.secondary">
                    {t("noPreviousRoundContext")}
                  </Typography>
                )}
                {profile && (
                  <Box sx={{ mt: 1 }}>
                    <Typography
                      fontWeight={800}
                      variant="caption"
                      display="block"
                    >
                      {t("banContext")}
                    </Typography>
                    <Typography variant="caption" display="block">
                      {profile.has_bans
                        ? t("banSummary")
                            .replace("{source}", profile.source || "Steam")
                            .replace("{vac}", bans.NumberOfVACBans ?? 0)
                            .replace("{game}", bans.NumberOfGameBans ?? 0)
                            .replace("{days}", bans.DaysSinceLastBan ?? "–")
                        : t("noBanContext")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("contextNotScored")}
                    </Typography>
                  </Box>
                )}
              </Box>
            )}
          </Box>
        );
      })}
    </Box>
  );
}
