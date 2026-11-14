// Heuristics for prioritizing human review; passing them does not prove a translation correct.
import en from "../src/i18n/locales/en.js";
import { settingsPanelsEn } from "../src/i18n/locales/settings-panels.js";
import { readFileSync } from "node:fs";

const main = JSON.parse(readFileSync(new URL("../src/i18n/locales/fr-draft.json", import.meta.url), "utf8"));
const panels = JSON.parse(readFileSync(new URL("../src/i18n/locales/fr-settings-panels-draft.json", import.meta.url), "utf8"));
const findings = [];
const rules = [
  [/team\s*kill/i, /compétence|aptitude/i, "teamkill translated as skill"],
  [/\bkick(?:ed|ing)?\b/i, /coup de pied|frapp[ée]|pété/i, "kick translated literally"],
  [/\bsquad/i, /escadron|escadrille/i, "squad translated as air squadron"],
  [/\bswitch/i, /interrupteur|commutateur|commutation/i, "switch translated as electrical device"],
  [/\b(?:remov|delet)/i, /enlèvement/i, "removal translated as abduction"],
  [/\b(?:pool|connection)/i, /piscine/i, "connection pool translated as swimming pool"],
  [/\b(?:cooldown)/i, /refroidissement/i, "cooldown translated as physical cooling"],
  [/\b(?:disable|disabled|disabling)/i, /handicap[ée]/i, "disabled translated as disability"],
  [/\bplayers?\b/i, /lecteurs?|lectrices?/i, "player translated as reader"],
  [/\bpoll(?:ing)?\b/i, /\b(?:vote|votes|votation|sondage)/i, "polling translated as voting"],
  [/\blog\s+only\b/i, /connectez|connexion/i, "log translated as login"],
];
function walk(source, translated, path) {
  if (typeof source === "string") {
    if (typeof translated !== "string") { findings.push({ path, issue: "missing translation", source }); return; }
    const tokens = (text) => [...text.matchAll(/{{\s*([^{}]+)\s*}}/g)].map((m) => m[1]).sort().join("|");
    if (tokens(source) !== tokens(translated)) findings.push({ path, issue: "interpolation mismatch", source, translated });
    if (/&(?:apos|amp|quot|lt|gt);/.test(translated) && !/&(?:apos|amp|quot|lt|gt);/.test(source)) findings.push({ path, issue: "unexpected HTML entity", source, translated });
    for (const [sourcePattern, targetPattern, issue] of rules) {
      // A boolean switch is a UI toggle; "commutateur" is correct there.
      if (issue === "switch translated as electrical device" && /boolean/i.test(source)) continue;
      if (sourcePattern.test(source) && targetPattern.test(translated)) findings.push({ path, issue, source, translated });
    }
    if (source.length > 65 && translated.length < source.length * 0.48) findings.push({ path, issue: "possible omitted content", source, translated });
    return;
  }
  if (source && typeof source === "object") for (const [key, value] of Object.entries(source)) walk(value, translated?.[key], `${path}.${key}`);
}
walk(en, main, "main");
walk(settingsPanelsEn, panels, "settingsPanels");
process.stdout.write(JSON.stringify({ count: findings.length, findings }, null, 2) + "\n");
if (findings.length) process.exitCode = 1;
