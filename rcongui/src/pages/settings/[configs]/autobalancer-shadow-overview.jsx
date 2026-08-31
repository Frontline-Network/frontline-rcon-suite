import {
  Alert,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  TextField,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { useState } from "react";
import { toast } from "react-toastify";
import { useAuth } from "@/hooks/useAuth";
import { cmd } from "@/utils/fetchUtils";
import AutobalancerModeratorDashboard from "@/pages/settings/[configs]/autobalancer-moderator-dashboard";
import PageState from "@/components/shared/PageState";

const REJECTION_LABELS = {
  squad_should_stay: "Squad sollte zusammenbleiben",
  critical_role: "Rolle ist spielerisch zu wichtig",
  recent_join_or_move: "Verbindungs- oder Squadzeit wirkt falsch",
  better_candidate: "Ein anderer Kandidat wäre fairer",
  skill_balance: "Stärkeausgleich ist nicht überzeugend",
  wrong_team_counts: "Teamzählung oder Wechselzahl ist falsch",
  other: "Anderer Grund",
};

const STRATEGY_LABELS = {
  "squad-first": "Squad zuerst",
  "balanced-v2": "Ausgewogen V2 (empfohlen)",
  "skill-first": "Stärke zuerst (nur Diagnose)",
};

const permissionGranted = (permissions, permission) =>
  Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some((item) => item.permission === permission)
  );

const AutobalancerShadowOverview = ({ config, onOpenSettings }) => {
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

  const acceptDecision = (decision) =>
    review.mutate({
      decisionId: decision.decision_id,
      verdict: "accepted",
      reasonCategory: null,
      reviewComment: null,
      preferredStrategy: decision.strategy_version || "balanced-v2",
      preferredPlayerId: decision.player_id || null,
    });

  const rejectDecision = (decision) => {
    setReviewTarget(decision);
    setCategory(decision.review_category || "");
    setComment(decision.review_comment || "");
    setPreferredStrategy(decision.review_preferred_strategy || "");
    setPreferredPlayerId(decision.review_preferred_player_id || "");
  };

  if (isLoading) {
    return (
      <PageState
        kind="loading"
        title="Autobalancer-Dashboard wird geladen …"
        titleComponent="h1"
      />
    );
  }

  if (isError || !data) {
    return (
      <PageState
        kind="error"
        title="Autobalancer-Dashboard konnte nicht geladen werden"
        description="Bitte Berechtigung und Autobalancer-Dienst prüfen."
        titleComponent="h1"
        action={{ label: "Erneut versuchen", onClick: refetch }}
      />
    );
  }

  return (
    <>
      <AutobalancerModeratorDashboard
        config={config}
        data={data}
        liveStatus={liveStatus}
        canReview={canReview}
        isFetching={isFetching}
        reviewPending={review.isPending}
        onRefresh={refetch}
        onAccept={acceptDecision}
        onReject={rejectDecision}
        onOpenSettings={onOpenSettings}
      />

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
            Regel oder Gewichtung gezielt verbessert werden muss.
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
                      { ...plan, strategy },
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
            helperText={`${comment.length}/1000 Zeichen – zum Beispiel: Welcher andere Spieler wäre fairer gewesen?`}
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
    </>
  );
};

export default AutobalancerShadowOverview;
