import { useEffect, useId, useMemo, useState } from "react";
import { useTranslation } from "react-i18next";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControlLabel,
  Stack,
  Switch,
  Typography,
} from "@mui/material";
import { alpha, useTheme } from "@mui/material/styles";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import { ActionButton } from "@/features/player-action/ActionMenu";
import { Actions } from "@/features/player-action/actions";
import { cmd } from "@/utils/fetchUtils";
import { getThemeTeamColors } from "@/themes/teamColors";
import { formatRoleLabel } from "../live/player-display-labels";
import {
  buildLiveBalanceStatus,
  validateLiveRecommendation,
} from "./live-balance.mjs";
import {
  balanceRecommendations,
  holdRecommendations,
  recommendationNotice,
  recommendationStatus,
} from "./balance-recommendations.mjs";
import { balanceActionPreflight } from "./balance-action-guard.mjs";

const DEFAULT_BALANCE_SETTINGS = {
  targetDifference: 2,
  skillGapSoftLimit: 8,
  minimumImprovement: 2.5,
  coordinatedSquadSwitchesEnabled: false,
  allowIndividualSquadFallback: true,
};

const settingsFromConfig = (config) => ({
  targetDifference:
    config.target_difference ?? DEFAULT_BALANCE_SETTINGS.targetDifference,
  skillGapSoftLimit:
    config.skill_gap_soft_limit ?? DEFAULT_BALANCE_SETTINGS.skillGapSoftLimit,
  minimumImprovement:
    config.skill_gap_min_improvement ??
    DEFAULT_BALANCE_SETTINGS.minimumImprovement,
  coordinatedSquadSwitchesEnabled:
    config.coordinated_squad_switches_enabled === true,
  allowIndividualSquadFallback:
    config.allow_individual_squad_fallback !== false,
});

const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));

const ratingFormatter = (language) => (value) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat(language, { maximumFractionDigits: 1 }).format(
        value
      )
    : "–";

const qualityLabel = (t, confidence) => {
  if (!Number.isFinite(confidence)) return t("liveViews.balance.notMeasurable");
  if (confidence >= 0.8) return t("liveViews.balance.confidenceHigh");
  if (confidence >= 0.6) return t("liveViews.balance.confidenceMedium");
  return t("liveViews.balance.confidenceLow");
};

const qualityColor = (confidence) => {
  if (!Number.isFinite(confidence)) return "text.secondary";
  if (confidence >= 0.8) return "success.main";
  if (confidence >= 0.6) return "warning.main";
  return "error.main";
};

const Metric = ({ label, children, divider = true }) => (
  <Box
    sx={{
      minWidth: 0,
      px: { xs: 1.25, md: 1.5 },
      py: 1.15,
      borderRight: divider ? "1px solid" : 0,
      borderBottom: { xs: "1px solid", md: 0 },
      borderColor: "divider",
      "&:last-of-type": { borderRight: 0 },
    }}
  >
    <Typography
      variant="caption"
      color="text.secondary"
      sx={{ display: "block", mb: 0.45, fontWeight: 700 }}
    >
      {label}
    </Typography>
    {children}
  </Box>
);

const StrengthBar = ({ allies, axis, label }) => {
  const { t, i18n } = useTranslation();
  const formatRating = ratingFormatter(i18n.resolvedLanguage);
  const theme = useTheme();
  const teamColors = getThemeTeamColors(theme);
  const hasRatings = Number.isFinite(allies) && Number.isFinite(axis);
  const difference = hasRatings ? allies - axis : 0;
  const alliesShare = hasRatings ? clamp(50 + difference / 2, 12, 88) : 50;

  return (
    <Box sx={{ minWidth: 0, flex: 1 }}>
      <Stack direction="row" justifyContent="space-between" sx={{ mb: 0.5 }}>
        <Typography variant="caption" color="text.secondary">
          {label}
        </Typography>
        <Typography variant="caption" color="text.secondary">
          {formatRating(allies)} : {formatRating(axis)}
        </Typography>
      </Stack>
      <Box data-theme-surface="control"
        role="img"
        aria-label={t("liveViews.balance.barDescription", {
          label,
          allies: formatRating(allies),
          axis: formatRating(axis),
        })}
        sx={{
          position: "relative",
          display: "flex",
          height: 12,
          overflow: "hidden",
          border: "1px solid",
          borderColor: "divider",
          backgroundColor: "background.default",
        }}
      >
        <Box sx={{ width: `${alliesShare}%`, bgcolor: teamColors.allies }} />
        <Box sx={{ flex: 1, bgcolor: teamColors.axis }} />
        <Box
          aria-hidden
          sx={{
            position: "absolute",
            inset: "-1px auto -1px 50%",
            width: 2,
            bgcolor: "common.white",
            opacity: 0.9,
          }}
        />
      </Box>
    </Box>
  );
};

