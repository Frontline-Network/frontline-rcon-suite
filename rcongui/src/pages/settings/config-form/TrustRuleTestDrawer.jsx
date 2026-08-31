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
import ConfigTestDrawer from "./ConfigTestDrawer";
import { simulateTrustRule } from "./simulateTrustRule.mjs";

const copyByLanguage = {
  de: {
    vacBans: {
      title: "VAC-/Spielsperren sicher prüfen",
      description:
        "Prüfe eine Steam-Sperrhistorie gegen den aktuellen Entwurf und sieh, wie belastbar die Entscheidung ist.",
      notice:
        "Die Simulation bildet den aktuellen CRCON-Ablauf ab: Beim Beitritt werden zuerst gespeicherte Steam-Daten geprüft. Eine Hintergrundaktualisierung kann danach eine zweite Prüfung auslösen. Es wird nichts gespeichert und keine Sperre ausgeführt.",
      dataStatus: "Zustand der gespeicherten Steam-Daten",
      dataStatuses: {
        current: "Vorhanden · jünger als 12 Stunden",
        stale: "Vorhanden · älter als 12 Stunden",
        unknownAge: "Vorhanden · Alter unbekannt",
        missing: "Noch kein Datensatz vorhanden",
        invalid: "Antwort fehlt oder ist ungültig",
      },
      vacBanned: "VAC-Sperre gemeldet",
      gameBans: "Anzahl Spielsperren",
      daysSinceLastBan: "Tage seit der letzten Sperre",
      playerFlag: "Spieler-Markierung (optional)",
    },
    tkBans: {
      title: "TK-Sperre sicher prüfen",
      description:
        "Prüfe einen frühen Teamkill gegen Zeitfenster, Ausnahmen, Toleranz und Sperrmaßnahme.",
      notice:
        "Die Simulation folgt der aktuellen Auswertung der letzten 500 Spielerlogs. Ist das Spielerprofil nicht verfügbar, läuft die Prüfung weiter; VIP-, Sitzungs- und Markierungs-Ausnahmen können dann nicht sicher greifen. Es wird nichts gespeichert und keine Sperre ausgeführt.",
      profileStatus: "Verfügbarkeit des Spielerprofils",
      profileStatuses: {
        available: "Profil verfügbar",
        missing: "Profil nicht verfügbar",
      },
      vipLookupStatus: "VIP-Liste",
      vipLookupStatuses: {
        available: "VIP-Liste verfügbar",
        unavailable: "VIP-Liste nicht verfügbar",
      },
      isVip: "Beispielspieler ist VIP",
      sessions: "Bisherige Sitzungen",
      playerFlag: "Spieler-Markierung (optional)",
      hasConnectEvent: "Beitritt in den letzten 500 Logs gefunden",
      weapon: "Waffe des Teamkills",
      minutesAfterConnect: "Minuten seit dem Beitritt",
      ownKillsBeforeEvent: "Eigene Kills vor diesem Teamkill",
      deathsBeforeEvent: "Eigene Tode vor diesem Teamkill",
      teamkillsIncludingCurrent: "Teamkills seit dem Beitritt inklusive diesem",
    },
    yes: "Ja",
    no: "Nein",
    run: "Simulation ausführen",
    close: "Simulation schließen",
    result: "Erwartete Entscheidung",
    outcomes: {
      off: [
        "Regel ist ausgeschaltet",
        "Dieser Beispielzustand wird nicht geprüft.",
      ],
      unavailable: [
        "Keine automatische Sperre mit diesen Daten",
        "CRCON kann aus dem gespeicherten Datensatz keine belastbare Sperrentscheidung ableiten.",
      ],
      exempt: [
        "Spieler ist ausgenommen",
        "Eine konfigurierte Ausnahme beendet die Prüfung vor der Sperrmaßnahme.",
      ],
      noAction: [
        "Keine Sperrmaßnahme",
        "Der Beispielzustand erreicht die konfigurierte Sperrbedingung nicht.",
      ],
      configError: [
        "Sperrmaßnahme scheitert an der Vorlage",
        "Die Bedingung wäre erfüllt, aber ein unbekannter Platzhalter verhindert den nächsten Schritt.",
      ],
      action: [
        "Sperrmaßnahme wird ausgelöst",
        "Der Beispielzustand erfüllt die Regel und führt mit den sichtbaren Werten zur gezeigten Maßnahme.",
      ],
    },
    risks: {
      staleData:
        "Der erste VAC-Entscheid basiert auf einem Datensatz, der älter als zwölf Stunden ist; die Aktualisierung läuft erst parallel an.",
      unknownAge:
        "Das Aktualisierungsalter ist unbekannt. CRCON verwendet den vorhandenen Datensatz trotzdem für die erste Prüfung.",
      profileUnavailable:
        "Ohne Spielerprofil können VIP-, Sitzungs- und Markierungs-Ausnahmen nicht bewertet werden; die TK-Prüfung läuft dennoch weiter.",
      vipLookupUnavailable:
        "Die VIP-Liste ist nicht verfügbar. Eine mögliche VIP-Ausnahme kann nicht erkannt werden.",
      yearsIgnored:
        "Der vorhandene Backend-Vertrag rechnet das Feld Jahre nicht in die TK-Sperrdauer ein.",
      notificationTemplate:
        "Die Sperre wird zuerst ausgeführt; anschließend kann die Discord-Nachricht wegen eines unbekannten Platzhalters fehlschlagen.",
      reasonTemplate:
        "Die VAC-Sperrgrundvorlage enthält einen unbekannten Platzhalter.",
      missing:
        "Ohne gespeicherten Datensatz bleibt die erste Prüfung offen; eine Sperre ist erst nach erfolgreicher Steam-Aktualisierung möglich.",
      invalid:
        "Eine ungültige Steam-Antwort führt zu keiner automatischen Sperre und muss betrieblich beobachtet werden.",
    },
    stages: {
      storedData: {
        current: "Steam-Daten · aktueller gespeicherter Datensatz",
        stale: "Steam-Daten · gespeicherter Datensatz älter als 12 Stunden",
        unknownAge: "Steam-Daten · Aktualisierungsalter unbekannt",
        missing: "Steam-Daten · kein gespeicherter Datensatz",
        invalid: "Steam-Daten · Antwort nicht auswertbar",
      },
      refresh: "Steam-Aktualisierung · im Hintergrund eingeplant",
      freshRecheck: "Folgeprüfung · nach dem Hintergrundjob möglich",
      exemption: {
        flag: "Ausnahme · Spieler-Markierung geschützt",
        vip: "Ausnahme · VIP geschützt",
        sessions: "Ausnahme · genügend bekannte Sitzungen",
        weapon: "Ausnahme · Waffe wird nicht gezählt",
      },
      history:
        "Sperrhistorie · {{days}} Tage · VAC {{vac}} · {{gameBans}} Spielsperren",
      decisionAllow: "Entscheidung · Schwelle nicht erreicht",
      decisionInvalid: "Entscheidung · Datensatz nicht auswertbar",
      decisionTemplate: "Entscheidung · Sperrgrundvorlage ungültig",
      profile: {
        available: "Spielerprofil · verfügbar",
        missing: "Spielerprofil · nicht verfügbar, Ausnahmen unsicher",
      },
      logWindow: {
        connected: "Logfenster · Beitritt gefunden",
        missingConnect: "Logfenster · kein Beitritt in den letzten 500 Zeilen",
      },
      window: {
        expired: "Zeitfenster · Teamkill liegt außerhalb der Frist",
        stoppedByKills: "Zeitfenster · Prüfung nach eigenen Kills beendet",
        stoppedByDeaths: "Zeitfenster · Prüfung nach eigenen Toden beendet",
      },
      counter: "Toleranz · {{teamkills}} Teamkills bei {{tolerance}} erlaubt",
      actionBlacklist: "Sperre · Sperrliste {{id}} · {{duration}}",
      actionServer: "Sperre · direkt auf diesem Server · {{duration}}",
      auditSend: "Audit · Discord-Nachricht wird gesendet",
      auditError:
        "Audit · Nachrichtenvorlage kann nach der Sperre fehlschlagen",
      permanent: "dauerhaft",
      days: "{{count}} Tage",
      hours: "{{count}} Stunden",
      minutes: "{{count}} Minuten",
      durationUnits: {
        weeks: ["Woche", "Wochen"],
        days: ["Tag", "Tage"],
        hours: ["Stunde", "Stunden"],
        minutes: ["Minute", "Minuten"],
      },
      expiresToday: "läuft heute ab",
      vacYes: "aktiv",
      vacNo: "nicht aktiv",
    },
  },
  en: {
    vacBans: {
      title: "Test VAC and game-ban safety",
      description:
        "Check a Steam ban history against the current draft and see how trustworthy the decision is.",
      notice:
        "The simulation mirrors CRCON's current flow: stored Steam data is checked first when a player connects. A background refresh can trigger a second check. Nothing is saved and no ban is executed.",
      dataStatus: "Stored Steam data state",
      dataStatuses: {
        current: "Available · newer than 12 hours",
        stale: "Available · older than 12 hours",
        unknownAge: "Available · age unknown",
        missing: "No stored record yet",
        invalid: "Response missing or invalid",
      },
      vacBanned: "VAC ban reported",
      gameBans: "Number of game bans",
      daysSinceLastBan: "Days since the latest ban",
      playerFlag: "Player flag (optional)",
    },
    tkBans: {
      title: "Test teamkill-ban safety",
      description:
        "Check an early teamkill against the time window, exemptions, tolerance and ban action.",
      notice:
        "The simulation follows the current scan of the latest 500 player logs. If the player profile is unavailable, enforcement continues and VIP, session and flag exemptions cannot be evaluated safely. Nothing is saved and no ban is executed.",
      profileStatus: "Player profile availability",
      profileStatuses: {
        available: "Profile available",
        missing: "Profile unavailable",
      },
      vipLookupStatus: "VIP list",
      vipLookupStatuses: {
        available: "VIP list available",
        unavailable: "VIP list unavailable",
      },
      isVip: "Sample player is a VIP",
      sessions: "Previous sessions",
      playerFlag: "Player flag (optional)",
      hasConnectEvent: "Connection found in the latest 500 logs",
      weapon: "Teamkill weapon",
      minutesAfterConnect: "Minutes since connection",
      ownKillsBeforeEvent: "Own kills before this teamkill",
      deathsBeforeEvent: "Own deaths before this teamkill",
      teamkillsIncludingCurrent:
        "Teamkills since connection including this one",
    },
    yes: "Yes",
    no: "No",
    run: "Run simulation",
    close: "Close simulation",
    result: "Expected decision",
    outcomes: {
      off: ["Rule is off", "This sample state is not checked."],
      unavailable: [
        "No automatic ban with this data",
        "CRCON cannot derive a trustworthy ban decision from the stored record.",
      ],
      exempt: [
        "Player is exempt",
        "A configured exemption ends the check before the ban action.",
      ],
      noAction: [
        "No ban action",
        "The sample state does not reach the configured ban condition.",
      ],
      configError: [
        "Ban action fails on the template",
        "The condition is met, but an unknown placeholder prevents the next step.",
      ],
      action: [
        "Ban action is triggered",
        "The sample state meets the rule and leads to the shown action with the visible values.",
      ],
    },
    risks: {
      staleData:
        "The first VAC decision uses data older than twelve hours; refresh starts in parallel.",
      unknownAge:
        "The update age is unknown. CRCON still uses the stored record for the first check.",
      profileUnavailable:
        "Without a player profile, VIP, session and flag exemptions cannot be evaluated; teamkill enforcement still continues.",
      vipLookupUnavailable:
        "The VIP list is unavailable, so a possible VIP exemption cannot be detected.",
      yearsIgnored:
        "The current backend contract does not include the years field in the teamkill-ban duration.",
      notificationTemplate:
        "The ban happens first; the Discord message can then fail because of an unknown placeholder.",
      reasonTemplate:
        "The VAC ban-reason template contains an unknown placeholder.",
      missing:
        "Without a stored record the first check remains open; a ban is possible only after a successful Steam refresh.",
      invalid:
        "An invalid Steam response causes no automatic ban and needs operational attention.",
    },
    stages: {
      storedData: {
        current: "Steam data · current stored record",
        stale: "Steam data · stored record older than 12 hours",
        unknownAge: "Steam data · update age unknown",
        missing: "Steam data · no stored record",
        invalid: "Steam data · response cannot be evaluated",
      },
      refresh: "Steam refresh · queued in the background",
      freshRecheck: "Follow-up check · possible after the background job",
      exemption: {
        flag: "Exemption · player flag protected",
        vip: "Exemption · VIP protected",
        sessions: "Exemption · enough known sessions",
        weapon: "Exemption · weapon is not counted",
      },
      history:
        "Ban history · {{days}} days · VAC {{vac}} · {{gameBans}} game bans",
      decisionAllow: "Decision · threshold not reached",
      decisionInvalid: "Decision · record cannot be evaluated",
      decisionTemplate: "Decision · ban-reason template invalid",
      profile: {
        available: "Player profile · available",
        missing: "Player profile · unavailable, exemptions uncertain",
      },
      logWindow: {
        connected: "Log window · connection found",
        missingConnect: "Log window · no connection in the latest 500 lines",
      },
      window: {
        expired: "Time window · teamkill is outside the limit",
        stoppedByKills: "Time window · check ended after own kills",
        stoppedByDeaths: "Time window · check ended after own deaths",
      },
      counter: "Tolerance · {{teamkills}} teamkills with {{tolerance}} allowed",
      actionBlacklist: "Ban · blacklist {{id}} · {{duration}}",
      actionServer: "Ban · directly on this server · {{duration}}",
      auditSend: "Audit · Discord message is sent",
      auditError: "Audit · message template can fail after the ban",
      permanent: "permanent",
      days: "{{count}} days",
      hours: "{{count}} hours",
      minutes: "{{count}} minutes",
      durationUnits: {
        weeks: ["week", "weeks"],
        days: ["day", "days"],
        hours: ["hour", "hours"],
        minutes: ["minute", "minutes"],
      },
      expiresToday: "expires today",
      vacYes: "active",
      vacNo: "not active",
    },
  },
};

