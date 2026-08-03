import {
  Alert,
  Box,
  Button,
  Card,
  CardActions,
  CardContent,
  Chip,
  Stack,
  Typography,
} from "@mui/material";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { cmd } from "@/utils/fetchUtils";

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

const AutobalancerCard = () => {
  const queryClient = useQueryClient();
  const { data: status, isError } = useQuery({
    queryKey: [{ queryIdentifier: "get_autobalancer_status" }],
    queryFn: cmd.GET_AUTOBALANCER_STATUS,
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

  if (isError || !status) return null;
  const proposal = status.proposal;
  const counts = status.team_counts || {};
  return (
    <Card variant="outlined" sx={{ m: 1.5 }}>
      <CardContent sx={{ pb: 1 }}>
        <Stack
          direction={{ xs: "column", md: "row" }}
          spacing={1}
          alignItems={{ md: "center" }}
        >
          <Typography variant="h6">Fair Autobalancer</Typography>
          <Chip
            size="small"
            label={status.mode}
            color={status.mode === "auto" ? "success" : "default"}
          />
          <Chip
            size="small"
            label={PHASE_LABELS[status.phase] || status.phase}
          />
          <Typography variant="body2" color="text.secondary">
            Allies {counts.allies ?? "–"} : {counts.axis ?? "–"} Axis ·{" "}
            {status.required_switches ?? 0} Wechsel nötig
          </Typography>
        </Stack>
        {proposal && (
          <Box sx={{ mt: 1 }}>
            <Typography variant="body2">
              Vorschlag: <strong>{proposal.player_name}</strong> nach{" "}
              {status.plan?.target_team || "Gegenteam"}
            </Typography>
            <Typography variant="caption" color="text.secondary">
              Auswahlgrund: {proposal.reason} · Schutzstufe {proposal.base_tier}
            </Typography>
          </Box>
        )}
        {(status.warnings || []).map((warning) => (
          <Alert key={warning} severity="warning" sx={{ mt: 1, py: 0 }}>
            {warning}
          </Alert>
        ))}
        {(status.block_reasons || []).map((reason) => (
          <Alert key={reason} severity="info" sx={{ mt: 1, py: 0 }}>
            {reason}
          </Alert>
        ))}
      </CardContent>
      {status.incident_id && (
        <CardActions>
          {status.mode === "manual" && status.phase === "proposed" && (
            <Button
              size="small"
              variant="contained"
              disabled={approve.isPending}
              onClick={() => approve.mutate()}
            >
              Vorschlag freigeben
            </Button>
          )}
          <Button
            size="small"
            color="warning"
            disabled={cancel.isPending}
            onClick={() => cancel.mutate()}
          >
            Incident abbrechen
          </Button>
        </CardActions>
      )}
    </Card>
  );
};

export default AutobalancerCard;
