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
import {
  buildLiveBalanceStatus,
  validateLiveRecommendation,
} from "./live-balance.mjs";
import {
  balanceRecommendations,
  holdRecommendations,
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

const formatRating = (value) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 }).format(value)
    : "–";

const qualityLabel = (confidence) => {
  if (!Number.isFinite(confidence)) return "Nicht messbar";
  if (confidence >= 0.8) return "Hohe Aussagekraft";
  if (confidence >= 0.6) return "Mittlere Aussagekraft";
  return "Niedrige Aussagekraft";
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
      <Box
        role="img"
        aria-label={`${label}: Alliierte ${formatRating(
          allies
        )}, Achsenmächte ${formatRating(axis)}`}
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
  const { t } = useTranslation();
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
      allies: "Alliierte",
      axis: "Achsenmächte",
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

    let headline = "Teams ausgeglichen";
    let tone = "success";
    if (blocked) {
      headline = "Ausgleich derzeit blockiert";
      tone = "warning";
    } else if (countUnbalanced) {
      headline = "Spielerzahl unausgeglichen";
      tone = "error";
    } else if (strengthUnbalanced) {
      headline = "Geschätzte Teamstärke unausgeglichen";
      tone = "error";
    } else if (warning) {
      headline = "Balance weiter beobachten";
      tone = "warning";
    }

    const recommendation = squadRecommendation
      ? {
          kind: squadRecommendation.kind,
          title:
            squadRecommendation.kind === "squad_swap"
              ? "Koordinierter Squad-Tausch"
              : "Squad gemeinsam wechseln",
          detail: `${squadRecommendation.member_count} Spieler bleiben als Gruppe zusammen`,
        }
      : strengthSwap
      ? {
          kind: "swap",
          title: "Kontrollierter 1:1-Tausch",
          detail: "Spielerzahl bleibt unverändert",
        }
      : proposal
      ? {
          kind: "move",
          title: "Kontrollierter Teamwechsel",
          detail: `${status.required_switches || 1} Wechsel vorgesehen`,
        }
      : {
          kind: "observe",
          title:
            countUnbalanced || strengthUnbalanced
              ? "Analyse läuft"
              : "Kein Eingriff",
          detail:
            countUnbalanced || strengthUnbalanced
              ? "Noch kein sicherer Kandidat"
              : "Innerhalb der Grenzwerte",
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
  }, [status, liveStatus]);

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
              label: `${move.squad_name} gemeinsam nach ${
                insight.teamLabels[move.target_team]
              }`,
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
          label: `Empfohlen nach ${
            insight.teamLabels[insight.strengthSwap.weaker_team]
          }`,
        },
        [weaker?.player_id]: {
          targetTeam: insight.strengthSwap.stronger_team,
          label: `Empfohlen nach ${
            insight.teamLabels[insight.strengthSwap.stronger_team]
          }`,
        },
      };
    }
    if (insight.proposal?.player_id) {
      return {
        [insight.proposal.player_id]: {
          targetTeam: insight.targetTeam,
          label: `Empfohlen nach ${
            insight.teamLabels[insight.targetTeam] || "Gegenteam"
          }`,
        },
      };
    }
    return {};
  }, [insight, validated]);

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
    <Box
      component="section"
      aria-label="Live-Balance-Assistent"
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
              Live-Balance
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
              label="Direkte Live-Daten"
              color="info"
              sx={{ borderRadius: 0 }}
            />
          )}
          {expanded && (
            <Chip
              size="small"
              variant="outlined"
              label="Keine Historie nötig"
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
            Warum?
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
                Öffnen
              </Button>
            )
          )}
        </Stack>
      </Stack>

      {detailsFeedback}

      {recommendations.length > 0 && (
        <Alert
          severity={validated[0] ? "info" : "warning"}
          sx={{ borderRadius: 0 }}
          action={
            <Button
              color="inherit"
              onClick={refreshRecommendations}
              disabled={reviewOpen}
            >
              Neu bewerten
            </Button>
          }
        >
          {validated[0]
            ? "Vorschlag für 60 Sekunden festgehalten. Live-Werte und Gültigkeit werden weiter geprüft."
            : "Festgehaltener Vorschlag nicht mehr gültig: Teams, Spieler oder Voraussetzungen haben sich geändert. Kein Eingriff möglich."}
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
            <Metric label="Spielerzahl">
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
                  ? `${status.required_switches} Wechsel nötig`
                  : "Ausgeglichen"}
              </Typography>
            </Metric>
            <Metric label="Geschätzte Teamstärke">
              <Typography
                variant="body2"
                sx={{
                  color: teamColors[insight.weakerTeam],
                  fontWeight: 700,
                }}
              >
                {insight.weakerTeam
                  ? `${insight.teamLabels[insight.weakerTeam]} schwächer`
                  : "Nicht messbar"}
              </Typography>
              <Typography
                variant="body2"
                sx={{
                  color: teamColors[insight.strongerTeam],
                  fontWeight: 700,
                }}
              >
                {insight.strongerTeam
                  ? `${insight.teamLabels[insight.strongerTeam]} stärker`
                  : ""}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Stärke-Index {formatRating(insight.ratings.allies)} :{" "}
                {formatRating(insight.ratings.axis)} · Abstand{" "}
                {formatRating(insight.ratingDifference)}
              </Typography>
            </Metric>
            <Metric label="Aussagekraft">
              <Typography
                variant="body2"
                sx={{
                  color: qualityColor(insight.effectiveConfidence),
                  fontWeight: 800,
                }}
              >
                {qualityLabel(insight.effectiveConfidence)}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Aktueller Snapshot ·{" "}
                {Number.isFinite(insight.effectiveConfidence)
                  ? `${Math.round(insight.effectiveConfidence * 100)} %`
                  : "unvollständig"}
              </Typography>
            </Metric>
            <Metric label="Empfehlung">
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
                  ? "Vorgeschlagener Squad"
                  : swap
                  ? "Vorgeschlagene Spieler"
                  : "Vorgeschlagener Spieler"
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
                    Vor dem Wechsel werden alle Mitglieder informiert.
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
                    nach {insight.teamLabels[insight.targetTeam] || "Gegenteam"}
                  </Typography>
                </>
              ) : (
                <Typography variant="body2" color="text.secondary">
                  Noch kein sicherer Vorschlag
                </Typography>
              )}
            </Metric>
            <Metric label="Prognose" divider={false}>
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
                    ? "Nahezu ausgeglichen"
                    : `${formatRating(insight.projectedGap)} Punkte Abstand`
                  : "Keine Prognose verfügbar"}
              </Typography>
              <Typography variant="caption" color="text.secondary">
                {Number.isFinite(insight.projectedGap)
                  ? `vorher ${formatRating(insight.beforeGap)}`
                  : "Noch keine belastbare Projektion"}
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
                Die Bewertung entsteht sofort aus dem aktuellen Server-Snapshot.
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Spielerzahl, Level und bereits vorhandene Werte der laufenden
                Runde werden direkt ausgewertet. Frühere Runden oder eine
                Lernphase sind nicht erforderlich. Führungsrollen und
                Spezialtrupps bleiben von Vorschlägen ausgeschlossen.
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
            label="Stärke-Index Live"
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
                label="Stärke-Index-Prognose"
                allies={insight.projectedRatings.allies}
                axis={insight.projectedRatings.axis}
              />
            </>
          ) : (
            <Typography variant="caption" color="text.secondary">
              Keine Prognose verfügbar
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
              ? "Squad-Wechsel prüfen"
              : swap
              ? "Tausch prüfen"
              : proposalName
              ? "Wechsel prüfen"
              : "Kein Eingriff nötig"}
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
              Alternativen
            </Button>
          )}
          <Button
            color="inherit"
            disabled={detailsDisabled || !expanded}
            onClick={() => setExpanded(false)}
          >
            Beobachten
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
            ? "Koordinierten Squad-Wechsel prüfen"
            : swap
            ? "Live-Tausch prüfen"
            : "Live-Teamwechsel prüfen"}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1.5}>
            <Alert severity="info" variant="outlined">
              Grundlage ist ausschließlich der aktuelle Server-Snapshot. Es muss
              keine Historie gesammelt werden. Ausgeführt wird erst nach der
              regulären Sicherheitsbestätigung.
            </Alert>
            <Alert severity={activeValid ? "info" : "warning"}>
              {activeValid
                ? "Diese Auswahl bleibt bis zum Schließen unverändert. Vor der Ausführung wird sie erneut mit frischen Live-Daten geprüft."
                : "Dieser Vorschlag ist nicht mehr gültig. Es wird kein Wechsel ausgeführt. Dialog schließen und neu bewerten."}
            </Alert>

            {recommendations.length > 1 && (
              <Box>
                <Typography
                  variant="overline"
                  color="text.secondary"
                  sx={{ display: "block", mb: 0.75 }}
                >
                  Vorschlag auswählen
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
                        ? "Festgehaltener Vorschlag"
                        : `Alternative ${index}`}
                    </Button>
                  ))}
                </Stack>
              </Box>
            )}

            {activeRecommendation?.kind === "squad_move" ||
            activeRecommendation?.kind === "squad_swap" ? (
              <Box
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
                        {item.member_count} Mitglieder ·{" "}
                        {item.members
                          .map((member) => member.player_name)
                          .join(", ")}
                      </Typography>
                    </Box>
                  );
                })}
              </Box>
            ) : activeRecommendation?.kind === "strength_swap" ? (
              <Box
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
                      {player.unit_name || "Kein Trupp"} ·{" "}
                      {player.role || "Rolle unbekannt"}
                    </Typography>
                    <Typography variant="caption" color="text.secondary">
                      Stärke-Index {formatRating(player.rating)} / 100 ·
                      Aussagekraft{" "}
                      {Math.round((player.rating_confidence || 0) * 100)} %
                    </Typography>
                  </Box>
                ))}
              </Box>
            ) : activeRecommendation ? (
              <Box sx={{ p: 1.5, border: "1px solid", borderColor: "divider" }}>
                <Typography variant="caption" color="text.secondary">
                  {insight.teamLabels[activeRecommendation.player.team]} →{" "}
                  {insight.teamLabels[activeRecommendation.target_team]}
                </Typography>
                <Typography variant="h6" sx={{ fontWeight: 800 }}>
                  {activeRecommendation.player.player_name}
                </Typography>
                <Typography variant="body2" color="text.secondary">
                  {activeRecommendation.player.unit_name || "Kein Trupp"} ·{" "}
                  {activeRecommendation.player.role || "Rolle unbekannt"}
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
                  Was bedeutet der Stärke-Index?
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Er vergleicht ausschließlich die Spieler, die jetzt auf diesem
                  Server verbunden sind. Der Wert ist kein offizieller Rang und
                  keine dauerhafte Bewertung eines Spielers.
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
                    So liest du den Wert
                  </Typography>
                  <Typography variant="caption">
                    0 steht für das untere, 100 für das obere Ende des aktuellen
                    Spielerfeldes. 50 ist die Mitte dieses Feldes. Der Index
                    lässt sich deshalb nur innerhalb des gerade laufenden
                    Servers vergleichen.
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    So wird er berechnet
                  </Typography>
                  <Typography variant="caption">
                    Sobald Rundenwerte vorliegen, zählen das Spielerlevel zu 45
                    % und die aktuelle Rundenleistung zu 55 %. Dafür werden
                    Kills, Kampfwert sowie Offensive, Defensive und Support pro
                    Minute miteinander verglichen.
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    So entsteht die Teamstärke
                  </Typography>
                  <Typography variant="caption">
                    Die Indizes aller Spieler eines Teams werden gemittelt.
                    Stehen die Teams beispielsweise bei 53 zu 47, beträgt der
                    Team-Abstand 6 Indexpunkte. Je näher der Abstand an 0 liegt,
                    desto ähnlicher ist die geschätzte Teamstärke.
                  </Typography>
                </Box>
                <Box>
                  <Typography
                    variant="overline"
                    color="text.secondary"
                    sx={{ display: "block" }}
                  >
                    Was bedeutet Aussagekraft?
                  </Typography>
                  <Typography variant="caption">
                    Ohne verwertbare Rundenwerte dient das Level sofort als
                    vorläufige Schätzung. Ist ein Level vorhanden, startet die
                    Aussagekraft bei 65 % und steigt mit Live-Werten während der
                    ersten 15 Spielminuten auf bis zu 100 %. Fehlt auch das
                    Level, wird die Aussagekraft entsprechend niedriger
                    ausgewiesen. Früh in der Runde sollte der Vorschlag daher
                    vorsichtiger bewertet werden.
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
                Nicht einbezogen werden frühere Runden, Siege,
                Clan-Zugehörigkeit, VIP-Status oder Moderationsmaßnahmen.
                Führungsrollen und Spezialtrupps zählen zur Teamstärke, werden
                aber nicht als Tausch-Kandidaten vorgeschlagen.
              </Typography>
            </Box>

            <Box
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
                  Spielerzahl
                </Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {insight.counts.allies} : {insight.counts.axis}
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Team-Abstand vorher
                </Typography>
                <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
                  {formatRating(activeRecommendation?.rating_gap_before)}{" "}
                  Indexpunkte
                </Typography>
              </Box>
              <Box>
                <Typography variant="caption" color="text.secondary">
                  Team-Abstand danach
                </Typography>
                <Typography
                  variant="subtitle1"
                  sx={{ color: "success.main", fontWeight: 800 }}
                >
                  {formatRating(activeRecommendation?.projected_rating_gap)}{" "}
                  Indexpunkte
                </Typography>
              </Box>
            </Box>

            <Typography variant="caption" color="text.secondary">
              Der Live-Assistent führt keinen automatischen Wechsel aus. Vor
              einer Squad-Aktion werden Live-Mitglieder, Teamzuordnung und
              Berechtigungen nochmals geprüft. Alle Mitglieder erhalten zuerst
              eine Nachricht; danach müssen sie ihren Squad im Zielteam neu
              bilden.
            </Typography>
            {squad && !status.coordinated_squad_switches_enabled && (
              <Alert severity="warning" variant="outlined">
                Koordinierte Squad-Wechsel sind in den
                Autobalancer-Einstellungen noch deaktiviert. Aktiviere sie dort,
                bevor diese Moderationsaktion ausgeführt werden kann.
              </Alert>
            )}
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 1.5 }}>
          <Button color="inherit" onClick={() => setReviewOpen(false)}>
            Schließen
          </Button>
          {activeRecommendation && (
            <ActionButton
              action={reviewedAction}
              recipients={actionRecipients}
              params={squadActionParams}
              label={
                activeRecommendation.kind === "squad_move" ||
                activeRecommendation.kind === "squad_swap"
                  ? "Squad(s) informieren und wechseln"
                  : activeRecommendation.kind === "strength_swap"
                  ? "Beide Teams wechseln"
                  : "Spieler jetzt wechseln"
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
