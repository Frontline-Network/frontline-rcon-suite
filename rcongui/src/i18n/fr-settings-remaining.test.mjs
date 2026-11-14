import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { remainingSettingsFr } from "./locales/fr-settings-remaining.js";
import { otherSettingsFr } from "./locales/fr-settings-others.js";

test("French settings namespaces match English keys and preserve variables", () => {
  const values = { ...remainingSettingsFr, others: otherSettingsFr };
  const tokens = text => [...text.matchAll(/\{\{?[^{}]+\}\}?/g)].map(match => match[0]).sort();
  let count = 0;
  const compare = (english, french, path) => {
    assert.deepEqual(Object.keys(french).sort(), Object.keys(english).sort(), path);
    for (const key of Object.keys(english)) {
      const label = `${path}.${key}`;
      if (typeof english[key] === "string") {
        assert.equal(typeof french[key], "string", label);
        assert.ok(french[key].trim(), label);
        assert.deepEqual(tokens(french[key]), tokens(english[key]), label);
        count++;
      } else compare(english[key], french[key], label);
    }
  };
  for (const [key, value] of Object.entries(values)) compare(en.settings[key], value, `settings.${key}`);
  assert.equal(count, 358);
  assert.match(values.autosettings.applyAllDescription, /tous les serveurs connectés/);
  assert.match(values.welcome.disableHint, /message vide désactive/);
  assert.match(values.services.diagnostics.omitted, /Aucun journal brut/);
});
