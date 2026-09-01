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
import { simulateLevelRule } from "./simulateLevelRule.mjs";

const copyByLanguage = {
  de: {
    title: "Level-Regel prüfen",
    description:
      "Teste einen Beispielspieler gegen den aktuellen Entwurf, ohne eine Serveraktion auszuführen.",
    notice:
      "Die Simulation nutzt nur die sichtbaren Formularwerte. Sie speichert nichts und sendet keine Nachricht an den Gameserver.",
    playerLevel: "Level des Beispielspielers",
    serverPlayers: "Spieler auf dem Server",
    role: "Rolle des Beispielspielers",
    noRole: "Keine bestimmte Rolle",
    flag: "Spieler-Markierung (optional)",
    run: "Simulation ausführen",
    close: "Simulation schließen",
    result: "Erwartete Wirkung",
    stage: { warn: "Warnen", punish: "Bestrafen", kick: "Kicken" },
    resultCopy: {
      off: ["Regel ist ausgeschaltet", "Für diesen Spieler erfolgt keine Prüfung."],
      waiting: [
        "Startbedingung noch nicht erreicht",
        "Die Regel beginnt erst ab {{count}} Spielern.",
      ],
      exempt: [
        "Spieler ist ausgenommen",
        "Eine konfigurierte Ausnahme verhindert die weitere Eskalation.",
      ],
      allowed: [
        "Spieler erfüllt die Regel",
        "Mit diesen Testdaten wird keine Levelgrenze verletzt.",
      ],
      immediate: [
        "Direkter Eingriff wegen Serverlevel",
        "Der Spieler verletzt die allgemeine Levelgrenze {{level}}.",
      ],
      escalation: [
        "Rollenbezogene Eskalation",
        "Für diese Rolle gilt mindestens Level {{level}}. Die konfigurierte Wirkungskette würde beginnen.",
      ],
      detected: [
        "Verstoß ohne Maßnahme erkannt",
        "Für diese Rolle gilt mindestens Level {{level}}, aber keine Eskalationsstufe ist aktiviert.",
      ],
      observeSuffix:
        " Im Modus Beobachten wird die Wirkung nur protokolliert und nicht ausgeführt.",
    },
  },
  en: {
    title: "Test level rule",
    description:
      "Check a sample player against the current draft without executing a server action.",
    notice:
      "The simulation only uses the visible form values. It saves nothing and sends no command to the game server.",
    playerLevel: "Sample player level",
    serverPlayers: "Players on the server",
    role: "Sample player role",
    noRole: "No specific role",
    flag: "Player flag (optional)",
    run: "Run simulation",
    close: "Close simulation",
    result: "Expected effect",
    stage: { warn: "Warn", punish: "Punish", kick: "Kick" },
    resultCopy: {
      off: ["Rule is off", "This player is not checked."],
      waiting: [
        "Start condition not reached",
        "The rule starts at {{count}} players.",
      ],
      exempt: [
        "Player is exempt",
        "A configured exception prevents further escalation.",
      ],
      allowed: [
        "Player passes the rule",
        "These test values do not violate a level threshold.",
      ],
      immediate: [
        "Immediate server-level action",
        "The player violates the general level threshold {{level}}.",
      ],
      escalation: [
        "Role-based escalation",
        "This role requires level {{level}}. The configured action sequence would begin.",
      ],
      detected: [
        "Violation detected without an action",
        "This role requires level {{level}}, but no escalation stage is enabled.",
      ],
      observeSuffix:
        " In Observe mode, the effect is logged but not executed.",
    },
  },
};

const fill = (value, variables) =>
  Object.entries(variables).reduce(
    (text, [key, replacement]) =>
      text.replace(`{{${key}}}`, String(replacement)),
    value
  );

export default function LevelRuleTestDrawer({ open, onClose, data }) {
  const { i18n, t } = useTranslation();
  const copy = copyByLanguage[i18n.language?.startsWith("de") ? "de" : "en"];
  const [sample, setSample] = useState({
    playerLevel: 20,
    serverPlayers: 60,
    role: "officer",
    playerFlag: "",
  });
  const [hasRun, setHasRun] = useState(false);

  useEffect(() => {
    if (!open) setHasRun(false);
  }, [open]);
  const simulation = useMemo(
    () => simulateLevelRule(data, sample),
    [data, sample]
  );

  const result = useMemo(() => {
    if (!hasRun) return null;
    const [title, template] = copy.resultCopy[simulation.outcome];
    const description =
      fill(template, {
        count: simulation.startAt ?? 0,
        level: simulation.requiredLevel ?? 0,
      }) +
      (simulation.mode === "observe" &&
      ["immediate", "escalation"].includes(simulation.outcome)
        ? copy.resultCopy.observeSuffix
        : "");
    const tone = ["immediate", "escalation"].includes(simulation.outcome)
      ? simulation.mode === "observe"
        ? "warning"
        : "error"
      : simulation.outcome === "detected"
      ? "warning"
      : simulation.outcome === "allowed"
      ? "success"
      : "info";
    return {
      title,
      description,
      tone,
      steps: simulation.stages.map((stage) => copy.stage[stage]),
    };
  }, [copy, hasRun, simulation]);

  const update = (field) => (event) => {
    setHasRun(false);
    setSample((current) => ({
      ...current,
      [field]: ["playerLevel", "serverPlayers"].includes(field)
        ? Number(event.target.value)
        : event.target.value,
    }));
  };

  return (
    <ConfigTestDrawer
      open={open}
      onClose={onClose}
      title={copy.title}
      description={copy.description}
      notice={copy.notice}
      result={result}
      resultLabel={copy.result}
      runLabel={copy.run}
      closeLabel={copy.close}
      onRun={() => setHasRun(true)}
    >
      <Stack spacing={1.5}>
        <TextField
          type="number"
          label={copy.playerLevel}
          value={sample.playerLevel}
          onChange={update("playerLevel")}
          inputProps={{ min: 0, max: 500, step: 1 }}
        />
        <TextField
          type="number"
          label={copy.serverPlayers}
          value={sample.serverPlayers}
          onChange={update("serverPlayers")}
          inputProps={{ min: 0, max: 100, step: 1 }}
        />
        <FormControl fullWidth>
          <InputLabel id="level-test-role-label">{copy.role}</InputLabel>
          <Select
            labelId="level-test-role-label"
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
        <TextField
          label={copy.flag}
          value={sample.playerFlag}
          onChange={update("playerFlag")}
        />
      </Stack>
    </ConfigTestDrawer>
  );
}
