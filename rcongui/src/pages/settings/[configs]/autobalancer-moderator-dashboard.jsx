import i18n from "@/i18n";
import { translateOperatorMessage } from "@/i18n/operator-messages";
import { useTranslation } from "react-i18next";
import ArrowBackIcon from "@mui/icons-material/ArrowBack";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BalanceIcon from "@mui/icons-material/Balance";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ErrorOutlineIcon from "@mui/icons-material/ErrorOutline";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import HelpOutlineIcon from "@mui/icons-material/HelpOutline";
import HistoryIcon from "@mui/icons-material/History";
import InsightsIcon from "@mui/icons-material/Insights";
import PlaylistAddCheckIcon from "@mui/icons-material/PlaylistAddCheck";
import RefreshIcon from "@mui/icons-material/Refresh";
import ScienceIcon from "@mui/icons-material/Science";
import SettingsIcon from "@mui/icons-material/Settings";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  Divider,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  Tab,
  Tabs,
  Typography,
  alpha,
} from "@mui/material";
import { useEffect, useMemo, useState } from "react";
import AutobalancerHistoryDashboard from "@/pages/settings/[configs]/autobalancer-history-dashboard";
import AutobalancerRoundHistory from "@/pages/settings/[configs]/autobalancer-round-history";
import AutobalancerShadowCharts from "@/pages/settings/[configs]/autobalancer-shadow-charts";

const MODE_LABELS = () => ({
  disabled: i18n.t("settingsPanels.autobalancer.disabled"),
  shadow: i18n.t("settingsPanels.autobalancer.shadowMode"),
  manual: i18n.t("settingsPanels.autobalancer.manualMode"),
  auto: i18n.t("settingsPanels.autobalancer.automaticMode"),
});

const PHASE_LABELS = () => ({
  idle: i18n.t("settingsPanels.autobalancer.idle"),
  observing: i18n.t("settingsPanels.autobalancer.observing"),
  volunteer: i18n.t("settingsPanels.autobalancer.volunteer"),
  proposed: i18n.t("settingsPanels.autobalancer.proposed"),
  armed: i18n.t("settingsPanels.autobalancer.armed"),
  verifying: i18n.t("settingsPanels.autobalancer.verifying"),
  cooldown: i18n.t("settingsPanels.autobalancer.cooldown"),
  blocked: i18n.t("settingsPanels.autobalancer.blocked"),
});

const STRATEGY_LABELS = () => ({
  "squad-first": i18n.t("settingsPanels.autobalancer.squadFirst"),
  "balanced-v2": i18n.t("settingsPanels.autobalancer.balancedV2"),
  "skill-first": i18n.t("settingsPanels.autobalancer.skillFirst"),
});

const ROLE_FAMILY_LABELS = () => ({
  combat_infantry: "Combat Infantry",
  support: "Support / Engineer / Medic",
  commander: "Commander",
  leader: "Squad Leader",
  specialist: "Armor / Recon / Artillery / Mortar / Helicopter",
});

const REVIEW_CATEGORY_LABELS = () => ({
  squad_should_stay: i18n.t("settingsPanels.autobalancer.squadShouldStay"),
  critical_role: i18n.t("settingsPanels.autobalancer.criticalRoleReason"),
  recent_join_or_move: i18n.t("settingsPanels.autobalancer.recentJoinReason"),
  better_candidate: i18n.t("settingsPanels.autobalancer.betterCandidateReason"),
  skill_balance: i18n.t("settingsPanels.autobalancer.skillBalanceReason"),
  wrong_team_counts: i18n.t("settingsPanels.autobalancer.wrongCountsReason"),
  other: i18n.t("settingsPanels.autobalancer.otherReason"),
});

const formatPercent = (value) =>
  Number.isFinite(value)
    ? `${Math.round(value * 100)} %`
    : i18n.t("settingsPanels.autobalancer.noData");

