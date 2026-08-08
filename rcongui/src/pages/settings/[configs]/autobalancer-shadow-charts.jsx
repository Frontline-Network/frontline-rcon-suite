import {
  Alert,
  Box,
  Card,
  CardContent,
  Chip,
  Stack,
  Typography,
  useTheme,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { ChartsReferenceLine } from "@mui/x-charts/ChartsReferenceLine";
import { LineChart } from "@mui/x-charts/LineChart";
import TeamBalanceBar from "@/components/shared/TeamBalanceBar";

const PHASE_LABELS = {
  idle: "Kein Eingriff nötig",
  observing: "Ungleichgewicht wird beobachtet",
  volunteer: "Freiwillige werden gesucht",
  proposed: "Shadow-Vorschlag erstellt",
  armed: "Kandidat vorgemerkt",
  verifying: "Wechsel wird bestätigt",
  cooldown: "Neue Stabilitätsprüfung läuft",
  blocked: "Sicherheitsbedingung blockiert",
};

const UNRELIABLE_REASONS = [
  "Spielerdaten sind unvollständig",
  "Teamzählungen stimmen nicht überein",
  "Kartendaten sind nicht stabil",
  "Autobalancer-Dienst liefert keinen aktuellen Status",
];

const REJECTION_LABELS = {
  squad_should_stay: "Squad zusammenhalten",
  critical_role: "Kritische Rolle",
  recent_join_or_move: "Join-/Squadzeit",
  better_candidate: "Besserer Kandidat",
  skill_balance: "Stärkeausgleich",
  wrong_team_counts: "Teamzählung",
  other: "Anderer Grund",
};

const STRATEGY_LABELS = {
  "squad-first": "Squad zuerst",
  "balanced-v2": "Ausgewogen V2",
  "skill-first": "Stärke zuerst (Diagnose)",
};

const ChartShell = ({ title, subtitle, children }) => (
  <Card variant="outlined" sx={{ minWidth: 0 }}>
    <CardContent>
      <Typography variant="h6" sx={{ fontWeight: 700 }}>
        {title}
      </Typography>
      <Typography variant="caption" color="text.secondary">
        {subtitle}
      </Typography>
      <Box sx={{ mt: 1 }}>{children}</Box>
    </CardContent>
  </Card>
);

const LiveBalance = ({ status, targetDifference, minimumPlayers }) => {
  const theme = useTheme();
  const counts = status?.team_counts || {};
  const allies = counts.allies;
  const axis = counts.axis;
  const hasCounts = Number.isFinite(allies) && Number.isFinite(axis);
  const reasons = status?.block_reasons || [];
  const updatedAt = status?.updated_at ? new Date(status.updated_at) : null;
  const stale =
    !updatedAt ||
    Number.isNaN(updatedAt.getTime()) ||
    Date.now() - updatedAt.getTime() > 20_000;
  const unreliable =
    stale ||
    !hasCounts ||
    reasons.some((reason) => UNRELIABLE_REASONS.includes(reason));
  const difference = hasCounts ? Math.abs(allies - axis) : null;
  const balanced = !unreliable && difference <= targetDifference;
  const inactive = reasons.includes("Mindestspielerzahl ist nicht erreicht");

  const state = unreliable
    ? {
        label: stale
          ? "KEINE AKTUELLEN LIVE-DATEN"
          : "NICHT VERLÄSSLICH MESSBAR",
        color: "warning",
        border: theme.palette.warning.main,
        background: theme.palette.warning.main + "12",
      }
    : balanced
    ? {
        label: "AUSGEGLICHEN",
        color: "success",
        border: theme.palette.success.main,
        background: theme.palette.success.main + "12",
      }
    : {
        label: "UNAUSGEGLICHEN",
        color: "error",
        border: theme.palette.error.main,
        background: theme.palette.error.main + "12",
      };

  return (
    <Box
      sx={{
        mt: 2,
        p: { xs: 2, md: 3 },
        border: 2,
        borderColor: state.border,
        borderRadius: 2,
        backgroundColor: state.background,
      }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        alignItems={{ md: "center" }}
        spacing={2}
      >
        <Box>
          <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
            <Chip
              color={state.color}
              label={state.label}
              sx={{ fontWeight: 800, letterSpacing: 0.5 }}
            />
            <Chip
              size="small"
              variant="outlined"
              label="LIVE · alle 5 Sekunden"
            />
            {updatedAt && !Number.isNaN(updatedAt.getTime()) && (
              <Typography variant="caption" color="text.secondary">
                Stand {updatedAt.toLocaleTimeString("de-DE")}
              </Typography>
            )}
          </Stack>
          {unreliable && (
            <Typography variant="body1" sx={{ mt: 1 }}>
              Der Snapshot ist unvollständig. Aus diesen Zahlen wird keine Balanceentscheidung abgeleitet.
            </Typography>
          )}
        </Box>
        <Stack alignItems={{ md: "flex-end" }} spacing={0.5}>
          <Typography variant="h5" sx={{ fontWeight: 700 }}>
            {unreliable
              ? "Keine Entscheidung"
              : `${status?.required_switches ?? 0} Wechsel nötig`}
          </Typography>
          <Typography color="text.secondary">
            {PHASE_LABELS[status?.phase] || status?.phase || "Kein Live-Status"}
          </Typography>
          {inactive && (
            <Typography variant="caption" color="text.secondary">
              Unter {minimumPlayers} Spielern bleibt der Balancer inaktiv.
            </Typography>
          )}
        </Stack>
      </Stack>

      <TeamBalanceBar
        allies={allies}
        axis={axis}
        targetDifference={targetDifference}
      />

      {status?.team_ratings && (
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
          <Chip
            size="small"
            variant="outlined"
            label={`Teamrating Allies ${
              status.team_ratings.allies ?? "–"
            } · Axis ${status.team_ratings.axis ?? "–"}`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={`Datenvertrauen ${Math.round(
              (status.data_confidence || 0) * 100
            )} %`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={`Strategie ${
              STRATEGY_LABELS[status.strategy] || status.strategy || "–"
            }`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={`Ratingmodell ${status.rating_model_version || "legacy"}`}
          />
        </Stack>
      )}

      {(status?.warnings || []).map((warning) => (
        <Alert key={warning} severity="warning" sx={{ mt: 1 }}>
          {warning}
        </Alert>
      ))}

      {unreliable && (
        <Stack direction="row" gap={1} flexWrap="wrap" sx={{ mt: 1.5 }}>
          {stale && (
            <Chip
              size="small"
              color="warning"
              label="Der letzte Messwert ist älter als 20 Sekunden"
            />
          )}
          {reasons
            .filter((reason) => UNRELIABLE_REASONS.includes(reason))
            .map((reason) => (
              <Chip key={reason} size="small" color="warning" label={reason} />
            ))}
        </Stack>
      )}
    </Box>
  );
};

const DifferenceTimeline = ({ timeline, targetDifference }) => {
  const points = (timeline || [])
    .map((sample) => ({
      time: new Date(sample.updated_at),
      difference: sample.team_difference,
      roundId: sample.round_id,
    }))
    .filter(
      (point) =>
        !Number.isNaN(point.time.getTime()) && Number.isFinite(point.difference)
    );

  if (points.length < 8) {
    return (
      <Alert severity="info">
        Zeitverlauf sammelt Daten: {points.length}/8 Messpunkte. Alle 30
        Sekunden kommt ein Punkt hinzu; danach erscheint der Graph.
      </Alert>
    );
  }

  const maximum = Math.max(
    targetDifference + 2,
    ...points.map((point) => Math.abs(point.difference))
  );
  return (
    <LineChart
      height={300}
      margin={{ left: 50, right: 20, top: 20, bottom: 30 }}
      xAxis={[
        {
          data: points.map((point) => point.time),
          scaleType: "time",
          valueFormatter: (value) =>
            new Intl.DateTimeFormat("de-DE", {
              hour: "2-digit",
              minute: "2-digit",
            }).format(value),
        },
      ]}
      yAxis={[
        {
          min: -maximum,
          max: maximum,
          tickMinStep: 1,
          valueFormatter: (value) => `${value > 0 ? "+" : ""}${value}`,
        },
      ]}
      series={[
        {
          label: "Teamdifferenz",
          data: points.map((point) => point.difference),
          color: "#2563eb",
          showMark: points.length < 40,
          curve: "linear",
          valueFormatter: (value) =>
            value > 0
              ? `Allies +${value}`
              : value < 0
              ? `Axis +${Math.abs(value)}`
              : "Gleichstand",
        },
      ]}
      grid={{ horizontal: true }}
    >
      <ChartsReferenceLine
        y={targetDifference}
        label={`Grenze +${targetDifference}`}
        lineStyle={{ stroke: "#d97706", strokeDasharray: "6 4" }}
      />
      <ChartsReferenceLine
        y={-targetDifference}
        label={`Grenze -${targetDifference}`}
        lineStyle={{ stroke: "#d97706", strokeDasharray: "6 4" }}
      />
      <ChartsReferenceLine
        y={0}
        lineStyle={{ stroke: "#64748b", strokeWidth: 1.5 }}
      />
    </LineChart>
  );
};

const DistributionCharts = ({ summary }) => {
  const tiers = Object.entries(summary?.protection_tiers || {});
  const reviews = [
    { label: "Akzeptabel", value: summary?.accepted || 0 },
    { label: "Abgelehnt", value: summary?.rejected || 0 },
    { label: "Offen", value: summary?.pending_review || 0 },
  ];
  const rejectionReasons = Object.entries(summary?.rejection_categories || {});

  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
        mt: 2,
      }}
    >
      <ChartShell
        title="Ausgewählte Schutzstufen"
        subtitle="Anzahl Shadow-Vorschläge je Stufe; 0 ist der geringste Eingriff, 5 der stärkste Schutz."
      >
        {tiers.length ? (
          <BarChart
            height={260}
            xAxis={[
              {
                scaleType: "band",
                data: tiers.map(([tier]) => `Stufe ${tier}`),
              },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                data: tiers.map(([, count]) => count),
                label: "Vorschläge",
                color: "#2563eb",
                valueFormatter: (value) => `${value} Vorschläge`,
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">Noch keine Shadow-Vorschläge vorhanden.</Alert>
        )}
      </ChartShell>

      <ChartShell
        title="Bewertungen"
        subtitle="Wie viele Kandidaten wurden akzeptiert, abgelehnt oder noch nicht geprüft?"
      >
        {summary?.proposals ? (
          <BarChart
            height={260}
            xAxis={[
              { scaleType: "band", data: reviews.map((item) => item.label) },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                data: reviews.map((item) => item.value),
                label: "Vorschläge",
                color: "#0f766e",
                valueFormatter: (value) => `${value} Vorschläge`,
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">Noch keine Bewertungen vorhanden.</Alert>
        )}
      </ChartShell>

      {rejectionReasons.length > 0 && (
        <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
          <ChartShell
            title="Ablehnungsgründe"
            subtitle="Häufigkeit des wichtigsten von einem Admin gewählten Grundes."
          >
            <BarChart
              layout="horizontal"
              height={Math.max(240, rejectionReasons.length * 48)}
              yAxis={[
                {
                  scaleType: "band",
                  data: rejectionReasons.map(
                    ([reason]) => REJECTION_LABELS[reason] || reason
                  ),
                },
              ]}
              xAxis={[{ min: 0, tickMinStep: 1 }]}
              series={[
                {
                  data: rejectionReasons.map(([, count]) => count),
                  label: "Ablehnungen",
                  color: "#d97706",
                  valueFormatter: (value) => `${value} Ablehnungen`,
                },
              ]}
              grid={{ vertical: true }}
            />
          </ChartShell>
        </Box>
      )}
    </Box>
  );
};

const AutobalancerShadowCharts = ({ status, timeline, summary, config }) => {
  const targetDifference = config?.target_difference ?? 2;
  return (
    <>
      <LiveBalance
        status={status}
        targetDifference={targetDifference}
        minimumPlayers={config?.minimum_players ?? 40}
      />
      <Box sx={{ mt: 2 }}>
        <ChartShell
          title="Teamdifferenz im Zeitverlauf"
          subtitle="Letzte sechs Stunden, Messung alle 30 Sekunden. Positive Werte: Allies größer; negative Werte: Axis größer. Orange Linien markieren die erlaubte Differenz."
        >
          <DifferenceTimeline
            timeline={timeline}
            targetDifference={targetDifference}
          />
        </ChartShell>
      </Box>
      <DistributionCharts summary={summary} />
    </>
  );
};

export default AutobalancerShadowCharts;
