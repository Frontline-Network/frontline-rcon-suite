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

const PHASE_EXPLANATIONS = {
  idle: "Aktuell liegt kein zu bearbeitender Balance-Vorfall vor.",
  observing: "Die Teamdifferenz ist zu groß. Der Dienst prüft, ob sie lange genug in derselben Richtung bestehen bleibt.",
  volunteer: "Geeignete Spieler im größeren Team können sich jetzt mit !balance freiwillig melden.",
  proposed: "Ein Kandidat wurde berechnet. Im manuellen Modus wartet der Vorschlag auf eine Admin-Freigabe.",
  armed: "Der Kandidat ist vorgemerkt. Ein Wechsel ist nur nach seinem nächsten frischen Todesereignis möglich.",
  verifying: "Der RCON-Befehl wurde gesendet. Log und neuer Snapshot müssen den Wechsel jetzt bestätigen.",
  cooldown: "Der vorherige Vorfall ist beendet. Vor einem neuen Versuch muss die Differenz erneut stabil bestehen.",
  blocked: "Mindestens eine Sicherheitsbedingung ist nicht erfüllt. Deshalb plant der Dienst momentan keinen Wechsel.",
};

const MODE_LABELS = {
  disabled: "Aus",
  shadow: "Shadow – nur beobachten",
  manual: "Manuell",
  auto: "Automatisch",
};

const MODE_EXPLANATIONS = {
  disabled: "Der Autobalancer ist ausgeschaltet.",
  shadow: "Testbetrieb: Es werden nur Vorschläge protokolliert. Niemand erhält Nachrichten oder wird verschoben.",
  manual: "Ein Vorschlag muss von einem Admin freigegeben werden. Der Wechsel erfolgt anschließend nach dem Tod.",
  auto: "Nach der Freiwilligenphase wird automatisch ausgewählt. Der Wechsel erfolgt nach dem Tod.",
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
            label={MODE_LABELS[status.mode] || status.mode}
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
        <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
          {MODE_EXPLANATIONS[status.mode]}
        </Typography>
        <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
          <strong>Aktuelle Phase:</strong> {PHASE_EXPLANATIONS[status.phase]}
        </Typography>
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
        {(status.block_reasons || []).length > 0 && (
          <Typography variant="subtitle2" sx={{ mt: 1.5 }}>
            Warum passiert gerade nichts?
          </Typography>
        )}
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
