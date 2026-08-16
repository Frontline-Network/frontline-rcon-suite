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
  LinearProgress,
  Stack,
  Tab,
  Tabs,
  Typography,
  alpha,
} from "@mui/material";
import { useMemo, useState } from "react";
import AutobalancerHistoryDashboard from "@/pages/settings/[configs]/autobalancer-history-dashboard";
import AutobalancerRoundHistory from "@/pages/settings/[configs]/autobalancer-round-history";
import AutobalancerShadowCharts from "@/pages/settings/[configs]/autobalancer-shadow-charts";

const MODE_LABELS = {
  disabled: "Ausgeschaltet",
  shadow: "Shadow-Modus",
  manual: "Manueller Betrieb",
  auto: "Automatischer Betrieb",
};

const PHASE_LABELS = {
  idle: "Kein Eingriff nötig",
  observing: "Ungleichgewicht wird beobachtet",
  volunteer: "Freiwillige werden gesucht",
  proposed: "Vorschlag liegt vor",
  armed: "Kandidat ist vorgemerkt",
  verifying: "Wechsel wird bestätigt",
  cooldown: "Stabilitätsprüfung läuft",
  blocked: "Sicherheitsbedingung blockiert",
};

const STRATEGY_LABELS = {
  "squad-first": "Squad zuerst",
  "balanced-v2": "Ausgewogen V2",
  "skill-first": "Stärke zuerst",
};

const ROLE_FAMILY_LABELS = {
  combat_infantry: "Combat Infantry",
  support: "Support / Engineer / Medic",
  commander: "Commander",
  leader: "Squad Leader",
  specialist: "Armor / Recon / Artillery / Mortar / Helicopter",
};

const REVIEW_CATEGORY_LABELS = {
  squad_should_stay: "Squad sollte zusammenbleiben",
  critical_role: "Rolle ist spielerisch zu wichtig",
  recent_join_or_move: "Verbindungs- oder Squadzeit wirkt falsch",
  better_candidate: "Ein anderer Kandidat wäre fairer",
  skill_balance: "Stärkeausgleich ist nicht überzeugend",
  wrong_team_counts: "Teamzählung oder Wechselzahl ist falsch",
  other: "Anderer Grund",
};

const formatPercent = (value) =>
  Number.isFinite(value) ? `${Math.round(value * 100)} %` : "Noch keine Daten";

