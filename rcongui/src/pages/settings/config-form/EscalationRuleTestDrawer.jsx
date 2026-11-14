import { useEffect, useMemo, useState } from "react";
import {
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Stack,
  TextField,
} from "@mui/material";
import { useTranslation } from "react-i18next";
import { getAllRoles } from "@/constants/roles";
import ConfigTestDrawer from "./ConfigTestDrawer";
import { simulateEscalationRule } from "./simulateEscalationRule.mjs";
import frenchCopy from "./escalation-copy-fr.json";

const copyByLanguage = {
  de: {
    noLeader: {
      title: "Truppführer-Regel prüfen",
      description:
        "Teste einen Beispieltrupp gegen den aktuellen Entwurf der vierstufigen Regel.",
      condition: "Zustand des Beispieltrupps",
      conditions: {
        leaderless: "Trupp ohne Truppführer",
        led: "Truppführer vorhanden",
        unassigned: "Spieler nicht zugewiesen",
        commander: "Kommandantenplatz",
      },
    },
    noSoloTank: {
      title: "Solo-Panzer-Regel prüfen",
      description:
        "Teste eine Beispielbesatzung gegen den aktuellen Entwurf der vierstufigen Regel.",
      condition: "Trupptyp des Beispielspielers",
      conditions: {
        armor: "Panzertrupp",
        infantry: "Infanterietrupp",
        recon: "Aufklärungstrupp",
      },
    },
    notice:
      "Die Simulation folgt der gespeicherten CRCON-Ablauflogik mit den sichtbaren Formularwerten. Sie verändert keinen Status, speichert nichts und sendet keine Aktion an den Gameserver.",
    serverPlayers: "Spieler auf dem Server",
    squadPlayers: "Spieler im Trupp",
    playerLevel: "Level des Beispielspielers",
    role: "Rolle des Beispielspielers",
    noRole: "Keine bestimmte Rolle",
    flag: "Spieler-Markierung (optional)",
    run: "Simulation ausführen",
    close: "Simulation schließen",
    result: "Erwartete Wirkung",
    resultCopy: {
      off: ["Regel ist ausgeschaltet", "Der Beispielzustand wird nicht geprüft."],
      waiting: [
        "Globale Startbedingung nicht erreicht",
        "Die Regel beginnt erst ab {{count}} Spielern auf dem Server.",
      ],
      noViolation: [
        "Kein Regelverstoß",
        "Der Beispielzustand erfüllt die Erkennungsbedingung nicht.",
      ],
      exempt: [
        "Spieler ist ausgenommen",
        "Die konfigurierte Ausnahme beendet die Wirkungskette vor der ersten Prüfung.",
      ],
      escalation: [
        "Wirkungskette wird ausgelöst",
        "Bleibt der Verstoß bestehen, durchläuft der Spieler die unten gezeigten Stufen.",
      ],
      paused: [
        "Wirkungskette wartet an einer Schwelle",
        "Der Verstoß wird erkannt, die nächste Maßnahme ist mit diesen Testdaten aber noch gesperrt.",
      ],
      detected: [
        "Verstoß ohne sichtbare Maßnahme",
        "Der Zustand wird erkannt, aber Warnung, Bestrafung und Kick sind nicht erreichbar.",
      ],
    },
    reason: {
      led: "Der Trupp besitzt einen Truppführer.",
      unassigned: "Nicht zugewiesene Spieler werden übersprungen.",
      commander: "Der Kommandantenplatz wird übersprungen.",
      nonArmor: "Nur Panzertrupps werden geprüft.",
      crewed: "Der Panzertrupp besitzt mindestens zwei Mitglieder.",
      flag: "Die Spieler-Markierung steht im Ausnahmekatalog.",
      level: "Das Spielerlevel liegt im geschützten Bereich.",
      role: "Die Spielerrolle steht im Ausnahmekatalog.",
    },
    observeSuffix:
      " Im Modus Beobachten werden diese Schritte nur im Audit protokolliert.",
    stages: {
      note: "Bestätigen",
      warn: "Warnen",
      punish: "Bestrafen",
      kick: "Kicken",
      unlimited: "unbegrenzt",
      count: "{{count}}× · alle {{seconds}} Sekunden",
      kickDelay: "nach {{seconds}} Sekunden Frist",
      blockedServer: "pausiert · erst ab {{count}} Spielern",
      blockedSquad: "pausiert · erst ab {{count}} Truppmitgliedern",
    },
  },
  en: {
    noLeader: {
      title: "Test squad-leader rule",
      description:
        "Check a sample squad against the current four-stage rule draft.",
      condition: "Sample squad state",
      conditions: {
        leaderless: "Squad without a leader",
        led: "Squad leader present",
        unassigned: "Player is unassigned",
        commander: "Commander slot",
      },
    },
    noSoloTank: {
      title: "Test solo-tank rule",
      description:
        "Check a sample crew against the current four-stage rule draft.",
      condition: "Sample player squad type",
      conditions: {
        armor: "Armor squad",
        infantry: "Infantry squad",
        recon: "Recon squad",
      },
    },
    notice:
      "The simulation follows CRCON's saved escalation logic with the visible form values. It changes no state, saves nothing and sends no action to the game server.",
    serverPlayers: "Players on the server",
    squadPlayers: "Players in the squad",
    playerLevel: "Sample player level",
    role: "Sample player role",
    noRole: "No specific role",
    flag: "Player flag (optional)",
    run: "Run simulation",
    close: "Close simulation",
    result: "Expected effect",
    resultCopy: {
      off: ["Rule is off", "The sample state is not checked."],
      waiting: [
        "Global start condition not reached",
        "The rule starts at {{count}} players on the server.",
      ],
      noViolation: [
        "No rule violation",
        "The sample state does not meet the detection condition.",
      ],
      exempt: [
        "Player is exempt",
        "The configured exemption ends the effect chain before the first check.",
      ],
      escalation: [
        "Effect chain is triggered",
        "If the violation persists, the player moves through the stages below.",
      ],
      paused: [
        "Effect chain is waiting at a threshold",
        "The violation is detected, but the next action is blocked by these sample values.",
      ],
      detected: [
        "Violation without a visible action",
        "The state is detected, but warning, punishment and kick are unreachable.",
      ],
    },
    reason: {
      led: "The squad has a leader.",
      unassigned: "Unassigned players are skipped.",
      commander: "The commander slot is skipped.",
      nonArmor: "Only armor squads are checked.",
      crewed: "The armor squad has at least two members.",
      flag: "The player flag is in the exemption catalog.",
      level: "The player level is inside the protected range.",
      role: "The player role is in the exemption catalog.",
    },
    observeSuffix:
      " In Observe mode, these steps are only written to the audit log.",
    stages: {
      note: "Confirm",
      warn: "Warn",
      punish: "Punish",
      kick: "Kick",
      unlimited: "unlimited",
      count: "{{count}}× · every {{seconds}} seconds",
      kickDelay: "after a {{seconds}} second grace period",
      blockedServer: "paused · starts at {{count}} players",
      blockedSquad: "paused · starts at {{count}} squad members",
    },
  },
};

