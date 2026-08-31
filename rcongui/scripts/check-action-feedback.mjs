import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const actionResult = read("src/components/shared/ActionResult.jsx");
const actionBar = read("src/pages/settings/config-form/ConfigActionBar.jsx");
const campaignWorkbench = read(
  "src/pages/settings/broadcast-message/BroadcastCampaignWorkbench.jsx"
);

for (const kind of [
  "running",
  "success",
  "partial",
  "error",
  "conflict",
  "forbidden",
  "destructive",
]) {
  assert.match(
    actionResult,
    new RegExp(`\\b${kind}\\b`),
    `ActionResult must support the ${kind} result kind`
  );
}

assert.match(actionResult, /export const ACTION_RESULT_KINDS/);
assert.match(actionResult, /if \(!result\) return null/);
assert.match(actionResult, /result\.kind/);
assert.match(actionResult, /result\.retainedConfiguration/);
assert.match(actionResult, /result\.nextAction/);
assert.match(actionResult, /result\.auditHref/);
assert.match(actionResult, /result\.onRetry/);
assert.doesNotMatch(
  actionResult,
  /success\s*,\s*error|error\s*,\s*success/,
  "ActionResult must use one exclusive result kind instead of parallel success and error flags"
);

assert.match(actionBar, /<ActionResult result=\{result\} compact \/>/);
assert.match(campaignWorkbench, /kind: "success"/);
assert.doesNotMatch(
  campaignWorkbench,
  /actionSaved && <Alert severity="success"/,
  "Campaign save feedback must use the common exclusive result model"
);

console.log(
  "Action feedback contract passed: one exclusive result kind carries retry, retained-state and audit context."
);