const AutobalancerCard = ({
  teams,
  onHighlightPlayers,
  detailsExpanded,
  onDetailsExpandedChange,
  detailsDisabled = false,
  detailsFeedback,
}) => {
  const { t, i18n } = useTranslation();
  const formatRating = ratingFormatter(i18n.resolvedLanguage);
  const detailsId = useId();
  const theme = useTheme();
  const teamColors = getThemeTeamColors(theme);
  const [localExpanded, setLocalExpanded] = useState(true);
  const controlled = detailsExpanded !== undefined;
  const expanded = controlled ? detailsExpanded : localExpanded;
  const setExpanded = (value) => {
    if (controlled) onDetailsExpandedChange?.(value);
    else setLocalExpanded(value);
  };
  const [explanationOpen, setExplanationOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [selectedRecommendation, setSelectedRecommendation] = useState(0);
  const [balanceSettings, setBalanceSettings] = useState(
    DEFAULT_BALANCE_SETTINGS
  );

  useEffect(() => {
    let mounted = true;
    cmd
      .GET_AUTOBALANCER_CONFIG({ throwRouteError: false })
      .then((config) => {
        if (!mounted || !config) return;
        setBalanceSettings(settingsFromConfig(config));
      })
      .catch(() => {});
    return () => {
      mounted = false;
    };
  }, []);

  const liveStatus = useMemo(
    () => buildLiveBalanceStatus(teams, balanceSettings),
    [balanceSettings, teams]
  );

  const [held, setHeld] = useState(null);
  useEffect(() => {
    const update = () =>
      setHeld((previous) =>
        holdRecommendations(
          previous,
          balanceRecommendations(liveStatus),
          Date.now(),
          reviewOpen
        )
      );
    update();
    if (reviewOpen || !held?.items.length) return;
    const timer = setTimeout(update, Math.max(0, held.expiresAt - Date.now()));
    return () => clearTimeout(timer);
  }, [liveStatus, held, reviewOpen]);

  const validated = useMemo(
    () =>
      (held?.items ?? []).map((item) =>
        validateLiveRecommendation(teams, balanceSettings, item)
      ),
    [held, teams, balanceSettings]
  );
  const recommendations = useMemo(
    () =>
      (held?.items ?? []).map(
        (item, index) =>
          validated[index] ?? {
            ...item,
            projected_rating_gap: null,
            projected_team_ratings: null,
          }
      ),
    [held, validated]
  );
  const status = useMemo(
    () => recommendationStatus(liveStatus, recommendations),
    [liveStatus, recommendations]
  );
  const refreshRecommendations = () => {
    setSelectedRecommendation(0);
    setHeld(
      holdRecommendations(null, balanceRecommendations(liveStatus), Date.now())
    );
  };

  const insight = useMemo(() => {
    if (!status) return null;
    const counts = status.team_counts || {};
    const ratings = status.team_ratings || {};
    const teamLabels = status.team_labels || {
      allies: t("views.team.allies"),
      axis: t("views.team.axis"),
    };
    const countDifference =
      Number.isFinite(counts.allies) && Number.isFinite(counts.axis)
        ? Math.abs(counts.allies - counts.axis)
        : null;
    const ratingDifference =
      Number.isFinite(ratings.allies) && Number.isFinite(ratings.axis)
        ? Math.abs(ratings.allies - ratings.axis)
        : null;
    const strengthLimit = status.strength_thresholds?.soft_limit ?? 8;
    const countUnbalanced = Number(status.required_switches || 0) > 0;
    const strengthUnbalanced =
      Boolean(liveStatus.strength_swap) ||
      Boolean(
        !countUnbalanced &&
          liveStatus.squad_recommendation?.kind === "squad_swap"
      ) ||
      (Number.isFinite(ratingDifference) && ratingDifference > strengthLimit);
    const blocked = (status.block_reasons || []).length > 0;
    const warning = (status.warnings || []).length > 0;
    const strongerTeam =
      Number.isFinite(ratings.allies) && Number.isFinite(ratings.axis)
        ? ratings.allies >= ratings.axis
          ? "allies"
          : "axis"
        : null;
    const weakerTeam =
      strongerTeam === "allies"
        ? "axis"
        : strongerTeam === "axis"
        ? "allies"
        : null;
    const squadRecommendation = status.squad_recommendation;
    const strengthSwap = status.strength_swap;
    const proposal = status.proposal;
    const plan = status.plan || {};
    const targetTeam = plan.target_team;
    const projectedGap =
      squadRecommendation?.projected_rating_gap ??
      strengthSwap?.projected_rating_gap ??
      plan.projected_rating_gap;
    const beforeGap =
      squadRecommendation?.rating_gap_before ??
      strengthSwap?.rating_gap_before ??
      plan.rating_gap_before ??
      ratingDifference;
    const dataConfidence = Number(status.data_confidence);
    const pairConfidence = Number(
      squadRecommendation?.rating_confidence ?? strengthSwap?.rating_confidence
    );
    const effectiveConfidence = Number.isFinite(pairConfidence)
      ? Math.min(dataConfidence, pairConfidence)
      : dataConfidence;

    let headline = t("liveViews.balance.balancedTeams");
    let tone = "success";
    if (blocked) {
      headline = t("liveViews.balance.blocked");
      tone = "warning";
    } else if (countUnbalanced) {
      headline = t("liveViews.balance.unevenCounts");
      tone = "error";
    } else if (strengthUnbalanced) {
      headline = t("liveViews.balance.unevenStrength");
      tone = "error";
    } else if (warning) {
      headline = t("liveViews.balance.keepWatching");
      tone = "warning";
    }

    const recommendation = squadRecommendation
      ? {
          kind: squadRecommendation.kind,
          title:
            squadRecommendation.kind === "squad_swap"
              ? t("liveViews.balance.squadSwap")
              : t("liveViews.balance.squadMove"),
          detail: t("liveViews.balance.groupTogether", {
            count: squadRecommendation.member_count,
          }),
        }
      : strengthSwap
      ? {
          kind: "swap",
          title: t("liveViews.balance.controlledSwap"),
          detail: t("liveViews.balance.countUnchanged"),
        }
      : proposal
      ? {
          kind: "move",
          title: t("liveViews.balance.controlledMove"),
          detail: t("liveViews.balance.plannedSwitches", {
            count: status.required_switches || 1,
          }),
        }
      : {
          kind: "observe",
          title:
            countUnbalanced || strengthUnbalanced
              ? t("liveViews.balance.analysing")
              : t("liveViews.balance.noIntervention"),
          detail:
            countUnbalanced || strengthUnbalanced
              ? t("liveViews.balance.noCandidate")
              : t("liveViews.balance.withinLimits"),
        };

    const projectedRatings =
      squadRecommendation?.projected_team_ratings ??
      strengthSwap?.projected_team_ratings ??
      plan.projected_team_ratings;

    return {
      counts,
      ratings,
      teamLabels,
      countDifference,
      ratingDifference,
      countUnbalanced,
      strengthUnbalanced,
      blocked,
      warning,
      strongerTeam,
      weakerTeam,
      squadRecommendation,
      strengthSwap,
      proposal,
      plan,
      targetTeam,
      projectedGap,
      beforeGap,
      projectedRatings,
      effectiveConfidence,
      headline,
      tone,
      recommendation,
      needsAttention:
        blocked ||
        countUnbalanced ||
        strengthUnbalanced ||
        warning ||
        Boolean(squadRecommendation) ||
        Boolean(proposal),
    };
  }, [status, liveStatus, t]);

  const highlights = useMemo(() => {
    if (!insight || !validated[0]) return {};
    if (insight.squadRecommendation) {
      return Object.fromEntries(
        insight.squadRecommendation.moves.flatMap((move) => {
          const squad = insight.squadRecommendation.squads.find(
            (item) =>
              item.team === move.source_team &&
              item.squad_name === move.squad_name
          );
          return (squad?.members || []).map((player) => [
            player.player_id,
            {
              targetTeam: move.target_team,
              label: t("liveViews.balance.squadDestination", {
                squad: move.squad_name,
                team: insight.teamLabels[move.target_team],
              }),
            },
          ]);
        })
      );
    }
    if (insight.strengthSwap) {
      const { stronger_player: stronger, weaker_player: weaker } =
        insight.strengthSwap;
      return {
        [stronger?.player_id]: {
          targetTeam: insight.strengthSwap.weaker_team,
          label: t("liveViews.balance.recommendedDestination", {
            team: insight.teamLabels[insight.strengthSwap.weaker_team],
          }),
        },
        [weaker?.player_id]: {
          targetTeam: insight.strengthSwap.stronger_team,
          label: t("liveViews.balance.recommendedDestination", {
            team: insight.teamLabels[insight.strengthSwap.stronger_team],
          }),
        },
      };
    }
    if (insight.proposal?.player_id) {
      return {
        [insight.proposal.player_id]: {
          targetTeam: insight.targetTeam,
          label: t("liveViews.balance.recommendedDestination", {
            team:
              insight.teamLabels[insight.targetTeam] ||
              t("liveViews.balance.otherTeam"),
          }),
        },
      };
    }
    return {};
  }, [insight, validated, t]);

  useEffect(() => {
    onHighlightPlayers?.(highlights);
    return () => onHighlightPlayers?.({});
  }, [highlights, onHighlightPlayers]);

  useEffect(() => {
    // A saved compact view stays compact when the live status changes.
    // The headline and its warning color remain visible and keep updating.
    if (!controlled && insight?.needsAttention) setLocalExpanded(true);
  }, [controlled, insight?.headline]);

  if (!status || !insight) return null;

  const toneColor =
    insight.tone === "success"
      ? "success.main"
      : insight.tone === "warning"
      ? "warning.main"
      : "error.main";
  const ToneIcon =
    insight.tone === "success"
      ? CheckCircleOutlineIcon
      : insight.tone === "warning"
      ? ReportProblemOutlinedIcon
      : BalanceOutlinedIcon;
  const swap = insight.strengthSwap;
  const squad = insight.squadRecommendation;
  const proposalName = insight.proposal?.player_name;
  const alternativesAvailable = recommendations.length > 1;
  const activeRecommendation =
    recommendations[
      Math.min(selectedRecommendation, recommendations.length - 1)
    ];
  const activeValid = Boolean(
    validated[Math.min(selectedRecommendation, recommendations.length - 1)]
  );
  const noticeContext = {
    blocked: insight.blocked,
    balanced:
      !insight.countUnbalanced &&
      !insight.strengthUnbalanced &&
      !insight.warning,
    reviewing: reviewOpen,
  };
  const notice = recommendationNotice(
    {
      ...noticeContext,
      valid: Boolean(validated[0]),
    },
    t
  );
  const reviewNotice = recommendationNotice(
    {
      ...noticeContext,
      valid: activeValid,
      reviewing: true,
    },
    t
  );
  const hasProjection =
    Number.isFinite(insight.projectedRatings?.allies) &&
    Number.isFinite(insight.projectedRatings?.axis);
  const actionRecipients = activeRecommendation
    ? activeRecommendation.kind === "squad_move" ||
      activeRecommendation.kind === "squad_swap"
      ? [
          {
            player_id: `squad:${activeRecommendation.moves
              .map((move) => `${move.source_team}:${move.squad_name}`)
              .join("+")}`,
            name: activeRecommendation.squads
              .map((item) => `Squad ${item.squad_name}`)
              .join(" ↔ "),
          },
        ]
      : activeRecommendation.kind === "strength_swap"
      ? [
          activeRecommendation.stronger_player,
          activeRecommendation.weaker_player,
        ].map((player) => ({
          player_id: player.player_id,
          name: player.player_name,
        }))
      : [
          {
            player_id: activeRecommendation.player.player_id,
            name: activeRecommendation.player.player_name,
          },
        ]
    : [];
  const squadActionParams =
    activeRecommendation?.kind === "squad_move" ||
    activeRecommendation?.kind === "squad_swap"
      ? {
          moves: activeRecommendation.moves.map((move) => ({
            ...move,
            target_label:
              insight.teamLabels[move.target_team] || move.target_team,
          })),
        }
      : undefined;

  const baseAction = activeRecommendation?.kind.startsWith("squad_")
    ? Actions.CoordinatedSquadSwitch
    : Actions.SwitchPlayer;
  const reviewedAction = activeRecommendation
    ? {
        ...baseAction,
        preflight: balanceActionPreflight({
          t,
          recommendation: activeRecommendation,
          recipientIds: actionRecipients.map((player) => player.player_id),
          readTeams: () => cmd.GET_LIVE_TEAMS({ throwRouteError: false }),
          readSettings: async () =>
            settingsFromConfig(
              await cmd.GET_AUTOBALANCER_CONFIG({ throwRouteError: false })
            ),
        }),
      }
    : null;

  return (
    <Box data-theme-surface="panel"
      component="section"
      data-testid="live-balance-card"
      aria-label={t("liveViews.balance.assistant")}
      sx={(theme) => ({
        mb: 1.5,
        border: "1px solid",
        borderColor: alpha(theme.palette[toneColor.split(".")[0]].main, 0.65),
        borderRadius: 0,
        backgroundColor: "background.paper",
        overflow: "hidden",
      })}
    >
      <Stack
        direction={{ xs: "column", sm: "row" }}
        alignItems={{ sm: "center" }}
        justifyContent="space-between"
        gap={1}
        sx={{
          minHeight: 46,
          px: 1.5,
          py: 0.75,
          borderBottom: "1px solid",
          borderColor: "divider",
          backgroundColor: "background.default",
        }}
      >
        <Stack direction="row" alignItems="center" spacing={1} minWidth={0}>
          <ToneIcon sx={{ color: toneColor }} aria-hidden />
          <Box minWidth={0}>
            <Typography
              variant="overline"
              color="primary.main"
              sx={{ display: "block", lineHeight: 1.1 }}
            >
              {t("liveViews.balance.title")}
            </Typography>
            <Typography
              variant="subtitle1"
              sx={{ color: toneColor, fontWeight: 800 }}
            >
              {insight.headline}
            </Typography>
          </Box>
        </Stack>
        <Stack
          direction="row"
          alignItems="center"
          spacing={0.75}
          flexWrap="wrap"
        >
          {expanded && (
            <Chip
              size="small"
              label={t("liveViews.balance.directData")}
              color="info"
              sx={{ borderRadius: 0 }}
            />
          )}
          {expanded && (
            <Chip
              size="small"
              variant="outlined"
              label={t("liveViews.balance.noHistory")}
              sx={{ borderRadius: 0 }}
            />
          )}
          <Button
            size="small"
            color="inherit"
            startIcon={<InfoOutlinedIcon />}
            disabled={!expanded && detailsDisabled}
            onClick={() => {
              if (!expanded) setExpanded(true);
              setExplanationOpen((value) => !value);
            }}
          >
            {t("liveViews.balance.why")}
          </Button>
          {controlled ? (
            <FormControlLabel
              label={t("views.live.balanceDetails")}
              sx={{
                m: 0,
                "& .MuiFormControlLabel-label": { fontSize: "0.75rem" },
              }}
              control={
                <Switch
                  size="small"
                  checked={expanded}
                  disabled={detailsDisabled}
                  onChange={(_, checked) => setExpanded(checked)}
                  inputProps={{
                    role: "switch",
                    "aria-label": t("views.live.balanceDetailsToggle"),
                    "aria-controls": detailsId,
                  }}
                />
              }
            />
          ) : (
            !expanded && (
              <Button size="small" onClick={() => setExpanded(true)}>
                {t("liveViews.balance.open")}
              </Button>
            )
          )}
        </Stack>
      </Stack>

      {detailsFeedback}

      {recommendations.length > 0 && (
        <Alert
          severity={notice.severity}
          role="status"
          sx={{ borderRadius: 0 }}
          action={
            <Button
              color="inherit"
              onClick={refreshRecommendations}
              disabled={reviewOpen}
            >
              {t("liveViews.balance.refresh")}
            </Button>
          }
        >
          <Typography variant="body2" sx={{ fontWeight: 700 }}>
            {notice.title}
          </Typography>
          {notice.description}
        </Alert>
      )}

      <Collapse id={detailsId} in={expanded} unmountOnExit>
        <Box>
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "0.78fr 1.25fr 1fr 1.35fr 1.65fr 1.15fr",
              },
              borderBottom: "1px solid",
              borderColor: "divider",
              "& > :last-child": { borderBottom: 0 },
            }}
          >
            <Metric label={t("liveViews.balance.playerCount")}>
              <Typography
                variant="h6"
                sx={{ fontWeight: 800, fontVariantNumeric: "tabular-nums" }}
              >
                {insight.counts.allies ?? "–"} : {insight.counts.axis ?? "–"}
              </Typography>
              <Typography
                variant="caption"
                sx={{
                  color: insight.countUnbalanced
                    ? "error.main"
                    : "success.main",
                  fontWeight: 700,
                }}
              >
                {insight.countUnbalanced
                  ? t("liveViews.balance.switchesRequired", {
                      count: status.required_switches,
                    })
                  : t("liveViews.balance.balanced")}
              </Typography>
            </Metric>
            <Metric label={t("liveViews.balance.teamStrength")}>
              <Typography
                variant="body2"
                sx={{
                  color: teamColors[insight.weakerTeam],
                  fontWeight: 700,
                }}
              >
                {insight.weakerTeam
                  ? t("liveViews.balance.weaker", {
                      team: insight.teamLabels[insight.weakerTeam],
                    })
                  : t("liveViews.balance.notMeasurable")}
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: teamColors[insight.strongerTeam],
                  fontWeight: 700,
                }}
              >
                {insight.strongerTeam
                  ? t("liveViews.balance.stronger", {
                      team: insight.teamLabels[insight.strongerTeam],
                    })
                  : ""}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("liveViews.balance.strengthSummary", {
                  allies: formatRating(insight.ratings.allies),
                  axis: formatRating(insight.ratings.axis),
                  gap: formatRating(insight.ratingDifference),
                })}
              </Typography>
            </Metric>
            <Metric label={t("liveViews.balance.confidence")}>
              <Typography
                variant="body2"
                sx={{
                  color: qualityColor(insight.effectiveConfidence),
                  fontWeight: 800,
                }}
              >
                {qualityLabel(t, insight.effectiveConfidence)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("liveViews.balance.currentSnapshot")} ·{" "}
                {Number.isFinite(insight.effectiveConfidence)
                  ? `${Math.round(insight.effectiveConfidence * 100)} %`
                  : t("liveViews.balance.incomplete")}
              </Typography>
            </Metric>
            <Metric label={t("liveViews.balance.recommendation")}>
              <Stack direction="row" alignItems="center" spacing={0.75}>
                {["swap", "squad_move", "squad_swap"].includes(
                  insight.recommendation.kind
                ) && <SwapHorizIcon fontSize="small" aria-hidden />}
                <Typography variant="body2" sx={{ fontWeight: 800 }}>
                  {insight.recommendation.title}
                </Typography>
              </Stack>
              <Typography variant="caption" color="text.secondary">
                {insight.recommendation.detail}
              </Typography>
            </Metric>
            <Metric
              label={
                squad
                  ? t("liveViews.balance.suggestedSquad")
                  : swap
                  ? t("liveViews.balance.suggestedPlayers")
                  : t("liveViews.balance.suggestedPlayer")
              }
            >
              {squad ? (
                <>
                  {squad.squads.map((item, index) => {
                    const move = squad.moves[index];
                    return (
                      <Typography
                        key={`${item.team}:${item.squad_name}`}
                        variant="body2"
                        sx={{ fontWeight: 800 }}
                      >
                        Squad {item.squad_name} ({item.member_count}) →{" "}
                        {insight.teamLabels[move.target_team]}
                      </Typography>
                    );
                  })}
                  <Typography variant="caption" color="text.secondary">
                    {t("liveViews.balance.membersNotified")}
                  </Typography>
                </>
              ) : swap ? (
                <>
                  <Typography
                    variant="body2"
                    sx={{
                      color: teamColors[swap.weaker_team],
                      fontWeight: 800,
                    }}
                  >
                    <Box
                      component="span"
                      sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                    >
                      <span>{swap.stronger_player?.player_name}</span>
                      <ArrowForwardIcon sx={{ fontSize: 16 }} aria-hidden />
                      <span>{insight.teamLabels[swap.weaker_team]}</span>
                    </Box>
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{
                      color: teamColors[swap.stronger_team],
                      fontWeight: 800,
                    }}
                  >
                    <Box
                      component="span"
                      sx={{ display: "flex", alignItems: "center", gap: 0.5 }}
                    >
                      <span>{swap.weaker_player?.player_name}</span>
                      <ArrowForwardIcon sx={{ fontSize: 16 }} aria-hidden />
                      <span>{insight.teamLabels[swap.stronger_team]}</span>
                    </Box>
                  </Typography>
                </>
              ) : proposalName ? (
                <>
                  <Typography variant="body2" sx={{ fontWeight: 800 }}>
                    {proposalName}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {t("liveViews.balance.destination", {
                      team:
                        insight.teamLabels[insight.targetTeam] ||
                        t("liveViews.balance.otherTeam"),
                    })}
                  </Typography>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  {t("liveViews.balance.noSuggestion")}
                </Typography>
              )}
            </Metric>
            <Metric label={t("liveViews.balance.forecast")} divider={false}>
              <Typography
                variant="body2"
                sx={{
                  color:
                    Number.isFinite(insight.projectedGap) &&
                    insight.projectedGap <=
                      (status.strength_thresholds?.soft_limit ?? 8)
                      ? "success.main"
                      : "text.primary",
                  fontWeight: 800,
                }}
              >
                {Number.isFinite(insight.projectedGap)
                  ? insight.projectedGap <=
                    (status.strength_thresholds?.soft_limit ?? 8)
                    ? t("liveViews.balance.nearlyBalanced")
                    : t("liveViews.balance.gapPoints", {
                        gap: formatRating(insight.projectedGap),
                      })
                  : t("liveViews.balance.noForecast")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {Number.isFinite(insight.projectedGap)
                  ? t("liveViews.balance.beforeGap", {
                      gap: formatRating(insight.beforeGap),
                    })
                  : t("liveViews.balance.noProjection")}
              </Typography>
            </Metric>
          </Box>

          <Collapse in={explanationOpen}>
            <Box
              sx={{
                px: 1.5,
                py: 1.25,
                borderBottom: "1px solid",
                borderColor: "divider",
                bgcolor: (theme) => alpha(theme.palette.info.main, 0.07),
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {t("liveViews.balance.snapshotTitle")}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {t("liveViews.balance.snapshotExplanation")}
              </Typography>
            </Box>
          </Collapse>
        </Box>
      </Collapse>

      <Stack
        direction={{ xs: "column", lg: "row" }}
        alignItems={{ lg: "center" }}
        gap={1.5}
        sx={{ px: 1.5, py: 1.25 }}
      >
        <Stack
          direction={{ xs: "column", sm: "row" }}
          alignItems={{ sm: "center" }}
          gap={1.5}
          sx={{ minWidth: 0, flex: 1 }}
        >
          <StrengthBar
            label={t("liveViews.balance.indexLive")}
            allies={insight.ratings.allies}
            axis={insight.ratings.axis}
          />
          {hasProjection ? (
            <>
              <ArrowForwardIcon
                sx={{ color: "text.secondary", alignSelf: "center" }}
                aria-hidden
              />
              <StrengthBar
                label={t("liveViews.balance.indexForecast")}
                allies={insight.projectedRatings.allies}
                axis={insight.projectedRatings.axis}
              />
            </>
          ) : (
            <Typography variant="caption" color="text.secondary">
              {t("liveViews.balance.noForecast")}
            </Typography>
          )}
        </Stack>
        <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
          <Button
            variant={insight.needsAttention ? "contained" : "outlined"}
            disabled={recommendations.length === 0}
            onClick={() => {
              setSelectedRecommendation(0);
              setReviewOpen(true);
            }}
          >
            {squad
              ? t("liveViews.balance.reviewSquad")
              : swap
              ? t("liveViews.balance.reviewSwap")
              : proposalName
              ? t("liveViews.balance.reviewMove")
              : t("liveViews.balance.noAction")}
          </Button>
          {alternativesAvailable && (
            <Button
              variant="outlined"
              onClick={() => {
                setSelectedRecommendation(
                  Math.min(1, recommendations.length - 1)
                );
                setReviewOpen(true);
              }}
            >
              {t("liveViews.balance.alternatives")}
            </Button>
          )}
          <Button
            color="inherit"
            disabled={detailsDisabled || !expanded}
            onClick={() => setExpanded(false)}
          >
            {t("liveViews.balance.observe")}
          </Button>
        </Stack>
      </Stack>

      <Dialog
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        fullWidth
        maxWidth="md"
        aria-labelledby="live-balance-review-title"
      >
        <DialogTitle id="live-balance-review-title">
          {squad
            ? t("liveViews.balance.reviewSquadTitle")
            : swap
            ? t("liveViews.balance.reviewSwapTitle")
            : t("liveViews.balance.reviewMoveTitle")}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1.5}>
            <Alert severity="info" variant="outlined">
              {t("liveViews.balance.reviewExplanation")}
            </Alert>
            <Alert severity={reviewNotice.severity} role="status">
              <Typography variant="body2" sx={{ fontWeight: 700 }}>
                {reviewNotice.title}
              </Typography>
              {reviewNotice.description}
            </Alert>

            {recommendations.length > 1 && (
              <Box>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ display: "block", mb: 0.75 }}
                >
                  {t("liveViews.balance.selectSuggestion")}
                </Typography>
                <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
                  {recommendations.map((recommendation, index) => (
                    <Button
                      key={
                        recommendation.moves
                          ?.map(
                            (move) => `${move.source_team}:${move.squad_name}`
                          )
                          .join("+") ||
                        `${recommendation.stronger_player?.player_id}-${recommendation.weaker_player?.player_id}`
                      }
                      variant={
                        selectedRecommendation === index
                          ? "contained"
                          : "outlined"
                      }
                      onClick={() => setSelectedRecommendation(index)}
                      sx={{ borderRadius: 0, justifyContent: "flex-start" }}
                    >
                      {index === 0
                        ? t("liveViews.balance.heldSuggestion")
                        : t("liveViews.balance.alternative", { number: index })}
                    </Button>
                  ))}
                </Stack>
              </Box>
            )}

            {activeRecommendation?.kind === "squad_move" ||
            activeRecommendation?.kind === "squad_swap" ? (
              <Box data-theme-surface="panel"
                sx={{
                  display: "grid",
                  gridTemplateColumns: {
                    xs: "1fr",
                    md:
                      activeRecommendation.squads.length > 1
                        ? "1fr 1fr"
                        : "1fr",
                  },
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                {activeRecommendation.squads.map((item, index) => {
                  const move = activeRecommendation.moves[index];
                  return (
                    <Box
                      key={`${item.team}:${item.squad_name}`}
                      sx={{
                        p: 1.5,
                        borderLeft: {
                          xs: 0,
                          md: index > 0 ? "1px solid" : 0,
                        },
                        borderTop: {
                          xs: index > 0 ? "1px solid" : 0,
                          md: 0,
                        },
                        borderColor: "divider",
                      }}
                    >
                      <Typography variant="caption" color="text.secondary">
                        {insight.teamLabels[item.team]} →{" "}
                        {insight.teamLabels[move.target_team]}
                      </Typography>
                      <Typography variant="h6" sx={{ fontWeight: 800 }}>
                        Squad {item.squad_name}
                      </Typography>
                      <Typography variant="body2" color="text.secondary">
                        {t("liveViews.balance.members", {
                          count: item.member_count,
                        })}{" "}
                        ·{" "}
                        {item.members
                          .map((member) => member.player_name)
                          .join(", ")}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            ) : activeRecommendation?.kind === "strength_swap" ? (
              <Box data-theme-surface="panel"
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                  border: "1px solid",
                  borderColor: "divider",
                }}
              >
                {[
                  {
                    player: activeRecommendation.stronger_player,
                    target: activeRecommendation.weaker_team,
                  },
                  {
                    player: activeRecommendation.weaker_player,
                    target: activeRecommendation.stronger_team,
                  },
                ].map(({ player, target }, index) => (
                  <Box
                    key={player.player_id}
                    sx={{
                      p: 1.5,
                      borderRight: { xs: 0, md: index === 0 ? "1px solid" : 0 },
                      borderBottom: {
                        xs: index === 0 ? "1px solid" : 0,
                        md: 0,
                      },
                      borderColor: "divider",
                    }}
                  >
                    <Typography variant="caption" color="text.secondary">
                      {insight.teamLabels[player.team]} →{" "}
                      {insight.teamLabels[target]}
                    </Typography>
                    <Typography variant="h6" sx={{ fontWeight: 800 }}>
                      {player.player_name}
                    </Typography>
                    <Typography variant="body2" color="text.secondary">
                      {player.unit_name || t("liveViews.balance.noSquad")} ·{" "}
                      {player.role
                        ? formatRoleLabel(t, player.role)
                        : t("liveViews.balance.unknownRole")}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      {t("liveViews.balance.playerStrength", {
                        rating: formatRating(player.rating),
                        confidence: Math.round(
                          (player.rating_confidence || 0) * 100
                        ),
                      })}
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : activeRecommendation ? (
              <Box data-theme-surface="panel" sx={{ p: 1.5, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="caption" color="text.secondary">
                  {insight.teamLabels[activeRecommendation.player.team]} →{" "}
                  {insight.teamLabels[activeRecommendation.target_team]}
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {activeRecommendation.player.player_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {activeRecommendation.player.unit_name ||
                    t("liveViews.balance.noSquad")}{" "}
                  ·{" "}
                  {activeRecommendation.player.role
                    ? formatRoleLabel(t, activeRecommendation.player.role)
                    : t("liveViews.balance.unknownRole")}
                </Typography>
              </Box>
            ) : null}

            <Box
              sx={{
                borderLeft: "3px solid",
                borderColor: "info.main",
                bgcolor: (theme) => alpha(theme.palette.info.main, 0.06),
              }}
            >
              <Box sx={{ p: 1.25 }}>
                <Typography variant="body2" sx={{ fontWeight: 800 }}>
                  {t("liveViews.balance.indexMeaning")}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  {t("liveViews.balance.indexExplanation")}
                </Typography>
              </Box>
              <Box
                sx={{
                  display: "grid",
                  gridTemplateColumns: { xs: "1fr", md: "repeat(2, 1fr)" },
                  borderTop: "1px solid",
                  borderColor: "divider",
                  "& > div": { p: 1.25 },
                  "& > div:nth-of-type(even)": {
                    borderLeft: { md: "1px solid" },
                    borderColor: "divider",
                  },
                  "& > div:nth-of-type(n+2)": {
                    borderTop: { xs: "1px solid", md: 0 },
                    borderColor: "divider",
                  },
                  "& > div:nth-of-type(n+3)": {
                    borderTop: { md: "1px solid" },
                    borderColor: "divider",
                  },
                }}
              >
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    {t("liveViews.balance.readingTitle")}
                  </Typography>
                  <Typography variant="caption">
                    {t("liveViews.balance.readingExplanation")}
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    {t("liveViews.balance.calculationTitle")}
                  </Typography>
                  <Typography variant="caption">
                    {t("liveViews.balance.calculationExplanation")}
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    {t("liveViews.balance.teamCalculationTitle")}
                  </Typography>
                  <Typography variant="caption">
                    {t("liveViews.balance.teamCalculationExplanation")}
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    {t("liveViews.balance.confidenceTitle")}
                  </Typography>
                  <Typography variant="caption">
                    {t("liveViews.balance.confidenceExplanation")}
                  </Typography>
                </Box>
              </Box>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{
                  display: "block",
                  p: 1.25,
                  borderTop: "1px solid",
                  borderColor: "divider",
                }}
              >
                {t("liveViews.balance.excludedData")}
              </Typography>
            </Box>

            <Box data-theme-surface="panel"
              sx={{
                display: "grid",
                gridTemplateColumns: { xs: "1fr", sm: "repeat(3, 1fr)" },
                border: "1px solid",
                borderColor: "divider",
                "& > div": { p: 1.25 },
                "& > div + div": {
                  borderLeft: { sm: "1px solid" },
                  borderTop: { xs: "1px solid", sm: 0 },
                  borderColor: "divider",
                },
              }}
            >
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("liveViews.balance.playerCount")}
                </Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {insight.counts.allies} : {insight.counts.axis}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("liveViews.balance.gapBefore")}
                </Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {formatRating(activeRecommendation?.rating_gap_before)}{" "}
                  {t("liveViews.balance.indexPoints")}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  {t("liveViews.balance.gapAfter")}
                </Typography>
                <Typography
                  variant="subtitle1"
                  sx={{ color: "success.main", fontWeight: 800 }}
                >
                  {formatRating(activeRecommendation?.projected_rating_gap)}{" "}
                  {t("liveViews.balance.indexPoints")}
                </Typography>
              </Box>
            </Box>

            <Typography variant="caption" color="text.secondary">
              {t("liveViews.balance.executionExplanation")}
            </Typography>
            {squad && !status.coordinated_squad_switches_enabled && (
              <Alert severity="warning" variant="outlined">
                {t("liveViews.balance.squadDisabled")}
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 1.5 }}>
          <Button color="inherit" onClick={() => setReviewOpen(false)}>
            {t("liveViews.balance.close")}
          </Button>
          {activeRecommendation && (
            <ActionButton
              action={reviewedAction}
              recipients={actionRecipients}
              params={squadActionParams}
              label={
                activeRecommendation.kind === "squad_move" ||
                activeRecommendation.kind === "squad_swap"
                  ? t("liveViews.balance.executeSquads")
                  : activeRecommendation.kind === "strength_swap"
                  ? t("liveViews.balance.executeSwap")
                  : t("liveViews.balance.executeMove")
              }
              {...(!activeValid ||
              insight.blocked ||
              ((activeRecommendation.kind === "squad_move" ||
                activeRecommendation.kind === "squad_swap") &&
                !status.coordinated_squad_switches_enabled)
                ? { disabled: true }
                : {})}
              variant="contained"
              onBeforeAction={() => setReviewOpen(false)}
              sx={{ minHeight: 40 }}
            />
          )}
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default AutobalancerCard;