const fill = (value, variables) =>
  Object.entries(variables).reduce(
    (text, [key, replacement]) =>
      text.replace(`{{${key}}}`, String(replacement)),
    value
  );

const formatStage = (stage, copy) => {
  const label = copy.stages[stage.kind];
  if (stage.blocked) {
    return `${label} · ${fill(
      stage.blocked.reason === "serverPlayers"
        ? copy.stages.blockedServer
        : copy.stages.blockedSquad,
      { count: stage.blocked.minimum }
    )}`;
  }
  if (stage.kind === "kick") {
    return `${label} · ${fill(copy.stages.kickDelay, {
      seconds: stage.delay,
    })}`;
  }
  return `${label} · ${
    stage.count === -1
      ? copy.stages.unlimited
      : fill(copy.stages.count, {
          count: stage.count,
          seconds: stage.interval,
        })
  }`;
};

const initialSample = (kind) => ({
  serverPlayers: 60,
  squadPlayers: kind === "noSoloTank" ? 1 : 3,
  playerLevel: 100,
  playerFlag: "",
  role: "rifleman",
  squadState: "leaderless",
  squadType: "armor",
});

export default function EscalationRuleTestDrawer({
  open,
  onClose,
  data,
  kind,
}) {
  const { i18n, t } = useTranslation();
  const language = (i18n.resolvedLanguage || i18n.language || "en").split("-")[0];
  const copy = language === "fr" ? frenchCopy : copyByLanguage[language === "de" ? "de" : "en"];
  const kindCopy = copy[kind];
  const [sample, setSample] = useState(() => initialSample(kind));
  const [hasRun, setHasRun] = useState(false);

  useEffect(() => {
    setSample(initialSample(kind));
    setHasRun(false);
  }, [kind]);

  useEffect(() => {
    setHasRun(false);
  }, [open]);

  const simulation = useMemo(
    () => simulateEscalationRule(kind, data, sample),
    [data, kind, sample]
  );

  const result = useMemo(() => {
    if (!hasRun) return null;
    const [title, template] = copy.resultCopy[simulation.outcome];
    const reason = simulation.reason ? copy.reason[simulation.reason] : "";
    const modeSuffix =
      simulation.mode === "observe" &&
      ["escalation", "paused", "detected"].includes(simulation.outcome)
        ? copy.observeSuffix
        : "";
    return {
      title,
      description:
        fill(template, { count: simulation.startAt ?? 0 }) +
        (reason ? ` ${reason}` : "") +
        modeSuffix,
      tone:
        simulation.outcome === "escalation"
          ? simulation.mode === "observe"
            ? "warning"
            : "error"
          : simulation.outcome === "paused" || simulation.outcome === "detected"
          ? "warning"
          : simulation.outcome === "noViolation"
          ? "success"
          : "info",
      steps: simulation.stages.map((stage) => formatStage(stage, copy)),
    };
  }, [copy, hasRun, simulation]);

  const update = (field) => (event) => {
    setHasRun(false);
    setSample((current) => ({
      ...current,
      [field]: ["serverPlayers", "squadPlayers", "playerLevel"].includes(field)
        ? Number(event.target.value)
        : event.target.value,
    }));
  };

  const conditionValue =
    kind === "noLeader" ? sample.squadState : sample.squadType;
  const conditionField = kind === "noLeader" ? "squadState" : "squadType";

  return (
    <ConfigTestDrawer
      open={open}
      onClose={onClose}
      title={kindCopy.title}
      description={kindCopy.description}
      notice={copy.notice}
      result={result}
      resultLabel={copy.result}
      runLabel={copy.run}
      closeLabel={copy.close}
      onRun={() => setHasRun(true)}
    >
      <Stack spacing={1.5}>
        <FormControl fullWidth>
          <InputLabel id={`escalation-test-${conditionField}-label`}>
            {kindCopy.condition}
          </InputLabel>
          <Select
            labelId={`escalation-test-${conditionField}-label`}
            label={kindCopy.condition}
            value={conditionValue}
            onChange={update(conditionField)}
          >
            {Object.entries(kindCopy.conditions).map(([value, label]) => (
              <MenuItem key={value} value={value}>
                {label}
              </MenuItem>
            ))}
          </Select>
        </FormControl>
        <TextField
          type="number"
          label={copy.serverPlayers}
          value={sample.serverPlayers}
          onChange={update("serverPlayers")}
          inputProps={{ min: 0, max: 100, step: 1 }}
        />
        <TextField
          type="number"
          label={copy.squadPlayers}
          value={sample.squadPlayers}
          onChange={update("squadPlayers")}
          inputProps={{ min: 1, max: 6, step: 1 }}
        />
        <TextField
          type="number"
          label={copy.playerLevel}
          value={sample.playerLevel}
          onChange={update("playerLevel")}
          inputProps={{ min: 0, max: 500, step: 1 }}
        />
        {kind === "noLeader" && (
          <FormControl fullWidth>
            <InputLabel id="escalation-test-role-label">{copy.role}</InputLabel>
            <Select
              labelId="escalation-test-role-label"
              label={copy.role}
              value={sample.role}
              onChange={update("role")}
            >
              <MenuItem value="">{copy.noRole}</MenuItem>
              {getAllRoles().map((role) => (
                <MenuItem key={role.value} value={role.value}>
                  {t(`settings.configForms.roles.${role.value}`, {
                    defaultValue: role.label,
                  })}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        <TextField
          label={copy.flag}
          value={sample.playerFlag}
          onChange={update("playerFlag")}
        />
      </Stack>
    </ConfigTestDrawer>
  );
}