const formatNumber = (value, digits = 1) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat(i18n.resolvedLanguage, {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(value)
    : "–";

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat(i18n.resolvedLanguage, {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "–";

const formatMinutes = (seconds) =>
  Number.isFinite(seconds)
    ? i18n.t("settingsPanels.autobalancer.minutesValue", {
        v0: Math.floor(seconds / 60),
      })
    : i18n.t("settingsPanels.autobalancer.unknownLower");

const getTeamLabels = (value) => {
  const labels = value?.team_labels || {};
  const allies = String(labels.allies || "").trim();
  const axis = String(labels.axis || "").trim();
  return {
    allies: /^(allies|allied)$/i.test(allies)
      ? i18n.t("settingsPanels.autobalancer.allies")
      : allies || i18n.t("settingsPanels.autobalancer.allies"),
    axis: /^(axis|axis powers)$/i.test(axis)
      ? i18n.t("settingsPanels.autobalancer.axis")
      : axis || i18n.t("settingsPanels.autobalancer.axis"),
  };
};

const getModeStatus = (mode) => {
  if (mode === "shadow") {
    return {
      title: i18n.t("settingsPanels.autobalancer.safeTesting"),
      detail: i18n.t("settingsPanels.autobalancer.safeTestingHelp"),
      color: "info",
    };
  }
  if (mode === "manual") {
    return {
      title: i18n.t("settingsPanels.autobalancer.manualMode"),
      detail: i18n.t("settingsPanels.autobalancer.approvalRequired"),
      color: "warning",
    };
  }
  if (mode === "auto") {
    return {
      title: i18n.t("settingsPanels.autobalancer.automaticMode"),
      detail: i18n.t("settingsPanels.autobalancer.automaticApprovalHelp"),
      color: "success",
    };
  }
  return {
    title: i18n.t("settingsPanels.autobalancer.balancerDisabled"),
    detail: i18n.t("settingsPanels.autobalancer.balancerDisabledHelp"),
    color: "default",
  };
};

const getTeamProjection = (decision) => {
  const allies = decision?.allies_count;
  const axis = decision?.axis_count;
  if (!Number.isFinite(allies) || !Number.isFinite(axis)) return null;
  const source = decision.source_team;
  const switches = Math.max(1, Number(decision.required_switches) || 1);
  const moved = Math.min(switches, 1);
  const after =
    source === "allies"
      ? { allies: allies - moved, axis: axis + moved }
      : source === "axis"
      ? { allies: allies + moved, axis: axis - moved }
      : { allies, axis };
  return {
    before: { allies, axis, difference: Math.abs(allies - axis) },
    after: {
      ...after,
      difference: Math.abs(after.allies - after.axis),
    },
  };
};

const getDecisionAssessment = (decision) => {
  const projection = getTeamProjection(decision);
  const gapBefore = decision?.rating_gap_before;
  const gapAfter = decision?.projected_rating_gap;
  const hasRating = Number.isFinite(gapBefore) && Number.isFinite(gapAfter);
  const ratingImproves = hasRating ? gapAfter <= gapBefore : null;
  const confidence = decision?.rating_confidence;
  const ratingReliable = Number.isFinite(confidence) && confidence >= 0.6;
  const protectedRole = Boolean(
    decision?.is_leader ||
      decision?.rating_role_family === "commander" ||
      Number(decision?.protection_tier) >= 4
  );
  const tier = Number(decision?.protection_tier);
  const squadImpact = !Number.isFinite(tier)
    ? "unknown"
    : tier <= 1
    ? "low"
    : tier <= 2
    ? "medium"
    : "high";
  const countImproves = projection
    ? projection.after.difference < projection.before.difference
    : null;
  const hasWarnings = Boolean(decision?.audit_warnings?.length);

  if (hasWarnings || countImproves === null) {
    return {
      label: i18n.t("settingsPanels.autobalancer.doNotReview"),
      color: "error",
      title: i18n.t("settingsPanels.autobalancer.checkDataFirst"),
      explanation: i18n.t("settingsPanels.autobalancer.unsafeReference"),
      projection,
      gapBefore,
      gapAfter,
      ratingImproves,
      ratingReliable,
      protectedRole,
      squadImpact,
      countImproves,
    };
  }

  if (protectedRole || squadImpact === "high") {
    return {
      label: i18n.t("settingsPanels.autobalancer.leanReject"),
      color: "warning",
      title: i18n.t("settingsPanels.autobalancer.excessiveDisruption"),
      explanation: i18n.t(
        "settingsPanels.autobalancer.excessiveDisruptionHelp"
      ),
      projection,
      gapBefore,
      gapAfter,
      ratingImproves,
      ratingReliable,
      protectedRole,
      squadImpact,
      countImproves,
    };
  }

  if (countImproves && ratingImproves === true && ratingReliable) {
    return {
      label: i18n.t("settingsPanels.autobalancer.acceptable"),
      color: "success",
      title: i18n.t("settingsPanels.autobalancer.bothGoalsImprove"),
      explanation: i18n.t("settingsPanels.autobalancer.bothGoalsImproveHelp"),
      projection,
      gapBefore,
      gapAfter,
      ratingImproves,
      ratingReliable,
      protectedRole,
      squadImpact,
      countImproves,
    };
  }

  return {
    label: i18n.t("settingsPanels.autobalancer.reviewCloser"),
    color: "warning",
    title: i18n.t("settingsPanels.autobalancer.weighGoals"),
    explanation: i18n.t("settingsPanels.autobalancer.weighGoalsHelp"),
    projection,
    gapBefore,
    gapAfter,
    ratingImproves,
    ratingReliable,
    protectedRole,
    squadImpact,
    countImproves,
  };
};

const MetricCard = ({ label, value, caption, color = "text.primary" }) => (
  <Card variant="outlined" sx={{ minWidth: 0, height: "100%" }}>
    <CardContent sx={{ p: 2, "&:last-child": { pb: 2 } }}>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography
        variant="h5"
        color={color}
        sx={{ mt: 0.5, fontWeight: 700, overflowWrap: "anywhere" }}
      >
        {value}
      </Typography>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ mt: 0.5, display: "block" }}
      >
        {caption}
      </Typography>
    </CardContent>
  </Card>
);

const OperationsTimeline = ({ steps }) => (
  <Box
    component="section"
    aria-labelledby="autobalancer-operations-title"
    sx={{ mt: 1.5 }}
  >
    <Typography
      id="autobalancer-operations-title"
      variant="overline"
      color="text.secondary"
    >
      {i18n.t("settingsPanels.autobalancer.operationsTimeline")}
    </Typography>
    <Box
      sx={{
        mt: 0.75,
        display: "grid",
        gridTemplateColumns: {
          xs: "1fr",
          sm: "repeat(2, minmax(0, 1fr))",
          lg: "repeat(5, minmax(0, 1fr))",
        },
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 1,
        overflow: "hidden",
        backgroundColor: "background.paper",
      }}
    >
      {steps.map((step, index) => (
        <Box
          key={step.label}
          sx={{
            minWidth: 0,
            p: 1.5,
            borderLeft: {
              xs: 0,
              sm: index % 2 ? "1px solid" : 0,
              lg: index ? "1px solid" : 0,
            },
            borderTop: {
              xs: index ? "1px solid" : 0,
              sm: index > 1 ? "1px solid" : 0,
              lg: 0,
            },
            borderColor: "divider",
          }}
        >
          <Stack direction="row" spacing={1} alignItems="center">
            <Box
              sx={{
                width: 28,
                height: 28,
                display: "grid",
                placeItems: "center",
                flex: "0 0 auto",
                border: "1px solid",
                borderColor: step.color || "divider",
                borderRadius: 0.75,
                color: step.color || "text.secondary",
                "& .MuiSvgIcon-root": { fontSize: 17 },
              }}
            >
              {step.icon}
            </Box>
            <Typography variant="caption" color="text.secondary">
              {step.label}
            </Typography>
          </Stack>
          <Typography
            variant="subtitle1"
            color={step.color || "text.primary"}
            sx={{ mt: 1, fontWeight: 700, overflowWrap: "anywhere" }}
          >
            {step.value}
          </Typography>
          <Typography
            variant="caption"
            color="text.secondary"
            sx={{ mt: 0.35, display: "block" }}
          >
            {step.caption}
          </Typography>
        </Box>
      ))}
    </Box>
  </Box>
);

const QualityCard = ({ title, value, explanation, progress, color }) => (
  <Card variant="outlined" sx={{ minWidth: 0 }}>
    <CardContent>
      <Stack
        direction="row"
        justifyContent="space-between"
        alignItems="center"
        gap={1}
      >
        <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
          {title}
        </Typography>
        <Chip size="small" color={color} label={value} />
      </Stack>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
        {explanation}
      </Typography>
      <LinearProgress
        variant="determinate"
        color={color === "success" ? "success" : "primary"}
        value={Math.max(0, Math.min(100, progress || 0))}
        sx={{ mt: 1.5, height: 7, borderRadius: 4 }}
      />
    </CardContent>
  </Card>
);

const ChecklistRow = ({ state, title, explanation, result }) => {
  const icon =
    state === "good" ? (
      <CheckCircleOutlineIcon color="success" />
    ) : state === "bad" ? (
      <ErrorOutlineIcon color="error" />
    ) : (
      <HelpOutlineIcon color="warning" />
    );
  return (
    <Stack
      direction={{ xs: "column", sm: "row" }}
      alignItems={{ sm: "center" }}
      gap={1.5}
      sx={{ px: 2, py: 1.5 }}
    >
      <Stack
        direction="row"
        gap={1.25}
        alignItems="center"
        sx={{ minWidth: 0, flex: 1 }}
      >
        {icon}
        <Box sx={{ minWidth: 0 }}>
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {title}
          </Typography>
          <Typography variant="caption" color="text.secondary">
            {explanation}
          </Typography>
        </Box>
      </Stack>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ pl: { xs: 4.5, sm: 0 }, textAlign: { sm: "right" } }}
      >
        {result}
      </Typography>
    </Stack>
  );
};

