import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
const main = JSON.parse(readFileSync(new URL("./locales/fr-draft.json", import.meta.url), "utf8"));
const { autobalancer } = JSON.parse(readFileSync(new URL("./locales/fr-settings-panels-draft.json", import.meta.url), "utf8"));

test("French balancer distinguishes disabled, live state and team counts", () => {
  assert.equal(main.language.fr, "Français");
  assert.equal(autobalancer.off, "Désactivé");
  assert.equal(autobalancer.liveState, "État en direct");
  assert.equal(autobalancer.teamCounts, "Effectifs des équipes");
  assert.equal(autobalancer.history, "Historique");
  assert.equal(autobalancer.refresh, "Actualiser");
  assert.match(autobalancer.operationsTimeline, /interventions/);
});

test("French explanations retain safeguards and arithmetic", () => {
  assert.match(autobalancer.incompleteSnapshotHelp, /incomplet/);
  assert.match(autobalancer.incompleteSnapshotHelp, /ne seront pas utilisés/);
  assert.match(main.liveViews.balance.executionExplanation, /ne transfère pas automatiquement/);
  assert.match(main.liveViews.balance.teamCalculationExplanation, /proche de 0/);
  assert.match(main.liveViews.balance.confidenceExplanation, /65 %/);
  assert.match(main.liveViews.balance.confidenceExplanation, /100 %/);
  assert.match(main.liveViews.balance.excludedData, /ne sont pas proposés/);
});
