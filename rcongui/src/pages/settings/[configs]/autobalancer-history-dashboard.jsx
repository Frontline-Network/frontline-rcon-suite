import {
  Alert,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  CircularProgress,
  LinearProgress,
  MenuItem,
  Stack,
  TextField,
  Typography,
  useTheme,
} from "@mui/material";
import { BarChart } from "@mui/x-charts/BarChart";
import { LineChart } from "@mui/x-charts/LineChart";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { cmd } from "@/utils/fetchUtils";

const percent = (value) =>
  value == null ? "–" : `${Math.round(value * 100)} %`;

const formatMap = (value) =>
  (value || "Unbekannte Karte")
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const ROLE_LABELS = {
  combat_infantry: "Combat Infantry",
  support: "Support / Engineer / Medic",
  leader: "Squad Leader",
  specialist: "Armor / Recon / Artillery / Mortar / Helicopter",
  legacy: "Legacy ohne Rollenbezug",
};

const STRATEGY_LABELS = {
  "squad-first": "Squad zuerst",
  "balanced-v2": "Ausgewogen V2",
  "skill-first": "Stärke zuerst (Diagnose)",
};

const Metric = ({ label, value, caption, color = "text.primary" }) => (
  <Card variant="outlined">
    <CardContent>
      <Typography variant="caption" color="text.secondary">
        {label}
      </Typography>
      <Typography variant="h4" color={color} sx={{ fontWeight: 800, mt: 0.5 }}>
        {value}
      </Typography>
      <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>
        {caption}
      </Typography>
    </CardContent>
  </Card>
);

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

const WeeklyBalanceChart = ({ weekly }) => {
  const theme = useTheme();
  const rows = (weekly || []).filter((row) => row.balanced_ratio != null);
  if (rows.length < 2) {
    return <Alert severity="info">Noch zu wenige messbare Wochen.</Alert>;
  }
  return (
    <LineChart
      height={280}
      xAxis={[
        {
          scaleType: "time",
          data: rows.map((row) => new Date(row.week)),
          valueFormatter: (value) =>
            new Intl.DateTimeFormat("de-DE", {
              day: "2-digit",
              month: "2-digit",
            }).format(value),
        },
      ]}
      yAxis={[
        {
          min: 0,
          max: 100,
          valueFormatter: (value) => `${value} %`,
        },
      ]}
      series={[
        {
          label: "Zeit im Zielbereich",
          data: rows.map((row) => Math.round(row.balanced_ratio * 100)),
          color: theme.palette.success.main,
          showMark: rows.length < 16,
          valueFormatter: (value) => `${value} %`,
        },
      ]}
      grid={{ horizontal: true }}
    />
  );
};

