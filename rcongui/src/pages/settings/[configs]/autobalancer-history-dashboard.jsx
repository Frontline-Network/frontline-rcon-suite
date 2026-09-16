import i18n from "@/i18n";
import { translateOperatorMessage } from "@/i18n/operator-messages";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { cmd } from "@/utils/fetchUtils";

const percent = (value) =>
  value == null ? "–" : `${Math.round(value * 100)} %`;

const formatMap = (value) =>
  (value || i18n.t("settingsPanels.autobalancer.unknownMap"))
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const ROLE_LABELS = () => ({
  combat_infantry: "Combat Infantry",
  support: "Support / Engineer / Medic",
  leader: "Squad Leader",
  specialist: "Armor / Recon / Artillery / Mortar / Helicopter",
  legacy: i18n.t("settingsPanels.autobalancer.legacyNoRole"),
});

const STRATEGY_LABELS = () => ({
  "squad-first": i18n.t("settingsPanels.autobalancer.squadFirst"),
  "balanced-v2": i18n.t("settingsPanels.autobalancer.balancedV2"),
  "skill-first": i18n.t("settingsPanels.autobalancer.skillFirstDiagnostic"),
});

const Metric = ({ label, value, caption, color = "text.primary" }) => (
  <Card variant="outlined">
    <CardContent>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" color={color} sx={{ fontWeight: 800, mt: 0.5 }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {caption}
      </Typography>
    </CardContent>
  </Card>
);

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

const WeeklyBalanceChart = ({ weekly }) => {
  const theme = useTheme();
  const rows = (weekly || []).filter((row) => row.balanced_ratio != null);
  if (rows.length < 2) {
    return (
      <Alert severity="info">
        {i18n.t("settingsPanels.autobalancer.tooFewWeeks")}
      </Alert>
    );
  }
  return (
    <LineChart
      height={280}
      xAxis={[
        {
          scaleType: "time",
          data: rows.map((row) => new Date(row.week)),
          valueFormatter: (value) =>
            new Intl.DateTimeFormat(i18n.resolvedLanguage, {
              day: "2-digit",
              month: "2-digit",
            }).format(value),
        },
      ]}
      yAxis={[
        {
          min: 0,
          max: 100,
          valueFormatter: (value) => `${value} %`,
        },
      ]}
      series={[
        {
          label: i18n.t("settingsPanels.autobalancer.timeInRange"),
          data: rows.map((row) => Math.round(row.balanced_ratio * 100)),
          color: theme.palette.success.main,
          showMark: rows.length < 16,
          valueFormatter: (value) => `${value} %`,
        },
      ]}
      grid={{ horizontal: true }}
    />
  );
};

