import i18n from "@/i18n";
import { translateOperatorMessage } from "@/i18n/operator-messages";
import { useTranslation } from "react-i18next";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Stack,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import { ChartsReferenceLine } from "@mui/x-charts/ChartsReferenceLine";
import { LineChart } from "@mui/x-charts/LineChart";
import { useQuery } from "@tanstack/react-query";
import { useState } from "react";
import { useTheme } from "@mui/material/styles";
import { cmd } from "@/utils/fetchUtils";

const formatMap = (name) =>
  (name || i18n.t("settingsPanels.autobalancer.unknownMap"))
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) => letter.toUpperCase());

const formatDate = (value) =>
  value
    ? new Intl.DateTimeFormat(i18n.resolvedLanguage, {
        dateStyle: "short",
        timeStyle: "short",
      }).format(new Date(value))
    : "–";

const formatDuration = (seconds) => {
  const minutes = Math.round((seconds || 0) / 60);
  return `${Math.floor(minutes / 60)}:${String(minutes % 60).padStart(
    2,
    "0"
  )} h`;
};

const STRATEGY_LABELS = () => ({
  "squad-first": i18n.t("settingsPanels.autobalancer.squadFirst"),
  "balanced-v2": i18n.t("settingsPanels.autobalancer.balancedV2"),
  "skill-first": i18n.t("settingsPanels.autobalancer.skillFirstDiagnostic"),
});

const CandidateWhatIf = ({ analysis, teamLabels }) => {
  const whatIf = analysis?.candidate_what_if;
  if (analysis?.quality?.source !== "live_snapshots") {
    return (
      <Alert severity="info" sx={{ mt: 1 }}>
        {i18n.t("settingsPanels.autobalancer.noHistoricalCandidates")}
      </Alert>
    );
  }
  if (!whatIf) {
    return (
      <Alert severity="success" sx={{ mt: 1 }}>
        {i18n.t("settingsPanels.autobalancer.noHistoricalIncident")}
      </Alert>
    );
  }
  return (
    <Box sx={{ mt: 2 }}>
      <Typography variant="h6" sx={{ fontWeight: 700 }}>
        {i18n.t("settingsPanels.autobalancer.candidateWhatIf")}
      </Typography>
      <Typography variant="body2" color="text.secondary">
        {i18n.t("settingsPanels.autobalancer.updated")}{" "}
        {formatDate(whatIf.captured_at)} · {teamLabels.allies}{" "}
        {whatIf.allies_count}:{whatIf.axis_count} {teamLabels.axis}{" "}
        {i18n.t("settingsPanels.autobalancer.modelFragment")}{" "}
        {whatIf.rating_model_version}
      </Typography>
      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", lg: "repeat(3, 1fr)" },
          gap: 1,
          mt: 1,
        }}
      >
        {Object.entries(whatIf.strategies || {}).map(([strategy, plan]) => {
          const candidate = plan?.candidates?.[0];
          return (
            <Box
              key={strategy}
              sx={{
                p: 1.5,
                border: 1,
                borderColor: "divider",
                borderRadius: 1,
              }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {STRATEGY_LABELS()[strategy] || strategy}
              </Typography>
              <Typography variant="body1" sx={{ mt: 0.5 }}>
                {candidate?.player_name ||
                  candidate?.player_id ||
                  i18n.t("settingsPanels.autobalancer.noCandidate")}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {i18n.t("settingsPanels.autobalancer.protectionTier")}{" "}
                {candidate?.effective_tier ?? "–"}{" "}
                {i18n.t("settingsPanels.autobalancer.gapFragment")}{" "}
                {plan?.rating_gap_before ?? "–"} →{" "}
                {plan?.projected_rating_gap ?? "–"}
              </Typography>
            </Box>
          );
        })}
      </Box>
      <Typography variant="caption" color="text.secondary">
        {translateOperatorMessage(whatIf.limitations, i18n.t)}
      </Typography>
    </Box>
  );
};

