import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  FormControlLabel,
  MenuItem,
  Stack,
  Switch,
  TextField,
  Typography,
} from "@mui/material";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { useAuth } from "@/hooks/useAuth";
import { canUse } from "@/pages/views/live-map/api";
import { voteRequest } from "./api";
import { copy } from "./copy";
import VotePanel from "./VotePanel";

const fields = {
  confirmation_seconds: [30, 180],
  duration_seconds: [60, 300],
  minimum_participants: [3, 50],
  leadership_seconds: [300, 1800],
  team_gap_seconds: [600, 3600],
  target_cooldown_seconds: [1800, 86400],
};

export default function LeadershipVotes() {
  const { user, permissions } = useAuth();
  const { i18n } = useTranslation();
  const c = copy[i18n.language?.startsWith("de") ? "de" : "en"];
  const allowed = canUse(permissions, "can_manage_leadership_votes");
  const view = canUse(permissions, "can_view_admin_incidents");
  const client = useQueryClient();
  const key = ["leadership-votes", window.location.origin, user?.username];
  const query = useQuery({
    queryKey: [...key, "config"],
    queryFn: () => voteRequest("config"),
    enabled: allowed,
    retry: false,
    refetchOnWindowFocus: false,
  });
  const status = useQuery({
    queryKey: [...key, "status"],
    queryFn: () => voteRequest("status"),
    enabled: view,
    refetchInterval: 5000,
    retry: false,
  });
  const [draft, setDraft] = useState(null);
  useEffect(() => {
    if (query.data) setDraft(query.data.config);
  }, [query.data]);
  const save = useMutation({
    mutationFn: () => voteRequest("config", draft),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  const cancel = useMutation({
    mutationFn: (id) => voteRequest(`votes/${id}/cancel`, {}, "POST"),
    onSuccess: () => client.invalidateQueries({ queryKey: key }),
  });
  const error = query.error || status.error || save.error || cancel.error;
  if (!allowed || [401, 403].includes(query.error?.status))
    return <Alert severity="warning">{c.permission}</Alert>;
  return (
    <Box
      component="section"
      aria-label={c.title}
      sx={{
        mt: 3,
        p: { xs: 2, md: 3 },
        border: "1px solid",
        borderColor: "divider",
        borderRadius: 2,
      }}
    >
      <Typography component="h2" variant="h5" sx={{ mb: 1 }}>
        {c.title}
      </Typography>
      <Typography color="text.secondary" sx={{ mb: 2 }}>
        {c.subtitle}
      </Typography>
      <Stack spacing={2}>
        <Alert severity="info">{c.dryRunInfo}</Alert>
        {draft?.mode === "active" && (
          <Alert severity="warning">{c.warning}</Alert>
        )}
        {query.data?.conflicts?.length > 0 && (
          <Alert severity="error">
            {c.conflicts}: {query.data.conflicts.join(", ")}
          </Alert>
        )}
        {error && <Alert severity="error">{error.message}</Alert>}
        {save.isSuccess && <Alert severity="success">{c.saved}</Alert>}
        {!draft ? (
          <Typography>{c.loading}</Typography>
        ) : (
          <Stack
            component="form"
            spacing={2}
            onSubmit={(e) => {
              e.preventDefault();
              save.mutate();
            }}
          >
            <FormControlLabel
              control={
                <Switch
                  checked={draft.enabled}
                  disabled={!query.data?.can_enable && !draft.enabled}
                  onChange={(e) =>
                    setDraft({ ...draft, enabled: e.target.checked })
                  }
                />
              }
              label={c.enabled}
            />
            {!query.data?.can_enable && (
              <Alert severity="info">{c.kickPermission}</Alert>
            )}
            <Typography>{c.flow}</Typography>
            <Typography color="text.secondary">{c.references}</Typography>
            <Box
              sx={{
                display: "grid",
                gap: 2,
                gridTemplateColumns: {
                  xs: "1fr",
                  md: "repeat(3, minmax(0, 1fr))",
                },
              }}
            >
              {Object.entries(fields).map(([name, [min, max]]) => (
                <TextField
                  key={name}
                  required
                  label={c[name]}
                  type="number"
                  value={draft[name]}
                  inputProps={{ min, max, step: 1 }}
                  onChange={(e) =>
                    setDraft({
                      ...draft,
                      [name]:
                        e.target.value === "" ? "" : Number(e.target.value),
                    })
                  }
                />
              ))}
              <TextField
                select
                label={c.mode}
                value={draft.mode}
                onChange={(e) => setDraft({ ...draft, mode: e.target.value })}
              >
                <MenuItem value="dry_run">{c.dryRun}</MenuItem>
                <MenuItem value="active">{c.activeMode}</MenuItem>
              </TextField>
            </Box>
            <Typography>{c.quorum}</Typography>
            <Typography variant="body2" color="text.secondary">
              {c.frozen}
            </Typography>
            <Button
              type="submit"
              variant="contained"
              disabled={
                save.isPending ||
                (draft.enabled &&
                  (!query.data?.can_enable ||
                    query.data?.conflicts?.length > 0))
              }
              sx={{ alignSelf: "flex-start" }}
            >
              {c.save}
            </Button>
          </Stack>
        )}
        {view && !status.error && (
          <>
            <Typography component="h2" variant="h5">
              {c.statusTitle}
            </Typography>
            {status.data?.votes?.length === 0 && (
              <Typography>{c.empty}</Typography>
            )}
            {(status.data?.votes || []).map((vote) => (
              <VotePanel
                key={vote.id}
                vote={vote}
                canCancel={canUse(permissions, "can_claim_admin_incidents")}
                pending={cancel.isPending}
                onCancel={() => cancel.mutate(vote.id)}
              />
            ))}
          </>
        )}
      </Stack>
    </Box>
  );
}
