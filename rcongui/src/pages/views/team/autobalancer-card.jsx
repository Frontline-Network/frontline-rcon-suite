import { useEffect, useMemo, useState } from "react";
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
  Stack,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import { ActionButton } from "@/features/player-action/ActionMenu";
import { Actions } from "@/features/player-action/actions";
import { buildLiveBalanceStatus } from "./live-balance.mjs";

const TEAM_COLORS = {
  allies: "#65a9d6",
  axis: "#ed6259",
};

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
        <Box sx={{ width: `${alliesShare}%`, bgcolor: TEAM_COLORS.allies }} />
        <Box sx={{ flex: 1, bgcolor: TEAM_COLORS.axis }} />
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

const AutobalancerCard = ({ teams, onHighlightPlayers }) => {
  const [expanded, setExpanded] = useState(true);
  const [explanationOpen, setExplanationOpen] = useState(false);
  const [reviewOpen, setReviewOpen] = useState(false);
  const [selectedRecommendation, setSelectedRecommendation] = useState(0);
  const status = useMemo(() => buildLiveBalanceStatus(teams), [teams]);

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
      Boolean(status.strength_swap) ||
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
    const strengthSwap = status.strength_swap;
    const proposal = status.proposal;
    const plan = status.plan || {};
    const targetTeam = plan.target_team;
    const projectedGap =
      strengthSwap?.projected_rating_gap ?? plan.projected_rating_gap;
    const beforeGap =
      strengthSwap?.rating_gap_before ??
      plan.rating_gap_before ??
      ratingDifference;
    const dataConfidence = Number(status.data_confidence);
    const pairConfidence = Number(strengthSwap?.rating_confidence);
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

    const recommendation = strengthSwap
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

    const projectedRatings = (() => {
      if (!Number.isFinite(projectedGap) || !strongerTeam) return ratings;
      const midpoint = (ratings.allies + ratings.axis) / 2;
      const halfGap = projectedGap / 2;
      return {
        allies:
          strongerTeam === "allies" ? midpoint + halfGap : midpoint - halfGap,
        axis: strongerTeam === "axis" ? midpoint + halfGap : midpoint - halfGap,
      };
    })();

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
        Boolean(proposal),
    };
  }, [status]);

  const highlights = useMemo(() => {
    if (!insight) return {};
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
  }, [insight]);

  useEffect(() => {
    onHighlightPlayers?.(highlights);
    return () => onHighlightPlayers?.({});
  }, [highlights, onHighlightPlayers]);

  useEffect(() => {
    if (insight?.needsAttention) setExpanded(true);
  }, [insight?.headline]);

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
  const proposalName = insight.proposal?.player_name;
  const alternativesAvailable =
    (status.strength_swap_alternatives || []).length > 0 ||
    Object.values(status.strategy_plans || {}).filter(Boolean).length > 1;
  const recommendations = swap
    ? [swap, ...(status.strength_swap_alternatives || [])]
    : insight.proposal
    ? [
        {
          kind: "move",
          target_team: insight.targetTeam,
          player: insight.proposal,
          rating_gap_before: insight.beforeGap,
          projected_rating_gap: insight.projectedGap,
          rating_confidence: insight.proposal.rating_confidence,
        },
      ]
    : [];
  const activeRecommendation =
    recommendations[
      Math.min(selectedRecommendation, recommendations.length - 1)
    ];
  const actionRecipients = activeRecommendation
    ? activeRecommendation.kind === "strength_swap"
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
          borderBottom: expanded ? "1px solid" : 0,
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
          <Chip
            size="small"
            label="Direkte Live-Daten"
            color="info"
            sx={{ borderRadius: 0 }}
          />
          <Chip
            size="small"
            variant="outlined"
            label="Keine Historie nötig"
            sx={{ borderRadius: 0 }}
          />
          <Button
            size="small"
            color="inherit"
            startIcon={<InfoOutlinedIcon />}
            onClick={() => {
              setExpanded(true);
              setExplanationOpen((value) => !value);
            }}
          >
            Warum?
          </Button>
          {!expanded && (
            <Button size="small" onClick={() => setExpanded(true)}>
              Öffnen
            </Button>
          )}
        </Stack>
      </Stack>

      <Collapse in={expanded}>
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
                  color: TEAM_COLORS[insight.weakerTeam],
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
                  color: TEAM_COLORS[insight.strongerTeam],
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
                {insight.recommendation.kind === "swap" && (
                  <SwapHorizIcon fontSize="small" aria-hidden />
                )}
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
                swap ? "Vorgeschlagene Spieler" : "Vorgeschlagener Spieler"
              }
            >
              {swap ? (
                <>
                  <Typography
                    variant="body2"
                    sx={{
                      color: TEAM_COLORS[swap.weaker_team],
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
                      color: TEAM_COLORS[swap.stronger_team],
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
                  : insight.needsAttention
                  ? "Prüfung nötig"
                  : "Stabil"}
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
                label="Stärke-Index vorher"
                allies={insight.ratings.allies}
                axis={insight.ratings.axis}
              />
              <ArrowForwardIcon
                sx={{ color: "text.secondary", alignSelf: "center" }}
                aria-hidden
              />
              <StrengthBar
                label="Stärke-Index nachher"
                allies={insight.projectedRatings.allies}
                axis={insight.projectedRatings.axis}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button
                variant={insight.needsAttention ? "contained" : "outlined"}
                disabled={insight.blocked || recommendations.length === 0}
                onClick={() => {
                  setSelectedRecommendation(0);
                  setReviewOpen(true);
                }}
              >
                {swap
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
              <Button color="inherit" onClick={() => setExpanded(false)}>
                Beobachten
              </Button>
            </Stack>
          </Stack>
        </Box>
      </Collapse>

      <Dialog
        open={reviewOpen}
        onClose={() => setReviewOpen(false)}
        fullWidth
        maxWidth="md"
        aria-labelledby="live-balance-review-title"
      >
        <DialogTitle id="live-balance-review-title">
          {swap ? "Live-Tausch prüfen" : "Live-Teamwechsel prüfen"}
        </DialogTitle>
        <DialogContent dividers>
          <Stack spacing={1.5}>
            <Alert severity="info" variant="outlined">
              Grundlage ist ausschließlich der aktuelle Server-Snapshot. Es muss
              keine Historie gesammelt werden. Ausgeführt wird erst nach der
              regulären Sicherheitsbestätigung.
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
                      key={`${recommendation.stronger_player?.player_id}-${recommendation.weaker_player?.player_id}`}
                      variant={
                        selectedRecommendation === index
                          ? "contained"
                          : "outlined"
                      }
                      onClick={() => setSelectedRecommendation(index)}
                      sx={{ borderRadius: 0, justifyContent: "flex-start" }}
                    >
                      {index === 0 ? "Beste Prognose" : `Alternative ${index}`}
                    </Button>
                  ))}
                </Stack>
              </Box>
            )}

            {activeRecommendation?.kind === "strength_swap" ? (
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
                p: 1.25,
                borderLeft: "3px solid",
                borderColor: "info.main",
                bgcolor: (theme) => alpha(theme.palette.info.main, 0.06),
              }}
            >
              <Typography variant="body2" sx={{ fontWeight: 800 }}>
                Was bedeutet der Stärke-Index?
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Er ist eine Vergleichsskala von 0 bis 100 für die aktuell
                verbundenen Spieler. 50 entspricht dem momentanen
                Server-Durchschnitt; ein höherer Wert bedeutet eine stärkere
                aktuelle Einschätzung. Berechnet wird er aus Spielerlevel und
                den bereits vorhandenen Werten dieser Runde – er ist kein
                offizieller Rang des Gameservers.
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
              Der Live-Assistent führt keinen automatischen Wechsel aus. Die
              vorhandene Moderationsaktion prüft Berechtigung und Zielspieler
              nochmals unmittelbar vor dem RCON-Befehl.
            </Typography>
          </Stack>
        </DialogContent>
        <DialogActions sx={{ p: 1.5 }}>
          <Button color="inherit" onClick={() => setReviewOpen(false)}>
            Schließen
          </Button>
          {activeRecommendation && (
            <ActionButton
              action={Actions.SwitchPlayer}
              recipients={actionRecipients}
              label={
                activeRecommendation.kind === "strength_swap"
                  ? "Beide Teams wechseln"
                  : "Spieler jetzt wechseln"
              }
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
