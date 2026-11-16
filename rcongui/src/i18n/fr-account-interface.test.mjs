import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { accountInterfaceFr } from "./locales/fr-account-interface.js";

test("French account and interface copy matches English keys and variables", () => {
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
  for (const key of Object.keys(accountInterfaceFr)) compare(en[key], accountInterfaceFr[key], key);
  assert.equal(count, 179);
  assert.match(accountInterfaceFr.accountPassword.sent, /Si un compte actif/);
  assert.match(accountInterfaceFr.accountPassword.saveFailed, /connexion a été interrompue/);
  assert.match(accountInterfaceFr.updates.preview, /ne confirment aucun déploiement réel/);
});