const TeamBalance = ({ projection, gapBefore, gapAfter, teamLabels }) => {
  if (!projection) {
    return (
      <Alert severity="warning">
        {i18n.t("settingsPanels.autobalancer.incompleteProposalCounts")}
      </Alert>
    );
  }
  const totalBefore = projection.before.allies + projection.before.axis;
  const totalAfter = projection.after.allies + projection.after.axis;
  const states = [
    {
      label: i18n.t("settingsPanels.autobalancer.before"),
      ...projection.before,
      total: totalBefore,
      gap: gapBefore,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.after"),
      ...projection.after,
      total: totalAfter,
      gap: gapAfter,
    },
  ];
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", md: "1fr auto 1fr" },
        gap: 1.5,
        alignItems: "center",
      }}
    >
      {states.map((state, index) => (
        <Box key={state.label} sx={{ display: "contents" }}>
          {index === 1 && (
            <ArrowForwardIcon
              sx={{
                color: "text.secondary",
                transform: { xs: "rotate(90deg)", md: "none" },
                justifySelf: "center",
              }}
            />
          )}
          <Box sx={{ p: 1.5, borderRadius: 1, bgcolor: "action.hover" }}>
            <Typography variant="caption" color="text.secondary">
              {state.label}
            </Typography>
            <Stack
              direction="row"
              justifyContent="space-between"
              sx={{ mt: 0.75 }}
            >
              <Typography variant="body2" color="text.blue">
                {teamLabels.allies} {state.allies}
              </Typography>
              <Typography variant="body2" color="text.red">
                {teamLabels.axis} {state.axis}
              </Typography>
            </Stack>
            <Box
              sx={{
                display: "flex",
                height: 10,
                overflow: "hidden",
                borderRadius: 5,
                mt: 1,
                bgcolor: "divider",
              }}
            >
              <Box
                sx={{
                  width: `${
                    state.total ? (state.allies / state.total) * 100 : 50
                  }%`,
                  bgcolor: "text.blue",
                }}
              />
              <Box sx={{ flex: 1, bgcolor: "text.red" }} />
            </Box>
            <Stack
              direction="row"
              justifyContent="space-between"
              sx={{ mt: 1 }}
            >
              <Typography variant="caption" color="text.secondary">
                {i18n.t("settingsPanels.autobalancer.ratingGap")}
              </Typography>
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {formatNumber(state.gap)}
              </Typography>
            </Stack>
          </Box>
        </Box>
      ))}
    </Box>
  );
};

