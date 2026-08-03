import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import RefreshIcon from "@mui/icons-material/Refresh";
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
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  InputLabel,
  LinearProgress,
  MenuItem,
  Select,
  Stack,
  TextField,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "react-toastify";
import { useAuth } from "@/hooks/useAuth";
import { cmd } from "@/utils/fetchUtils";
import AutobalancerShadowCharts from "@/pages/settings/[configs]/autobalancer-shadow-charts";
import AutobalancerRoundHistory from "@/pages/settings/[configs]/autobalancer-round-history";
import AutobalancerHistoryDashboard from "@/pages/settings/[configs]/autobalancer-history-dashboard";

const TIER_LABELS = {
  0: "0 · kaum Squad-Bindung",
  1: "1 · kurz im unvollständigen Squad",
  2: "2 · unvollständiger Infantry-Squad",
  3: "3 · voller oder stabiler Infantry-Squad",
  4: "4 · Squad Leader",
  5: "5 · Armor, Recon oder Artillery",
};

const REJECTION_LABELS = {
  squad_should_stay: "Squad sollte zusammenbleiben",
  critical_role: "Rolle ist spielerisch zu wichtig",
  recent_join_or_move: "Verbindungs- oder Squadzeit wirkt falsch",
  better_candidate: "Ein anderer Kandidat wäre fairer",
  skill_balance: "Stärkeausgleich ist nicht überzeugend",
  wrong_team_counts: "Teamzählung oder Wechselzahl ist falsch",
  other: "Anderer Grund",
};

const TEAM_LABELS = { allies: "Allies", axis: "Axis" };
const STRATEGY_LABELS = {
  "squad-first": "Squad zuerst",
  "balanced-v2": "Ausgewogen V2 (empfohlen)",
  "skill-first": "Stärke zuerst (nur Diagnose)",
};

const ROLE_FAMILY_LABELS = {
  combat_infantry: "Combat Infantry",
  support: "Support / Engineer / Medic",
  leader: "Squad Leader",
  specialist: "Armor / Recon / Artillery",
};

const formatPercent = (value) =>
  value === null || value === undefined
    ? "noch keine Daten"
    : `${Math.round(value * 100)} %`;

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat("de-DE", {
        dateStyle: "short",
        timeStyle: "medium",
      }).format(new Date(value))
    : "–";

const formatMinutes = (seconds) =>
  Number.isFinite(seconds) ? `${Math.floor(seconds / 60)} Min.` : "unbekannt";

const permissionGranted = (permissions, permission) =>
  Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some((item) => item.permission === permission)
  );

const Metric = ({ label, value, explanation }) => (
  <Box
    sx={{
      border: 1,
      borderColor: "divider",
      borderRadius: 1,
      p: 1.5,
      minWidth: 0,
    }}
  >
    <Typography variant="h5" sx={{ fontWeight: 700 }}>
      {value}
    </Typography>
    <Typography variant="subtitle2">{label}</Typography>
    <Typography variant="caption" color="text.secondary">
      {explanation}
    </Typography>
  </Box>
);

const Goal = ({ label, value, target, met, progress, explanation }) => (
  <Box>
    <Stack direction="row" justifyContent="space-between" spacing={2}>
      <Typography variant="body2" sx={{ fontWeight: 700 }}>
        {label}
      </Typography>
      <Chip
        size="small"
        color={met ? "success" : "default"}
        label={`${value} / Ziel ${target}`}
      />
    </Stack>
    <LinearProgress
      variant="determinate"
      color={met ? "success" : "primary"}
      value={Math.max(0, Math.min(100, progress))}
      sx={{ mt: 1, mb: 0.5, height: 7, borderRadius: 4 }}
    />
    <Typography variant="caption" color="text.secondary">
      {explanation}
    </Typography>
  </Box>
);

