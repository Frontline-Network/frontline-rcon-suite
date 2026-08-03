import ExpandMoreIcon from "@mui/icons-material/ExpandMore";
import {
  Accordion,
  AccordionDetails,
  AccordionSummary,
  Alert,
  Box,
  Chip,
  Divider,
  Stack,
  Typography,
} from "@mui/material";

const MODE_INFO = {
  disabled: {
    label: "Ausgeschaltet",
    severity: "warning",
    text: "Der Dienst plant nichts, sendet keine Nachrichten und führt keine Wechsel aus.",
  },
  shadow: {
    label: "Shadow – nur beobachten",
    severity: "info",
    text: "Sicherer Testbetrieb: Der vollständige Algorithmus berechnet Vorschläge und schreibt sie ins Audit. Spieler erhalten keine Nachricht und niemand wird verschoben.",
  },
  manual: {
    label: "Manuell freigeben",
    severity: "warning",
    text: "Der Dienst sucht Freiwillige und erstellt danach einen Vorschlag. Erst eine Admin-Freigabe in der Teamansicht merkt den Spieler für den Wechsel nach seinem Tod vor.",
  },
  auto: {
    label: "Automatisch",
    severity: "warning",
    text: "Der Dienst sucht Freiwillige und wählt danach selbst. Auch im Automatikmodus erfolgt der Wechsel ausschließlich nach dem nächsten Tod des ausgewählten Spielers.",
  },
};

const MODE_CARDS = [
  {
    mode: "disabled",
    title: "disabled – aus",
    text: "Kein Polling, keine Planung, keine Nachrichten und keine Teamwechsel. Das ist der sichere Upstream-Standard.",
  },
  {
    mode: "shadow",
    title: "shadow – testen",
    text: "Plant mit echten Daten und speichert Entscheidungen. Es gibt keinerlei sichtbare Auswirkung für Spieler. Genau dafür ist der FLN-Pilot gedacht.",
  },
  {
    mode: "manual",
    title: "manual – Admin entscheidet",
    text: "Freiwilligenphase und Kandidatenauswahl laufen automatisch. Ein Admin muss den Vorschlag freigeben; erst danach wartet der Dienst auf den Tod.",
  },
  {
    mode: "auto",
    title: "auto – selbstständig",
    text: "Nach der Freiwilligenphase wird der beste zulässige Kandidat automatisch vorgemerkt. Es gibt niemals einen erzwungenen Wechsel eines lebenden Spielers.",
  },
];

