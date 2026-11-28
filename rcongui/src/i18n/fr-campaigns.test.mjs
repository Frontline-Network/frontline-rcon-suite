import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { campaignsFr } from "./locales/fr-campaigns.js";

test("French campaigns cover the English catalog and retain all template variables", () => {
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
  compare(en.settings.campaigns, campaignsFr, "settings.campaigns");
  assert.equal(count, 191);
  assert.match(campaignsFr.vipLifecycle.testModeHelp, /manuellement.*envoyé/);
  assert.match(campaignsFr.broadcastDisclaimer, /ne garantit pas/);
  assert.match(campaignsFr.testNow, /Envoyer/);
});
