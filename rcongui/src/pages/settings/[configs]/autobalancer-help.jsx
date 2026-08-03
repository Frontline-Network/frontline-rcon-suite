import { Alert, Box, Chip, Divider, Stack, Typography } from "@mui/material";

const MODE_INFO = {
  disabled: {
    label: "Ausgeschaltet",
    severity: "warning",
    text: "Der Dienst plant nichts, sendet keine Nachrichten und führt keine Wechsel aus.",
  },
  shadow: {
    label: "Shadow – nur beobachten",
    severity: "info",
    text: "Sicherer Testbetrieb: Vorschläge werden protokolliert, aber Spieler erhalten keine Nachricht und niemand wird verschoben.",
  },
  manual: {
    label: "Manuell freigeben",
    severity: "warning",
    text: "Nach der Freiwilligenphase entsteht ein Vorschlag. Erst eine Admin-Freigabe in der Teamansicht merkt den Spieler für den Wechsel nach seinem Tod vor.",
  },
  auto: {
    label: "Automatisch",
    severity: "warning",
    text: "Nach der Freiwilligenphase wird automatisch ein Kandidat vorgemerkt. Auch hier erfolgt der Wechsel ausschließlich nach seinem nächsten Tod.",
  },
};

const AutobalancerHelp = ({ config = {} }) => {
  const mode = MODE_INFO[config.mode] || MODE_INFO.disabled;
  const targetDifference = config.target_difference ?? 2;
  const stableSeconds = config.stable_difference_seconds ?? 45;
  const minimumPlayers = config.minimum_players ?? 40;
  const volunteerSeconds = config.volunteer_phase_seconds ?? 30;
  const startMinutes = config.map_start_grace_minutes ?? 5;
  const endMinutes = config.map_end_guard_minutes ?? 10;
  const cooldownMaps = config.cooldown_maps ?? 3;
  const maxSwitches = config.max_switches_per_incident ?? 3;

  return (
    <Stack spacing={2} sx={{ mt: 2, mb: 3 }}>
      <Alert severity={mode.severity}>
        <strong>Aktiver Modus: {mode.label}.</strong> {mode.text}
      </Alert>

      <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Stack direction="row" spacing={1} alignItems="center" sx={{ mb: 1 }}>
          <Typography variant="h6">Wann greift der Balancer ein?</Typography>
          <Chip size="small" label={`mehr als ${targetDifference} Spieler Unterschied`} />
        </Stack>
        <Typography variant="body2" paragraph>
          Ein Vorfall beginnt erst, wenn die erlaubte Teamdifferenz länger als{" "}
          <strong>{stableSeconds} Sekunden</strong> überschritten ist und mindestens{" "}
          <strong>{minimumPlayers} Spieler</strong> verbunden sind. Die Richtung des
          Ungleichgewichts muss dabei gleich bleiben.
        </Typography>
        <Typography variant="body2">
          Zusätzlich passiert in den ersten <strong>{startMinutes} Minuten</strong> und
          den letzten <strong>{endMinutes} Minuten</strong> einer Runde nichts. Eine
          Differenz von genau {targetDifference} ist noch erlaubt. Ein Teamwechsel
          verringert die Differenz um zwei.
        </Typography>
      </Box>

      <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Ablauf in manual und auto
        </Typography>
        <Stack spacing={0.75} divider={<Divider flexItem />}>
          <Typography variant="body2">
            <strong>1. Freiwillige:</strong> Geeignete Spieler im größeren Team haben{" "}
            {volunteerSeconds} Sekunden Zeit für <code>{config.volunteer_command || "!balance"}</code>.
          </Typography>
          <Typography variant="body2">
            <strong>2. Auswahl:</strong> Commander sind ausgeschlossen. Neu verbundene
            Spieler, etablierte Squads, Squad Leader, Armor und Recon werden gestaffelt
            geschützt.
          </Typography>
          <Typography variant="body2">
            <strong>3. Wechsel:</strong> Es wird immer nur ein Spieler vorgemerkt. Der
            Wechsel erfolgt nach seinem nächsten Tod, danach werden alle Daten neu
            berechnet.
          </Typography>
        </Stack>
      </Box>

      <Alert severity="success">
        <strong>Schutznetz:</strong> Ein verschobener Spieler ist {cooldownMaps} Karten
        geschützt. Pro Vorfall sind höchstens {maxSwitches} Wechsel erlaubt. Bei
        ausgeglichenen Spielerzahlen gibt es keine reinen Stärkewechsel.
      </Alert>

      <Typography variant="caption" color="text.secondary">
        Änderungen gelten nur für diesen CRCON-Server. Mit „Einstellungen speichern“
        übernehmen. Die deutschen Standardnachrichten müssen für den Shadow-Pilot nicht
        geändert werden; sie werden erst in manual oder auto versendet. Der native
        HLL-Autobalancer wird durch diese Seite nicht verändert und sollte aktiviert bleiben.
      </Typography>
    </Stack>
  );
};

export default AutobalancerHelp;
