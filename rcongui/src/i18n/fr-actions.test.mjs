import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { actionsFr } from "./locales/fr-actions.js";

function verify(source, translation, path = "actions") {
  if (typeof source === "string") {
    assert.equal(typeof translation, "string", path);
    assert.ok(translation.trim(), path);
    assert.deepEqual(
      [...translation.matchAll(/{{\s*([^{}]+)\s*}}/g)].map((match) => match[1]).sort(),
      [...source.matchAll(/{{\s*([^{}]+)\s*}}/g)].map((match) => match[1]).sort(),
      path,
    );
    assert.doesNotMatch(translation, /&(?:apos|amp|quot|lt|gt);/, path);
    return;
  }
  assert.deepEqual(Object.keys(translation).sort(), Object.keys(source).sort(), path);
  for (const key of Object.keys(source)) verify(source[key], translation[key], `${path}.${key}`);
}

test("reviewed French player and moderation actions preserve every label and placeholder", () => {
  verify(en.actions, actionsFr);
  assert.match(actionsFr.kick.name, /Expulser/);
  assert.match(actionsFr.switchOnDeath.description, /après sa prochaine mort/);
  assert.match(actionsFr.disband.irreversible, /ne peut pas être annulée/);
  assert.match(actionsFr.removeFromSquad.description, /redéploie/i);
});