const StrategyComparison = ({ decision }) => {
  const strategies = Object.entries(decision.strategy_plans || {});
  if (!strategies.length) return null;
  return (
    <Box sx={{ mt: 1.5 }}>
      <Typography variant="subtitle2" sx={{ mb: 1 }}>
        Drei Shadow-Strategien – gleiche Ausgangslage
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "repeat(3, 1fr)" },
          gap: 1,
        }}
      >
        {strategies.map(([name, plan]) => (
          <Card
            key={name}
            variant="outlined"
            sx={{
              borderColor:
                name === decision.strategy_version ? "primary.main" : "divider",
            }}
          >
            <CardContent>
              <Stack direction="row" gap={0.75} flexWrap="wrap">
                <Chip
                  size="small"
                  color={name === "balanced-v2" ? "primary" : "default"}
                  label={STRATEGY_LABELS[name] || name}
                />
                {name === decision.strategy_version && (
                  <Chip size="small" variant="outlined" label="verwendet" />
                )}
              </Stack>
              <Typography sx={{ fontWeight: 700, mt: 1 }}>
                {plan.player_name || "Kein Kandidat"}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                Schutzstufe {plan.effective_tier ?? "–"} · Ratingdifferenz{" "}
                {plan.rating_gap_before ?? decision.rating_gap_before ?? "–"} →{" "}
                {plan.projected_rating_gap ?? "–"}
              </Typography>
              {(plan.warnings || []).map((warning) => (
                <Typography
                  key={warning}
                  variant="caption"
                  color="warning.main"
                  sx={{ display: "block", mt: 0.5 }}
                >
                  {warning}
                </Typography>
              ))}
            </CardContent>
          </Card>
        ))}
      </Box>
      <Typography variant="caption" color="text.secondary">
        {decision.strategies_agree
          ? "Alle Strategien wählen denselben ersten Kandidaten."
          : "Die Strategien wählen unterschiedliche Kandidaten. Genau solche Fälle sind für die Kalibrierung besonders wichtig."}
      </Typography>
    </Box>
  );
};

