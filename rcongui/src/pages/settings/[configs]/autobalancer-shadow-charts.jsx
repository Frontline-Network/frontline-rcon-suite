import i18n from "@/i18n";
import { translateOperatorMessage } from "@/i18n/operator-messages";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { ChartsReferenceLine } from "@mui/x-charts/ChartsReferenceLine";
import { LineChart } from "@mui/x-charts/LineChart";
import TeamBalanceBar from "@/components/shared/TeamBalanceBar";

const PHASE_LABELS = () => ({
  idle: i18n.t("settingsPanels.autobalancer.idle"),
  observing: i18n.t("settingsPanels.autobalancer.observing"),
  volunteer: i18n.t("settingsPanels.autobalancer.volunteer"),
  proposed: i18n.t("settingsPanels.autobalancer.shadowProposed"),
  armed: i18n.t("settingsPanels.autobalancer.candidateQueued"),
  verifying: i18n.t("settingsPanels.autobalancer.verifying"),
  cooldown: i18n.t("settingsPanels.autobalancer.newStabilityCheck"),
  blocked: i18n.t("settingsPanels.autobalancer.blocked"),
});

const UNRELIABLE_REASONS = [
  "Spielerdaten sind unvollständig",
  "Teamzählungen stimmen nicht überein",
  "Kartendaten sind nicht stabil",
  "Autobalancer-Dienst liefert keinen aktuellen Status",
];

const REJECTION_LABELS = () => ({
  squad_should_stay: i18n.t("settingsPanels.autobalancer.keepSquad"),
  critical_role: i18n.t("settingsPanels.autobalancer.criticalRole"),
  recent_join_or_move: i18n.t("settingsPanels.autobalancer.joinSquadTime"),
  better_candidate: i18n.t("settingsPanels.autobalancer.betterCandidate"),
  skill_balance: i18n.t("settingsPanels.autobalancer.skillBalance"),
  wrong_team_counts: i18n.t("settingsPanels.autobalancer.teamCounting"),
  other: i18n.t("settingsPanels.autobalancer.otherReason"),
});

const STRATEGY_LABELS = () => ({
  "squad-first": i18n.t("settingsPanels.autobalancer.squadFirst"),
  "balanced-v2": i18n.t("settingsPanels.autobalancer.balancedV2"),
  "skill-first": i18n.t("settingsPanels.autobalancer.skillFirstDiagnostic"),
});

const ChartShell = ({ title, subtitle, children }) => (
  <Card variant="outlined" sx={{ minWidth: 0 }}>
    <CardContent>
      <Typography variant="h6" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {subtitle}
      </Typography>
      <Box sx={{ mt: 1 }}>{children}</Box>
    </CardContent>
  </Card>
);