const FIELD_GROUPS = [
  {
    title: "1. Wann startet ein Balance-Vorfall?",
    intro:
      "Diese Werte entscheiden, ob ein kurzzeitiger Spielerunterschied ignoriert oder als echter Balance-Vorfall behandelt wird.",
    fields: [
      {
        key: "target_difference",
        label: "Erlaubte Teamdifferenz",
        unit: "Spieler",
        recommended: "2",
        description:
          "Solange die absolute Differenz höchstens diesen Wert hat, passiert nichts. Bei 2 sind 50:48 und 49:47 erlaubt; 50:47 überschreitet den Grenzwert.",
        lower:
          "Strenger und mehr Eingriffe. Bei 0 würde bereits 50:49 einen Vorfall auslösen.",
        higher:
          "Mehr Toleranz, aber ungleichere Runden bleiben länger bestehen.",
      },
      {
        key: "minimum_players",
        label: "Mindestanzahl Spieler",
        unit: "Spieler insgesamt",
        recommended: "40",
        description:
          "Allies und Axis werden zusammengezählt. Unterhalb dieses Werts startet kein Vorfall, damit der Balancer das Seeding nicht stört.",
        lower: "Der Balancer kann schon während des Serveraufbaus eingreifen.",
        higher:
          "Mehr Schutz fürs Seeding, aber spätere Aktivierung bei mittelvollen Servern.",
      },
      {
        key: "stable_difference_seconds",
        label: "Ungleichgewicht muss bestehen",
        unit: "Sekunden",
        recommended: "45 Sekunden",
        description:
          "Der Grenzwert muss ununterbrochen in derselben Richtung überschritten sein. Wird die Balance behoben oder wechselt das größere Team, beginnt die Zeit von vorn.",
        lower:
          "Schnellere Reaktion, aber mehr Fehlalarme durch Beitritte und Disconnects.",
        higher:
          "Ruhigere Entscheidungen, dafür bleibt ein echtes Ungleichgewicht länger bestehen.",
      },
      {
        key: "poll_interval_seconds",
        label: "Prüfintervall",
        unit: "Sekunden",
        recommended: "5 Sekunden",
        description:
          "Technischer Abstand zwischen zwei vollständigen Prüfungen. Das ist nicht die Wartezeit bis zum Wechsel; die stabile Differenz gilt zusätzlich.",
        lower:
          "Aktuellere Anzeige, aber mehr RCON-, Redis- und Datenbankabfragen.",
        higher:
          "Weniger Last, aber langsamere Reaktion auf Änderungen und Todesereignisse.",
      },
    ],
  },
  {
    title: "2. Schutzzeiten für Runde und Spieler",
    intro:
      "Diese Sperren sind harte Sicherheitsbedingungen. Ein freiwilliger Spieler kann sie nicht umgehen.",
    fields: [
      {
        key: "map_start_grace_minutes",
        label: "Schutz nach Kartenstart",
        unit: "Minuten",
        recommended: "5 Minuten",
        description:
          "Nach dem Kartenwechsel dürfen sich Spieler zunächst selbst verteilen und ihre Squads aufbauen. In dieser Zeit wird niemand ausgewählt.",
        lower:
          "Frühere Eingriffe, während Teams und Squads noch nicht stabil sind.",
        higher:
          "Mehr Aufbauzeit, aber längere mögliche Unbalance zu Rundenbeginn.",
      },
      {
        key: "map_end_guard_minutes",
        label: "Schutz vor Kartenende",
        unit: "Minuten",
        recommended: "10 Minuten",
        description:
          "Wenn laut Spielzeit nur noch so viele Minuten verbleiben, wird kein neuer Wechsel geplant. Ein laufender Vorgang wird bei ungültigen Bedingungen verworfen.",
        lower: "Der Balancer darf noch sehr spät in die Runde eingreifen.",
        higher:
          "Spieler werden früher vor späten, wenig hilfreichen Wechseln geschützt.",
      },
      {
        key: "connection_grace_seconds",
        label: "Schutz nach Verbindung",
        unit: "Sekunden",
        recommended: "120 Sekunden",
        description:
          "Ein frisch verbundener Spieler ist für diese Zeit kein automatischer Kandidat. So kann er Team und Squad wählen und vollständig laden.",
        lower: "Neue Spieler können fast sofort ausgewählt werden.",
        higher:
          "Mehr Schutz für neue Spieler, aber eine kleinere Kandidatenmenge.",
      },
      {
        key: "cooldown_maps",
        label: "Schutz nach einem Autobalance-Wechsel",
        unit: "Karten",
        recommended: "3 Karten",
        description:
          "Nach einem bestätigten Wechsel ist der Spieler über diese Anzahl Karten hart ausgeschlossen. Der Schutz gilt auch bei freiwilligem Melden.",
        lower: "Dieselben Spieler können häufiger betroffen sein.",
        higher:
          "Fairer für Einzelne, aber bei kleinen Stammgruppen stehen weniger Kandidaten bereit.",
      },
      {
        key: "max_switches_per_incident",
        label: "Maximale Wechsel pro Vorfall",
        unit: "Wechsel",
        recommended: "3 Wechsel",
        description:
          "Absolute Sicherheitsgrenze für einen zusammenhängenden Vorfall. Nach jedem einzelnen Wechsel wird neu gerechnet; der alte Mehrspielerplan wird nie blind abgearbeitet.",
        lower:
          "Kleinere Eingriffe, große Differenzen werden eventuell nicht vollständig korrigiert.",
        higher:
          "Größere Korrekturen möglich, aber mehr Spieler können in einem Vorfall betroffen sein.",
      },
    ],
  },
  {
    title: "3. Freiwillige, Admin-Freigabe und Vormerkung",
    intro:
      "Diese Werte wirken erst in manual oder auto. Im Shadow-Modus gibt es weder Direktnachrichten noch eine aktive Vormerkung.",
    fields: [
      {
        key: "volunteer_phase_seconds",
        label: "Freiwilligenphase",
        unit: "Sekunden",
        recommended: "30 Sekunden",
        description:
          "Geeignete Spieler im größeren Team erhalten einmalig den Aufruf. Nur während dieses Zeitfensters und nur für den aktuellen Vorfall akzeptiert der Dienst den Chatbefehl.",
        lower:
          "Weniger Zeit zum Reagieren; automatische Auswahl beginnt früher.",
        higher: "Mehr Chance auf Freiwillige, aber langsamere Korrektur.",
      },
      {
        key: "volunteer_command",
        label: "Chatbefehl für Freiwillige",
        recommended: "!balance",
        description:
          "Exakt dieser einzelne Chatbefehl meldet einen Spieler freiwillig. Er funktioniert nicht dauerhaft und bringt keine Belohnung oder Umgehung der Schutzregeln.",
        important:
          "Der Befehl muss mit ! beginnen und darf keine Leerzeichen enthalten.",
      },
      {
        key: "manual_proposal_timeout_seconds",
        label: "Zeit für Admin-Freigabe",
        unit: "Sekunden",
        recommended: "120 Sekunden",
        description:
          "Nur in manual: So lange bleibt der Kandidatenvorschlag in der Teamansicht gültig. Bei Freigabe werden alle Bedingungen noch einmal geprüft.",
        lower:
          "Admins müssen schneller reagieren; Vorschläge veralten seltener.",
        higher:
          "Mehr Reaktionszeit, aber die Spielsituation kann sich stärker verändern.",
      },
      {
        key: "candidate_timeout_seconds",
        label: "Wartezeit auf den Tod des Kandidaten",
        unit: "Sekunden",
        recommended: "180 Sekunden",
        description:
          "Nach Freigabe oder automatischer Auswahl wartet der Dienst höchstens so lange auf den nächsten Tod. Danach wird die Vormerkung gelöscht und neu geplant.",
        lower: "Schnellere Neuauswahl bei lange überlebenden Spielern.",
        higher: "Weniger Neuauswahl, aber eine Vormerkung bleibt länger offen.",
      },
    ],
  },
  {
    title: "4. Technische Sicherheitsfenster",
    intro:
      "Diese Werte schützen vor verspäteten Logs und unbestätigten RCON-Aktionen. Die Standardwerte sollten normalerweise nicht verändert werden.",
    fields: [
      {
        key: "death_event_max_age_seconds",
        label: "Maximales Alter des Todesereignisses",
        unit: "Sekunden",
        recommended: "5 Sekunden",
        description:
          "Ein Wechsel darf nur durch einen frischen Tod des aktuell vorgemerkten Spielers ausgelöst werden. Alte oder doppelte Kill-Logs werden nicht verwendet.",
        lower:
          "Strenger gegen verspätete Logs, aber echte Ereignisse könnten bei Last verworfen werden.",
        higher:
          "Toleranter bei Verzögerung, aber ältere Ereignisse bleiben länger gültig.",
      },
      {
        key: "switch_confirmation_timeout_seconds",
        label: "Zeit zur Bestätigung des Wechsels",
        unit: "Sekunden",
        recommended: "15 Sekunden",
        description:
          "Nach dem RCON-Befehl müssen Teamwechsel-Log und ein neuer Snapshot bestätigen, dass der Spieler wirklich im Zielteam ist und die Differenz kleiner wurde.",
        lower:
          "Fehler werden schneller gemeldet, langsame Bestätigungen können aber fehlen.",
        higher:
          "Mehr Zeit für RCON und Logs, dafür längere Unklarheit bei einem Fehlschlag.",
      },
    ],
  },
  {
    title: "5. Rollenrating und Shadow-Strategie (V2)",
    intro:
      "Das Rollenrating ist ein sekundäres Sicherheitskriterium. Squad-Schutz bleibt vorrangig und bei ausgeglichenen Spielerzahlen findet niemals ein Stärkewechsel statt.",
    fields: [
      {
        key: "skill_strategy",
        label: "Aktive Shadow-Strategie",
        recommended: "balanced-v2",
        description:
          "balanced-v2 schützt Squads zuerst, verhindert aber grobe statistische Schieflagen. squad-first dient als alte Referenz. skill-first wird parallel nur zur Diagnose berechnet und ist nicht für spätere Ausführung vorgesehen.",
        important:
          "Im Shadow-Modus werden immer alle drei Varianten gespeichert. Dieser Wert legt fest, welche davon als Empfehlung hervorgehoben wird.",
      },
      {
        key: "skill_gap_soft_limit",
        label: "Weiche Grenze der Ratingdifferenz",
        unit: "Ratingpunkte",
        recommended: "8",
        description:
          "Bleibt die projizierte Differenz unter diesem Wert, gewinnt der am wenigsten geschützte passende Kandidat. Oberhalb darf balanced-v2 höchstens eine Schutzstufe weiter suchen, wenn dies deutlich hilft.",
        lower:
          "Statistik greift früher in die Auswahl ein; dadurch werden eher stärker geschützte Squads berührt.",
        higher:
          "Squad-Schutz dominiert länger, größere Stärkeunterschiede werden toleriert.",
      },
      {
        key: "skill_gap_min_improvement",
        label: "Mindestverbesserung für eine Schutzstufen-Eskalation",
        unit: "Ratingpunkte",
        recommended: "2.5",
        description:
          "Eine um genau eine Stufe stärker geschützte Alternative wird nur gewählt, wenn sie die projizierte Ratingdifferenz mindestens um diesen Betrag verbessert.",
        lower:
          "Schon kleine statistische Vorteile rechtfertigen häufiger einen stärkeren Eingriff in Squads.",
        higher:
          "Nur sehr deutliche Vorteile können die zusätzliche Schutzstufe rechtfertigen.",
      },
      {
        key: "skill_gap_hard_warning",
        label: "Deutliche Ratingwarnung",
        unit: "Ratingpunkte",
        recommended: "12",
        description:
          "Ab dieser projizierten Differenz erhält der Shadow-Vorschlag eine gut sichtbare Warnung. Die Warnung löst keinen Wechsel aus und hebt keine harte Sperre auf.",
        lower:
          "Admins sehen Warnungen schon bei kleineren statistischen Differenzen.",
        higher: "Nur sehr große Unterschiede werden markiert.",
      },
      {
        key: "history_half_life_days",
        label: "Halbwertszeit der Historie",
        unit: "Tage",
        recommended: "30",
        description:
          "Leistung aus einer 30 Tage alten Runde zählt noch halb so stark wie eine aktuelle Runde. Maximal 20 Karten aus 90 Tagen mit mindestens zehn Minuten Spielzeit fließen ein.",
        lower:
          "Das Rating reagiert schneller auf aktuelle Form, schwankt aber stärker.",
        higher:
          "Ältere Leistungen bleiben länger wichtig; Veränderungen werden langsamer sichtbar.",
      },
      {
        key: "history_server_numbers",
        label: "Server für die Spielstärke-Historie",
        recommended: "[1, 2]",
        description:
          "Abgeschlossene Karten dieser CRCON-Server dürfen für das Rating verwendet werden. Die Historie ist nur ein sekundärer Tie-Breaker nach allen Schutzstufen.",
        important:
          "Für den gemeinsamen FLN-Pool bleiben Server 1 und 2 eingetragen. Eine leere Liste bedeutet: keine serverübergreifende Historie.",
      },
    ],
  },
  {
    title: "6. Spielernachrichten",
    intro:
      "Ingame-Texte enthalten bewusst keine Ratings, Komponenten oder Konfidenzwerte. Diese Daten sehen ausschließlich berechtigte CRCON-Admins.",
    fields: [
      {
        key: "messages",
        label: "Spielernachrichten",
        displayValue: "4 deutsche Vorlagen",
        recommended: "Standardvorlagen",
        description:
          "Vorlagen für Freiwilligenaufruf, Annahme, Auswahl und bestätigten Wechsel. Im Shadow-Modus wird keine dieser Nachrichten gesendet.",
        important:
          "Die Platzhalter in geschweiften Klammern müssen erhalten bleiben. Änderungen sind unter „Erweitert (JSON)“ möglich.",
      },
    ],
  },
];