const fill = (value, variables) =>
  Object.entries(variables).reduce(
    (text, [key, replacement]) =>
      text.replaceAll(`{{${key}}}`, String(replacement)),
    value
  );

const durationLabel = (simulation, copy) => {
  if (simulation.kind === "vacBans") {
    if (simulation.expiresInDays === null) return copy.stages.permanent;
    if (simulation.expiresInDays === 0) return copy.stages.expiresToday;
    return fill(copy.stages.days, { count: simulation.expiresInDays });
  }
  const explicitParts = Object.entries(simulation.duration || {})
    .filter(([, count]) => count > 0)
    .map(([unit, count]) => {
      const labels = copy.stages.durationUnits[unit];
      return `${count} ${labels[count === 1 ? 0 : 1]}`;
    });
  if (explicitParts.length) return explicitParts.join(" · ");
  const minutes = simulation.durationMinutes || 0;
  if (minutes <= 0) return copy.stages.permanent;
  if (minutes % (24 * 60) === 0) {
    return fill(copy.stages.days, { count: minutes / (24 * 60) });
  }
  if (minutes % 60 === 0) {
    return fill(copy.stages.hours, { count: minutes / 60 });
  }
  return fill(copy.stages.minutes, { count: minutes });
};

const targetLabel = (stage, simulation, copy) =>
  fill(
    stage.target?.kind === "blacklist"
      ? copy.stages.actionBlacklist
      : copy.stages.actionServer,
    {
      id: stage.target?.id ?? "–",
      duration: durationLabel(simulation, copy),
    }
  );

