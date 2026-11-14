import test from "node:test";
import assert from "node:assert/strict";
import en from "./locales/en.js";
import { navigationFr, sidebarFr } from "./locales/fr-navigation.js";
import { mapsFr } from "./locales/fr-maps.js";

test("French navigation, sidebar and maps preserve all keys and placeholders", () => {
  const tokens = text => [...text.matchAll(/\{\{?[^{}]+\}\}?|![a-z]+(?:\s+(?:help|never|add))?/g)].map(match => match[0]).sort();
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
  compare(en.navigation, navigationFr, "navigation");
  compare(en.sidebar, sidebarFr, "sidebar");
  compare(en.maps, mapsFr, "maps");
  assert.equal(count, 432);
  assert.match(mapsFr.objectivesIntro, /redémarre immédiatement/);
  assert.match(mapsFr.votemapWorkbench.resetDescription, /irréversible/);
  assert.match(mapsFr.votemapWorkbench.winnerDescription, /immédiatement/);
});