const formatValue = (value, unit) => {
  if (Array.isArray(value)) return `[${value.join(", ")}]`;
  if (value === undefined || value === null || value === "")
    return "nicht gesetzt";
  return `${value}${unit ? ` ${unit}` : ""}`;
};

const SettingExplanation = ({ field, config }) => {
  const currentValue =
    field.displayValue || formatValue(config[field.key], field.unit);
  return (
    <Box sx={{ py: 1.5 }}>
      <Stack
        direction={{ xs: "column", sm: "row" }}
        spacing={1}
        alignItems={{ sm: "center" }}
        sx={{ mb: 0.75 }}
      >
        <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
          {field.label}
        </Typography>
        <Chip size="small" color="primary" label={`Aktuell: ${currentValue}`} />
        <Chip
          size="small"
          variant="outlined"
          label={`FLN-Empfehlung: ${field.recommended}`}
        />
      </Stack>
      <Typography
        variant="caption"
        color="text.secondary"
        sx={{ display: "block", mb: 0.75 }}
      >
        Technischer Name: <code>{field.key}</code>
      </Typography>
      <Typography variant="body2" paragraph sx={{ mb: 0.75 }}>
        <strong>Wirkung:</strong> {field.description}
      </Typography>
      {field.lower && (
        <Typography variant="body2" color="text.secondary">
          <strong>Wenn niedriger:</strong> {field.lower}
        </Typography>
      )}
      {field.higher && (
        <Typography variant="body2" color="text.secondary">
          <strong>Wenn höher:</strong> {field.higher}
        </Typography>
      )}
      {field.important && (
        <Typography variant="body2" color="warning.main">
          <strong>Wichtig:</strong> {field.important}
        </Typography>
      )}
    </Box>
  );
};

