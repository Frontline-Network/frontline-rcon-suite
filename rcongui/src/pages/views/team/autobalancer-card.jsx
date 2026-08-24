import { useEffect, useState } from "react";
import {
  Alert,
  Box,
  Button,
  Chip,
  Collapse,
  IconButton,
  Stack,
  Tooltip,
  Typography,
} from "@mui/material";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import CheckCircleOutlineIcon from "@mui/icons-material/CheckCircleOutline";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import ReportProblemOutlinedIcon from "@mui/icons-material/ReportProblemOutlined";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Link } from "react-router-dom";
import TeamBalanceBar from "@/components/shared/TeamBalanceBar";
import { cmd } from "@/utils/fetchUtils";
import { useAuth } from "@/hooks/useAuth";

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

const AutobalancerCard = () => {
  const queryClient = useQueryClient();
  const { permissions } = useAuth();
  const [expanded, setExpanded] = useState(false);
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

  const warnings = status?.warnings ?? [];
  const blockReasons = status?.block_reasons ?? [];
  const proposal = status?.proposal;
  const needsAttention = Boolean(
    proposal || warnings.length || blockReasons.length || status?.incident_id
  );

  useEffect(() => {
    if (needsAttention) setExpanded(true);
  }, [needsAttention]);

  if (!canViewAutobalancer || isError || !status) return null;

  const counts = status.team_counts || {};
  const teamLabels = status.team_labels || {
    allies: "Alliierte",
    axis: "Achsenmächte",
  };
  const balanced = !status.required_switches && !needsAttention;

  return (
    <Box
      component="section"
      aria-label="Autobalancer"
      sx={{
        mb: 1.5,
        border: "1px solid",
        borderColor: needsAttention ? "warning.main" : "divider",
        borderRadius: 1,
        backgroundColor: "background.paper",
        overflow: "hidden",
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        spacing={1}
        sx={{ minHeight: 52, px: 1.5, py: 0.5 }}
      >
        {balanced ? (
          <CheckCircleOutlineIcon color="success" aria-hidden />
        ) : needsAttention ? (
          <ReportProblemOutlinedIcon color="warning" aria-hidden />
        ) : (
          <BalanceOutlinedIcon color="primary" aria-hidden />
        )}
        <Box sx={{ minWidth: 0, flex: 1 }}>
          <Stack
            direction="row"
            spacing={1}
            alignItems="center"
            flexWrap="wrap"
          >
            <Typography variant="subtitle2">Autobalancer</Typography>
            <Chip
              size="small"
              label={MODE_LABELS[status.mode] || status.mode}
              color={status.mode === "auto" ? "success" : "default"}
              sx={{ height: 22 }}
            />
            <Chip
              size="small"
              label={PHASE_LABELS[status.phase] || status.phase}
              variant="outlined"
              sx={{ height: 22 }}
            />
          </Stack>
          <Typography variant="caption" color="text.secondary">
            {balanced
              ? "Aktuell ausgeglichen"
              : `${status.required_switches ?? 0} Wechsel nötig`}
          </Typography>
        </Box>
        <Tooltip title={expanded ? "Details schließen" : "Details öffnen"}>
          <IconButton
            aria-label={
              expanded
                ? "Autobalancer-Details schließen"
                : "Autobalancer-Details öffnen"
            }
            aria-expanded={expanded}
            onClick={() => setExpanded((value) => !value)}
            sx={{ minWidth: 44, minHeight: 44 }}
          >
            <ExpandMoreIcon
              sx={{
                transform: expanded ? "rotate(180deg)" : "rotate(0deg)",
                transition: "transform 150ms ease",
              }}
            />
          </IconButton>
        </Tooltip>
      </Stack>

      <Collapse in={expanded}>
        <Box
          sx={{
            px: 1.5,
            pb: 1.5,
            borderTop: "1px solid",
            borderColor: "divider",
          }}
        >
          <TeamBalanceBar
            compact
            allies={counts.allies}
            axis={counts.axis}
            alliesLabel={teamLabels.allies}
            axisLabel={teamLabels.axis}
            targetDifference={status.target_difference}
          />
          {proposal && (
            <Alert severity="warning" sx={{ mt: 1 }}>
              Vorschlag: <strong>{proposal.player_name}</strong> nach{" "}
              {teamLabels[status.plan?.target_team] || "Gegenteam"}
            </Alert>
          )}
          {warnings.map((warning) => (
            <Alert key={warning} severity="warning" sx={{ mt: 1 }}>
              {warning}
            </Alert>
          ))}
          {blockReasons.map((reason) => (
            <Alert key={reason} severity="info" sx={{ mt: 1 }}>
              {reason}
            </Alert>
          ))}
          <Stack
            direction={{ xs: "column", sm: "row" }}
            spacing={1}
            sx={{ mt: 1.25 }}
          >
            <Button component={Link} to="/views/autobalancer" size="small">
              Dashboard öffnen
            </Button>
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
            {status.incident_id && (
              <Button
                size="small"
                color="warning"
                disabled={cancel.isPending}
                onClick={() => cancel.mutate()}
              >
                Incident abbrechen
              </Button>
            )}
          </Stack>
        </Box>
      </Collapse>
    </Box>
  );
};

export default AutobalancerCard;
