import { useEffect, useMemo, useState } from "react";
import { Alert, Box, Card, CardContent, Checkbox, Chip, FormControlLabel, FormGroup, MenuItem, Skeleton, Stack, Switch, TextField, Typography } from "@mui/material";
import { get, execute } from "@/utils/fetchUtils";
import { useAuth } from "@/hooks/useAuth";
import { useTranslation } from "react-i18next";
import PageHeader from "@/components/shared/PageHeader";
import ConfigActionBar from "../config-form/ConfigActionBar";
import { french } from "./french.js";

const english = {
  "Mörser": "Mortar", "Hubschrauber": "Helicopter",
  "Für bestehende Einstellungen Vietnam-Trupparten bei Bedarf auswählen.": "For existing settings, select Vietnam squad types if needed.",
  "Wähle mindestens eine Squad-Truppart für die Rangliste.": "Select a squad type to generate a squad ranking.",
  "Ohne Infanterie, Panzer, Artillerie oder Aufklärung gibt es keine Squad-Rangliste.": "No squad ranking can be generated without infantry, armor, artillery or recon.", "Bitte wähle mindestens eine Statistik für die Vorschau.": "Select at least one statistic to see a preview.", "Gilt nur, wenn beide Ranglisten aktiviert sind; 5 bis 30 Sekunden.": "Applies only when both rankings are enabled; 5 to 30 seconds.",
  "Automatisierung": "Automation", "Versand": "Delivery", "Aktiv": "Active", "Pausiert": "Paused", "Nachrichtensprache unabhängig von der Sprache dieser Oberfläche.": "The message language is independent of the interface language.", "Nachrichten an Spieler": "Messages to players", "Wähle, welche Ranglisten automatisch gesendet werden.": "Choose which rankings are sent automatically.", "Eine Nachricht pro Rangliste; die Squad-Nachricht folgt nach dem eingestellten Abstand.": "One message per ranking; the squad message follows after the selected delay.", "5 bis 30 Sekunden": "5 to 30 seconds", "Die ausgewählten Trupparten werden gemeinsam gewertet.": "Selected unit types are ranked together.", "Auswahl und Gewichtung": "Selection and weighting", "Statistiken auswählen": "Choose statistics", "Wähle mindestens eine Kategorie für den automatischen Versand.": "Select at least one category for automatic delivery.", "Gewichtung kombinierter Werte": "Weighting combined scores", "Faktor von 0 bis 5": "Multiplier from 0 to 5", "Optionaler eigener Text ersetzt die übersetzte Überschrift.": "Optional custom text replaces the translated heading.", "Keine Änderungen": "No changes", "Nicht gespeicherte Änderungen": "Unsaved changes", "Einstellungen werden nur für diesen Server gespeichert.": "Settings are saved for this server only.", "Zurücksetzen": "Reset", "Wird gespeichert …": "Saving…", "Nur Ansicht": "Read only", "Du darfst diese Einstellungen ansehen, aber nicht ändern.": "You can view these settings but cannot change them.", "Bitte mindestens eine Rangliste auswählen.": "Select at least one ranking.", "Bitte mindestens eine Truppart auswählen.": "Select at least one unit type.", "Bitte mindestens eine Statistik auswählen.": "Select at least one statistic.", "Der Nachrichtenabstand muss eine ganze Zahl von 5 bis 30 sein.": "Message delay must be a whole number from 5 to 30.", "Die Faktoren müssen zwischen 0 und 5 liegen.": "Multipliers must be between 0 and 5.", "Die Überschrift muss einzeilig und höchstens 60 Zeichen lang sein.": "The heading must be one line and no more than 60 characters.", "Bitte die markierten Einstellungen prüfen.": "Review the highlighted settings.", "Beispieldaten": "Sample data", "Bis zu": "Up to", "Platzierungen": "places", "Die Vorschau verwendet Beispieldaten. Die Darstellung im Spiel kann abweichen.": "The preview uses sample data. The in-game display may differ.", "Nur verbundene Spieler zählen. Kein Chat-Befehl erforderlich.": "Only connected players are included. No chat command is required.", "Keine Rangliste ausgewählt.": "No ranking selected.", "Empfänger und Sprache": "Recipients and language", "Ranglisten und Trupparten": "Rankings and unit types", "Änderungen verwerfen": "Discard changes", "Wähle die Ranglisten und Statistiken für die automatischen Nachrichten.": "Choose the rankings and statistics for the automatic messages.", "Die Vorschau zeigt Beispielwerte für die gewählte Anzahl an Platzierungen.": "The preview shows sample values for the selected number of places.", "Nachrichtentext": "Message text", "Spieler und Squads werden nacheinander gesendet.": "Player and squad messages are sent in sequence.",
  "Match-Statistiken": "Match statistics", "Sende die besten Leistungen nach einem regulären Match automatisch als Admin-Nachricht an alle Spieler.": "Automatically send the top performances to all players as an admin message at the end of a regular match.",
  "Automatisch am Matchende senden": "Send automatically at match end", "Sprache der Nachricht": "Message language", "Ranglisten": "Rankings", "Spieler": "Players", "Platzierungen je Kategorie": "Places per category", "Trupparten": "Unit types", "Infanterie": "Infantry", "Panzer": "Armor", "Artillerie": "Artillery", "Aufklärung": "Recon", "Angezeigte Statistiken": "Statistics to display", "Zerstörte Fahrzeuge": "Vehicles destroyed", "Angriff / Verteidigung": "Offense / defense", "Kill-/Death-Verhältnis": "Kill/death ratio", "Kills pro Minute": "Kills per minute", "Support-Faktor für Teamplay": "Support multiplier for teamplay", "Kampf + Support × Faktor": "Combat + support × multiplier", "Verteidigungsfaktor": "Defense multiplier", "Angriff + Verteidigung × Faktor": "Offense + defense × multiplier", "Eigene Überschrift (optional)": "Custom heading (optional)", "Speichern": "Save", "Nachrichtenvorschau": "Message preview", "Beispielwerte – die tatsächliche Darstellung kann auf der Konsole abweichen.": "Example values; the actual display may differ on console.", "Automatischer Versand deaktiviert": "Automatic sending disabled", "Die Vorschau zeigt je Kategorie ein Beispiel. Die Anzahl der Platzierungen gilt für die tatsächliche Nachricht.": "The preview shows one example per category. The selected number of places applies to the actual message.", "Spieler benötigen keinen Chat-Befehl. Gewertet werden Spieler, die zum Matchende verbunden sind.": "Players do not need a chat command. Only players connected at match end are included.", "Speichern fehlgeschlagen": "Could not save settings", "Einstellungen gespeichert.": "Settings saved.", "Abstand zwischen Nachrichten (Sekunden)": "Delay between messages (seconds)", "Spieler und Squads werden als getrennte Nachrichten gesendet.": "Players and squads are sent as separate messages.", "Spieler-Nachricht": "Player message", "Squad-Nachricht": "Squad message"
};