const LiveBalance = ({ status, targetDifference, minimumPlayers }) => {
  const theme = useTheme();
  const counts = status?.team_counts || {};
  const allies = counts.allies;
  const axis = counts.axis;
  const teamLabels = status?.team_labels || {
    allies: "Allies",
    axis: "Axis",
  };
  const hasCounts = Number.isFinite(allies) && Number.isFinite(axis);
  const reasons = status?.block_reasons || [];
  const updatedAt = status?.updated_at ? new Date(status.updated_at) : null;
  const stale =
    !updatedAt ||
    Number.isNaN(updatedAt.getTime()) ||
    Date.now() - updatedAt.getTime() > 20_000;
  const unreliable =
    stale ||
    !hasCounts ||
    reasons.some((reason) => UNRELIABLE_REASONS.includes(reason));
  const difference = hasCounts ? Math.abs(allies - axis) : null;
  const balanced = !unreliable && difference <= targetDifference;
  const inactive = reasons.includes("Mindestspielerzahl ist nicht erreicht");

  const state = unreliable
    ? {
        label: stale
          ? i18n.t("settingsPanels.autobalancer.noCurrentLiveData")
          : i18n.t("settingsPanels.autobalancer.notReliable"),
        color: "warning",
        border: theme.palette.warning.main,
        background: theme.palette.warning.main + "12",
      }
    : balanced
    ? {
        label: i18n.t("settingsPanels.autobalancer.balanced"),
        color: "success",
        border: theme.palette.success.main,
        background: theme.palette.success.main + "12",
      }
    : {
        label: i18n.t("settingsPanels.autobalancer.unbalanced"),
        color: "error",
        border: theme.palette.error.main,
        background: theme.palette.error.main + "12",
      };

  return (
    <Box
      sx={{
        mt: 2,
        p: { xs: 2, md: 3 },
        border: 2,
        borderColor: state.border,
        borderRadius: 2,
        backgroundColor: state.background,
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        spacing={2}
      >
        <Box>
          <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
            <Chip
              color={state.color}
              label={state.label}
              sx={{ fontWeight: 800, letterSpacing: 0.5 }}
            />
            <Chip
              size="small"
              variant="outlined"
              label={i18n.t("settingsPanels.autobalancer.liveEveryFive")}
            />
            {updatedAt && !Number.isNaN(updatedAt.getTime()) && (
              <Typography variant="caption" color="text.secondary">
                {i18n.t("settingsPanels.autobalancer.updated")}{" "}
                {updatedAt.toLocaleTimeString(i18n.resolvedLanguage)}
              </Typography>
            )}
          </Stack>
          {unreliable && (
            <Typography variant="body1" sx={{ mt: 1 }}>
              {i18n.t("settingsPanels.autobalancer.incompleteSnapshotHelp")}
            </Typography>
          )}
        </Box>
        <Stack alignItems={{ md: "flex-end" }} spacing={0.5}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            {unreliable
              ? i18n.t("settingsPanels.autobalancer.noDecision")
              : i18n.t("settingsPanels.autobalancer.switchesNeeded", {
                  v0: status?.required_switches ?? 0,
                })}
          </Typography>
          <Typography color="text.secondary">
            {PHASE_LABELS()[status?.phase] ||
              status?.phase ||
              i18n.t("settingsPanels.autobalancer.noLiveStatus")}
          </Typography>
          {inactive && (
            <Typography variant="caption" color="text.secondary">
              {i18n.t("settingsPanels.autobalancer.below")} {minimumPlayers}{" "}
              {i18n.t("settingsPanels.autobalancer.inactivePlayersSuffix")}
            </Typography>
          )}
        </Stack>
      </Stack>

      <TeamBalanceBar
        allies={allies}
        axis={axis}
        alliesLabel={teamLabels.allies}
        axisLabel={teamLabels.axis}
        targetDifference={targetDifference}
      />

      {status?.team_ratings && (
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.teamRatingValue", {
              v0: teamLabels.allies,
              v1: status.team_ratings.allies ?? "–",
              v2: teamLabels.axis,
              v3: status.team_ratings.axis ?? "–",
            })}
          />
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.dataConfidenceValue", {
              v0: Math.round((status.data_confidence || 0) * 100),
            })}
          />
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.strategyValue", {
              v0: STRATEGY_LABELS()[status.strategy] || status.strategy || "–",
            })}
          />
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.ratingModelValue", {
              v0: status.rating_model_version || "legacy",
            })}
          />
        </Stack>
      )}

      {(status?.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning" sx={{ mt: 1 }}>
          {translateOperatorMessage(warning, i18n.t)}
        </Alert>
      ))}

      {unreliable && (
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
          {stale && (
            <Chip
              size="small"
              color="warning"
              label={i18n.t("settingsPanels.autobalancer.staleMeasurement")}
            />
          )}
          {reasons
            .filter((reason) => UNRELIABLE_REASONS.includes(reason))
            .map((reason) => (
              <Chip
                key={reason}
                size="small"
                color="warning"
                label={translateOperatorMessage(reason, i18n.t)}
              />
            ))}
        </Stack>
      )}
    </Box>
  );
};

const DifferenceTimeline = ({ timeline, targetDifference, teamLabels }) => {
  const theme = useTheme();
  const points = (timeline || [])
    .map((sample) => ({
      time: new Date(sample.updated_at),
      difference: sample.team_difference,
      roundId: sample.round_id,
    }))
    .filter(
      (point) =>
        !Number.isNaN(point.time.getTime()) && Number.isFinite(point.difference)
    );

  if (points.length < 8) {
    return (
      <Alert severity="info">
        {i18n.t("settingsPanels.autobalancer.collectingTimeline")}{" "}
        {points.length}
        {i18n.t("settingsPanels.autobalancer.timelineProgress")}
      </Alert>
    );
  }

  const maximum = Math.max(
    targetDifference + 2,
    ...points.map((point) => Math.abs(point.difference))
  );
  return (
    <LineChart
      height={300}
      margin={{ left: 50, right: 20, top: 20, bottom: 30 }}
      xAxis={[
        {
          data: points.map((point) => point.time),
          scaleType: "time",
          valueFormatter: (value) =>
            new Intl.DateTimeFormat(i18n.resolvedLanguage, {
              hour: "2-digit",
              minute: "2-digit",
            }).format(value),
        },
      ]}
      yAxis={[
        {
          min: -maximum,
          max: maximum,
          tickMinStep: 1,
          valueFormatter: (value) => `${value > 0 ? "+" : ""}${value}`,
        },
      ]}
      series={[
        {
          label: i18n.t("settingsPanels.autobalancer.teamDifference"),
          data: points.map((point) => point.difference),
          color: theme.palette.info.main,
          showMark: points.length < 40,
          curve: "linear",
          valueFormatter: (value) =>
            value > 0
              ? `${teamLabels.allies} +${value}`
              : value < 0
              ? `${teamLabels.axis} +${Math.abs(value)}`
              : i18n.t("settingsPanels.autobalancer.tie"),
        },
      ]}
      grid={{ horizontal: true }}
    >
      <ChartsReferenceLine
        y={targetDifference}
        label={i18n.t("settingsPanels.autobalancer.positiveLimit", {
          v0: targetDifference,
        })}
        lineStyle={{
          stroke: theme.palette.warning.main,
          strokeDasharray: "6 4",
        }}
      />
      <ChartsReferenceLine
        y={-targetDifference}
        label={i18n.t("settingsPanels.autobalancer.negativeLimit", {
          v0: targetDifference,
        })}
        lineStyle={{
          stroke: theme.palette.warning.main,
          strokeDasharray: "6 4",
        }}
      />
      <ChartsReferenceLine
        y={0}
        lineStyle={{ stroke: theme.palette.text.secondary, strokeWidth: 1.5 }}
      />
    </LineChart>
  );
};