const ProposalDetail = ({
  decision,
  canReview,
  reviewPending,
  onAccept,
  onReject,
  onBack,
}) => {
  const assessment = getDecisionAssessment(decision);
  const teamLabels = getTeamLabels(decision);
  const plans = Object.entries(decision?.strategy_plans || {});
  const alternative = plans
    .filter(
      ([, plan]) => plan?.player_id && plan.player_id !== decision.player_id
    )
    .sort(
      ([, a], [, b]) =>
        (a.projected_rating_gap ?? Infinity) -
        (b.projected_rating_gap ?? Infinity)
    )[0];
  const confidence = decision?.rating_confidence;

  return (
    <Box>
      <Button
        startIcon={<ArrowBackIcon />}
        color="inherit"
        onClick={onBack}
        sx={{ mb: 1 }}
      >
        {i18n.t("settingsPanels.autobalancer.backToProposals")}
      </Button>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        gap={2}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="overline" color="text.secondary">
            {i18n.t("settingsPanels.autobalancer.proposalDate")}{" "}
            {formatDate(decision.created_at)}
          </Typography>
          <Typography component="h1" variant="h4" sx={{ fontWeight: 700 }}>
            {i18n.t("settingsPanels.autobalancer.reviewCandidate", {
              name:
                decision.player_name ||
                i18n.t("settingsPanels.autobalancer.unknownCandidate"),
            })}
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {decision.map_name ||
              i18n.t("settingsPanels.autobalancer.unknownMap")}{" "}
            · {teamLabels[decision.source_team]} →{" "}
            {teamLabels[decision.target_team]}
          </Typography>
        </Box>
        <Chip
          color={assessment.color}
          label={assessment.label}
          sx={{ alignSelf: { md: "flex-start" }, fontWeight: 700 }}
        />
      </Stack>

      {decision.review_verdict && (
        <Alert
          severity={
            decision.review_verdict === "accepted" ? "success" : "warning"
          }
          sx={{ mb: 2 }}
        >
          <strong>
            {decision.review_verdict === "accepted"
              ? i18n.t("settingsPanels.autobalancer.acceptedReview")
              : i18n.t("settingsPanels.autobalancer.rejectedReview")}
          </strong>{" "}
          {decision.reviewed_by &&
            i18n.t("settingsPanels.autobalancer.reviewedBy", {
              v0: decision.reviewed_by,
            })}
          {decision.reviewed_at &&
            i18n.t("settingsPanels.autobalancer.reviewedAt", {
              v0: formatDate(decision.reviewed_at),
            })}
          .
          {decision.review_category && (
            <>
              {" "}
              {i18n.t("settingsPanels.autobalancer.reasonLabel")}{" "}
              {REVIEW_CATEGORY_LABELS()[decision.review_category] ||
                decision.review_category}
              .
            </>
          )}
          {decision.review_comment && (
            <>
              {" "}
              {i18n.t("settingsPanels.autobalancer.commentLabel")}{" "}
              {decision.review_comment}
            </>
          )}
        </Alert>
      )}

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            xl: "minmax(0, 1.55fr) minmax(300px, .75fr)",
          },
          gap: 2,
          alignItems: "start",
        }}
      >
        <Stack spacing={2}>
          <Card variant="outlined" sx={{ overflow: "hidden" }}>
            <Box
              sx={(theme) => ({
                p: 2,
                borderBottom: 1,
                borderColor: "divider",
                bgcolor: alpha(
                  theme.palette[assessment.color]?.main ||
                    theme.palette.warning.main,
                  0.1
                ),
              })}
            >
              <Typography variant="overline" color="text.secondary">
                {i18n.t("settingsPanels.autobalancer.recommendation")}
              </Typography>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {assessment.title}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mt: 0.75 }}
              >
                {assessment.explanation}
              </Typography>
            </Box>
            <Stack divider={<Divider flexItem />}>
              <ChecklistRow
                state={assessment.protectedRole ? "bad" : "good"}
                title={i18n.t(
                  "settingsPanels.autobalancer.protectedRoleQuestion"
                )}
                explanation={i18n.t(
                  "settingsPanels.autobalancer.protectedRoleHelp"
                )}
                result={
                  assessment.protectedRole
                    ? i18n.t("settingsPanels.autobalancer.yesAvoid")
                    : i18n.t("settingsPanels.autobalancer.noGood")
                }
              />
              <ChecklistRow
                state={
                  assessment.squadImpact === "low"
                    ? "good"
                    : assessment.squadImpact === "high"
                    ? "bad"
                    : "uncertain"
                }
                title={i18n.t(
                  "settingsPanels.autobalancer.squadImpactQuestion"
                )}
                explanation={i18n.t(
                  "settingsPanels.autobalancer.squadImpactHelp"
                )}
                result={i18n.t("settingsPanels.autobalancer.impactTier", {
                  v0: i18n.t(
                    `settingsPanels.autobalancer.${assessment.squadImpact}`
                  ),
                  v1: decision.protection_tier ?? "–",
                })}
              />
              <ChecklistRow
                state={
                  assessment.countImproves === true
                    ? "good"
                    : assessment.countImproves === false
                    ? "bad"
                    : "uncertain"
                }
                title={i18n.t(
                  "settingsPanels.autobalancer.countsImproveQuestion"
                )}
                explanation={i18n.t(
                  "settingsPanels.autobalancer.countsImproveHelp"
                )}
                result={
                  assessment.projection
                    ? i18n.t("settingsPanels.autobalancer.playersProjection", {
                        v0: assessment.projection.before.difference,
                        v1: assessment.projection.after.difference,
                      })
                    : i18n.t("settingsPanels.autobalancer.notMeasurable")
                }
              />
              <ChecklistRow
                state={
                  assessment.ratingImproves === true
                    ? "good"
                    : assessment.ratingImproves === false
                    ? "bad"
                    : "uncertain"
                }
                title={i18n.t(
                  "settingsPanels.autobalancer.skillImproveQuestion"
                )}
                explanation={i18n.t(
                  "settingsPanels.autobalancer.skillImproveHelp"
                )}
                result={`${formatNumber(assessment.gapBefore)} → ${formatNumber(
                  assessment.gapAfter
                )}`}
              />
              <ChecklistRow
                state={assessment.ratingReliable ? "good" : "uncertain"}
                title={i18n.t(
                  "settingsPanels.autobalancer.reliableRatingQuestion"
                )}
                explanation={i18n.t(
                  "settingsPanels.autobalancer.reliableRatingHelp"
                )}
                result={i18n.t("settingsPanels.autobalancer.confidenceValue", {
                  v0: formatPercent(confidence),
                })}
              />
            </Stack>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
                {i18n.t("settingsPanels.autobalancer.switchEffect")}
              </Typography>
              <TeamBalance
                projection={assessment.projection}
                gapBefore={assessment.gapBefore}
                gapAfter={assessment.gapAfter}
                teamLabels={teamLabels}
              />
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 1.5 }}
              >
                {i18n.t("settingsPanels.autobalancer.candidateSnapshotHelp")}
              </Typography>
            </CardContent>
          </Card>

          {(decision.audit_warnings || []).map((warning) => (
            <Alert key={warning} severity="error">
              {i18n.t("settingsPanels.autobalancer.automaticRuleWarning")}{" "}
              {translateOperatorMessage(warning, i18n.t)}
            </Alert>
          ))}

          <Accordion variant="outlined" disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {i18n.t("settingsPanels.autobalancer.showTechnical")}
              </Typography>
            </AccordionSummary>
            <AccordionDetails>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    sm: "repeat(2, minmax(0, 1fr))",
                  },
                  gap: 1,
                }}
              >
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.strategyLabel")}{" "}
                  {STRATEGY_LABELS()[decision.strategy_version] ||
                    decision.strategy_version ||
                    "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.ratingModelLabel")}{" "}
                  {decision.rating_model_version || "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.effectiveRatingLabel")}{" "}
                  {Math.round(decision.rating ?? 50)}/100
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.rawValueLabel")}{" "}
                  {decision.rating_raw == null
                    ? "–"
                    : `${Math.round(decision.rating_raw)}/100`}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.roleFamilyLabel")}{" "}
                  {ROLE_FAMILY_LABELS()[decision.rating_role_family] ||
                    decision.rating_role_family ||
                    "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.historyLabel")}{" "}
                  {decision.rating_history_source || "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.connectedLabel")}{" "}
                  {formatMinutes(decision.connected_seconds)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.inSquadLabel")}{" "}
                  {formatMinutes(decision.squad_seconds)}
                </Typography>
              </Box>
            </AccordionDetails>
          </Accordion>

          <Card variant="outlined">
            <CardContent>
              <Stack
                direction={{ xs: "column", md: "row" }}
                justifyContent="space-between"
                alignItems={{ md: "center" }}
                gap={2}
              >
                <Box>
                  <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                    {i18n.t("settingsPanels.autobalancer.reviewQuestion")}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {i18n.t("settingsPanels.autobalancer.shadowReviewHelp")}
                  </Typography>
                </Box>
                {canReview ? (
                  <Stack
                    direction="row"
                    gap={1}
                    flexWrap="wrap"
                    justifyContent={{ md: "flex-end" }}
                  >
                    <Button
                      color="warning"
                      variant="outlined"
                      disabled={reviewPending}
                      onClick={() => onReject(decision)}
                    >
                      {i18n.t("settingsPanels.autobalancer.unacceptable")}
                    </Button>
                    <Button color="inherit" variant="outlined" onClick={onBack}>
                      {i18n.t("settingsPanels.autobalancer.reviewLater")}
                    </Button>
                    <Button
                      color="success"
                      variant="contained"
                      disabled={reviewPending || assessment.color === "error"}
                      onClick={() => onAccept(decision)}
                    >
                      {i18n.t(
                        "settingsPanels.autobalancer.candidateAcceptable"
                      )}
                    </Button>
                  </Stack>
                ) : (
                  <Alert severity="info">
                    {i18n.t("settingsPanels.autobalancer.reviewPermission")}
                  </Alert>
                )}
              </Stack>
            </CardContent>
          </Card>
        </Stack>

        <Stack spacing={2}>
          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {i18n.t("settingsPanels.autobalancer.whyPlayer")}
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {translateOperatorMessage(decision.selection_reason, i18n.t) ||
                  i18n.t("settingsPanels.autobalancer.noSelectionReason")}
              </Typography>
              <Stack spacing={1} sx={{ mt: 2 }}>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="body2" color="text.secondary">
                    Squad
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 700, textAlign: "right" }}
                  >
                    {decision.unit_name ||
                      i18n.t("settingsPanels.autobalancer.unassigned")}
                  </Typography>
                </Stack>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="body2" color="text.secondary">
                    {i18n.t("settingsPanels.autobalancer.role")}
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 700, textAlign: "right" }}
                  >
                    {decision.role ||
                      i18n.t("settingsPanels.autobalancer.unknown")}
                  </Typography>
                </Stack>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="body2" color="text.secondary">
                    {i18n.t("settingsPanels.autobalancer.squadImpact")}
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {i18n.t(
                      `settingsPanels.autobalancer.${assessment.squadImpact}`
                    )}
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {i18n.t("settingsPanels.autobalancer.alternative")}
              </Typography>
              {alternative ? (
                <>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 1 }}
                  >
                    <strong>
                      {alternative[1].player_name || alternative[1].player_id}
                    </strong>{" "}
                    {i18n.t("settingsPanels.autobalancer.selectedByPrefix")}
                    {STRATEGY_LABELS()[alternative[0]] || alternative[0]}
                    {i18n.t("settingsPanels.autobalancer.selectedBySuffix")}
                  </Typography>
                  <Stack spacing={1} sx={{ mt: 2 }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={1}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {i18n.t("settingsPanels.autobalancer.planAfter")}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {formatNumber(alternative[1].projected_rating_gap)}
                      </Typography>
                    </Stack>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={1}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {i18n.t("settingsPanels.autobalancer.protectionTier")}
                      </Typography>
                      <Typography variant="body2" sx={{ fontWeight: 700 }}>
                        {alternative[1].effective_tier ?? "–"}
                      </Typography>
                    </Stack>
                  </Stack>
                </>
              ) : (
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 1 }}
                >
                  {i18n.t("settingsPanels.autobalancer.noAlternative")}
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                {i18n.t("settingsPanels.autobalancer.dataQuality")}
              </Typography>
              <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
                <Chip
                  size="small"
                  color={decision.audit_warnings?.length ? "error" : "success"}
                  label={
                    decision.audit_warnings?.length
                      ? i18n.t("settingsPanels.autobalancer.checkSnapshot")
                      : i18n.t("settingsPanels.autobalancer.completeSnapshot")
                  }
                />
                <Chip
                  size="small"
                  color={assessment.ratingReliable ? "success" : "warning"}
                  label={
                    assessment.ratingReliable
                      ? i18n.t("settingsPanels.autobalancer.sufficientRating")
                      : i18n.t("settingsPanels.autobalancer.uncertainRating")
                  }
                />
              </Stack>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 1.5 }}
              >
                {i18n.t("settingsPanels.autobalancer.qualityScope")}
              </Typography>
            </CardContent>
          </Card>
        </Stack>
      </Box>
    </Box>
  );
};

