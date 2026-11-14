import test from "node:test";
import assert from "node:assert/strict";
import { editAccountCopy, accountCopy } from "./edit-account-copy.js";

test("account editor has complete French and German labels with regional selection", () => {
  for (const language of ["de", "fr"]) {
    assert.deepEqual(Object.keys(editAccountCopy[language]).sort(), Object.keys(editAccountCopy.en).sort());
    for (const value of Object.values(editAccountCopy[language])) assert.ok(value.trim());
  }
  assert.equal(accountCopy("fr-FR"), editAccountCopy.fr);
  assert.equal(accountCopy("unknown"), editAccountCopy.en);
  assert.equal(new Intl.DisplayNames(["fr"], { type: "region" }).of("DE"), "Allemagne");
});