const languages = {
  en: ["English", "MATCH TOP PLAYERS", "Kills", "Defense", "Support", "Combat", "Offense", "Vehicles destroyed"],
  de: ["Deutsch", "BESTE SPIELER DER RUNDE", "Kills", "Verteidigung", "Unterstützung", "Kampf", "Angriff", "Fahrzeuge zerstört"],
  fr: ["Français", "MEILLEURS JOUEURS", "Éliminations", "Défense", "Soutien", "Combat", "Attaque", "Véhicules détruits"],
  es: ["Español", "MEJORES JUGADORES", "Bajas", "Defensa", "Apoyo", "Combate", "Ataque", "Vehículos destruidos"],
  ru: ["Русский", "ЛУЧШИЕ ИГРОКИ", "Убийства", "Защита", "Поддержка", "Бой", "Атака", "Уничтожено техники"],
  pt: ["Português (Brasil)", "MELHORES JOGADORES", "Abates", "Defesa", "Apoio", "Combate", "Ataque", "Veículos destruídos"],
  pl: ["Polski", "NAJLEPSI GRACZE", "Zabójstwa", "Obrona", "Wsparcie", "Walka", "Atak", "Zniszczone pojazdy"],
  zh: ["中文", "本局最佳玩家", "击杀", "防御", "支援", "战斗", "进攻", "摧毁载具"],
};
const stats = [["kills", "Kills", 42], ["defense", "Defense", 3200], ["support", "Support", 2150], ["combat", "Combat", 1800], ["offense", "Offense", 2300], ["vehicles_destroyed", "Zerstörte Fahrzeuge", 4]];
const extra = {
  en: ["Teamplay", "Offense/Defense", "K/D", "Kills/min", "TOP SQUADS"],
  de: ["Teamspiel", "Angriff/Verteidigung", "K/D", "Kills/Min", "BESTE SQUADS"],
  fr: ["Jeu d'équipe", "Attaque/Défense", "É/M", "Élim./min", "MEILLEURES ESCOUADES"],
  es: ["Juego en equipo", "Ataque/Defensa", "B/M", "Bajas/min", "MEJORES ESCUADRAS"],
  ru: ["Командная игра", "Атака/Защита", "У/С", "Убийств/мин", "ЛУЧШИЕ ОТРЯДЫ"],
  pt: ["Trabalho em equipe", "Ataque/Defesa", "A/M", "Abates/min", "MELHORES ESQUADRÕES"],
  pl: ["Gra zespołowa", "Atak/Obrona", "Z/Ś", "Zabójstwa/min", "NAJLEPSZE DRUŻYNY"],
  zh: ["团队配合", "进攻/防御", "击杀/死亡", "击杀/分钟", "最佳小队"],
};
stats.push(["teamplay", "Teamplay", 2800], ["offdef", "Angriff / Verteidigung", 4200], ["kd", "Kill-/Death-Verhältnis", 2.5], ["kpm", "Kills pro Minute", 1.2]);
const units = [["commander", "Commander"], ["infantry", "Infanterie"], ["armor", "Panzer"], ["artillery", "Artillerie"], ["recon", "Aufklärung"], ["mortar", "Mörser"], ["helicopter", "Hubschrauber"]];

