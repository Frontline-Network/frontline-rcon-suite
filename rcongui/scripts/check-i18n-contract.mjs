import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { parse } from "@babel/parser";
import en from "../src/i18n/locales/en.js";
import de from "../src/i18n/locales/de.js";
import { settingsPanelsDe, settingsPanelsEn } from "../src/i18n/locales/settings-panels.js";
import { seedVipJournalCopy } from "../src/i18n/locales/seed-vip-journal.js";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const failures = [];
const stats = { sourceFiles: 0, bilingualObjects: 0, staticReferences: 0 };
const flatten = (value, prefix = "") => Object.fromEntries(Object.entries(value).flatMap(([key, item]) => item && typeof item === "object" ? Object.entries(flatten(item, `${prefix}${key}.`)) : [[prefix + key, item]]));
const variables = (text) => [...String(text).matchAll(/\{\{\s*-?\s*([\w.]+)(?:\s*,[^}]*)?\s*\}\}|(?<!\{)\{(\w+)\}(?!\})/g)].map((match) => match[1] || match[2]).sort();
function compare(label, german, english) {
  const a = flatten(german), b = flatten(english);
  for (const key of new Set([...Object.keys(a), ...Object.keys(b)])) {
    if (!Object.hasOwn(a, key) || !Object.hasOwn(b, key)) failures.push(`${label}: missing ${Object.hasOwn(a, key) ? "English" : "German"} key ${key}`);
    else if (typeof a[key] !== typeof b[key]) failures.push(`${label}: mismatched value type ${key}`);
    else if (typeof a[key] === "string") {
      if (!a[key].trim() || !b[key].trim()) failures.push(`${label}: empty translation ${key}`);
      if (JSON.stringify(variables(a[key])) !== JSON.stringify(variables(b[key]))) failures.push(`${label}: interpolation mismatch ${key}`);
    }
  }
}
compare("main catalogs", de, en);
compare("lazy settings catalogs", settingsPanelsDe, settingsPanelsEn);
compare("seed VIP journal", seedVipJournalCopy.de, seedVipJournalCopy.en);
compare("seed VIP journal French", seedVipJournalCopy.fr, seedVipJournalCopy.en);
const combinedEnglish = { ...en, settingsPanels: settingsPanelsEn, seedVipJournal: seedVipJournalCopy.en };
const globalKeys = new Set(Object.keys(flatten(combinedEnglish)));
const syntaxTrees = new Map();
const bilingualByDirectory = new Map();
const keyName = (property) => property.key?.name ?? property.key?.value;
const literalValue = (node) => {
  if (!node) return undefined;
  if (["StringLiteral", "NumericLiteral", "BooleanLiteral"].includes(node.type)) return node.value;
  if (node.type === "NullLiteral") return null;
  if (node.type === "ArrayExpression") return node.elements.map(literalValue);
  if (node.type === "ObjectExpression") return Object.fromEntries(node.properties.filter((item) => item.type === "ObjectProperty" && keyName(item) !== undefined).map((item) => [keyName(item), literalValue(item.value)]));
  // Local copy helpers may contain interpolation functions. Compare their
  // argument counts without executing any application code in the audit.
  if (["ArrowFunctionExpression", "FunctionExpression"].includes(node.type)) return `[function:${node.params.length}]`;
  return "[dynamic]";
};
function walk(node, visitor, ancestors = []) {
  if (!node || typeof node !== "object") return;
  visitor(node, ancestors);
  for (const [key, value] of Object.entries(node)) {
    if (["loc", "start", "end", "extra", "comments", "leadingComments", "trailingComments", "innerComments"].includes(key)) continue;
    if (Array.isArray(value)) value.forEach((item) => walk(item, visitor, [...ancestors, node]));
    else if (value && typeof value === "object") walk(value, visitor, [...ancestors, node]);
  }
}
function collect(directory) {
  for (const item of fs.readdirSync(directory, { withFileTypes: true })) {
    const filename = path.join(directory, item.name);
    if (item.isDirectory()) collect(filename);
    else if (/\.(jsx?|mjs)$/.test(filename) && !/\.test\./.test(filename) && !filename.includes(`${path.sep}mirage${path.sep}`)) {
      const relative = path.relative(root, filename).replaceAll("\\", "/");
      const tree = parse(fs.readFileSync(filename, "utf8"), { sourceType: "unambiguous", plugins: ["jsx"] });
      syntaxTrees.set(relative, tree);
      stats.sourceFiles++;
      walk(tree, (node) => {
        if (node.type !== "ObjectExpression") return;
        const german = node.properties.find((prop) => keyName(prop) === "de")?.value;
        const english = node.properties.find((prop) => keyName(prop) === "en")?.value;
        if (german?.type === "ObjectExpression" && english?.type === "ObjectExpression") {
          stats.bilingualObjects++;
          const germanCopy = literalValue(german), englishCopy = literalValue(english);
          compare(`${relative}:${node.loc.start.line}`, germanCopy, englishCopy);
          const directoryKeys = bilingualByDirectory.get(path.posix.dirname(relative)) || new Set();
          Object.keys(flatten(englishCopy)).forEach((key) => directoryKeys.add(key));
          bilingualByDirectory.set(path.posix.dirname(relative), directoryKeys);
          if (relative === "src/pages/settings/maps/workbench-translations.js") Object.keys(flatten(englishCopy)).forEach((key) => globalKeys.add(`maps.${key}`));
        }
        if (relative.startsWith("src/i18n/locales/")) {
          const seen = new Set();
          for (const prop of node.properties) {
            const key = keyName(prop);
            if (key === undefined) continue;
            if (seen.has(key)) failures.push(`${relative}:${prop.loc.start.line}: duplicate translation property ${key}`);
            seen.add(key);
          }
        }
      });
    }
  }
}
collect(path.join(root, "src"));
const germanWords = /[äöüÄÖÜß]|\b(?:nicht|Kein|Keine|keine|Spieler|Spielern|Abstimmung|Einstellungen|werden|Speichern|Abbrechen|Verbindung|Fehler|anzeigen|auswählen|gelöscht|erfolgreich|zulässig|verfügbar|Bestätigung|Berechtigung)\b/;
for (const [filename, tree] of syntaxTrees) {
  if (filename.startsWith("src/i18n/") || /\/demo\.js$/.test(filename)) continue;
  const source = fs.readFileSync(path.join(root, filename), "utf8");
  if (source.includes("settingsPanels.") && !source.includes('import "@/i18n/register-settings-panels"')) {
    failures.push(`${filename}: lazy settings translations must be registered before rendering`);
  }
  const localKeys = bilingualByDirectory.get(path.posix.dirname(filename)) || new Set();
  walk(tree, (node, ancestors) => {
    if (node.type === "CallExpression" && (node.callee?.name === "t" || (node.callee?.type === "MemberExpression" && node.callee.property?.name === "t"))) {
      const argument = node.arguments[0];
      const key = argument?.type === "StringLiteral" ? argument.value : argument?.type === "TemplateLiteral" && !argument.expressions.length ? argument.quasis[0].value.cooked : null;
      if (key) {
        stats.staticReferences++;
        if (![key, `${key}_one`, `${key}_other`].some((candidate) => globalKeys.has(candidate) || localKeys.has(candidate))) failures.push(`${filename}:${node.loc.start.line}: unknown translation key ${key}`);
      }
    }
    const directText = node.type === "JSXText" ? node.value : node.type === "StringLiteral" && ancestors.at(-1)?.type === "JSXAttribute" ? node.value : null;
    // This narrow source guard supplements the complete dictionary/reference
    // audit and real English browser checks; it never guesses at user content.
    if (directText && germanWords.test(directText)) failures.push(`${filename}:${node.loc.start.line}: untranslated JSX copy ${JSON.stringify(directText.trim())}`);
  });
}
// The public statistics UI has a separate lazy-loaded English base catalog.
const publicLocales = path.resolve(root, "../rcongui_public/src/i18n/locales");
for (const name of fs.readdirSync(path.join(publicLocales, "en"))) {
  const english = flatten(JSON.parse(fs.readFileSync(path.join(publicLocales, "en", name), "utf8")));
  const germanFile = path.join(publicLocales, "de", name);
  if (!fs.existsSync(germanFile)) continue;
  const german = flatten(JSON.parse(fs.readFileSync(germanFile, "utf8")));
  for (const [key, value] of Object.entries(german)) {
    if (!Object.hasOwn(english, key)) failures.push(`public/${name}: missing English key ${key}`);
    else if (JSON.stringify(variables(value)) !== JSON.stringify(variables(english[key]))) failures.push(`public/${name}: interpolation mismatch ${key}`);
  }
}
assert.equal(failures.length, 0, `English completeness contract failed:\n${failures.join("\n")}`);
console.log(`English completeness: ${Object.keys(flatten(combinedEnglish)).length} catalog keys (including lazy settings); ${stats.sourceFiles} source files; ${stats.bilingualObjects} local DE/EN objects; ${stats.staticReferences} static references; public English catalogs verified.`);
