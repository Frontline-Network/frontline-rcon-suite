import assert from "node:assert/strict";
import fs from "node:fs";
import path from "node:path";

const ROOT = path.resolve(import.meta.dirname, "..");
const read = (relativePath) =>
  fs.readFileSync(path.join(ROOT, relativePath), "utf8");

const pageHeader = read("src/components/shared/PageHeader.jsx");
const pageState = read("src/components/shared/PageState.jsx");
const dashboard = read("src/pages/dashboard.jsx");
const autosettings = read("src/pages/settings/autosettings/index.jsx");
const playerHeader = read("src/components/player/profile/Header.jsx");
const systemLayout = read(
  "src/pages/settings/system-diagnostics/SystemDiagnosticsLayout.jsx"
);
const configDetail = read("src/pages/settings/[configs]/detail.jsx");
const configFormLayout = read(
  "src/pages/settings/config-form/ConfigFormLayout.jsx"
);
const seedingWorkbenchLayout = read(
  "src/pages/settings/config-form/SeedingWorkbenchLayout.jsx"
);
const objectives = read("src/pages/settings/maps/objectives/index.jsx");
const objectivePicker = read(
  "src/pages/settings/maps/objectives/MapObjectivesPicker.jsx"
);
const votemapSettings = read(
  "src/pages/settings/maps/votemap/settings/index.jsx"
);
const controlLayout = read(
  "src/pages/settings/general-group/ControlPageLayout.jsx"
);
const apps = read("src/pages/apps/index.jsx");
const discordApp = read("src/pages/apps/discord-report-bot/index.jsx");
const autobalancer = read(
  "src/pages/settings/[configs]/autobalancer-moderator-dashboard.jsx"
);

assert.match(pageHeader, /component="header"/);
assert.match(pageHeader, /aria-labelledby=\{titleId\}/);
assert.match(pageHeader, /component="h1"/);

for (const state of [
  "empty",
  "error",
  "success",
  "offline",
  "conflict",
  "forbidden",
]) {
  assert.match(pageState, new RegExp(`${state}:`));
}
assert.match(pageState, /kind === "loading"/);
assert.match(
  pageState,
  /role=\{alertStates\.has\(kind\) \? "alert" : "status"\}/
);
assert.match(pageState, /aria-live=/);

for (const [name, source] of [
  ["dashboard", dashboard],
  ["player profile", playerHeader],
  ["apps", apps],
  ["discord app", discordApp],
]) {
  assert.match(
    source,
    /component="h1"/,
    `${name} must expose its page title as H1`
  );
}

assert.match(autosettings, /<PageHeader/);
assert.match(systemLayout, /title=\{activeSection\.label\}/);
assert.match(
  configDetail,
  /embedded=\{isIntegrationHub \|\| isSystemDiagnostics\}/
);
assert.match(configFormLayout, /\{!embedded && \(/);
assert.match(seedingWorkbenchLayout, /\{!embedded && \(/);
assert.match(objectives, /<PageHeader/);
assert.match(objectives, /id="alert-dialog-title"/);
assert.match(objectives, /id="alert-dialog-description"/);
assert.match(objectivePicker, /aria-label=\{t\("maps\.objectiveGridCell"/);
assert.match(votemapSettings, /id="votemap-default-method"/);
assert.match(votemapSettings, /labelId="votemap-default-method-label"/);
assert.match(controlLayout, /id="control-page-section"/);
assert.match(controlLayout, /labelId="control-page-section-label"/);
assert.ok(
  (autobalancer.match(/component="h1"/g) ?? []).length >= 2,
  "Autobalancer overview and proposal detail must each expose an H1"
);

console.log(
  "Page semantics contract passed: headings, labelled controls and shared states stay connected."
);