const formatNumber = (value, digits = 1) =>
  Number.isFinite(value)
    ? new Intl.NumberFormat("de-DE", {
        minimumFractionDigits: digits,
        maximumFractionDigits: digits,
      }).format(value)
    : "–";

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("de-DE", {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "–";

const formatMinutes = (seconds) =>
  Number.isFinite(seconds) ? `${Math.floor(seconds / 60)} Min.` : "unbekannt";

const getTeamLabels = (value) =>
  value?.team_labels || { allies: "Allies", axis: "Axis" };

const getModeStatus = (mode) => {
  if (mode === "shadow") {
    return {
      title: "Sicherer Testbetrieb",
      detail: "Keine Nachrichten und keine automatischen Spielerwechsel",
      color: "info",
    };
  }
  if (mode === "manual") {
    return {
      title: "Manueller Betrieb",
      detail: "Jeder Vorschlag benötigt eine Freigabe",
      color: "warning",
    };
  }
  if (mode === "auto") {
    return {
      title: "Automatischer Betrieb",
      detail: "Freigaben erfolgen nach den konfigurierten Regeln",
      color: "success",
    };
  }
  return {
    title: "Autobalancer ausgeschaltet",
    detail: "Es werden keine neuen Balancevorfälle bearbeitet",
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
    ? "Unbekannt"
    : tier <= 1
    ? "Gering"
    : tier <= 2
    ? "Mittel"
    : "Hoch";
  const countImproves = projection
    ? projection.after.difference < projection.before.difference
    : null;
  const hasWarnings = Boolean(decision?.audit_warnings?.length);

  if (hasWarnings || countImproves === null) {
    return {
      label: "Nicht bewerten",
      color: "error",
      title: "Daten zuerst prüfen",
      explanation:
        "Der Sicherheitsnachweis enthält Warnungen oder die Teamzählung ist unvollständig. Dieser Vorschlag sollte nicht als faire Referenz bewertet werden.",
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

  if (protectedRole || squadImpact === "Hoch") {
    return {
      label: "Eher ablehnen",
      color: "warning",
      title: "Der Eingriff in Rolle oder Squad ist zu groß",
      explanation:
        "Die Spielerzahl kann sich verbessern, aber der Kandidat ist spielerisch stark gebunden. Prüfe zuerst eine weniger geschützte Alternative.",
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
      label: "Akzeptabel",
      color: "success",
      title: "Der Vorschlag verbessert beide Balanceziele",
      explanation:
        "Spielerzahl und geschätzte Teamstärke werden besser, ohne eine geschützte Rolle oder einen stark gebundenen Squad zu treffen.",
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
    label: "Genauer prüfen",
    color: "warning",
    title: "Spielerzahl und Teamstärke müssen abgewogen werden",
    explanation:
      "Der Wechsel reduziert die Spielerzahldifferenz. Die Ratingaussage ist jedoch unsicher oder entwickelt sich nicht in dieselbe Richtung.",
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
        Für diesen Vorschlag liegt keine vollständige Teamzählung vor.
      </Alert>
    );
  }
  const totalBefore = projection.before.allies + projection.before.axis;
  const totalAfter = projection.after.allies + projection.after.axis;
  const states = [
    {
      label: "Vorher",
      ...projection.before,
      total: totalBefore,
      gap: gapBefore,
    },
    { label: "Nachher", ...projection.after, total: totalAfter, gap: gapAfter },
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
                Ratingdifferenz
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
        Zurück zu offenen Vorschlägen
      </Button>
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        gap={2}
        sx={{ mb: 2 }}
      >
        <Box>
          <Typography variant="overline" color="text.secondary">
            Vorschlag vom {formatDate(decision.created_at)}
          </Typography>
          <Typography variant="h4" sx={{ fontWeight: 700 }}>
            {decision.player_name || "Unbekannter Kandidat"} prüfen
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            {decision.map_name || "Unbekannte Karte"} ·{" "}
            {teamLabels[decision.source_team]} →{" "}
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
              ? "Als akzeptabel bewertet."
              : "Als nicht akzeptabel bewertet."}
          </strong>{" "}
          {decision.reviewed_by && `Von ${decision.reviewed_by}`}
          {decision.reviewed_at && ` am ${formatDate(decision.reviewed_at)}`}.
          {decision.review_category && (
            <>
              {" "}
              Grund: {REVIEW_CATEGORY_LABELS[decision.review_category] ||
                decision.review_category}.
            </>
          )}
          {decision.review_comment && <> Kommentar: {decision.review_comment}</>}
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
                Empfehlung
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
                title="Geschützte Rolle?"
                explanation="Commander, Squad Lead und wichtige Spezialrollen werden besonders geschützt."
                result={
                  assessment.protectedRole
                    ? "Ja · Eingriff vermeiden"
                    : "Nein · gut"
                }
              />
              <ChecklistRow
                state={
                  assessment.squadImpact === "Gering"
                    ? "good"
                    : assessment.squadImpact === "Hoch"
                    ? "bad"
                    : "uncertain"
                }
                title="Wie stark wird der Squad beeinträchtigt?"
                explanation="Bewertet Rolle, Squadgröße und bisherige Squad-Bindung."
                result={`${assessment.squadImpact} · Schutzstufe ${
                  decision.protection_tier ?? "–"
                }`}
              />
              <ChecklistRow
                state={
                  assessment.countImproves === true
                    ? "good"
                    : assessment.countImproves === false
                    ? "bad"
                    : "uncertain"
                }
                title="Spielerzahl verbessert sich?"
                explanation="Vergleicht die Teamdifferenz vor und nach genau diesem Wechsel."
                result={
                  assessment.projection
                    ? `${assessment.projection.before.difference} → ${assessment.projection.after.difference} Spieler`
                    : "Nicht messbar"
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
                title="Geschätzte Stärke verbessert sich?"
                explanation="Niedrigere Ratingdifferenz bedeutet statistisch ähnlichere Teams."
                result={`${formatNumber(assessment.gapBefore)} → ${formatNumber(
                  assessment.gapAfter
                )}`}
              />
              <ChecklistRow
                state={assessment.ratingReliable ? "good" : "uncertain"}
                title="Ratingdaten verlässlich?"
                explanation="Unter 60 % nur als Hinweis verwenden, nicht als alleinigen Grund."
                result={`${formatPercent(confidence)} Vertrauen`}
              />
            </Stack>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700, mb: 1.5 }}>
                Was verändert dieser Wechsel?
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
                Die Werte gelten für diesen Kandidaten im gespeicherten
                Snapshot. Strategie-Gesamtwerte stehen separat in den
                technischen Details.
              </Typography>
            </CardContent>
          </Card>

          {(decision.audit_warnings || []).map((warning) => (
            <Alert key={warning} severity="error">
              Automatische Regelwarnung: {warning}
            </Alert>
          ))}

          <Accordion variant="outlined" disableGutters>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                Technische Details anzeigen
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
                  Strategie:{" "}
                  {STRATEGY_LABELS[decision.strategy_version] ||
                    decision.strategy_version ||
                    "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Ratingmodell: {decision.rating_model_version || "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Effektives Rating: {Math.round(decision.rating ?? 50)}/100
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Rohwert:{" "}
                  {decision.rating_raw == null
                    ? "–"
                    : `${Math.round(decision.rating_raw)}/100`}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Rollenfamilie:{" "}
                  {ROLE_FAMILY_LABELS[decision.rating_role_family] ||
                    decision.rating_role_family ||
                    "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Historie: {decision.rating_history_source || "Legacy"}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Verbunden: {formatMinutes(decision.connected_seconds)}
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Im Squad: {formatMinutes(decision.squad_seconds)}
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
                    Wie bewertest du diesen Vorschlag?
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    Im Shadow-Modus wird nur die Bewertung gespeichert. Es wird
                    kein Spieler verschoben.
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
                      Nicht akzeptabel
                    </Button>
                    <Button color="inherit" variant="outlined" onClick={onBack}>
                      Später prüfen
                    </Button>
                    <Button
                      color="success"
                      variant="contained"
                      disabled={reviewPending || assessment.color === "error"}
                      onClick={() => onAccept(decision)}
                    >
                      Kandidat akzeptabel
                    </Button>
                  </Stack>
                ) : (
                  <Alert severity="info">
                    Zum Bewerten ist die Berechtigung „Autobalancer ausführen“
                    erforderlich.
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
                Warum dieser Spieler?
              </Typography>
              <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
                {decision.selection_reason ||
                  "Für diesen Vorschlag wurde kein Auswahlgrund gespeichert."}
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
                    {decision.unit_name || "Nicht zugewiesen"}
                  </Typography>
                </Stack>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="body2" color="text.secondary">
                    Rolle
                  </Typography>
                  <Typography
                    variant="body2"
                    sx={{ fontWeight: 700, textAlign: "right" }}
                  >
                    {decision.role || "Unbekannt"}
                  </Typography>
                </Stack>
                <Stack direction="row" justifyContent="space-between" gap={1}>
                  <Typography variant="body2" color="text.secondary">
                    Squad-Eingriff
                  </Typography>
                  <Typography variant="body2" sx={{ fontWeight: 700 }}>
                    {assessment.squadImpact}
                  </Typography>
                </Stack>
              </Stack>
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Alternative
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
                    wird von „
                    {STRATEGY_LABELS[alternative[0]] || alternative[0]}“ zuerst
                    gewählt.
                  </Typography>
                  <Stack spacing={1} sx={{ mt: 2 }}>
                    <Stack
                      direction="row"
                      justifyContent="space-between"
                      gap={1}
                    >
                      <Typography variant="body2" color="text.secondary">
                        Gesamtplan danach
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
                        Schutzstufe
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
                  Die Strategien nennen keinen anderen ersten Kandidaten.
                </Typography>
              )}
            </CardContent>
          </Card>

          <Card variant="outlined">
            <CardContent>
              <Typography variant="h6" sx={{ fontWeight: 700 }}>
                Datenqualität
              </Typography>
              <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
                <Chip
                  size="small"
                  color={decision.audit_warnings?.length ? "error" : "success"}
                  label={
                    decision.audit_warnings?.length
                      ? "Snapshot prüfen"
                      : "Snapshot vollständig"
                  }
                />
                <Chip
                  size="small"
                  color={assessment.ratingReliable ? "success" : "warning"}
                  label={
                    assessment.ratingReliable
                      ? "Rating ausreichend"
                      : "Rating unsicher"
                  }
                />
              </Stack>
              <Typography
                variant="caption"
                color="text.secondary"
                sx={{ display: "block", mt: 1.5 }}
              >
                Jede Kennzeichnung gilt nur für den genannten Datenblock.
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
  emptyMessage = "Noch keine Shadow-Vorschläge vorhanden.",
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
                    {decision.player_name || "Unbekannter Kandidat"}
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
                      ? "Spielerzahl wird besser"
                      : "Teamzählung prüfen"}
                  </Typography>
                  <Typography variant="caption" color="text.secondary">
                    {assessment.projection
                      ? `${assessment.projection.before.allies}:${assessment.projection.before.axis} → ${assessment.projection.after.allies}:${assessment.projection.after.axis}`
                      : "Keine vollständige Projektion"}
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
                      ? "Akzeptabel"
                      : decision.review_verdict === "rejected"
                      ? "Nicht akzeptabel"
                      : assessment.label
                  }
                />
                <Button
                  variant="outlined"
                  onClick={() => onOpen(decision)}
                  aria-label={`Vorschlag für ${
                    decision.player_name || "unbekannten Kandidaten"
                  } ${isReviewed ? "ansehen" : "prüfen"}`}
                >
                  {isReviewed ? "Ansehen" : "Prüfen"}
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
  const [section, setSection] = useState("live");
  const [selectedDecisionId, setSelectedDecisionId] = useState(null);
  const summary = data.summary || {};
  const goals = data.pilot_goals || {};
  const decisions = data.decisions || [];
  const status = liveStatus || data.live_status || {};
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
  const nextTask = pending.length
    ? pending.length === 1
      ? "1 Vorschlag wartet auf eine Bewertung"
      : `${pending.length} Vorschläge warten auf eine Bewertung`
    : "Aktuell wartet kein Vorschlag auf eine Bewertung";

  const openDecision = (decision) => {
    setSelectedDecisionId(decision.decision_id);
    setSection("proposals");
  };

  const switchSection = (value) => {
    setSection(value);
    if (value !== "proposals") setSelectedDecisionId(null);
  };

  if (section === "proposals" && selectedDecision) {
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
          <Typography variant="h3" sx={{ fontWeight: 700 }}>
            Autobalancer
          </Typography>
          <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
            Live-Zustand, Vorschlagsprüfung und Pilotfreigabe für Moderatoren
          </Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap">
          <Chip
            icon={config?.mode === "shadow" ? <ScienceIcon /> : <BalanceIcon />}
            color={modeStatus.color}
            label={
              MODE_LABELS[config?.mode] || config?.mode || "Unbekannter Modus"
            }
          />
          <Button
            startIcon={<RefreshIcon />}
            variant="outlined"
            disabled={isFetching}
            onClick={onRefresh}
          >
            Aktualisieren
          </Button>
        </Stack>
      </Stack>

      <Tabs
        value={section}
        onChange={(_, value) => switchSection(value)}
        variant="scrollable"
        scrollButtons="auto"
        allowScrollButtonsMobile
        sx={{ mt: 2, borderBottom: 1, borderColor: "divider" }}
      >
        <Tab
          value="live"
          icon={<InsightsIcon />}
          iconPosition="start"
          label="Live"
        />
        <Tab
          value="proposals"
          icon={<PlaylistAddCheckIcon />}
          iconPosition="start"
          label={`Vorschläge prüfen (${pending.length})`}
        />
        <Tab
          value="pilot"
          icon={<ShieldOutlinedIcon />}
          iconPosition="start"
          label="Pilotfreigabe"
        />
        <Tab
          value="history"
          icon={<HistoryIcon />}
          iconPosition="start"
          label="Historie"
        />
        <Tab
          value="settings"
          icon={<SettingsIcon />}
          iconPosition="start"
          label="Einstellungen"
          onClick={onOpenSettings}
        />
      </Tabs>

      {section === "settings" && (
        <Alert severity="info" sx={{ mt: 2 }}>
          Die Einstellungen wurden unterhalb des Dashboards geöffnet. Dieser
          Bereich ist für Administratoren vorgesehen.
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
                    Was ist jetzt zu tun?
                  </Typography>
                  <Typography variant="h5" sx={{ fontWeight: 700 }}>
                    {nextTask}
                  </Typography>
                  <Typography
                    variant="body2"
                    color="text.secondary"
                    sx={{ mt: 0.75 }}
                  >
                    {pending.length
                      ? `Prüfe als Nächstes ${Math.min(
                          5,
                          pending.length
                        )} Vorschläge. So wird die Pilotfreigabe belastbarer.`
                      : "Der Live-Zustand wird weiter beobachtet. Es ist aktuell keine Moderationsaufgabe offen."}
                  </Typography>
                </Box>
                {pending.length > 0 && (
                  <Button
                    variant="contained"
                    endIcon={<ArrowForwardIcon />}
                    onClick={() => openDecision(pending[0])}
                  >
                    Nächsten Vorschlag prüfen
                  </Button>
                )}
              </Stack>
            </CardContent>
          </Card>

          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                md: "repeat(3, minmax(0, 1fr))",
              },
              gap: 1.5,
              mt: 1.5,
            }}
          >
            <MetricCard
              label="Aktueller Zustand"
              value={modeStatus.title}
              caption={modeStatus.detail}
            />
            <MetricCard
              label="Teamunterschied"
              value={
                difference == null ? "Nicht messbar" : `${difference} Spieler`
              }
              caption={
                hasCounts
                  ? `${teamLabels.allies} ${counts.allies} · ${teamLabels.axis} ${counts.axis}`
                  : "Live-Snapshot unvollständig"
              }
            />
            <MetricCard
              label="Pilotstatus"
              value={
                goals.ready_for_manual
                  ? "Bereit zur Prüfung"
                  : "Noch nicht bereit"
              }
              caption={`${
                summary.reviewed ?? 0
              } von ${totalReviewsTarget} Bewertungen abgeschlossen`}
              color={goals.ready_for_manual ? "success.main" : "text.primary"}
            />
          </Box>

          <Stack
            direction={{ xs: "column", sm: "row" }}
            justifyContent="space-between"
            alignItems={{ sm: "flex-end" }}
            gap={1}
            sx={{ mt: 3, mb: 1.5 }}
          >
            <Box>
              <Typography variant="h5" sx={{ fontWeight: 700 }}>
                Offene Vorschläge
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Nur unbewertete Vorschläge, neueste zuerst
              </Typography>
            </Box>
            <Button color="inherit" onClick={() => switchSection("proposals")}>
              Alle {pending.length} anzeigen
            </Button>
          </Stack>
          <ProposalQueue
            decisions={pending.slice(0, 3)}
            onOpen={openDecision}
            emptyMessage={
              decisions.length
                ? "Alle vorhandenen Shadow-Vorschläge wurden bewertet. Neue Einträge erscheinen automatisch."
                : "Noch kein Shadow-Vorschlag vorhanden. Ein Eintrag erscheint, sobald ein Balancevorfall erkannt wird."
            }
            emptySeverity={decisions.length ? "success" : "info"}
          />

          <Box sx={{ mt: 3, mb: 1.5 }}>
            <Typography variant="h5" sx={{ fontWeight: 700 }}>
              Kann ich den Daten vertrauen?
            </Typography>
            <Typography variant="body2" color="text.secondary">
              Jede Kennzahl nennt ihren Bezug und die Folge für die
              Entscheidung.
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
              title="Live-Snapshot vollständig"
              value={
                status.data_confidence >= 0.95
                  ? "Ja"
                  : formatPercent(status.data_confidence)
              }
              color={status.data_confidence >= 0.95 ? "success" : "warning"}
              progress={(status.data_confidence || 0) * 100}
              explanation="Gilt für die aktuelle Teamzählung. Bei unvollständigen Daten darf daraus keine Wechselentscheidung entstehen."
            />
            <QualityCard
              title="Rating ausreichend sicher"
              value={formatPercent(summary.median_rating_confidence)}
              color={
                summary.median_rating_confidence >= 0.6 ? "success" : "warning"
              }
              progress={(summary.median_rating_confidence || 0) * 100}
              explanation="Gilt für die bewerteten Shadow-Vorschläge. Unter 60 % ist das Rating nur ein Hinweis."
            />
          </Box>

          <Accordion variant="outlined" disableGutters sx={{ mt: 2 }}>
            <AccordionSummary expandIcon={<ExpandMoreIcon />}>
              <Box>
                <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                  Live-Diagnose und Diagramme
                </Typography>
                <Typography variant="caption" color="text.secondary">
                  Technische Zeitreihen für Ursachenanalyse und
                  Betriebskontrolle
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

      {section === "proposals" && (
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
                Vorschläge prüfen
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Bewerte einen Kandidaten anhand derselben fünf Fairnessfragen.
              </Typography>
            </Box>
            <Chip
              label={`${pending.length} offen · ${
                summary.reviewed ?? 0
              } bewertet`}
            />
          </Stack>
          <ProposalQueue
            decisions={pending}
            onOpen={openDecision}
            emptyMessage={
              decisions.length
                ? "Keine offenen Vorschläge. Alle vorhandenen Bewertungen sind abgeschlossen."
                : "Noch kein Shadow-Vorschlag vorhanden."
            }
            emptySeverity={decisions.length ? "success" : "info"}
          />

          {reviewed.length > 0 && (
            <Box sx={{ mt: 3 }}>
              <Typography variant="h5" sx={{ fontWeight: 700, mb: 0.5 }}>
                Bereits bewertet
              </Typography>
              <Typography
                variant="body2"
                color="text.secondary"
                sx={{ mb: 1.5 }}
              >
                Diese Entscheidungen bleiben für Kontrolle und Korrekturen
                einsehbar.
              </Typography>
              <ProposalQueue decisions={reviewed} onOpen={openDecision} />
            </Box>
          )}
        </Box>
      )}

      {section === "pilot" && (
        <Box sx={{ mt: 2 }}>
          <Alert
            severity={goals.ready_for_manual ? "success" : "warning"}
            sx={{ mb: 2 }}
          >
            <strong>
              {goals.ready_for_manual
                ? "Bereit zur gemeinsamen Prüfung."
                : "Noch nicht für den manuellen Betrieb bereit."}
            </strong>{" "}
            Die Freigabe erfolgt immer bewusst durch Administratoren; es gibt
            keine automatische Umschaltung.
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
          <AutobalancerRoundHistory
            config={config}
            teamLabels={teamLabels}
          />
        </Box>
      )}
    </Box>
  );
};

export default AutobalancerModeratorDashboard;