const DistributionCharts = ({ summary }) => {
  const theme = useTheme();
  const tiers = Object.entries(summary?.protection_tiers || {});
  const reviews = [
    {
      label: i18n.t("settingsPanels.autobalancer.acceptable"),
      value: summary?.accepted || 0,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.rejected"),
      value: summary?.rejected || 0,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.open"),
      value: summary?.pending_review || 0,
    },
  ];
  const rejectionReasons = Object.entries(summary?.rejection_categories || {});

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
        mt: 2,
      }}
    >
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.selectedTiers")}
        subtitle={i18n.t("settingsPanels.autobalancer.selectedTiersHelp")}
      >
        {tiers.length ? (
          <BarChart
            height={260}
            xAxis={[
              {
                scaleType: "band",
                data: tiers.map(([tier]) =>
                  i18n.t("settingsPanels.autobalancer.tierValue", { v0: tier })
                ),
              },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                data: tiers.map(([, count]) => count),
                label: i18n.t("settingsPanels.autobalancer.proposals"),
                color: theme.palette.info.main,
                valueFormatter: (value) =>
                  i18n.t("settingsPanels.autobalancer.proposalCount", {
                    v0: value,
                  }),
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">
            {i18n.t("settingsPanels.autobalancer.noShadowProposals")}
          </Alert>
        )}
      </ChartShell>

      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.reviews")}
        subtitle={i18n.t("settingsPanels.autobalancer.reviewsHelp")}
      >
        {summary?.proposals ? (
          <BarChart
            height={260}
            xAxis={[
              { scaleType: "band", data: reviews.map((item) => item.label) },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                data: reviews.map((item) => item.value),
                label: i18n.t("settingsPanels.autobalancer.proposals"),
                color: theme.palette.success.main,
                valueFormatter: (value) =>
                  i18n.t("settingsPanels.autobalancer.proposalCount", {
                    v0: value,
                  }),
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">
            {i18n.t("settingsPanels.autobalancer.noReviews")}
          </Alert>
        )}
      </ChartShell>

      {rejectionReasons.length > 0 && (
        <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
          <ChartShell
            title={i18n.t("settingsPanels.autobalancer.rejectionReasons")}
            subtitle={i18n.t(
              "settingsPanels.autobalancer.rejectionReasonsHelp"
            )}
          >
            <BarChart
              layout="horizontal"
              height={Math.max(240, rejectionReasons.length * 48)}
              yAxis={[
                {
                  scaleType: "band",
                  data: rejectionReasons.map(
                    ([reason]) => REJECTION_LABELS()[reason] || reason
                  ),
                },
              ]}
              xAxis={[{ min: 0, tickMinStep: 1 }]}
              series={[
                {
                  data: rejectionReasons.map(([, count]) => count),
                  label: i18n.t("settingsPanels.autobalancer.rejections"),
                  color: theme.palette.warning.main,
                  valueFormatter: (value) =>
                    i18n.t("settingsPanels.autobalancer.rejectionCount", {
                      v0: value,
                    }),
                },
              ]}
              grid={{ vertical: true }}
            />
          </ChartShell>
        </Box>
      )}
    </Box>
  );
};

const AutobalancerShadowCharts = ({ status, timeline, summary, config }) => {
  useTranslation();
  const targetDifference = config?.target_difference ?? 2;
  const teamLabels = status?.team_labels || {
    allies: "Allies",
    axis: "Axis",
  };
  return (
    <>
      <LiveBalance
        status={status}
        targetDifference={targetDifference}
        minimumPlayers={config?.minimum_players ?? 40}
      />
      <Box sx={{ mt: 2 }}>
        <ChartShell
          title={i18n.t("settingsPanels.autobalancer.differenceTimeline")}
          subtitle={i18n.t(
            "settingsPanels.autobalancer.differenceTimelineHelp",
            { v0: teamLabels.allies, v1: teamLabels.axis }
          )}
        >
          <DifferenceTimeline
            timeline={timeline}
            targetDifference={targetDifference}
            teamLabels={teamLabels}
          />
        </ChartShell>
      </Box>
      <DistributionCharts summary={summary} />
    </>
  );
};

export default AutobalancerShadowCharts;
import "@/i18n/register-settings-panels";
