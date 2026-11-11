import ExcludedPlayers from "./ExcludedPlayers";
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import {
  Alert,
  Tabs,
  Tab,
  List,
  ListItemButton,
  ListItemText,
  Autocomplete,
  Collapse,
  Box,
  Button,
  Card,
  CardContent,
  Chip,
  FormControlLabel,
  MenuItem,
  Stack,
  Slider,
  Switch,
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableRow,
  TextField,
  Typography,
} from "@mui/material";
import { get, execute } from "@/utils/fetchUtils";
import { isFakeMode } from "@/mirage/demo-data";
import { useAuth } from "@/hooks/useAuth";

async function read(command) {
  const response = await get(command);
  const data = await response.json();
  if (data.failed || data.error)
    throw new Error(
      typeof data.error === "string" ? data.error : JSON.stringify(data.error)
    );
  return data.result;
}

const labels = {
  melee: "Nahkampf",
  round: "Rundentreue",
  weekly: "Wochenaktivität",
  weekly_support: "Wöchentliche Team-Unterstützung",
  milestones: "Spielzeit-Meilensteine",
  balance: "Freiwilliger Teamausgleich",
};
const notes = {
  weekly_support:
    "Sammle Unterstützungspunkte über mehrere Runden: Montag bis Sonntag in der eingestellten Server-Zeitzone. Einmal pro Woche gibt es VIP beim Erreichen des Ziels. Nur neu erspielte Punkte zählen; die Seeding-Pause und das gemeinsame VIP-Limit gelten auch hier. Zielwerte gelten nur für diesen Server und können für HLL und HLLV unterschiedlich eingestellt werden.",
  melee:
    "Nur Gegnerkills mit Messer oder Spaten. Wiederholte Gegner werden gemeinsam mit Challenges begrenzt.",
  round:
    "Belohne Spieler, die bis zum Rundenende bleiben. Sowohl die Mindestspielzeit als auch der Mindestanteil an der Runde müssen erreicht sein.",
  weekly:
    "Belohne regelmäßiges Spielen: An der gewählten Anzahl von Tagen muss jeweils die Mindestspielzeit erreicht werden. Die Woche läuft von Montag bis Sonntag.",
  milestones:
    "Belohne insgesamt gesammelte Spielzeit ab Aktivierung. Jede Stufe kann ein Spieler einmal erreichen; frühere Spielzeit wird nicht nachgetragen.",
  balance:
    "Der bestehende Autobalancer-Befehl !balance meldet Spieler auch für diese Belohnung an. VIP gibt es erst nach dem freiwilligen Wechsel und der Mindestspielzeit im kleineren Team. Erzwungene Wechsel zählen nicht.",
};
const results = {
  queued: "Vorgemerkt",
  prepared: "Abgleich ausstehend",
  awarded: "Gutgeschrieben",
  preview: "Vorschau",
  skipped: "Nicht vergeben",
  review: "Prüfung erforderlich",
  reviewed: "Manuell geprüft",
};
const reasons = {
  daily_budget: "24-Stunden-Budget erreicht",
  rule_limit: "Regellimit erreicht",
  permanent_vip: "Dauerhaftes VIP",
  disabled_or_paused: "Deaktiviert oder pausiert",
  previous_write_needs_review: "Frühere Vergabe prüfen",
  partial_budget: "Teilbetrag: Restbudget",
  reconciled: "Nach Neustart bestätigt",
  uncertain_write: "Schreibergebnis unklar",
  readback_mismatch: "VIP-Ablauf nicht bestätigt",
};

