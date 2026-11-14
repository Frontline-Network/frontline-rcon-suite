import test from "node:test";
import assert from "node:assert/strict";
import { copy } from "./copy.js";
import { frenchLeadershipResults, leadershipResults, translateLeadershipResult } from "./result-copy.js";

test("French leadership voting copy includes all safety guidance, statuses and commands", () => {
  assert.deepEqual(Object.keys(copy.fr).sort(), Object.keys(copy.en).sort());
  assert.deepEqual(Object.keys(copy.fr.statuses).sort(), Object.keys(copy.en.statuses).sort());
  for (const [key, value] of Object.entries(copy.en)) {
    if (typeof value !== "string") continue;
    assert.ok(copy.fr[key]?.trim(), key);
    const commands = (s) => [...s.matchAll(/![a-z]+/g)].map((match) => match[0]).sort();
    assert.deepEqual(commands(copy.fr[key]), commands(value), key);
  }
});

test("French outcomes translate recognized system text but preserve arbitrary content", () => {
  assert.deepEqual(Object.keys(frenchLeadershipResults).sort(), Object.keys(leadershipResults).sort());
  for (const [key, [de, en]] of Object.entries(leadershipResults)) {
    assert.equal(translateLeadershipResult(`${de} / ${en}`, "fr-FR"), frenchLeadershipResults[key]);
  }
  assert.equal(translateLeadershipResult("unrecognized / player content", "fr"), "unrecognized / player content");
});