const HistoricalChart = ({ analysis, targetDifference, teamLabels }) => {
  const theme = useTheme();
  const points = (analysis?.timeline || [])
    .map((sample) => ({
      time: new Date(sample.updated_at),
      difference: sample.team_difference,
    }))
    .filter(
      (point) =>
        !Number.isNaN(point.time.getTime()) && Number.isFinite(point.difference)
    );
  if (points.length < 2) {
    return (
      <Alert severity="info">
        {i18n.t("settingsPanels.autobalancer.noRoundChart")}
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
            new Intl.DateTimeFormat(i18n.resolvedLanguage, {
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
          label: i18n.t("settingsPanels.autobalancer.historicalDifference"),
          data: points.map((point) => point.difference),
          color: theme.palette.info.main,
          showMark: false,
          curve: "linear",
          valueFormatter: (value) =>
            value > 0
              ? `${teamLabels.allies} +${value}`
              : value < 0
              ? `${teamLabels.axis} +${Math.abs(value)}`
              : i18n.t("settingsPanels.autobalancer.tie"),
        },
      ]}
      grid={{ horizontal: true }}
    >
      <ChartsReferenceLine
        y={targetDifference}
        label={i18n.t("settingsPanels.autobalancer.positiveLimit", {
          v0: targetDifference,
        })}
        lineStyle={{
          stroke: theme.palette.warning.main,
          strokeDasharray: "6 4",
        }}
      />
      <ChartsReferenceLine
        y={-targetDifference}
        label={i18n.t("settingsPanels.autobalancer.negativeLimit", {
          v0: targetDifference,
        })}
        lineStyle={{
          stroke: theme.palette.warning.main,
          strokeDasharray: "6 4",
        }}
      />
      <ChartsReferenceLine
        y={0}
        lineStyle={{ stroke: theme.palette.text.secondary, strokeWidth: 1.5 }}
      />
    </LineChart>
  );
};

const HistoricalAnalysis = ({ analysis, targetDifference, teamLabels }) => {
  if (!analysis) return null;
  const metrics = analysis.metrics || {};
  const quality = analysis.quality || {};
  const state =
    analysis.status === "balanced"
      ? {
          label: i18n.t("settingsPanels.autobalancer.historicallyBalanced"),
          color: "success",
        }
      : analysis.status === "unbalanced"
      ? {
          label: i18n.t("settingsPanels.autobalancer.historicallyUnbalanced"),
          color: "error",
        }
      : analysis.status === "transient"
      ? {
          label: i18n.t("settingsPanels.autobalancer.transientImbalance"),
          color: "warning",
        }
      : {
          label: i18n.t("settingsPanels.autobalancer.unreliableHistory"),
          color: "warning",
        };

  return (
    <Box
      sx={{ mt: 2, p: 2, border: 1, borderColor: "divider", borderRadius: 2 }}
    >
      <Stack
        direction={{ xs: "column", md: "row" }}
        justifyContent="space-between"
        spacing={1}
      >
        <Box>
          <Chip
            color={state.color}
            label={state.label}
            sx={{ fontWeight: 700 }}
          />
          <Typography variant="h5" sx={{ mt: 1, fontWeight: 700 }}>
            {formatMap(analysis.round?.map_name)}
          </Typography>
          <Typography variant="body2" color="text.secondary">
            {formatDate(analysis.round?.start)}{" "}
            {i18n.t("settingsPanels.autobalancer.toLower")}{" "}
            {formatDate(analysis.round?.end)}
          </Typography>
        </Box>
        <Stack
          direction="row"
          gap={1}
          flexWrap="wrap"
          alignContent="flex-start"
        >
          <Chip
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.inRangeValue", {
              v0:
                metrics.balanced_ratio == null
                  ? "–"
                  : `${Math.round(metrics.balanced_ratio * 100)} %`,
            })}
          />
          <Chip
            variant="outlined"
            label={i18n.t(
              "settingsPanels.autobalancer.largestDifferenceValue",
              { v0: metrics.maximum_difference ?? "–" }
            )}
          />
          <Chip
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.longestAdvantageValue", {
              v0: Math.round((metrics.longest_unbalanced_seconds || 0) / 60),
            })}
          />
          <Chip
            variant="outlined"
            label={i18n.t("settingsPanels.autobalancer.incidentCount", {
              v0: metrics.incident_count ?? "–",
            })}
          />
        </Stack>
      </Stack>
      {!quality.reliable && (
        <Alert severity="warning" sx={{ mt: 2 }}>
          {i18n.t("settingsPanels.autobalancer.unreliableHistoryHelp")}
        </Alert>
      )}
      <HistoricalChart
        analysis={analysis}
        targetDifference={targetDifference}
        teamLabels={teamLabels}
      />
      <CandidateWhatIf analysis={analysis} teamLabels={teamLabels} />
      <Typography variant="caption" color="text.secondary">
        {i18n.t("settingsPanels.autobalancer.dataSource")}{" "}
        {quality.source === "live_snapshots"
          ? i18n.t("settingsPanels.autobalancer.exactSnapshots")
          : i18n.t("settingsPanels.autobalancer.historicalLogs")}
        {i18n.t("settingsPanels.autobalancer.qualityValue", {
          v0: translateOperatorMessage(quality.level || "niedrig", i18n.t),
          v1: Math.round((quality.score || 0) * 100),
        })}
        {i18n.t("settingsPanels.autobalancer.validMeasurements", {
          v0: quality.valid_events || 0,
        })}
        {i18n.t("settingsPanels.autobalancer.noRetrospectiveCandidates")}
      </Typography>
    </Box>
  );
};