async function result(response) {
  const data = await response.json();
  if (data.failed || data.error) throw new Error(typeof data.error === "string" ? data.error : JSON.stringify(data.error));
  return data.result;
}

const numericFields = ["message_gap_seconds", "support_multiplier", "defense_multiplier"];
const asDraft = (config) => ({ ...config, ...Object.fromEntries(numericFields.map((key) => [key, String(config[key])])) });
const asPayload = (config) => ({ ...config, ...Object.fromEntries(numericFields.map((key) => [key, Number(config[key])])) });
const choicesGrid = { display: "grid", gridTemplateColumns: { xs: "1fr", sm: "repeat(2, minmax(0, 1fr))" }, gap: { xs: 0, sm: "0 16px" } };

function Section({ title, description, children }) {
  return <Card variant="outlined"><CardContent sx={{ p: { xs: 2, md: 2.5 }, "&:last-child": { pb: { xs: 2, md: 2.5 } } }}>
    <Typography component="h2" variant="h6">{title}</Typography>
    {description && <Typography variant="body2" color="text.secondary" sx={{ mt: 0.5 }}>{description}</Typography>}
    <Stack spacing={2} sx={{ mt: 2 }}>{children}</Stack>
  </CardContent></Card>;
}

export default function EndMatchStats() {
  const { i18n } = useTranslation();
  const language = (i18n.resolvedLanguage || i18n.language || "de").split("-")[0];
  const tr = (value) => language === "fr" ? (french[value] || english[value] || value) : language === "en" ? (english[value] || value) : value;
  const { permissions } = useAuth();
  const canEdit = permissions?.is_superuser || permissions?.permissions?.some((p) => p.permission === "can_change_auto_broadcast_config");
  const [config, setConfig] = useState(null);
  const [saved, setSaved] = useState(null);
  const [error, setError] = useState("");
  const [notice, setNotice] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => {
    let active = true;
    get("get_end_match_stats_config").then(result).then((data) => {
      if (active) { const draft = asDraft(data); setConfig(draft); setSaved(draft); }
    }).catch((e) => { if (active) setError(e.message); });
    return () => { active = false; };
  }, []);
  const dirty = !!config && !!saved && JSON.stringify(config) !== JSON.stringify(saved);
  const issues = useMemo(() => {
    if (!config) return [];
    const failures = [];
    if (config.enabled && !config.include_players && !config.include_squads) failures.push("Bitte mindestens eine Rangliste auswählen.");
    if (!config.unit_types.length) failures.push("Bitte mindestens eine Truppart auswählen.");
    if (config.enabled && !stats.some(([key]) => config[key])) failures.push("Bitte mindestens eine Statistik auswählen.");
    const gap = Number(config.message_gap_seconds);
    if (!config.message_gap_seconds.trim() || !Number.isInteger(gap) || gap < 5 || gap > 30) failures.push("Der Nachrichtenabstand muss eine ganze Zahl von 5 bis 30 sein.");
    if ([config.support_multiplier, config.defense_multiplier].some((value) => !value.trim() || !Number.isFinite(Number(value)) || Number(value) < 0 || Number(value) > 5)) failures.push("Die Faktoren müssen zwischen 0 und 5 liegen.");
    if (config.title.length > 60 || /[\r\n]/.test(config.title)) failures.push("Die Überschrift muss einzeilig und höchstens 60 Zeichen lang sein.");
    return failures;
  }, [config]);
  const change = (key, value) => { setConfig((c) => ({ ...c, [key]: value })); setNotice(""); setError(""); };
  async function save() {
    if (!config || issues.length || busy) return;
    setBusy(true); setError(""); setNotice("");
    try {
      const payload = asPayload(config);
      for (const command of ["validate_end_match_stats_config", "set_end_match_stats_config"]) {
        if (await result(await execute(command, { config: payload })) !== true) throw new Error(tr("Speichern fehlgeschlagen"));
      }
      const fresh = asDraft(await result(await get("get_end_match_stats_config")));
      setConfig(fresh); setSaved(fresh); setNotice("Einstellungen gespeichert.");
    } catch (e) { setError(e.message); } finally { setBusy(false); }
  }
  const labelFor = (i) => i < 6 ? languages[config.language][i + 2] : extra[config.language][i - 6];
  const previewLines = (squad = false) => stats.flatMap(([key, , value], i) => {
    if (!config[key]) return [];
    const names = squad ? ["Able (allies)", "Baker (axis)", "Charlie (allies)"] : ["Player 1", "Player 2", "Player 3"];
    const rawMultiplier = key === "teamplay" ? config.support_multiplier : config.defense_multiplier;
    const multiplier = Number(rawMultiplier);
    if ((key === "teamplay" || key === "offdef") && (!rawMultiplier.trim() || !Number.isFinite(multiplier) || multiplier < 0 || multiplier > 5)) return [`${labelFor(i)}: —`];
    const base = key === "teamplay" ? 1800 + 2150 * multiplier : key === "offdef" ? 2300 + 3200 * multiplier : value;
    const entries = names.slice(0, config.top_count).map((name, rank) => {
      const sample = base * [1, 0.8, 0.6][rank];
      return `${name} (${key === "kd" || key === "kpm" ? Number(sample.toFixed(2)) : Math.round(sample)})`;
    });
    return [`${labelFor(i)}: ${entries.join(", ")}`];
  });
  const disabled = !canEdit || busy;
  return <Stack spacing={2} sx={{ maxWidth: 1440, mx: "auto", px: { xs: 1, md: 2 }, pb: 3 }}>
    <PageHeader eyebrow={tr("Automatisierung")} title={tr("Match-Statistiken")} subtitle={tr("Sende die besten Leistungen nach einem regulären Match automatisch als Admin-Nachricht an alle Spieler.")} actions={config && <Chip size="small" color={config.enabled ? "success" : "default"} label={tr(config.enabled ? "Aktiv" : "Pausiert")} />} />
    {error && <Alert severity="error" role="alert">{error}</Alert>}{notice && <Alert severity="success" role="status">{tr(notice)}</Alert>}
    {!config && !error && <><Skeleton variant="rounded" height={160} /><Skeleton variant="rounded" height={240} /></>}
    {config && <>
      {!canEdit && <Alert severity="info">{tr("Du darfst diese Einstellungen ansehen, aber nicht ändern.")}</Alert>}
      <Box sx={{ display: "grid", gridTemplateColumns: { xs: "minmax(0, 1fr)", lg: "minmax(0, 1.15fr) minmax(340px, 0.85fr)" }, gap: 2, alignItems: "start" }}>
        <Stack spacing={2}>
          <Section title={tr("Versand")} description={tr("Nachrichtensprache unabhängig von der Sprache dieser Oberfläche.")}>
            <FormControlLabel control={<Switch checked={config.enabled} disabled={disabled} onChange={(e) => change("enabled", e.target.checked)} />} label={tr("Automatisch am Matchende senden")} />
            <TextField select label={tr("Sprache der Nachricht")} value={config.language} disabled={disabled} onChange={(e) => change("language", e.target.value)} fullWidth>{Object.entries(languages).map(([key, value]) => <MenuItem key={key} value={key}>{value[0]}</MenuItem>)}</TextField>
            <TextField label={tr("Eigene Überschrift (optional)")} value={config.title} placeholder={languages[config.language][1]} disabled={disabled} inputProps={{ maxLength: 60 }} onChange={(e) => change("title", e.target.value)} helperText={tr("Optionaler eigener Text ersetzt die übersetzte Überschrift.")} fullWidth />
          </Section>
          <Section title={tr("Ranglisten und Trupparten")} description={tr("Wähle, welche Ranglisten automatisch gesendet werden.")}>
            <FormGroup sx={choicesGrid}>
              <FormControlLabel control={<Checkbox checked={config.include_players} disabled={disabled} onChange={(e) => change("include_players", e.target.checked)} />} label={tr("Spieler")} />
              <FormControlLabel control={<Checkbox checked={config.include_squads} disabled={disabled} onChange={(e) => change("include_squads", e.target.checked)} />} label={tr("Squads")} />
            </FormGroup>
            {issues.includes("Bitte mindestens eine Rangliste auswählen.") && <Alert severity="warning">{tr("Bitte mindestens eine Rangliste auswählen.")}</Alert>}
            {config.include_squads && !config.unit_types.some((unit) => unit !== "commander") && <Alert severity="warning">{tr("Wähle mindestens eine Squad-Truppart für die Rangliste.")}</Alert>}
            <Typography variant="body2" color="text.secondary">{tr("Eine Nachricht pro Rangliste; die Squad-Nachricht folgt nach dem eingestellten Abstand.")}</Typography>
            <Box sx={choicesGrid}>
              <TextField select label={tr("Platzierungen je Kategorie")} value={config.top_count} disabled={disabled} onChange={(e) => change("top_count", Number(e.target.value))} fullWidth>{[1, 2, 3].map((n) => <MenuItem key={n} value={n}>Top {n}</MenuItem>)}</TextField>
              <TextField type="number" label={tr("Abstand zwischen Nachrichten (Sekunden)")} value={config.message_gap_seconds} disabled={disabled} error={issues.includes("Der Nachrichtenabstand muss eine ganze Zahl von 5 bis 30 sein.")} inputProps={{ min: 5, max: 30, step: 1 }} onChange={(e) => change("message_gap_seconds", e.target.value)} helperText={tr("Gilt nur, wenn beide Ranglisten aktiviert sind; 5 bis 30 Sekunden.")} fullWidth />
            </Box>
            <Box><Typography component="h3" variant="subtitle1">{tr("Trupparten")}</Typography><Typography variant="body2" color="text.secondary">{tr("Die ausgewählten Trupparten werden gemeinsam gewertet.")}</Typography>
              <Typography variant="body2" color="text.secondary">{tr("Für bestehende Einstellungen Vietnam-Trupparten bei Bedarf auswählen.")}</Typography>
              <FormGroup sx={{ ...choicesGrid, mt: 0.5 }}>{units.map(([key, label]) => <FormControlLabel key={key} control={<Checkbox checked={config.unit_types.includes(key)} disabled={disabled} onChange={(e) => change("unit_types", e.target.checked ? [...config.unit_types, key] : config.unit_types.filter((v) => v !== key))} />} label={tr(label)} />)}</FormGroup>
              {issues.includes("Bitte mindestens eine Truppart auswählen.") && <Alert severity="warning">{tr("Bitte mindestens eine Truppart auswählen.")}</Alert>}
            </Box>
          </Section>
          <Section title={tr("Angezeigte Statistiken")} description={tr("Wähle mindestens eine Kategorie für den automatischen Versand.")}>
            <FormGroup sx={choicesGrid}>{stats.map(([key, label]) => <FormControlLabel key={key} control={<Checkbox checked={config[key]} disabled={disabled} onChange={(e) => change(key, e.target.checked)} />} label={tr(label)} />)}</FormGroup>
            {issues.includes("Bitte mindestens eine Statistik auswählen.") && <Alert severity="warning">{tr("Bitte mindestens eine Statistik auswählen.")}</Alert>}
            <Box><Typography component="h3" variant="subtitle1">{tr("Gewichtung kombinierter Werte")}</Typography><Typography variant="body2" color="text.secondary">{tr("Faktor von 0 bis 5")}</Typography></Box>
            <Box sx={choicesGrid}>
              <TextField type="number" label={tr("Support-Faktor für Teamplay")} value={config.support_multiplier} disabled={disabled} error={issues.includes("Die Faktoren müssen zwischen 0 und 5 liegen.")} inputProps={{ min: 0, max: 5, step: 0.1 }} onChange={(e) => change("support_multiplier", e.target.value)} helperText={tr("Kampf + Support × Faktor")} fullWidth />
              <TextField type="number" label={tr("Verteidigungsfaktor")} value={config.defense_multiplier} disabled={disabled} error={issues.includes("Die Faktoren müssen zwischen 0 und 5 liegen.")} inputProps={{ min: 0, max: 5, step: 0.1 }} onChange={(e) => change("defense_multiplier", e.target.value)} helperText={tr("Angriff + Verteidigung × Faktor")} fullWidth />
            </Box>
          </Section>
        </Stack>
        <Box sx={{ position: { xs: "static", lg: "sticky" }, top: { lg: 16 }, minWidth: 0 }}>
          <Section title={tr("Nachrichtenvorschau")} description={tr("Die Vorschau verwendet Beispieldaten. Die Darstellung im Spiel kann abweichen.")}>
            <Stack direction="row" spacing={1} useFlexGap flexWrap="wrap"><Chip size="small" label={tr("Beispieldaten")} /><Chip size="small" variant="outlined" label={`${tr("Bis zu")} ${config.top_count} ${tr("Platzierungen")}`} /></Stack>
            {!config.enabled && <Alert severity="info">{tr("Automatischer Versand deaktiviert")}</Alert>}
            {config.enabled && !config.include_players && !config.include_squads && <Alert severity="warning">{tr("Keine Rangliste ausgewählt.")}</Alert>}
            {config.enabled && !stats.some(([key]) => config[key]) && <Alert severity="warning">{tr("Bitte wähle mindestens eine Statistik für die Vorschau.")}</Alert>}
            {config.enabled && stats.some(([key]) => config[key]) && [[config.include_players, "Spieler-Nachricht", config.title.trim() || languages[config.language][1], false], [config.include_squads, "Squad-Nachricht", extra[config.language][4], true]].map(([enabled, label, heading, squad]) => enabled && <Box key={label}>
              <Typography component="h3" variant="subtitle2">{tr(label)}</Typography>
              <Box component="pre" sx={{ whiteSpace: "pre-wrap", overflowWrap: "anywhere", bgcolor: "action.hover", p: 2, mt: 1, mb: 0, borderRadius: 1, fontFamily: "inherit", fontSize: "body2.fontSize", lineHeight: 1.6 }}>{[heading, ...previewLines(squad)].join("\n")}</Box>
            </Box>)}
            <Typography variant="body2" color="text.secondary">{tr("Nur verbundene Spieler zählen. Kein Chat-Befehl erforderlich.")}</Typography>
          </Section>
        </Box>
      </Box>
      {issues.length > 0 && <Alert severity="warning" role="alert"><Typography variant="body2">{tr("Bitte die markierten Einstellungen prüfen.")}</Typography><Box component="ul" sx={{ my: 0.5, pl: 2 }}>{issues.map((issue) => <li key={issue}>{tr(issue)}</li>)}</Box></Alert>}
      <ConfigActionBar dirty={dirty} dirtyLabel={tr("Nicht gespeicherte Änderungen")} stateLabel={tr(dirty ? "Nicht gespeicherte Änderungen" : "Keine Änderungen")} stateDescription={tr("Einstellungen werden nur für diesen Server gespeichert.")} primaryAction={{ label: tr("Speichern"), loadingLabel: tr("Wird gespeichert …"), loading: busy, disabled: disabled || !dirty || issues.length > 0, onClick: save }} secondaryActions={[{ label: tr("Zurücksetzen"), disabled: disabled || !dirty, onClick: () => { setConfig(saved); setError(""); setNotice(""); } }]} />
    </>}
  </Stack>;
}
