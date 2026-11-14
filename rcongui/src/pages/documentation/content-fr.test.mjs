import test from "node:test";
import assert from "node:assert/strict";
import { helpArticles } from "./content.js";
import { frenchHelp } from "./content-fr.js";

test("every help article has a nonempty French title, summary and body", () => {
  assert.equal(Object.keys(frenchHelp).length, helpArticles.length);
  for (const article of helpArticles) {
    for (const field of ["title", "summary", "body"]) {
      assert.ok(frenchHelp[article.id]?.[field]?.trim(), `${article.id}.${field}`);
    }
  }
});