const AutobalancerRoundHistory = ({ config, teamLabels }) => {
  useTranslation();
  const [draft, setDraft] = useState({ search: "", dateFrom: "", dateTo: "" });
  const [filters, setFilters] = useState(draft);
  const [page, setPage] = useState(1);
  const [mapId, setMapId] = useState(null);

  const { data, isLoading, isError } = useQuery({
    queryKey: [
      {
        queryIdentifier: "get_autobalancer_round_archive",
        page,
        filters,
        mapId,
      },
    ],
    queryFn: () =>
      cmd.GET_AUTOBALANCER_ROUND_ARCHIVE({
        params: {
          page,
          limit: 12,
          search: filters.search,
          date_from: filters.dateFrom,
          date_to: filters.dateTo,
          map_id: mapId || "",
        },
      }),
    retry: false,
  });

  const runSearch = () => {
    setPage(1);
    setMapId(null);
    setFilters({ ...draft });
  };
  const clearSearch = () => {
    const empty = { search: "", dateFrom: "", dateTo: "" };
    setDraft(empty);
    setFilters(empty);
    setPage(1);
    setMapId(null);
  };
  const totalPages = Math.max(
    1,
    Math.ceil((data?.total || 0) / (data?.page_size || 12))
  );

  return (
    <Accordion sx={{ mt: 2 }}>
      <AccordionSummary expandIcon={<ExpandMoreIcon />}>
        <Stack
          direction={{ xs: "column", sm: "row" }}
          spacing={1}
          alignItems={{ sm: "center" }}
        >
          <Typography sx={{ fontWeight: 700 }}>
            {i18n.t("settingsPanels.autobalancer.browseRounds")}
          </Typography>
          {data && (
            <Chip
              size="small"
              label={i18n.t("settingsPanels.autobalancer.roundsFound", {
                v0: data.total,
              })}
            />
          )}
        </Stack>
      </AccordionSummary>
      <AccordionDetails>
        <Typography variant="body2" color="text.secondary" sx={{ mb: 2 }}>
          {i18n.t("settingsPanels.autobalancer.browseRoundsHelp")}
        </Typography>
        <Stack
          direction={{ xs: "column", md: "row" }}
          gap={1.5}
          alignItems={{ md: "center" }}
        >
          <TextField
            size="small"
            label={i18n.t("settingsPanels.autobalancer.searchMap")}
            placeholder={i18n.t("settingsPanels.autobalancer.mapExample")}
            value={draft.search}
            onChange={(event) =>
              setDraft({ ...draft, search: event.target.value })
            }
            onKeyDown={(event) => event.key === "Enter" && runSearch()}
          />
          <TextField
            size="small"
            type="date"
            label={i18n.t("settingsPanels.autobalancer.from")}
            value={draft.dateFrom}
            onChange={(event) =>
              setDraft({ ...draft, dateFrom: event.target.value })
            }
            InputLabelProps={{ shrink: true }}
          />
          <TextField
            size="small"
            type="date"
            label={i18n.t("settingsPanels.autobalancer.through")}
            value={draft.dateTo}
            onChange={(event) =>
              setDraft({ ...draft, dateTo: event.target.value })
            }
            InputLabelProps={{ shrink: true }}
          />
          <Button variant="contained" onClick={runSearch}>
            {i18n.t("settingsPanels.autobalancer.search")}
          </Button>
          <Button onClick={clearSearch}>
            {i18n.t("settingsPanels.autobalancer.reset")}
          </Button>
        </Stack>

        {isLoading && (
          <Stack alignItems="center" sx={{ py: 4 }}>
            <CircularProgress size={28} />
          </Stack>
        )}
        {isError && (
          <Alert severity="error" sx={{ mt: 2 }}>
            {i18n.t("settingsPanels.autobalancer.roundHistoryLoadError")}
          </Alert>
        )}
        {!isLoading && !isError && data && (
          <>
            <HistoricalAnalysis
              analysis={data.analysis}
              targetDifference={config?.target_difference ?? 2}
              teamLabels={teamLabels}
            />
            <TableContainer sx={{ mt: 2 }}>
              <Table size="small">
                <TableHead>
                  <TableRow>
                    <TableCell>Start</TableCell>
                    <TableCell>
                      {i18n.t("settingsPanels.autobalancer.map")}
                    </TableCell>
                    <TableCell>
                      {i18n.t("settingsPanels.autobalancer.duration")}
                    </TableCell>
                    <TableCell>
                      {i18n.t("settingsPanels.autobalancer.result")}
                    </TableCell>
                    <TableCell>Shadow</TableCell>
                    <TableCell align="right">
                      {i18n.t("settingsPanels.autobalancer.teamHistory")}
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {(data.rounds || []).map((round) => (
                    <TableRow
                      key={round.map_id}
                      selected={mapId === round.map_id}
                      hover
                    >
                      <TableCell>{formatDate(round.start)}</TableCell>
                      <TableCell>{formatMap(round.map_name)}</TableCell>
                      <TableCell>
                        {formatDuration(round.duration_seconds)}
                      </TableCell>
                      <TableCell>
                        {round.result?.allies ?? "–"} :{" "}
                        {round.result?.axis ?? "–"}
                      </TableCell>
                      <TableCell>{round.shadow_proposals}</TableCell>
                      <TableCell align="right">
                        <Button
                          size="small"
                          onClick={() => setMapId(round.map_id)}
                        >
                          {i18n.t("settingsPanels.autobalancer.show")}
                        </Button>
                      </TableCell>
                    </TableRow>
                  ))}
                  {!data.rounds?.length && (
                    <TableRow>
                      <TableCell colSpan={6}>
                        {i18n.t("settingsPanels.autobalancer.noMatchingRound")}
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>
            <Stack
              direction="row"
              justifyContent="space-between"
              alignItems="center"
              sx={{ mt: 1.5 }}
            >
              <Button
                disabled={page <= 1}
                onClick={() => {
                  setPage((value) => value - 1);
                  setMapId(null);
                }}
              >
                {i18n.t("settingsPanels.autobalancer.back")}
              </Button>
              <Typography variant="body2">
                {i18n.t("settingsPanels.autobalancer.page")} {page}{" "}
                {i18n.t("settingsPanels.autobalancer.ofLower")} {totalPages}
              </Typography>
              <Button
                disabled={page >= totalPages}
                onClick={() => {
                  setPage((value) => value + 1);
                  setMapId(null);
                }}
              >
                {i18n.t("settingsPanels.autobalancer.next")}
              </Button>
            </Stack>
          </>
        )}
      </AccordionDetails>
    </Accordion>
  );
};

export default AutobalancerRoundHistory;
import "@/i18n/register-settings-panels";
