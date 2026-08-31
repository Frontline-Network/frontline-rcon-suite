import { useEffect, useMemo, useState } from "react";
import {
  Box,
  Button,
  Chip,
  Collapse,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import { alpha } from "@mui/material/styles";
import ArrowForwardIcon from "@mui/icons-material/ArrowForward";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import InfoOutlinedIcon from "@mui/icons-material/InfoOutlined";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import SwapHorizIcon from "@mui/icons-material/SwapHoriz";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import { cmd } from "@/utils/fetchUtils";
import { useAuth } from "@/hooks/useAuth";

const TEAM_COLORS = {
  allies: "#65a9d6",
  axis: "#ed6259",
};

const PHASE_LABELS = {
  idle: "Bereit",
  observing: "Beobachtung",
  volunteer: "Freiwilligenphase",
  proposed: "Vorschlag",
  armed: "Beim nächsten Tod",
  verifying: "Bestätigung läuft",
  cooldown: "Wartezeit",
  blocked: "Blockiert",
};

const MODE_LABELS = {
  disabled: "Aus",
  shadow: "Shadow – nur beobachten",
  manual: "Manuell",
  auto: "Automatisch",
};

const clamp = (value, minimum, maximum) =>
  Math.min(maximum, Math.max(minimum, value));

const formatRating = (value) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat("de-DE", { maximumFractionDigits: 1 }).format(value)
    : "–";

const qualityLabel = (confidence) => {
  if (!Number.isFinite(confidence)) return "Nicht messbar";
  if (confidence >= 0.8) return "Hohe Sicherheit";
  if (confidence >= 0.6) return "Mittlere Sicherheit";
  return "Nur als Hinweis";
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

const AutobalancerCard = ({ onHighlightPlayers }) => {
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const [expanded, setExpanded] = useState(true);
  const [explanationOpen, setExplanationOpen] = useState(false);
  const canViewAutobalancer =
    permissions?.is_superuser ||
    permissions?.permissions?.some(
      ({ permission }) => permission === "can_view_autobalancer"
    );
  const { data: status, isError } = useQuery({
    queryKey: [{ queryIdentifier: "get_autobalancer_status" }],
    queryFn: cmd.GET_AUTOBALANCER_STATUS,
    enabled: Boolean(canViewAutobalancer),
    refetchInterval: 5_000,
    retry: false,
  });
  const refresh = () =>
    queryClient.invalidateQueries({
      queryKey: [{ queryIdentifier: "get_autobalancer_status" }],
    });
  const approve = useMutation({
    mutationFn: () =>
      cmd.APPROVE_AUTOBALANCER({
        payload: { decision_id: status?.decision_id },
      }),
    onSuccess: refresh,
  });
  const cancel = useMutation({
    mutationFn: () =>
      cmd.CANCEL_AUTOBALANCER({
        payload: {
          incident_id: status?.incident_id,
          reason: "Über die Teamansicht abgebrochen",
        },
      }),
    onSuccess: refresh,
  });

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
      headline = "Teamstärke unausgeglichen";
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

  if (!canViewAutobalancer || isError || !status || !insight) return null;

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

  return (
    <Box
      component="section"
      aria-label="Live-Balance-Assistent"
      sx={(theme) => ({
        mb: 1.5,
        border: "1px solid",
        borderColor: alpha(
          theme.palette[toneColor.split(".")[0]].main,
          0.65
        ),
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
            label={MODE_LABELS[status.mode] || status.mode}
            color={status.mode === "auto" ? "success" : "default"}
            sx={{ borderRadius: 0 }}
          />
          <Chip
            size="small"
            variant="outlined"
            label={PHASE_LABELS[status.phase] || status.phase}
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
            <Metric label="Teamstärke">
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
                Differenz {formatRating(insight.ratingDifference)}
              </Typography>
            </Metric>
            <Metric label="Datenqualität">
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
                Live-Daten{" "}
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
                    <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
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
                    <Box component="span" sx={{ display: "flex", alignItems: "center", gap: 0.5 }}>
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
                Die Bewertung verbindet Spielerzahl und geschätzte Teamstärke.
              </Typography>
              <Typography variant="caption" color="text.secondary">
                Ein 1:1-Tausch ist nur eine Moderator-Empfehlung und wird nie
                automatisch ausgeführt. Führungsrollen und Spezialtrupps werden
                dafür ausgeschlossen. Vor der Entscheidung bleiben Rolle,
                Truppbindung und Datenqualität zu prüfen.
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
                label="Vorher (Teamstärke)"
                allies={insight.ratings.allies}
                axis={insight.ratings.axis}
              />
              <ArrowForwardIcon
                sx={{ color: "text.secondary", alignSelf: "center" }}
                aria-hidden
              />
              <StrengthBar
                label="Nachher (Prognose)"
                allies={insight.projectedRatings.allies}
                axis={insight.projectedRatings.axis}
              />
            </Stack>
            <Stack direction={{ xs: "column", sm: "row" }} spacing={1}>
              <Button
                component={Link}
                to="/views/autobalancer"
                variant={insight.needsAttention ? "contained" : "outlined"}
                disabled={insight.blocked}
              >
                {swap
                  ? "Tausch prüfen"
                  : proposalName
                  ? "Wechsel prüfen"
                  : "Dashboard öffnen"}
              </Button>
              {alternativesAvailable && (
                <Button
                  component={Link}
                  to="/views/autobalancer"
                  variant="outlined"
                >
                  Alternativen
                </Button>
              )}
              {status.mode === "manual" && status.phase === "proposed" && (
                <Tooltip title="Gibt den bereits geprüften Vorschlag frei">
                  <Button
                    color="success"
                    variant="outlined"
                    disabled={approve.isPending}
                    onClick={() => approve.mutate()}
                  >
                    Freigeben
                  </Button>
                </Tooltip>
              )}
              {status.incident_id && (
                <Button
                  color="warning"
                  variant="outlined"
                  disabled={cancel.isPending}
                  onClick={() => cancel.mutate()}
                >
                  Abbrechen
                </Button>
              )}
              <Button color="inherit" onClick={() => setExpanded(false)}>
                Beobachten
              </Button>
            </Stack>
          </Stack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default AutobalancerCard;