const formatStage = (stage, simulation, copy) => {
  switch (stage.kind) {
    case "storedData":
      return copy.stages.storedData[stage.status];
    case "refresh":
      return copy.stages.refresh;
    case "freshRecheck":
      return copy.stages.freshRecheck;
    case "exemption":
      return copy.stages.exemption[stage.status];
    case "history":
      return fill(copy.stages.history, {
        days: stage.days,
        vac: stage.vacBanned ? copy.stages.vacYes : copy.stages.vacNo,
        gameBans: stage.gameBans,
      });
    case "decision":
      return stage.status === "templateError"
        ? copy.stages.decisionTemplate
        : stage.status === "invalid"
        ? copy.stages.decisionInvalid
        : copy.stages.decisionAllow;
    case "profile":
      return copy.stages.profile[stage.status];
    case "logWindow":
      return copy.stages.logWindow[stage.status];
    case "window":
      return copy.stages.window[stage.status];
    case "counter":
      return fill(copy.stages.counter, stage);
    case "action":
      return targetLabel(stage, simulation, copy);
    case "audit":
      return stage.status === "send"
        ? copy.stages.auditSend
        : copy.stages.auditError;
    default:
      return "";
  }
};

const initialSample = (kind) =>
  kind === "vacBans"
    ? {
        dataStatus: "current",
        vacBanned: true,
        gameBans: 0,
        daysSinceLastBan: 30,
        playerFlag: "",
      }
    : {
        profileStatus: "available",
        vipLookupStatus: "available",
        isVip: false,
        sessions: 0,
        playerFlag: "",
        hasConnectEvent: true,
        weapon: "Rifle",
        minutesAfterConnect: 2,
        ownKillsBeforeEvent: 0,
        deathsBeforeEvent: 0,
        teamkillsIncludingCurrent: 3,
      };