const ProposalQueue = ({
  decisions,
  onOpen,
  emptyMessage = i18n.t("settingsPanels.autobalancer.noShadowProposals"),
  emptySeverity = "info",
}) => {
  if (!decisions.length) {
    return <Alert severity={emptySeverity}>{emptyMessage}</Alert>;
  }
  return (
    <Stack spacing={1}>
      {decisions.map((decision) => {
        const assessment = getDecisionAssessment(decision);
        const isReviewed = Boolean(decision.review_verdict);
        return (
          <Card key={decision.decision_id} variant="outlined">
            <CardContent sx={{ p: 1.5, "&:last-child": { pb: 1.5 } }}>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    md: "minmax(180px, 1.2fr) minmax(180px, 1fr) auto auto",
                  },
                  gap: 1.5,
                  alignItems: "center",
                }}
              >
                <Box sx={{ minWidth: 0 }}>
                  <Typography
                    variant="subtitle2"
                    sx={{ fontWeight: 700 }}
                    noWrap
                  >
                    {decision.player_name ||
                      i18n.t("settingsPanels.autobalancer.unknownCandidate")}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {getTeamLabels(decision)[decision.source_team]} →{" "}
                    {getTeamLabels(decision)[decision.target_team]} ·{" "}
                    {formatDate(decision.created_at)}
                  </Typography>
                </Box>
                <Box>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {assessment.countImproves
                      ? i18n.t("settingsPanels.autobalancer.countsImprove")
                      : i18n.t("settingsPanels.autobalancer.checkCounts")}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {assessment.projection
                      ? `${assessment.projection.before.allies}:${assessment.projection.before.axis} → ${assessment.projection.after.allies}:${assessment.projection.after.axis}`
                      : i18n.t(
                          "settingsPanels.autobalancer.incompleteProjection"
                        )}
                  </Typography>
                </Box>
                <Chip
                  size="small"
                  color={
                    decision.review_verdict === "accepted"
                      ? "success"
                      : decision.review_verdict === "rejected"
                      ? "warning"
                      : assessment.color
                  }
                  label={
                    decision.review_verdict === "accepted"
                      ? i18n.t("settingsPanels.autobalancer.acceptable")
                      : decision.review_verdict === "rejected"
                      ? i18n.t("settingsPanels.autobalancer.unacceptable")
                      : assessment.label
                  }
                />
                <Button
                  variant="outlined"
                  onClick={() => onOpen(decision)}
                  aria-label={i18n.t(
                    "settingsPanels.autobalancer.proposalAction",
                    {
                      v0:
                        decision.player_name ||
                        i18n.t(
                          "settingsPanels.autobalancer.unknownCandidateLower"
                        ),
                      v1: isReviewed
                        ? i18n.t("settingsPanels.autobalancer.viewLower")
                        : i18n.t("settingsPanels.autobalancer.reviewLower"),
                    }
                  )}
                >
                  {isReviewed
                    ? i18n.t("settingsPanels.autobalancer.view")
                    : i18n.t("settingsPanels.autobalancer.review")}
                </Button>
              </Box>
            </CardContent>
          </Card>
        );
      })}
    </Stack>
  );
};

