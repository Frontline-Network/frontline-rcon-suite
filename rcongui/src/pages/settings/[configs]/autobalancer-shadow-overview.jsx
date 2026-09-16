import i18n from "@/i18n";
import { useTranslation } from "react-i18next";
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

const REJECTION_LABELS = () => ({
  squad_should_stay: i18n.t("settingsPanels.autobalancer.squadShouldStay"),
  critical_role: i18n.t("settingsPanels.autobalancer.criticalRoleReason"),
  recent_join_or_move: i18n.t("settingsPanels.autobalancer.recentJoinReason"),
  better_candidate: i18n.t("settingsPanels.autobalancer.betterCandidateReason"),
  skill_balance: i18n.t("settingsPanels.autobalancer.skillBalanceReason"),
  wrong_team_counts: i18n.t("settingsPanels.autobalancer.wrongCountsReason"),
  other: i18n.t("settingsPanels.autobalancer.otherReason"),
});

const STRATEGY_LABELS = () => ({
  "squad-first": i18n.t("settingsPanels.autobalancer.squadFirst"),
  "balanced-v2": i18n.t("settingsPanels.autobalancer.balancedV2Recommended"),
  "skill-first": i18n.t("settingsPanels.autobalancer.skillFirstOnlyDiagnostic"),
});

const permissionGranted = (permissions, permission) =>
  Boolean(
    permissions?.is_superuser ||
      permissions?.permissions?.some((item) => item.permission === permission)
  );

const AutobalancerShadowOverview = ({ config, onOpenSettings }) => {
  useTranslation();
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
      toast.success(i18n.t("settingsPanels.autobalancer.reviewSaved"));
      setReviewTarget(null);
      setCategory("");
      setComment("");
      setPreferredStrategy("");
      setPreferredPlayerId("");
      queryClient.invalidateQueries({ queryKey });
    },
    onError: (error) =>
      toast.error(
        error?.message || i18n.t("settingsPanels.autobalancer.reviewSaveError")
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
        title={i18n.t("settingsPanels.autobalancer.dashboardLoading")}
        titleComponent="h1"
      />
    );
  }

  if (isError || !data) {
    return (
      <PageState
        kind="error"
        title={i18n.t("settingsPanels.autobalancer.dashboardLoadError")}
        description={i18n.t(
          "settingsPanels.autobalancer.checkPermissionService"
        )}
        titleComponent="h1"
        action={{
          label: i18n.t("settingsPanels.autobalancer.retry"),
          onClick: refetch,
        }}
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
        <DialogTitle>
          {i18n.t("settingsPanels.autobalancer.rejectionQuestion")}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            {i18n.t("settingsPanels.autobalancer.rejectionHelp")}
          </DialogContentText>
          <FormControl fullWidth required sx={{ mb: 2 }}>
            <InputLabel id="shadow-rejection-label">
              {i18n.t("settingsPanels.autobalancer.mainReason")}
            </InputLabel>
            <Select
              labelId="shadow-rejection-label"
              label={i18n.t("settingsPanels.autobalancer.mainReason")}
              value={category}
              onChange={(event) => setCategory(event.target.value)}
            >
              {Object.entries(REJECTION_LABELS()).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel id="shadow-preferred-strategy-label">
              {i18n.t("settingsPanels.autobalancer.betterStrategyQuestion")}
            </InputLabel>
            <Select
              labelId="shadow-preferred-strategy-label"
              label={i18n.t(
                "settingsPanels.autobalancer.betterStrategyQuestion"
              )}
              value={preferredStrategy}
              onChange={(event) => {
                const value = event.target.value;
                setPreferredStrategy(value);
                setPreferredPlayerId(
                  reviewTarget?.strategy_plans?.[value]?.player_id || ""
                );
              }}
            >
              <MenuItem value="">
                {i18n.t("settingsPanels.autobalancer.notSpecified")}
              </MenuItem>
              {Object.keys(reviewTarget?.strategy_plans || {}).map((value) => (
                <MenuItem key={value} value={value}>
                  {STRATEGY_LABELS()[value] || value}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <FormControl fullWidth sx={{ mb: 2 }}>
            <InputLabel id="shadow-preferred-player-label">
              {i18n.t("settingsPanels.autobalancer.betterCandidateOptional")}
            </InputLabel>
            <Select
              labelId="shadow-preferred-player-label"
              label={i18n.t(
                "settingsPanels.autobalancer.betterCandidateOptional"
              )}
              value={preferredPlayerId}
              onChange={(event) => setPreferredPlayerId(event.target.value)}
            >
              <MenuItem value="">
                {i18n.t("settingsPanels.autobalancer.notSpecified")}
              </MenuItem>
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
                  {STRATEGY_LABELS()[plan.strategy] || plan.strategy}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          <TextField
            fullWidth
            multiline
            minRows={3}
            label={i18n.t("settingsPanels.autobalancer.commentOptional")}
            value={comment}
            inputProps={{ maxLength: 1000 }}
            helperText={i18n.t("settingsPanels.autobalancer.commentHelp", {
              v0: comment.length,
            })}
            onChange={(event) => setComment(event.target.value)}
          />
        </DialogContent>
        <DialogActions>
          <Button
            color="inherit"
            disabled={review.isPending}
            onClick={() => setReviewTarget(null)}
          >
            {i18n.t("settingsPanels.autobalancer.cancel")}
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
            {i18n.t("settingsPanels.autobalancer.saveRejection")}
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
};

export default AutobalancerShadowOverview;
import "@/i18n/register-settings-panels";