const AutobalancerShadowOverview = ({ config }) => {
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const canReview = permissionGranted(permissions, "can_execute_autobalancer");
  const [reviewTarget, setReviewTarget] = useState(null);
  const [category, setCategory] = useState("");
  const [comment, setComment] = useState("");
  const [preferredStrategy, setPreferredStrategy] = useState("");
  const [preferredPlayerId, setPreferredPlayerId] = useState("");
  const queryKey = [{ queryIdentifier: "get_autobalancer_shadow_overview" }];
  const { data, isLoading, isError, refetch, isFetching } = useQuery({
    queryKey,
    queryFn: () =>
      cmd.GET_AUTOBALANCER_SHADOW_OVERVIEW({
        params: { limit: 500, timeline_limit: 720 },
      }),
    refetchInterval: 30_000,
    retry: false,
  });
  const { data: liveStatus } = useQuery({
    queryKey: [{ queryIdentifier: "get_autobalancer_status" }],
    queryFn: cmd.GET_AUTOBALANCER_STATUS,
    refetchInterval: 5_000,
    retry: false,
  });

  const review = useMutation({
    mutationFn: async ({
      decisionId,
      verdict,
      reasonCategory,
      reviewComment,
      preferredStrategy: selectedStrategy,
      preferredPlayerId: selectedPlayer,
    }) => {
      const response = await cmd.REVIEW_AUTOBALANCER_SHADOW_DECISION({
        payload: {
          decision_id: decisionId,
          verdict,
          category: reasonCategory,
          comment: reviewComment,
          preferred_strategy: selectedStrategy || null,
          preferred_player_id: selectedPlayer || null,
        },
      });
      if (response?.failed) throw new Error(response.error);
      return response?.result;
    },
    onSuccess: () => {
      toast.success("Shadow-Vorschlag wurde bewertet.");
      setReviewTarget(null);
      setCategory("");
      setComment("");
      setPreferredStrategy("");
      setPreferredPlayerId("");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) =>
      toast.error(
        error?.message || "Bewertung konnte nicht gespeichert werden."
      ),
  });

  if (isLoading) {
    return (
      <Card variant="outlined">
        <CardContent>
          <Typography>Shadow-Auswertung wird geladen …</Typography>
        </CardContent>
      </Card>
    );
  }
  if (isError || !data) {
    return (
      <Alert severity="error">
        Die Shadow-Auswertung konnte nicht geladen werden. Bitte Berechtigung
        und Autobalancer-Dienst prüfen.
      </Alert>
    );
  }

  const summary = data.summary || {};
  const goals = data.pilot_goals || {};
  const decisions = data.decisions || [];
  const acceptance = summary.acceptance_rate;
  const mode = config?.mode;

  return (
    <Card variant="outlined">
      <CardContent>
        <Stack
          direction={{ xs: "column", md: "row" }}
          justifyContent="space-between"
          alignItems={{ md: "center" }}
          spacing={1}
        >
          <Box>
            <Typography variant="h4">Autobalancer Live-Dashboard</Typography>
            <Typography variant="body2" color="text.secondary">
              Der aktuelle Serverzustand aktualisiert sich automatisch.
              Shadow-Auswertungen folgen darunter.
            </Typography>
          </Box>
          <Button
            startIcon={<RefreshIcon />}
            variant="outlined"
            disabled={isFetching}
            onClick={() => refetch()}
          >
            Aktualisieren
          </Button>
        </Stack>

        <AutobalancerShadowCharts
          status={liveStatus || data.live_status}
          timeline={data.timeline}
          summary={summary}
          config={config}
        />

        <AutobalancerHistoryDashboard
          config={config}
          shadowSummary={summary}
          pilotGoals={goals}
        />

        <AutobalancerRoundHistory config={config} />

        {mode !== "shadow" && (
          <Alert severity="info" sx={{ mt: 2 }}>
            Aktueller Modus: <strong>{mode}</strong>. Die Übersicht zeigt
            weiterhin die früheren Shadow-Vorschläge; neue Shadow-Daten
            entstehen nur im Modus „shadow“.
          </Alert>
        )}

        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              alignItems={{ sm: "center" }}
            >
              <Typography sx={{ fontWeight: 700 }}>
                Adminbewertungen und Auditwerte
              </Typography>
              <Chip
                size="small"
                color={goals.ready_for_manual ? "success" : "default"}
                label={
                  goals.ready_for_manual
                    ? "Admin-Teilziele erreicht"
                    : `${
                        summary.reviewed ?? 0
                      }/20 Bewertungen · ${formatPercent(acceptance)}`
                }
              />
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "1fr",
                  sm: "repeat(2, minmax(0, 1fr))",
                  lg: "repeat(4, minmax(0, 1fr))",
                },
                gap: 1.5,
              }}
            >
              <Metric
                label="Vorschläge"
                value={summary.proposals ?? 0}
                explanation={`${
                  summary.rounds_observed ?? 0
                } Karten mit Vorschlag`}
              />
              <Metric
                label="Bewertet"
                value={summary.reviewed ?? 0}
                explanation={`${
                  summary.pending_review ?? 0
                } Bewertungen sind noch offen`}
              />
              <Metric
                label="Akzeptanzquote"
                value={formatPercent(acceptance)}
                explanation={`${summary.accepted ?? 0} akzeptabel · ${
                  summary.rejected ?? 0
                } nicht akzeptabel`}
              />
              <Metric
                label="Regelwarnungen"
                value={summary.rule_warning_proposals ?? 0}
                explanation="Commander-, Snapshot-, Team- oder Zuordnungsfehler"
              />
            </Box>
            <Stack spacing={2} sx={{ mt: 2 }}>
              <Goal
                label="Bewertete Karten"
                value={summary.reviewed_rounds ?? 0}
                target={goals.reviewed_rounds_target ?? 10}
                met={goals.reviewed_rounds_met}
                progress={
                  ((summary.reviewed_rounds ?? 0) /
                    (goals.reviewed_rounds_target || 10)) *
                  100
                }
                explanation="Eine Karte zählt, sobald mindestens ein Vorschlag daraus bewertet wurde."
              />
              <Goal
                label="Bewertete Vorschläge"
                value={summary.reviewed ?? 0}
                target={goals.reviewed_proposals_target ?? 20}
                met={goals.reviewed_proposals_met}
                progress={
                  ((summary.reviewed ?? 0) /
                    (goals.reviewed_proposals_target || 20)) *
                  100
                }
                explanation="Wenn nach zehn Karten noch keine 20 Vorschläge bewertet sind, läuft Shadow weiter."
              />
              <Goal
                label="Akzeptable Vorschläge"
                value={formatPercent(acceptance)}
                target={formatPercent(goals.acceptance_rate_target ?? 0.9)}
                met={goals.acceptance_rate_met}
                progress={(acceptance ?? 0) * 100}
                explanation="Ziel für manual: mindestens 90 % der bewerteten Vorschläge. Es erfolgt keine automatische Umschaltung."
              />
              <Goal
                label="Mediane Ratingkonfidenz"
                value={formatPercent(summary.median_rating_confidence)}
                target={formatPercent(goals.rating_confidence_target ?? 0.6)}
                met={goals.rating_confidence_met}
                progress={(summary.median_rating_confidence ?? 0) * 100}
                explanation="Das effektive Rating wird bei geringer Konfidenz automatisch zum neutralen Wert 50 zurückgeführt."
              />
              <Goal
                label="Ratingdifferenz-Guardrail"
                value={formatPercent(summary.gap_guardrail_rate)}
                target={formatPercent(goals.gap_guardrail_target ?? 0.95)}
                met={goals.gap_guardrail_met}
                progress={(summary.gap_guardrail_rate ?? 0) * 100}
                explanation="Mindestens 95 % der Empfehlungen dürfen die Ratingdifferenz um höchstens zwei Punkte verschlechtern."
              />
            </Stack>
          </AccordionDetails>
        </Accordion>

        <Accordion sx={{ mt: 2 }}>
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Stack
              direction={{ xs: "column", sm: "row" }}
              spacing={1}
              alignItems={{ sm: "center" }}
            >
              <Typography sx={{ fontWeight: 700 }}>
                Einzelne Shadow-Vorschläge prüfen
              </Typography>
              <Chip
                size="small"
                label={`${summary.pending_review ?? 0} offen · ${
                  summary.proposals ?? 0
                } gesamt`}
              />
            </Stack>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1.5 }}>
              Nur öffnen, wenn Kandidaten im Detail geprüft oder bewertet werden
              sollen.
            </Typography>

            {!decisions.length && (
              <Alert severity="info">
                Es gibt noch keinen Shadow-Vorschlag. Ein Eintrag entsteht erst,
                wenn mindestens 40 Spieler online sind, die Teamdifferenz größer
                als 2 ist und 45 Sekunden stabil bleibt – außerhalb der
                Schutzzeiten am Kartenanfang und Kartenende.
              </Alert>
            )}

            {decisions.map((decision) => {
              const verdict = decision.review_verdict;
              return (
                <Accordion key={decision.decision_id} disableGutters>
                  <AccordionSummary expandIcon={<ExpandMoreIcon />}>
                    <Stack
                      direction={{ xs: "column", md: "row" }}
                      spacing={{ xs: 0.25, md: 1 }}
                      alignItems={{ md: "center" }}
                      sx={{ width: "100%", pr: 1 }}
                    >
                      <Typography variant="body2" color="text.secondary">
                        {formatDate(decision.created_at)}
                      </Typography>
                      <Typography sx={{ fontWeight: 700 }}>
                        {decision.map_name || "Unbekannte Karte"} · Allies{" "}
                        {decision.allies_count ?? "–"}:
                        {decision.axis_count ?? "–"} Axis
                      </Typography>
                      <Typography sx={{ flexGrow: 1 }}>
                        Kandidat: {decision.player_name || "unbekannt"}
                      </Typography>
                      <Chip
                        size="small"
                        color={
                          verdict === "accepted"
                            ? "success"
                            : verdict === "rejected"
                            ? "warning"
                            : "default"
                        }
                        label={
                          verdict === "accepted"
                            ? "Akzeptabel"
                            : verdict === "rejected"
                            ? "Nicht akzeptabel"
                            : "Offen"
                        }
                      />
                    </Stack>
                  </AccordionSummary>
                  <AccordionDetails>
                    <Box
                      sx={{
                        display: "grid",
                        gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
                        gap: 2,
                      }}
                    >
                      <Box>
                        <Typography variant="subtitle2">
                          Ausgangslage
                        </Typography>
                        <Typography variant="body2">
                          Differenz {decision.difference ?? "–"}; geplant waren{" "}
                          {decision.required_switches ?? "–"} Wechsel von{" "}
                          {TEAM_LABELS[decision.source_team] ||
                            decision.source_team}{" "}
                          zu{" "}
                          {TEAM_LABELS[decision.target_team] ||
                            decision.target_team}
                          .
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          <strong>Auswahlgrund:</strong>{" "}
                          {decision.selection_reason || "nicht gespeichert"}
                        </Typography>
                        <Typography variant="body2">
                          <strong>Schutz:</strong>{" "}
                          {TIER_LABELS[decision.protection_tier] ||
                            `Stufe ${decision.protection_tier ?? "–"}`}
                          {decision.volunteer ? " · freiwillig" : ""}
                        </Typography>
                      </Box>
                      <Box>
                        <Typography variant="subtitle2">
                          Kandidat im Snapshot
                        </Typography>
                        <Typography variant="body2">
                          Squad {decision.unit_name || "nicht zugewiesen"} ·{" "}
                          {decision.unit_type || "unbekannter Typ"} ·{" "}
                          {decision.unit_size ?? "?"} Spieler
                        </Typography>
                        <Typography variant="body2">
                          Rolle {decision.role || "unbekannt"}
                          {decision.is_leader ? " · Squad Leader" : ""} ·
                          verbunden seit{" "}
                          {formatMinutes(decision.connected_seconds)} · im Squad
                          seit {formatMinutes(decision.squad_seconds)}
                        </Typography>
                        <Typography variant="body2" sx={{ mt: 1 }}>
                          Effektives Rating {Math.round(decision.rating ?? 50)}
                          /100
                          {decision.rating_raw != null
                            ? ` · Rohwert ${Math.round(
                                decision.rating_raw
                              )}/100`
                            : ""}
                          {" · "}Vertrauen{" "}
                          {formatPercent(decision.rating_confidence)}
                        </Typography>
                        <Typography variant="body2">
                          Rollenfamilie{" "}
                          {ROLE_FAMILY_LABELS[decision.rating_role_family] ||
                            decision.rating_role_family ||
                            "Legacy"}
                          {" · "}Historie{" "}
                          {decision.rating_history_source || "legacy"}
                          {" · "}Modell{" "}
                          {decision.rating_model_version || "legacy"}
                        </Typography>
                        <Typography variant="body2">
                          Ratingdifferenz {decision.rating_gap_before ?? "–"} →{" "}
                          {decision.projected_rating_gap ?? "–"} · Strategie{" "}
                          {STRATEGY_LABELS[decision.strategy_version] ||
                            decision.strategy_version ||
                            "legacy"}
                        </Typography>
                      </Box>
                    </Box>

                    <StrategyComparison decision={decision} />

                    {(decision.audit_warnings || []).map((warning) => (
                      <Alert key={warning} severity="error" sx={{ mt: 1 }}>
                        Automatische Regelwarnung: {warning}
                      </Alert>
                    ))}

                    {verdict && (
                      <Alert
                        severity={
                          verdict === "accepted" ? "success" : "warning"
                        }
                        sx={{ mt: 1.5 }}
                      >
                        Bewertung von {decision.reviewed_by || "Admin"} am{" "}
                        {formatDate(decision.reviewed_at)}:{" "}
                        {verdict === "accepted"
                          ? "Kandidat war akzeptabel."
                          : REJECTION_LABELS[decision.review_category] ||
                            "Nicht akzeptabel."}
                        {decision.review_comment
                          ? ` – ${decision.review_comment}`
                          : ""}
                        {decision.review_preferred_strategy
                          ? ` Bevorzugte Strategie: ${
                              STRATEGY_LABELS[
                                decision.review_preferred_strategy
                              ] || decision.review_preferred_strategy
                            }.`
                          : ""}
                      </Alert>
                    )}

                    {canReview ? (
                      <Stack direction="row" spacing={1} sx={{ mt: 1.5 }}>
                        <Button
                          size="small"
                          variant={
                            verdict === "accepted" ? "contained" : "outlined"
                          }
                          color="success"
                          disabled={review.isPending}
                          onClick={() =>
                            review.mutate({
                              decisionId: decision.decision_id,
                              verdict: "accepted",
                              reasonCategory: null,
                              reviewComment: null,
                              preferredStrategy:
                                decision.strategy_version || "balanced-v2",
                              preferredPlayerId: decision.player_id || null,
                            })
                          }
                        >
                          Kandidat akzeptabel
                        </Button>
                        <Button
                          size="small"
                          variant={
                            verdict === "rejected" ? "contained" : "outlined"
                          }
                          color="warning"
                          disabled={review.isPending}
                          onClick={() => {
                            setReviewTarget(decision);
                            setCategory(decision.review_category || "");
                            setComment(decision.review_comment || "");
                            setPreferredStrategy(
                              decision.review_preferred_strategy || ""
                            );
                            setPreferredPlayerId(
                              decision.review_preferred_player_id || ""
                            );
                          }}
                        >
                          Nicht akzeptabel
                        </Button>
                      </Stack>
                    ) : (
                      <Typography variant="caption" color="text.secondary">
                        Zum Bewerten ist die Berechtigung „Autobalancer
                        ausführen“ erforderlich.
                      </Typography>
                    )}
                  </AccordionDetails>
                </Accordion>
              );
            })}
          </AccordionDetails>
        </Accordion>
      </CardContent>

      <Dialog
        open={Boolean(reviewTarget)}
        onClose={() => !review.isPending && setReviewTarget(null)}
        fullWidth
        maxWidth="sm"
      >
        <DialogTitle>Warum ist der Kandidat nicht akzeptabel?</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Wähle den wichtigsten Grund. Diese Kategorien zeigen später, welche
            Regel oder Gewichtung wir gezielt verbessern müssen.
          </DialogContentText>
          <FormControl fullWidth required sx={{ mb: 2 }}>
            <InputLabel id="shadow-rejection-label">Hauptgrund</InputLabel>
            <Select
              labelId="shadow-rejection-label"
              label="Hauptgrund"
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {Object.entries(REJECTION_LABELS).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel id="shadow-preferred-strategy-label">
              Welche Strategie wäre besser? (optional)
            </InputLabel>
            <Select
              labelId="shadow-preferred-strategy-label"
              label="Welche Strategie wäre besser? (optional)"
              value={preferredStrategy}
              onChange={(event) => {
                const value = event.target.value;
                setPreferredStrategy(value);
                setPreferredPlayerId(
                  reviewTarget?.strategy_plans?.[value]?.player_id || ""
                );
              }}
            >
              <MenuItem value="">Keine Angabe</MenuItem>
              {Object.keys(reviewTarget?.strategy_plans || {}).map((value) => (
                <MenuItem key={value} value={value}>
                  {STRATEGY_LABELS[value] || value}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel id="shadow-preferred-player-label">
              Besserer Kandidat (optional)
            </InputLabel>
            <Select
              labelId="shadow-preferred-player-label"
              label="Besserer Kandidat (optional)"
              value={preferredPlayerId}
              onChange={(event) => setPreferredPlayerId(event.target.value)}
            >
              <MenuItem value="">Keine Angabe</MenuItem>
              {Array.from(
                new Map(
                  Object.entries(reviewTarget?.strategy_plans || {})
                    .filter(([, plan]) => plan.player_id)
                    .map(([strategy, plan]) => [
                      plan.player_id,
                      {
                        ...plan,
                        strategy,
                      },
                    ])
                ).values()
              ).map((plan) => (
                <MenuItem key={plan.player_id} value={plan.player_id}>
                  {plan.player_name || plan.player_id} ·{" "}
                  {STRATEGY_LABELS[plan.strategy] || plan.strategy}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            multiline
            minRows={3}
            label="Kommentar (optional)"
            value={comment}
            inputProps={{ maxLength: 1000 }}
            helperText={`${comment.length}/1000 Zeichen – z. B. welcher andere Spieler fairer gewesen wäre`}
            onChange={(event) => setComment(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button
            color="inherit"
            disabled={review.isPending}
            onClick={() => setReviewTarget(null)}
          >
            Abbrechen
          </Button>
          <Button
            color="warning"
            variant="contained"
            disabled={!category || review.isPending}
            onClick={() =>
              review.mutate({
                decisionId: reviewTarget.decision_id,
                verdict: "rejected",
                reasonCategory: category,
                reviewComment: comment,
                preferredStrategy,
                preferredPlayerId,
              })
            }
          >
            Ablehnung speichern
          </Button>
        </DialogActions>
      </Dialog>
    </Card>
  );
};

export default AutobalancerShadowOverview;