const AutobalancerModeratorDashboard = ({
  config,
  data,
  liveStatus,
  canReview,
  isFetching,
  reviewPending,
  onRefresh,
  onAccept,
  onReject,
  onOpenSettings,
}) => {
  useTranslation();
  const [section, setSection] = useState("live");
  const [selectedDecisionId, setSelectedDecisionId] = useState(null);
  const summary = data.summary || {};
  const goals = data.pilot_goals || {};
  const decisions = data.decisions || [];
  const status = liveStatus || data.live_status || {};
  const isPilot = config?.mode === "shadow";
  useEffect(() => {
    if (!isPilot && (section === "pilot" || section === "proposals")) {
      setSection("live");
      setSelectedDecisionId(null);
    }
  }, [isPilot, section]);
  const pending = decisions.filter((decision) => !decision.review_verdict);
  const reviewed = decisions.filter((decision) => decision.review_verdict);
  const selectedDecision = useMemo(
    () =>
      decisions.find((decision) => decision.decision_id === selectedDecisionId),
    [decisions, selectedDecisionId]
  );
  const modeStatus = getModeStatus(config?.mode);
  const counts = status.team_counts || {};
  const teamLabels = getTeamLabels(status);
  const hasCounts =
    Number.isFinite(counts.allies) && Number.isFinite(counts.axis);
  const difference = hasCounts ? Math.abs(counts.allies - counts.axis) : null;
  const totalReviewsTarget = goals.reviewed_proposals_target ?? 20;
  // Historical review backlog is never a currently executable proposal.
  const plannedMove = status.proposal || status.plan?.candidate;
  const lastExecuted = decisions
    .filter(
      (decision) => decision.status === "executed" && decision.executed_at
    )
    .sort((a, b) => new Date(b.executed_at) - new Date(a.executed_at))[0];
  const liveConfidence = Object.values(
    status.team_rating_confidence || {}
  ).filter(Number.isFinite);
  const ratingConfidence = liveConfidence.length
    ? Math.min(...liveConfidence)
    : null;
  const sourceTeam = plannedMove?.source_team || status.plan?.source_team;
  const targetTeam = plannedMove?.target_team || status.plan?.target_team;
  const plannedMoveCaption = plannedMove
    ? sourceTeam && targetTeam
      ? `${teamLabels[sourceTeam] || sourceTeam} → ${
          teamLabels[targetTeam] || targetTeam
        }`
      : i18n.t("settingsPanels.autobalancer.newestCandidate")
    : i18n.t("settingsPanels.autobalancer.proposalWhenNeeded");
  const timelineSteps = [
    {
      label: i18n.t("settingsPanels.autobalancer.liveState"),
      value: PHASE_LABELS()[status.phase] || modeStatus.title,
      caption: modeStatus.detail,
      color: status.phase === "blocked" ? "warning.main" : "info.main",
      icon: <InsightsIcon aria-hidden />,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.balanceDelta"),
      value:
        difference == null
          ? i18n.t("settingsPanels.autobalancer.notMeasurable")
          : i18n.t("settingsPanels.autobalancer.playerCount", {
              v0: difference,
            }),
      caption:
        status.required_switches > 0
          ? i18n.t("settingsPanels.autobalancer.switchesNeeded", {
              v0: status.required_switches,
            })
          : hasCounts
          ? i18n.t("settingsPanels.autobalancer.withinRange")
          : i18n.t("settingsPanels.autobalancer.incompleteLiveSnapshot"),
      color:
        difference > (config?.target_difference ?? 2)
          ? "warning.main"
          : "success.main",
      icon: <BalanceIcon aria-hidden />,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.plannedSwitch"),
      value:
        plannedMove?.player_name ||
        plannedMove?.name ||
        i18n.t("settingsPanels.autobalancer.noCandidateYet"),
      caption: plannedMoveCaption,
      color: plannedMove ? "primary.main" : "text.secondary",
      icon: <PlaylistAddCheckIcon aria-hidden />,
    },
    {
      label: i18n.t("settingsPanels.autobalancer.lastIntervention"),
      value:
        config?.mode === "shadow"
          ? i18n.t("settingsPanels.autobalancer.noLiveIntervention")
          : lastExecuted
          ? formatDate(lastExecuted.executed_at)
          : i18n.t("settingsPanels.autobalancer.noConfirmedSwitch"),
      caption:
        config?.mode === "shadow"
          ? i18n.t("settingsPanels.autobalancer.noShadowSwitches")
          : i18n.t("settingsPanels.autobalancer.confirmedSwitchScope"),
      icon: <HistoryIcon aria-hidden />,
    },
    {
      label: "Cooldown",
      value:
        status.phase === "cooldown"
          ? i18n.t("settingsPanels.autobalancer.cooldown")
          : i18n.t("settingsPanels.autobalancer.mapProtection", {
              v0: config?.cooldown_maps ?? 3,
            }),
      caption:
        status.phase === "cooldown"
          ? i18n.t("settingsPanels.autobalancer.recheckingAfterSwitch")
          : i18n.t("settingsPanels.autobalancer.protectionAfterSwitch"),
      color: status.phase === "cooldown" ? "warning.main" : "text.primary",
      icon: <ShieldOutlinedIcon aria-hidden />,
    },
  ];
  const nextTask = !isPilot
    ? PHASE_LABELS()[status.phase] || modeStatus.title
    : pending.length
    ? pending.length === 1
      ? i18n.t("settingsPanels.autobalancer.onePending")
      : i18n.t("settingsPanels.autobalancer.pendingCount", {
          v0: pending.length,
        })
    : i18n.t("settingsPanels.autobalancer.nonePending");

  const openDecision = (decision) => {
    setSelectedDecisionId(decision.decision_id);
    setSection("proposals");
  };

  const switchSection = (value) => {
    setSection(value);
    if (value !== "proposals") setSelectedDecisionId(null);
  };

  const selectSection = (value) => {
    switchSection(value);
    if (value === "settings") onOpenSettings();
  };

  if (isPilot && section === "proposals" && selectedDecision) {
    return (
      <ProposalDetail
        decision={selectedDecision}
        canReview={canReview}
        reviewPending={reviewPending}
        onAccept={onAccept}
        onReject={onReject}
        onBack={() => setSelectedDecisionId(null)}
      />
    );
  }

  return (
    <Box>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "flex-start" }}
        gap={2}
      >
        <Box>
          <Typography component="h1" variant="h3" sx={{ fontWeight: 700 }}>
            Autobalancer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {i18n.t(
              `settingsPanels.autobalancer.${
                isPilot ? "moderatorIntro" : "operatorIntro"
              }`
            )}
          </Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap">
          <Chip
            icon={config?.mode === "shadow" ? <ScienceIcon /> : <BalanceIcon />}
            color={modeStatus.color}
            label={
              MODE_LABELS()[config?.mode] ||
              config?.mode ||
              i18n.t("settingsPanels.autobalancer.unknownMode")
            }
          />
          <Button
            startIcon={<RefreshIcon />}
            variant="outlined"
            disabled={isFetching}
            onClick={onRefresh}
          >
            {i18n.t("settingsPanels.autobalancer.refresh")}
          </Button>
        </Stack>
      </Stack>

      <FormControl
        fullWidth
        size="small"
        sx={{ mt: 2, display: { xs: "flex", md: "none" } }}
      >
        <InputLabel id="autobalancer-section-label">
          {i18n.t("settingsPanels.autobalancer.section")}
        </InputLabel>
        <Select
          labelId="autobalancer-section-label"
          value={section}
          label={i18n.t("settingsPanels.autobalancer.section")}
          onChange={(event) => selectSection(event.target.value)}
        >
          <MenuItem value="live">
            {i18n.t("settingsPanels.autobalancer.liveOverview")}
          </MenuItem>
          {isPilot && (
            <MenuItem value="proposals">
              {i18n.t("settingsPanels.autobalancer.reviewProposalsPrefix")}
              {pending.length})
            </MenuItem>
          )}
          {isPilot && (
            <MenuItem value="pilot">
              {i18n.t("settingsPanels.autobalancer.pilotApproval")}
            </MenuItem>
          )}
          <MenuItem value="history">
            {i18n.t("settingsPanels.autobalancer.history")}
          </MenuItem>
          <MenuItem value="settings">
            {i18n.t("settingsPanels.autobalancer.settings")}
          </MenuItem>
        </Select>
      </FormControl>

      <Tabs
        value={section}
        onChange={(_, value) => selectSection(value)}
        variant="scrollable"
        scrollButtons="auto"
        sx={{
          mt: 2,
          borderBottom: 1,
          borderColor: "divider",
          display: { xs: "none", md: "flex" },
        }}
      >
        <Tab
          value="live"
          icon={<InsightsIcon />}
          iconPosition="start"
          label="Live"
        />
        {isPilot && (
          <Tab
            value="proposals"
            icon={<PlaylistAddCheckIcon />}
            iconPosition="start"
            label={i18n.t("settingsPanels.autobalancer.reviewProposalsCount", {
              v0: pending.length,
            })}
          />
        )}
        {isPilot && (
          <Tab
            value="pilot"
            icon={<ShieldOutlinedIcon />}
            iconPosition="start"
            label={i18n.t("settingsPanels.autobalancer.pilotApproval")}
          />
        )}
        <Tab
          value="history"
          icon={<HistoryIcon />}
          iconPosition="start"
          label={i18n.t("settingsPanels.autobalancer.history")}
        />
        <Tab
          value="settings"
          icon={<SettingsIcon />}
          iconPosition="start"
          label={i18n.t("settingsPanels.autobalancer.settings")}
        />
      </Tabs>

      {section === "settings" && (
        <Alert severity="info" sx={{ mt: 2 }}>
          {i18n.t("settingsPanels.autobalancer.settingsOpened")}
        </Alert>
      )}

      {section === "live" && (
        <>
          <Card
            variant="outlined"
            sx={(theme) => ({
              mt: 2,
              borderColor: alpha(theme.palette.primary.main, 0.65),
              background: `linear-gradient(120deg, ${alpha(
                theme.palette.primary.main,
                0.12
              )}, ${alpha(theme.palette.background.paper, 0.98)} 72%)`,
            })}
          >
            <CardContent>
              <Stack
                direction={{ xs: "column", md: "row" }}
                justifyContent="space-between"
                alignItems={{ md: "center" }}
                gap={2}
              >
                <Box>
                  <Typography variant="overline" color="text.secondary">
                    {i18n.t(
                      `settingsPanels.autobalancer.${
                        isPilot ? "whatNext" : "liveState"
                      }`
                    )}
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {nextTask}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.75 }}
                  >
                    {!isPilot
                      ? (status.block_reasons || [])
                          .map((reason) =>
                            translateOperatorMessage(reason, i18n.t)
                          )
                          .join(" · ") || modeStatus.detail
                      : pending.length
                      ? i18n.t("settingsPanels.autobalancer.reviewNextCount", {
                          v0: Math.min(5, pending.length),
                        })
                      : i18n.t("settingsPanels.autobalancer.noTask")}
                  </Typography>
                </Box>
                {isPilot && pending.length > 0 && (
                  <Button
                    variant="contained"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => openDecision(pending[0])}
                  >
                    {i18n.t("settingsPanels.autobalancer.reviewNext")}
                  </Button>
                )}
              </Stack>
            </CardContent>
          </Card>

          <OperationsTimeline steps={timelineSteps} />

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0, 1fr))",
              },
              gap: 1.5,
              mt: 1.5,
            }}
          >
            <MetricCard
              label={i18n.t("settingsPanels.autobalancer.teamCounts")}
              value={
                hasCounts
                  ? `${teamLabels.allies} ${counts.allies} · ${teamLabels.axis} ${counts.axis}`
                  : i18n.t("settingsPanels.autobalancer.unavailable")
              }
              caption={i18n.t("settingsPanels.autobalancer.bothTeamsSnapshot")}
            />
            {isPilot ? (
              <MetricCard
                label={i18n.t("settingsPanels.autobalancer.pilotStatus")}
                value={
                  goals.ready_for_manual
                    ? i18n.t("settingsPanels.autobalancer.readyReview")
                    : i18n.t("settingsPanels.autobalancer.notReady")
                }
                caption={i18n.t("settingsPanels.autobalancer.reviewProgress", {
                  v0: summary.reviewed ?? 0,
                  v1: totalReviewsTarget,
                })}
                color={goals.ready_for_manual ? "success.main" : "text.primary"}
              />
            ) : (
              <MetricCard
                label={i18n.t("settingsPanels.autobalancer.plannedSwitch")}
                value={
                  plannedMove?.player_name ||
                  plannedMove?.name ||
                  i18n.t("settingsPanels.autobalancer.noCandidateYet")
                }
                caption={plannedMoveCaption}
              />
            )}
          </Box>

          {isPilot && (
            <>
              <Stack
                direction={{ xs: "column", sm: "row" }}
                justifyContent="space-between"
                alignItems={{ sm: "flex-end" }}
                gap={1}
                sx={{ mt: 3, mb: 1.5 }}
              >
                <Box>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {i18n.t("settingsPanels.autobalancer.openProposals")}
                  </Typography>
                  <Typography variant="body2" color="text.secondary">
                    {i18n.t("settingsPanels.autobalancer.openProposalsHelp")}
                  </Typography>
                </Box>
                <Button
                  color="inherit"
                  onClick={() => switchSection("proposals")}
                >
                  {i18n.t("settingsPanels.autobalancer.showAll", {
                    count: pending.length,
                  })}
                </Button>
              </Stack>
              <ProposalQueue
                decisions={pending.slice(0, 3)}
                onOpen={openDecision}
                emptyMessage={
                  decisions.length
                    ? i18n.t("settingsPanels.autobalancer.allReviewed")
                    : i18n.t("settingsPanels.autobalancer.noIncidentYet")
                }
                emptySeverity={decisions.length ? "success" : "info"}
              />
            </>
          )}

          <Box sx={{ mt: 3, mb: 1.5 }}>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              {i18n.t("settingsPanels.autobalancer.trustData")}
            </Typography>
            <Typography variant="body2" color="text.secondary">
              {i18n.t("settingsPanels.autobalancer.metricScope")}
            </Typography>
          </Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(2, minmax(0, 1fr))",
              },
              gap: 1.5,
            }}
          >
            <QualityCard
              title={i18n.t("settingsPanels.autobalancer.liveSnapshotComplete")}
              value={
                status.data_confidence >= 0.95
                  ? i18n.t("settingsPanels.autobalancer.yes")
                  : formatPercent(status.data_confidence)
              }
              color={status.data_confidence >= 0.95 ? "success" : "warning"}
              progress={(status.data_confidence || 0) * 100}
              explanation={i18n.t(
                "settingsPanels.autobalancer.liveSnapshotCompleteHelp"
              )}
            />
            <QualityCard
              title={i18n.t("settingsPanels.autobalancer.ratingReliable")}
              value={formatPercent(ratingConfidence)}
              color={ratingConfidence >= 0.6 ? "success" : "warning"}
              progress={(ratingConfidence || 0) * 100}
              explanation={i18n.t(
                "settingsPanels.autobalancer.ratingReliableHelp"
              )}
            />
          </Box>

          <Accordion variant="outlined" disableGutters sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  {i18n.t("settingsPanels.autobalancer.liveDiagnostics")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {i18n.t("settingsPanels.autobalancer.liveDiagnosticsHelp")}
                </Typography>
              </Box>
            </AccordionSummary>
            <AccordionDetails>
              <AutobalancerShadowCharts
                status={status}
                timeline={data.timeline}
                summary={summary}
                config={config}
              />
            </AccordionDetails>
          </Accordion>
        </>
      )}

      {isPilot && section === "proposals" && (
        <Box sx={{ mt: 2 }}>
          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "flex-end" }}
            gap={1}
            sx={{ mb: 1.5 }}
          >
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                {i18n.t("settingsPanels.autobalancer.reviewProposals")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {i18n.t("settingsPanels.autobalancer.reviewFairness")}
              </Typography>
            </Box>
            <Chip
              label={i18n.t("settingsPanels.autobalancer.openReviewedCount", {
                v0: pending.length,
                v1: summary.reviewed ?? 0,
              })}
            />
          </Stack>
          <ProposalQueue
            decisions={pending}
            onOpen={openDecision}
            emptyMessage={
              decisions.length
                ? i18n.t("settingsPanels.autobalancer.noOpenProposals")
                : i18n.t("settingsPanels.autobalancer.noShadowProposal")
            }
            emptySeverity={decisions.length ? "success" : "info"}
          />

          {reviewed.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                {i18n.t("settingsPanels.autobalancer.alreadyReviewed")}
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 1.5 }}
              >
                {i18n.t("settingsPanels.autobalancer.reviewHistoryHelp")}
              </Typography>
              <ProposalQueue decisions={reviewed} onOpen={openDecision} />
            </Box>
          )}
        </Box>
      )}

      {isPilot && section === "pilot" && (
        <Box sx={{ mt: 2 }}>
          <Alert
            severity={goals.ready_for_manual ? "success" : "warning"}
            sx={{ mb: 2 }}
          >
            <strong>
              {goals.ready_for_manual
                ? i18n.t("settingsPanels.autobalancer.readyJointReview")
                : i18n.t("settingsPanels.autobalancer.notReadyManual")}
            </strong>{" "}
            {i18n.t("settingsPanels.autobalancer.approvalAlwaysManual")}
          </Alert>
          <AutobalancerHistoryDashboard
            config={config}
            shadowSummary={summary}
            pilotGoals={goals}
          />
        </Box>
      )}

      {section === "history" && (
        <Box sx={{ mt: 2 }}>
          <AutobalancerRoundHistory config={config} teamLabels={teamLabels} />
        </Box>
      )}
    </Box>
  );
};

export default AutobalancerModeratorDashboard;
import "@/i18n/register-settings-panels";