const awardPeriods = {
  rolling_day: "Letzte 24 Stunden",
  day: "Täglich",
  week: "Wöchentlich",
  month: "Monatlich",
};
function ThresholdSlider({
  label,
  value,
  onChange,
  min = 1,
  max = 10000,
  helperText,
}) {
  const [original] = useState(value);
  const stops = [];
  for (
    let n = min;
    n <= max;
    n +=
      n < 100
        ? 1
        : n < 1000
        ? 10
        : n < 10000
        ? 100
        : n < 100000
        ? 1000
        : n < 1000000
        ? 10000
        : 1000000
  )
    stops.push(n);
  const choices = [...new Set([...stops, max, original, value])]
    .filter((n) => Number.isFinite(n) && n >= min)
    .sort((a, b) => a - b);
  return (
    <Box
      sx={{
        minWidth: 0,
        width: "100%",
        flex: "1 1 auto",
        px: 1,
        "& > .MuiTypography-root:first-child": { display: "inline-block" },
        "& > .MuiTypography-root:nth-child(2)": { float: "right" },
      }}
    >
      <Typography variant="body2">{label}</Typography>
      <Typography fontWeight={600}>{value.toLocaleString("de-DE")}</Typography>
      <Slider
        aria-label={label}
        value={choices.indexOf(value)}
        min={0}
        max={choices.length - 1}
        step={1}
        valueLabelDisplay="auto"
        valueLabelFormat={(i) => choices[i]}
        getAriaValueText={(i) => String(choices[i])}
        onChange={(_, i) => onChange(choices[i])}
      />
      {helperText && (
        <Typography variant="caption" color="text.secondary">
          {helperText}
        </Typography>
      )}
    </Box>
  );
}
function AwardLimitSlider({
  value,
  onChange,
  period = "rolling_day",
  onPeriodChange,
}) {
  const [original] = useState(value);
  const choices = [
    ...new Set([
      ...Array.from({ length: 20 }, (_, i) => i + 1),
      25,
      30,
      50,
      100,
      250,
      500,
      1000,
      original,
      value,
    ]),
  ]
    .filter((v) => Number.isInteger(v) && v >= 1 && v <= 1000)
    .sort((a, b) => a - b);
  const format = (count) =>
    `${count} ${count === 1 ? "Vergabe" : "Vergaben"} / ${
      awardPeriods[period]
    }`;
  return (
    <Box
      sx={{
        minWidth: 0,
        width: "100%",
        flex: "1 1 auto",
        px: 1,
        "& > .MuiTypography-root:first-child": { display: "inline-block" },
        "& > .MuiTypography-root:nth-child(2)": { float: "right" },
      }}
    >
      <Typography variant="body2">Maximale Vergaben</Typography>
      <Typography fontWeight={600} sx={{ mb: 1 }}>
        {format(value)}
      </Typography>
      <Slider
        aria-label="Maximale Vergaben"
        value={choices.indexOf(value)}
        min={0}
        max={choices.length - 1}
        step={1}
        marks={[1, 10, 20, 1000].map((count) => ({
          value: choices.indexOf(count),
          label: String(count),
        }))}
        valueLabelDisplay="auto"
        valueLabelFormat={(index) => choices[index]}
        getAriaValueText={(index) => format(choices[index])}
        onChange={(_, index) => onChange(choices[index])}
      />
      <Typography variant="caption" color="text.secondary">
        So oft darf ein Spieler diese Belohnung im gewählten Zeitraum erhalten.
        Das gemeinsame VIP-Limit gilt zusätzlich. Kalenderzeiträume beginnen um
        Mitternacht in der eingestellten Zeitzone, Wochen am Montag, Monate am
        1.
      </Typography>
      <TextField
        select
        fullWidth
        label="Zeitraum für maximale Vergaben"
        value={period}
        onChange={(e) => onPeriodChange(e.target.value)}
        sx={{ mt: 1 }}
      >
        {Object.entries(awardPeriods).map(([key, text]) => (
          <MenuItem key={key} value={key}>
            {text}
          </MenuItem>
        ))}
      </TextField>
      <Typography variant="caption" color="text.secondary"></Typography>
    </Box>
  );
}

function VipDurationSlider({
  label = "VIP-Dauer (Tage)",
  value,
  onChange,
  helperText,
}) {
  // Indexed stops make short rewards and longer memberships easy to select.
  // Keep imported values as an exact stop; never round them just by opening/saving.
  const [original] = useState(value);
  const choices = [
    ...new Set([
      0.5,
      1,
      2,
      4,
      6,
      12,
      24,
      48,
      72,
      120,
      168,
      336,
      720,
      1440,
      2160,
      4320,
      8760,
      original,
      value,
    ]),
  ]
    .filter((v) => Number.isFinite(v) && v > 0 && v <= 8760)
    .sort((a, b) => a - b);
  const format = (hours) =>
    `${(hours / 24).toLocaleString("de-DE", {
      maximumFractionDigits: 4,
    })} Tage (${hours.toLocaleString("de-DE")} Stunden)`;
  const marks = [24, 168, 720, 8760].map((hours) => ({
    value: choices.indexOf(hours),
    label: `${hours / 24} T.`,
  }));
  return (
    <Box
      sx={{
        minWidth: 0,
        width: "100%",
        flex: "1 1 auto",
        px: 1,
        "& > .MuiTypography-root:first-child": { display: "inline-block" },
        "& > .MuiTypography-root:nth-child(2)": { float: "right" },
      }}
    >
      <Typography variant="body2">{label}</Typography>
      <Typography fontWeight={600} sx={{ mb: 1 }}>
        {value < 24
          ? `${value.toLocaleString("de-DE")} Stunden`
          : `${(value / 24).toLocaleString("de-DE", {
              maximumFractionDigits: 2,
            })} ${value === 24 ? "Tag" : "Tage"}`}
      </Typography>
      <Slider
        aria-label={label}
        value={choices.indexOf(value)}
        min={0}
        max={choices.length - 1}
        step={1}
        marks={marks}
        valueLabelDisplay="auto"
        valueLabelFormat={(index) => format(choices[index])}
        getAriaValueText={(index) => format(choices[index])}
        onChange={(_, index) => onChange(choices[index])}
      />
      <Typography variant="caption" color="text.secondary">
        {helperText ||
          "Wähle die VIP-Dauer. Ein Tag entspricht 24 Stunden; kürzere Belohnungen sind ebenfalls möglich."}
      </Typography>
    </Box>
  );
}

function localTime(value) {
  if (!value) return "";
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "";
  return new Date(date.getTime() - date.getTimezoneOffset() * 60000)
    .toISOString()
    .slice(0, 16);
}

