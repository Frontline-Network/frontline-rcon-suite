import { Alert, Box, Chip, Stack, Typography } from "@mui/material";
import BalanceOutlinedIcon from "@mui/icons-material/BalanceOutlined";
import GroupsOutlinedIcon from "@mui/icons-material/GroupsOutlined";
import ShieldOutlinedIcon from "@mui/icons-material/ShieldOutlined";

const MODE_INFO = {
  disabled: {
    label: "Aus",
    severity: "info",
    text: "Der Dienst beobachtet und plant keine Teamwechsel.",
  },
  shadow: {
    label: "Beobachten",
    severity: "info",
    text: "Vorschläge werden nur berechnet und protokolliert. Spieler merken nichts davon.",
  },
  manual: {
    label: "Manuell",
    severity: "warning",
    text: "Der Dienst bereitet Vorschläge vor; ein Administrator gibt jeden Eingriff frei.",
  },
  auto: {
    label: "Automatisch",
    severity: "warning",
    text: "Zulässige Einzelwechsel werden nach der Freiwilligenphase automatisch vorgemerkt.",
  },
};

const SummaryItem = ({ icon, label, value, detail }) => (
  <Box sx={{ p: 1.5, minWidth: 0 }}>
    <Stack direction="row" spacing={0.75} alignItems="center" sx={{ mb: 0.5 }}>
      {icon}
      <Typography variant="overline" color="text.secondary">
        {label}
      </Typography>
    </Stack>
    <Typography variant="subtitle1" sx={{ fontWeight: 800 }}>
      {value}
    </Typography>
    <Typography variant="caption" color="text.secondary">
      {detail}
    </Typography>
  </Box>
);

const AutobalancerHelp = ({ config = {} }) => {
  const mode = MODE_INFO[config.mode] || MODE_INFO.disabled;
  const targetDifference = config.target_difference ?? 2;
  const stableSeconds = config.stable_difference_seconds ?? 45;
  const squadSwitches = config.coordinated_squad_switches_enabled === true;
  const individualFallback = config.allow_individual_squad_fallback !== false;

  return (
    <Stack spacing={1.5} sx={{ mt: 2, mb: 2 }}>
      <Alert severity={mode.severity} variant="outlined">
        <strong>Betriebsmodus: {mode.label}.</strong> {mode.text}
      </Alert>

      <Box
        sx={{
          display: "grid",
          gridTemplateColumns: { xs: "1fr", md: "repeat(3, 1fr)" },
          border: "1px solid",
          borderColor: "divider",
          bgcolor: "background.paper",
          "& > div + div": {
            borderLeft: { md: "1px solid" },
            borderTop: { xs: "1px solid", md: 0 },
            borderColor: "divider",
          },
        }}
      >
        <SummaryItem
          icon={<BalanceOutlinedIcon fontSize="small" color="primary" />}
          label="Eingriff"
          value={`Mehr als ${targetDifference} Spieler`}
          detail={`Das Ungleichgewicht muss mindestens ${stableSeconds} Sekunden bestehen.`}
        />
        <SummaryItem
          icon={<GroupsOutlinedIcon fontSize="small" color="primary" />}
          label="Squads"
          value={squadSwitches ? "Gemeinsam wechselbar" : "Nur Vorschlag"}
          detail={
            squadSwitches
              ? "Moderatoren können vollständige Infanterie-Squads nach erneuter Live-Prüfung wechseln."
              : "Squad-Vorschläge bleiben sichtbar, die gemeinsame Ausführung ist aber gesperrt."
          }
        />
        <SummaryItem
          icon={<ShieldOutlinedIcon fontSize="small" color="primary" />}
          label="Fallback"
          value={
            individualFallback
              ? "Einzelspieler erlaubt"
              : "Squads bleiben zusammen"
          }
          detail="Führungs- und Spezialtrupps bleiben in beiden Fällen geschützt."
        />
      </Box>

      <Stack direction="row" spacing={0.75} flexWrap="wrap" useFlexGap>
        <Chip label="Live-Daten" size="small" color="info" />
        <Chip label="Aktueller Server" size="small" variant="outlined" />
        <Chip
          label="Squad-Mitglieder werden vorab informiert"
          size="small"
          variant="outlined"
        />
      </Stack>

      {squadSwitches && (
        <Alert severity="warning" variant="outlined">
          Hell Let Loose verschiebt Spieler, nicht die Squad-Struktur. Nach
          einem Gruppenwechsel müssen die Mitglieder den Squad im Zielteam neu
          bilden. Deshalb prüft die Aktion alle Mitglieder erneut, informiert
          sie zuerst und verlangt eine zweite Bestätigung.
        </Alert>
      )}
    </Stack>
  );
};

export default AutobalancerHelp;