function BooleanSelect({ id, label, value, onChange, copy }) {
  return (
    <FormControl fullWidth>
      <InputLabel id={`${id}-label`}>{label}</InputLabel>
      <Select
        labelId={`${id}-label`}
        label={label}
        value={value ? "yes" : "no"}
        onChange={(event) => onChange(event.target.value === "yes")}
      >
        <MenuItem value="yes">{copy.yes}</MenuItem>
        <MenuItem value="no">{copy.no}</MenuItem>
      </Select>
    </FormControl>
  );
}

export default function TrustRuleTestDrawer({ open, onClose, data, kind }) {
  const { i18n } = useTranslation();
  const language = i18n.language?.startsWith("de") ? "de" : "en";
  const copy = copyByLanguage[language];
  const kindCopy = copy[kind];
  const [sample, setSample] = useState(() => initialSample(kind));
  const [hasRun, setHasRun] = useState(false);
  const whitelist = data?.whitelist_players || {};
  const showVacFlag =
    Array.isArray(data?.whitelist_flags) && data.whitelist_flags.length > 0;
  const showVip = Boolean(whitelist.is_vip);
  const showSessions = Number(whitelist.has_at_least_n_sessions) > 0;
  const showTkFlag =
    Array.isArray(whitelist.has_flag) && whitelist.has_flag.length > 0;

  useEffect(() => {
    setSample(initialSample(kind));
    setHasRun(false);
  }, [kind]);

  useEffect(() => {
    setHasRun(false);
  }, [open]);

  const simulation = useMemo(
    () => simulateTrustRule(kind, data, sample),
    [data, kind, sample]
  );

  const result = useMemo(() => {
    if (!hasRun) return null;
    const [title, description] = copy.outcomes[simulation.outcome];
    const riskText = simulation.risks
      .map((risk) => copy.risks[risk])
      .filter(Boolean)
      .join(" ");
    return {
      title,
      description: `${description}${riskText ? ` ${riskText}` : ""}`,
      tone:
        simulation.outcome === "action"
          ? simulation.risks.length
            ? "warning"
            : "error"
          : simulation.outcome === "configError"
          ? "error"
          : simulation.outcome === "unavailable"
          ? "warning"
          : simulation.outcome === "noAction"
          ? simulation.risks.length
            ? "warning"
            : "success"
          : simulation.outcome === "exempt"
          ? "success"
          : "info",
      steps: simulation.stages
        .map((stage) => formatStage(stage, simulation, copy))
        .filter(Boolean),
    };
  }, [copy, hasRun, simulation]);

  const updateValue = (field, value) => {
    setHasRun(false);
    setSample((current) => ({ ...current, [field]: value }));
  };
  const update =
    (field, numeric = false) =>
    (event) =>
      updateValue(
        field,
        numeric ? Number(event.target.value) : event.target.value
      );

  return (
    <ConfigTestDrawer
      open={open}
      onClose={onClose}
      title={kindCopy.title}
      description={kindCopy.description}
      notice={kindCopy.notice}
      result={result}
      resultLabel={copy.result}
      runLabel={copy.run}
      closeLabel={copy.close}
      onRun={() => setHasRun(true)}
    >
      {kind === "vacBans" ? (
        <Stack spacing={1.5}>
          <FormControl fullWidth>
            <InputLabel id="trust-test-data-status-label">
              {kindCopy.dataStatus}
            </InputLabel>
            <Select
              labelId="trust-test-data-status-label"
              label={kindCopy.dataStatus}
              value={sample.dataStatus}
              onChange={update("dataStatus")}
            >
              {Object.entries(kindCopy.dataStatuses).map(([value, label]) => (
                <MenuItem key={value} value={value}>
                  {label}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
          {!["missing", "invalid"].includes(sample.dataStatus) && (
            <>
              <BooleanSelect
                id="trust-test-vac-banned"
                label={kindCopy.vacBanned}
                value={sample.vacBanned}
                onChange={(value) => updateValue("vacBanned", value)}
                copy={copy}
              />
              <TextField
                type="number"
                label={kindCopy.gameBans}
                value={sample.gameBans}
                onChange={update("gameBans", true)}
                inputProps={{ min: 0, step: 1 }}
              />
              <TextField
                type="number"
                label={kindCopy.daysSinceLastBan}
                value={sample.daysSinceLastBan}
                onChange={update("daysSinceLastBan", true)}
                inputProps={{ min: 0, step: 1 }}
              />
              {showVacFlag && (
                <TextField
                  label={kindCopy.playerFlag}
                  value={sample.playerFlag}
                  onChange={update("playerFlag")}
                />
              )}
            </>
          )}
        </Stack>
      ) : (
        <Stack spacing={1.5}>
          <FormControl fullWidth>
            <InputLabel id="trust-test-profile-status-label">
              {kindCopy.profileStatus}
            </InputLabel>
            <Select
              labelId="trust-test-profile-status-label"
              label={kindCopy.profileStatus}
              value={sample.profileStatus}
              onChange={update("profileStatus")}
            >
              {Object.entries(kindCopy.profileStatuses).map(
                ([value, label]) => (
                  <MenuItem key={value} value={value}>
                    {label}
                  </MenuItem>
                )
              )}
            </Select>
          </FormControl>
          {sample.profileStatus === "available" && (
            <>
              {showVip && (
                <>
                  <FormControl fullWidth>
                    <InputLabel id="trust-test-vip-status-label">
                      {kindCopy.vipLookupStatus}
                    </InputLabel>
                    <Select
                      labelId="trust-test-vip-status-label"
                      label={kindCopy.vipLookupStatus}
                      value={sample.vipLookupStatus}
                      onChange={update("vipLookupStatus")}
                    >
                      {Object.entries(kindCopy.vipLookupStatuses).map(
                        ([value, label]) => (
                          <MenuItem key={value} value={value}>
                            {label}
                          </MenuItem>
                        )
                      )}
                    </Select>
                  </FormControl>
                  <BooleanSelect
                    id="trust-test-is-vip"
                    label={kindCopy.isVip}
                    value={sample.isVip}
                    onChange={(value) => updateValue("isVip", value)}
                    copy={copy}
                  />
                </>
              )}
              {showSessions && (
                <TextField
                  type="number"
                  label={kindCopy.sessions}
                  value={sample.sessions}
                  onChange={update("sessions", true)}
                  inputProps={{ min: 0, step: 1 }}
                />
              )}
              {showTkFlag && (
                <TextField
                  label={kindCopy.playerFlag}
                  value={sample.playerFlag}
                  onChange={update("playerFlag")}
                />
              )}
            </>
          )}
          <BooleanSelect
            id="trust-test-connect-event"
            label={kindCopy.hasConnectEvent}
            value={sample.hasConnectEvent}
            onChange={(value) => updateValue("hasConnectEvent", value)}
            copy={copy}
          />
          <TextField
            label={kindCopy.weapon}
            value={sample.weapon}
            onChange={update("weapon")}
          />
          <TextField
            type="number"
            label={kindCopy.minutesAfterConnect}
            value={sample.minutesAfterConnect}
            onChange={update("minutesAfterConnect", true)}
            inputProps={{ min: 0, step: 1 }}
          />
          <TextField
            type="number"
            label={kindCopy.ownKillsBeforeEvent}
            value={sample.ownKillsBeforeEvent}
            onChange={update("ownKillsBeforeEvent", true)}
            inputProps={{ min: 0, step: 1 }}
          />
          <TextField
            type="number"
            label={kindCopy.deathsBeforeEvent}
            value={sample.deathsBeforeEvent}
            onChange={update("deathsBeforeEvent", true)}
            inputProps={{ min: 0, step: 1 }}
          />
          <TextField
            type="number"
            label={kindCopy.teamkillsIncludingCurrent}
            value={sample.teamkillsIncludingCurrent}
            onChange={update("teamkillsIncludingCurrent", true)}
            inputProps={{ min: 0, step: 1 }}
          />
        </Stack>
      )}
    </ConfigTestDrawer>
  );
}