export default function VipRewards() {
  const { permissions } = useAuth();
  const has = (key) =>
    permissions?.is_superuser ||
    permissions?.permissions?.some((p) => p.permission === key);
  const canEdit = has("can_change_seed_vip_config");
  const canInspect = has("can_view_vip_ids");
  const [section, setSection] = useState("rules");
  const [selectedRule, setSelectedRule] = useState("weekly_support");
  const [config, setConfig] = useState(null);
  const [saved, setSaved] = useState(null);
  const [status, setStatus] = useState(null);
  const [journal, setJournal] = useState({ results: [], total: 0 });
  const [offset, setOffset] = useState(0);
  const [filter, setFilter] = useState("");
  const [mode, setMode] = useState("true");
  const [progress, setProgress] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  const [weapons, setWeapons] = useState([]);
  const [weaponError, setWeaponError] = useState("");
  useEffect(() => {
    let mounted = true;
    read("get_vip_rewards_weapons")
      .then((data) => {
        if (mounted) setWeapons(data.weapons.map((w) => w.name));
      })
      .catch(() => {
        if (mounted)
          setWeaponError(
            "Die Waffenliste konnte nicht geladen werden. Vorhandene Auswahlen bleiben erhalten. Bitte lade die Seite erneut."
          );
      });
    return () => {
      mounted = false;
    };
  }, []);
  useEffect(() => {
    let mounted = true;
    read("get_vip_rewards_config")
      .then((c) => {
        if (mounted) {
          setConfig(c);
          setSaved(c);
          setMode(String(c.dry_run));
        }
      })
      .catch((e) => mounted && setError(e.message));
    return () => {
      mounted = false;
    };
  }, []);
  useEffect(() => {
    if (!canInspect) return;
    let mounted = true;
    const refresh = () =>
      Promise.all([
        read("get_vip_rewards_status"),
        read(
          `get_vip_rewards_journal?${new URLSearchParams({
            offset,
            limit: 25,
            preview: mode,
            ...(filter ? { player_id: filter } : {}),
          })}`
        ),
      ])
        .then(([s, j]) => {
          if (mounted) {
            setStatus(s);
            setJournal(j);
          }
        })
        .catch((e) => mounted && setError(e.message));
    refresh();
    const timer = setInterval(refresh, 15000);
    return () => {
      mounted = false;
      clearInterval(timer);
    };
  }, [offset, filter, mode, canInspect]);
  const change = (key, value) => setConfig((c) => ({ ...c, [key]: value }));
  const ruleChange = (key, field, value) =>
    setConfig((c) => ({ ...c, [key]: { ...c[key], [field]: value } }));
  const listChange = (key, index, field, value) =>
    setConfig((c) => ({
      ...c,
      [key]: c[key].map((r, i) => (i === index ? { ...r, [field]: value } : r)),
    }));
  async function save() {
    setBusy(true);
    setError("");
    setNotice("");
    try {
      if (
        config.challenges.some((rule) => rule.enabled && !rule.weapons.length)
      ) {
        throw new Error(
          "Bitte wähle für jede aktive Waffen-Challenge mindestens eine Waffe aus."
        );
      }
      for (const command of [
        "validate_vip_rewards_config",
        "set_vip_rewards_config",
      ]) {
        const response = await execute(command, { config });
        const data = await response.json();
        if (data.failed || data.error || data.result !== true)
          throw new Error(
            typeof data.error === "string"
              ? data.error
              : JSON.stringify(data.error || "Speichern fehlgeschlagen")
          );
      }
      const current = await read("get_vip_rewards_config");
      setConfig(current);
      setSaved(current);
      setNotice(
        "Einstellungen gespeichert. Der Dienst übernimmt sie bei der nächsten Prüfung."
      );
    } catch (e) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  }
  async function acknowledge(row) {
    if (
      !window.confirm(
        "VIP-Ablauf und zwischenzeitliche Änderungen geprüft? Die Bestätigung erlaubt zukünftige Belohnungen, zahlt diesen Eintrag aber nicht erneut aus."
      )
    )
      return;
    try {
      const response = await execute("acknowledge_vip_reward_review", {
        grant_id: row.id,
      });
      const data = await response.json();
      if (data.failed || data.error || data.result !== true)
        throw new Error(data.error || "Eintrag konnte nicht bestätigt werden");
      setJournal((j) => ({
        ...j,
        results: j.results.map((r) =>
          r.id === row.id
            ? {
                ...r,
                status: "reviewed",
                reason: "Manuell geprüft; keine erneute Auszahlung",
              }
            : r
        ),
      }));
    } catch (e) {
      setError(e.message);
    }
  }
  if (!config)
    return (
      <Alert severity={error ? "error" : "info"}>
        {error || "VIP-Belohnungen werden geladen …"}
      </Alert>
    );
  const changed = JSON.stringify(saved) !== JSON.stringify(config);
  const toggle = (label, checked, onChange) => (
    <FormControlLabel
      label={label}
      control={
        <Switch
          checked={checked}
          onChange={(e) => onChange(e.target.checked)}
        />
      }
    />
  );
  const counts = status?.counts || {},
    targets = status?.thresholds || {};
  const statusText = !status
    ? "Status wird geladen"
    : status.status === "active"
    ? "Aktiv"
    : status.status === "disabled"
    ? "Deaktiviert"
    : status.status === "seeding"
    ? `Pausiert: Seeding / Freigabeprüfung - Allies ${counts.allies ?? "?"}/${
        targets.allies ?? "?"
      }, Axis ${counts.axis ?? "?"}/${targets.axis ?? "?"}`
    : "Pausiert: kein bestätigter Serverstatus";
  return (
    <Stack
      spacing={3}
      sx={{
        width: "100%",
        minWidth: 0,
        boxSizing: "border-box",
        maxWidth: 1440,
        mx: "auto",
        p: { xs: 1, md: 3 },
      }}
    >
      {isFakeMode() && (
        <Alert severity="info">
          Lokaler Formulartest mit simulierten Daten. Speichern verändert nur
          diese Vorschau. Es werden keine Spieler angeschrieben und keine
          VIP-Rechte vergeben. Nach dem Neuladen wird der Test zurückgesetzt.
        </Alert>
      )}
      <Box>
        <Typography variant="h4">VIP-Belohnungen</Typography>
        <Typography color="text.secondary">
          Zusätzliche Belohnungen für Spielzeit, Teamhilfe und
          Herausforderungen.
        </Typography>
      </Box>
      {error && (
        <Alert severity="error" onClose={() => setError("")}>
          {error}
        </Alert>
      )}
      {notice && (
        <Alert severity="success" onClose={() => setNotice("")}>
          {notice}
        </Alert>
      )}
      <Stack direction="row" gap={1} alignItems="center" flexWrap="wrap">
        <Chip size="small" label={statusText} />
        <Chip
          size="small"
          color="primary"
          variant="outlined"
          label={config.dry_run ? "Vorschau" : "Livebetrieb"}
        />
      </Stack>
      <Tabs
        value={section}
        onChange={(_, value) => setSection(value)}
        variant="scrollable"
        scrollButtons="auto"
        aria-label="VIP-Bereiche"
      >
        <Tab value="rules" label="Belohnungen" />
        <Tab value="general" label="Grundeinstellungen" />
        {canInspect && <Tab value="journal" label="Vergabejournal" />}
      </Tabs>
      {!canEdit && (
        <Alert severity="info">
          Nur Lesezugriff. Änderungen erfordern die Berechtigung für
          Seed-VIP-Einstellungen.
        </Alert>
      )}
      <Box
        component="fieldset"
        disabled={!canEdit || busy}
        sx={{ border: 0, p: 0, m: 0, minWidth: 0 }}
      >
        <Stack spacing={2}>
          {section === "general" && (
            <Box sx={{ maxWidth: 900 }}>
              <Typography variant="h6" sx={{ mb: 2 }}>
                Betrieb und Grenzen
              </Typography>
              <Typography color="text.secondary" sx={{ mb: 2 }}>
                Diese Einstellungen gelten für alle zusätzlichen
                VIP-Belohnungen.{" "}
                <Link to="/settings/others/seed-vip">
                  Seed-VIP separat einstellen
                </Link>
              </Typography>
              <Stack>
                {toggle(
                  "Neue VIP-Belohnungen aktivieren",
                  config.enabled,
                  (v) => change("enabled", v)
                )}
                {toggle(
                  "Vorschau: keine VIP-Vergabe und keine Spielernachrichten",
                  config.dry_run,
                  (v) => change("dry_run", v)
                )}
                {toggle(
                  "Während des Seedens pausieren",
                  config.pause_during_seeding,
                  (v) => change("pause_during_seeding", v)
                )}
                {toggle(
                  "Spieler nach erfolgreicher Vergabe benachrichtigen",
                  config.notify_player,
                  (v) => change("notify_player", v)
                )}
              </Stack>
              <Typography variant="body2" sx={{ mb: 2 }}>
                Seed-VIP-Zielzahlen müssen fünf Minuten gehalten werden. Prüfung
                alle 30 Sekunden. Vorschau und Livebetrieb haben getrennte
                Fortschritte und Budgets.
              </Typography>
              <Stack direction="row" gap={2} flexWrap="wrap">
                <VipDurationSlider
                  label="Maximale VIP-Tage pro Spieler je 24 Stunden"
                  helperText="Obergrenze für alle Regeln zusammen innerhalb der letzten 24 Stunden. Überschüsse werden nicht später nachgezahlt."
                  value={config.daily_hours}
                  step={0.5}
                  onChange={(v) => change("daily_hours", v)}
                />
                <ThresholdSlider
                  label="Abstand beim selben Gegner (Minuten)"
                  helperText="Weitere Kills desselben Gegners zählen erst nach diesem Abstand erneut für Nahkampf und Challenges."
                  value={config.opponent_cooldown_minutes}
                  onChange={(v) => change("opponent_cooldown_minutes", v)}
                />
                <Autocomplete
                  sx={{ minWidth: 220, flex: 1 }}
                  disableClearable
                  options={[
                    ...new Set([
                      config.timezone,
                      "UTC",
                      ...(Intl.supportedValuesOf
                        ? Intl.supportedValuesOf("timeZone")
                        : [
                            "Europe/Berlin",
                            "Europe/London",
                            "America/New_York",
                          ]),
                    ]),
                  ].sort()}
                  value={config.timezone}
                  onChange={(_, value) => change("timezone", value)}
                  renderInput={(params) => (
                    <TextField
                      {...params}
                      size="small"
                      label="Zeitzone"
                      helperText="Bestimmt Tages-, Wochen- und Monatsgrenzen. Sommerzeit wird automatisch berücksichtigt."
                    />
                  )}
                />
              </Stack>
              <TextField
                fullWidth
                size="small"
                sx={{ mt: 2 }}
                label="Chatbefehl für den Wochenfortschritt"
                value={config.status_command}
                helperText="Zum Beispiel !rewards oder !teamvip. Leer lassen zum Abschalten. Antwort nur privat, höchstens alle 30 Sekunden pro Spieler. Im Probelauf keine Nachrichten."
                onChange={(e) => change("status_command", e.target.value)}
              />
              <ExcludedPlayers
                value={config.excluded_player_ids}
                onChange={(ids) => change("excluded_player_ids", ids)}
              />
            </Box>
          )}
          {section === "rules" && (
            <Box
              sx={{
                display: "grid",
                gridTemplateColumns: {
                  xs: "minmax(0, 1fr)",
                  md: "280px minmax(0, 1fr)",
                },
                gap: { xs: 3, md: 4 },
                minHeight: { md: 600 },
              }}
            >
              <Box
                component="nav"
                aria-label="Belohnungsregeln"
                sx={{
                  borderRight: { md: 1 },
                  borderColor: { md: "divider" },
                  pr: { md: 2 },
                }}
              >
                <Typography variant="h6">Regel auswählen</Typography>
                <Typography
                  variant="body2"
                  color="text.secondary"
                  sx={{ mt: 0.5, mb: 2 }}
                >
                  Belohnungen gezielt konfigurieren.
                </Typography>
                <List
                  disablePadding
                  sx={{
                    display: { xs: "grid", md: "block" },
                    gridTemplateColumns: { xs: "1fr", sm: "1fr 1fr" },
                  }}
                >
                  {Object.entries({
                    ...labels,
                    events: "Events",
                    challenges: "Waffen-Challenges",
                  }).map(([key, title]) => {
                    const active = Array.isArray(config[key])
                      ? config[key].some((r) => r.enabled)
                      : config[key].enabled;
                    return (
                      <ListItemButton
                        key={key}
                        selected={selectedRule === key}
                        onClick={() => setSelectedRule(key)}
                        sx={{ borderRadius: 1, mb: 0.5, py: 1.25 }}
                      >
                        <ListItemText
                          primary={title}
                          secondary={active ? "Aktiv" : "Aus"}
                          primaryTypographyProps={{
                            fontWeight: selectedRule === key ? 600 : 400,
                          }}
                          secondaryTypographyProps={{
                            color: active ? "primary.main" : "text.secondary",
                          }}
                        />
                      </ListItemButton>
                    );
                  })}
                </List>
              </Box>
              <Box
                sx={{
                  minWidth: 0,
                  "& > .MuiCard-root": {
                    boxShadow: "none",
                    background: "transparent",
                    border: 0,
                  },
                  "& > .MuiCard-root > .MuiCardContent-root": {
                    p: 0,
                    maxWidth: 900,
                  },
                }}
              >
                {Object.entries(labels)
                  .filter(([key]) => key === selectedRule)
                  .map(([key, title]) => (
                    <Card key={key}>
                      <CardContent>
                        <Typography variant="h5" sx={{ mb: 1 }}>
                          {title}
                        </Typography>
                        <Typography variant="body2" color="text.secondary">
                          {key === "weekly_support"
                            ? "Unterstützungspunkte über mehrere Runden sammeln. Ein Wochenziel für hilfreiches Teamplay."
                            : notes[key]}
                        </Typography>
                        {toggle(
                          `${title} aktivieren`,
                          config[key].enabled,
                          (v) => ruleChange(key, "enabled", v)
                        )}
                        {!config[key].enabled && (
                          <Typography color="text.secondary" sx={{ mt: 3 }}>
                            Aktiviere diese Regel, um Voraussetzungen und
                            Belohnung einzustellen. Gespeicherte Werte bleiben
                            beim Ausschalten erhalten.
                          </Typography>
                        )}
                        <Collapse in={config[key].enabled} unmountOnExit>
                          <Stack gap={3} sx={{ mt: 3 }}>
                            <Typography variant="h6">
                              Voraussetzungen
                            </Typography>
                            {key === "melee" && (
                              <Typography color="text.secondary">
                                Ein gültiger Nahkampfkill gegen einen Gegner.
                                Der eingestellte Abstand beim selben Gegner gilt
                                zusätzlich.
                              </Typography>
                            )}
                            {key === "milestones" && (
                              <Typography color="text.secondary">
                                Erreichte Spielstunden und die zugehörige
                                Belohnung legst du unten je Stufe fest.
                              </Typography>
                            )}
                            {["round", "weekly", "balance"].includes(key) && (
                              <ThresholdSlider
                                label="Mindestspielzeit (Minuten)"
                                max={240}
                                value={config[key].minutes}
                                onChange={(v) => ruleChange(key, "minutes", v)}
                              />
                            )}
                            {key === "round" && (
                              <ThresholdSlider
                                label="Mindestanteil der Runde (%)"
                                value={Math.round(config.round.fraction * 100)}
                                max={100}
                                onChange={(v) =>
                                  ruleChange(key, "fraction", v / 100)
                                }
                              />
                            )}
                            {key === "weekly_support" && (
                              <ThresholdSlider
                                label="Unterstützungspunkte pro Woche"
                                value={config.weekly_support.points}
                                max={100000000}
                                helperText="Beispielwert: 5.000 Punkte. Passe das Ziel an die Spielweise auf deinem Server an."
                                onChange={(v) => ruleChange(key, "points", v)}
                              />
                            )}
                            {key === "weekly" && (
                              <ThresholdSlider
                                label="Unterschiedliche Tage"
                                value={config.weekly.days}
                                max={7}
                                onChange={(v) => ruleChange(key, "days", v)}
                              />
                            )}
                            {key === "balance" && (
                              <>
                                <ThresholdSlider
                                  label="Mindest-Teamdifferenz"
                                  max={50}
                                  value={config.balance.difference}
                                  min={2}
                                  onChange={(v) =>
                                    ruleChange(key, "difference", v)
                                  }
                                />
                                <ThresholdSlider
                                  label="Anmeldung gültig (Minuten)"
                                  value={config.balance.signup_minutes}
                                  max={30}
                                  onChange={(v) =>
                                    ruleChange(key, "signup_minutes", v)
                                  }
                                />
                              </>
                            )}
                            <Typography
                              variant="h6"
                              sx={{
                                pt: 2,
                                borderTop: 1,
                                borderColor: "divider",
                              }}
                            >
                              Belohnung
                            </Typography>
                            {key !== "milestones" && (
                              <VipDurationSlider
                                label="VIP-Dauer (Tage)"
                                value={config[key].hours}
                                step={0.5}
                                onChange={(v) => ruleChange(key, "hours", v)}
                              />
                            )}
                            {["melee", "round", "balance"].includes(key) && (
                              <AwardLimitSlider
                                value={config[key].limit}
                                period={config[key].limit_period}
                                onPeriodChange={(v) =>
                                  ruleChange(key, "limit_period", v)
                                }
                                onChange={(v) => ruleChange(key, "limit", v)}
                              />
                            )}
                          </Stack>
                          {key === "weekly_support" && (
                            <Alert severity="info" sx={{ mt: 3 }}>
                              Wer{" "}
                              {config.weekly_support.points.toLocaleString(
                                "de-DE"
                              )}{" "}
                              Unterstützungspunkte erreicht, erhält{" "}
                              {config.weekly_support.hours < 24
                                ? `${config.weekly_support.hours} Stunden`
                                : `${
                                    config.weekly_support.hours / 24
                                  } Tage`}{" "}
                              VIP. Einmal pro Woche, Montag bis Sonntag ·{" "}
                              {config.timezone}.
                            </Alert>
                          )}
                          {key === "milestones" && (
                            <Stack gap={2}>
                              {config.milestones.milestones.map((m, i) => (
                                <Stack
                                  key={i}
                                  direction="row"
                                  gap={2}
                                  flexWrap="wrap"
                                >
                                  <ThresholdSlider
                                    label="Spielstunden"
                                    value={m.play_hours}
                                    onChange={(v) =>
                                      ruleChange(
                                        key,
                                        "milestones",
                                        config.milestones.milestones.map(
                                          (x, j) =>
                                            j === i
                                              ? { ...x, play_hours: v }
                                              : x
                                        )
                                      )
                                    }
                                  />
                                  <VipDurationSlider
                                    label="VIP-Dauer (Tage)"
                                    value={m.hours}
                                    step={0.5}
                                    onChange={(v) =>
                                      ruleChange(
                                        key,
                                        "milestones",
                                        config.milestones.milestones.map(
                                          (x, j) =>
                                            j === i ? { ...x, hours: v } : x
                                        )
                                      )
                                    }
                                  />
                                  <Button
                                    onClick={() =>
                                      ruleChange(
                                        key,
                                        "milestones",
                                        config.milestones.milestones.filter(
                                          (_, j) => j !== i
                                        )
                                      )
                                    }
                                  >
                                    Entfernen
                                  </Button>
                                </Stack>
                              ))}
                              <Button
                                onClick={() =>
                                  ruleChange(key, "milestones", [
                                    ...config.milestones.milestones,
                                    { play_hours: 200, hours: 12 },
                                  ])
                                }
                              >
                                Meilenstein hinzufügen
                              </Button>
                            </Stack>
                          )}
                        </Collapse>
                      </CardContent>
                    </Card>
                  ))}
                {["events", "challenges"]
                  .filter((key) => key === selectedRule)
                  .map((key) => (
                    <Card key={key}>
                      <CardContent>
                        <Typography variant="h6">
                          {key === "events" ? "Events" : "Waffen-Challenges"}
                        </Typography>
                        <Typography color="text.secondary">
                          {key === "events"
                            ? "Belohne die Teilnahme in einem festgelegten Zeitraum, zum Beispiel an einem Community-Abend."
                            : "Wähle Waffen aus der Liste und lege fest, wie viele Gegnerkills damit nötig sind. Teamkills zählen nicht."}
                        </Typography>
                        <Stack gap={3} sx={{ mt: 2 }}>
                          {config[key].map((r, i) => (
                            <Stack
                              gap={2}
                              key={r.id}
                              sx={{
                                borderBottom: 1,
                                borderColor: "divider",
                                pb: 2,
                              }}
                            >
                              <Stack
                                direction="row"
                                flexWrap="wrap"
                                gap={2}
                                alignItems="center"
                              >
                                <TextField
                                  size="small"
                                  label="Name"
                                  value={r.name}
                                  onChange={(e) =>
                                    listChange(key, i, "name", e.target.value)
                                  }
                                />
                                {toggle("Aktiviert", r.enabled, (v) =>
                                  listChange(key, i, "enabled", v)
                                )}
                                <Button
                                  color="error"
                                  onClick={() =>
                                    change(
                                      key,
                                      config[key].filter((_, j) => j !== i)
                                    )
                                  }
                                >
                                  Entfernen
                                </Button>
                              </Stack>
                              <Collapse in={r.enabled} unmountOnExit>
                                <Stack gap={2}>
                                  <VipDurationSlider
                                    label="VIP-Dauer (Tage)"
                                    value={r.hours}
                                    step={0.5}
                                    onChange={(v) =>
                                      listChange(key, i, "hours", v)
                                    }
                                  />
                                  {key === "events" ? (
                                    <ThresholdSlider
                                      label="Mindestspielzeit (Minuten)"
                                      max={240}
                                      value={r.minutes}
                                      onChange={(v) =>
                                        listChange(key, i, "minutes", v)
                                      }
                                    />
                                  ) : (
                                    <>
                                      {weaponError && (
                                        <Alert severity="warning">
                                          {weaponError}
                                        </Alert>
                                      )}
                                      <Autocomplete
                                        multiple
                                        options={[
                                          ...new Set([
                                            ...weapons,
                                            ...r.weapons,
                                          ]),
                                        ]}
                                        value={r.weapons}
                                        onChange={(_, value) =>
                                          listChange(key, i, "weapons", value)
                                        }
                                        disableCloseOnSelect
                                        noOptionsText="Keine passende Waffe gefunden"
                                        renderInput={(params) => (
                                          <TextField
                                            {...params}
                                            label="Waffen auswählen"
                                            helperText="Suchen und mehrere Waffen auswählen. Kills mit diesen Waffen werden gemeinsam gezählt."
                                          />
                                        )}
                                      />
                                      <Stack
                                        direction="row"
                                        gap={2}
                                        flexWrap="wrap"
                                      >
                                        <ThresholdSlider
                                          label="Gegnerkills"
                                          value={r.kills}
                                          onChange={(v) =>
                                            listChange(key, i, "kills", v)
                                          }
                                        />
                                        <TextField
                                          size="small"
                                          select
                                          label="Zeitraum"
                                          value={r.period}
                                          onChange={(e) =>
                                            listChange(
                                              key,
                                              i,
                                              "period",
                                              e.target.value
                                            )
                                          }
                                          sx={{ minWidth: 180 }}
                                        >
                                          {[
                                            ["day", "Täglich"],
                                            ["week", "Wöchentlich"],
                                            ["fixed", "Fester Zeitraum"],
                                          ].map(([v, l]) => (
                                            <MenuItem key={v} value={v}>
                                              {l}
                                            </MenuItem>
                                          ))}
                                        </TextField>
                                      </Stack>
                                    </>
                                  )}
                                  {(key === "events" ||
                                    r.period === "fixed") && (
                                    <Stack
                                      direction="row"
                                      gap={2}
                                      flexWrap="wrap"
                                    >
                                      {["start", "end"].map((field) => (
                                        <TextField
                                          key={field}
                                          size="small"
                                          type="datetime-local"
                                          label={`${
                                            field === "start"
                                              ? "Beginn"
                                              : "Ende"
                                          } (${
                                            Intl.DateTimeFormat().resolvedOptions()
                                              .timeZone
                                          })`}
                                          InputLabelProps={{ shrink: true }}
                                          value={localTime(r[field])}
                                          onChange={(e) =>
                                            listChange(
                                              key,
                                              i,
                                              field,
                                              e.target.value
                                                ? new Date(
                                                    e.target.value
                                                  ).toISOString()
                                                : ""
                                            )
                                          }
                                          sx={{ flex: 1, minWidth: 250 }}
                                        />
                                      ))}
                                    </Stack>
                                  )}
                                </Stack>
                              </Collapse>
                            </Stack>
                          ))}
                        </Stack>
                        <Button
                          sx={{ mt: 2 }}
                          onClick={() =>
                            change(key, [
                              ...config[key],
                              key === "events"
                                ? {
                                    id: crypto.randomUUID(),
                                    name: "Neues Event",
                                    enabled: false,
                                    hours: 4,
                                    limit: 1,
                                    minutes: 60,
                                    start: new Date().toISOString(),
                                    end: new Date(
                                      Date.now() + 86400000
                                    ).toISOString(),
                                  }
                                : {
                                    id: crypto.randomUUID(),
                                    name: "Neue Challenge",
                                    enabled: false,
                                    hours: 2,
                                    limit: 1,
                                    weapons: [],
                                    kills: 10,
                                    period: "day",
                                    start: null,
                                    end: null,
                                  },
                            ])
                          }
                        >
                          {key === "events"
                            ? "Event hinzufügen"
                            : "Challenge hinzufügen"}
                        </Button>
                      </CardContent>
                    </Card>
                  ))}
              </Box>
            </Box>
          )}
          <Stack
            direction="row"
            gap={2}
            flexWrap="wrap"
            alignItems="center"
            sx={{
              position: "sticky",
              bottom: 0,
              zIndex: 5,
              bgcolor: "background.paper",
              borderTop: 1,
              borderColor: "divider",
              p: 2,
            }}
          >
            <Typography variant="body2" color="text.secondary" sx={{ flex: 1 }}>
              {changed
                ? "Ungespeicherte Änderungen"
                : "Alle Änderungen gespeichert"}
            </Typography>
            <Button
              variant="contained"
              sx={{
                bgcolor: "primary.main",
                color: "primary.contrastText",
                "&:hover": { bgcolor: "primary.dark" },
              }}
              disabled={!changed || busy}
              onClick={save}
            >
              {busy ? "Speichert …" : "Einstellungen speichern"}
            </Button>
            <Button
              disabled={!changed || busy}
              onClick={() => setConfig(saved)}
            >
              Änderungen verwerfen
            </Button>
          </Stack>
        </Stack>
      </Box>
      {canInspect && section === "journal" && (
        <Card>
          <CardContent>
            <Typography variant="h6">
              Vergabejournal und Spielerfortschritt
            </Typography>
            <Stack direction="row" gap={2} flexWrap="wrap" sx={{ my: 2 }}>
              <TextField
                size="small"
                label="Spieler-ID filtern"
                value={filter}
                onChange={(e) => {
                  setFilter(e.target.value.trim());
                  setOffset(0);
                  setProgress(null);
                }}
              />
              <TextField
                size="small"
                select
                label="Journal"
                value={mode}
                onChange={(e) => {
                  setMode(e.target.value);
                  setOffset(0);
                }}
              >
                <MenuItem value="true">Vorschau</MenuItem>
                <MenuItem value="false">Live</MenuItem>
              </TextField>
              <Button
                disabled={!filter}
                onClick={() =>
                  read(
                    `get_vip_rewards_progress?player_id=${encodeURIComponent(
                      filter
                    )}`
                  )
                    .then(setProgress)
                    .catch((e) => setError(e.message))
                }
              >
                Aktuellen Fortschritt anzeigen
              </Button>
            </Stack>
            {progress && (
              <Alert severity="info">
                Aktueller Betriebsmodus: {status?.preview ? "Vorschau" : "Live"}
                . Spielzeit-Meilensteine:{" "}
                {((progress.total || 0) / 3600).toFixed(2)} h; Rundentreue:{" "}
                {Math.floor((progress.round || 0) / 60)} min; erfasste
                Spieltage: {Object.keys(progress.days || {}).length}.
                {progress.weekly_support && (
                  <>
                    {" "}
                    Wochenziel Unterstützung (Woche ab{" "}
                    {progress.weekly_support.week}):{" "}
                    {progress.weekly_support.points} /{" "}
                    {config.weekly_support.points} Punkte.
                  </>
                )}
              </Alert>
            )}
            <Box
              sx={{
                overflowX: "auto",
                border: 1,
                borderColor: "divider",
                borderRadius: 2,
                mt: 2,
              }}
            >
              <Table
                size="small"
                aria-label="VIP-Vergabejournal"
                sx={{
                  minWidth: 760,
                  "& th": {
                    bgcolor: "action.hover",
                    py: 1.5,
                    fontWeight: 600,
                    whiteSpace: "nowrap",
                  },
                  "& td": { py: 2, verticalAlign: "top" },
                  "& tbody tr:last-child td": { borderBottom: 0 },
                }}
              >
                <TableHead>
                  <TableRow>
                    {[
                      "Zeit",
                      "Spieler",
                      "Regel",
                      "VIP-Gutschrift",
                      "Ergebnis",
                    ].map((h) => (
                      <TableCell key={h}>{h}</TableCell>
                    ))}
                  </TableRow>
                </TableHead>
                <TableBody>
                  {journal.results.map((r) => (
                    <TableRow key={r.id} hover>
                      <TableCell>
                        <Typography
                          variant="body2"
                          sx={{ whiteSpace: "nowrap" }}
                        >
                          {new Date(r.occurred * 1000).toLocaleDateString()}
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          {new Date(r.occurred * 1000).toLocaleTimeString()}
                        </Typography>
                      </TableCell>
                      <TableCell sx={{ maxWidth: 230 }}>
                        <Typography
                          component={Link}
                          to={`/records/players/${encodeURIComponent(
                            r.player_id
                          )}`}
                          variant="body2"
                          sx={{
                            fontFamily: "monospace",
                            overflowWrap: "anywhere",
                            color: "primary.main",
                            textDecoration: "none",
                            "&:hover": { textDecoration: "underline" },
                          }}
                        >
                          {r.player_id}
                        </Typography>
                      </TableCell>
                      <TableCell>{labels[r.rule] || r.rule}</TableCell>
                      <TableCell>
                        <Typography
                          variant="body2"
                          fontWeight={600}
                          sx={{ fontVariantNumeric: "tabular-nums" }}
                        >
                          {(r.credited_seconds / 3600).toLocaleString(
                            undefined,
                            { maximumFractionDigits: 2 }
                          )}{" "}
                          h
                        </Typography>
                        <Typography variant="caption" color="text.secondary">
                          von{" "}
                          {(r.requested_seconds / 3600).toLocaleString(
                            undefined,
                            { maximumFractionDigits: 2 }
                          )}{" "}
                          h beantragt
                        </Typography>
                        {["prepared", "review"].includes(r.status) && (
                          <Typography variant="caption" display="block">
                            Budget reserviert; Gutschrift unbestätigt
                          </Typography>
                        )}
                      </TableCell>
                      <TableCell>
                        <Chip
                          size="small"
                          variant="outlined"
                          label={results[r.status] || r.status}
                          color={
                            r.status === "review"
                              ? "warning"
                              : r.status === "awarded"
                              ? "success"
                              : r.status === "preview"
                              ? "info"
                              : "default"
                          }
                          sx={{ mb: 0.5 }}
                        />
                        <Typography
                          variant="caption"
                          display="block"
                          color="text.secondary"
                        >
                          {reasons[r.reason] || r.reason}
                        </Typography>
                        {r.status === "review" && (
                          <Typography variant="caption" display="block">
                            Zielablauf: {r.target || "unbekannt"}
                          </Typography>
                        )}
                        {r.status === "review" && has("can_add_vip") && (
                          <Button size="small" onClick={() => acknowledge(r)}>
                            Als geprüft markieren
                          </Button>
                        )}
                      </TableCell>
                    </TableRow>
                  ))}
                  {!journal.results.length && (
                    <TableRow>
                      <TableCell
                        colSpan={5}
                        sx={{
                          textAlign: "center",
                          color: "text.secondary",
                          height: 100,
                        }}
                      >
                        Noch keine Vergaben für diese Auswahl.
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </Box>
            <Stack direction="row" alignItems="center" gap={2} sx={{ mt: 2 }}>
              <Button
                disabled={!offset}
                onClick={() => setOffset(Math.max(0, offset - 25))}
              >
                Zurück
              </Button>
              <Typography variant="body2" color="text.secondary">
                {journal.total
                  ? `${offset + 1}–${Math.min(
                      offset + 25,
                      journal.total
                    )} von ${journal.total}`
                  : "0"}{" "}
                Einträge
              </Typography>
              <Button
                disabled={offset + 25 >= journal.total}
                onClick={() => setOffset(offset + 25)}
              >
                Weiter
              </Button>
            </Stack>
          </CardContent>
        </Card>
      )}
    </Stack>
  );
}