const AutobalancerHelp = ({ config = {} }) => {
  const mode = MODE_INFO[config.mode] || MODE_INFO.disabled;
  const targetDifference = config.target_difference ?? 2;
  const stableSeconds = config.stable_difference_seconds ?? 45;
  const maxSwitches = config.max_switches_per_incident ?? 3;

  return (
    <Stack spacing={2} sx={{ mt: 2, mb: 3 }}>
      <Alert severity={mode.severity}>
        <strong>Aktiver Modus: {mode.label}.</strong> {mode.text}
      </Alert>

      <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="h5" sx={{ mb: 1 }}>
          Kurz gesagt: Was macht der Balancer?
        </Typography>
        <Typography variant="body2" paragraph>
          Er greift nur ein, wenn die <strong>Spielerzahlen</strong> länger als{" "}
          <strong>{stableSeconds} Sekunden</strong> um mehr als{" "}
          <strong>{targetDifference} Spieler</strong> auseinanderliegen. Bei
          gleichen Spielerzahlen führt er niemals einen reinen Stärkewechsel
          durch.
        </Typography>
        <Typography component="ol" variant="body2" sx={{ pl: 2.5, mb: 1 }}>
          <li>Vollständige Team-, Spieler-, Rollen- und Squaddaten prüfen.</li>
          <li>
            Harte Sperren anwenden: Commander, Kartenzeiten, Neuverbindungen und
            Cooldown.
          </li>
          <li>
            Squads möglichst erhalten und unter den zulässigen Spielern fair
            auswählen.
          </li>
          <li>
            Immer nur einen Spieler behandeln und danach alles neu berechnen.
          </li>
        </Typography>
        <Alert severity="success" sx={{ mt: 1 }}>
          Ein Wechsel reduziert die Teamdifferenz um zwei: Aus 50:44 wird nach
          einem Wechsel 49:45. Bei Zieldifferenz 2 wären rechnerisch zwei
          Wechsel nötig – trotzdem wird nach dem ersten Wechsel vollständig neu
          geplant. Pro Vorfall gelten maximal {maxSwitches} Wechsel.
        </Alert>
      </Box>

      <Box sx={{ p: 2, border: 1, borderColor: "divider", borderRadius: 1 }}>
        <Typography variant="h6" sx={{ mb: 1 }}>
          Was bedeuten die vier Modi?
        </Typography>
        <Box
          sx={{
            display: "grid",
            gridTemplateColumns: { xs: "1fr", md: "1fr 1fr" },
            gap: 1.5,
          }}
        >
          {MODE_CARDS.map((item) => (
            <Box
              key={item.mode}
              sx={{
                p: 1.5,
                border: 1,
                borderColor:
                  config.mode === item.mode ? "primary.main" : "divider",
                borderRadius: 1,
                bgcolor:
                  config.mode === item.mode ? "action.selected" : "transparent",
              }}
            >
              <Typography variant="subtitle2" sx={{ fontWeight: 700 }}>
                {item.title} {config.mode === item.mode ? "(aktuell)" : ""}
              </Typography>
              <Typography variant="body2" color="text.secondary">
                {item.text}
              </Typography>
            </Box>
          ))}
        </Box>
      </Box>

      <Alert severity="info">
        <strong>Begriffe:</strong> Ein „Vorfall“ ist ein zusammenhängendes
        Ungleichgewicht. „Vorgemerkt“ bedeutet: Der Dienst wartet auf den
        nächsten Tod genau dieses Spielers. „Bestätigt“ bedeutet: Log und
        frischer Snapshot zeigen den Spieler im Zielteam und eine kleinere
        Teamdifferenz.
      </Alert>

      <Typography variant="h5">Alle Einstellungen einzeln erklärt</Typography>
      <Typography variant="body2" color="text.secondary">
        Die Bereiche lassen sich aufklappen. „Aktuell“ ist der gerade
        gespeicherte Wert dieses Servers; „FLN-Empfehlung“ ist der sichere
        Pilotwert.
      </Typography>

      {FIELD_GROUPS.map((group, groupIndex) => (
        <Accordion
          key={group.title}
          defaultExpanded={groupIndex === 0}
          disableGutters
        >
          <AccordionSummary expandIcon={<ExpandMoreIcon />}>
            <Typography variant="subtitle1" sx={{ fontWeight: 700 }}>
              {group.title}
            </Typography>
          </AccordionSummary>
          <AccordionDetails>
            <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
              {group.intro}
            </Typography>
            <Divider />
            {group.fields.map((field, index) => (
              <Box key={field.key}>
                <SettingExplanation field={field} config={config} />
                {index < group.fields.length - 1 && <Divider />}
              </Box>
            ))}
          </AccordionDetails>
        </Accordion>
      ))}

      <Alert severity="warning">
        <strong>Vor dem Wechsel auf manual oder auto:</strong> Shadow-Vorschläge
        in der Teamansicht und im Audit auswerten. Der native HLL-Autobalancer
        bleibt ein separater vorgelagerter Schutz und wird durch diese
        Einstellungen nicht verändert.
      </Alert>

      <Typography variant="caption" color="text.secondary">
        Änderungen gelten nur für diesen CRCON-Server. Mit „Einstellungen
        speichern“ übernehmen. Die deutschen Standardnachrichten müssen für den
        Shadow-Pilot nicht geändert werden.
      </Typography>
    </Stack>
  );
};

export default AutobalancerHelp;
