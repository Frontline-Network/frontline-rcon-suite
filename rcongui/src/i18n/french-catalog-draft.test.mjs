import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import en from "./locales/en.js";
import { settingsPanelsEn } from "./locales/settings-panels.js";

// Execute the production composition itself, not a hand-built approximation.
// Node requires a JSON import attribute whereas Vite accepts the application's
// JSON import, so inline only that import and resolve the unchanged JS modules.
const localeUrl = new URL("./locales/fr.js", import.meta.url);
const draft = readFileSync(new URL("./locales/fr-draft.json", import.meta.url), "utf8");
let localeSource = readFileSync(localeUrl, "utf8");
const jsonImport = 'import draft from "./fr-draft.json";';
assert.ok(localeSource.includes(jsonImport), "Update the test when the production JSON import changes");
localeSource = localeSource.replace(jsonImport, `const draft = ${draft};`);
localeSource = localeSource.replace(/from\s+"(\.\/[^\"]+\.js)"/g, (_, path) => `from "${new URL(path, localeUrl).href}"`);
const { default: fr } = await import(`data:text/javascript;base64,${Buffer.from(localeSource).toString("base64")}`);
const panels = JSON.parse(readFileSync(new URL("./locales/fr-settings-panels-draft.json", import.meta.url), "utf8"));

function verify(source, target, path) {
  if (typeof source === "string") {
    assert.equal(typeof target, "string", path);
    assert.ok(target.trim(), path);
    const tokens = (s) => [...s.matchAll(/{{\s*([^{}]+)\s*}}/g)].map((m) => m[1].trim()).sort();
    assert.deepEqual(tokens(target), tokens(source), path);
    const templateMarkers = (s) => [...s.matchAll(/(?<!\{)\{([A-Za-z_][A-Za-z_0-9]*)\}(?!\})|<([A-Z_][A-Z_0-9]*)>/g)].map((m) => m[0]).sort();
    assert.deepEqual(templateMarkers(target), templateMarkers(source), `${path}: game message markers`);
    assert.doesNotMatch(target, /&(?:apos|amp|quot|lt|gt);/, path);
  } else if (source && typeof source === "object") {
    assert.equal(typeof target, "object", path);
    assert.notEqual(target, null, path);
    for (const key of Object.keys(source)) verify(source[key], target[key], `${path}.${key}`);
  }
}

test("the effective French catalog and lazy panels cover English and preserve interpolation", () => {
  verify(en, fr, "main");
  verify(settingsPanelsEn, panels, "settingsPanels");
});

test("the shipped locale explicitly registers French and lazy panels", () => {
  const index = readFileSync(new URL("./index.js", import.meta.url), "utf8");
  const register = readFileSync(new URL("./register-settings-panels.js", import.meta.url), "utf8");
  const selector = readFileSync(new URL("../components/layout/LanguageSelector.jsx", import.meta.url), "utf8");
  assert.match(index, /supportedLanguages\s*=\s*\[[^\]]*["']fr["']/);
  assert.match(index, /import\(["']\.\/locales\/fr["']\)/);
  assert.match(index, /addResourceBundle\(["']fr["'],\s*["']translation["'],\s*fr/);
  assert.match(index, /initialLanguage\s*===\s*["']fr["']/);
  assert.match(selector, /await\s+ensureLanguageLoaded\(code\)/);
  assert.match(register, /fr\s*:\s*settingsPanelsFr/);
  assert.match(register, /addResourceBundle\(language,\s*["']translation["'],\s*\{\s*settingsPanels\s*\}/);
  assert.match(selector, /code\s*:\s*["']fr["']/);
});