const WhatIfCharts = ({ rows }) => {
  const theme = useTheme();
  if (!rows?.length) return null;
  const labels = rows.map((row) => row.label);
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title="Was wäre ausgeglichen gewesen?"
        subtitle="Anteil der messbaren Spielzeit innerhalb der jeweiligen Zieldifferenz."
      >
        <BarChart
          height={280}
          xAxis={[{ scaleType: "band", data: labels }]}
          yAxis={[
            { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
          ]}
          series={[
            {
              label: "Balancezeit",
              data: rows.map((row) =>
                row.balanced_time_ratio == null
                  ? null
                  : Math.round(row.balanced_time_ratio * 100)
              ),
              color: theme.palette.success.main,
              valueFormatter: (value) =>
                value == null ? "nicht messbar" : `${value} %`,
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      <ChartShell
        title="Kosten der Varianten"
        subtitle="Geschätzte notwendige Teamwechsel pro messbarer Runde; weniger ist ruhiger."
      >
        <BarChart
          height={280}
          xAxis={[{ scaleType: "band", data: labels }]}
          yAxis={[{ min: 0 }]}
          series={[
            {
              label: "Wechsel je Runde",
              data: rows.map((row) => row.switches_per_round),
              color: theme.palette.warning.main,
              valueFormatter: (value) =>
                value == null ? "nicht messbar" : `${value} Wechsel/Runde`,
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
    </Box>
  );
};

const BreakdownCharts = ({ summary }) => {
  const theme = useTheme();
  const quality = Object.entries(summary?.quality_levels || {});
  const differences = summary?.difference_distribution || [];
  const maps = (summary?.maps || [])
    .filter((row) => row.balanced_ratio != null)
    .slice(0, 8);
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title="Datenqualität"
        subtitle="Exakt stammt aus neuen Live-Snapshots; hoch/mittel/niedrig aus rekonstruierten Logs."
      >
        <BarChart
          height={250}
          xAxis={[{ scaleType: "band", data: quality.map(([level]) => level) }]}
          yAxis={[{ min: 0, tickMinStep: 1 }]}
          series={[
            {
              label: "Runden",
              data: quality.map(([, count]) => count),
              color: theme.palette.info.main,
              valueFormatter: (value) => `${value} Runden`,
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      <ChartShell
        title="Größte Teamdifferenz je Runde"
        subtitle="Nur messbare Zeitfenster mit mindestens der konfigurierten Spielerzahl."
      >
        <BarChart
          height={250}
          xAxis={[
            {
              scaleType: "band",
              data: differences.map((row) => row.bucket),
            },
          ]}
          yAxis={[{ min: 0, tickMinStep: 1 }]}
          series={[
            {
              label: "Runden",
              data: differences.map((row) => row.rounds),
              color: theme.palette.warning.main,
              valueFormatter: (value) => `${value} Runden`,
            },
          ]}
          grid={{ horizontal: true }}
        />
      </ChartShell>
      {maps.length > 0 && (
        <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
          <ChartShell
            title="Balancezeit nach Karte"
            subtitle="Die meistgespielten Karten im gewählten Zeitraum; nur messbare Runden."
          >
            <BarChart
              layout="horizontal"
              height={Math.max(280, maps.length * 42)}
              yAxis={[
                {
                  scaleType: "band",
                  data: maps.map((row) => formatMap(row.map_name)),
                },
              ]}
              xAxis={[
                { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
              ]}
              series={[
                {
                  label: "Zeit im Zielbereich",
                  data: maps.map((row) => Math.round(row.balanced_ratio * 100)),
                  color: theme.palette.success.main,
                  valueFormatter: (value) => `${value} %`,
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

const CalibrationCharts = ({ quality }) => {
  const theme = useTheme();
  const roles = quality?.role_confidence || [];
  const confidence = quality?.confidence_distribution || [];
  const strategies = quality?.strategies || [];
  if (!roles.length && !strategies.length) {
    return (
      <Alert severity="info">
        Rollenrating und Strategievergleich sammeln erst mit den neuen exakten
        30-Sekunden-Snapshots belastbare Daten. Rekonstruierte Altrunden werden
        hierfür bewusst nicht verwendet.
      </Alert>
    );
  }
  return (
    <Box
      sx={{
        display: "grid",
        gridTemplateColumns: { xs: "1fr", lg: "1fr 1fr" },
        gap: 2,
      }}
    >
      <ChartShell
        title="Ratingvertrauen nach Rollenfamilie"
        subtitle="Median je Rollenfamilie. 60 % ist das Pilot-Mindestziel; mehr Beobachtungen machen das Rating stabiler."
      >
        {roles.length ? (
          <BarChart
            height={300}
            xAxis={[
              {
                scaleType: "band",
                data: roles.map(
                  (row) => ROLE_LABELS[row.role_family] || row.role_family
                ),
              },
            ]}
            yAxis={[
              { min: 0, max: 100, valueFormatter: (value) => `${value} %` },
            ]}
            series={[
              {
                label: "Medianes Vertrauen",
                data: roles.map((row) =>
                  Math.round((row.median_confidence || 0) * 100)
                ),
                color: theme.palette.info.main,
                valueFormatter: (value) => `${value} %`,
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">Noch keine exakten Rollendaten.</Alert>
        )}
      </ChartShell>
      <ChartShell
        title="Verteilung der Ratingkonfidenz"
        subtitle="Anzahl Spielerbeobachtungen je Vertrauensbereich; Ziel ist eine Verschiebung in die Bereiche ab 60 %."
      >
        {confidence.some((row) => row.observations) ? (
          <BarChart
            height={300}
            xAxis={[
              {
                scaleType: "band",
                data: confidence.map((row) => row.bucket),
              },
            ]}
            yAxis={[{ min: 0, tickMinStep: 1 }]}
            series={[
              {
                label: "Beobachtungen",
                data: confidence.map((row) => row.observations),
                color: theme.palette.warning.main,
                valueFormatter: (value) => `${value} Beobachtungen`,
              },
            ]}
            grid={{ horizontal: true }}
          />
        ) : (
          <Alert severity="info">Noch keine Konfidenzdaten.</Alert>
        )}
      </ChartShell>
      <Box sx={{ gridColumn: { lg: "1 / -1" } }}>
        <ChartShell
          title="Shadow-Strategien im direkten Vergleich"
          subtitle="Durchschnittliche projizierte Ratingdifferenz nach dem ersten Kandidaten. Niedriger ist statistisch ausgeglichener; Squad-Schutz bleibt bei Ausgewogen V2 vorrangig."
        >
          {strategies.length ? (
            <BarChart
              height={300}
              xAxis={[
                {
                  scaleType: "band",
                  data: strategies.map(
                    (row) => STRATEGY_LABELS[row.strategy] || row.strategy
                  ),
                },
              ]}
              yAxis={[{ min: 0 }]}
              series={[
                {
                  label: "Ø projizierte Ratingdifferenz",
                  data: strategies.map((row) => row.average_projected_gap),
                  color: theme.palette.success.main,
                  valueFormatter: (value) =>
                    value == null ? "noch keine Daten" : value.toFixed(1),
                },
              ]}
              grid={{ horizontal: true }}
            />
          ) : (
            <Alert severity="info">Noch kein V2-Strategievergleich.</Alert>
          )}
        </ChartShell>
      </Box>
    </Box>
  );
};

const AutobalancerHistoryDashboard = ({
  config,
  shadowSummary = {},
  pilotGoals = {},
}) => {
  const initial = {
    days: 90,
    search: "",
    targetDifference: config?.target_difference ?? 2,
    stableSeconds: config?.stable_difference_seconds ?? 45,
  };
  const [draft, setDraft] = useState(initial);
  const [filters, setFilters] = useState(initial);
  const { data, isLoading, isFetching, isError } = useQuery({
    queryKey: [
      {
        queryIdentifier: "get_autobalancer_history_dashboard",
        filters,
      },
    ],
    queryFn: () =>
      cmd.GET_AUTOBALANCER_HISTORY_DASHBOARD({
        params: {
          days: filters.days,
          search: filters.search,
          target_difference: filters.targetDifference,
          stable_difference_seconds: filters.stableSeconds,
          limit: 100,
        },
      }),
    retry: false,
    staleTime: 10 * 60 * 1000,
    refetchInterval: (query) =>
      query.state.data?.backfill?.complete ? false : 15_000,
  });
  const summary = data?.summary;
  const sources = data?.source_counts || {};
  const quality = data?.rating_quality || {};
  const ratingConfidence =
    quality.median_rating_confidence ?? shadowSummary.median_rating_confidence;
  const criteria = [
    {
      label: `${quality.fully_captured_rounds || 0}/10 vollständige Runden`,
      met: (quality.fully_captured_rounds || 0) >= 10,
    },
    {
      label: `${percent(quality.snapshot_coverage)} exakte Abdeckung`,
      met: quality.snapshot_coverage >= 0.95,
    },
    {
      label: `${shadowSummary.reviewed || 0}/20 Bewertungen`,
      met: (shadowSummary.reviewed || 0) >= 20,
    },
    {
      label: `${percent(shadowSummary.acceptance_rate)} akzeptiert`,
      met: shadowSummary.acceptance_rate >= 0.9,
    },
    {
      label: `${percent(ratingConfidence)} Ratingvertrauen`,
      met: ratingConfidence >= 0.6,
    },
    {
      label: `${percent(
        shadowSummary.gap_guardrail_rate ?? quality.gap_guardrail_rate
      )} Rating-Guardrail`,
      met:
        (shadowSummary.gap_guardrail_rate ?? quality.gap_guardrail_rate) >=
        0.95,
    },
    {
      label: `${shadowSummary.rule_warning_proposals || 0} harte Verletzungen`,
      met: (shadowSummary.rule_warning_proposals || 0) === 0,
    },
    {
      label: `${shadowSummary.size_overshoot_proposals || 0} Überschwinger`,
      met: (shadowSummary.size_overshoot_proposals || 0) === 0,
    },
  ];
  const calibrationReady = criteria.every((criterion) => criterion.met);

  return (
    <Box sx={{ mt: 2 }}>
      <Stack
        direction={{ xs: "column", lg: "row" }}
        justifyContent="space-between"
        spacing={1}
      >
        <Box>
          <Typography variant="h5" sx={{ fontWeight: 800 }}>
            Historische Balance-Auswertung
          </Typography>
          <Typography variant="body2" color="text.secondary">
            Vergleicht echte FLN-Runden mit den aktuellen und alternativen
            Balancer-Einstellungen.
          </Typography>
        </Box>
        <Stack direction="row" gap={1} flexWrap="wrap" alignItems="center">
          <Chip
            size="small"
            variant="outlined"
            label={`${sources.live_snapshots || 0} exakt`}
          />
          <Chip
            size="small"
            variant="outlined"
            label={`${sources.historical_logs || 0} rekonstruiert`}
          />
          {data?.generated_at && (
            <Typography variant="caption" color="text.secondary">
              Stand {new Date(data.generated_at).toLocaleString("de-DE")}
            </Typography>
          )}
        </Stack>
      </Stack>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: {
            xs: "1fr",
            sm: "repeat(2, minmax(0, 1fr))",
            xl: "repeat(5, minmax(0, 1fr))",
          },
          gap: 1.5,
          mt: 1.5,
        }}
      >
        <Metric
          label="Exakte Datenabdeckung"
          value={percent(quality.snapshot_coverage)}
          caption={`Ziel ${percent(0.95)} · nur gültige 30-Sekunden-Snapshots`}
          color={
            quality.snapshot_coverage >= 0.95 ? "success.main" : "warning.main"
          }
        />
        <Metric
          label="Mediane Ratingkonfidenz"
          value={percent(
            quality.median_rating_confidence ??
              shadowSummary.median_rating_confidence
          )}
          caption={`Ziel ${percent(
            pilotGoals.rating_confidence_target ?? 0.6
          )} · role-aware-v2`}
          color={
            (quality.median_rating_confidence ??
              shadowSummary.median_rating_confidence) >= 0.6
              ? "success.main"
              : "warning.main"
          }
        />
        <Metric
          label="Bewertete Vorschläge"
          value={shadowSummary.reviewed ?? 0}
          caption={`Ziel ${
            pilotGoals.reviewed_proposals_target ?? 20
          } · Adminbewertungen`}
          color={
            (shadowSummary.reviewed ?? 0) >=
            (pilotGoals.reviewed_proposals_target ?? 20)
              ? "success.main"
              : "text.primary"
          }
        />
        <Metric
          label="Admin-Akzeptanzrate"
          value={percent(shadowSummary.acceptance_rate)}
          caption={`Ziel ${percent(
            pilotGoals.acceptance_rate_target ?? 0.9
          )} · nur bewertete Vorschläge`}
          color={
            shadowSummary.acceptance_rate >=
            (pilotGoals.acceptance_rate_target ?? 0.9)
              ? "success.main"
              : "warning.main"
          }
        />
        <Metric
          label="Harte Regelverletzungen"
          value={shadowSummary.rule_warning_proposals ?? 0}
          caption="Ziel 0 · Commander, Cooldown, Snapshot und Teamrichtung"
          color={
            (shadowSummary.rule_warning_proposals ?? 0) === 0
              ? "success.main"
              : "error.main"
          }
        />
      </Box>

      <Alert severity={calibrationReady ? "success" : "info"} sx={{ mt: 1.5 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, mb: 0.75 }}>
          {calibrationReady
            ? "Alle messbaren V2-Freigabekriterien sind erfüllt"
            : "Shadow-Kalibrierung läuft – manual bleibt gesperrt"}
        </Typography>
        <Stack direction="row" gap={0.75} flexWrap="wrap">
          {criteria.map((criterion) => (
            <Chip
              key={criterion.label}
              size="small"
              color={criterion.met ? "success" : "default"}
              variant={criterion.met ? "filled" : "outlined"}
              label={criterion.label}
            />
          ))}
        </Stack>
        <Typography variant="caption" sx={{ display: "block", mt: 0.75 }}>
          Auch bei erfüllten Kriterien erfolgt kein automatischer Moduswechsel;
          der Kalibrierungsbericht wird gemeinsam geprüft.
        </Typography>
      </Alert>

      <Card variant="outlined" sx={{ mt: 1.5 }}>
        <CardContent>
          <Stack
            direction={{ xs: "column", md: "row" }}
            gap={1.5}
            alignItems={{ md: "center" }}
          >
            <TextField
              select
              size="small"
              label="Zeitraum"
              value={draft.days}
              onChange={(event) =>
                setDraft({ ...draft, days: Number(event.target.value) })
              }
              sx={{ minWidth: 150 }}
            >
              <MenuItem value={30}>30 Tage</MenuItem>
              <MenuItem value={90}>90 Tage</MenuItem>
              <MenuItem value={180}>180 Tage</MenuItem>
              <MenuItem value={365}>1 Jahr</MenuItem>
            </TextField>
            <TextField
              size="small"
              label="Karte optional"
              placeholder="z. B. Carentan"
              value={draft.search}
              onChange={(event) =>
                setDraft({ ...draft, search: event.target.value })
              }
            />
            <TextField
              select
              size="small"
              label="Erlaubte Differenz"
              value={draft.targetDifference}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  targetDifference: Number(event.target.value),
                })
              }
              sx={{ minWidth: 170 }}
            >
              {[1, 2, 3].map((value) => (
                <MenuItem key={value} value={value}>
                  {value} Spieler
                </MenuItem>
              ))}
            </TextField>
            <TextField
              select
              size="small"
              label="Muss stabil sein"
              value={draft.stableSeconds}
              onChange={(event) =>
                setDraft({
                  ...draft,
                  stableSeconds: Number(event.target.value),
                })
              }
              sx={{ minWidth: 165 }}
            >
              {[30, 45, 60, 90].map((value) => (
                <MenuItem key={value} value={value}>
                  {value} Sekunden
                </MenuItem>
              ))}
            </TextField>
            <Button
              variant="contained"
              disabled={isFetching}
              onClick={() => setFilters({ ...draft })}
            >
              Auswerten
            </Button>
          </Stack>
          {isFetching && <LinearProgress sx={{ mt: 1.5 }} />}
        </CardContent>
      </Card>

      {isLoading && (
        <Stack alignItems="center" sx={{ py: 6 }}>
          <CircularProgress />
          <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
            Historische Runden werden ausgewertet …
          </Typography>
        </Stack>
      )}
      {isError && (
        <Alert severity="error" sx={{ mt: 2 }}>
          Die historische Sammelauswertung konnte nicht geladen werden.
        </Alert>
      )}
      {!isLoading && !isError && summary && (
        <Stack spacing={2} sx={{ mt: 2 }}>
          {!data.backfill?.complete && (
            <Alert severity="info">
              Historische Auswertung wird im Hintergrund aufgebaut:{" "}
              {data.backfill?.analyzed_rounds || 0}/
              {data.backfill?.requested_rounds || 0} Runden fertig. Die Seite
              aktualisiert sich automatisch.
            </Alert>
          )}
          <Box
            sx={{
              display: "grid",
              gridTemplateColumns: {
                xs: "1fr",
                sm: "repeat(2, minmax(0, 1fr))",
                xl: "repeat(4, minmax(0, 1fr))",
              },
              gap: 1.5,
            }}
          >
            <Metric
              label="Messbare Runden"
              value={`${summary.measurable_rounds}/${summary.rounds_analyzed}`}
              caption={`${percent(summary.coverage_ratio)} Datenabdeckung`}
              color={
                summary.coverage_ratio >= 0.7 ? "success.main" : "warning.main"
              }
            />
            <Metric
              label="Zeit im Zielbereich"
              value={percent(summary.balanced_time_ratio)}
              caption={`Differenz höchstens ${filters.targetDifference}`}
            />
            <Metric
              label="Balance-Vorfälle"
              value={summary.incidents_per_10_rounds ?? "–"}
              caption="pro 10 messbare Runden"
            />
            <Metric
              label="Geschätzte Eingriffe"
              value={summary.switches_per_round ?? "–"}
              caption="notwendige Wechsel je messbarer Runde"
            />
          </Box>
          {summary.coverage_ratio < 0.5 && (
            <Alert severity="warning">
              Weniger als die Hälfte der gewählten Runden ist zuverlässig
              messbar. Die Ergebnisgraphen verwenden ausschließlich belastbare
              Zeitfenster; nicht messbare Runden bleiben in der
              Datenqualitätsanzeige sichtbar.
            </Alert>
          )}
          <CalibrationCharts quality={quality} />
          <ChartShell
            title="Balancezeit im Wochenverlauf"
            subtitle="Anteil der messbaren Zeit innerhalb der gewählten Teamdifferenz."
          >
            <WeeklyBalanceChart weekly={summary.weekly} />
          </ChartShell>
          <WhatIfCharts rows={data.what_if} />
          <BreakdownCharts summary={summary} />
        </Stack>
      )}
    </Box>
  );
};

export default AutobalancerHistoryDashboard;