const WhatIfCharts = ({ rows }) => {
  const theme = useTheme();
  if (!rows?.length) return null;
  const labels = rows.map((row) => translateOperatorMessage(row.label, i18n.t));
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.whatIfBalanced")}
        subtitle={i18n.t("settingsPanels.autobalancer.whatIfHelp")}
      >
        <BarChart
          height={280}
          xAxis={[{ scaleType: "band", data: labels }]}
          yAxis={[
            { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
          ]}
          series={[
            {
              label: i18n.t("settingsPanels.autobalancer.balancedTime"),
              data: rows.map((row) =>
                row.balanced_time_ratio == null
                  ? null
                  : Math.round(row.balanced_time_ratio * 100)
              ),
              color: theme.palette.success.main,
              valueFormatter: (value) =>
                value == null
                  ? i18n.t("settingsPanels.autobalancer.notMeasurableLower")
                  : `${value} %`,
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.variantCost")}
        subtitle={i18n.t("settingsPanels.autobalancer.variantCostHelp")}
      >
        <BarChart
          height={280}
          xAxis={[{ scaleType: "band", data: labels }]}
          yAxis={[{ min: 0 }]}
          series={[
            {
              label: i18n.t("settingsPanels.autobalancer.switchesPerRound"),
              data: rows.map((row) => row.switches_per_round),
              color: theme.palette.warning.main,
              valueFormatter: (value) =>
                value == null
                  ? i18n.t("settingsPanels.autobalancer.notMeasurableLower")
                  : i18n.t(
                      "settingsPanels.autobalancer.switchesPerRoundValue",
                      { v0: value }
                    ),
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
    </Box>
  );
};

const BreakdownCharts = ({ summary }) => {
  const theme = useTheme();
  const quality = Object.entries(summary?.quality_levels || {});
  const differences = summary?.difference_distribution || [];
  const maps = (summary?.maps || [])
    .filter((row) => row.balanced_ratio != null)
    .slice(0, 8);
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.dataQuality")}
        subtitle={i18n.t("settingsPanels.autobalancer.dataQualityHelp")}
      >
        <BarChart
          height={250}
          xAxis={[
            {
              scaleType: "band",
              data: quality.map(([level]) =>
                translateOperatorMessage(level, i18n.t)
              ),
            },
          ]}
          yAxis={[{ min: 0, tickMinStep: 1 }]}
          series={[
            {
              label: i18n.t("settingsPanels.autobalancer.rounds"),
              data: quality.map(([, count]) => count),
              color: theme.palette.info.main,
              valueFormatter: (value) =>
                i18n.t("settingsPanels.autobalancer.roundCount", { v0: value }),
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.maximumTeamDifference")}
        subtitle={i18n.t("settingsPanels.autobalancer.measurableWindows")}
      >
        <BarChart
          height={250}
          xAxis={[
            {
              scaleType: "band",
              data: differences.map((row) => row.bucket),
            },
          ]}
          yAxis={[{ min: 0, tickMinStep: 1 }]}
          series={[
            {
              label: i18n.t("settingsPanels.autobalancer.rounds"),
              data: differences.map((row) => row.rounds),
              color: theme.palette.warning.main,
              valueFormatter: (value) =>
                i18n.t("settingsPanels.autobalancer.roundCount", { v0: value }),
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      {maps.length > 0 && (
        <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
          <ChartShell
            title={i18n.t("settingsPanels.autobalancer.balanceByMap")}
            subtitle={i18n.t("settingsPanels.autobalancer.balanceByMapHelp")}
          >
            <BarChart
              layout="horizontal"
              height={Math.max(280, maps.length * 42)}
              yAxis={[
                {
                  scaleType: "band",
                  data: maps.map((row) => formatMap(row.map_name)),
                },
              ]}
              xAxis={[
                { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
              ]}
              series={[
                {
                  label: i18n.t("settingsPanels.autobalancer.timeInRange"),
                  data: maps.map((row) => Math.round(row.balanced_ratio * 100)),
                  color: theme.palette.success.main,
                  valueFormatter: (value) => `${value} %`,
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

const CalibrationCharts = ({ quality }) => {
  const theme = useTheme();
  const roles = quality?.role_confidence || [];
  const confidence = quality?.confidence_distribution || [];
  const strategies = quality?.strategies || [];
  if (!roles.length && !strategies.length) {
    return (
      <Alert severity="info">
        {i18n.t("settingsPanels.autobalancer.roleSnapshotHelp")}
      </Alert>
    );
  }
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.confidenceByRole")}
        subtitle={i18n.t("settingsPanels.autobalancer.confidenceByRoleHelp")}
      >
        {roles.length ? (
          <BarChart
            height={300}
            xAxis={[
              {
                scaleType: "band",
                data: roles.map(
                  (row) => ROLE_LABELS()[row.role_family] || row.role_family
                ),
              },
            ]}
            yAxis={[
              { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
            ]}
            series={[
              {
                label: i18n.t("settingsPanels.autobalancer.medianConfidence"),
                data: roles.map((row) =>
                  Math.round((row.median_confidence || 0) * 100)
                ),
                color: theme.palette.info.main,
                valueFormatter: (value) => `${value} %`,
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">
            {i18n.t("settingsPanels.autobalancer.noRoleData")}
          </Alert>
        )}
      </ChartShell>
      <ChartShell
        title={i18n.t("settingsPanels.autobalancer.confidenceDistribution")}
        subtitle={i18n.t(
          "settingsPanels.autobalancer.confidenceDistributionHelp"
        )}
      >
        {confidence.some((row) => row.observations) ? (
          <BarChart
            height={300}
            xAxis={[
              {
                scaleType: "band",
                data: confidence.map((row) => row.bucket),
              },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                label: i18n.t("settingsPanels.autobalancer.observations"),
                data: confidence.map((row) => row.observations),
                color: theme.palette.warning.main,
                valueFormatter: (value) =>
                  i18n.t("settingsPanels.autobalancer.observationCount", {
                    v0: value,
                  }),
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">
            {i18n.t("settingsPanels.autobalancer.noConfidenceData")}
          </Alert>
        )}
      </ChartShell>
      <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
        <ChartShell
          title={i18n.t("settingsPanels.autobalancer.strategyComparison")}
          subtitle={i18n.t(
            "settingsPanels.autobalancer.strategyComparisonHelp"
          )}
        >
          {strategies.length ? (
            <BarChart
              height={300}
              xAxis={[
                {
                  scaleType: "band",
                  data: strategies.map(
                    (row) => STRATEGY_LABELS()[row.strategy] || row.strategy
                  ),
                },
              ]}
              yAxis={[{ min: 0 }]}
              series={[
                {
                  label: i18n.t(
                    "settingsPanels.autobalancer.averageProjectedGap"
                  ),
                  data: strategies.map((row) => row.average_projected_gap),
                  color: theme.palette.success.main,
                  valueFormatter: (value) =>
                    value == null
                      ? i18n.t("settingsPanels.autobalancer.noDataLower")
                      : value.toFixed(1),
                },
              ]}
              grid={{ horizontal: true }}
            />
          ) : (
            <Alert severity="info">
              {i18n.t("settingsPanels.autobalancer.noStrategyComparison")}
            </Alert>
          )}
        </ChartShell>
      </Box>
    </Box>
  );
};

const AutobalancerHistoryDashboard = ({
  config,
  shadowSummary = {},
  pilotGoals = {},
}) => {
  useTranslation();
  const initial = {
    days: 90,
    search: "",
    targetDifference: config?.target_difference ?? 2,
    stableSeconds: config?.stable_difference_seconds ?? 45,
  };
  const [draft, setDraft] = useState(initial);
  const [filters, setFilters] = useState(initial);
  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: [
      {
        queryIdentifier: "get_autobalancer_history_dashboard",
        filters,
      },
    ],
    queryFn: () =>
      cmd.GET_AUTOBALANCER_HISTORY_DASHBOARD({
        params: {
          days: filters.days,
          search: filters.search,
          target_difference: filters.targetDifference,
          stable_difference_seconds: filters.stableSeconds,
          limit: 100,
        },
      }),
    retry: false,
    staleTime: 10 * 60 * 1000,
    refetchInterval: (query) =>
      query.state.data?.backfill?.complete ? false : 15_000,
  });
  const summary = data?.summary;
  const sources = data?.source_counts || {};
  const quality = data?.rating_quality || {};
  const ratingConfidence =
    quality.median_rating_confidence ?? shadowSummary.median_rating_confidence;
  const criteria = [
    {
      label: i18n.t("settingsPanels.autobalancer.fullRounds", {
        v0: quality.fully_captured_rounds || 0,
      }),
      met: (quality.fully_captured_rounds || 0) >= 10,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.exactCoverage", {
        v0: percent(quality.snapshot_coverage),
      }),
      met: quality.snapshot_coverage >= 0.95,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.reviewTarget", {
        v0: shadowSummary.reviewed || 0,
      }),
      met: (shadowSummary.reviewed || 0) >= 20,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.acceptedRatio", {
        v0: percent(shadowSummary.acceptance_rate),
      }),
      met: shadowSummary.acceptance_rate >= 0.9,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.ratingConfidenceValue", {
        v0: percent(ratingConfidence),
      }),
      met: ratingConfidence >= 0.6,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.ratingGuardrail", {
        v0: percent(
          shadowSummary.gap_guardrail_rate ?? quality.gap_guardrail_rate
        ),
      }),
      met:
        (shadowSummary.gap_guardrail_rate ?? quality.gap_guardrail_rate) >=
        0.95,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.hardViolations", {
        v0: shadowSummary.rule_warning_proposals || 0,
      }),
      met: (shadowSummary.rule_warning_proposals || 0) === 0,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.overshoots", {
        v0: shadowSummary.size_overshoot_proposals || 0,
      }),
      met: (shadowSummary.size_overshoot_proposals || 0) === 0,
    },
  ];
  const calibrationReady = criteria.every((criterion) => criterion.met);

  return (
    <Box sx={{ mt: 2 }}>
      <Stack
        direction={{ xs: "column", lg: "row" }}
        justifyContent="space-between"
        spacing={1}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            {i18n.t("settingsPanels.autobalancer.historyTitle")}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {i18n.t("settingsPanels.autobalancer.historyIntro")}
          </Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.exactCount", {
              v0: sources.live_snapshots || 0,
            })}
          />
          <Chip
            size="small"
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.reconstructedCount", {
              v0: sources.historical_logs || 0,
            })}
          />
          {data?.generated_at && (
            <Typography variant="caption" color="text.secondary">
              {i18n.t("settingsPanels.autobalancer.updated")}{" "}
              {new Date(data.generated_at).toLocaleString(
                i18n.resolvedLanguage
              )}
            </Typography>
          )}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, minmax(0, 1fr))",
            xl: "repeat(5, minmax(0, 1fr))",
          },
          gap: 1.5,
          mt: 1.5,
        }}
      >
        <Metric
          label={i18n.t("settingsPanels.autobalancer.exactDataCoverage")}
          value={percent(quality.snapshot_coverage)}
          caption={i18n.t("settingsPanels.autobalancer.validSnapshotTarget", {
            v0: percent(0.95),
          })}
          color={
            quality.snapshot_coverage >= 0.95 ? "success.main" : "warning.main"
          }
        />
        <Metric
          label={i18n.t("settingsPanels.autobalancer.medianRatingConfidence")}
          value={percent(
            quality.median_rating_confidence ??
              shadowSummary.median_rating_confidence
          )}
          caption={i18n.t("settingsPanels.autobalancer.roleAwareTarget", {
            v0: percent(pilotGoals.rating_confidence_target ?? 0.6),
          })}
          color={
            (quality.median_rating_confidence ??
              shadowSummary.median_rating_confidence) >= 0.6
              ? "success.main"
              : "warning.main"
          }
        />
        <Metric
          label={i18n.t("settingsPanels.autobalancer.reviewedProposals")}
          value={shadowSummary.reviewed ?? 0}
          caption={i18n.t("settingsPanels.autobalancer.adminReviewTarget", {
            v0: pilotGoals.reviewed_proposals_target ?? 20,
          })}
          color={
            (shadowSummary.reviewed ?? 0) >=
            (pilotGoals.reviewed_proposals_target ?? 20)
              ? "success.main"
              : "text.primary"
          }
        />
        <Metric
          label={i18n.t("settingsPanels.autobalancer.acceptanceRate")}
          value={percent(shadowSummary.acceptance_rate)}
          caption={i18n.t("settingsPanels.autobalancer.reviewedTarget", {
            v0: percent(pilotGoals.acceptance_rate_target ?? 0.9),
          })}
          color={
            shadowSummary.acceptance_rate >=
            (pilotGoals.acceptance_rate_target ?? 0.9)
              ? "success.main"
              : "warning.main"
          }
        />
        <Metric
          label={i18n.t("settingsPanels.autobalancer.hardRuleViolations")}
          value={shadowSummary.rule_warning_proposals ?? 0}
          caption={i18n.t("settingsPanels.autobalancer.hardRuleTarget")}
          color={
            (shadowSummary.rule_warning_proposals ?? 0) === 0
              ? "success.main"
              : "error.main"
          }
        />
      </Box>

      <Alert severity={calibrationReady ? "success" : "info"} sx={{ mt: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
          {calibrationReady
            ? i18n.t("settingsPanels.autobalancer.criteriaMet")
            : i18n.t("settingsPanels.autobalancer.calibrating")}
        </Typography>
        <Stack direction="row" gap={0.75} flexWrap="wrap">
          {criteria.map((criterion) => (
            <Chip
              key={criterion.label}
              size="small"
              color={criterion.met ? "success" : "default"}
              variant={criterion.met ? "filled" : "outlined"}
              label={criterion.label}
            />
          ))}
        </Stack>
        <Typography variant="caption" sx={{ display: "block", mt: 0.75 }}>
          {i18n.t("settingsPanels.autobalancer.manualApproval")}
        </Typography>
      </Alert>

      <Card variant="outlined" sx={{ mt: 1.5 }}>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            gap={1.5}
            alignItems={{ md: "center" }}
          >
            <TextField
              select
              size="small"
              label={i18n.t("settingsPanels.autobalancer.period")}
              value={draft.days}
              onChange={(event) =>
                setDraft({ ...draft, days: Number(event.target.value) })
              }
              sx={{ minWidth: 150 }}
            >
              <MenuItem value={30}>
                {i18n.t("settingsPanels.autobalancer.days30")}
              </MenuItem>
              <MenuItem value={90}>
                {i18n.t("settingsPanels.autobalancer.days90")}
              </MenuItem>
              <MenuItem value={180}>
                {i18n.t("settingsPanels.autobalancer.days180")}
              </MenuItem>
              <MenuItem value={365}>
                {i18n.t("settingsPanels.autobalancer.year1")}
              </MenuItem>
            </TextField>
            <TextField
              size="small"
              label={i18n.t("settingsPanels.autobalancer.optionalMap")}
              placeholder={i18n.t("settingsPanels.autobalancer.mapExample")}
              value={draft.search}
              onChange={(event) =>
                setDraft({ ...draft, search: event.target.value })
              }
            />
            <TextField
              select
              size="small"
              label={i18n.t("settingsPanels.autobalancer.allowedDifference")}
              value={draft.targetDifference}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  targetDifference: Number(event.target.value),
                })
              }
              sx={{ minWidth: 170 }}
            >
              {[1, 2, 3].map((value) => (
                <MenuItem key={value} value={value}>
                  {value} {i18n.t("settingsPanels.autobalancer.players")}
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label={i18n.t("settingsPanels.autobalancer.stableFor")}
              value={draft.stableSeconds}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  stableSeconds: Number(event.target.value),
                })
              }
              sx={{ minWidth: 165 }}
            >
              {[30, 45, 60, 90].map((value) => (
                <MenuItem key={value} value={value}>
                  {value} {i18n.t("settingsPanels.autobalancer.seconds")}
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              disabled={isFetching}
              onClick={() => setFilters({ ...draft })}
            >
              {i18n.t("settingsPanels.autobalancer.analyse")}
            </Button>
          </Stack>
          {isFetching && <LinearProgress sx={{ mt: 1.5 }} />}
        </CardContent>
      </Card>

      {isLoading && (
        <Stack alignItems="center" sx={{ py: 6 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            {i18n.t("settingsPanels.autobalancer.analysingHistory")}
          </Typography>
        </Stack>
      )}
      {isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          {i18n.t("settingsPanels.autobalancer.historyLoadError")}
        </Alert>
      )}
      {!isLoading && !isError && summary && (
        <Stack spacing={2} sx={{ mt: 2 }}>
          {!data.backfill?.complete && (
            <Alert severity="info">
              {i18n.t("settingsPanels.autobalancer.historyBuilding")}{" "}
              {data.backfill?.analyzed_rounds || 0}/
              {data.backfill?.requested_rounds || 0}{" "}
              {i18n.t("settingsPanels.autobalancer.historyBuildingProgress")}
            </Alert>
          )}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0, 1fr))",
                xl: "repeat(4, minmax(0, 1fr))",
              },
              gap: 1.5,
            }}
          >
            <Metric
              label={i18n.t("settingsPanels.autobalancer.measurableRounds")}
              value={`${summary.measurable_rounds}/${summary.rounds_analyzed}`}
              caption={i18n.t("settingsPanels.autobalancer.dataCoverageValue", {
                v0: percent(summary.coverage_ratio),
              })}
              color={
                summary.coverage_ratio >= 0.7 ? "success.main" : "warning.main"
              }
            />
            <Metric
              label={i18n.t("settingsPanels.autobalancer.timeInRange")}
              value={percent(summary.balanced_time_ratio)}
              caption={i18n.t(
                "settingsPanels.autobalancer.maximumDifferenceValue",
                { v0: filters.targetDifference }
              )}
            />
            <Metric
              label={i18n.t("settingsPanels.autobalancer.balanceIncidents")}
              value={summary.incidents_per_10_rounds ?? "–"}
              caption={i18n.t("settingsPanels.autobalancer.perTenRounds")}
            />
            <Metric
              label={i18n.t(
                "settingsPanels.autobalancer.estimatedInterventions"
              )}
              value={summary.switches_per_round ?? "–"}
              caption={i18n.t(
                "settingsPanels.autobalancer.requiredSwitchesPerRound"
              )}
            />
          </Box>
          {summary.coverage_ratio < 0.5 && (
            <Alert severity="warning">
              {i18n.t("settingsPanels.autobalancer.lowCoverageWarning")}
            </Alert>
          )}
          <CalibrationCharts quality={quality} />
          <ChartShell
            title={i18n.t("settingsPanels.autobalancer.weeklyBalance")}
            subtitle={i18n.t("settingsPanels.autobalancer.weeklyBalanceHelp")}
          >
            <WeeklyBalanceChart weekly={summary.weekly} />
          </ChartShell>
          <WhatIfCharts rows={data.what_if} />
          <BreakdownCharts summary={summary} />
        </Stack>
      )}
    </Box>
  );
};

export default AutobalancerHistoryDashboard;
import "@/i18n/register-settings-panels";
